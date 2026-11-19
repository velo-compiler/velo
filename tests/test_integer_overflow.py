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


def run_code(code: str, tmp_path: Path, mode: str = "--debug") -> subprocess.CompletedProcess:
    src_file = tmp_path / "overflow_test.vl"
    src_file.write_text(code, encoding="utf-8")
    cmd = [str(VELO_EXE), "run", str(src_file), mode]
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=get_env(),
    )


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_signed_32bit_overflow_boundaries(tmp_path, mode):
    """Verify that signed 32-bit integer arithmetic wraps using two's complement without UB."""
    code = """
use std.io

act main() -> i32 {
    let max_val: i32 = 2147483647
    let min_val: i32 = -2147483647 - 1

    // 1. Addition overflow: INT32_MAX + 1 wraps to INT32_MIN
    let add_ovf: i32 = max_val + 1
    if add_ovf != min_val {
        println_str("FAIL: i32 addition overflow did not wrap to min_val")
        return 1
    }

    // 2. Subtraction underflow: INT32_MIN - 1 wraps to INT32_MAX
    let sub_udf: i32 = min_val - 1
    if sub_udf != max_val {
        println_str("FAIL: i32 subtraction underflow did not wrap to max_val")
        return 2
    }

    // 3. Multiplication overflow: INT32_MAX * 2 wraps to -2
    let mul_ovf: i32 = max_val * 2
    if mul_ovf != -2 {
        println_str("FAIL: i32 multiplication overflow did not wrap to -2")
        return 3
    }

    // 4. Strict-overflow anti-UB optimization check:
    // With -fwrapv, the compiler cannot assume (x + 1 > x) is always true.
    let x: i32 = 2147483647
    let x_plus_one: i32 = x + 1
    if not (x_plus_one < x) {
        println_str("FAIL: (x + 1 < x) check optimized away or invalid")
        return 4
    }

    println_str("PASS: signed 32-bit overflow wraparound verified")
    return 0
}
"""
    res = run_code(code, tmp_path, mode)
    assert res.returncode == 0, f"Failed in {mode}:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "PASS: signed 32-bit overflow wraparound verified" in res.stdout


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_signed_64bit_overflow_boundaries(tmp_path, mode):
    """Verify that signed 64-bit integer arithmetic wraps using two's complement without UB."""
    code = """
use std.io

act main() -> i32 {
    let max_val: i64 = 9223372036854775807
    let min_val: i64 = -9223372036854775807 - 1

    // 1. Addition overflow: INT64_MAX + 1 wraps to INT64_MIN
    let add_ovf: i64 = max_val + 1
    if add_ovf != min_val {
        println_str("FAIL: i64 addition overflow did not wrap to min_val")
        return 1
    }

    // 2. Subtraction underflow: INT64_MIN - 1 wraps to INT64_MAX
    let sub_udf: i64 = min_val - 1
    if sub_udf != max_val {
        println_str("FAIL: i64 subtraction underflow did not wrap to max_val")
        return 2
    }

    // 3. Multiplication overflow: INT64_MAX * 2 wraps to -2
    let mul_ovf: i64 = max_val * 2
    if mul_ovf != -2 {
        println_str("FAIL: i64 multiplication overflow did not wrap to -2")
        return 3
    }

    // 4. Anti-UB check: (x + 1 < x) must evaluate to true on overflow
    let x: i64 = 9223372036854775807
    let x_plus_one: i64 = x + 1
    if not (x_plus_one < x) {
        println_str("FAIL: i64 (x + 1 < x) check failed")
        return 4
    }

    println_str("PASS: signed 64-bit overflow wraparound verified")
    return 0
}
"""
    res = run_code(code, tmp_path, mode)
    assert res.returncode == 0, f"Failed in {mode}:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "PASS: signed 64-bit overflow wraparound verified" in res.stdout


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_unsigned_overflow_boundaries(tmp_path, mode):
    """Verify standard unsigned wraparound at 32-bit and 64-bit limits."""
    code = """
use std.io

act main() -> i32 {
    let u32_max: u32 = 0xFFFFFFFF as u32
    if (u32_max + (1 as u32)) != (0 as u32) {
        println_str("FAIL: u32 wrap addition")
        return 1
    }
    if ((0 as u32) - (1 as u32)) != u32_max {
        println_str("FAIL: u32 wrap subtraction")
        return 2
    }

    let u64_max: u64 = 0xFFFFFFFFFFFFFFFF as u64
    if (u64_max + (1 as u64)) != (0 as u64) {
        println_str("FAIL: u64 wrap addition")
        return 3
    }
    if ((0 as u64) - (1 as u64)) != u64_max {
        println_str("FAIL: u64 wrap subtraction")
        return 4
    }

    println_str("PASS: unsigned overflow boundaries verified")
    return 0
}
"""
    res = run_code(code, tmp_path, mode)
    assert res.returncode == 0, f"Failed in {mode}:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "PASS: unsigned overflow boundaries verified" in res.stdout


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_checked_and_overflowing_arithmetic_library(tmp_path, mode):
    """Verify std.math.int checked and overflowing arithmetic functions in both modes."""
    code = """
use std.io
use std.math.int

act main() -> i32 {
    let min_i32_val: i32 = -2147483647 - 1
    let max_i32_val: i32 = 2147483647
    let min_i64_val: i64 = -9223372036854775807 - 1
    let max_i64_val: i64 = 9223372036854775807

    // 1. checked_add_i32
    mut r32: i32 = 0
    let ok_add = checked_add_i32(max_i32_val, 1, @r32)
    if ok_add or r32 != min_i32_val {
        println_str("FAIL: checked_add_i32 overflow")
        return 1
    }
    let ok_add2 = checked_add_i32(50, 75, @r32)
    if not ok_add2 or r32 != 125 {
        println_str("FAIL: checked_add_i32 normal")
        return 2
    }

    // 2. checked_sub_i32
    let ok_sub = checked_sub_i32(min_i32_val, 1, @r32)
    if ok_sub or r32 != max_i32_val {
        println_str("FAIL: checked_sub_i32 underflow")
        return 3
    }

    // 3. checked_mul_i32
    let ok_mul = checked_mul_i32(2000000, 2000, @r32)
    if ok_mul {
        println_str("FAIL: checked_mul_i32 overflow")
        return 4
    }

    // 4. checked_div_i32 edge case (INT32_MIN / -1)
    let ok_div_trap = checked_div_i32(min_i32_val, -1, @r32)
    if ok_div_trap {
        println_str("FAIL: checked_div_i32 INT32_MIN / -1 should fail")
        return 5
    }
    let ok_div_zero = checked_div_i32(100, 0, @r32)
    if ok_div_zero {
        println_str("FAIL: checked_div_i32 div by zero should fail")
        return 6
    }
    let ok_div_valid = checked_div_i32(100, 4, @r32)
    if not ok_div_valid or r32 != 25 {
        println_str("FAIL: checked_div_i32 normal division")
        return 7
    }

    // 5. checked_add_i64
    mut r64: i64 = 0
    let ok_add64 = checked_add_i64(max_i64_val, 1, @r64)
    if ok_add64 or r64 != min_i64_val {
        println_str("FAIL: checked_add_i64 overflow")
        return 8
    }

    // 6. checked_div_i64 edge case (INT64_MIN / -1)
    let ok_div64_trap = checked_div_i64(min_i64_val, -1, @r64)
    if ok_div64_trap {
        println_str("FAIL: checked_div_i64 INT64_MIN / -1 should fail")
        return 9
    }

    // 7. checked_add_u32 and checked_mul_u64
    mut ru32: u32 = 0
    let ok_uadd = checked_add_u32(0xFFFFFFFF as u32, 1 as u32, @ru32)
    if ok_uadd or ru32 != (0 as u32) {
        println_str("FAIL: checked_add_u32")
        return 10
    }

    mut ru64: u64 = 0
    let ok_umul = checked_mul_u64(0xFFFFFFFFFFFFFFFF as u64, 2 as u64, @ru64)
    if ok_umul {
        println_str("FAIL: checked_mul_u64")
        return 11
    }

    println_str("PASS: checked arithmetic verified")
    return 0
}
"""
    res = run_code(code, tmp_path, mode)
    assert res.returncode == 0, f"Failed in {mode}:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "PASS: checked arithmetic verified" in res.stdout
