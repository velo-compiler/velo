"""
Tests for POSIX process spawning and pipe draining (Phase 75 / Tasks 75.1 & 75.2).

Verifies that `std.os.proc_linux`, `std.os.proc_macos`, `std.os.pipe_io_linux`,
and `std.os.pipe_io_macos` implement real POSIX process execution and stream
draining via `fork()`, `dup2()`, `velo_posix_execvp()`, `velo_posix_poll()`,
and `waitpid()` replacing former dead stubs.
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
    env["VELO_STD"] = str(REPO_ROOT / "std")
    env.pop("VELO_TARGET_PLATFORM", None)
    if target is not None:
        env["VELO_TARGET_PLATFORM"] = target
    return env


def test_proc_linux_and_macos_contain_no_stub_comments():
    """Task 75.1: Verify proc_linux.vl and proc_macos.vl no longer have the fork stub comment."""
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
    assert "posix_decode_status" in linux_src
    assert "posix_decode_status" in macos_src


def test_pipe_io_linux_and_macos_contain_no_stub_comments():
    """Task 75.2: Verify pipe_io_linux.vl and pipe_io_macos.vl no longer have the drain stub comment."""
    linux_src = (REPO_ROOT / "std" / "os" / "pipe_io_linux.vl").read_text(encoding="utf-8")
    macos_src = (REPO_ROOT / "std" / "os" / "pipe_io_macos.vl").read_text(encoding="utf-8")
    assert "POSIX drain stub" not in linux_src, "pipe_io_linux.vl still contains POSIX drain stub comment"
    assert "POSIX drain stub" not in macos_src, "pipe_io_macos.vl still contains POSIX drain stub comment"
    assert "velo_posix_poll" in linux_src
    assert "velo_posix_poll" in macos_src
    assert "os_pipe_drain_streams" in linux_src
    assert "os_pipe_drain_streams" in macos_src


def test_zero_stub_comments_remain_in_std():
    """
    Task 75.5: Audit every remaining stub comment in std/ ensuring the count is zero.
    `grep -rin 'stub' std/` must return zero hits outside explicitly documented _unsupported modules.
    """
    stub_pattern = re.compile(r'\bstubs?\b', re.IGNORECASE)
    std_dir = REPO_ROOT / "std"
    violating_files = []
    for file_path in std_dir.rglob("*.vl"):
        if "_unsupported" in file_path.name:
            continue
        text = file_path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if stub_pattern.search(line):
                violating_files.append((str(file_path.relative_to(REPO_ROOT)), line_no, line.strip()))

    assert not violating_files, "Found stub comments in std/:\n" + "\n".join(
        f"  {f}:{ln}: {line}" for f, ln, line in violating_files
    )


@pytest.mark.parametrize("target", ["linux", "macos"])
def test_cross_target_emission_contains_posix_spawn_primitives(tmp_path, target):
    """
    Task 75.1: When emitting C for linux or macos, std.os.process emits real POSIX
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

    assert "fork(" in c_text, f"Missing fork in emitted C for {target}"
    assert "dup2(" in c_text, f"Missing dup2 in emitted C for {target}"
    assert "velo_posix_execvp(" in c_text, f"Missing velo_posix_execvp in emitted C for {target}"
    assert "waitpid(" in c_text, f"Missing waitpid in emitted C for {target}"
    assert "_exit(" in c_text, f"Missing _exit in emitted C for {target}"

    win32_symbols = [
        "CreateProcessA", "WaitForSingleObject", "GetExitCodeProcess",
        "TerminateProcess", "CloseHandle", "STARTUPINFOA", "PROCESS_INFORMATION"
    ]
    for sym in win32_symbols:
        assert sym not in c_text, f"Unexpected Win32 symbol {sym} emitted for target={target}"


@pytest.mark.parametrize("target", ["linux", "macos"])
def test_cross_target_emission_contains_posix_pipe_drain_primitives(tmp_path, target):
    """
    Task 75.2: When emitting C for linux or macos, std.os.pipe emits real POSIX
    pipe/read/velo_posix_poll calls with zero Win32 symbols.
    """
    src = tmp_path / f"drain_probe_{target}.vl"
    src.write_text(
        'use std.os.pipe\nuse std.mem.arena\n\n'
        'act main() -> i32 {\n'
        '    mut arena = arena_init(4096)\n'
        '    let out = os_spawn_capture(@arena, "echo test")\n'
        '    arena_free(@arena)\n'
        '    return 0\n'
        '}\n',
        encoding="utf-8",
    )
    out_c = tmp_path / f"drain_probe_{target}.c"
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

    assert "velo_posix_poll(" in c_text, f"Missing velo_posix_poll in emitted C for {target}"
    assert "read(" in c_text, f"Missing read in emitted C for {target}"
    assert "pipe(" in c_text, f"Missing pipe in emitted C for {target}"

    win32_symbols = [
        "PeekNamedPipe", "ReadFile", "CreatePipe", "STARTF_USESTDHANDLES"
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
        encoding="utf-8",
        errors="replace",
        env=_env(),
        timeout=30,
    )
    assert build_res.returncode == 0, f"build failed:\n{build_res.stdout}\n{build_res.stderr}"

    run_res = subprocess.run(
        [str(out_bin)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    assert run_res.returncode == 0, f"run failed with code {run_res.returncode}"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX host execution test; runs on Linux/macOS")
def test_posix_host_pipe_drain_two_streams_and_exit_7(tmp_path):
    """
    Task 75.2 exit criterion: A child process writing to both stdout and stderr
    and exiting with code 7 must be cleanly drained and report exit_code == 7
    with success == false.
    """
    src = tmp_path / "test_drain_7.vl"
    src.write_text(
        'use std.os.pipe\nuse std.mem.arena\n\n'
        'act main() -> i32 {\n'
        '    mut arena = arena_init(65536)\n'
        '    let out = os_spawn_capture(@arena, "echo out_msg; echo err_msg >&2; exit 7")\n'
        '    if out.exit_code != 7 { return 1 }\n'
        '    if out.success { return 2 }\n'
        '    arena_free(@arena)\n'
        '    return 0\n'
        '}\n',
        encoding="utf-8",
    )
    out_bin = tmp_path / "test_drain_7"
    build_res = subprocess.run(
        [str(require_velo_exe()), "build", str(src), "-o", str(out_bin)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_env(),
        timeout=30,
    )
    assert build_res.returncode == 0, f"build failed:\n{build_res.stdout}\n{build_res.stderr}"

    run_res = subprocess.run(
        [str(out_bin)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    assert run_res.returncode == 0, f"run failed with code {run_res.returncode}"


@pytest.mark.parametrize("target", ["linux", "macos", "windows"])
def test_cross_target_emission_os_process_signal(tmp_path, target):
    """
    Task 75.3: Verify cross-target emission of os_process_signal for linux, macos, and windows.
    POSIX targets must include status decoding with signal isolation, and Windows must
    consistently return 0.
    """
    src = tmp_path / f"sig_probe_{target}.vl"
    src.write_text(
        'use std.os.process\n\n'
        'act main() -> i32 {\n'
        '    mut proc = os_spawn("echo test")\n'
        '    let sig = os_process_signal(@proc)\n'
        '    let sig_null = os_process_signal(null)\n'
        '    let code = os_process_wait(@proc)\n'
        '    return 0\n'
        '}\n',
        encoding="utf-8",
    )
    out_c = tmp_path / f"sig_probe_{target}.c"
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

    assert "os_process_signal" in c_text, f"Missing os_process_signal in emitted C for {target}"
    if target in ("linux", "macos"):
        assert "waitpid(" in c_text, f"Missing waitpid in emitted C for {target}"
        assert "127" in c_text, f"Missing signal mask in emitted C for {target}"
        assert "CreateProcessA" not in c_text
    else:
        assert "CreateProcessA" in c_text
        assert "waitpid" not in c_text


def test_windows_host_process_signal_returns_zero(tmp_path):
    """
    Task 75.3: On Windows host, verify that os_process_signal returns 0 for a finished process
    and for null.
    """
    if sys.platform != "win32":
        pytest.skip("Windows-specific test")
    src = tmp_path / "test_win_signal.vl"
    src.write_text(
        'use std.os.process\n\n'
        'act main() -> i32 {\n'
        '    mut proc = os_spawn("cmd.exe /c exit 0")\n'
        '    let wait_res = os_process_wait(@proc)\n'
        '    if wait_res != 0 { return 1 }\n'
        '    let sig = os_process_signal(@proc)\n'
        '    if sig != 0 { return 2 }\n'
        '    let sig_null = os_process_signal(null)\n'
        '    if sig_null != 0 { return 3 }\n'
        '    return 0\n'
        '}\n',
        encoding="utf-8",
    )
    out_bin = tmp_path / "test_win_signal.exe"
    build_res = subprocess.run(
        [str(require_velo_exe()), "build", str(src), "-o", str(out_bin)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_env(),
        timeout=30,
    )
    assert build_res.returncode == 0, f"build failed:\n{build_res.stdout}\n{build_res.stderr}"

    run_res = subprocess.run(
        [str(out_bin)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    assert run_res.returncode == 0, f"run failed with code {run_res.returncode}"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX host execution test; runs on Linux/macOS")
def test_posix_host_process_signal_decoding(tmp_path):
    """
    Task 75.3: On POSIX hosts, verify that terminating signals (e.g. SIGTERM=15, SIGSEGV=11)
    are accurately decoded by os_process_signal and waitpid status decoding.
    """
    src = tmp_path / "test_posix_sig.vl"
    src.write_text(
        'use std.os.process\n\n'
        'act main() -> i32 {\n'
        '    // 1. Process killed by SIGTERM (15)\n'
        '    mut proc_term = os_spawn("kill -15 $$")\n'
        '    let code_term = os_process_wait(@proc_term)\n'
        '    let sig_term = os_process_signal(@proc_term)\n'
        '    if sig_term != 15 { return 1 }\n'
        '    if code_term != 128 + 15 { return 2 }\n\n'
        '    // 2. Process killed by SIGSEGV (11)\n'
        '    mut proc_segv = os_spawn("kill -11 $$")\n'
        '    let code_segv = os_process_wait(@proc_segv)\n'
        '    let sig_segv = os_process_signal(@proc_segv)\n'
        '    if sig_segv != 11 { return 3 }\n'
        '    if code_segv != 128 + 11 { return 4 }\n\n'
        '    // 3. Normal process has signal == 0\n'
        '    mut proc_norm = os_spawn("echo normal")\n'
        '    let code_norm = os_process_wait(@proc_norm)\n'
        '    let sig_norm = os_process_signal(@proc_norm)\n'
        '    if sig_norm != 0 { return 5 }\n'
        '    if code_norm != 0 { return 6 }\n\n'
        '    return 0\n'
        '}\n',
        encoding="utf-8",
    )
    out_bin = tmp_path / "test_posix_sig"
    build_res = subprocess.run(
        [str(require_velo_exe()), "build", str(src), "-o", str(out_bin)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_env(),
        timeout=30,
    )
    assert build_res.returncode == 0, f"build failed:\n{build_res.stdout}\n{build_res.stderr}"

    run_res = subprocess.run(
        [str(out_bin)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    assert run_res.returncode == 0, f"run failed with code {run_res.returncode}"

