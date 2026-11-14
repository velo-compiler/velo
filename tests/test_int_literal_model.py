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


def test_parse_decimal_int_literal_boundaries(tmp_path):
    source = f"""use "{NUM_UTILS_PATH}"
use std.io

act main() {{
    // 0
    let lit0 = parse_decimal_int_literal("0", 0, 1)
    assert(lit0.val == 0u64)
    assert(not lit0.overflow)

    // 2147483647 (INT32_MAX)
    let lit_i32_max = parse_decimal_int_literal("2147483647", 0, 10)
    assert(lit_i32_max.val == 2147483647u64)
    assert(not lit_i32_max.overflow)

    // 2147483648 (INT32_MAX + 1)
    let lit_i32_plus1 = parse_decimal_int_literal("2147483648", 0, 10)
    assert(lit_i32_plus1.val == 2147483648u64)
    assert(not lit_i32_plus1.overflow)

    // 9223372036854775807 (INT64_MAX)
    let lit_i64_max = parse_decimal_int_literal("9223372036854775807", 0, 19)
    assert(lit_i64_max.val == 9223372036854775807u64)
    assert(not lit_i64_max.overflow)

    // 18446744073709551615 (UINT64_MAX)
    let lit_u64_max = parse_decimal_int_literal("18446744073709551615", 0, 20)
    assert(lit_u64_max.val == 18446744073709551615u64)
    assert(not lit_u64_max.overflow)

    // 18446744073709551616 (UINT64_MAX + 1) -> overflow!
    let lit_ovf1 = parse_decimal_int_literal("18446744073709551616", 0, 20)
    assert(lit_ovf1.overflow)

    // Huge literal -> overflow!
    let lit_ovf2 = parse_decimal_int_literal("99999999999999999999999999999999", 0, 32)
    assert(lit_ovf2.overflow)

    // Malformed digits -> rejected with overflow!
    let lit_malformed = parse_decimal_int_literal("12a34", 0, 5)
    assert(lit_malformed.overflow)

    // Underscores handled properly
    let lit_underscores = parse_decimal_int_literal("1_000_000", 0, 9)
    assert(lit_underscores.val == 1000000u64)
    assert(not lit_underscores.overflow)

    println_str("OK_DECIMAL_BOUNDARIES")
}}
"""
    res = run_velo_source(source, tmp_path)
    assert res.returncode == 0, f"run failed:\n{res.stderr}\n{res.stdout}"
    assert "OK_DECIMAL_BOUNDARIES" in res.stdout


def test_parse_hex_int_literal_boundaries(tmp_path):
    source = f"""use "{NUM_UTILS_PATH}"
use std.io

act main() {{
    // 0x0
    let lit0 = parse_hex_int_literal("0x0", 0, 3)
    assert(lit0.val == 0u64)
    assert(lit0.base == 16)
    assert(not lit0.overflow)

    // 0x7FFFFFFF (INT32_MAX)
    let lit_i32_max = parse_hex_int_literal("0x7FFFFFFF", 0, 10)
    assert(lit_i32_max.val == 0x7FFFFFFFu64)
    assert(not lit_i32_max.overflow)

    // 0x80000000
    let lit_80m = parse_hex_int_literal("0x80000000", 0, 10)
    assert(lit_80m.val == 0x80000000u64)
    assert(not lit_80m.overflow)

    // 0xFFFFFFFF
    let lit_u32_max = parse_hex_int_literal("0xFFFFFFFF", 0, 10)
    assert(lit_u32_max.val == 0xFFFFFFFFu64)
    assert(not lit_u32_max.overflow)

    // 0xFFFFFFFFFFFFFFFF (UINT64_MAX)
    let lit_u64_max = parse_hex_int_literal("0xFFFFFFFFFFFFFFFF", 0, 18)
    assert(lit_u64_max.val == 0xFFFFFFFFFFFFFFFFu64)
    assert(not lit_u64_max.overflow)

    // 0x1_0000_0000_0000_0000 (UINT64_MAX + 1) -> overflow!
    let lit_ovf1 = parse_hex_int_literal("0x1_0000_0000_0000_0000", 0, 23)
    assert(lit_ovf1.overflow)

    // 0x10000000000000000 -> overflow!
    let lit_ovf2 = parse_hex_int_literal("0x10000000000000000", 0, 19)
    assert(lit_ovf2.overflow)

    // 0x (empty input after prefix) -> overflow/rejected!
    let lit_empty = parse_hex_int_literal("0x", 0, 2)
    assert(lit_empty.overflow)

    // 0xG (malformed hex digit) -> overflow/rejected!
    let lit_malformed = parse_hex_int_literal("0xG", 0, 3)
    assert(lit_malformed.overflow)

    // Underscores and lower/upper case: 0xDead_Beef
    let lit_mixed = parse_hex_int_literal("0xDead_Beef", 0, 11)
    assert(lit_mixed.val == 0xDEADBEEFu64)
    assert(not lit_mixed.overflow)

    println_str("OK_HEX_BOUNDARIES")
}}
"""
    res = run_velo_source(source, tmp_path)
    assert res.returncode == 0, f"run failed:\n{res.stderr}\n{res.stdout}"
    assert "OK_HEX_BOUNDARIES" in res.stdout


def test_parse_bin_int_literal_boundaries(tmp_path):
    source = f"""use "{NUM_UTILS_PATH}"
use std.io

act main() {{
    // 0b0
    let s0 = "0b0"
    let lit0 = parse_bin_int_literal(s0, 0, str.len(s0))
    assert(lit0.val == 0u64)
    assert(lit0.base == 2)
    assert(not lit0.overflow)

    // Leading zeros: 0b001
    let slz = "0b001"
    let lit_lz = parse_bin_int_literal(slz, 0, str.len(slz))
    assert(lit_lz.val == 1u64)
    assert(not lit_lz.overflow)

    // 32-bit all-ones: 0b11111111_11111111_11111111_11111111 (4294967295)
    let s32 = "0b11111111_11111111_11111111_11111111"
    let lit_u32_max = parse_bin_int_literal(s32, 0, str.len(s32))
    assert(lit_u32_max.val == 4294967295u64)
    assert(not lit_u32_max.overflow)

    // 64-bit all-ones (UINT64_MAX)
    let s64 = "0b11111111_11111111_11111111_11111111_11111111_11111111_11111111_11111111"
    let lit_u64_max = parse_bin_int_literal(s64, 0, str.len(s64))
    assert(lit_u64_max.val == 0xFFFFFFFFFFFFFFFFu64)
    assert(not lit_u64_max.overflow)

    // 65-bit overflow: 0b1_0000000000000000_0000000000000000_0000000000000000_0000000000000000
    let sovf = "0b1_0000000000000000_0000000000000000_0000000000000000_0000000000000000"
    let lit_ovf = parse_bin_int_literal(sovf, 0, str.len(sovf))
    assert(lit_ovf.overflow)

    // Empty 0b -> overflow/rejected
    let sempty = "0b"
    let lit_empty = parse_bin_int_literal(sempty, 0, str.len(sempty))
    assert(lit_empty.overflow)

    // Invalid digit '2' -> overflow/rejected
    let sd2 = "0b102"
    let lit_d2 = parse_bin_int_literal(sd2, 0, str.len(sd2))
    assert(lit_d2.overflow)

    let sbad = "0b2"
    let lit_bad = parse_bin_int_literal(sbad, 0, str.len(sbad))
    assert(lit_bad.overflow)

    println_str("OK_BIN_BOUNDARIES")
}}
"""
    res = run_velo_source(source, tmp_path)
    assert res.returncode == 0, f"run failed:\n{res.stderr}\n{res.stdout}"
    assert "OK_BIN_BOUNDARIES" in res.stdout


def test_parse_oct_int_literal_boundaries(tmp_path):
    source = f"""use "{NUM_UTILS_PATH}"
use std.io

act main() {{
    // 0o0
    let s0 = "0o0"
    let lit0 = parse_oct_int_literal(s0, 0, str.len(s0))
    assert(lit0.val == 0u64)
    assert(lit0.base == 8)
    assert(not lit0.overflow)

    // Leading zeros: 0o007
    let slz = "0o007"
    let lit_lz = parse_oct_int_literal(slz, 0, str.len(slz))
    assert(lit_lz.val == 7u64)
    assert(not lit_lz.overflow)

    // 32-bit all-ones: 0o37777777777 (4294967295)
    let s32 = "0o37777777777"
    let lit_u32_max = parse_oct_int_literal(s32, 0, str.len(s32))
    assert(lit_u32_max.val == 4294967295u64)
    assert(not lit_u32_max.overflow)

    // 64-bit all-ones: 0o1777777777777777777777 (UINT64_MAX)
    let s64 = "0o1777777777777777777777"
    let lit_u64_max = parse_oct_int_literal(s64, 0, str.len(s64))
    assert(lit_u64_max.val == 0xFFFFFFFFFFFFFFFFu64)
    assert(not lit_u64_max.overflow)

    // Overflow: 0o2000000000000000000000 (> UINT64_MAX)
    let sovf = "0o2000000000000000000000"
    let lit_ovf = parse_oct_int_literal(sovf, 0, str.len(sovf))
    assert(lit_ovf.overflow)

    // Empty 0o -> overflow/rejected
    let sempty = "0o"
    let lit_empty = parse_oct_int_literal(sempty, 0, str.len(sempty))
    assert(lit_empty.overflow)

    // Invalid digit '8' -> overflow/rejected
    let sd8 = "0o18"
    let lit_d8 = parse_oct_int_literal(sd8, 0, str.len(sd8))
    assert(lit_d8.overflow)

    let sbad = "0o8"
    let lit_bad = parse_oct_int_literal(sbad, 0, str.len(sbad))
    assert(lit_bad.overflow)

    // Invalid digit '9' -> overflow/rejected
    let sd9 = "0o79"
    let lit_d9 = parse_oct_int_literal(sd9, 0, str.len(sd9))
    assert(lit_d9.overflow)

    println_str("OK_OCT_BOUNDARIES")
}}
"""
    res = run_velo_source(source, tmp_path)
    assert res.returncode == 0, f"run failed:\n{res.stderr}\n{res.stdout}"
    assert "OK_OCT_BOUNDARIES" in res.stdout


@pytest.mark.parametrize("lit", [
    "0b2",
    "0b102",
    "0o8",
    "0o78",
    "0b",
    "0o",
])
def test_bin_oct_invalid_digits_and_empty_rejected(lit, tmp_path):
    source = (
        "use std.io\n\n"
        "act main() {\n"
        f"    let x = {lit}\n"
        "}\n"
    )
    probe = tmp_path / "invalid_lit.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")

    res = subprocess.run(
        [str(VELO_EXE), "check", str(probe)],
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0, f"velo check accepted invalid literal {lit}"
