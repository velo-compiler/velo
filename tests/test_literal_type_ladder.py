"""Tests for the unsuffixed literal type ladder and suffixed literal strictness (Task 53.6).

Rule:
- Unsuffixed integer literal type ladder:
    fits i32 ([-2^31, 2^31-1]) -> i32
    else fits i64 ([-2^63, 2^63-1]) -> i64
    else fits u64 ([0, 2^64-1]) -> u64
    else compile error.
- Suffixed literals remain strict (no implicit narrowing or cross-family conversion).
- Contextual literal adaptation adapts unsuffixed literals to the target integer type
  if and only if the constant value fits within the target type's range.
"""

import os
import subprocess
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = REPO_ROOT / "bin" / "velo.exe"


def get_env():
    env = os.environ.copy()
    if r"C:\msys64\ucrt64\bin" not in env.get("PATH", ""):
        env["PATH"] = r"C:\msys64\ucrt64\bin;" + env.get("PATH", "")
    return env


def run_velo_check(source: str, tmp_path: Path):
    probe = tmp_path / "probe.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")
    return subprocess.run(
        [str(VELO_EXE), "check", str(probe)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
    )


# ---------------------------------------------------------------------------
# 1. Inferred static type for unsuffixed boundaries
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lit,expected_type", [
    # Decimal i32
    ("0", "i32"),
    ("1", "i32"),
    ("2147483647", "i32"),
    # Decimal i64
    ("2147483648", "i64"),
    ("4294967295", "i64"),
    ("9223372036854775807", "i64"),
    # Decimal u64
    ("9223372036854775808", "u64"),
    ("18446744073709551615", "u64"),
    # Negative i32
    ("-1", "i32"),
    ("-2147483648", "i32"),
    # Negative i64
    ("-2147483649", "i64"),
    ("-9223372036854775808", "i64"),
    # Hexadecimal i32
    ("0x0", "i32"),
    ("0x7FFFFFFF", "i32"),
    # Hexadecimal i64
    ("0x80000000", "i64"),
    ("0xFFFFFFFF", "i64"),
    ("0x7FFFFFFFFFFFFFFF", "i64"),
    # Hexadecimal u64
    ("0x8000000000000000", "u64"),
    ("0xFFFFFFFFFFFFFFFF", "u64"),
    # Binary
    ("0b01111111_11111111_11111111_11111111", "i32"),
    ("0b10000000_00000000_00000000_00000000", "i64"),
    ("0b10000000_00000000_00000000_00000000_00000000_00000000_00000000_00000000", "u64"),
    # Octal
    ("0o17777777777", "i32"),
    ("0o20000000000", "i64"),
    ("0o1000000000000000000000", "u64"),
])
def test_unsuffixed_literal_inferred_type(lit, expected_type, tmp_path):
    # Verify the inferred type at compile time by passing to a function expecting that exact type
    source = f"""use std.io

act expect_i32(v: i32) {{}}
act expect_i64(v: i64) {{}}
act expect_u64(v: u64) {{}}

act main() {{
    let x = {lit}
    expect_{expected_type}(x)
}}
"""
    res = run_velo_check(source, tmp_path)
    assert res.returncode == 0, f"check failed for {lit} expecting {expected_type}:\n{res.stdout}\n{res.stderr}"


# ---------------------------------------------------------------------------
# 2. Explicit suffix overrides (strictness)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lit,expected_type", [
    ("0u64", "u64"),
    ("42u64", "u64"),
    ("0i64", "i64"),
    ("42i64", "i64"),
    ("0u8", "u8"),
    ("42u8", "u8"),
    ("0i8", "i8"),
    ("0u16", "u16"),
    ("0i16", "i16"),
    ("0u32", "u32"),
    ("0i32", "i32"),
    ("0usize", "usize"),
    ("0isize", "isize"),
])
def test_explicit_suffix_overrides_ladder(lit, expected_type, tmp_path):
    source = f"""use std.io

act expect_{expected_type}(v: {expected_type}) {{}}

act main() {{
    let x = {lit}
    expect_{expected_type}(x)
}}
"""
    res = run_velo_check(source, tmp_path)
    assert res.returncode == 0, f"check failed for {lit} with explicit suffix:\n{res.stdout}\n{res.stderr}"


@pytest.mark.parametrize("source,expected_msg", [
    ("act main() { let a: u8 = 0u16 }", "Cannot implicitly convert 'u16' to narrower type 'u8'"),
    ("act main() { let a: i32 = 0i64 }", "Cannot implicitly convert 'i64' to narrower type 'i32'"),
    ("act main() { let a: u32 = 0u64 }", "Cannot implicitly convert 'u64' to narrower type 'u32'"),
    ("act main() { let a: i8 = 0u8 }", "Cannot implicitly convert 'u8' to 'i8'"),
])
def test_suffixed_literals_reject_implicit_conversion(source, expected_msg, tmp_path):
    res = run_velo_check(source, tmp_path)
    assert res.returncode != 0, f"velo check accepted strict suffix violation: {source}"
    assert expected_msg in res.stdout or expected_msg in res.stderr


# ---------------------------------------------------------------------------
# 3. Contextual literal out-of-range diagnostics
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("target_type,lit", [
    ("u8", "256"),
    ("i8", "128"),
    ("i8", "-129"),
    ("u16", "65536"),
    ("i16", "32768"),
    ("i16", "-32769"),
    ("u32", "4294967296"),
    ("i32", "2147483648"),
    ("i32", "-2147483649"),
    ("i64", "9223372036854775808"),
    ("i64", "-9223372036854775809"),
])
def test_out_of_range_contextual_literal_rejected(target_type, lit, tmp_path):
    source = f"""act main() {{
    let a: {target_type} = {lit}
}}
"""
    res = run_velo_check(source, tmp_path)
    assert res.returncode != 0, f"accepted out of range literal {lit} for {target_type}"
    combined = res.stdout + res.stderr
    assert f"out of range for type '{target_type}'" in combined or "exceeds" in combined.lower()
