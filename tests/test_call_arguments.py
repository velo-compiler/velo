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


# ==============================================================================
# 8. Comprehensive Call Path Audit Matrix (Task 59.5)
# ==============================================================================

class TestCallPathAuditMatrix:
    """
    Security Gate: Audit every call path across the compiler to guarantee that
    NO call path bypasses argument type checking or arity checking.

    Paths audited:
    1. Free functions
    2. Methods
    3. UFCS calls
    4. extern act functions
    5. Generic functions
    6. Function pointer variables (act(...) -> ...)
    7. Struct field function pointers (holder.cb(...))
    8. Kind variant constructors (Kind.Variant(...))
    9. Struct literal initializers (Data { ... })
    10. Builtin sizeof
    11. Builtin assert
    12. Builtin SIMD constructors (f32x4, etc.)
    13. Builtin reflection (field_count, field_value)
    14. Builtin modules:
        - io.* (sys.io)
        - mem.* (sys.mem)
        - fs.* (sys.fs)
        - str.* (sys.str)
        - math.* (sys.math)
        - time.* (sys.time)
        - os.* (sys.os)
        - shelf.* (dynamic array)
        - ring.* (ring buffer)
        - map.* (hash map)
        - bitset.* (bit vector)
    """

    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    # 1. Free functions
    def test_audit_free_function_type_mismatch_rejected(self):
        code = """
        act calc(x: i32) -> i32 { return x + 1 }
        act main() {
            calc("hello")
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'i32', got 'string'" in res.stdout

    def test_audit_free_function_arity_mismatch_rejected(self):
        code = """
        act calc(x: i32) -> i32 { return x + 1 }
        act main() {
            calc(1, 2)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in function call" in res.stdout

    def test_audit_free_function_valid_accepted(self):
        code = """
        act calc(x: i32) -> i32 { return x + 1 }
        act main() {
            calc(42)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 2. Methods
    def test_audit_method_arg_type_mismatch_rejected(self):
        code = """
        data Counter { val: i32 }
        act inc(self: @Counter, step: i32) { self.val = self.val + step }
        act main() {
            mut c = Counter { val: 0 }
            c.inc("one")
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'i32', got 'string'" in res.stdout

    def test_audit_method_receiver_type_mismatch_rejected(self):
        code = """
        data Counter { val: i32 }
        act inc(self: @Counter, step: i32) { self.val = self.val + step }
        act main() {
            let not_counter: i32 = 123
            not_counter.inc(1)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in method receiver: expected '@Counter', got 'i32'" in res.stdout

    def test_audit_method_valid_accepted(self):
        code = """
        data Counter { val: i32 }
        act inc(self: @Counter, step: i32) { self.val = self.val + step }
        act main() {
            mut c = Counter { val: 0 }
            c.inc(5)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 3. UFCS calls
    def test_audit_ufcs_arg_type_mismatch_rejected(self):
        code = """
        data Point { x: i32, y: i32 }
        act offset(self: @Point, dx: i32, dy: i32) { self.x += dx; self.y += dy }
        act main() {
            mut p = Point { x: 0, y: 0 }
            p.offset(1, "bad")
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 2: expected 'i32', got 'string'" in res.stdout

    def test_audit_ufcs_receiver_type_mismatch_rejected(self):
        code = """
        data Point { x: i32, y: i32 }
        act offset(self: @Point, dx: i32, dy: i32) { self.x += dx; self.y += dy }
        act main() {
            let s: string = "point"
            s.offset(1, 2)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in method receiver: expected '@Point', got 'string'" in res.stdout

    def test_audit_ufcs_valid_accepted(self):
        code = """
        data Point { x: i32, y: i32 }
        act offset(self: @Point, dx: i32, dy: i32) { self.x += dx; self.y += dy }
        act main() {
            mut p = Point { x: 0, y: 0 }
            p.offset(1, 2)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 4. extern act
    def test_audit_extern_arg_type_mismatch_rejected(self):
        code = """
        extern act c_puts(s: string) -> i32
        act main() {
            c_puts(123)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'string', got 'i32'" in res.stdout

    def test_audit_extern_arity_mismatch_rejected(self):
        code = """
        extern act c_puts(s: string) -> i32
        act main() {
            c_puts("a", "b")
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in function call" in res.stdout

    def test_audit_extern_valid_accepted(self):
        code = """
        extern act c_puts(s: string) -> i32
        act main() {
            c_puts("hello")
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 5. Generic functions
    def test_audit_generic_arg_type_mismatch_rejected(self):
        code = """
        act wrap[T](val: T, tag: string) -> T { return val }
        act main() {
            wrap[i32](42, 999)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 2: expected 'string', got 'i32'" in res.stdout

    def test_audit_generic_valid_accepted(self):
        code = """
        act wrap[T](val: T, tag: string) -> T { return val }
        act main() {
            wrap[i32](42, "tag")
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 6. Function pointer variables
    def test_audit_fn_ptr_var_arg_type_mismatch_rejected(self):
        code = """
        act apply(cb: act(i32) -> i32) -> i32 {
            return cb("hello")
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'i32', got 'string'" in res.stdout

    def test_audit_fn_ptr_var_arity_mismatch_rejected(self):
        code = """
        act apply(cb: act(i32) -> i32) -> i32 {
            return cb(1, 2)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in function call" in res.stdout

    def test_audit_fn_ptr_var_valid_accepted(self):
        code = """
        act apply(cb: act(i32) -> i32) -> i32 {
            return cb(42)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 7. Struct field function pointers
    def test_audit_struct_field_fn_ptr_arg_type_mismatch_rejected(self):
        code = """
        data Handler {
            on_event: act(i32) -> i32
        }
        act trigger(h: Handler) -> i32 {
            return h.on_event("wrong")
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'i32', got 'string'" in res.stdout

    def test_audit_struct_field_fn_ptr_arity_mismatch_rejected(self):
        code = """
        data Handler {
            on_event: act(i32) -> i32
        }
        act trigger(h: Handler) -> i32 {
            return h.on_event()
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in function call" in res.stdout

    def test_audit_struct_field_fn_ptr_valid_accepted(self):
        code = """
        data Handler {
            on_event: act(i32) -> i32
        }
        act trigger(h: Handler) -> i32 {
            return h.on_event(42)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 8. Kind variant constructors
    def test_audit_kind_variant_arg_type_mismatch_rejected(self):
        code = """
        kind Shape {
            Circle(radius: f64)
            Rect(w: f64, h: f64)
        }
        act main() {
            let s = Shape.Circle("not_radius")
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'f64', got 'string'" in res.stdout

    def test_audit_kind_variant_arity_mismatch_rejected(self):
        code = """
        kind Shape {
            Circle(radius: f64)
            Rect(w: f64, h: f64)
        }
        act main() {
            let s = Shape.Rect(1.0)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Mismatched argument count in variant constructor" in res.stdout

    def test_audit_kind_variant_no_payload_with_arg_rejected(self):
        code = """
        kind Shape {
            Point
            Circle(radius: f64)
        }
        act main() {
            let s = Shape.Point(123)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Variant does not take arguments" in res.stdout

    def test_audit_kind_variant_valid_accepted(self):
        code = """
        kind Shape {
            Point
            Circle(radius: f64)
            Rect(w: f64, h: f64)
        }
        act main() {
            let p = Shape.Point
            let c = Shape.Circle(3.14)
            let r = Shape.Rect(2.0, 4.0)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 9. Struct literal initializers
    def test_audit_struct_literal_field_type_mismatch_rejected(self):
        code = """
        data Config {
            timeout: i32
            label: string
        }
        act main() {
            let c = Config { timeout: "10s", label: "test" }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in field initializer" in res.stdout

    def test_audit_struct_literal_missing_field_rejected(self):
        code = """
        data Config {
            timeout: i32
            label: string
        }
        act main() {
            let c = Config { timeout: 10 }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Struct literal is missing field with no default" in res.stdout

    def test_audit_struct_literal_valid_accepted(self):
        code = """
        data Config {
            timeout: i32
            label: string
        }
        act main() {
            let c = Config { timeout: 10, label: "test" }
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 10. Builtin sizeof
    def test_audit_builtin_sizeof_arity_mismatch_rejected(self):
        code = """
        act main() {
            let s = sizeof()
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "sizeof takes exactly 1 argument" in res.stdout

    def test_audit_builtin_sizeof_valid_accepted(self):
        code = """
        act main() {
            let s = sizeof(i64)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 11. Builtin assert
    def test_audit_builtin_assert_type_mismatch_rejected(self):
        code = """
        act main() {
            assert("not_a_bool")
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "assert condition must be a boolean expression" in res.stdout

    def test_audit_builtin_assert_arity_mismatch_rejected(self):
        code = """
        act main() {
            assert()
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "assert takes 1 or 2 arguments" in res.stdout

    def test_audit_builtin_assert_valid_accepted(self):
        code = """
        act main() {
            assert(true)
            assert(1 == 1, "math works")
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 12. Builtin SIMD constructors
    def test_audit_builtin_simd_type_mismatch_rejected(self):
        code = """
        act main() {
            let v = f32x4("bad", 1.0, 2.0, 3.0)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "f32x4 constructor arguments must be float or integer (got string)" in res.stdout

    def test_audit_builtin_simd_arity_mismatch_rejected(self):
        code = """
        act main() {
            let v = f32x4(1.0, 2.0)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "f32x4 constructor expects exactly 4 arguments" in res.stdout

    def test_audit_builtin_simd_valid_accepted(self):
        code = """
        act main() {
            let v = f32x4(1.0, 2.0, 3.0, 4.0)
            let s = f32x4_splat(5.0)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 13. Builtin reflection
    def test_audit_builtin_reflect_field_count_non_struct_rejected(self):
        code = """
        act main() {
            let n = field_count(i32)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "'i32' is not a struct" in res.stdout

    def test_audit_builtin_reflect_field_count_arity_mismatch_rejected(self):
        code = """
        data Item { x: i32 }
        act main() {
            let n = field_count(Item, 1)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "field_count expects exactly 1 argument" in res.stdout

    def test_audit_builtin_reflect_field_count_valid_accepted(self):
        code = """
        data Item { x: i32, y: f64 }
        act main() {
            let n = field_count(Item)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_audit_builtin_reflect_field_value_non_struct_rejected(self):
        code = """
        act main() {
            let x: i32 = 42
            let f = field_value(x, 0)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "field_value target must be a struct or pointer to struct (got i32)" in res.stdout

    def test_audit_builtin_reflect_field_value_valid_accepted(self):
        code = """
        data Item { x: i32, y: string }
        act main() {
            let it = Item { x: 10, y: "abc" }
            let v = field_value(it, 0)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 14. Builtin modules
    # 14.1 io.*
    def test_audit_module_io_type_mismatch_rejected(self):
        code = """
        use sys.io
        act main() {
            io.println_byte("not_a_byte")
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "io.println_byte expects u8 (got string)" in res.stdout

    def test_audit_module_io_arity_mismatch_rejected(self):
        code = """
        use sys.io
        act main() {
            io.println_empty("unexpected")
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "io.println_empty expects exactly 0 arguments" in res.stdout

    def test_audit_module_io_valid_accepted(self):
        code = """
        use sys.io
        act main() {
            io.println("hello world")
            io.print("test")
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 14.2 mem.*
    def test_audit_module_mem_type_mismatch_rejected(self):
        code = """
        use sys.mem
        act main() {
            mem.copy(123, 456, 789)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "mem.copy expects pointer arguments (got i32)" in res.stdout

    def test_audit_module_mem_arity_mismatch_rejected(self):
        code = """
        use sys.mem
        act main() {
            mem.copy(@null, @null)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "mem.copy expects exactly 3 arguments" in res.stdout

    def test_audit_module_mem_valid_accepted(self):
        code = """
        use sys.mem
        act main() {
            let p1: @i32 = mem.heap_alloc(@i32, 4)
            let p2: @i32 = mem.heap_alloc(@i32, 4)
            mem.copy(p1, p2, 4)
            mem.free(p1)
            mem.free(p2)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 14.3 fs.*
    def test_audit_module_fs_type_mismatch_rejected(self):
        code = """
        use sys.fs
        act main() {
            let c = fs.read_file(123)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "fs.read_file expects string arguments (got i32)" in res.stdout

    def test_audit_module_fs_arity_mismatch_rejected(self):
        code = """
        use sys.fs
        act main() {
            let c = fs.read_file()
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "fs.read_file expects exactly 1 argument" in res.stdout

    def test_audit_module_fs_valid_accepted(self):
        code = """
        use sys.fs
        act main() {
            let b = fs.exists("nonexistent.txt")
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 14.4 str.*
    def test_audit_module_str_type_mismatch_rejected(self):
        code = """
        act main() {
            let n = str.len(123)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "str.len expects string arguments (got i32)" in res.stdout

    def test_audit_module_str_arity_mismatch_rejected(self):
        code = """
        act main() {
            let n = str.len("a", "b")
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "str.len expects exactly 1 argument" in res.stdout

    def test_audit_module_str_valid_accepted(self):
        code = """
        act main() {
            let n = str.len("hello")
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 14.5 math.*
    def test_audit_module_math_type_mismatch_rejected(self):
        code = """
        use sys.math
        act main() {
            let x = math.sqrt("hello")
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "math.sqrt expects f64 (or int) arguments (got string)" in res.stdout

    def test_audit_module_math_arity_mismatch_rejected(self):
        code = """
        use sys.math
        act main() {
            let x = math.sqrt()
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "math.sqrt expects exactly 1 argument" in res.stdout

    def test_audit_module_math_valid_accepted(self):
        code = """
        use sys.math
        act main() {
            let x = math.sqrt(16.0)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 14.6 time.*
    def test_audit_module_time_type_mismatch_rejected(self):
        code = """
        use sys.time
        act main() {
            time.sleep_ms("slow")
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "time.sleep_ms expects int arguments (got string)" in res.stdout

    def test_audit_module_time_arity_mismatch_rejected(self):
        code = """
        use sys.time
        act main() {
            time.sleep_ms(1, 2)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "time.sleep_ms expects exactly 1 argument" in res.stdout

    def test_audit_module_time_valid_accepted(self):
        code = """
        use sys.time
        act main() {
            let t = time.now()
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 14.7 os.*
    def test_audit_module_os_type_mismatch_rejected(self):
        code = """
        use sys.os
        act main() {
            os.exit("fail")
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "os.exit expects int arguments (got string)" in res.stdout

    def test_audit_module_os_arity_mismatch_rejected(self):
        code = """
        use sys.os
        act main() {
            os.exit()
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "os.exit expects exactly 1 argument" in res.stdout

    def test_audit_module_os_valid_accepted(self):
        code = """
        use sys.os
        act main() {
            let s = os.get_env("PATH")
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 14.8 shelf.*
    def test_audit_module_shelf_type_mismatch_rejected(self):
        code = """
        act main() {
            mut xs = shelf[1]
            xs.put("wrong")
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "shelf.put element mismatch: expected i32 (got string)" in res.stdout

    def test_audit_module_shelf_valid_accepted(self):
        code = """
        act main() {
            mut xs = shelf[1]
            xs.put(42)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 14.9 ring.*
    def test_audit_module_ring_type_mismatch_rejected(self):
        code = """
        act main() {
            mut r: ring[i32] = ring[]
            r.put("wrong")
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "ring.put element mismatch: expected i32 (got string)" in res.stdout

    def test_audit_module_ring_valid_accepted(self):
        code = """
        act main() {
            mut r: ring[i32] = ring[]
            r.put(42)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 14.10 map.*
    def test_audit_module_map_type_mismatch_rejected(self):
        code = """
        act main() {
            mut m: map[string, i32] = map[]
            m.put(123, "val")
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "map key mismatch: expected string (got i32)" in res.stdout

    def test_audit_module_map_valid_accepted(self):
        code = """
        act main() {
            mut m: map[string, i32] = map[]
            m.put("key", 42)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    # 14.11 bitset.*
    def test_audit_module_bitset_type_mismatch_rejected(self):
        code = """
        act main() {
            mut b: bitset = bitset[]
            b.set("index")
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "bitset index must be an integer (got string)" in res.stdout

    def test_audit_module_bitset_valid_accepted(self):
        code = """
        act main() {
            mut b: bitset = bitset[]
            b.set(4)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0


# ==============================================================================
# 9. Security & Regression Suite (Task 59.6)
# ==============================================================================

class TestSecurityRegressionSuite:
    """
    Validates Phase 59 Security Invariants and Phase Exit Criteria:
    - Every argument must be checked against its parameter type (no silent fallthrough).
    - Implicit narrowing and signed/unsigned mismatches remain rejected (Phase 46 contract).
    - Arity mismatches must be rejected at compile time (velo check).
    - Error messages must name the argument position, expected type, and actual type.
    - No C implicit conversion may be the only line of defense.
    - Explicit casts ('as <type>') must continue to be accepted.
    - The canonical defect programs:
        f("x") -> rejected at velo check
        f(1.5) -> rejected at velo check
        f(true) -> rejected at velo check
        g(1) -> rejected at velo check
        f(struct) -> rejected at velo check
        p.show(1.5) -> rejected at velo check
    """

    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_canonical_defect_string_to_int_rejected(self):
        code = """
        act f(a: i32) {}
        act main() {
            f("x")
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'i32', got 'string'" in res.stdout
        assert "semantic:" in res.stdout

    def test_canonical_defect_float_to_int_rejected(self):
        code = """
        act f(a: i32) {}
        act main() {
            f(1.5)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'i32', got 'f32'" in res.stdout
        assert "semantic:" in res.stdout

    def test_canonical_defect_bool_to_int_rejected(self):
        code = """
        act f(a: i32) {}
        act main() {
            f(true)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'i32', got 'bool'" in res.stdout
        assert "semantic:" in res.stdout

    def test_canonical_defect_int_to_bool_rejected(self):
        code = """
        act g(a: bool) {}
        act main() {
            g(1)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'bool', got 'i32'" in res.stdout
        assert "semantic:" in res.stdout

    def test_canonical_defect_struct_to_int_rejected(self):
        code = """
        data Item { id: i32 }
        act f(a: i32) {}
        act main() {
            let it = Item { id: 10 }
            f(it)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'i32', got 'Item'" in res.stdout
        assert "semantic:" in res.stdout

    def test_canonical_defect_method_ufcs_float_to_int_rejected(self):
        code = """
        data Point { x: i32 }
        act show(self: @Point, a: i32) {}
        act main() {
            mut p = Point { x: 0 }
            p.show(1.5)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 1: expected 'i32', got 'f32'" in res.stdout
        assert "semantic:" in res.stdout

    def test_multi_argument_position_reporting(self):
        code = """
        act h(a: i32, b: string, c: bool) {}
        act main() {
            h(1, "ok", 1.5)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 3: expected 'bool', got 'f32'" in res.stdout

    def test_multi_argument_middle_position_reporting(self):
        code = """
        act h(a: i32, b: string, c: bool) {}
        act main() {
            h(1, 100, true)
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Type mismatch in call argument 2: expected 'string', got 'i32'" in res.stdout

    def test_explicit_casts_for_all_canonical_defects_pass(self):
        code = """
        act f(a: i32) {}
        act g(a: bool) {}
        data Point { x: i32 }
        act show(self: @Point, a: i32) {}
        act main() {
            f(1.5 as i32)
            f(true as i32)
            g(1 as bool)
            mut p = Point { x: 0 }
            p.show(1.5 as i32)
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0


