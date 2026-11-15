"""
tests/test_call_arguments.py — Function/Method Call Argument Type Checking Test Matrix (Phase 59)

Audit ID: AUDIT-2026-11-08
Severity: P1 — checker accepts invalid programs; implicit truncation

Covers:
- Free function argument type checking across all type families
- Method and UFCS argument type checking
- Extern function call argument type checking
- Generic function instantiation argument type checking
- Arity checking (too few and too many arguments)
- Control group: valid arguments and explicit casts ('as <type>') must pass

Establishes the Red Baseline for Phase 59 (Task 59.1).
"""

import os
import subprocess
import tempfile
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).parent.parent.resolve()
VELO_EXE = ROOT_DIR / "bin" / ("velo.exe" if os.name == "nt" else "velo")
if not VELO_EXE.exists() and (ROOT_DIR / "bin" / "velo.exe").exists():
    VELO_EXE = ROOT_DIR / "bin" / "velo.exe"


def run_velo_check(source_code: str) -> subprocess.CompletedProcess:
    """Helper to run `velo check` on a temporary source file."""
    with tempfile.NamedTemporaryFile("w", suffix=".vl", delete=False) as f:
        f.write(source_code)
        f_name = f.name
    try:
        res = subprocess.run([str(VELO_EXE), "check", f_name], capture_output=True, text=True)
        return res
    finally:
        Path(f_name).unlink(missing_ok=True)


# ==============================================================================
# 1. Free Function Argument Type Mismatches (Red Baseline Matrix)
# ==============================================================================

class TestFreeFunctionArgTypeMismatches:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_string_to_int_param_rejected(self):
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

    def test_float_to_int_param_rejected(self):
        code = """
        act f(a: i32) {}
        act main() {
            f(1.5)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 1: expected 'i32', got 'f32'" in res.stdout

    def test_float_var_to_int_param_rejected(self):
        code = """
        act f(a: i32) {}
        act main() {
            let x: f64 = 3.14
            f(x)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 1: expected 'i32', got 'f64'" in res.stdout

    def test_bool_to_int_param_rejected(self):
        code = """
        act f(a: i32) {}
        act main() {
            f(true)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 1: expected 'i32', got 'bool'" in res.stdout

    def test_int_to_bool_param_rejected(self):
        code = """
        act g(b: bool) {}
        act main() {
            g(1)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 1: expected 'bool', got 'i32'" in res.stdout

    def test_struct_to_int_param_rejected(self):
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

    def test_pointer_to_int_param_rejected(self):
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

    def test_int_to_string_param_rejected(self):
        code = """
        act f(s: string) {}
        act main() {
            f(42)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 1: expected 'string', got 'i32'" in res.stdout

    def test_int_to_pointer_param_rejected(self):
        code = """
        act f(p: @i32) {}
        act main() {
            f(42)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 1: expected '@i32', got 'i32'" in res.stdout

    def test_struct_mismatch_param_rejected(self):
        code = """
        data Alpha { a: i32 }
        data Beta { b: i32 }
        act f(x: Alpha) {}
        act main() {
            mut b: Beta
            f(b)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 1: expected 'Alpha', got 'Beta'" in res.stdout

    def test_pointer_type_mismatch_param_rejected(self):
        code = """
        act f(p: @i32) {}
        act main() {
            let q: @f64 = null
            f(q)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 1: expected '@i32', got '@f64'" in res.stdout

    def test_string_to_bool_param_rejected(self):
        code = """
        act f(b: bool) {}
        act main() {
            f("true")
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 1: expected 'bool', got 'string'" in res.stdout


# ==============================================================================
# 2. Method and UFCS Argument Type Mismatches
# ==============================================================================

class TestMethodArgTypeMismatches:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_method_string_to_int_param_rejected(self):
        code = """
        data Point { x: i32 }
        act show(self: @Point, a: i32) {}
        act main() {
            mut pt: Point
            let s: string = "bad"
            pt.show(s)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 1: expected 'i32', got 'string'" in res.stdout

    def test_method_float_to_int_param_rejected(self):
        code = """
        data Point { x: i32 }
        act show(self: @Point, a: i32) {}
        act main() {
            mut pt: Point
            pt.show(1.5)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 1: expected 'i32', got 'f32'" in res.stdout

    def test_method_struct_to_int_param_rejected(self):
        code = """
        data Point { x: i32 }
        data Other { val: i32 }
        act show(self: @Point, a: i32) {}
        act main() {
            mut pt: Point
            mut ot: Other
            pt.show(ot)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 1: expected 'i32', got 'Other'" in res.stdout


# ==============================================================================
# 3. Extern Function Call Argument Type Mismatches
# ==============================================================================

class TestExternArgTypeMismatches:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_extern_string_to_int_param_rejected(self):
        code = """
        extern act c_putchar(c: i32) -> i32
        act main() {
            let s: string = "x"
            c_putchar(s)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 1: expected 'i32', got 'string'" in res.stdout

    def test_extern_pointer_to_int_param_rejected(self):
        code = """
        extern act c_putchar(c: i32) -> i32
        act main() {
            let p: @i32 = null
            c_putchar(p)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 1: expected 'i32', got '@i32'" in res.stdout


# ==============================================================================
# 4. Generic Function Call Argument Type Mismatches
# ==============================================================================

class TestGenericArgTypeMismatches:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_generic_fixed_param_mismatch_rejected(self):
        code = """
        act pair_work[T](val: T, tag: i32) {}
        act main() {
            let s: string = "wrong"
            pair_work(100, s)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection, but check passed: {res.stdout}"
        assert "Type mismatch in call argument 2: expected 'i32', got 'string'" in res.stdout


# ==============================================================================
# 5. Arity Checks (Too Few / Too Many Arguments)
# ==============================================================================

class TestCallArityChecks:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_free_fn_too_few_args_rejected(self):
        code = """
        act f(a: i32, b: i32) {}
        act main() {
            f(10)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in function call" in res.stdout

    def test_free_fn_too_many_args_rejected(self):
        code = """
        act f(a: i32) {}
        act main() {
            f(10, 20)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in function call" in res.stdout

    def test_method_too_few_args_rejected(self):
        code = """
        data Item { id: i32 }
        act configure(self: @Item, a: i32, b: i32) {}
        act main() {
            mut it: Item
            it.configure(10)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in method call" in res.stdout

    def test_method_too_many_args_rejected(self):
        code = """
        data Item { id: i32 }
        act configure(self: @Item, a: i32) {}
        act main() {
            mut it: Item
            it.configure(10, 20)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in method call" in res.stdout

    def test_extern_too_few_args_rejected(self):
        code = """
        extern act ext_add(a: i32, b: i32) -> i32
        act main() {
            ext_add(10)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in function call" in res.stdout

    def test_extern_too_many_args_rejected(self):
        code = """
        extern act ext_add(a: i32, b: i32) -> i32
        act main() {
            ext_add(10, 20, 30)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in function call" in res.stdout

    def test_free_fn_zero_args_to_one_arg_rejected(self):
        code = """
        act f(a: i32) {}
        act main() {
            f()
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in function call" in res.stdout

    def test_free_fn_two_args_to_one_arg_rejected(self):
        code = """
        act f(a: i32) {}
        act main() {
            f(10, 20)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in function call" in res.stdout

    def test_free_fn_one_arg_to_zero_arg_rejected(self):
        code = """
        act f() {}
        act main() {
            f(10)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in function call" in res.stdout

    def test_free_fn_zero_args_to_zero_arg_accepted(self):
        code = """
        act f() {}
        act main() {
            f()
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_method_zero_args_to_one_arg_rejected(self):
        code = """
        data Item { id: i32 }
        act show(self: @Item, a: i32) {}
        act main() {
            mut it: Item
            it.show()
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in method call" in res.stdout

    def test_method_two_args_to_one_arg_rejected(self):
        code = """
        data Item { id: i32 }
        act show(self: @Item, a: i32) {}
        act main() {
            mut it: Item
            it.show(10, 20)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in method call" in res.stdout

    def test_method_one_arg_to_zero_arg_rejected(self):
        code = """
        data Item { id: i32 }
        act get_id(self: @Item) -> i32 { return self.id }
        act main() {
            mut it: Item
            it.get_id(10)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in method call" in res.stdout

    def test_method_zero_args_to_zero_arg_accepted(self):
        code = """
        data Item { id: i32 }
        act get_id(self: @Item) -> i32 { return self.id }
        act main() {
            mut it: Item
            it.get_id()
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_ufcs_method_as_free_fn_zero_args_rejected(self):
        code = """
        data Item { id: i32 }
        act show(self: @Item, a: i32) {}
        act main() {
            show()
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in function call" in res.stdout

    def test_ufcs_method_as_free_fn_one_arg_rejected(self):
        code = """
        data Item { id: i32 }
        act show(self: @Item, a: i32) {}
        act main() {
            mut it: Item
            show(@it)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in function call" in res.stdout

    def test_ufcs_method_as_free_fn_three_args_rejected(self):
        code = """
        data Item { id: i32 }
        act show(self: @Item, a: i32) {}
        act main() {
            mut it: Item
            show(@it, 10, 20)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in function call" in res.stdout

    def test_ufcs_method_as_free_fn_exact_args_accepted(self):
        code = """
        data Item { id: i32 }
        act show(self: @Item, a: i32) {}
        act main() {
            mut it: Item
            show(@it, 10)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_ufcs_free_fn_as_method_too_few_args_rejected(self):
        code = """
        act add(a: i32, b: i32) -> i32 { return a + b }
        act main() {
            let x = 10.add()
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in method call" in res.stdout

    def test_ufcs_free_fn_as_method_too_many_args_rejected(self):
        code = """
        act add(a: i32, b: i32) -> i32 { return a + b }
        act main() {
            let x = 10.add(20, 30)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in method call" in res.stdout

    def test_ufcs_free_fn_as_method_exact_args_accepted(self):
        code = """
        act add(a: i32, b: i32) -> i32 { return a + b }
        act main() {
            let x = 10.add(20)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_extern_zero_args_to_one_arg_rejected(self):
        code = """
        extern act ext_one(a: i32) -> i32
        act main() {
            ext_one()
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in function call" in res.stdout

    def test_extern_two_args_to_one_arg_rejected(self):
        code = """
        extern act ext_one(a: i32) -> i32
        act main() {
            ext_one(10, 20)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in function call" in res.stdout

    def test_extern_zero_args_to_two_args_rejected(self):
        code = """
        extern act ext_two(a: i32, b: i32) -> i32
        act main() {
            ext_two()
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in function call" in res.stdout

    def test_extern_exact_args_accepted(self):
        code = """
        extern act ext_two(a: i32, b: i32) -> i32
        act main() {
            ext_two(10, 20)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_sizeof_zero_args_rejected(self):
        code = """
        act main() {
            let s = sizeof()
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "sizeof takes exactly 1 argument" in res.stdout

    def test_sizeof_two_args_rejected(self):
        code = """
        act main() {
            let s = sizeof(i32, i64)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "sizeof takes exactly 1 argument" in res.stdout

    def test_sizeof_exact_one_arg_accepted(self):
        code = """
        act main() {
            let s = sizeof(i32)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0


# ==============================================================================
# 6. Control Group: Valid Argument Types and Explicit Casts Must Pass
# ==============================================================================

class TestCallArgValidControlGroup:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_valid_exact_types_accepted(self):
        code = """
        act f(a: i32, b: string, c: bool) {}
        act main() {
            let s: string = "ok"
            f(42, s, true)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected success, got {res.stdout}\n{res.stderr}"

    def test_explicit_cast_accepted(self):
        code = """
        act f(a: i32) {}
        act main() {
            f(1.5 as i32)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected success, got {res.stdout}\n{res.stderr}"

    def test_safe_widening_arg_accepted(self):
        code = """
        act f(a: i64) {}
        act main() {
            let x: i32 = 100
            f(x)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected success, got {res.stdout}\n{res.stderr}"


# ==============================================================================
# 7. Task 59.4: Guard Literal Adaptation Against Truncation & Type Invariants
# ==============================================================================

class TestLiteralAdaptationGuards:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_float_literal_to_i32_rejected(self):
        code = """
        act f(a: i32) {}
        act main() {
            f(1.5)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'i32', got 'f32'" in res.stdout

    def test_float_literal_to_i64_rejected(self):
        code = """
        act f(a: i64) {}
        act main() {
            f(3.14)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'i64', got 'f32'" in res.stdout

    def test_float_literal_to_u8_rejected(self):
        code = """
        act f(a: u8) {}
        act main() {
            f(2.5)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'u8', got 'f32'" in res.stdout

    def test_float_literal_to_u32_rejected(self):
        code = """
        act f(a: u32) {}
        act main() {
            f(0.5)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'u32', got 'f32'" in res.stdout

    def test_int_literal_to_bool_one_rejected(self):
        code = """
        act g(a: bool) {}
        act main() {
            g(1)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'bool', got 'i32'" in res.stdout

    def test_int_literal_to_bool_zero_rejected(self):
        code = """
        act g(a: bool) {}
        act main() {
            g(0)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'bool', got 'i32'" in res.stdout

    def test_int_literal_to_bool_negative_rejected(self):
        code = """
        act g(a: bool) {}
        act main() {
            g(-1)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'bool', got 'i32'" in res.stdout

    def test_bool_literal_to_int_true_rejected(self):
        code = """
        act f(a: i32) {}
        act main() {
            f(true)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'i32', got 'bool'" in res.stdout

    def test_bool_literal_to_int_false_rejected(self):
        code = """
        act f(a: i32) {}
        act main() {
            f(false)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'i32', got 'bool'" in res.stdout

    def test_negative_int_to_u8_rejected(self):
        code = """
        act f(a: u8) {}
        act main() {
            f(-1)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Integer literal '-1' out of range for type 'u8'" in res.stdout

    def test_negative_int_to_u16_rejected(self):
        code = """
        act f(a: u16) {}
        act main() {
            f(-1)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Integer literal '-1' out of range for type 'u16'" in res.stdout

    def test_negative_int_to_u32_rejected(self):
        code = """
        act f(a: u32) {}
        act main() {
            f(-1)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Integer literal '-1' out of range for type 'u32'" in res.stdout

    def test_negative_int_to_u64_rejected(self):
        code = """
        act f(a: u64) {}
        act main() {
            f(-1)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Integer literal '-1' out of range for type 'u64'" in res.stdout

    def test_negative_int_out_of_range_i8_rejected(self):
        code = """
        act f(a: i8) {}
        act main() {
            f(-129)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Integer literal '-129' out of range for type 'i8'" in res.stdout

    def test_negative_int_out_of_range_i16_rejected(self):
        code = """
        act f(a: i16) {}
        act main() {
            f(-32769)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Integer literal '-32769' out of range for type 'i16'" in res.stdout

    def test_negative_int_out_of_range_i32_rejected(self):
        code = """
        act f(a: i32) {}
        act main() {
            f(-2147483649)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "out of range for type 'i32'" in res.stdout
        assert "-2147483649" in res.stdout

    def test_negative_int_in_range_i8_accepted(self):
        code = """
        act f(a: i8) {}
        act main() {
            f(-128)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_negative_int_in_range_i16_accepted(self):
        code = """
        act f(a: i16) {}
        act main() {
            f(-32768)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_negative_int_in_range_i32_accepted(self):
        code = """
        act f(a: i32) {}
        act main() {
            f(-2147483648)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_positive_int_out_of_range_i8_rejected(self):
        code = """
        act f(a: i8) {}
        act main() {
            f(128)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Integer literal '128' out of range for type 'i8'" in res.stdout

    def test_positive_int_out_of_range_u8_rejected(self):
        code = """
        act f(a: u8) {}
        act main() {
            f(256)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Integer literal '256' out of range for type 'u8'" in res.stdout

    def test_positive_int_out_of_range_i16_rejected(self):
        code = """
        act f(a: i16) {}
        act main() {
            f(32768)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Integer literal '32768' out of range for type 'i16'" in res.stdout

    def test_positive_int_out_of_range_u16_rejected(self):
        code = """
        act f(a: u16) {}
        act main() {
            f(65536)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Integer literal '65536' out of range for type 'u16'" in res.stdout

    def test_positive_int_in_range_u8_accepted(self):
        code = """
        act f(a: u8) {}
        act main() {
            f(255)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_positive_int_in_range_u16_accepted(self):
        code = """
        act f(a: u16) {}
        act main() {
            f(65535)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_positive_int_out_of_range_i32_rejected(self):
        code = """
        act f(a: i32) {}
        act main() {
            f(2147483648)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "out of range for type 'i32'" in res.stdout
        assert "2147483648" in res.stdout

    def test_positive_int_in_range_i32_accepted(self):
        code = """
        act f(a: i32) {}
        act main() {
            f(2147483647)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_positive_int_out_of_range_u32_rejected(self):
        code = """
        act f(a: u32) {}
        act main() {
            f(4294967296)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "out of range for type 'u32'" in res.stdout
        assert "4294967296" in res.stdout

    def test_positive_int_in_range_u32_accepted(self):
        code = """
        act f(a: u32) {}
        act main() {
            f(4294967295)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_negative_float_literal_to_int_rejected(self):
        code = """
        act f(a: i32) {}
        act main() {
            f(-1.5)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'i32', got 'f32'" in res.stdout

    def test_negative_float_literal_to_bool_rejected(self):
        code = """
        act g(a: bool) {}
        act main() {
            g(-1.5)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'bool', got 'f32'" in res.stdout

    def test_explicit_cast_float_to_int_accepted(self):
        code = """
        act f(a: i32) {}
        act main() {
            f(1.5 as i32)
            f(-1.5 as i32)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_explicit_cast_int_to_bool_accepted(self):
        code = """
        act g(a: bool) {}
        act main() {
            g(1 as bool)
            g(0 as bool)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_explicit_cast_bool_to_int_accepted(self):
        code = """
        act f(a: i32) {}
        act main() {
            f(true as i32)
            f(false as i32)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_explicit_cast_negative_int_to_u32_accepted(self):
        code = """
        act f(a: u32) {}
        act main() {
            f(-1 as u32)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_explicit_cast_overflow_int_to_u8_accepted(self):
        code = """
        act f(a: u8) {}
        act main() {
            f(256 as u8)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0
