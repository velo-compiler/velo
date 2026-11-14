# tests/test_safe_c_literal_emission.py
"""
Task 53.7: Verification tests for safe C numeric literal emission.

Validates that:
1. Boundary integer literals (INT64_MIN, INT32_MIN, INT64_MAX, UINT64_MAX) emit safe C99 expressions
   that cannot re-wrap or produce signed overflow / implementation-defined conversions.
2. Runtime values of boundary literals survive parse -> check -> emit -> run and match mathematical values.
3. String interpolation correctly formats unsigned 64-bit integers (%llu) rather than truncating/wrapping (%lld).
4. Emitted C compiles cleanly under GCC with -Wall -Wextra -Wconversion.
"""

import os
import subprocess
import tempfile
import pytest

COMPILER = "bin/velo.exe"
GCC = r"C:\msys64\ucrt64\bin\gcc.exe"


def has_toolchain():
    return os.path.exists(COMPILER) and os.path.exists(GCC)


pytestmark = pytest.mark.skipif(not has_toolchain(), reason="velo.exe or gcc not found")


def get_env():
    env = dict(os.environ)
    env["PATH"] = r"C:\msys64\ucrt64\bin;" + env.get("PATH", "")
    return env


def run_velo_source(code: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "test.vl")
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
        return subprocess.run(
            [COMPILER, "run", src],
            env=get_env(),
            capture_output=True,
            text=True,
            timeout=30,
        )


def emit_c_source(code: str) -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "test.vl")
        out_c = os.path.join(tmpdir, "test.c")
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
        res = subprocess.run(
            [COMPILER, "emit-c", src, "-o", out_c],
            env=get_env(),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert res.returncode == 0, f"emit-c failed: {res.stderr}\n{res.stdout}"
        with open(out_c, "r", encoding="utf-8") as f:
            return f.read()


def test_int64_min_emitted_c_pattern():
    """Verify INT64_MIN emits (-9223372036854775807LL - 1LL) across all numeric bases."""
    code = """
act main() {
    let a: i64 = -9223372036854775808
    let b: i64 = -0x8000_0000_0000_0000
    let c: i64 = -0b1000000000000000000000000000000000000000000000000000000000000000
    let d: i64 = -0o1000000000000000000000
}
"""
    c_out = emit_c_source(code)
    # Must use standard C99 INT64_MIN pattern to avoid unsigned wrapping in C
    assert "(-9223372036854775807LL - 1LL)" in c_out
    assert "(-9223372036854775808ULL)" not in c_out


def test_int32_min_emitted_c_pattern():
    """Verify INT32_MIN emits (-2147483647 - 1) when typed as i32."""
    code = """
act main() {
    let a: i32 = -2147483648
    let b: i32 = -0x8000_0000
}
"""
    c_out = emit_c_source(code)
    assert "(-2147483647 - 1)" in c_out
    assert "(-2147483648LL)" not in c_out


def test_wide_positive_literals_emitted_c_pattern():
    """Verify wide positive literals have proper LL/ULL suffixes in emitted C."""
    code = """
act main() {
    let max_i64: i64 = 9223372036854775807
    let max_u64: u64 = 18446744073709551615
    let hex_u64: u64 = 0xFFFFFFFFFFFFFFFF
    let hex_i64: i64 = 0x7FFFFFFFFFFFFFFF
}
"""
    c_out = emit_c_source(code)
    assert "9223372036854775807LL" in c_out
    assert "18446744073709551615ULL" in c_out
    assert "0xFFFFFFFFFFFFFFFFULL" in c_out
    assert "0x7FFFFFFFFFFFFFFFLL" in c_out


def test_runtime_boundaries_survive_execution():
    """Verify boundary values survive parse -> check -> emit -> run with exact values."""
    code = """
act main() {
    let min_i64: i64 = -9223372036854775808
    let max_i64: i64 = 9223372036854775807
    let min_i32: i32 = -2147483648
    let max_i32: i32 = 2147483647
    let max_u64: u64 = 18446744073709551615
    let max_u64_hex: u64 = 0xFFFFFFFFFFFFFFFF
    let max_u32_hex: u32 = 0xFFFFFFFF

    io.println("min_i64={min_i64}")
    io.println("max_i64={max_i64}")
    io.println("min_i32={min_i32}")
    io.println("max_i32={max_i32}")
    io.println("max_u64={max_u64}")
    io.println("max_u64_hex={max_u64_hex}")
    io.println("max_u32_hex={max_u32_hex}")

    // Arithmetic and comparison semantics on INT64_MIN
    let is_neg: bool = min_i64 < 0
    let half_min: i64 = min_i64 / 2
    let plus_one: i64 = min_i64 + 1
    io.println("is_neg={is_neg}")
    io.println("half_min={half_min}")
    io.println("plus_one={plus_one}")
}
"""
    res = run_velo_source(code)
    assert res.returncode == 0, f"Run failed: {res.stderr}\n{res.stdout}"
    out = res.stdout
    assert "min_i64=-9223372036854775808" in out
    assert "max_i64=9223372036854775807" in out
    assert "min_i32=-2147483648" in out
    assert "max_i32=2147483647" in out
    # Unsigned 64-bit must not wrap to -1
    assert "max_u64=18446744073709551615" in out
    assert "max_u64_hex=18446744073709551615" in out
    assert "max_u32_hex=4294967295" in out
    # Arithmetic & relations
    assert "is_neg=true" in out
    assert "half_min=-4611686018427387904" in out
    assert "plus_one=-9223372036854775807" in out


def test_mixed_signed_unsigned_boundary_comparisons():
    """Verify comparisons between INT64_MIN, 0u64, and UINT64_MAX operate safely."""
    code = """
act main() {
    let min_i64: i64 = -9223372036854775808
    let max_u64: u64 = 18446744073709551615
    let zero_u64: u64 = 0u64

    let lt_zero: bool = min_i64 < zero_u64
    let lt_max: bool = min_i64 < max_u64
    let gt_check: bool = max_u64 > min_i64
    let eq_check: bool = min_i64 == max_u64

    io.println("lt_zero={lt_zero}")
    io.println("lt_max={lt_max}")
    io.println("gt_check={gt_check}")
    io.println("eq_check={eq_check}")
}
"""
    res = run_velo_source(code)
    assert res.returncode == 0, f"Run failed: {res.stderr}\n{res.stdout}"
    out = res.stdout
    assert "lt_zero=true" in out
    assert "lt_max=true" in out
    assert "gt_check=true" in out
    assert "eq_check=false" in out


def test_emitted_c_compiles_with_strict_gcc_flags():
    """Verify emitted C compiles without signed conversion warnings under GCC."""
    code = """
act main() {
    let min_i64: i64 = -9223372036854775808
    let max_i64: i64 = 9223372036854775807
    let min_i32: i32 = -2147483648
    let max_i32: i32 = 2147483647
    let max_u64: u64 = 18446744073709551615
    let max_u64_hex: u64 = 0xFFFFFFFFFFFFFFFF
    let max_u32_hex: u32 = 0xFFFFFFFF
    io.println("{min_i64} {max_i64} {min_i32} {max_i32} {max_u64} {max_u64_hex} {max_u32_hex}")
}
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "test.vl")
        out_c = os.path.join(tmpdir, "test.c")
        out_o = os.path.join(tmpdir, "test.o")
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
        res_emit = subprocess.run(
            [COMPILER, "emit-c", src, "-o", out_c],
            env=get_env(),
            capture_output=True,
            text=True,
        )
        assert res_emit.returncode == 0

        # Compile with GCC -Wconversion and treat warnings as errors (excluding runtime pragmas)
        res_gcc = subprocess.run(
            [
                GCC,
                "-I",
                "runtime",
                "-c",
                out_c,
                "-o",
                out_o,
                "-Wall",
                "-Wextra",
                "-Wconversion",
                "-Wno-unknown-pragmas",
                "-Wno-pedantic",
                "-Wno-unused-parameter",
                "-Werror",
            ],
            env=get_env(),
            capture_output=True,
            text=True,
        )
        assert res_gcc.returncode == 0, f"GCC failed with warnings/errors: {res_gcc.stderr}"
