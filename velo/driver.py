import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Optional

from velo.lexer import Lexer
from velo.parser import Parser
from velo.codegen_c import CCodeGenerator

class CompilerDriver:
    def __init__(self, cache_dir: Optional[str] = None):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.runtime_dir = (self.root_dir / "velo" / "runtime").resolve()
        self.cache_dir = Path(cache_dir) if cache_dir else (self.root_dir / ".velo_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

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

    def compile_to_c(self, source_path: str) -> str:
        path = Path(source_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        source_text = path.read_text(encoding="utf-8")

        # 1. Lex
        lexer = Lexer(source_text, filename=str(path))
        tokens = lexer.tokenize()

        # 2. Parse
        parser = Parser(tokens)
        ast = parser.parse()

        # 3. Codegen
        codegen = CCodeGenerator()
        c_code = codegen.generate(ast)

        return c_code

    def build(self, source_path: str, output_path: Optional[str] = None) -> str:
        path = Path(source_path).resolve()
        c_code = self.compile_to_c(source_path)

        # Write generated C code
        stem = path.stem
        c_file = self.cache_dir / f"{stem}.c"
        c_file.write_text(c_code, encoding="utf-8")

        # Determine target exe path
        if output_path:
            exe_file = Path(output_path).resolve()
        else:
            exe_extension = ".exe" if sys.platform == "win32" else ""
            exe_file = self.cache_dir / f"{stem}{exe_extension}"

        gcc = self._find_gcc()
        gcc_bin_dir = str(Path(gcc).parent.resolve())

        # Ensure GCC's own bin directory is first in PATH to avoid DLL Hell (e.g. PostgreSQL's libwinpthread)
        env = os.environ.copy()
        current_path = env.get("PATH", "")
        env["PATH"] = f"{gcc_bin_dir}{os.pathsep}{current_path}"

        cmd = [
            gcc,
            "-O2",
            "-std=c99",
            str(c_file),
            f"-I{self.runtime_dir}",
            "-o",
            str(exe_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            raise RuntimeError(f"GCC Compilation Failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\n\nGenerated C Code:\n{c_code}")

        return str(exe_file)

    def run(self, source_path: str, args: Optional[list] = None) -> int:
        exe_path = self.build(source_path)
        cmd = [exe_path] + (args or [])
        res = subprocess.run(cmd)
        return res.returncode
