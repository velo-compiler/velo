"""
Build a release archive for the Velo toolchain (Phase 71, Task 71.6).

This script is the single supported way to produce a distributable artifact. It
runs the release gates first and refuses to package a tree that fails them, so
an archive in `dist/` always corresponds to a verified commit.

Usage:
    python scripts/release.py              # full gates, then package
    python scripts/release.py --skip-tests # skip the (slow) pytest run
    python scripts/release.py --out DIR    # write archives somewhere else

Gates, in order:
    1. `VERSION` exists, is semver, and agrees with `src/common/version.vl`.
    2. `bootstrap.c` matches `velo emit-c src/main.vl` (file output, not stdout).
    3. `scripts/check_determinism.py` reports a fixed point.
    4. The worktree has no uncommitted changes to tracked files.
    5. The full test suite passes (unless --skip-tests).

Artifacts are written to `dist/`:
    velo-<version>-<platform>.zip
    SHA256SUMS

The archive is deliberately complete enough to build from scratch on a machine
that has only a C compiler: the compiler binary, `bootstrap.c`, `runtime/`,
`std/`, the licenses, and the docs needed to use them.
"""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = REPO_ROOT / "VERSION"
VERSION_VL = REPO_ROOT / "src" / "common" / "version.vl"
BOOTSTRAP_C = REPO_ROOT / "bootstrap.c"
MAIN_VL = REPO_ROOT / "src" / "main.vl"

IS_WINDOWS = sys.platform == "win32"
VELO_EXE = REPO_ROOT / "bin" / ("velo.exe" if IS_WINDOWS else "velo")

# Files and directories that go into every archive, as repo-relative paths.
ARCHIVE_ENTRIES = [
    "bootstrap.c",
    "VERSION",
    "LICENSE-MIT",
    "LICENSE-APACHE",
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "runtime",
    "std",
    "docs",
]


class GateFailure(Exception):
    """A release gate failed; the message is user-facing."""


def fail(message):
    raise GateFailure(message)


def read_version():
    if not VERSION_FILE.exists():
        fail("VERSION is missing from the repository root")
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not re.match(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$", version):
        fail(f"VERSION is not MAJOR.MINOR.PATCH[-PRE]: {version!r}")
    return version


def gate_version_agreement(version):
    if not VERSION_VL.exists():
        fail("src/common/version.vl is missing")
    text = VERSION_VL.read_text(encoding="utf-8")
    match = re.search(r'let\s+VELO_VERSION\s*:\s*string\s*=\s*"([^"]*)"', text)
    if not match:
        fail("src/common/version.vl does not declare VELO_VERSION: string")
    declared = match.group(1)
    if declared != version:
        fail(
            f"version drift: VERSION says {version!r} but src/common/version.vl "
            f"declares {declared!r}. Update both in the same commit."
        )
    print(f"  [ok] version {version} agrees across VERSION and src/common/version.vl")


def gate_velo_binary():
    if not VELO_EXE.exists():
        fail(f"{VELO_EXE} is missing; run scripts/bootstrap first")
    res = subprocess.run(
        [str(VELO_EXE), "version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if res.returncode != 0:
        fail(f"{VELO_EXE} version exited {res.returncode}: {res.stderr.strip()}")
    print(f"  [ok] compiler reports: {res.stdout.splitlines()[0]}")


def gate_bootstrap_snapshot(tmp_dir):
    """
    bootstrap.c must equal `emit-c src/main.vl -o <fresh>`.

    The source path is spelled *relatively*, exactly as the committed snapshot
    was generated. `#line` directives embed the path verbatim
    (`src/backend/codegen_line.vl:6-17` only normalizes `\\` to `/`), so an
    absolute path yields a byte-different `bootstrap.c` for identical source.
    """
    fresh = tmp_dir / "fresh_bootstrap.c"
    if fresh.exists():
        fresh.unlink()
    res = subprocess.run(
        [str(VELO_EXE), "emit-c", "src/main.vl", "-o", str(fresh)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(REPO_ROOT),
    )
    if res.returncode != 0:
        fail(f"emit-c failed: {res.stdout.strip()} {res.stderr.strip()}")
    if sha256_file(fresh) != sha256_file(BOOTSTRAP_C):
        fail(
            "bootstrap.c does not match the current compiler source. "
            "Regenerate it with: bin/velo emit-c src/main.vl -o bootstrap.c"
        )
    print("  [ok] bootstrap.c matches emit-c output")


def gate_determinism():
    script = REPO_ROOT / "scripts" / "check_determinism.py"
    res = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(REPO_ROOT),
    )
    if res.returncode != 0:
        fail(f"determinism check failed:\n{res.stdout}\n{res.stderr}")
    print("  [ok] bootstrap chain is deterministic")


def gate_clean_worktree():
    """Tracked files must be committed; untracked build products are fine."""
    res = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(REPO_ROOT),
    )
    if res.returncode != 0:
        fail("git status failed; is this a git repository?")
    if res.stdout.strip():
        fail(
            "uncommitted changes to tracked files:\n"
            + res.stdout
            + "\nCommit them before packaging a release."
        )
    print("  [ok] worktree is clean for tracked files")


def gate_test_suite():
    res = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-q"],
        cwd=str(REPO_ROOT),
    )
    if res.returncode != 0:
        fail("test suite failed")
    print("  [ok] test suite passed")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def platform_tag():
    if IS_WINDOWS:
        return "windows-x86_64"
    if sys.platform == "darwin":
        return "macos-" + _machine()
    return "linux-" + _machine()


def _machine():
    machine = os.uname().machine if hasattr(os, "uname") else "unknown"
    return {"AMD64": "x86_64", "arm64": "aarch64"}.get(machine, machine)


def build_archive(version, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"velo-{version}-{platform_tag()}.zip"
    archive_path = out_dir / name

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as bundle:
        # The compiler binary sits at the archive root as `velo[.exe]`.
        bundle.write(VELO_EXE, VELO_EXE.name)
        for entry in ARCHIVE_ENTRIES:
            source = REPO_ROOT / entry
            if not source.exists():
                fail(f"expected archive entry is missing: {entry}")
            if source.is_dir():
                for path in sorted(source.rglob("*")):
                    if not path.is_file():
                        continue
                    if "__pycache__" in path.parts or path.suffix == ".pyc":
                        continue
                    bundle.write(path, path.relative_to(REPO_ROOT).as_posix())
            else:
                bundle.write(source, entry)

    print(f"  [ok] wrote {archive_path} ({archive_path.stat().st_size:,} bytes)")
    print(f"       SHA-256: {sha256_file(archive_path)}")
    return archive_path


def write_checksums(out_dir, archives):
    sums_path = out_dir / "SHA256SUMS"
    lines = [f"{sha256_file(path)}  {path.name}" for path in archives]
    sums_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"  [ok] wrote {sums_path}")
    return sums_path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build a Velo release archive.")
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="skip the full pytest run (the other gates still apply)",
    )
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "dist"),
        help="output directory for the archive (default: dist/)",
    )
    args = parser.parse_args(argv)

    if not IS_WINDOWS and not VELO_EXE.exists():
        alt = REPO_ROOT / "bin" / "velo.exe"
        if alt.exists():
            print(f"note: using {alt.name} via conftest compatibility shim")

    print("=== Velo release gates ===")
    version = read_version()
    gate_version_agreement(version)
    gate_velo_binary()
    tmp_dir = REPO_ROOT / ".velo_cache"
    tmp_dir.mkdir(exist_ok=True)
    gate_bootstrap_snapshot(tmp_dir)
    gate_determinism()
    gate_clean_worktree()
    if args.skip_tests:
        print("  [--] test suite skipped by request")
    else:
        gate_test_suite()

    print("=== Packaging ===")
    out_dir = Path(args.out)
    archive = build_archive(version, out_dir)
    write_checksums(out_dir, [archive])
    print("=== Done ===")
    print(f"Artifact: {archive}")
    print("Verify a fresh machine with:")
    print(f"  cc -O2 -std=c99 -I runtime bootstrap.c -o velo -lm -lpthread")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except GateFailure as failure:
        print(f"\n[Velo Release] FAILED: {failure}", file=sys.stderr)
        sys.exit(1)
