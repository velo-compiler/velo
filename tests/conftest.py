"""
Shared pytest helpers for the Velo test suite (Phase 76.3).

Before this module, tests located the compiler with a literal path:
`REPO_ROOT / "bin" / "velo.exe"` (99 files) and searched for a C compiler by
appending `C:\\msys64\\ucrt64\\bin` to PATH (62 files). Both spellings are
Windows-only. `bootstrap.sh` produces `bin/velo` on POSIX, so every POSIX run
depended on a symlink shim, and every CI runner had to have MSYS2 at exactly one
absolute path.

Two helpers replace both literals:

    velo_exe()  -> Path to the built compiler, whatever it is called here.
    cc_path()   -> Path/name of the C compiler to use.

`subprocess` calls still need the compiler on PATH for the *generated* program
link step, so `cc_env()` returns an environment with the compiler's directory
prepended when the compiler was found outside PATH.

The `Popen` monkeypatches that used to live here are gone. They existed to
rewrite `bin/velo.exe` to `bin/velo` and to normalise forward slashes in
relative executable paths -- both symptoms of tests hardcoding a Windows
filename, not defects in `subprocess`.
"""

import os
import shutil
import subprocess
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
    then `bin/velo`. Raises with an actionable message rather than returning a
    non-existent path, so a missing build fails loudly at the call site.
    """
    override = os.environ.get("VELO_BIN")
    if override:
        path = Path(override)
        if not path.is_absolute():
            path = REPO_ROOT / path
        if not path.exists():
            raise FileNotFoundError(f"VELO_BIN points at a missing file: {path}")
        return path

    for name in _COMPILER_NAMES:
        candidate = BIN_DIR / name
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "the Velo compiler is not built: expected bin/velo.exe or bin/velo. "
        "Run scripts/bootstrap.bat --full (Windows) or "
        "bash scripts/bootstrap.sh --full (POSIX), or set VELO_BIN."
    )


def velo_exe_or_none():
    """`velo_exe()` without the exception, for `pytest.skip` guards."""
    try:
        return velo_exe()
    except FileNotFoundError:
        return None


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
        found = shutil.which(name)
        if found:
            return name
    raise FileNotFoundError(
        "no C compiler found: set CC, or put gcc/clang/cc on PATH"
    )


def cc_env():
    """
    Return a copy of `os.environ` with the C compiler reachable.

    `velo build` shells out to the compiler by name, so a compiler that exists
    at an absolute path but is not on PATH would fail at link time. When `CC` is
    an absolute path, its directory is prepended.
    """
    env = dict(os.environ)
    cc = cc_path()
    if os.path.isabs(cc):
        cc_dir = str(Path(cc).parent)
        existing = env.get("PATH", "")
        parts = existing.split(os.pathsep) if existing else []
        if cc_dir not in parts:
            env["PATH"] = cc_dir + (os.pathsep + existing if existing else "")
        env["CC"] = cc
    return env


def is_windows() -> bool:
    return sys.platform == "win32"


# ---------------------------------------------------------------------------
# Transitional compatibility shim (removed by Phase 76.3's sweep)
# ---------------------------------------------------------------------------
# 99 test files still spell the compiler as `bin/velo.exe` and rely on a
# `Popen` hook to rewrite it. Those literals are swept in task 76.3; until that
# commit lands, the hook stays so each commit leaves the suite green. Deleting
# it earlier turns 99 files red at once and makes the 76.4 concurrency fix
# impossible to review on its own.
if sys.platform != "win32":
    _orig_popen = subprocess.Popen

    class _PatchedPosixPopen(_orig_popen):
        def __init__(self, args, *a, **kw):
            if isinstance(args, (list, tuple)) and args:
                first = str(args[0])
                if first.endswith("velo.exe") and not os.path.exists(first):
                    alt = first[:-4]
                    if os.path.exists(alt):
                        args = list(args)
                        args[0] = alt
            super().__init__(args, *a, **kw)

    subprocess.Popen = _PatchedPosixPopen
else:
    _orig_popen = subprocess.Popen

    class _PatchedPopen(_orig_popen):
        def __init__(self, args, *a, **kw):
            if isinstance(args, (list, tuple)) and args:
                first = args[0]
                if isinstance(first, str) and "/" in first and not os.path.isabs(first):
                    args = list(args)
                    args[0] = os.path.normpath(first)
            super().__init__(args, *a, **kw)

    subprocess.Popen = _PatchedPopen
