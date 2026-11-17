"""
Platform variant resolution (Phase 70 / Task 70.1).

The compiler used to answer "which platform am I?" by calling
`os_is_windows()`, which lives in `std/os/env_windows.vl` -- a Win32-only
module. A compiler built on Linux therefore still believed it was on Windows,
resolved every facade to its `_windows` variant, and emitted C full of kernel32
externs that could not link. The convention also knew only two platforms, so
macOS was silently mapped onto `_linux`.

Task 70.1 replaces that with one table in `src/backend/platform_resolve.vl`,
shared by the skip decision and the resolution so the two cannot disagree, and
with host identity read from the runtime header instead of from a
platform-specific std module.

These tests are built on fixtures rather than on the real `std/`, because
resolving `std/` also depends on the facades (Task 70.5) and on moving the
Win32 externs out of the platform-neutral files (Task 70.2). What 70.1 owns is
the table, and the table is what is asserted here.
"""

import os
import subprocess
from pathlib import Path

import pytest

from conftest import cc_dir, require_velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()

MAIN = """
use "bar.vl"

act main() -> i32 {
    let name = bar_name()
    if name == null { return 1 }
    return 0
}
"""

NEUTRAL = """
act bar_name() -> string {
    return "variant-neutral"
}
"""

WINDOWS = """
act bar_name() -> string {
    return "variant-windows"
}
"""

LINUX = """
act bar_name() -> string {
    return "variant-linux"
}
"""


def _env(target=None):
    env = os.environ.copy()
    directory = cc_dir()
    if directory and directory not in env.get("PATH", ""):
        env["PATH"] = directory + os.pathsep + env.get("PATH", "")
    env.pop("VELO_TARGET_PLATFORM", None)
    if target is not None:
        env["VELO_TARGET_PLATFORM"] = target
    return env


def _emit(tmp_path, files, target=None):
    """Write `files` (name -> text) into tmp_path and emit C for main.vl."""
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    out_c = tmp_path / "out.c"
    res = subprocess.run(
        [str(require_velo_exe()), "emit-c", "main.vl", "-o", str(out_c)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_env(target),
    )
    return res, (out_c.read_text(encoding="utf-8") if out_c.exists() else "")


def test_windows_target_selects_the_windows_variant(tmp_path):
    files = {"main.vl": MAIN, "bar_windows.vl": WINDOWS, "bar_linux.vl": LINUX}
    res, emitted = _emit(tmp_path, files, target="windows")
    assert res.returncode == 0, res.stdout + res.stderr
    assert "variant-windows" in emitted
    assert "variant-linux" not in emitted, (
        "the linux variant must be skipped when the target is windows"
    )


def test_linux_target_selects_the_linux_variant(tmp_path):
    """
    The assertion the old code could not satisfy.

    Before 70.1 the platform came from `os_is_windows()`, which on a
    Windows-built compiler always says Windows, so this test could not pass on
    the maintainer host and the linux variant was unverifiable dead code.
    """
    files = {"main.vl": MAIN, "bar_windows.vl": WINDOWS, "bar_linux.vl": LINUX}
    res, emitted = _emit(tmp_path, files, target="linux")
    assert res.returncode == 0, res.stdout + res.stderr
    assert "variant-linux" in emitted
    assert "variant-windows" not in emitted, (
        "the windows variant must be skipped when the target is linux"
    )


def test_neutral_file_is_used_when_no_variant_exists(tmp_path):
    """
    A module with no platform variant is not platform-specific at all.

    Windows and linux each have a variant on disk for the std modules this probe
    reaches, so both targets must still fall through to the neutral `bar.vl`.
    macOS is excluded here on purpose: it has no `_macos` variants yet, which is
    Task 70.3, and `test_macos_target_reports_missing_variants` pins that state
    instead of pretending otherwise.
    """
    files = {"main.vl": MAIN, "bar.vl": NEUTRAL}
    for target in (None, "windows", "linux"):
        case = tmp_path / (target or "host")
        case.mkdir()
        res, emitted = _emit(case, files, target=target)
        assert res.returncode == 0, f"target={target}: " + res.stdout + res.stderr
        assert "variant-neutral" in emitted, f"target={target}"


def test_a_foreign_variant_does_not_replace_an_existing_neutral_module(tmp_path):
    """
    A present neutral module wins over another platform's variant.

    This is what `std/os/pipe.vl` depends on: it exists, it declares the capture
    API, and it imports `pipe_win32.vl` itself. Resolving it to that backend
    because the target happens to be windows removed the facade's declarations.
    """
    files = {"main.vl": MAIN, "bar.vl": NEUTRAL, "bar_linux.vl": LINUX}
    res, emitted = _emit(tmp_path, files, target="windows")
    assert res.returncode == 0, res.stdout + res.stderr
    assert "variant-neutral" in emitted
    assert "variant-linux" not in emitted


def test_host_target_defaults_to_the_host_platform(tmp_path):
    """
    With no override, resolution follows the host the compiler was built for.

    `velo_host_platform()` reads the runtime header's `_WIN32` branch, so the
    answer describes the machine the compiler runs on rather than a std module
    that may not exist there. The compile runs with the repository as its
    working directory so `-I "runtime"` picks up the in-tree header rather than
    any `~/.velo/include` install left behind by an earlier release.
    """
    probe = tmp_path / "host.vl"
    probe.write_text(
        'use std.io\n\nextern act velo_host_platform() -> string\n\n'
        'act main() -> i32 {\n    println_str(velo_host_platform())\n    return 0\n}\n',
        encoding="utf-8",
    )
    res = subprocess.run(
        [str(require_velo_exe()), "run", str(probe)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_env(),
    )
    assert res.returncode == 0, res.stdout + res.stderr
    reported = res.stdout.strip()
    assert reported in ("windows", "linux", "macos"), f"unexpected host: {reported!r}"


def test_macos_target_reports_missing_variants(tmp_path):
    """
    macOS is a declared target with no implementations yet, and must say so.

    Task 70.1 gave the table a macOS row; Task 70.3/70.5 supply the `_macos`
    variants and the facades that would use them. Until then a module implemented
    only for windows and linux has no macOS implementation, and the build has to
    fail with a diagnostic naming that, rather than emit C that cannot link.

    This is the record of that gap: when 70.3 lands the diagnostic disappears and
    this assertion is what will need updating.
    """
    files = {
        "main.vl": MAIN,
        "bar_windows.vl": WINDOWS,
        "bar_linux.vl": LINUX,
    }
    res, _emitted = _emit(tmp_path, files, target="macos")
    combined = res.stdout + res.stderr
    assert res.returncode != 0, (
        "a macOS build must not silently succeed while no _macos variants exist"
    )
    assert "macos" in combined, combined
    assert "bar_windows.vl" in combined or "bar_linux.vl" in combined, combined


def test_missing_variant_for_the_target_is_reported(tmp_path):
    """
    A module implemented only for another platform must say so.

    Silence here is the defect Phase 70 is about: the program compiles, emits C,
    and fails at link time with an undefined `VirtualAlloc` rather than a
    diagnostic naming the module that has no implementation for this target.
    """
    files = {"main.vl": MAIN, "bar_linux.vl": LINUX}
    res, _emitted = _emit(tmp_path, files, target="windows")
    combined = res.stdout + res.stderr
    assert res.returncode != 0, "a module with no implementation must not build"
    assert "bar_linux.vl" in combined, (
        "the diagnostic must name the variant that does exist:\n" + combined
    )
    assert "windows" in combined, (
        "the diagnostic must name the target that lacks an implementation:\n" + combined
    )


def test_a_backend_suffix_is_not_treated_as_a_variant(tmp_path):
    """
    `_win32.vl` and `_posix.vl` name backends that a facade imports by name.

    `std/os/pipe.vl` declares `os_spawn_capture` and `use`s `pipe_win32.vl` as
    its backend. If the resolver treated `_win32.vl` as a variant spelling, a
    neutral `bar.vl` would be replaced by `bar_win32.vl`, and the real facade
    would be dropped along with every function it declares. That regression
    broke `std.os` outright, so the negative case is pinned here.

    The neutral file must win even though a `_win32.vl` sibling exists.
    """
    files = {"main.vl": MAIN, "bar.vl": NEUTRAL, "bar_win32.vl": WINDOWS}
    res, emitted = _emit(tmp_path, files, target="windows")
    assert res.returncode == 0, res.stdout + res.stderr
    assert "variant-neutral" in emitted
    assert "variant-windows" not in emitted, (
        "a neutral module that exists must not be replaced by a _win32 backend"
    )
