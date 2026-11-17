"""Tests for strict integer/float conversion and explicit cast enforcement (Task 46.1).

Covers:
- Safe widening within same signedness (i8->i16->i32->i64/isize, u8->u16->u32->u64/usize, f32->f64)
- Rejection of narrowing conversions without explicit cast 'as <type>'
- Rejection of signed/unsigned conversions without explicit cast 'as <type>'
- Contextual adaptation of unsuffixed integer literals within valid target range
- Compile-time diagnostic when unsuffixed integer literal exceeds target range
- Suffixed integer literals respecting strict type compatibility
- Struct field initialization and default initializers
- Function argument and return value type compatibility
- Floating-point narrowing and widening
"""
import os
import tempfile
import subprocess
from pathlib import Path
import pytest
from conftest import velo_exe

ROOT_DIR = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()


def run_velo_check(source_code: str) -> subprocess.CompletedProcess:
    """Helper to run `velo check` on a snippet."""
    with tempfile.NamedTemporaryFile("w", suffix=".vl", delete=False) as f:
        f.write(source_code)
        f_name = f.name
    try:
        res = subprocess.run([str(VELO_EXE), "check", f_name], capture_output=True, text=True)
        return res
    finally:
        Path(f_name).unlink(missing_ok=True)


class TestIntTypeConversions:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo.exe not built")

    def test_safe_unsigned_widening(self):
        code = """
        act main() -> i32 {
            let a: u8 = 10
            let b: u16 = a
            let c: u32 = b
            let d: u64 = c
            let e: usize = d
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected success, got {res.stdout}\n{res.stderr}"

    def test_safe_signed_widening(self):
        code = """
        act main() -> i32 {
            let a: i8 = 10
            let b: i16 = a
            let c: i32 = b
            let d: i64 = c
            let e: isize = d
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected success, got {res.stdout}\n{res.stderr}"

    def test_narrowing_variable_decl_rejected(self):
        code = """
        act main() -> i32 {
            let big: u64 = 42
            let small: u8 = big
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Cannot implicitly convert 'u64' to narrower type 'u8'. Use explicit cast 'as u8'." in res.stdout

    def test_narrowing_with_explicit_cast_accepted(self):
        code = """
        act main() -> i32 {
            let big: u64 = 42
            let small: u8 = big as u8
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected success, got {res.stdout}\n{res.stderr}"

    def test_signed_to_unsigned_rejected(self):
        code = """
        act main() -> i32 {
            let s: i32 = 10
            let u: u32 = s
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Cannot implicitly convert 'i32' to 'u32'. Use explicit cast 'as u32'." in res.stdout

    def test_unsigned_to_signed_rejected(self):
        code = """
        act main() -> i32 {
            let u: u32 = 10
            let s: i32 = u
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Cannot implicitly convert 'u32' to 'i32'. Use explicit cast 'as i32'." in res.stdout

    def test_signed_unsigned_explicit_cast_accepted(self):
        code = """
        act main() -> i32 {
            let s: i32 = 10
            let u: u32 = s as u32
            let s2: i32 = u as i32
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected success, got {res.stdout}\n{res.stderr}"

    def test_narrowing_assignment_rejected(self):
        code = """
        act main() -> i32 {
            mut small: u8 = 0
            let big: u64 = 100
            small = big
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Cannot implicitly convert 'u64' to narrower type 'u8'. Use explicit cast 'as u8'." in res.stdout

    def test_assignment_with_explicit_cast_accepted(self):
        code = """
        act main() -> i32 {
            mut small: u8 = 0
            let big: u64 = 100
            small = big as u8
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected success, got {res.stdout}\n{res.stderr}"

    def test_function_arg_narrowing_rejected(self):
        code = """
        act consume_u8(val: u8) {}
        act main() -> i32 {
            let val64: u64 = 5
            consume_u8(val64)
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Cannot implicitly convert 'u64' to narrower type 'u8'. Use explicit cast 'as u8'." in res.stdout

    def test_function_arg_cast_accepted(self):
        code = """
        act consume_u8(val: u8) {}
        act main() -> i32 {
            let val64: u64 = 5
            consume_u8(val64 as u8)
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected success, got {res.stdout}\n{res.stderr}"

    def test_return_narrowing_rejected(self):
        code = """
        act get_byte() -> u8 {
            let big: u64 = 25
            return big
        }
        act main() -> i32 { return 0 }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Cannot implicitly convert 'u64' to narrower type 'u8'. Use explicit cast 'as u8'." in res.stdout

    def test_struct_field_narrowing_rejected(self):
        code = """
        data Packet {
            header_len: u8
        }
        act main() -> i32 {
            let len: u64 = 12
            let p = Packet{ header_len: len }
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Cannot implicitly convert 'u64' to narrower type 'u8'. Use explicit cast 'as u8'." in res.stdout

    def test_struct_default_field_narrowing_rejected(self):
        code = """
        data Config {
            timeout_ms: u32 = 5000_u64
        }
        act main() -> i32 { return 0 }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Cannot implicitly convert 'u64' to narrower type 'u32'. Use explicit cast 'as u32'." in res.stdout


class TestIntegerLiteralAdaptation:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo.exe not built")

    def test_in_range_literals_adapt_successfully(self):
        code = """
        act main() -> i32 {
            let a: u8 = 255
            let b: i8 = -128
            let c: i8 = 127
            let d: u16 = 65535
            let e: i16 = -32768
            let f: usize = 0
            let g: u64 = 18446744073709551615
            let h: i64 = -9223372036854775808
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected success, got {res.stdout}\n{res.stderr}"

    def test_u8_literal_overflow_rejected(self):
        code = """
        act main() -> i32 {
            let a: u8 = 256
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Integer literal '256' out of range for type 'u8'" in res.stdout

    def test_u8_negative_literal_rejected(self):
        code = """
        act main() -> i32 {
            let a: u8 = -1
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Integer literal '-1' out of range for type 'u8'" in res.stdout

    def test_i8_literal_overflow_rejected(self):
        code = """
        act main() -> i32 {
            let a: i8 = 128
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Integer literal '128' out of range for type 'i8'" in res.stdout

    def test_i8_negative_literal_underflow_rejected(self):
        code = """
        act main() -> i32 {
            let a: i8 = -129
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Integer literal '-129' out of range for type 'i8'" in res.stdout

    def test_suffixed_literal_strictly_checked(self):
        code = """
        act main() -> i32 {
            let a: u8 = 10_u64
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Cannot implicitly convert 'u64' to narrower type 'u8'. Use explicit cast 'as u8'." in res.stdout


class TestFloatConversions:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo.exe not built")

    def test_float_widening_accepted(self):
        code = """
        act main() -> i32 {
            let a: f32 = 1.5
            let b: f64 = a
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected success, got {res.stdout}\n{res.stderr}"

    def test_float_narrowing_rejected(self):
        code = """
        act main() -> i32 {
            let big: f64 = 3.1415926535
            let small: f32 = big
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Cannot implicitly convert 'f64' to narrower type 'f32'. Use explicit cast 'as f32'." in res.stdout

    def test_float_narrowing_with_cast_accepted(self):
        code = """
        act main() -> i32 {
            let big: f64 = 3.1415926535
            let small: f32 = big as f32
            return 0
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected success, got {res.stdout}\n{res.stderr}"


class TestCallArgumentTypeChecking:
    """Matrix of function argument type mismatch checks (Phase 59: AUDIT-2026-11-08)."""
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo.exe not built")

    def test_fn_call_string_to_int_rejected(self):
        code = """
        act f(a: i32) {}
        act main() {
            let s: string = "hello"
            f(s)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 1: expected 'i32', got 'string'" in res.stdout

    def test_fn_call_float_to_int_rejected(self):
        code = """
        act f(a: i32) {}
        act main() {
            f(1.5)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 1: expected 'i32', got 'f32'" in res.stdout

    def test_fn_call_bool_to_int_rejected(self):
        code = """
        act f(a: i32) {}
        act main() {
            f(true)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 1: expected 'i32', got 'bool'" in res.stdout

    def test_fn_call_int_to_bool_rejected(self):
        code = """
        act g(a: bool) {}
        act main() {
            g(1)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 1: expected 'bool', got 'i32'" in res.stdout

    def test_fn_call_struct_to_int_rejected(self):
        code = """
        data S { x: i32 }
        act f(a: i32) {}
        act main() {
            mut s: S
            f(s)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 1: expected 'i32', got 'S'" in res.stdout

    def test_fn_call_pointer_to_int_rejected(self):
        code = """
        act f(a: i32) {}
        act main() {
            let p: @i32 = null
            f(p)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 1: expected 'i32', got '@i32'" in res.stdout


# ==============================================================================
# Phase 60: Condition Type Checking Red Baseline (Task 60.1)
# ==============================================================================

class TestConditionTypeChecking:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo.exe not built")

    def test_if_int_literal_condition_rejected(self):
        code = """
        act main() {
            if 1 {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'i32'" in res.stdout

    def test_if_string_literal_condition_rejected(self):
        code = """
        act main() {
            if "hello" {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'string'" in res.stdout

    def test_if_struct_condition_rejected(self):
        code = """
        data Point { x: i32 }
        act main() {
            let p = Point { x: 0 }
            if p {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'Point'" in res.stdout

    def test_if_pointer_condition_rejected(self):
        code = """
        act main() {
            let x: i32 = 10
            let p: @i32 = @x
            if p {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got '@i32'" in res.stdout

    def test_if_null_condition_rejected(self):
        code = """
        act main() {
            if null {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got '@void'" in res.stdout

    def test_if_float_condition_rejected(self):
        code = """
        act main() {
            if 1.5 {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'f32'" in res.stdout


