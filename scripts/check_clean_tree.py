"""Fail when a command mutates the working tree outside the allowlist.

Task 67.4 of the Phase 67 audit. Phases 67.1-67.3 fixed eight tests that
depended on an ambient `scratch/` directory: they wrote into it without
creating it, so they passed only on a machine where some earlier run had left
it behind. Those defects were invisible for as long as the developer tree
carried the directory, and every fix is only as durable as its enforcement.

This script is that enforcement. It snapshots the working tree, runs the
command, snapshots again, and fails if the command created a path outside the
allowlist or modified a tracked file. So a future test that writes a relative
path into the repository root breaks CI instead of quietly making itself
depend on state that a clean checkout does not have.

TWO SNAPSHOTS, ON PURPOSE
-------------------------
`git status` alone is not enough. Git does not track *empty* directories: a
test that runs `fs_create_dir_str("scratch")` and cleans its files up leaves
`scratch/` behind, and `git status --porcelain -uall` reports nothing at all.
That is not hypothetical -- an empty ambient `scratch/` is exactly the state
Task 67.3 found in the repository, and it is the state every later suite then
depended on. So the gate diffs the filesystem as well as git:

* the filesystem walk sees new files and new directories, including empty ones;
* `git status` sees modifications to *tracked* files, which a path-set diff
  cannot distinguish from a pre-existing file.

Build products are expected, so both allow `bin/`, `.velo_cache/`,
`__pycache__/`, `node_modules/` and compiled artefacts (`*.exe`, `*.o`, ...).
Everything else -- `scratch/`, `test_output.log`, any stray file or directory
-- is reported as a leak.

Usage (from the repository root):

    python scripts/check_clean_tree.py -- python -m pytest tests -q

Exit status is 0 when the tree is unchanged apart from allowed build
artefacts, 1 when something leaked, and the command's own non-zero status is
propagated when it fails, so a failing test suite is never reported as a
passing gate.

`--root` exists so the gate can be tested against a throwaway git repository
instead of the real tree; arguments after `--` are the command to run.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ALLOWED_PREFIXES = (
    "bin/",
    ".velo_cache/",
    "website/node_modules/",
)

ALLOWED_SUFFIXES = (
    ".pyc",
    ".pyo",
    ".exe",
    ".o",
    ".obj",
    ".dll",
    ".lib",
    ".pdb",
    ".ilk",
)

# Directories that are build/test output or version control internals. They are
# pruned from the walk, which also allows them by prefix.
PRUNED_DIRS = {
    "bin",
    ".velo_cache",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    ".git",
}


def is_allowed(path: str) -> bool:
    if path.startswith(ALLOWED_PREFIXES):
        return True
    if any(part in PRUNED_DIRS for part in path.split("/")):
        return True
    return path.endswith(ALLOWED_SUFFIXES)


def fs_entries(root: Path):
    """Relative paths of every file and directory, pruning build products.

    Directories are included as well as files so an empty directory created by
    the command is visible; that is the case `git status` cannot report.
    """
    entries = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in PRUNED_DIRS]
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        prefix = "" if rel_dir == "." else rel_dir + "/"
        for name in dirnames:
            entries.add(prefix + name + "/")
        for name in filenames:
            path = prefix + name
            if not is_allowed(path):
                entries.add(path)
    return entries


def git_entries(root: Path):
    """{(status, path)} from `git status --porcelain -uall`.

    `-uall` is required: with the default, an untracked directory is reported
    as one entry (`?? scratch/`) that would hide every file inside it.
    """
    proc = subprocess.run(
        ["git", "status", "--porcelain", "-uall"],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise SystemExit(f"git status failed in {root}:\n{proc.stderr}")

    entries = set()
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        code, path = line[:2], line[3:].strip()
        # A rename is reported as "R  old -> new"; the new path is the one that
        # exists in the tree afterwards.
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        entries.add((code, path.strip('"').replace("\\", "/")))
    return entries


def leaks(before_fs, after_fs, before_git, after_git):
    """Entries the command introduced or modified, excluding build artefacts."""
    created = sorted(path for path in after_fs - before_fs if not is_allowed(path))
    # Tracked modifications do not change the path set, so they come from git.
    changed = sorted(
        (code, path)
        for code, path in after_git - before_git
        if not code.startswith("??") and not is_allowed(path)
    )
    return created, changed


def snapshot_gate(root: Path, command):
    """Run `command`; return (created, changed, command_returncode)."""
    before_fs, before_git = fs_entries(root), git_entries(root)
    proc = subprocess.run(command, cwd=str(root))
    after_fs, after_git = fs_entries(root), git_entries(root)
    created, changed = leaks(before_fs, after_fs, before_git, after_git)
    return created, changed, proc.returncode


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail when a command leaves the working tree dirty.",
    )
    parser.add_argument(
        "--root",
        default=str(ROOT),
        help="git repository to watch (default: this repository)",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="command to run, after a `--` separator",
    )
    args = parser.parse_args(argv)

    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("no command given; use `-- <command> [args...]`")

    created, changed, returncode = snapshot_gate(Path(args.root).resolve(), command)

    if created or changed:
        print("CLEAN-TREE GATE FAILED: the command changed the working tree.")
        print("Every path below appeared or was modified during the run and is")
        print("not an allowed build artefact. A clean checkout would not have")
        print("it, so anything that needs it depends on ambient local state.")
        for path in created:
            print(f"  created  {path}")
        for code, path in changed:
            print(f"  {code}  {path}")
        return 1

    if returncode != 0:
        print(f"CLEAN-TREE GATE: command failed with code {returncode}.")
        return returncode

    print("CLEAN-TREE GATE: no leaked paths, working tree unchanged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
