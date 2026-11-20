import os
import subprocess
import sys
from pathlib import Path
import pytest
from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()


def get_env():
    env = os.environ.copy()
    if sys.platform == "win32":
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    env["VELO_STD"] = str(REPO_ROOT / "std")
    return env


def run_code(code: str, tmp_path: Path, mode: str = "--debug", extra_flags: list = None) -> subprocess.CompletedProcess:
    src_file = tmp_path / "arr_bounds_test.vl"
    src_file.write_text(code, encoding="utf-8")
    cmd = [str(VELO_EXE), "run", str(src_file), mode]
    if extra_flags:
        cmd.extend(extra_flags)
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=get_env(),
    )


def check_code(code: str, tmp_path: Path) -> subprocess.CompletedProcess:
    src_file = tmp_path / "arr_bounds_check.vl"
    src_file.write_text(code, encoding="utf-8")
    cmd = [str(VELO_EXE), "check", str(src_file)]
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=get_env(),
    )


def emit_c_code(code: str, tmp_path: Path, extra_flags: list = None) -> subprocess.CompletedProcess:
    src_file = tmp_path / "arr_bounds_emit.vl"
    src_file.write_text(code, encoding="utf-8")
    cmd = [str(VELO_EXE), "emit-c", str(src_file)]
    if extra_flags:
        cmd.extend(extra_flags)
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=get_env(),
    )


# -----------------------------------------------------------------------------
# Dynamic Index Probe Tests (Task 74.3 / gaps.md:1073 & 1139-1146)
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_dynamic_index_write_oob_fatal(tmp_path, mode):
    """Exact probe from gaps.md:1073: mut buf: [4]i32; mut i: i32 = 7; buf[i] = 1 traps with fatal."""
    code = """
act main() -> i32 {
    mut buf: [4]i32
    mut i: i32 = 7
    buf[i] = 1
    return 0
}
"""
    p = run_code(code, tmp_path, mode)
    assert p.returncode == 1, f"Expected fatal exit code 1, got {p.returncode}"
    assert "Velo Fatal Error: array index out of bounds: 7 (len 4)!" in p.stderr


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_dynamic_index_write_oob_unsafe_opt_out(tmp_path, mode):
    """Exact probe with --unsafe-array-index asserts the unchecked path for parity with shelf policy."""
    code = """
act main() -> i32 {
    mut buf: [4]i32
    mut i: i32 = 7
    buf[i] = 1
    return 0
}
"""
    p = run_code(code, tmp_path, mode, extra_flags=["--unsafe-array-index"])
    assert p.returncode == 0, f"Expected exit code 0 with --unsafe-array-index, got {p.returncode}"
    assert "Velo Fatal Error" not in p.stderr


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_dynamic_index_read_oob_fatal(tmp_path, mode):
    """Dynamic index read out of bounds traps with a clean fatal diagnostic."""
    code = """
act main() -> i32 {
    let buf: [4]i32 = [10, 20, 30, 40]
    mut i: i32 = 4
    let x = buf[i]
    return x
}
"""
    p = run_code(code, tmp_path, mode)
    assert p.returncode == 1
    assert "Velo Fatal Error: array index out of bounds: 4 (len 4)!" in p.stderr


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_dynamic_index_read_oob_unsafe_opt_out(tmp_path, mode):
    """Dynamic index read out of bounds with --unsafe-array-index runs unchecked."""
    code = """
act main() -> i32 {
    let buf: [4]i32 = [10, 20, 30, 40]
    mut i: i32 = 4
    let x = buf[i]
    return 0
}
"""
    p = run_code(code, tmp_path, mode, extra_flags=["--unsafe-array-index"])
    assert p.returncode == 0
    assert "Velo Fatal Error" not in p.stderr


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_dynamic_index_negative_oob_fatal(tmp_path, mode):
    """Dynamic negative index into a fixed array traps with fatal."""
    code = """
act main() -> i32 {
    mut buf: [4]i32
    mut i: i32 = -1
    buf[i] = 100
    return 0
}
"""
    p = run_code(code, tmp_path, mode)
    assert p.returncode == 1
    assert "Velo Fatal Error: array index out of bounds: -1 (len 4)!" in p.stderr


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_dynamic_index_in_bounds_success(tmp_path, mode):
    """Valid dynamic index within bounds succeeds in both read and write operations."""
    code = """
act main() -> i32 {
    mut buf: [4]i32
    mut i: i32 = 0
    loop i < 4 {
        buf[i] = i * 10
        i += 1
    }
    mut sum = 0
    i = 0
    loop i < 4 {
        sum += buf[i]
        i += 1
    }
    // 0 + 10 + 20 + 30 = 60
    if sum != 60 { return 1 }
    return 0
}
"""
    p = run_code(code, tmp_path, mode)
    assert p.returncode == 0


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_unsigned_dynamic_index_oob_fatal(tmp_path, mode):
    """Unsigned integer dynamic index exceeding bounds traps with fatal."""
    code = """
act main() -> i32 {
    mut buf: [4]i32
    mut idx: u32 = 10u32
    buf[idx] = 1
    return 0
}
"""
    p = run_code(code, tmp_path, mode)
    assert p.returncode == 1
    assert "Velo Fatal Error: array index out of bounds: 10 (len 4)!" in p.stderr


# -----------------------------------------------------------------------------
# Compile-Time Constant Bounds Checks
# -----------------------------------------------------------------------------


def test_constant_index_oob_rejected_at_compile_time(tmp_path):
    """Literal out-of-bounds index buf[4] is rejected at compile time."""
    code = """
act main() -> i32 {
    mut buf: [4]i32
    buf[4] = 1
    return 0
}
"""
    p = check_code(code, tmp_path)
    assert p.returncode != 0
    assert "Array index out of bounds" in (p.stdout + p.stderr)


def test_constant_negative_index_rejected_at_compile_time(tmp_path):
    """Constant negative index buf[-1] is rejected at compile time."""
    code = """
act main() -> i32 {
    mut buf: [4]i32
    buf[-1] = 1
    return 0
}
"""
    p = check_code(code, tmp_path)
    assert p.returncode != 0
    assert "Array index out of bounds" in (p.stdout + p.stderr)


def test_constant_expr_oob_rejected_at_compile_time(tmp_path):
    """Constant expression out of bounds buf[2 + 2] is rejected at compile time."""
    code = """
act main() -> i32 {
    mut buf: [4]i32
    buf[2 + 2] = 1
    return 0
}
"""
    p = check_code(code, tmp_path)
    assert p.returncode != 0
    assert "Array index out of bounds" in (p.stdout + p.stderr)


# -----------------------------------------------------------------------------
# Guard Elision & Optimization
# -----------------------------------------------------------------------------


def test_proven_in_bounds_constant_elides_guard(tmp_path):
    """Constant in-bounds index buf[2] elides velo_arr_idx guard in emitted C."""
    code = """
act main() -> i32 {
    mut buf: [4]i32
    buf[2] = 42
    mut i: i32 = 1
    buf[i] = 10
    return buf[2] + buf[i]
}
"""
    p = emit_c_code(code, tmp_path)
    assert p.returncode == 0
    lines = p.stdout.splitlines()

    # buf[2] must NOT be wrapped with velo_arr_idx
    assert "buf[velo_arr_idx(2" not in p.stdout, "Unexpected guard around constant index 2"
    assert "buf[2]" in p.stdout, "Expected constant access buf[2] in emitted C"

    # buf[i] MUST be wrapped with velo_arr_idx
    assert "buf[velo_arr_idx(i, 4)]" in p.stdout, "Expected velo_arr_idx(i, 4) in emitted C"


def test_unsafe_array_index_flag_elides_guard(tmp_path):
    """--unsafe-array-index flag elides velo_arr_idx guard for dynamic indexing in emitted C."""
    code = """
act main() -> i32 {
    mut buf: [4]i32
    mut i: i32 = 1
    buf[i] = 10
    return buf[i]
}
"""
    p = emit_c_code(code, tmp_path, extra_flags=["--unsafe-array-index"])
    assert p.returncode == 0
    assert "velo_arr_idx" not in p.stdout


# -----------------------------------------------------------------------------
# Compound Structures & Short-Circuit Evaluation
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_short_circuit_with_array_bounds(tmp_path, mode):
    """Logical short-circuit prevents array bounds guard from firing when condition is false."""
    code = """
act main() -> i32 {
    mut buf: [4]i32
    mut i: i32 = 10
    if i < 4 and buf[i] == 1 {
        return 1
    }
    return 0
}
"""
    p = run_code(code, tmp_path, mode)
    assert p.returncode == 0


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_multidimensional_fixed_array_bounds(tmp_path, mode):
    """Multidimensional fixed array traps when second dimension exceeds bounds."""
    code = """
act main() -> i32 {
    mut matrix: [2][3]i32
    mut i: i32 = 0
    mut j: i32 = 3
    matrix[i][j] = 1
    return 0
}
"""
    p = run_code(code, tmp_path, mode)
    assert p.returncode == 1
    assert "Velo Fatal Error: array index out of bounds: 3 (len 3)!" in p.stderr


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_struct_with_fixed_array_field_bounds(tmp_path, mode):
    """Struct containing fixed array traps when field array exceeds bounds."""
    code = """
data Buffer {
    data: [8]u8
}

act main() -> i32 {
    mut b: Buffer
    mut i: i32 = 8
    b.data[i] = 1u8
    return 0
}
"""
    p = run_code(code, tmp_path, mode)
    assert p.returncode == 1
    assert "Velo Fatal Error: array index out of bounds: 8 (len 8)!" in p.stderr
