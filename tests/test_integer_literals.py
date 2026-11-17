# Phase 53: Boundary conformance tests for unsuffixed integer literal width and overflow.
#
# Audit ID: AUDIT-2026-11-02
# Goal: Pin the expected mathematical values, non-wrapping semantics, and compile-time
# overflow rejection (> u64) across all four bases (decimal, hex, binary, octal).
import os
import subprocess
import pytest
from pathlib import Path
from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()


def get_env():
    env = os.environ.copy()
    if cc_dir() not in env.get("PATH", ""):
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return env


def run_velo(args, cwd=REPO_ROOT):
    return subprocess.run(
        [str(VELO_EXE), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env()
    )


# ---------------------------------------------------------------------------
# 1. 32-bit non-wrapping and in-range boundaries across all bases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lit,expected", [
    ("0", 0),
    ("0x0", 0),
    ("0b0", 0),
    ("0o0", 0),
    ("1", 1),
    ("0x1", 1),
    ("0b1", 1),
    ("0o1", 1),
    ("2147483647", 2147483647),
    ("0x7FFFFFFF", 2147483647),
    ("0b01111111_11111111_11111111_11111111", 2147483647),
    ("0o17777777777", 2147483647),
])
def test_integer_literal_32bit_in_range_values(lit, expected, tmp_path):
    source = (
        "use std.io\n\n"
        "act main() {\n"
        f"    let x = {lit}\n"
        "    println_i64(x as i64)\n"
        "}\n"
    )
    probe = tmp_path / "in_range.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")

    res = run_velo(["run", str(probe)])
    assert res.returncode == 0, f"run failed for {lit}:\n{res.stderr}\n{res.stdout}"
    assert res.stdout.strip() == str(expected), f"value mismatch for {lit}:\n{res.stdout!r}"


# ---------------------------------------------------------------------------
# 2. Values in (INT32_MAX, UINT32_MAX] must NOT wrap to negative
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lit,expected", [
    ("2147483648", 2147483648),
    ("0x80000000", 2147483648),
    ("0b10000000_00000000_00000000_00000000", 2147483648),
    ("0o20000000000", 2147483648),
    ("4294967295", 4294967295),
    ("0xFFFFFFFF", 4294967295),
    ("0b11111111_11111111_11111111_11111111", 4294967295),
    ("0o37777777777", 4294967295),
])
def test_integer_literal_32bit_overflow_must_not_wrap_negative(lit, expected, tmp_path):
    source = (
        "use std.io\n\n"
        "act main() {\n"
        f"    let x = {lit}\n"
        "    assert(x > 0)\n"
        "    println_u64(x as u64)\n"
        "}\n"
    )
    probe = tmp_path / "nowrap32.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")

    res = run_velo(["run", str(probe)])
    assert res.returncode == 0, f"run failed for {lit} (wrapped to negative?):\n{res.stderr}\n{res.stdout}"
    assert res.stdout.strip() == str(expected), f"value mismatch for {lit}:\n{res.stdout!r}"


# ---------------------------------------------------------------------------
# 3. 64-bit boundaries (INT64_MAX, UINT64_MAX)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lit,expected", [
    # INT64_MAX (9223372036854775807)
    ("9223372036854775807", 9223372036854775807),
    ("0x7FFFFFFFFFFFFFFF", 9223372036854775807),
    ("0b01111111_11111111_11111111_11111111_11111111_11111111_11111111_11111111", 9223372036854775807),
    ("0o777777777777777777777", 9223372036854775807),
    # INT64_MAX + 1 (9223372036854775808)
    ("9223372036854775808", 9223372036854775808),
    ("0x8000000000000000", 9223372036854775808),
    ("0b10000000_00000000_00000000_00000000_00000000_00000000_00000000_00000000", 9223372036854775808),
    ("0o1000000000000000000000", 9223372036854775808),
    # UINT64_MAX (18446744073709551615)
    ("18446744073709551615", 18446744073709551615),
    ("0xFFFFFFFFFFFFFFFF", 18446744073709551615),
    ("0b11111111_11111111_11111111_11111111_11111111_11111111_11111111_11111111", 18446744073709551615),
    ("0o1777777777777777777777", 18446744073709551615),
])
def test_integer_literal_64bit_boundaries(lit, expected, tmp_path):
    source = (
        "use std.io\n\n"
        "act main() {\n"
        f"    let x = {lit}\n"
        "    assert(x > 0)\n"
        "    println_u64(x as u64)\n"
        "}\n"
    )
    probe = tmp_path / "nowrap64.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")

    res = run_velo(["run", str(probe)])
    assert res.returncode == 0, f"run failed for {lit}:\n{res.stderr}\n{res.stdout}"
    assert res.stdout.strip() == str(expected), f"value mismatch for {lit}:\n{res.stdout!r}"


# ---------------------------------------------------------------------------
# 4. Negative minimums
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lit,expected", [
    ("-2147483648", -2147483648),
    ("-9223372036854775807 - 1", -9223372036854775808),
])
def test_integer_literal_negative_minimums(lit, expected, tmp_path):
    source = (
        "use std.io\n\n"
        "act main() {\n"
        f"    let x: i64 = {lit}\n"
        "    println_i64(x)\n"
        "}\n"
    )
    probe = tmp_path / "neg_min.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")

    res = run_velo(["run", str(probe)])
    assert res.returncode == 0, f"run failed for {lit}:\n{res.stderr}\n{res.stdout}"
    assert res.stdout.strip() == str(expected), f"value mismatch for {lit}:\n{res.stdout!r}"


# ---------------------------------------------------------------------------
# 5. Overflows above UINT64_MAX (> u64) must be compile-time errors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lit", [
    "18446744073709551616",
    "99999999999999999999999999999999",
    "0x10000000000000000",
    "0x1_0000_0000_0000_0000",
    "0b1_0000000000000000_0000000000000000_0000000000000000_0000000000000000",
    "0o2000000000000000000000",
])
def test_integer_literal_overflow_above_u64_rejected(lit, tmp_path):
    source = (
        "use std.io\n\n"
        "act main() {\n"
        f"    let x = {lit}\n"
        "}\n"
    )
    probe = tmp_path / "overflow_u64.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")

    res = run_velo(["check", str(probe)])
    assert res.returncode != 0, f"velo check accepted literal exceeding u64: {lit}"
    combined = (res.stdout + res.stderr).lower()
    assert "overflow" in combined or "out of range" in combined or "too large" in combined, (
        f"diagnostic did not mention overflow for {lit}:\n{res.stdout}\n{res.stderr}"
    )


# ---------------------------------------------------------------------------
# 6. Range loop with endpoint above INT32_MAX must not wrap
# ---------------------------------------------------------------------------


def test_range_loop_endpoint_above_int32_max(tmp_path):
    source = (
        "use std.io\n\n"
        "act main() {\n"
        "    mut count = 0\n"
        "    loop i in 0..3000000000 {\n"
        "        count += 1\n"
        "        if count >= 3 { break }\n"
        "    }\n"
        "    println_i64(count as i64)\n"
        "}\n"
    )
    probe = tmp_path / "range_endpoint.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")

    res = run_velo(["run", str(probe)])
    assert res.returncode == 0, f"run failed:\n{res.stderr}\n{res.stdout}"
    assert res.stdout.strip() == "3", f"range loop executed {res.stdout.strip()} times (expected 3)"
