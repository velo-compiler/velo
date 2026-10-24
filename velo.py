#!/usr/bin/env python3
import sys
import json
import argparse
from pathlib import Path
from velo.driver import CompilerDriver

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

    # 'build' command
    build_parser = subparsers.add_parser("build", help="Compile a Velo program into a native executable")
    build_parser.add_argument("file", help="Path to the .vl source file")
    build_parser.add_argument("-o", "--output", help="Path for the output executable")
    build_parser.add_argument("--unsafe-shelf-index", action="store_true", help="Lower shelf index reads unguarded (out-of-range becomes silent UB)")

    # 'emit-c' command
    emit_parser = subparsers.add_parser("emit-c", help="Emit generated C99 code without compiling")
    emit_parser.add_argument("file", help="Path to the .vl source file")
    emit_parser.add_argument("--unsafe-shelf-index", action="store_true", help="Lower shelf index reads unguarded (out-of-range becomes silent UB)")

    # 'check' command
    check_parser = subparsers.add_parser("check", help="Validate a Velo program without generating code")
    check_parser.add_argument("file", help="Path to the .vl source file")
    check_parser.add_argument("--json", action="store_true", dest="json_mode", help="Emit diagnostics as machine-readable JSON")
    check_parser.add_argument("--unsafe-shelf-index", action="store_true", help="Lower shelf index reads unguarded (out-of-range becomes silent UB)")

    # 'doc' command
    doc_parser = subparsers.add_parser("doc", help="Generate Markdown API documentation from source")
    doc_parser.add_argument("file", help="Path to the .vl source file")
    doc_parser.add_argument("-o", "--output", help="Path for the output markdown file")

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
            exit_code = driver.run(args.file, args.args)
            sys.exit(exit_code)
        elif args.command == "build":
            exe_path = driver.build(args.file, args.output)
            print(f"[Velo] Successfully built: {exe_path}")
        elif args.command == "emit-c":
            c_code = driver.compile_to_c(args.file)
            print(c_code)
        elif args.command == "check":
            report = driver.check(args.file)
            if args.json_mode:
                print(json.dumps(report, ensure_ascii=False))
            else:
                for diag in report["diagnostics"]:
                    tag = "Warning" if diag["severity"] == "warning" else "Error"
                    if diag["line"] > 0:
                        print(f"[Velo {tag}] {diag['file']}:{diag['line']}:{diag['col']} - {diag['message']}", file=sys.stderr)
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
    except Exception as e:
        print(f"\n[Velo Error] {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
