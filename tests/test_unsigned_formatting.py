"""
tests/test_unsigned_formatting.py — Test Matrix for Unsigned Integer Formatting (Phase 57)

Audit ID: AUDIT-2026-11-06
Severity: P0 — silent wrong output
Verifies formatting of all unsigned integer types (u8, u16, u32, u64, usize)
across boundary values (0, 1, max-1, max) through all formatting paths:
- io.println(val)
- io.print(val)
- String interpolation "{val}"
- Emitted C format specifiers and casts (%llu / %zu vs %lld)

Establishes the Red Baseline for Phase 57 (Task 57.1).
"""

import os
import subprocess
import tempfile
from pathlib import Path
import pytest


def get_build_env():
    """Returns an environment with ucrt64 GCC in PATH for compiling generated C."""
    env = dict(os.environ)
    ucrt_bin = r"C:\msys64\ucrt64\bin"
    if os.path.exists(ucrt_bin) and ucrt_bin not in env.get("PATH", ""):
        env["PATH"] = ucrt_bin + ";" + env.get("PATH", "")
    return env


def run_velo_source(source_code: str, timeout: float = 2.0) -> subprocess.CompletedProcess:
    """Compiles Velo source to an executable using bin/velo.exe build, then executes directly."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_path = Path(tmp_dir) / "test.vl"
        exe_path = Path(tmp_dir) / "test.exe"
        src_path.write_text(source_code, encoding="utf-8")

        build_res = subprocess.run(
            ["bin/velo.exe", "build", str(src_path), "-o", str(exe_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=get_build_env(),
            cwd=Path.cwd()
        )
        if build_res.returncode != 0:
            return build_res

        try:
            return subprocess.run(
                [str(exe_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
                cwd=Path.cwd()
            )
        except subprocess.TimeoutExpired as e:
            pytest.fail(f"Execution timed out after {timeout}s: {e}")


def emit_c_velo_source(source_code: str) -> str:
    """Emits C source code using bin/velo.exe emit-c."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_path = Path(tmp_dir) / "test.vl"
        c_path = Path(tmp_dir) / "test.c"
        src_path.write_text(source_code, encoding="utf-8")

        res = subprocess.run(
            ["bin/velo.exe", "emit-c", str(src_path), "-o", str(c_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=Path.cwd()
        )
        assert res.returncode == 0, f"emit-c failed:\nstdout: {res.stdout}\nstderr: {res.stderr}"
        return c_path.read_text(encoding="utf-8")


UNSIGNED_MATRIX = [
    # (type, label, literal_val, expected_str)
    # u8 (0 .. 255)
    ("u8", "zero", "0u8", "0"),
    ("u8", "one", "1u8", "1"),
    ("u8", "max_minus_1", "254u8", "254"),
    ("u8", "max", "255u8", "255"),

    # u16 (0 .. 65535)
    ("u16", "zero", "0u16", "0"),
    ("u16", "one", "1u16", "1"),
    ("u16", "max_minus_1", "65534u16", "65534"),
    ("u16", "max", "65535u16", "65535"),

    # u32 (0 .. 4294967295)
    ("u32", "zero", "0u32", "0"),
    ("u32", "one", "1u32", "1"),
    ("u32", "max_minus_1", "4294967294u32", "4294967294"),
    ("u32", "max", "4294967295u32", "4294967295"),

    # u64 (0 .. 18446744073709551615)
    ("u64", "zero", "0u64", "0"),
    ("u64", "one", "1u64", "1"),
    ("u64", "max_minus_1", "18446744073709551614u64", "18446744073709551614"),
    ("u64", "max", "18446744073709551615u64", "18446744073709551615"),

    # usize (0 .. 18446744073709551615 on 64-bit target)
    ("usize", "zero", "0usize", "0"),
    ("usize", "one", "1usize", "1"),
    ("usize", "max_minus_1", "18446744073709551614usize", "18446744073709551614"),
    ("usize", "max", "18446744073709551615usize", "18446744073709551615"),
]


# ==============================================================================
# 1. io.println(val) Unsigned Matrix
# ==============================================================================

@pytest.mark.parametrize("type_name,label,literal_val,expected_str", UNSIGNED_MATRIX)
def test_io_println_unsigned_variable(type_name, label, literal_val, expected_str):
    """Verify io.println(var) formats exact decimal string for all unsigned types."""
    code = f"""use sys.io
act main() -> i32 {{
    let val: {type_name} = {literal_val}
    io.println(val)
    return 0
}}
"""
    res = run_velo_source(code)
    assert res.returncode == 0
    actual = res.stdout.strip()
    # Security gate: unsigned value must never have a '-' prefix
    assert not actual.startswith("-"), f"Unsigned value wrapped negative: got {actual}"
    assert actual == expected_str, f"Mismatch for {type_name} {label}: expected {expected_str}, got {actual}"


@pytest.mark.parametrize("type_name,label,literal_val,expected_str", UNSIGNED_MATRIX)
def test_io_println_unsigned_literal(type_name, label, literal_val, expected_str):
    """Verify io.println(literal) formats exact decimal string without variable."""
    code = f"""use sys.io
act main() -> i32 {{
    io.println({literal_val})
    return 0
}}
"""
    res = run_velo_source(code)
    assert res.returncode == 0
    actual = res.stdout.strip()
    assert not actual.startswith("-"), f"Unsigned literal wrapped negative: got {actual}"
    assert actual == expected_str, f"Mismatch for {literal_val}: expected {expected_str}, got {actual}"


# ==============================================================================
# 2. io.print(val) Unsigned Matrix
# ==============================================================================

@pytest.mark.parametrize("type_name,label,literal_val,expected_str", UNSIGNED_MATRIX)
def test_io_print_unsigned_variable(type_name, label, literal_val, expected_str):
    """Verify io.print(var) formats exact decimal string without trailing newline."""
    code = f"""use sys.io
act main() -> i32 {{
    let val: {type_name} = {literal_val}
    io.print(val)
    return 0
}}
"""
    res = run_velo_source(code)
    assert res.returncode == 0
    actual = res.stdout
    assert not actual.startswith("-"), f"Unsigned value wrapped negative: got {actual}"
    assert actual == expected_str, f"Mismatch for {type_name} {label}: expected {expected_str}, got {actual}"


# ==============================================================================
# 3. String Interpolation "{val}" Unsigned Matrix
# ==============================================================================

@pytest.mark.parametrize("type_name,label,literal_val,expected_str", UNSIGNED_MATRIX)
def test_interpolation_unsigned_variable(type_name, label, literal_val, expected_str):
    """Verify "{val}" string interpolation formats exact decimal string."""
    code = f"""use sys.io
act main() -> i32 {{
    let val: {type_name} = {literal_val}
    io.println("val={{val}}")
    return 0
}}
"""
    res = run_velo_source(code)
    assert res.returncode == 0
    actual = res.stdout.strip()
    expected_line = f"val={expected_str}"
    assert not "val=-" in actual, f"Unsigned interpolation wrapped negative: got {actual}"
    assert actual == expected_line, f"Mismatch for {type_name} {label}: expected {expected_line}, got {actual}"


# ==============================================================================
# 4. Emitted C Security Invariant: No Signed Conversion for Unsigned Types
# ==============================================================================

@pytest.mark.parametrize("type_name", ["u8", "u16", "u32", "u64", "usize"])
def test_emitted_c_no_signed_conversion_for_unsigned(type_name):
    """Security Invariant: Emitted C must use unsigned format/cast, not %lld or (long long)."""
    code = f"""use sys.io
act main() -> i32 {{
    let val: {type_name} = 0{type_name}
    io.println(val)
    return 0
}}
"""
    c_code = emit_c_velo_source(code)
    # The security gate requires unsigned specifier (%llu or %zu), never signed %lld
    assert "printf(\"%lld" not in c_code, f"Emitted signed %lld for unsigned type {type_name}"
    assert "(long long)" not in c_code, f"Emitted signed (long long) cast for unsigned type {type_name}"


# ==============================================================================
# 5. Emitted C Security Invariant: String Interpolation Format/Argument Split
# ==============================================================================

@pytest.mark.parametrize("type_name", ["u8", "u16", "u32", "u64", "usize"])
def test_emitted_c_no_signed_conversion_for_unsigned_interpolation(type_name):
    """Security Invariant: String interpolation of unsigned types must emit %llu / (unsigned long long)."""
    code = f"""use sys.io
act main() -> i32 {{
    let val: {type_name} = 0{type_name}
    io.println("val={{val}}")
    return 0
}}
"""
    c_code = emit_c_velo_source(code)
    assert "%llu" in c_code, f"Missing unsigned %llu specifier for {type_name}"
    assert "(unsigned long long)" in c_code, f"Missing unsigned (unsigned long long) cast for {type_name}"
    assert "%lld" not in c_code, f"Emitted signed %lld for unsigned interpolation of {type_name}"
    assert "(long long)" not in c_code, f"Emitted signed (long long) cast for unsigned interpolation of {type_name}"


@pytest.mark.parametrize("type_name", ["i8", "i16", "i32", "i64", "isize"])
def test_emitted_c_signed_regression_interpolation(type_name):
    """Signed Regression: String interpolation of signed types must emit %lld / (long long)."""
    code = f"""use sys.io
act main() -> i32 {{
    let val: {type_name} = 0{type_name}
    io.println("val={{val}}")
    return 0
}}
"""
    c_code = emit_c_velo_source(code)
    assert "%lld" in c_code, f"Missing signed %lld specifier for {type_name}"
    assert "(long long)" in c_code, f"Missing signed (long long) cast for {type_name}"
    assert "%llu" not in c_code, f"Emitted unsigned %llu for signed interpolation of {type_name}"
    assert "(unsigned long long)" not in c_code, f"Emitted unsigned (unsigned long long) cast for signed interpolation of {type_name}"


def test_emitted_c_mixed_interpolation_alignment():
    """Security Gate: Mixed interpolation must maintain exact 1:1 format and argument alignment."""
    code = """use sys.io
act main() -> i32 {
    let u: u64 = 18446744073709551615u64
    let s: i64 = -42i64
    io.println("u={u}, s={s}")
    return 0
}
"""
    c_code = emit_c_velo_source(code)
    assert "printf(\"u=%llu, s=%lld\\n\", (unsigned long long)(u), (long long)(s))" in c_code
