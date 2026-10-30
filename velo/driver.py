import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Set, List, Tuple

from velo.lexer import Lexer, LexerError
from velo.parser import Parser, ParserError
from velo.codegen_c import CCodeGenerator
from velo.ast_nodes import Program, Decl, UseStmt

class CompilerDriver:
    def __init__(self, cache_dir: Optional[str] = None):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.runtime_dir = (self.root_dir / "velo" / "runtime").resolve()
        self.cache_dir = Path(cache_dir) if cache_dir else (self.root_dir / ".velo_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # 5.2 slice 11: the --unsafe-shelf-index knob (set once by the CLI)
        self.unsafe_index_flag = False
        self.no_line_directives = False

    def _find_gcc(self) -> str:
        gcc_path = shutil.which("gcc")
        if not gcc_path:
            # Check common MSYS2 locations on Windows
            if sys.platform == "win32":
                for candidate in [
                    r"C:\msys64\ucrt64\bin\gcc.exe",
                    r"C:\msys64\mingw64\bin\gcc.exe",
                ]:
                    if os.path.exists(candidate):
                        return candidate
            raise RuntimeError("GCC not found in system PATH! Please install GCC (MinGW or MSYS2).")
        return gcc_path

    def _find_cl(self) -> Tuple[Optional[str], Optional[str]]:
        """Returns (cl_path, vcvars_bat_path). If cl is in PATH, vcvars_bat_path is None."""
        cl_path = shutil.which("cl")
        if cl_path:
            return (cl_path, None)
        if sys.platform == "win32":
            candidates = [
                r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat",
                r"C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat",
                r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat",
                r"C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat",
                r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat",
                r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional\VC\Auxiliary\Build\vcvars64.bat",
                r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\VC\Auxiliary\Build\vcvars64.bat",
                r"C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat",
            ]
            for candidate in candidates:
                if os.path.exists(candidate):
                    return ("cl", candidate)
        raise RuntimeError("MSVC compiler (cl.exe) not found in system PATH or Visual Studio installation!")

    def resolve_program(self, source_path: str) -> Program:
        root_path = Path(source_path).resolve()
        if not root_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        visited_paths: Set[Path] = set()
        all_declarations: List[Decl] = []

        def load_file(file_path: Path):
            resolved_file = file_path.resolve()
            if resolved_file in visited_paths:
                return
            visited_paths.add(resolved_file)

            if not resolved_file.exists():
                raise FileNotFoundError(f"Source file not found: {resolved_file}")

            source_text = resolved_file.read_text(encoding="utf-8")
            lexer = Lexer(source_text, filename=str(resolved_file))
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            ast = parser.parse()

            # Recursively load imported modules before adding current file declarations
            for decl in ast.declarations:
                if isinstance(decl, UseStmt):
                    mod = decl.module_path
                    if not mod.startswith("sys."):
                        if mod.startswith("std."):
                            target = (self.root_dir / "std" / f"{mod[4:].replace('.', '/')}.vl").resolve()
                        else:
                            target = (resolved_file.parent / mod).resolve()
                            if not target.exists() and not mod.endswith(".vl"):
                                target = (resolved_file.parent / f"{mod}.vl").resolve()
                        if not target.exists():
                            # Fallback: check relative to root source directory
                            alt_target = (root_path.parent / mod).resolve()
                            if not alt_target.exists() and not mod.endswith(".vl"):
                                alt_target = (root_path.parent / f"{mod}.vl").resolve()
                            if alt_target.exists():
                                target = alt_target
                            else:
                                raise FileNotFoundError(
                                    f"Module not found: '{mod}' referenced in {resolved_file}"
                                )
                        load_file(target)

            # Append non-file use declarations and all other declarations
            for decl in ast.declarations:
                if isinstance(decl, UseStmt) and not decl.module_path.startswith("sys."):
                    continue
                all_declarations.append(decl)

        load_file(root_path)
        return Program(declarations=all_declarations)

    def compile_to_c(self, source_path: str, is_test: bool = False, no_line_directives: bool = False) -> str:
        ast = self.resolve_program(source_path)
        codegen = CCodeGenerator()
        codegen.unsafe_shelf_index = self.unsafe_index_flag   # 5.2 slice 11: the knob
        codegen.is_test = is_test
        codegen.no_line_directives = no_line_directives or self.no_line_directives
        codegen.source_path = source_path
        c_code = codegen.generate(ast)
        return c_code

    def check(self, source_path: str) -> dict:
        """Validate a program (lex, parse, semantic analysis, monomorphization)
        without emitting code or executing.

        Returns a machine-readable report:
            {"file": <invoked path>, "ok": <bool>, "diagnostics": [
                {"file", "line", "col", "severity", "message"}]}

        line/col are 1-based; 0/0 marks unpositioned diagnostics (load errors
        and semantic-stage ValueErrors, which carry no position today). This
        compiler fails fast at the first lex/parse error, so typically one
        diagnostic is reported where the self-hosted compiler collects many
        (see gaps.md 6.7)."""
        diagnostics: List[dict] = []

        def add_error(message: str, line: int = 0, col: int = 0) -> None:
            diagnostics.append({
                "file": source_path,
                "line": line,
                "col": col,
                "severity": "error",
                "message": message,
            })

        try:
            ast = self.resolve_program(source_path)
            codegen = CCodeGenerator()
            codegen.unsafe_shelf_index = self.unsafe_index_flag  # 5.2 slice 11
            codegen.generate(ast)  # semantic validation; C output discarded
            return {"file": source_path, "ok": True, "diagnostics": []}
        except LexerError as exc:
            text = str(exc)
            prefix = f"Lexer Error at line {exc.line}, col {exc.col}: "
            add_error(text[len(prefix):] if text.startswith(prefix) else text, exc.line, exc.col)
        except ParserError as exc:
            tok = exc.token
            text = str(exc)
            prefix = f"Parser Error at line {tok.line}, col {tok.col}: "
            add_error(text[len(prefix):] if text.startswith(prefix) else text, tok.line, tok.col)
        except Exception as exc:
            add_error(str(exc))
        return {"file": source_path, "ok": False, "diagnostics": diagnostics}


    def build(self, source_path: str, output_path: Optional[str] = None,
              debug: bool = False, release: bool = False, opt_level: Optional[str] = None,
              libs: Optional[list] = None, lib_dirs: Optional[list] = None,
              extra_flags: Optional[list] = None,
              is_test: bool = False, cc: str = "gcc", no_line_directives: bool = False) -> str:
        path = Path(source_path).resolve()
        c_code = self.compile_to_c(source_path, is_test=is_test, no_line_directives=no_line_directives)

        # Write generated C code
        stem = f"{path.stem}_test" if is_test else path.stem
        c_file = self.cache_dir / f"{stem}.c"
        c_file.write_text(c_code, encoding="utf-8")

        # Determine target exe path
        if output_path:
            exe_file = Path(output_path).resolve()
        else:
            exe_extension = ".exe" if sys.platform == "win32" else ""
            exe_file = self.cache_dir / f"{stem}{exe_extension}"

        # 6.2 Optimization Flags & Build Modes
        if debug and release:
            raise ValueError("Cannot specify both --debug and --release")

        if cc not in ("gcc", "cl"):
            raise ValueError(f"Unknown C compiler backend '{cc}'. Expected 'gcc' or 'cl'.")

        if cc == "cl":
            cl_exe, vcvars_bat = self._find_cl()
            cl_flags = ["/nologo", "/TC", "/W3", "/wd4090", "/wd4996", "/D_CRT_SECURE_NO_WARNINGS"]
            if debug:
                cl_flags.extend(["/Od", "/Zi"])
            elif opt_level is not None:
                if opt_level == "0":
                    cl_flags.append("/Od")
                elif opt_level == "1":
                    cl_flags.append("/O1")
                else:
                    cl_flags.append("/O2")
            elif release:
                cl_flags.append("/O2")
            else:
                cl_flags.append("/O2")

            link_flags = []
            if lib_dirs:
                for d in lib_dirs:
                    raw_d = d[2:] if d.startswith("-L") else d
                    link_flags.append(f"/LIBPATH:{raw_d}")
            if libs:
                for lib in libs:
                    raw_lib = lib[2:] if lib.startswith("-l") else lib
                    if not raw_lib.endswith(".lib"):
                        raw_lib = f"{raw_lib}.lib"
                    link_flags.append(raw_lib)
            if debug:
                link_flags.append("/DEBUG")

            if extra_flags:
                for ef in extra_flags:
                    if ef.startswith("/link") or ef.startswith("-link") or ef.startswith("/LIBPATH") or ef.startswith("-L") or ef.startswith("-l"):
                        link_flags.append(ef)
                    else:
                        cl_flags.append(ef)

            cmd_parts = [
                cl_exe,
                *cl_flags,
                f"/I{self.runtime_dir}",
                str(c_file),
                f"/Fe:{exe_file}"
            ]
            if link_flags:
                cmd_parts.extend(["/link", *link_flags])

            self.last_gcc_cmd = cmd_parts
            self.last_cc_cmd = cmd_parts
            if vcvars_bat:
                args_str = subprocess.list2cmdline(cmd_parts)
                full_cmd = f'call "{vcvars_bat}" >nul && {args_str}'
                result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            else:
                result = subprocess.run(cmd_parts, capture_output=True, text=True)

            if result.returncode != 0:
                raise RuntimeError(f"MSVC Compilation Failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\n\nGenerated C Code:\n{c_code}")

            return str(exe_file)

        gcc = self._find_gcc()
        gcc_bin_dir = str(Path(gcc).parent.resolve())

        # Ensure GCC's own bin directory is first in PATH to avoid DLL Hell (e.g. PostgreSQL's libwinpthread)
        env = os.environ.copy()
        current_path = env.get("PATH", "")
        env["PATH"] = f"{gcc_bin_dir}{os.pathsep}{current_path}"

        flags = []
        if opt_level is not None:
            flags.append(f"-O{opt_level}")
        elif debug:
            flags.append("-O0")
        elif release:
            flags.append("-O3")
        else:
            flags.append("-O2")

        if debug:
            flags.append("-g")
        if release:
            flags.append("-flto")

        # 6.1 Linker Flags for Third-Party C Libraries (-l<lib>, -L<dir>)
        linker_flags = []
        if lib_dirs:
            for d in lib_dirs:
                linker_flags.append(d if d.startswith("-L") else f"-L{d}")
        if libs:
            for lib in libs:
                linker_flags.append(lib if lib.startswith("-l") else f"-l{lib}")
        if extra_flags:
            linker_flags.extend(extra_flags)

        cmd = [
            gcc,
            *flags,
            "-std=c99",
            str(c_file),
            f"-I{self.runtime_dir}",
            *linker_flags,
            "-o",
            str(exe_file)
        ]
        self.last_gcc_cmd = cmd
        self.last_cc_cmd = cmd

        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            raise RuntimeError(f"GCC Compilation Failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\n\nGenerated C Code:\n{c_code}")

        return str(exe_file)

    def run(self, source_path: str, args: Optional[list] = None,
            output_path: Optional[str] = None,
            debug: bool = False, release: bool = False, opt_level: Optional[str] = None,
            libs: Optional[list] = None, lib_dirs: Optional[list] = None,
            extra_flags: Optional[list] = None,
            cc: str = "gcc", no_line_directives: bool = False) -> int:
        exe_path = self.build(source_path, output_path=output_path,
                              debug=debug, release=release, opt_level=opt_level,
                              libs=libs, lib_dirs=lib_dirs, extra_flags=extra_flags, cc=cc,
                              no_line_directives=no_line_directives)
        cmd = [exe_path] + (args or [])
        res = subprocess.run(cmd)
        return res.returncode

    def test(self, target_path: Optional[str] = None, filter_str: Optional[str] = None,
             debug: bool = False, release: bool = False, opt_level: Optional[str] = None,
             libs: Optional[list] = None, lib_dirs: Optional[list] = None,
             cc: str = "gcc", no_line_directives: bool = False) -> int:
        target_str = target_path if target_path is not None else "."
        p = Path(target_str).resolve()
        test_files: List[Path] = []
        if p.is_file():
            test_files.append(p)
        elif p.is_dir():
            for f in sorted(p.rglob("*.vl")):
                # Check if file has test declarations
                try:
                    txt = f.read_text(encoding="utf-8")
                    if 'test "' in txt or "test '" in txt:
                        test_files.append(f)
                except Exception:
                    pass
        else:
            raise FileNotFoundError(f"Test target not found: {target_str}")

        if not test_files:
            print("No test files found.")
            return 0

        overall_exit = 0
        for tf in test_files:
            exe_path = self.build(str(tf), is_test=True, debug=debug, release=release,
                                  opt_level=opt_level, libs=libs, lib_dirs=lib_dirs, cc=cc,
                                  no_line_directives=no_line_directives)
            cmd = [exe_path]
            if filter_str:
                cmd.extend(["--filter", filter_str])
            res = subprocess.run(cmd)
            if res.returncode != 0:
                overall_exit = res.returncode
        return overall_exit

    def generate_docs(self, source_path: str) -> str:
        from velo.docgen import generate_markdown_docs
        return generate_markdown_docs(source_path)
