"""Check code formatting for Velo source files using `velo fmt --check`.

Used in CI workflows and local development pre-checks.
Adheres to the repository encoding contract (ASCII only output).

Usage:
    python scripts/check_formatting.py               # Checks changed/staged files, or help if none
    python scripts/check_formatting.py --staged      # Checks files staged in git index
    python scripts/check_formatting.py --changed     # Checks files changed against base/HEAD~1
    python scripts/check_formatting.py --all <dirs>  # Checks all .vl files in specified directories
    python scripts/check_formatting.py path/to/file.vl
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def find_velo_bin() -> str:
    env_bin = os.environ.get("VELO_BIN")
    if env_bin and Path(env_bin).exists():
        return str(Path(env_bin).resolve())
    candidates = [
        ROOT / "bin" / ("velo.exe" if sys.platform == "win32" else "velo"),
        ROOT / "bin" / ("velo" if sys.platform == "win32" else "velo.exe"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return "velo"


def get_git_files(args: list[str]) -> list[str]:
    try:
        res = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            encoding="utf-8",
            errors="replace",
        )
        if res.returncode != 0:
            return []
        lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        return [f for f in lines if f.endswith(".vl") and (ROOT / f).exists()]
    except Exception:
        return []


def check_files(velo_bin: str, files: list[str]) -> int:
    if not files:
        print("[check_formatting] No Velo source files to check.")
        return 0

    failed: list[str] = []
    for f in files:
        file_path = str(ROOT / f) if not Path(f).is_absolute() else f
        res = subprocess.run(
            [velo_bin, "fmt", file_path, "--check"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            encoding="utf-8",
            errors="replace",
        )
        if res.returncode != 0:
            failed.append(f)
            sys.stdout.write(res.stdout)
            if res.stderr:
                sys.stderr.write(res.stderr)

    if failed:
        print(f"[check_formatting] FAILED: {len(failed)} unformatted file(s) detected:")
        for f in failed:
            print(f"  - {f}")
        print("Run 'velo fmt <file>' to format them.")
        return 1

    print(f"[check_formatting] SUCCESS: All {len(files)} file(s) properly formatted.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Velo source formatting.")
    parser.add_argument("--staged", action="store_true", help="Check staged git files")
    parser.add_argument("--changed", action="store_true", help="Check modified git files")
    parser.add_argument("--all", nargs="*", help="Check all .vl files in given directories")
    parser.add_argument("files", nargs="*", help="Specific files to check")

    args = parser.parse_args()
    velo_bin = find_velo_bin()

    targets: list[str] = []
    if args.files:
        targets.extend(args.files)
    elif args.all is not None:
        dirs = args.all if args.all else ["."]
        for d in dirs:
            dir_path = ROOT / d
            if dir_path.is_file() and d.endswith(".vl"):
                targets.append(str(dir_path.relative_to(ROOT)))
            elif dir_path.is_dir():
                for p in dir_path.rglob("*.vl"):
                    # Exclude build products and hidden dirs
                    rel = p.relative_to(ROOT)
                    parts = rel.parts
                    if any(part in (".git", ".velo_cache", "bin", "node_modules") for part in parts):
                        continue
                    targets.append(str(rel))
    elif args.staged:
        targets = get_git_files(["diff", "--cached", "--name-only", "--diff-filter=ACM"])
    elif args.changed:
        targets = get_git_files(["diff", "--name-only", "--diff-filter=ACM", "HEAD~1"])
        if not targets:
            targets = get_git_files(["diff", "--name-only", "--diff-filter=ACM"])
    else:
        # Default behavior: check staged files if any, otherwise changed files
        targets = get_git_files(["diff", "--cached", "--name-only", "--diff-filter=ACM"])
        if not targets:
            targets = get_git_files(["diff", "--name-only", "--diff-filter=ACM"])

    return check_files(velo_bin, targets)


if __name__ == "__main__":
    sys.exit(main())
