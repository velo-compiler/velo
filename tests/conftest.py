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

import pytest

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


# ---------------------------------------------------------------------------
# Test tiers (Phase 76 / Task 76.6)
# ---------------------------------------------------------------------------
# The full suite takes ~16 minutes because it invokes a C compiler hundreds of
# times. A 16-minute red X on every push trains people to ignore CI, so the
# suite is split into two lanes:
#
#   fast  - pure Python: source-text assertions, YAML parsing, helper contracts,
#           JSON schema checks. No compiler invocation. Target: under 2 minutes.
#   slow  - everything that shells out to the compiler or a built binary.
#
# `slow` is added at collection time by the hook below, from a heuristic on each
# test function's source. It is *not* applied at first compiler invocation: a
# marker cannot be added mid-test, and a hook that ran there could not influence
# selection. The heuristic deliberately over-approximates -- a test wrongly
# called slow only loses the 2-minute lane, while a test wrongly called fast
# would put a compiler build in that lane and defeat its purpose.
#
# `fast` is never inferred. A module opts in explicitly with
# `pytestmark = pytest.mark.fast`, which is a promise that it invokes no
# compiler, and `-m fast` is what CI's push lane runs.

def pytest_addoption(parser):
    parser.addoption(
        "--bench",
        action="store_true",
        default=False,
        help="Run benchmark / performance microbenchmark tier (nightly CI)",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "fast: pure-Python test that never invokes a C compiler"
    )
    config.addinivalue_line(
        "markers", "slow: test that compiles or runs a built binary"
    )
    config.addinivalue_line(
        "markers", "bench: benchmark or microbenchmark test; skipped unless --bench is passed"
    )


# Presence of any of these in a test function's source means the test probably
# reaches the compiler, a built binary, or a subprocess. Kept as names rather
# than a subprocess-detection library because the point is a conservative
# signal, not an analysis.
_COMPILER_SIGNALS = (
    "velo_exe",
    "require_velo_exe",
    "cc_path",
    "cc_dir",
    "cc_env",
    "subprocess",
    "Popen",
)


def pytest_collection_modifyitems(config, items):
    """Mark tests that may invoke a compiler as `slow`, unless marked `fast`.
    Skip tests marked with `bench` or located in tests/benchmarks/ unless --bench is specified."""
    import inspect

    bench_enabled = config.getoption("--bench", False)
    skip_bench = pytest.mark.skip(reason="Benchmark tier: run with pytest --bench")

    for item in items:
        # Benchmark tier gating
        is_bench = item.get_closest_marker("bench") is not None or "benchmarks" in str(item.fspath)
        if is_bench:
            item.add_marker(pytest.mark.bench)
            if not bench_enabled:
                item.add_marker(skip_bench)
                continue

        if item.get_closest_marker("fast"):
            continue
        try:
            source = inspect.getsource(item.function)
        except (OSError, TypeError):
            source = ""
        if any(token in source for token in _COMPILER_SIGNALS):
            item.add_marker(pytest.mark.slow)
