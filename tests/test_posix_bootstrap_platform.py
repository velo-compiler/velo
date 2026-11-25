"""
POSIX and macOS bootstrap.c object file platform portability test suite (Phase 70 / Task 70.8).

Asserts that compiling bootstrap.c with 'cc -c' produces an object file with zero
undefined symbols from the 22-symbol Win32 portability set on non-Windows hosts
(Linux, macOS Darwin), and verifies that bootstrap.c compiles cleanly to a functional
compiler binary without kernel32 / advapi32 / ws2_32 dependencies.

On Windows build hosts:
Verifies that all 20 unwanted Win32 process/filesystem/crypto/networking symbols
are completely absent from 'nm -u' of bootstrap.o, and that VirtualAlloc / VirtualFree
extern declarations are strictly guarded by '#if defined(_WIN32)' with POSIX
static inline fallback implementations in velo_runtime.h.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import cc_dir, require_velo_exe
from release_meta import expected_banner_line

REPO_ROOT = Path(__file__).parent.parent.resolve()
BOOTSTRAP_C = REPO_ROOT / "bootstrap.c"

WIN32_PORTABILITY_SYMBOLS = {
    "GetFileAttributesExA", "GetFileAttributesA", "CreateDirectoryA", "RemoveDirectoryA",
    "DeleteFileA", "MoveFileExA", "CopyFileA", "FindFirstFileA", "FindNextFileA",
    "FindClose", "CreateProcessA", "GetEnvironmentVariableA", "SetEnvironmentVariableA",
    "ExitProcess", "GetCurrentProcessId", "VirtualAlloc", "VirtualFree",
    "GetStdHandle", "WriteFile", "ReadFile", "SetFilePointerEx",
    "GetFileSizeEx", "CloseHandle", "CreateFileA",
    "SystemFunction036", "WSAStartup", "WSACleanup", "closesocket", "ioctlsocket"
}


def _get_cc_env() -> dict:
    env = os.environ.copy()
    if sys.platform == "win32":
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return env


def _find_compiler() -> str:
    for candidate in ("cc", "gcc", "clang"):
        if shutil.which(candidate, path=_get_cc_env().get("PATH")):
            return candidate
    return "gcc" if sys.platform == "win32" else "cc"


def _get_nm_undefined_symbols(obj_path: Path) -> set[str]:
    """Runs 'nm -u' on an object file and returns the set of undefined symbol names."""
    nm_bin = shutil.which("nm", path=_get_cc_env().get("PATH"))
    if not nm_bin:
        pytest.skip("'nm' utility not found in PATH")

    res = subprocess.run(
        [nm_bin, "-u", str(obj_path)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_get_cc_env(),
        timeout=30,
    )
    assert res.returncode == 0, f"nm -u failed on {obj_path}:\n{res.stderr}"

    undefined = set()
    for line in res.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        symbol = parts[-1]
        # MinGW / PE leading underscore stripping
        if sys.platform == "win32" and symbol.startswith("_") and not symbol.startswith("__"):
            symbol = symbol[1:]
        undefined.add(symbol)
    return undefined


def test_posix_host_bootstrap_c_object_cleanliness(tmp_path):
    """
    Task 70.8: On non-Windows hosts (Linux, macOS), compile bootstrap.c with 'cc -c'
    and assert that nm -u contains NO undefined symbol from the 22-symbol Win32 set.
    """
    if sys.platform == "win32":
        pytest.skip("Runs natively on non-Windows hosts (Linux, macOS Darwin); see test_windows_host_bootstrap_c_object_cleanliness")

    cc = _find_compiler()
    obj_out = tmp_path / "bootstrap.o"
    compile_cmd = [
        cc, "-c", "-O2", "-std=c99",
        "-I", str(REPO_ROOT / "runtime"),
        "-I", str(REPO_ROOT / "velo" / "runtime"),
        str(BOOTSTRAP_C),
        "-o", str(obj_out),
    ]
    res = subprocess.run(
        compile_cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_get_cc_env(),
        timeout=60,
    )
    assert res.returncode == 0, f"Compilation of bootstrap.c with '{cc} -c' failed:\n{res.stderr}"
    assert obj_out.exists(), f"Object file {obj_out} was not produced"

    undefined_syms = _get_nm_undefined_symbols(obj_out)
    bad_symbols = undefined_syms & WIN32_PORTABILITY_SYMBOLS
    assert len(bad_symbols) == 0, (
        f"Undefined Win32 symbols found in {obj_out} on host {sys.platform}:\n{sorted(bad_symbols)}"
    )


def test_windows_host_bootstrap_c_object_cleanliness(tmp_path):
    """
    On a Windows build host, compile bootstrap.c with 'gcc -c' and assert that:
    1. All 20 unwanted Win32 process/filesystem/crypto/networking APIs are 100% absent from nm -u.
    2. VirtualAlloc and VirtualFree externs are strictly guarded with #if defined(_WIN32).
    3. velo_runtime.h provides POSIX static inline fallbacks for off-Windows compilation.
    """
    if sys.platform != "win32":
        pytest.skip("Windows-specific audit; runs only on Windows host")

    obj_out = tmp_path / "bootstrap.o"
    compile_cmd = [
        "gcc", "-c", "-O2", "-std=c99",
        "-I", str(REPO_ROOT / "runtime"),
        "-I", str(REPO_ROOT / "velo" / "runtime"),
        str(BOOTSTRAP_C),
        "-o", str(obj_out),
    ]
    res = subprocess.run(
        compile_cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_get_cc_env(),
        timeout=60,
    )
    assert res.returncode == 0, f"Compilation of bootstrap.c with 'gcc -c' failed:\n{res.stderr}"
    assert obj_out.exists(), f"Object file {obj_out} was not produced"

    undefined_syms = _get_nm_undefined_symbols(obj_out)
    # On Windows, VirtualAlloc/VirtualFree and std/io Win32 handle APIs are native (guarded with POSIX fallbacks in velo_runtime.h)
    unwanted_win32 = WIN32_PORTABILITY_SYMBOLS - {
        "VirtualAlloc", "VirtualFree",
        "GetStdHandle", "WriteFile", "ReadFile", "SetFilePointerEx",
        "GetFileSizeEx", "CloseHandle", "CreateFileA",
    }
    found_unwanted = undefined_syms & unwanted_win32
    assert len(found_unwanted) == 0, (
        f"Unexpected Win32 symbols found in bootstrap.o on Windows:\n{sorted(found_unwanted)}"
    )

    # Verify that VirtualAlloc and VirtualFree declarations in bootstrap.c are guarded by #if defined(_WIN32)
    lines = BOOTSTRAP_C.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if "extern uint8_t* VirtualAlloc(" in line or "extern int32_t VirtualFree(" in line:
            assert lines[i - 1] == "#if defined(_WIN32)", f"Unguarded extern at L{i+1}: {line}"
            assert lines[i + 1] == "#endif", f"Missing #endif at L{i+1}: {line}"

    # Verify that velo_runtime.h includes the static inline fallbacks for non-Windows hosts
    header_text = (REPO_ROOT / "runtime" / "velo_runtime.h").read_text(encoding="utf-8")
    assert "static inline uint8_t* VirtualAlloc" in header_text, "Missing non-Windows VirtualAlloc fallback"
    assert "static inline int32_t VirtualFree" in header_text, "Missing non-Windows VirtualFree fallback"
    for sym in ("GetStdHandle", "WriteFile", "ReadFile", "SetFilePointerEx", "GetFileSizeEx", "CloseHandle", "CreateFileA"):
        assert f"{sym}(" in header_text, f"Missing non-Windows {sym} fallback"
    assert "#include <sys/mman.h>" in header_text, "Missing sys/mman.h include in velo_runtime.h"


def test_posix_bootstrap_c_linkage_and_execution(tmp_path):
    """
    On non-Windows hosts (Linux, macOS), verify that bootstrap.c compiles and links
    directly into a functional binary using 'cc -O2 -std=c99 bootstrap.c -o velo -lm -lpthread'
    and executes 'version' with RC=0.
    """
    if sys.platform == "win32":
        pytest.skip("Runs natively on non-Windows hosts (Linux, macOS Darwin); Windows linking is covered in test_bootstrap_snapshot.py")

    cc = _find_compiler()
    bin_out = tmp_path / "velo_boot"
    link_cmd = [
        cc, "-O2", "-std=c99",
        "-I", str(REPO_ROOT / "runtime"),
        "-I", str(REPO_ROOT / "velo" / "runtime"),
        str(BOOTSTRAP_C),
        "-o", str(bin_out),
        "-lm", "-lpthread",
    ]
    res = subprocess.run(
        link_cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_get_cc_env(),
        timeout=60,
    )
    assert res.returncode == 0, f"Linking bootstrap.c on {sys.platform} failed:\n{res.stderr}"
    assert bin_out.exists(), f"Binary {bin_out} was not produced"

    res_ver = subprocess.run(
        [str(bin_out), "version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_get_cc_env(),
        timeout=15,
    )
    assert res_ver.returncode == 0
    assert expected_banner_line() in res_ver.stdout
