#!/usr/bin/env python3
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

    # 'emit-c' command
    emit_parser = subparsers.add_parser("emit-c", help="Emit generated C99 code without compiling")
    emit_parser.add_argument("file", help="Path to the .vl source file")
    emit_parser.add_argument("--unsafe-shelf-index", action="store_true", help="Lower shelf index reads unguarded (out-of-range becomes silent UB)")

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

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    driver = CompilerDriver()
    # 5.2 slice 11: --unsafe-shelf-index lowers shelf index READS unguarded
    # (writes stay guarded). Doc command doesn't emit, so it stays unset.
    driver.unsafe_index_flag = getattr(args, "unsafe_shelf_index", False)

    try:
        if args.command == "run":
            clean_args = []
            debug_mode = getattr(args, "debug", False)
            release_mode = getattr(args, "release", False)
            opt_level = getattr(args, "optimize", None)
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

            if debug_mode and release_mode:
                print("[Velo Error] Cannot specify both --debug and --release", file=sys.stderr)
                sys.exit(1)

            exit_code = driver.run(args.file, clean_args, debug=debug_mode, release=release_mode,
                                   opt_level=opt_level, libs=libs, lib_dirs=lib_dirs)
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
                                    lib_dirs=getattr(args, "lib_dirs", None))
            print(f"[Velo] Successfully built: {exe_path}")
        elif args.command == "emit-c":
            c_code = driver.compile_to_c(args.file)
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
                lib_dirs=getattr(args, "lib_dirs", None)
            )
            sys.exit(exit_code)
    except Exception as e:
        print(f"\n[Velo Error] {e}", file=sys.stderr)
        # 6.3 S1/S4: run/build/emit-c doc failures carrying a position (Lexer /
        # Parser errors) get the same additive source-snippet block. Prefix
        # stripping mirrors driver.check's row-building logic verbatim.
        color_enabled = (getattr(args, "color", "auto") == "always")
        if isinstance(e, LexerError):
            prefix = f"Lexer Error at line {e.line}, col {e.col}: "
            text = str(e)
            message = text[len(prefix):] if text.startswith(prefix) else text
            print_block(args.file, e.line, e.col, message, "error", sys.stderr,
                        length=getattr(e, "length", 1), color=color_enabled)
        elif isinstance(e, ParserError):
            tok = e.token
            prefix = f"Parser Error at line {tok.line}, col {tok.col}: "
            text = str(e)
            message = text[len(prefix):] if text.startswith(prefix) else text
            print_block(args.file, tok.line, tok.col, message, "error", sys.stderr,
                        length=getattr(tok, "length", 1), color=color_enabled)
        sys.exit(1)

if __name__ == "__main__":
    main()
