"""
POSIX process execution test suite (Phase 75 / Task 75.4).

Verifies the full lifecycle of POSIX subprocess execution on Linux and macOS:
1. spawn+wait exit code:
   - exit 0 normal termination
   - non-zero exit codes (42, 7)
   - asynchronous spawn and wait
   - non-blocking try_wait polling while running
   - argument array spawning via os_spawn_sync_argv
   - os_system shell execution helper
2. stdout/stderr capture:
   - isolated stdout capture via os_spawn_capture
   - isolated stderr capture
   - simultaneous interleaved dual-stream capture with exit code
   - os_capture_stdout helper
3. signal termination:
   - process terminating via SIGTERM (signal 15) -> os_process_signal == 15, code == 128 + 15
   - process terminating via SIGSEGV (signal 11) -> os_process_signal == 11, code == 128 + 11
   - process killed externally via os_process_kill -> os_process_signal == 9
   - normal exit and null handles return signal 0
4. non-existent binary:
   - spawning non-existent binary yields exit code 127 with diagnostic on stderr (never crash)
   - null and empty string command lines return exit code -1 gracefully
5. pipe close ordering:
   - concurrent poll draining prevents deadlock on stdout payloads exceeding 64KB kernel buffer
   - concurrent poll draining prevents deadlock on stderr payloads exceeding 64KB kernel buffer
   - repeated spawn-capture cycles cleanly close endpoints without descriptor leakage

Gated strictly on `sys.platform != "win32"` as specified by Phase 75.4.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import cc_dir, require_velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()

pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX process execution tests; runs on Linux/macOS",
)


def _env():
    env = os.environ.copy()
    directory = cc_dir()
    if directory and directory not in env.get("PATH", ""):
        env["PATH"] = directory + os.pathsep + env.get("PATH", "")
    env["VELO_STD"] = str(REPO_ROOT / "std")
    return env


def _build_and_run(tmp_path, name, velo_code, timeout=20):
    src = tmp_path / f"{name}.vl"
    src.write_text(velo_code, encoding="utf-8")
    out_bin = tmp_path / name
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
    assert build_res.returncode == 0, (
        f"build failed for {name}:\nstdout:\n{build_res.stdout}\nstderr:\n{build_res.stderr}"
    )
    run_res = subprocess.run(
        [str(out_bin)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    assert run_res.returncode == 0, (
        f"execution failed for {name} with code {run_res.returncode}\n"
        f"stdout:\n{run_res.stdout}\nstderr:\n{run_res.stderr}"
    )
    return run_res


def test_posix_spawn_wait_exit_code(tmp_path):
    """
    Task 75.4: Verify spawn+wait exit code handling across exit 0, non-zero exits,
    try_wait non-blocking polling, argv spawning, and os_system helper.
    """
    code = """use std.os.process
use std.mem.arena

act main() -> i32 {
    mut arena = arena_init(16384)

    // 1. Synchronous spawn: exit 0
    let res0 = os_spawn_sync("exit 0")
    if !res0.success or res0.exit_code != 0 { return 1 }

    // 2. Synchronous spawn: non-zero exit code (42)
    let res42 = os_spawn_sync("exit 42")
    if res42.success or res42.exit_code != 42 { return 2 }

    // 3. Synchronous spawn: exit 7
    let res7 = os_spawn_sync("exit 7")
    if res7.success or res7.exit_code != 7 { return 3 }

    // 4. Asynchronous spawn: wait
    mut proc = os_spawn("exit 88")
    if !proc.is_alive { return 4 }
    let code88 = os_process_wait(@proc)
    if code88 != 88 or proc.is_alive { return 5 }

    // 5. Asynchronous spawn: try_wait while running, then terminate
    mut long_proc = os_spawn("sleep 2")
    if !long_proc.is_alive { return 6 }
    let poll = os_process_try_wait(@long_proc)
    if poll != -1 or !long_proc.is_alive { return 7 }
    let kill_ok = os_process_kill(@long_proc)
    if !kill_ok { return 8 }

    // 6. os_spawn_sync_argv
    let cmd_args = arena_alloc(@arena, 3 * 8, 8) as @string
    cmd_args[0] = "sh"
    cmd_args[1] = "-c"
    cmd_args[2] = "exit 19"
    let res_argv = os_spawn_sync_argv(@arena, cmd_args, 3)
    if res_argv.success or res_argv.exit_code != 19 { return 9 }

    // 7. os_system
    let sys_code = os_system("exit 55")
    if sys_code != 55 { return 10 }

    arena_free(@arena)
    return 0
}
"""
    _build_and_run(tmp_path, "test_spawn_wait", code)


def test_posix_stdout_stderr_capture(tmp_path):
    """
    Task 75.4: Verify stdout and stderr capture across isolated stdout,
    isolated stderr, simultaneous dual-stream output, and os_capture_stdout helper.
    """
    code = """use std.os.process
use std.os.pipe
use std.mem.arena
use std.str.slice

act main() -> i32 {
    mut arena = arena_init(65536)

    // 1. stdout capture only
    let out1 = os_spawn_capture(@arena, "printf 'stdout_only_message'")
    if !out1.success or out1.exit_code != 0 { return 1 }
    if !slice_eq_str(slice_from_str(out1.stdout_str), "stdout_only_message") { return 2 }
    if raw_str_len(out1.stderr_str as @u8) != 0 { return 3 }

    // 2. stderr capture only
    let out2 = os_spawn_capture(@arena, "printf 'stderr_only_message' >&2")
    if !out2.success or out2.exit_code != 0 { return 4 }
    if raw_str_len(out2.stdout_str as @u8) != 0 { return 5 }
    if !slice_eq_str(slice_from_str(out2.stderr_str), "stderr_only_message") { return 6 }

    // 3. both stdout and stderr simultaneously with non-zero exit code
    let out3 = os_spawn_capture(@arena, "printf 'out_payload'; printf 'err_payload' >&2; exit 17")
    if out3.success or out3.exit_code != 17 { return 7 }
    if !slice_eq_str(slice_from_str(out3.stdout_str), "out_payload") { return 8 }
    if !slice_eq_str(slice_from_str(out3.stderr_str), "err_payload") { return 9 }

    // 4. os_capture_stdout helper
    let s4 = os_capture_stdout(@arena, "printf 'captured_output'")
    if !slice_eq_str(slice_from_str(s4), "captured_output") { return 10 }

    arena_free(@arena)
    return 0
}
"""
    _build_and_run(tmp_path, "test_capture", code)


def test_posix_signal_termination(tmp_path):
    """
    Task 75.4: Verify signal termination handling: SIGTERM (15), SIGSEGV (11),
    external kill (9), and os_process_signal decoding.
    """
    code = """use std.os.process

act main() -> i32 {
    // 1. Process killed by SIGTERM (15)
    mut proc_term = os_spawn("kill -15 $$")
    if !proc_term.is_alive { return 1 }
    let code_term = os_process_wait(@proc_term)
    let sig_term = os_process_signal(@proc_term)
    if sig_term != 15 { return 2 }
    if code_term != 128 + 15 { return 3 }
    if proc_term.is_alive { return 4 }

    // 2. Process killed by SIGSEGV (11)
    mut proc_segv = os_spawn("kill -11 $$")
    if !proc_segv.is_alive { return 5 }
    let code_segv = os_process_wait(@proc_segv)
    let sig_segv = os_process_signal(@proc_segv)
    if sig_segv != 11 { return 6 }
    if code_segv != 128 + 11 { return 7 }
    if proc_segv.is_alive { return 8 }

    // 3. Process killed externally via os_process_kill (SIGKILL = 9)
    mut proc_kill = os_spawn("sleep 10")
    if !proc_kill.is_alive { return 9 }
    let ok_kill = os_process_kill(@proc_kill)
    if !ok_kill { return 10 }
    let sig_kill = os_process_signal(@proc_kill)
    if sig_kill != 9 { return 11 }
    if proc_kill.is_alive { return 12 }

    // 4. Normal exit has signal == 0
    mut proc_norm = os_spawn("exit 0")
    let code_norm = os_process_wait(@proc_norm)
    let sig_norm = os_process_signal(@proc_norm)
    if sig_norm != 0 or code_norm != 0 { return 13 }

    // 5. Signal query on null handle returns 0
    if os_process_signal(null) != 0 { return 14 }

    return 0
}
"""
    _build_and_run(tmp_path, "test_signal", code)


def test_posix_non_existent_binary(tmp_path):
    """
    Task 75.4: Verify execution of non-existent binary yields a named error / shell 127,
    and invalid arguments (null / empty string) fail gracefully without crash or hang.
    """
    code = """use std.os.process
use std.os.pipe
use std.mem.arena
use std.str.slice

act main() -> i32 {
    mut arena = arena_init(65536)

    // 1. Spawning non-existent binary synchronously
    // In POSIX, sh -c '/nonexistent_xyz_404' returns 127, success == false (no crash)
    let res1 = os_spawn_sync("/nonexistent_bin_path_xyz_404_no_such_binary")
    if res1.success { return 1 }
    if res1.exit_code != 127 { return 2 }

    // 2. Spawning non-existent binary with capture
    let out1 = os_spawn_capture(@arena, "/nonexistent_bin_path_xyz_404_no_such_binary")
    if out1.success { return 3 }
    if out1.exit_code != 127 { return 4 }
    // Stderr should capture the shell's failure message
    let err_len = raw_str_len(out1.stderr_str as @u8)
    if err_len == 0 { return 5 }

    // 3. Spawning null command line
    let res_null = os_spawn_sync(null)
    if res_null.success or res_null.exit_code != -1 { return 6 }

    let out_null = os_spawn_capture(@arena, null)
    if out_null.success or out_null.exit_code != -1 { return 7 }

    // 4. Spawning empty command line
    let res_empty = os_spawn_sync("")
    if res_empty.success or res_empty.exit_code != -1 { return 8 }

    let out_empty = os_spawn_capture(@arena, "")
    if out_empty.success or out_empty.exit_code != -1 { return 9 }

    arena_free(@arena)
    return 0
}
"""
    _build_and_run(tmp_path, "test_non_existent", code)


def test_posix_pipe_close_ordering(tmp_path):
    """
    Task 75.4: Verify pipe close ordering:
    - Large stdout payload (> 64KB pipe buffer) drains concurrently without deadlock
    - Large stderr payload (> 64KB pipe buffer) drains concurrently without deadlock
    - Repeated spawn-capture cycles properly close endpoints and do not leak descriptors
    """
    code = """use std.os.process
use std.os.pipe
use std.mem.arena
use std.str.slice

act main() -> i32 {
    mut arena = arena_init(524288)

    // 1. Large stdout payload test (100KB > 64KB pipe buffer) to verify concurrent poll draining
    // and write-endpoint closure prevent deadlocks
    let out_large = os_spawn_capture(@arena, "dd if=/dev/zero bs=1024 count=100 2>/dev/null | tr '\\\\0' 'A'")
    if !out_large.success or out_large.exit_code != 0 { return 1 }
    let large_len = raw_str_len(out_large.stdout_str as @u8)
    if large_len != 102400 { return 2 }

    // 2. Large stderr payload test (100KB > 64KB pipe buffer)
    let out_err_large = os_spawn_capture(@arena, "dd if=/dev/zero bs=1024 count=100 2>/dev/null | tr '\\\\0' 'B' >&2")
    if !out_err_large.success or out_err_large.exit_code != 0 { return 3 }
    let err_large_len = raw_str_len(out_err_large.stderr_str as @u8)
    if err_large_len != 102400 { return 4 }

    // 3. Repeated spawn-capture cycles to verify descriptors are closed and do not leak
    mut cycle: usize = 0
    loop cycle < 30 {
        let out_c = os_spawn_capture(@arena, "printf 'cycle_token'")
        if !out_c.success or out_c.exit_code != 0 { return 5 }
        if !slice_eq_str(slice_from_str(out_c.stdout_str), "cycle_token") { return 6 }
        cycle += 1
    }

    arena_free(@arena)
    return 0
}
"""
    _build_and_run(tmp_path, "test_pipe_close", code)
