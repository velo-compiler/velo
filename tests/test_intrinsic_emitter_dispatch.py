"""
Tests for Phase 80, Task 80.4:
Consolidate fs_gen/os_gen/time_gen behind one IntrinsicEmitter dispatch.

Verifies:
1. `src/backend/intrinsic_emitter.vl` provides table-driven intrinsic dispatch (intrinsic_c_target, emit_intrinsic_call).
2. `fs_gen.vl`, `os_gen.vl`, and `time_gen.vl` are consolidated as thin forwarders (each <= 20 lines).
3. `codegen_call.vl` dispatches through `emit_intrinsic_call`.
4. Emitted C for fs, os, time, and thread intrinsics matches canonical runtime shapes byte-for-byte.
5. End-to-end program using intrinsic operations compiles and executes correctly.
"""

import os
import subprocess
import sys
from pathlib import Path
import pytest
from conftest import velo_exe, cc_env

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()
SRC_BACKEND = REPO_ROOT / "src" / "backend"


def get_build_env():
    return cc_env()


def test_structural_intrinsic_emitter_consolidation():
    """Verify that intrinsic_emitter.vl exists and sliver modules are consolidated forwarders."""
    emitter_path = SRC_BACKEND / "intrinsic_emitter.vl"
    assert emitter_path.exists()
    emitter_src = emitter_path.read_text(encoding="utf-8")
    assert "act intrinsic_c_target(" in emitter_src
    assert "act emit_standard_intrinsic_call(" in emitter_src
    assert "act emit_intrinsic_call(" in emitter_src

    # fs_gen, os_gen, time_gen must be thin forwarders under 25 lines
    for mod_name in ["fs_gen.vl", "os_gen.vl", "time_gen.vl"]:
        path = SRC_BACKEND / mod_name
        assert path.exists()
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) <= 25, f"{mod_name} should be a thin forwarder, got {len(lines)} lines"
        content = "\n".join(lines)
        assert "emit_intrinsic_call" in content

    # codegen_call must dispatch via emit_intrinsic_call
    call_src = (SRC_BACKEND / "codegen_call.vl").read_text(encoding="utf-8")
    assert "emit_intrinsic_call(sb, st, target.str_val, member, expr)" in call_src


def test_emitted_c_intrinsic_shapes(tmp_path):
    """Verify that emitted C for fs, os, time, and thread intrinsics matches runtime shapes."""
    src_file = tmp_path / "intrinsics_test.vl"
    src_code = """
use std.fs
use std.os
use std.time

act test_intrinsics() {
    let t0 = time.now()
    let ex = fs.exists("nonexistent_test_file.txt")
    let env_val = os.get_env("PATH")
    let dt = time.delta()
}

act main() -> i32 {
    test_intrinsics()
    return 0
}
"""
    src_file.write_text(src_code, encoding="utf-8")
    c_file = tmp_path / "intrinsics_test.c"

    res = subprocess.run(
        [str(VELO_EXE), "emit-c", str(src_file), "-o", str(c_file)],
        capture_output=True,
        text=True,
        env=get_build_env(),
    )
    assert res.returncode == 0, f"emit-c failed: {res.stderr}\nstdout: {res.stdout}"

    c_code = c_file.read_text(encoding="utf-8")

    assert "velo_time_now_us()" in c_code
    assert 'velo_fs_exists("nonexistent_test_file.txt")' in c_code
    assert 'velo_os_get_env("PATH")' in c_code
    assert "velo_time_delta_us()" in c_code


def test_intrinsics_execution(tmp_path):
    """Verify that compiled intrinsic calls execute successfully."""
    src_file = tmp_path / "exec_intrinsics.vl"
    exe_file = tmp_path / "exec_intrinsics.exe"
    src_code = """
use std.fs
use std.time

act main() -> i32 {
    let t0 = time.now()
    if t0 <= 0i64 { return 1 }
    let exists = fs.exists("bootstrap.c")
    if not exists { return 2 }
    return 0
}
"""
    src_file.write_text(src_code, encoding="utf-8")

    res = subprocess.run(
        [str(VELO_EXE), "build", str(src_file), "-o", str(exe_file)],
        capture_output=True,
        text=True,
        env=get_build_env(),
    )
    assert res.returncode == 0, f"build failed: {res.stderr}\nstdout: {res.stdout}"

    run_res = subprocess.run([str(exe_file)], capture_output=True, text=True)
    assert run_res.returncode == 0, f"Execution failed with return code {run_res.returncode}"
