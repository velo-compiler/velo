"""
POSIX and macOS foundation portability symbol audit test suite (Phase 70 / Task 70.7).

Asserts that probe programs importing any of the six foundation standard library
modules (std.fs, std.net, std.os, std.crypto, std.time, std.async) emit C code
that contains zero unresolved Win32 symbols matching the 22-symbol audit regex
when building for non-Windows platforms (Linux, macOS Darwin).

On Windows build hosts without target override, the assertion is inverted:
Win32 externs (such as VirtualAlloc, WSAStartup, etc.) are expected to appear
and must be strictly guarded with `#if defined(_WIN32)`.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import require_velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()

# 22-symbol Win32 audit pattern as specified by Phase 70 (gaps.md:650)
WIN32_PORTABILITY_REGEX = re.compile(
    r'\b('
    r'GetFileAttributesExA|GetFileAttributesA|CreateDirectoryA|RemoveDirectoryA|'
    r'DeleteFileA|MoveFileExA|CopyFileA|FindFirstFileA|FindNextFileA|FindClose|'
    r'CreateProcessA|GetEnvironmentVariableA|SetEnvironmentVariableA|ExitProcess|'
    r'GetCurrentProcessId|VirtualAlloc|VirtualFree|SystemFunction036|'
    r'WSAStartup|WSACleanup|closesocket|ioctlsocket'
    r')\b'
)

# Representative probe programs touching each foundation module's acts and types
MODULE_PROBES = {
    "std.fs": (
        'use std.fs\n\n'
        'act main() -> i32 {\n'
        '    let exists = fs_exists("README.md")\n'
        '    if exists { return 0 }\n'
        '    return 1\n'
        '}\n'
    ),
    "std.net": (
        'use std.net\n\n'
        'act main() -> i32 {\n'
        '    let sock = socket_create(2 as i32, 1 as i32, 0 as i32)\n'
        '    socket_close(@sock)\n'
        '    return 0\n'
        '}\n'
    ),
    "std.os": (
        'use std.os\n\n'
        'act main() -> i32 {\n'
        '    let pid = os_get_pid()\n'
        '    let has = os_has_env("PATH")\n'
        '    if has and pid > (0 as u32) { return 0 }\n'
        '    return 1\n'
        '}\n'
    ),
    "std.crypto": (
        'use std.crypto\n\n'
        'act main() -> i32 {\n'
        '    mut buf: [16]u8\n'
        '    let ok = crypto_random_bytes(buf as @u8, 16)\n'
        '    if ok { return 0 }\n'
        '    return 1\n'
        '}\n'
    ),
    "std.time": (
        'use std.time\n\n'
        'act main() -> i32 {\n'
        '    let t = time_monotonic_ms()\n'
        '    time_sleep_ms(1 as u32)\n'
        '    if t > (0 as u64) { return 0 }\n'
        '    return 1\n'
        '}\n'
    ),
    "std.async": (
        'use std.async\n\n'
        'act main() -> i32 {\n'
        '    mut p = poller_init(16)\n'
        '    poller_free(@p)\n'
        '    return 0\n'
        '}\n'
    ),
}


def _emit_probe(tmp_path: Path, mod_name: str, target: str | None = None) -> tuple[subprocess.CompletedProcess, str]:
    velo = require_velo_exe()
    src = tmp_path / f"probe_{mod_name.replace('.', '_')}.vl"
    src.write_text(MODULE_PROBES[mod_name], encoding="utf-8")
    out = tmp_path / f"probe_{mod_name.replace('.', '_')}_{target or 'host'}.c"

    env = os.environ.copy()
    if target is not None:
        env["VELO_TARGET_PLATFORM"] = target

    res = subprocess.run(
        [str(velo), "emit-c", str(src), "-o", str(out)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=30,
    )
    c_text = out.read_text(encoding="utf-8") if out.exists() else ""
    return res, c_text


@pytest.mark.parametrize("mod_name", sorted(MODULE_PROBES.keys()))
def test_posix_host_portability(tmp_path, mod_name):
    """
    On a non-Windows host (Linux, macOS), emitting C for any foundation module probe
    must succeed (RC=0) and contain zero symbols matching the 22 Win32 symbols.
    Skipped on Windows; see test_windows_host_inversion and test_cross_target_posix_portability.
    """
    if sys.platform == "win32":
        pytest.skip("Native non-Windows assertion; inverted on Windows host (see test_windows_host_inversion)")

    res, c_text = _emit_probe(tmp_path, mod_name)
    assert res.returncode == 0, f"emit-c failed for {mod_name} on host {sys.platform}:\n{res.stdout}\n{res.stderr}"
    matches = WIN32_PORTABILITY_REGEX.findall(c_text)
    assert len(matches) == 0, f"Disallowed Win32 symbols found in {mod_name} on {sys.platform}: {set(matches)}"


@pytest.mark.parametrize("mod_name", sorted(MODULE_PROBES.keys()))
def test_windows_host_inversion(tmp_path, mod_name):
    """
    On a Windows build host, the assertion is inverted:
    Native Windows emission contains expected Win32 symbols (e.g. VirtualAlloc),
    and all Win32 extern declarations must be guarded with #if defined(_WIN32).
    """
    if sys.platform != "win32":
        pytest.skip("Windows host inversion test; runs only on Windows host")

    res, c_text = _emit_probe(tmp_path, mod_name, target=None)
    assert res.returncode == 0, f"emit-c failed for {mod_name} on Windows:\n{res.stdout}\n{res.stderr}"

    # Verify that any emitted Win32 symbol is declared within #if defined(_WIN32)
    lines = c_text.splitlines()
    extern_pat = re.compile(r'extern\s+[^\n;]*\b(' + WIN32_PORTABILITY_REGEX.pattern[3:-3] + r')\b')
    for i, line in enumerate(lines):
        if extern_pat.search(line):
            assert lines[i - 1] == "#if defined(_WIN32)", f"Unguarded Win32 extern in {mod_name} at L{i+1}: {line}"
            assert lines[i + 1] == "#endif", f"Missing #endif in {mod_name} at L{i+1}: {line}"


@pytest.mark.parametrize("target", ["linux", "macos"])
@pytest.mark.parametrize("mod_name", sorted(MODULE_PROBES.keys()))
def test_cross_target_posix_portability(tmp_path, mod_name, target):
    """
    Cross-target compilation audit (verified on both Windows and non-Windows hosts):
    When VELO_TARGET_PLATFORM is linux or macos, emitting C for each of the 6
    foundation modules must succeed with RC=0 and emit ZERO Win32 symbols.
    """
    res, c_text = _emit_probe(tmp_path, mod_name, target=target)
    assert res.returncode == 0, (
        f"emit-c failed for {mod_name} targeting {target}:\nstdout:\n{res.stdout}\nstderr:\n{res.stderr}"
    )
    matches = WIN32_PORTABILITY_REGEX.findall(c_text)
    assert len(matches) == 0, (
        f"Disallowed Win32 symbols found in {mod_name} for target={target}: {set(matches)}"
    )
