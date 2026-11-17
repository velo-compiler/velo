# tests/test_literal_property_fuzz.py
"""
Task 53.9: Property and fuzz coverage for Velo integer literal parsing.

Verifies:
1. Deterministic valid corpus (1,000 cases): compares Velo parser's decimal,
   hexadecimal, binary, and octal values against Python's arbitrary-precision
   integer model across boundary powers, random 64-bit values, underscores, and suffixes.
2. Malformed / fuzz corpus (250+ cases): verifies that malformed inputs
   (empty prefixes, invalid digits for base, 100+ digit inputs, Unicode numerals,
   overflows > UINT64_MAX, and suffix range violations) produce compile diagnostics
   and never crash the compiler.
"""

import os
import random
import subprocess
import tempfile
import pytest
from conftest import cc_dir, velo_exe

COMPILER = str(velo_exe())


def get_env():
    env = dict(os.environ)
    env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return env


# Compiler diagnostics are UTF-8, and this corpus deliberately feeds non-ASCII
# source (full-width digits, Arabic-Indic, Devanagari). Decoding with the
# ambient codec -- which `text=True` alone does -- raises UnicodeDecodeError on
# a cp1252 console inside subprocess's reader thread, which then yields
# stdout=None and turns a passing rejection case into a TypeError. Pin the
# codec and replace undecodable bytes so the harness never fails on encoding.
DIAGNOSTIC_ENCODING = "utf-8"


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
            encoding=DIAGNOSTIC_ENCODING,
            errors="replace",
            timeout=30,
        )


def check_velo_source(code: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "test.vl")
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
        return subprocess.run(
            [COMPILER, "check", src],
            env=get_env(),
            capture_output=True,
            text=True,
            encoding=DIAGNOSTIC_ENCODING,
            errors="replace",
            timeout=10,
        )


def test_valid_deterministic_corpus_matches_python():
    """Generates 1,000 deterministic valid integer literals across all 4 bases,

    embeds them into executable Velo assertions, and proves they equal Python's
    exact arbitrary-precision integer calculations.
    """
    rng = random.Random(42)
    assertions = []

    # 1. Powers of 2 from 2^0 to 2^63
    for p in range(64):
        val = 1 << p
        assertions.append(f"assert({val}u64 == {val}u64)")
        assertions.append(f"assert(0x{val:X}u64 == {val}u64)")
        assertions.append(f"assert(0b{val:b}u64 == {val}u64)")
        assertions.append(f"assert(0o{val:o}u64 == {val}u64)")

    # 2. Powers of 10 from 10^0 to 10^19
    for p in range(20):
        val = 10**p
        if val <= 0xFFFFFFFFFFFFFFFF:
            assertions.append(f"assert({val}u64 == {val}u64)")
            assertions.append(f"assert(0x{val:X}u64 == {val}u64)")

    # 3. Exact boundary values around 8, 16, 32, 64-bit boundaries
    boundaries = [
        0, 1, 2, 126, 127, 128, 254, 255, 256,
        32766, 32767, 32768, 65534, 65535, 65536,
        2147483646, 2147483647, 2147483648, 4294967294, 4294967295, 4294967296,
        9223372036854775806, 9223372036854775807, 9223372036854775808,
        18446744073709551614, 18446744073709551615
    ]
    for b in boundaries:
        assertions.append(f"assert({b}u64 == {b}u64)")
        assertions.append(f"assert(0x{b:X}u64 == {b}u64)")
        assertions.append(f"assert(0b{b:b}u64 == {b}u64)")
        assertions.append(f"assert(0o{b:o}u64 == {b}u64)")

    # 4. Underscore formatting across bases
    assertions.append("assert(1_000_000u64 == 1000000u64)")
    assertions.append("assert(18_446_744_073_709_551_615u64 == 18446744073709551615u64)")
    assertions.append("assert(0xDEAD_BEEF_CAFE_BABE_u64 == 0xDEADBEEFCAFEBABE_u64)")
    assertions.append("assert(0b1111_0000_1010_0101_u64 == 0b1111000010100101_u64)")
    assertions.append("assert(0o755_644_123_u64 == 0o755644123_u64)")

    # 5. Hex lowercase, uppercase, and mixed case
    hex_patterns = ["0xabcdef", "0xABCDEF", "0xAbCdEf", "0x1a2B3c4D", "0x00FF", "0x00000001"]
    for hp in hex_patterns:
        val = int(hp, 16)
        assertions.append(f"assert({hp}u64 == {val}u64)")

    # 6. Pseudorandom 64-bit integer values across all 4 bases
    # Fill up until we reach >= 1,000 assertions
    while len(assertions) < 1000:
        val = rng.randint(0, 0xFFFFFFFFFFFFFFFF)
        assertions.append(f"assert({val}u64 == {val}u64)")
        assertions.append(f"assert(0x{val:X}u64 == {val}u64)")
        assertions.append(f"assert(0b{val:b}u64 == {val}u64)")
        assertions.append(f"assert(0o{val:o}u64 == {val}u64)")

    total_cases = len(assertions)
    assert total_cases >= 1000, f"Expected at least 1000 cases, got {total_cases}"

    code = "act main() {\n    " + "\n    ".join(assertions) + "\n    io.println(\"ALL_OK\")\n}"
    res = run_velo_source(code)
    assert res.returncode == 0, f"Execution failed:\n{res.stdout}\n{res.stderr}"
    assert "ALL_OK" in res.stdout


def test_malformed_fuzz_corpus_produces_diagnostics_without_crash():
    """Tests 250+ malformed, overflowing, and edge-case literal strings.

    Ensures each produces a compile diagnostic and does not crash or hang.
    """
    fuzz_cases = []

    # 1. Empty prefixes
    fuzz_cases.extend(["0x", "0X", "0b", "0B", "0o", "0O"])

    # 2. Invalid digits for radix
    for d in ["2", "3", "5", "8", "9", "a", "F"]:
        fuzz_cases.append(f"0b{d}")
        fuzz_cases.append(f"0b10{d}01")
    for d in ["8", "9", "a", "b", "z", "F"]:
        fuzz_cases.append(f"0o{d}")
        fuzz_cases.append(f"0o77{d}1")
    for d in ["g", "G", "h", "H", "z", "Z", "k", "K", "m", "M"]:
        fuzz_cases.append(f"0x{d}")
        fuzz_cases.append(f"0x12{d}34")

    # 3. Overflow beyond UINT64_MAX (18446744073709551615)
    fuzz_cases.extend([
        "18446744073709551616",
        "18446744073709551617",
        "18446744073709551620",
        "18446744073709551700",
        "19000000000000000000",
        "20000000000000000000",
        "99999999999999999999",
        "0x10000000000000000",
        "0x10000000000000001",
        "0x100000000000000000",
        "0xFFFFFFFFFFFFFFFFF",
        "0xFFFFFFFFFFFFFFFFFF",
        "0b1" + "0" * 64,
        "0b1" + "0" * 65,
        "0b" + "1" * 65,
        "0b" + "1" * 70,
        "0o2" + "0" * 21,
        "0o7" + "7" * 22,
        "0o10000000000000000000000",
    ])

    # 4. Massive 100+ digit inputs
    fuzz_cases.extend([
        "9" * 100,
        "1" + "0" * 120,
        "5" * 150,
        "0x" + "F" * 100,
        "0x" + "a" * 120,
        "0x" + "1" * 200,
        "0b" + "1" * 100,
        "0b" + "1" * 200,
        "0b" + "1" * 250,
        "0o" + "7" * 100,
        "0o" + "7" * 120,
    ])

    # 5. Unicode numerals (must be rejected by lexer/parser)
    fuzz_cases.extend([
        "１２３",         # full-width digits
        "０ｘ１０",       # full-width hex
        "١٢٣٤",           # Arabic-Indic
        "१२३४",           # Devanagari
    ])

    # 6. Suffixed bounds violations
    # u8: [0, 255]
    fuzz_cases.extend(["256_u8", "257_u8", "300_u8", "65535_u8", "-1_u8", "-10_u8"])
    # i8: [-128, 127]
    fuzz_cases.extend(["128_i8", "129_i8", "255_i8", "300_i8", "-129_i8", "-130_i8", "-200_i8"])
    # u16: [0, 65535]
    fuzz_cases.extend(["65536_u16", "65537_u16", "70000_u16", "100000_u16", "-1_u16"])
    # i16: [-32768, 32767]
    fuzz_cases.extend(["32768_i16", "32769_i16", "40000_i16", "-32769_i16", "-40000_i16"])
    # u32: [0, 4294967295]
    fuzz_cases.extend(["4294967296_u32", "4294967297_u32", "5000000000_u32", "-1_u32"])
    # i32: [-2147483648, 2147483647]
    fuzz_cases.extend(["2147483648_i32", "2147483649_i32", "3000000000_i32", "-2147483649_i32", "-3000000000_i32"])
    # u64: [0, 18446744073709551615]
    fuzz_cases.extend(["18446744073709551616_u64", "19000000000000000000_u64", "-1_u64"])
    # i64: [-9223372036854775808, 9223372036854775807]
    fuzz_cases.extend(["9223372036854775808_i64", "10000000000000000000_i64", "-9223372036854775809_i64"])

    # Expand with algorithmic variations to reach 250+ cases
    rng = random.Random(1337)
    for _ in range(160):
        # Generate random base with random invalid char
        base_choice = rng.choice(["b", "o", "x"])
        if base_choice == "b":
            inv_digit = rng.choice(["2", "3", "4", "5", "6", "7", "8", "9", "a", "x"])
            fuzz_cases.append(f"0b{rng.randint(0, 1)}{inv_digit}{rng.randint(0, 1)}")
        elif base_choice == "o":
            inv_digit = rng.choice(["8", "9", "a", "b", "c", "x"])
            fuzz_cases.append(f"0o{rng.randint(0, 7)}{inv_digit}{rng.randint(0, 7)}")
        else:
            inv_digit = rng.choice(["g", "h", "k", "m", "z", "Y"])
            fuzz_cases.append(f"0x{rng.randint(0, 9)}{inv_digit}{rng.randint(0, 9)}")

    assert len(fuzz_cases) >= 250, f"Expected at least 250 fuzz cases, got {len(fuzz_cases)}"

    # Test each fuzz case individually to ensure proper rejection and zero crashes
    for case in fuzz_cases:
        code = f"act main() {{\n    let x = {case}\n}}\n"
        res = check_velo_source(code)
        # Security invariant: compile error, never success, never crash
        assert res.returncode != 0, f"Malformed input '{case}' unexpectedly passed compilation!"
        # Check that compiler didn't crash (Windows crash codes e.g. 0xC0000005 = 3221225477)
        assert res.returncode not in (-11, -6, 3221225477, -1073741819), f"Compiler crashed on input '{case}'!"
        out = res.stdout + res.stderr
        assert len(out) > 0, f"Compiler produced no diagnostics for malformed input '{case}'!"
