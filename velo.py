#!/usr/bin/env python3
"""
HISTORICAL ARTIFACT — STAGE 1 BOOTSTRAP TRANSPILER (RETIRED)

This Python-based implementation was the Stage 1 prototype used to bootstrap
the self-hosted Stage 2 Velo compiler ('src/').

Per Task 80.5 and AGENTS.md, Stage 1 is frozen, retired, and exempt from language
parity and test maintenance requirements. The canonical compiler is in 'src/' and
bootstraps via 'bootstrap.c'. Do not modify this file or 'velo/' for new language
features.
"""
import os
import sys
import json
import argparse
from pathlib import Path
from velo.driver import CompilerDriver
from velo.lexer import LexerError            # 6.3 S1: catch-all block positions
from velo.parser import ParserError          # 6.3 S1: catch-all block positions
from velo.pretty_diag import print_block     # 6.3 S1: additive source-snippet blocks

def main():
    # 5.2: diagnostics (and all tool output) must carry the same bytes as the
    # self-hosted compiler — UTF-8 everywhere, so identical wording means
    # identical bytes on both stages (em-dash in shelf messages, gaps 6.7).
    try:
        if sys.stdout.encoding and sys.stdout.encoding.lower().replace('-', '') != 'utf8':
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if sys.stderr.encoding and sys.stderr.encoding.lower().replace('-', '') != 'utf8':
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass  # non-reconfigurable streams keep their locale encoding

    parser = argparse.ArgumentParser(
        prog="velo",
        description="Velo Programming Language Compiler (Stage 1 Bootstrap)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Velo command to execute")

    # 'run' command
    run_parser = subparsers.add_parser("run", help="Compile and immediately execute a Velo program")
    run_parser.add_argument("file", help="Path to the .vl source file")
    run_parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to the program")
    run_parser.add_argument("--unsafe-shelf-index", action="store_true", help="Lower shelf index reads unguarded (out-of-range becomes silent UB)")
    run_parser.add_argument("--debug", action="store_true", help="Compile with debug symbols (-O0 -g)")
    run_parser.add_argument("--release", action="store_true", help="Compile with release optimizations and LTO (-O3 -flto)")
    run_parser.add_argument("-O", "--optimize", choices=["0", "1", "2", "3", "s", "fast"], help="GCC optimization level")
    run_parser.add_argument("-l", dest="libs", action="append", default=[], help="Link with external library (e.g. -lraylib)")
    run_parser.add_argument("-L", dest="lib_dirs", action="append", default=[], help="Add library directory to search path (e.g. -L./lib)")
    run_parser.add_argument("--cc", choices=["gcc", "cl"], default="gcc", help="C compiler backend to invoke (default: gcc)")
    run_parser.add_argument("--no-line-directives", action="store_true", help="Suppress #line preprocessor directives in emitted C")

    # 'build' command
    build_parser = subparsers.add_parser("build", help="Compile a Velo program into a native executable")
    build_parser.add_argument("file", help="Path to the .vl source file")
    build_parser.add_argument("-o", "--output", help="Path for the output executable")
    build_parser.add_argument("--unsafe-shelf-index", action="store_true", help="Lower shelf index reads unguarded (out-of-range becomes silent UB)")
    build_parser.add_argument("--debug", action="store_true", help="Compile with debug symbols (-O0 -g)")
    build_parser.add_argument("--release", action="store_true", help="Compile with release optimizations and LTO (-O3 -flto)")
    build_parser.add_argument("-O", "--optimize", choices=["0", "1", "2", "3", "s", "fast"], help="GCC optimization level")
    build_parser.add_argument("-l", dest="libs", action="append", default=[], help="Link with external library (e.g. -lraylib)")
    build_parser.add_argument("-L", dest="lib_dirs", action="append", default=[], help="Add library directory to search path (e.g. -L./lib)")
    build_parser.add_argument("--cc", choices=["gcc", "cl"], default="gcc", help="C compiler backend to invoke (default: gcc)")
    build_parser.add_argument("--no-line-directives", action="store_true", help="Suppress #line preprocessor directives in emitted C")

    # 'emit-c' command
    emit_parser = subparsers.add_parser("emit-c", help="Emit generated C99 code without compiling")
    emit_parser.add_argument("file", help="Path to the .vl source file")
    emit_parser.add_argument("-o", "--output", help="Path for the output C source file")
    emit_parser.add_argument("--unsafe-shelf-index", action="store_true", help="Lower shelf index reads unguarded (out-of-range becomes silent UB)")
    emit_parser.add_argument("--no-line-directives", action="store_true", help="Suppress #line preprocessor directives in emitted C")

    # 'check' command
    check_parser = subparsers.add_parser("check", help="Validate a Velo program without generating code")
    check_parser.add_argument("file", help="Path to the .vl source file")
    check_parser.add_argument("--json", action="store_true", dest="json_mode", help="Emit diagnostics as machine-readable JSON")
    check_parser.add_argument("--unsafe-shelf-index", action="store_true", help="Lower shelf index reads unguarded (out-of-range becomes silent UB)")
    check_parser.add_argument("--color", choices=["auto", "always", "never"], default="auto", help="Configure diagnostic coloring: auto|always|never")

    # 'doc' command
    doc_parser = subparsers.add_parser("doc", help="Generate Markdown API documentation from source")
    doc_parser.add_argument("file", help="Path to the .vl source file")
    doc_parser.add_argument("-o", "--output", help="Path for the output markdown file")

    # 'lsp' command
    lsp_parser = subparsers.add_parser("lsp", help="Run the Velo Language Server (stdio JSON-RPC)")
    lsp_parser.add_argument("repo_root", nargs="?", default=None, help="Root repository directory (default: auto-detected)")

    # 'test' command
    test_parser = subparsers.add_parser("test", help="Run tests defined via 'test' blocks")
    test_parser.add_argument("target", nargs="?", default=".", help="Path to .vl source file or directory (default: current directory)")
    test_parser.add_argument("-k", "--filter", dest="filter", default=None, help="Filter tests by name substring")
    test_parser.add_argument("--unsafe-shelf-index", action="store_true", help="Lower shelf index reads unguarded (out-of-range becomes silent UB)")
    test_parser.add_argument("--debug", action="store_true", help="Compile with debug symbols (-O0 -g)")
    test_parser.add_argument("--release", action="store_true", help="Compile with release optimizations and LTO (-O3 -flto)")
    test_parser.add_argument("-O", "--optimize", choices=["0", "1", "2", "3", "s", "fast"], help="GCC optimization level")
    test_parser.add_argument("-l", dest="libs", action="append", default=[], help="Link with external library (e.g. -lraylib)")
    test_parser.add_argument("-L", dest="lib_dirs", action="append", default=[], help="Add library directory to search path (e.g. -L./lib)")
    test_parser.add_argument("--cc", choices=["gcc", "cl"], default="gcc", help="C compiler backend to invoke (default: gcc)")
    test_parser.add_argument("--no-line-directives", action="store_true", help="Suppress #line preprocessor directives in emitted C")

    # 'pkg' command
    pkg_parser = subparsers.add_parser("pkg", help="Package manager commands")
    pkg_subparsers = pkg_parser.add_subparsers(dest="pkg_command", help="Package action")
    pkg_check_parser = pkg_subparsers.add_parser("check", help="Validate a velo.pkg package manifest")
    pkg_check_parser.add_argument("manifest_path", nargs="?", default="velo.pkg", help="Path to velo.pkg (default: velo.pkg)")

    pkg_build_parser = pkg_subparsers.add_parser("build", help="Build project defined by velo.pkg")
    pkg_build_parser.add_argument("manifest_path", nargs="?", default="velo.pkg", help="Path to velo.pkg (default: velo.pkg)")
    pkg_build_parser.add_argument("-o", "--output", help="Path for the output executable")
    pkg_build_parser.add_argument("--unsafe-shelf-index", action="store_true", help="Lower shelf index reads unguarded")
    pkg_build_parser.add_argument("--debug", action="store_true", help="Compile with debug symbols (-O0 -g)")
    pkg_build_parser.add_argument("--release", action="store_true", help="Compile with release optimizations and LTO (-O3 -flto)")
    pkg_build_parser.add_argument("-O", "--optimize", choices=["0", "1", "2", "3", "s", "fast"], help="GCC optimization level")
    pkg_build_parser.add_argument("-l", dest="libs", action="append", default=[], help="Link with external library (e.g. -lraylib)")
    pkg_build_parser.add_argument("-L", dest="lib_dirs", action="append", default=[], help="Add library directory to search path (e.g. -L./lib)")
    pkg_build_parser.add_argument("--cc", choices=["gcc", "cl"], default="gcc", help="C compiler backend to invoke (default: gcc)")
    pkg_build_parser.add_argument("--no-line-directives", action="store_true", help="Suppress #line preprocessor directives in emitted C")

    pkg_run_parser = pkg_subparsers.add_parser("run", help="Build and run project defined by velo.pkg")
    pkg_run_parser.add_argument("manifest_path", nargs="?", default="velo.pkg", help="Path to velo.pkg (default: velo.pkg)")
    pkg_run_parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to the program")
    pkg_run_parser.add_argument("--unsafe-shelf-index", action="store_true", help="Lower shelf index reads unguarded")
    pkg_run_parser.add_argument("--debug", action="store_true", help="Compile with debug symbols (-O0 -g)")
    pkg_run_parser.add_argument("--release", action="store_true", help="Compile with release optimizations and LTO (-O3 -flto)")
    pkg_run_parser.add_argument("-O", "--optimize", choices=["0", "1", "2", "3", "s", "fast"], help="GCC optimization level")
    pkg_run_parser.add_argument("-l", dest="libs", action="append", default=[], help="Link with external library (e.g. -lraylib)")
    pkg_run_parser.add_argument("-L", dest="lib_dirs", action="append", default=[], help="Add library directory to search path (e.g. -L./lib)")
    pkg_run_parser.add_argument("--cc", choices=["gcc", "cl"], default="gcc", help="C compiler backend to invoke (default: gcc)")
    pkg_run_parser.add_argument("--no-line-directives", action="store_true", help="Suppress #line preprocessor directives in emitted C")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    driver = CompilerDriver()
    # 5.2 slice 11: --unsafe-shelf-index lowers shelf index READS unguarded
    # (writes stay guarded). Doc command doesn't emit, so it stays unset.
    driver.unsafe_index_flag = getattr(args, "unsafe_shelf_index", False)
    driver.no_line_directives = getattr(args, "no_line_directives", False)

    try:
        if args.command == "run":
            clean_args = []
            debug_mode = getattr(args, "debug", False)
            release_mode = getattr(args, "release", False)
            opt_level = getattr(args, "optimize", None)
            cc_backend = getattr(args, "cc", "gcc")
            libs = list(getattr(args, "libs", []) or [])
            lib_dirs = list(getattr(args, "lib_dirs", []) or [])

            i = 0
            raw_args = args.args or []
            while i < len(raw_args):
                arg = raw_args[i]
                if arg == "--":
                    clean_args.extend(raw_args[i + 1:])
                    break
                elif arg == "--debug":
                    debug_mode = True
                elif arg == "--release":
                    release_mode = True
                elif arg == "--unsafe-shelf-index":
                    driver.unsafe_index_flag = True
                elif arg == "--no-line-directives":
                    driver.no_line_directives = True
                elif arg == "--cc" and i + 1 < len(raw_args):
                    cc_backend = raw_args[i + 1]
                    i += 1
                elif arg.startswith("--cc="):
                    cc_backend = arg[5:]
                elif arg.startswith("-O"):
                    opt_level = arg[2:]
                elif arg == "-l" and i + 1 < len(raw_args):
                    libs.append(raw_args[i + 1])
                    i += 1
                elif arg.startswith("-l"):
                    libs.append(arg[2:])
                elif arg == "-L" and i + 1 < len(raw_args):
                    lib_dirs.append(raw_args[i + 1])
                    i += 1
                elif arg.startswith("-L"):
                    lib_dirs.append(arg[2:])
                else:
                    clean_args.append(arg)
                i += 1

            if cc_backend not in ("gcc", "cl"):
                print(f"[Velo Error] Unknown C compiler backend '{cc_backend}'. Expected 'gcc' or 'cl'.", file=sys.stderr)
                sys.exit(1)

            if debug_mode and release_mode:
                print("[Velo Error] Cannot specify both --debug and --release", file=sys.stderr)
                sys.exit(1)

            exit_code = driver.run(args.file, clean_args, debug=debug_mode, release=release_mode,
                                   opt_level=opt_level, libs=libs, lib_dirs=lib_dirs, cc=cc_backend)
            sys.exit(exit_code)
        elif args.command == "build":
            if getattr(args, "debug", False) and getattr(args, "release", False):
                print("[Velo Error] Cannot specify both --debug and --release", file=sys.stderr)
                sys.exit(1)
            exe_path = driver.build(args.file, args.output,
                                    debug=getattr(args, "debug", False),
                                    release=getattr(args, "release", False),
                                    opt_level=getattr(args, "optimize", None),
                                    libs=getattr(args, "libs", None),
                                    lib_dirs=getattr(args, "lib_dirs", None),
                                    cc=getattr(args, "cc", "gcc"))
            print(f"[Velo] Successfully built: {exe_path}")
        elif args.command == "emit-c":
            c_code = driver.compile_to_c(args.file)
            if getattr(args, "output", None):
                Path(args.output).write_text(c_code, encoding="utf-8")
            else:
                print(c_code)
        elif args.command == "check":
            report = driver.check(args.file)
            if args.json_mode:
                print(json.dumps(report, ensure_ascii=False))
            else:
                color_enabled = (getattr(args, "color", "auto") == "always")
                for diag in report["diagnostics"]:
                    tag = "Warning" if diag["severity"] == "warning" else "Error"
                    if diag["line"] > 0:
                        print(f"[Velo {tag}] {diag['file']}:{diag['line']}:{diag['col']} - {diag['message']}", file=sys.stderr)
                        # 6.3 S1/S4: the additive source-snippet block rides the row.
                        print_block(diag["file"], diag["line"], diag["col"],
                                    diag["message"], diag["severity"], sys.stderr,
                                    color=color_enabled)
                    else:
                        print(f"[Velo {tag}] {diag['message']}", file=sys.stderr)
            if report["ok"] and not args.json_mode:
                print(f"[Velo] Check passed: {args.file}")
            sys.exit(0 if report["ok"] else 1)
        elif args.command == "doc":
            docs = driver.generate_docs(args.file)
            if args.output:
                Path(args.output).write_text(docs, encoding="utf-8")
                print(f"[Velo] Successfully generated documentation: {args.output}")
            else:
                print(docs, end="")
        elif args.command == "lsp":
            from velo.lsp import run_server
            sys.exit(run_server(args.repo_root))
        elif args.command == "test":
            if getattr(args, "debug", False) and getattr(args, "release", False):
                print("[Velo Error] Cannot specify both --debug and --release", file=sys.stderr)
                sys.exit(1)
            exit_code = driver.test(
                args.target,
                filter_str=args.filter,
                debug=getattr(args, "debug", False),
                release=getattr(args, "release", False),
                opt_level=getattr(args, "optimize", None),
                libs=getattr(args, "libs", None),
                lib_dirs=getattr(args, "lib_dirs", None),
                cc=getattr(args, "cc", "gcc")
            )
            sys.exit(exit_code)
        elif args.command == "pkg":
            from velo.manifest import load_manifest, ManifestError
            sub_cmd = getattr(args, "pkg_command", None) or "check"
            m_path = getattr(args, "manifest_path", "velo.pkg") or "velo.pkg"
            if sub_cmd == "check":
                if os.path.isdir(m_path):
                    m_path = os.path.join(m_path, "velo.pkg")
                try:
                    m = load_manifest(m_path)
                    print(f"[Velo] Valid package manifest: {m.pkg.name} v{m.pkg.version} ({m.pkg.entry})")
                    sys.exit(0)
                except ManifestError as e:
                    print(str(e), file=sys.stderr)
                    sys.exit(1)
            elif sub_cmd in ("build", "run"):
                clean_args = []
                debug_mode = getattr(args, "debug", False)
                release_mode = getattr(args, "release", False)
                opt_level = getattr(args, "optimize", None)
                cc_backend = getattr(args, "cc", "gcc")
                libs = list(getattr(args, "libs", []) or [])
                lib_dirs = list(getattr(args, "lib_dirs", []) or [])

                if sub_cmd == "run":
                    raw_args = getattr(args, "args", []) or []
                    if not (os.path.isfile(m_path) or os.path.isdir(m_path) or m_path.endswith(".pkg")) and os.path.isfile("velo.pkg"):
                        clean_args.append(m_path)
                        m_path = "velo.pkg"

                    i = 0
                    while i < len(raw_args):
                        arg = raw_args[i]
                        if arg == "--":
                            clean_args.extend(raw_args[i + 1:])
                            break
                        elif arg == "--debug":
                            debug_mode = True
                        elif arg == "--release":
                            release_mode = True
                        elif arg == "--unsafe-shelf-index":
                            driver.unsafe_index_flag = True
                        elif arg == "--no-line-directives":
                            driver.no_line_directives = True
                        elif arg == "--cc" and i + 1 < len(raw_args):
                            cc_backend = raw_args[i + 1]
                            i += 1
                        elif arg.startswith("--cc="):
                            cc_backend = arg[5:]
                        elif arg.startswith("-O"):
                            opt_level = arg[2:]
                        elif arg == "-l" and i + 1 < len(raw_args):
                            libs.append(raw_args[i + 1])
                            i += 1
                        elif arg.startswith("-l"):
                            libs.append(arg[2:])
                        elif arg == "-L" and i + 1 < len(raw_args):
                            lib_dirs.append(raw_args[i + 1])
                            i += 1
                        elif arg.startswith("-L"):
                            lib_dirs.append(arg[2:])
                        else:
                            clean_args.append(arg)
                        i += 1

                if os.path.isdir(m_path):
                    m_path = os.path.join(m_path, "velo.pkg")

                try:
                    m = load_manifest(m_path)
                except ManifestError as e:
                    print(str(e), file=sys.stderr)
                    sys.exit(1)

                m_dir = os.path.dirname(m_path) or "."
                entry_file = os.path.normpath(os.path.join(m_dir, m.pkg.entry))
                if not os.path.exists(entry_file):
                    print(f"[Velo Error] Entry source file not found: {entry_file}", file=sys.stderr)
                    sys.exit(1)

                if cc_backend not in ("gcc", "cl"):
                    print(f"[Velo Error] Unknown C compiler backend '{cc_backend}'. Expected 'gcc' or 'cl'.", file=sys.stderr)
                    sys.exit(1)

                if debug_mode and release_mode:
                    print("[Velo Error] Cannot specify both --debug and --release", file=sys.stderr)
                    sys.exit(1)

                merged_libs = list(libs) + list(m.link.libs)
                extra_flags = list(m.link.flags)

                if sub_cmd == "build":
                    out_path = getattr(args, "output", None)
                    if not out_path:
                        bin_dir = os.path.join(m_dir, "bin")
                        exe_ext = ".exe" if sys.platform == "win32" else ""
                        if os.path.isdir(bin_dir):
                            out_path = os.path.join(bin_dir, f"{m.pkg.name}{exe_ext}")
                        else:
                            out_path = os.path.join(m_dir, f"{m.pkg.name}{exe_ext}")
                    exe_path = driver.build(entry_file, out_path,
                                            debug=debug_mode, release=release_mode,
                                            opt_level=opt_level, libs=merged_libs,
                                            lib_dirs=lib_dirs, extra_flags=extra_flags,
                                            cc=cc_backend)
                    print("[Velo] Successfully built binary!")
                    sys.exit(0)
                else:
                    exit_code = driver.run(entry_file, clean_args,
                                           debug=debug_mode, release=release_mode,
                                           opt_level=opt_level, libs=merged_libs,
                                           lib_dirs=lib_dirs, extra_flags=extra_flags,
                                           cc=cc_backend)
                    sys.exit(exit_code)
            else:
                print(f"[Velo Error] Unknown 'pkg' subcommand '{sub_cmd}'.", file=sys.stderr)
                sys.exit(1)
    except Exception as e:
        print(f"\n[Velo Error] {e}", file=sys.stderr)
        # 6.3 S1/S4: run/build/emit-c doc failures carrying a position (Lexer /
        # Parser errors) get the same additive source-snippet block. Prefix
        # stripping mirrors driver.check's row-building logic verbatim.
        color_enabled = (getattr(args, "color", "auto") == "always")
        err_path = getattr(args, "file", None) or getattr(args, "target", "<unknown>")
        if isinstance(e, LexerError):
            prefix = f"Lexer Error at line {e.line}, col {e.col}: "
            text = str(e)
            message = text[len(prefix):] if text.startswith(prefix) else text
            print_block(err_path, e.line, e.col, message, "error", sys.stderr,
                        length=getattr(e, "length", 1), color=color_enabled)
        elif isinstance(e, ParserError):
            tok = e.token
            prefix = f"Parser Error at line {tok.line}, col {tok.col}: "
            text = str(e)
            message = text[len(prefix):] if text.startswith(prefix) else text
            print_block(err_path, tok.line, tok.col, message, "error", sys.stderr,
                        length=getattr(tok, "length", 1), color=color_enabled)
        sys.exit(1)

if __name__ == "__main__":
    main()
