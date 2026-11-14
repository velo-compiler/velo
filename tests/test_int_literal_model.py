"""Tests for the IntLiteral value model in src/common/num_utils.vl (Task 53.2).

Verifies magnitude (u64), base, sign, and explicit overflow flag representation,
boundary fitting predicates, and checked conversions (no silent truncation).
"""

import subprocess
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
VELO_EXE = ROOT / "bin" / "velo.exe"
NUM_UTILS_PATH = (ROOT / "src" / "common" / "num_utils.vl").as_posix()


def run_velo_source(source: str, tmp_path: Path):
    probe = tmp_path / "probe_int_literal.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")
    return subprocess.run(
        [str(VELO_EXE), "run", str(probe)],
        capture_output=True,
        text=True,
    )


def test_int_literal_constructors_and_fields(tmp_path):
    source = f"""use "{NUM_UTILS_PATH}"
use std.io

act main() {{
    let lit1 = make_int_literal(42u64, 10, false, false)
    assert(lit1.val == 42u64)
    assert(lit1.base == 10)
    assert(not lit1.is_neg)
    assert(not lit1.overflow)

    let lit2 = make_int_literal_val(100u64, 16)
    assert(lit2.val == 100u64)
    assert(lit2.base == 16)
    assert(not lit2.is_neg)
    assert(not lit2.overflow)

    let lit3 = make_int_literal_overflow(8, true)
    assert(lit3.val == 0u64)
    assert(lit3.base == 8)
    assert(lit3.is_neg)
    assert(lit3.overflow)

    println_str("OK_CONSTRUCTORS")
}}
"""
    res = run_velo_source(source, tmp_path)
    assert res.returncode == 0, f"run failed:\n{res.stderr}\n{res.stdout}"
    assert "OK_CONSTRUCTORS" in res.stdout


def test_int_lit_fits_i32(tmp_path):
    source = f"""use "{NUM_UTILS_PATH}"
use std.io

act main() {{
    // 0 fits
    assert(int_lit_fits_i32(make_int_literal(0u64, 10, false, false)))
    // INT32_MAX (2147483647) fits
    assert(int_lit_fits_i32(make_int_literal(2147483647u64, 10, false, false)))
    // INT32_MAX + 1 (2147483648 positive) does NOT fit i32
    assert(not int_lit_fits_i32(make_int_literal(2147483648u64, 10, false, false)))
    // INT32_MIN (-2147483648) fits i32
    assert(int_lit_fits_i32(make_int_literal(2147483648u64, 10, true, false)))
    // -2147483649 does NOT fit i32
    assert(not int_lit_fits_i32(make_int_literal(2147483649u64, 10, true, false)))
    // Overflow flag rejects regardless of value
    assert(not int_lit_fits_i32(make_int_literal(0u64, 10, false, true)))

    println_str("OK_FITS_I32")
}}
"""
    res = run_velo_source(source, tmp_path)
    assert res.returncode == 0, f"run failed:\n{res.stderr}\n{res.stdout}"
    assert "OK_FITS_I32" in res.stdout


def test_int_lit_fits_u32(tmp_path):
    source = f"""use "{NUM_UTILS_PATH}"
use std.io

act main() {{
    assert(int_lit_fits_u32(make_int_literal(0u64, 10, false, false)))
    assert(int_lit_fits_u32(make_int_literal(4294967295u64, 10, false, false)))
    assert(not int_lit_fits_u32(make_int_literal(4294967296u64, 10, false, false)))
    // Negative does not fit u32
    assert(not int_lit_fits_u32(make_int_literal(1u64, 10, true, false)))
    // Overflow rejects
    assert(not int_lit_fits_u32(make_int_literal(10u64, 10, false, true)))

    println_str("OK_FITS_U32")
}}
"""
    res = run_velo_source(source, tmp_path)
    assert res.returncode == 0, f"run failed:\n{res.stderr}\n{res.stdout}"
    assert "OK_FITS_U32" in res.stdout


def test_int_lit_fits_i64_and_u64(tmp_path):
    source = f"""use "{NUM_UTILS_PATH}"
use std.io

act main() {{
    // INT64_MAX (0x7FFFFFFFFFFFFFFF) fits i64
    assert(int_lit_fits_i64(make_int_literal(0x7FFFFFFFFFFFFFFFu64, 16, false, false)))
    // INT64_MAX + 1 positive does NOT fit i64
    assert(not int_lit_fits_i64(make_int_literal(0x8000000000000000u64, 16, false, false)))
    // INT64_MIN (-0x8000000000000000) fits i64
    assert(int_lit_fits_i64(make_int_literal(0x8000000000000000u64, 16, true, false)))
    // Overflow rejects i64
    assert(not int_lit_fits_i64(make_int_literal(0u64, 10, false, true)))

    // UINT64_MAX fits u64
    assert(int_lit_fits_u64(make_int_literal(0xFFFFFFFFFFFFFFFFu64, 16, false, false)))
    // Negative rejects u64
    assert(not int_lit_fits_u64(make_int_literal(1u64, 10, true, false)))
    // Overflow rejects u64
    assert(not int_lit_fits_u64(make_int_literal(0u64, 10, false, true)))

    println_str("OK_FITS_64")
}}
"""
    res = run_velo_source(source, tmp_path)
    assert res.returncode == 0, f"run failed:\n{res.stderr}\n{res.stdout}"
    assert "OK_FITS_64" in res.stdout


def test_int_lit_checked_conversions(tmp_path):
    source = f"""use "{NUM_UTILS_PATH}"
use std.io
use std.mem

act main() {{
    mut val_i32: @i32 = mem.alloc(@i32, 1)
    mut val_u64: @u64 = mem.alloc(@u64, 1)
    mut val_i64: @i64 = mem.alloc(@i64, 1)

    // Positive i32
    let lit_pos = make_int_literal(12345u64, 10, false, false)
    assert(int_lit_to_i32_checked(lit_pos, val_i32))
    assert(val_i32[0] == 12345)

    // Negative i32
    let lit_neg = make_int_literal(2147483648u64, 10, true, false)
    assert(int_lit_to_i32_checked(lit_neg, val_i32))
    assert(val_i32[0] == -2147483647 - 1)

    // Overflows i32 -> MUST return false, no silent truncation!
    let lit_ovf_i32 = make_int_literal(2147483648u64, 10, false, false)
    assert(not int_lit_to_i32_checked(lit_ovf_i32, val_i32))

    // u64 conversion
    let lit_u64 = make_int_literal(0xFFFFFFFFFFFFFFFFu64, 16, false, false)
    assert(int_lit_to_u64_checked(lit_u64, val_u64))
    assert(val_u64[0] == 0xFFFFFFFFFFFFFFFFu64)
    // Negative rejected for u64
    let lit_neg_u64 = make_int_literal(1u64, 10, true, false)
    assert(not int_lit_to_u64_checked(lit_neg_u64, val_u64))

    // i64 conversion
    let lit_i64 = make_int_literal(0x8000000000000000u64, 16, true, false)
    assert(int_lit_to_i64_checked(lit_i64, val_i64))
    assert(val_i64[0] == -9223372036854775807i64 - 1i64)

    println_str("OK_CHECKED_CONVERSIONS")
}}
"""
    res = run_velo_source(source, tmp_path)
    assert res.returncode == 0, f"run failed:\n{res.stderr}\n{res.stdout}"
    assert "OK_CHECKED_CONVERSIONS" in res.stdout


def test_existing_parse_int_from_slice_wrapper_still_works(tmp_path):
    source = f"""use "{NUM_UTILS_PATH}"
use std.io

act main() {{
    let s = "42"
    let val = parse_int_from_slice(s, 0, 2)
    assert(val == 42)

    let hex_s = "0xFF"
    let val_hex = parse_int_from_slice(hex_s, 0, 4)
    assert(val_hex == 255)

    let ch = "'a'"
    let val_ch = parse_int_from_slice(ch, 0, 3)
    assert(val_ch == 97)

    println_str("OK_WRAPPER_WORKS")
}}
"""
    res = run_velo_source(source, tmp_path)
    assert res.returncode == 0, f"run failed:\n{res.stderr}\n{res.stdout}"
    assert "OK_WRAPPER_WORKS" in res.stdout
