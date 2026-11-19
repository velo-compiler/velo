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

MACOS = """
act bar_name() -> string {
    return "variant-macos"
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


def test_macos_target_selects_the_macos_variant(tmp_path):
    """
    Task 70.3: With bar_macos.vl present, target=macos selects it.
    """
    files = {
        "main.vl": MAIN,
        "bar_windows.vl": WINDOWS,
        "bar_linux.vl": LINUX,
        "bar_macos.vl": MACOS,
    }
    res, emitted = _emit(tmp_path, files, target="macos")
    assert res.returncode == 0, res.stdout + res.stderr
    assert "variant-macos" in emitted
    assert "variant-windows" not in emitted
    assert "variant-linux" not in emitted


def test_neutral_file_is_used_when_no_variant_exists(tmp_path):
    """
    A module with no platform variant is not platform-specific at all.

    All supported targets fall through to the neutral bar.vl when no variant exists.
    """
    files = {"main.vl": MAIN, "bar.vl": NEUTRAL}
    for target in (None, "windows", "linux", "macos"):
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
    When a module exists for windows/linux but lacks a _macos variant, target=macos fails.

    The fixture omits bar_macos.vl, verifying that the compiler diagnoses
    missing macOS variants rather than silently emitting C that cannot link.
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


@pytest.mark.parametrize("mod", [
    "std.time.clock",
    "std.time.sleep",
    "std.mem.page",
    "std.os.env",
    "std.os.process",
    "std.os.args",
    "std.io.handle",
    "std.async.poller",
    "std.net.types",
])
def test_macos_target_resolves_foundation_modules(tmp_path, mod):
    """Foundation std modules resolve and emit C cleanly under target=macos (Task 70.3/70.5)."""
    src = tmp_path / "probe.vl"
    src.write_text(f"use {mod}\n\nact main() -> i32 {{ return 0 }}\n", encoding="utf-8")
    out = tmp_path / "probe.c"
    res = subprocess.run(
        [str(require_velo_exe()), "emit-c", str(src), "-o", str(out)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_env("macos"),
        timeout=30,
    )
    assert res.returncode == 0, f"failed for {mod}:\n" + res.stdout + res.stderr


@pytest.mark.parametrize("target", ["windows", "linux", "macos"])
@pytest.mark.parametrize("module_case", [
    ("std.mem.page", "let p = os_page_alloc(4096)"),
    ("std.time.clock", "let t = time_monotonic_ms()"),
    ("std.time.sleep", "time_sleep_ms(1 as u32)"),
    ("std.os.env", "let fam = os_family()\n    let is_m = os_is_macos()"),
    ("std.os.process", "let p = os_spawn(\"echo\")"),
    ("std.os.args", "let raw = os_raw_cmdline()"),
    ("std.io.handle", "let h = io_stdout_handle()\n    let ok = io_is_valid_handle(h)"),
    ("std.async.poller", "let p = poller_init(16)"),
])
def test_facade_modules_resolve_and_emit_across_all_platforms(tmp_path, target, module_case):
    """
    Task 70.5: The 6 pure facades (page, clock, sleep, env, handle, poller)
    are deleted in favor of resolver-mediated variants, and process/args route
    through proc.vl and cmdline.vl.

    Calling acts from each module resolves to the target variant and emits valid C
    for windows, linux, and macos.
    """
    mod_name, act_call = module_case
    src = tmp_path / f"probe_{target}.vl"
    src.write_text(
        f"use {mod_name}\n\nact main() -> i32 {{\n    {act_call}\n    return 0\n}}\n",
        encoding="utf-8",
    )
    out = tmp_path / f"probe_{target}.c"
    res = subprocess.run(
        [str(require_velo_exe()), "emit-c", str(src), "-o", str(out)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_env(target),
        timeout=30,
    )
    assert res.returncode == 0, f"target={target} failed for {mod_name}:\n" + res.stdout + res.stderr
    emitted = out.read_text(encoding="utf-8")

    # Platform-specific assertions on emitted C
    if mod_name == "std.mem.page":
        if target == "windows":
            assert "VirtualAlloc" in emitted
            assert "mmap" not in emitted
        elif target == "linux":
            assert "mmap" in emitted
            assert "VirtualAlloc" not in emitted
            # Linux MAP_ANON is 32 (0x20)
            assert "32" in emitted
        elif target == "macos":
            assert "mmap" in emitted
            assert "VirtualAlloc" not in emitted
            # Darwin MAP_ANON is 4096 (0x1000)
            assert "4096" in emitted

    if mod_name == "std.time.clock":
        if target == "windows":
            assert "QueryPerformanceCounter" in emitted
            assert "clock_gettime" not in emitted
        elif target in ("linux", "macos"):
            assert "clock_gettime" in emitted
            assert "QueryPerformanceCounter" not in emitted


WIN32_PORTABILITY_SYMBOLS = (
    "GetFileAttributesExA", "GetFileAttributesA", "CreateDirectoryA", "RemoveDirectoryA",
    "DeleteFileA", "MoveFileExA", "CopyFileA", "FindFirstFileA", "FindNextFileA",
    "FindClose", "CreateProcessA", "GetEnvironmentVariableA", "SetEnvironmentVariableA",
    "ExitProcess", "GetCurrentProcessId", "VirtualAlloc", "VirtualFree",
    "SystemFunction036", "WSAStartup", "WSACleanup", "closesocket", "ioctlsocket"
)


def test_win32_externs_are_guarded_with_if_defined_win32(tmp_path):
    """
    Task 70.6: Any emitted Win32 extern declaration must be wrapped in
    #if defined(_WIN32) ... #endif in the emitted C translation unit.
    """
    src = tmp_path / "probe_extern.vl"
    src.write_text(
        'extern act VirtualAlloc(lpAddress: @u8, dwSize: usize, flAllocationType: u32, flProtect: u32) -> @u8\n'
        'act main() -> i32 { return 0 }\n',
        encoding="utf-8",
    )
    out = tmp_path / "probe_extern.c"
    res = subprocess.run(
        [str(require_velo_exe()), "emit-c", str(src), "-o", str(out)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert res.returncode == 0, f"emit-c failed:\n{res.stderr}"
    lines = out.read_text(encoding="utf-8").splitlines()
    found = False
    for i, line in enumerate(lines):
        if "extern uint8_t* VirtualAlloc" in line:
            found = True
            assert lines[i - 1] == "#if defined(_WIN32)", f"Expected guard before extern at line {i+1}: {line}"
            assert lines[i + 1] == "#endif", f"Expected #endif after extern at line {i+1}: {line}"
    assert found, "Expected extern declaration of VirtualAlloc"


@pytest.mark.parametrize("target", ["linux", "macos"])
def test_compiler_emission_cross_target_zero_win32_symbols(tmp_path, target):
    """
    Task 70.6: When emit-c compiles src/main.vl for a POSIX target (linux, macos),
    the emitted C must contain ZERO symbols from the 22-symbol Win32 set.
    """
    import re
    out = tmp_path / f"boot_{target}.c"
    res = subprocess.run(
        [str(require_velo_exe()), "emit-c", "src/main.vl", "-o", str(out)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_env(target),
        timeout=60,
    )
    assert res.returncode == 0, f"emit-c src/main.vl for {target} failed:\n{res.stderr}"
    c_text = out.read_text(encoding="utf-8")
    win32_pat = re.compile(
        r'extern\s+[^\n;]*\b(' + '|'.join(WIN32_PORTABILITY_SYMBOLS) + r')\b'
    )
    matches = win32_pat.findall(c_text)
    assert len(matches) == 0, f"Unexpected Win32 externs for target={target}: {matches}"


def test_bootstrap_c_has_guarded_win32_externs_and_no_unwanted_win32_symbols():
    """
    Task 70.6: In bootstrap.c, Win32 process and environment externs must not be present,
    and all Win32 extern declarations must be wrapped in #if defined(_WIN32).
    """
    import re
    boot_path = REPO_ROOT / "bootstrap.c"
    assert boot_path.exists()
    lines = boot_path.read_text(encoding="utf-8").splitlines()
    win32_extern_pat = re.compile(
        r'extern\s+[^\n;]*\b(' + '|'.join(WIN32_PORTABILITY_SYMBOLS) + r')\b'
    )
    # 1. Any Win32 extern declaration must be guarded by #if defined(_WIN32)
    for i, line in enumerate(lines):
        if win32_extern_pat.search(line):
            assert lines[i - 1] == "#if defined(_WIN32)", f"Unguarded Win32 extern at L{i+1}: {line}"
            assert lines[i + 1] == "#endif", f"Missing #endif at L{i+1}: {line}"

    # 2. Verify unwanted Win32 process/env APIs are completely eliminated from bootstrap.c
    text = "\n".join(lines)
    for sym in ("CreateProcessA", "DeleteFileA", "GetEnvironmentVariableA", "SetEnvironmentVariableA", "ExitProcess", "GetCurrentProcessId"):
        assert not re.search(r'extern\s+[^\n;]*\b' + sym + r'\b', text), f"Unwanted extern {sym} found in bootstrap.c"


