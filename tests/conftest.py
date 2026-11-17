"""
Shared pytest helpers for the Velo test suite (Phase 76.3).

Before this module, tests located the compiler with a literal path:
`REPO_ROOT / "bin" / "velo.exe"` (99 files) and searched for a C compiler by
appending `C:\\msys64\\ucrt64\\bin` to PATH (62 files). Both spellings are
Windows-only. `bootstrap.sh` produces `bin/velo` on POSIX, so every POSIX run
depended on a symlink shim, and every CI runner had to have MSYS2 at exactly one
absolute path.

The helpers that replace both literals:

    velo_exe()   -> Path to the built compiler, whatever it is called here.
    cc_path()    -> Path/name of the C compiler to use.
    cc_dir()     -> Directory holding that compiler (for PATH surgery).
    cc_env()     -> `os.environ` with the compiler reachable by name.
    is_windows() -> Platform predicate, so tests stop spelling `sys.platform`.

`velo_exe()` deliberately does not raise when nothing is built: tests
overwhelmingly guard with `if not velo_exe().exists(): pytest.skip(...)`, and a
raising helper would turn every one of those skips into a collection error. Use
`require_velo_exe()` where a missing build must fail loudly.

The `Popen` monkeypatches that used to live here are gone. They rewrote
`bin/velo.exe` to `bin/velo` and normalised forward slashes in relative
executable paths -- both symptoms of tests hardcoding a Windows filename, not
defects in `subprocess`.
"""

import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN_DIR = REPO_ROOT / "bin"

_COMPILER_NAMES = ("velo.exe", "velo")


def velo_exe() -> Path:
    """
    Return the path to the built Velo compiler.

    Resolution order: `VELO_BIN` (an explicit override, used by CI jobs that
    build under a different name such as `velo_msvc.exe`), then `bin/velo.exe`,
    then `bin/velo`. Falls back to the Windows name when nothing is built, so
    `velo_exe().exists()` is the natural skip guard.
    """
    override = os.environ.get("VELO_BIN")
    if override:
        path = Path(override)
        return path if path.is_absolute() else REPO_ROOT / path

    for name in _COMPILER_NAMES:
        candidate = BIN_DIR / name
        if candidate.exists():
            return candidate

    return BIN_DIR / _COMPILER_NAMES[0]


def require_velo_exe() -> Path:
    """`velo_exe()`, but fail loudly when the compiler has not been built."""
    path = velo_exe()
    if not path.exists():
        raise FileNotFoundError(
            f"the Velo compiler is not built: expected {path}. "
            "Run scripts/bootstrap.bat --full (Windows) or "
            "bash scripts/bootstrap.sh --full (POSIX), or set VELO_BIN."
        )
    return path


def velo_exe_or_none():
    """The compiler path when it exists, else None."""
    path = velo_exe()
    return path if path.exists() else None


def cc_path() -> str:
    """
    Return the C compiler to invoke.

    Honours `CC` first (the same variable the CI workflow and
    `scripts/bootstrap.sh` use), then falls back to whichever of gcc/clang/cc
    is on PATH. Returns the bare name when it is on PATH so subprocess calls do
    not depend on an absolute location.
    """
    requested = os.environ.get("CC")
    if requested:
        return requested

    for name in ("gcc", "clang", "cc"):
        if shutil.which(name):
            return name
    raise FileNotFoundError("no C compiler found: set CC, or put gcc/clang/cc on PATH")


def cc_dir() -> str:
    """
    Return the directory holding the C compiler, or "" when it is a bare name
    that cannot be located.

    Tests used to spell this as the literal `C:\\msys64\\ucrt64\\bin`, which is
    where MSYS2 puts gcc on Windows and nowhere else. Returning "" keeps the
    existing callers working: an empty PATH component is skipped by the OS, and
    `os.path.exists("")` is False.
    """
    cc = cc_path()
    if os.path.isabs(cc):
        return str(Path(cc).parent)
    found = shutil.which(cc)
    return str(Path(found).parent) if found else ""


def cc_env():
    """
    Return a copy of `os.environ` with the C compiler reachable by name.

    `velo build` shells out to the compiler by name, so a compiler that exists
    at an absolute path but is not on PATH would fail at link time. When `CC` is
    an absolute path, its directory is prepended.
    """
    env = dict(os.environ)
    cc = cc_path()
    if os.path.isabs(cc):
        directory = str(Path(cc).parent)
        existing = env.get("PATH", "")
        parts = existing.split(os.pathsep) if existing else []
        if directory not in parts:
            env["PATH"] = directory + (os.pathsep + existing if existing else "")
        env["CC"] = cc
    return env


def is_windows() -> bool:
    return sys.platform == "win32"
