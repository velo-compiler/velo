#!/usr/bin/env python3
import sys
import argparse
from velo.driver import CompilerDriver

def main():
    parser = argparse.ArgumentParser(
        prog="velo",
        description="Velo Programming Language Compiler (Stage 1 Bootstrap)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Velo command to execute")

    # 'run' command
    run_parser = subparsers.add_parser("run", help="Compile and immediately execute a Velo program")
    run_parser.add_argument("file", help="Path to the .vl source file")
    run_parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to the program")

    # 'build' command
    build_parser = subparsers.add_parser("build", help="Compile a Velo program into a native executable")
    build_parser.add_argument("file", help="Path to the .vl source file")
    build_parser.add_argument("-o", "--output", help="Path for the output executable")

    # 'emit-c' command
    emit_parser = subparsers.add_parser("emit-c", help="Emit generated C99 code without compiling")
    emit_parser.add_argument("file", help="Path to the .vl source file")

    # 'doc' command
    doc_parser = subparsers.add_parser("doc", help="Generate Markdown API documentation from source")
    doc_parser.add_argument("file", help="Path to the .vl source file")
    doc_parser.add_argument("-o", "--output", help="Path for the output markdown file")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    driver = CompilerDriver()

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
