"""
Tests for POSIX process spawning (Phase 75 / Task 75.1).

Verifies that `std.os.proc_linux` and `std.os.proc_macos` implement real POSIX
process spawning via `fork()`, `dup2()`, `velo_posix_execvp()`, and `waitpid()`
replacing the former dead stub handle.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import cc_dir, require_velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()


def _env(target=None):
    env = os.environ.copy()
    directory = cc_dir()
    if directory and directory not in env.get("PATH", ""):
        env["PATH"] = directory + os.pathsep + env.get("PATH", "")
    env.pop("VELO_TARGET_PLATFORM", None)
    if target is not None:
        env["VELO_TARGET_PLATFORM"] = target
    return env


def test_proc_linux_and_macos_contain_no_stub_comments():
    """Verify that proc_linux.vl and proc_macos.vl no longer have the fork stub comment."""
    linux_src = (REPO_ROOT / "std" / "os" / "proc_linux.vl").read_text(encoding="utf-8")
    macos_src = (REPO_ROOT / "std" / "os" / "proc_macos.vl").read_text(encoding="utf-8")
    assert "POSIX fork stub" not in linux_src, "proc_linux.vl still contains POSIX fork stub comment"
    assert "POSIX fork stub" not in macos_src, "proc_macos.vl still contains POSIX fork stub comment"
    assert "fork()" in linux_src
    assert "fork()" in macos_src
    assert "dup2" in linux_src
    assert "dup2" in macos_src
    assert "velo_posix_execvp" in linux_src
    assert "velo_posix_execvp" in macos_src


@pytest.mark.parametrize("target", ["linux", "macos"])
def test_cross_target_emission_contains_posix_spawn_primitives(tmp_path, target):
    """
    When emitting C for linux or macos, std.os.process emits real POSIX
    fork/dup2/execvp/waitpid calls with zero Win32 symbols.
    """
    src = tmp_path / f"spawn_probe_{target}.vl"
    src.write_text(
        'use std.os.process\n\n'
        'act main() -> i32 {\n'
        '    mut proc = os_spawn("echo hi")\n'
        '    if !proc.is_alive { return 1 }\n'
        '    let code = os_process_wait(@proc)\n'
        '    let sync_res = os_spawn_sync("echo test")\n'
        '    let sys_code = os_system("echo test")\n'
        '    return 0\n'
        '}\n',
        encoding="utf-8",
    )
    out_c = tmp_path / f"spawn_probe_{target}.c"
    res = subprocess.run(
        [str(require_velo_exe()), "emit-c", str(src), "-o", str(out_c)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_env(target),
        timeout=30,
    )
    assert res.returncode == 0, f"emit-c failed for {target}:\nstdout:\n{res.stdout}\nstderr:\n{res.stderr}"
    c_text = out_c.read_text(encoding="utf-8")

    # Assert POSIX primitives are present
    assert "fork(" in c_text, f"Missing fork in emitted C for {target}"
    assert "dup2(" in c_text, f"Missing dup2 in emitted C for {target}"
    assert "velo_posix_execvp(" in c_text, f"Missing velo_posix_execvp in emitted C for {target}"
    assert "waitpid(" in c_text, f"Missing waitpid in emitted C for {target}"
    assert "_exit(" in c_text, f"Missing _exit in emitted C for {target}"

    # Assert NO Win32 symbols are emitted
    win32_symbols = [
        "CreateProcessA", "WaitForSingleObject", "GetExitCodeProcess",
        "TerminateProcess", "CloseHandle", "STARTUPINFOA", "PROCESS_INFORMATION"
    ]
    for sym in win32_symbols:
        assert sym not in c_text, f"Unexpected Win32 symbol {sym} emitted for target={target}"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX host execution test; runs on Linux/macOS")
def test_posix_host_spawn_sync_execution(tmp_path):
    """
    On POSIX hosts, compiles and runs a program doing os_spawn_sync('echo hi')
    verifying clean exit code 0.
    """
    src = tmp_path / "run_spawn.vl"
    src.write_text(
        'use std.os.process\n\n'
        'act main() -> i32 {\n'
        '    let res = os_spawn_sync("echo hi")\n'
        '    if res.success and res.exit_code == 0 {\n'
        '        return 0\n'
        '    }\n'
        '    return 1\n'
        '}\n',
        encoding="utf-8",
    )
    out_bin = tmp_path / "run_spawn"
    build_res = subprocess.run(
        [str(require_velo_exe()), "build", str(src), "-o", str(out_bin)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert build_res.returncode == 0, f"build failed:\n{build_res.stdout}\n{build_res.stderr}"

    run_res = subprocess.run([str(out_bin)], capture_output=True, text=True, timeout=10)
    assert run_res.returncode == 0, f"run failed with code {run_res.returncode}"
