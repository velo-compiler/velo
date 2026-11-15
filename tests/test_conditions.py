"""
tests/test_conditions.py — if/loop Condition Type Checking Test Matrix (Phase 60)

Audit ID: AUDIT-2026-11-09
Severity: P1 — checker accepts invalid programs; pointer truthiness

Covers:
- `if` statement condition type checking (int, string, struct, pointer, null, float, negative int, array)
- `if` expression condition type checking (int, string, struct, pointer, null, float)
- `loop` condition type checking (float, string, struct, pointer, null)
- Control group: valid bool conditions, binary comparisons, logical operators, optional null-checks, count loops, and range loops

Establishes the Red Baseline for Phase 60 (Task 60.1).
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


def run_velo_emit_c(source_code: str) -> subprocess.CompletedProcess:
    """Helper to run `velo emit-c` on a temporary source file."""
    with tempfile.NamedTemporaryFile("w", suffix=".vl", delete=False) as f:
        f.write(source_code)
        f_name = f.name
    try:
        res = subprocess.run([str(VELO_EXE), "emit-c", f_name], capture_output=True, text=True)
        return res
    finally:
        Path(f_name).unlink(missing_ok=True)


# ==============================================================================
# 1. `if` Statement Condition Type Mismatches (Red Baseline)
# ==============================================================================

class TestIfStatementConditionTypeChecking:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_if_int_literal_rejected(self):
        code = """
        act main() {
            if 1 {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'if 1', but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'i32'" in res.stdout

    def test_if_int_var_rejected(self):
        code = """
        act main() {
            let n: i32 = 1
            if n {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'if <int_var>', but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'i32'" in res.stdout

    def test_if_negative_int_rejected(self):
        code = """
        act main() {
            if -1 {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'if -1', but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'i32'" in res.stdout

    def test_if_string_literal_rejected(self):
        code = """
        act main() {
            if "x" {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'if \"x\"', but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'string'" in res.stdout

    def test_if_string_var_rejected(self):
        code = """
        act main() {
            let s: string = "hello"
            if s {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'if <string_var>', but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'string'" in res.stdout

    def test_if_struct_var_rejected(self):
        code = """
        data Point { x: i32, y: i32 }
        act main() {
            let p = Point { x: 0, y: 0 }
            if p {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'if <struct_var>', but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'Point'" in res.stdout

    def test_if_pointer_var_rejected(self):
        code = """
        data Point { x: i32, y: i32 }
        act main() {
            let p = Point { x: 0, y: 0 }
            let ptr: @Point = @p
            if ptr {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'if <pointer_var>', but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got '@Point'" in res.stdout

    def test_if_null_literal_rejected(self):
        code = """
        act main() {
            if null {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'if null', but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got '@void'" in res.stdout

    def test_if_float_literal_rejected(self):
        code = """
        act main() {
            if 5.0 {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'if 5.0', but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'f32'" in res.stdout

    def test_if_array_rejected(self):
        code = """
        act main() {
            let arr: [4]i32 = [1, 2, 3, 4]
            if arr {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'if <array>', but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got '[4]i32'" in res.stdout


# ==============================================================================
# 2. `if` Expression Condition Type Mismatches (Red Baseline)
# ==============================================================================

class TestIfExpressionConditionTypeChecking:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_if_expr_int_condition_rejected(self):
        code = """
        act main() {
            let x = if 1 { 10 } else { 20 }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'if 1 {{...}} else {{...}}', but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'i32'" in res.stdout

    def test_if_expr_string_condition_rejected(self):
        code = """
        act main() {
            let x = if "x" { 10 } else { 20 }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'if \"x\" {{...}} else {{...}}', but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'string'" in res.stdout

    def test_if_expr_struct_condition_rejected(self):
        code = """
        data Point { x: i32 }
        act main() {
            let p = Point { x: 0 }
            let x = if p { 10 } else { 20 }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of struct in if-expression, but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'Point'" in res.stdout

    def test_if_expr_pointer_condition_rejected(self):
        code = """
        act main() {
            let val: i32 = 42
            let ptr: @i32 = @val
            let x = if ptr { 10 } else { 20 }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of pointer in if-expression, but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got '@i32'" in res.stdout

    def test_if_expr_null_condition_rejected(self):
        code = """
        act main() {
            let x = if null { 10 } else { 20 }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of null in if-expression, but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got '@void'" in res.stdout

    def test_if_expr_float_condition_rejected(self):
        code = """
        act main() {
            let x = if 3.14 { 10 } else { 20 }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of float in if-expression, but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'f32'" in res.stdout


# ==============================================================================
# 3. `loop` Condition Type Checking (Red Baseline)
# ==============================================================================

class TestLoopConditionTypeChecking:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_loop_float_condition_rejected(self):
        code = """
        act main() {
            loop 5.0 {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'loop 5.0', but check passed: {res.stdout}"

    def test_loop_string_condition_rejected(self):
        code = """
        act main() {
            loop "x" {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'loop \"x\"', but check passed: {res.stdout}"

    def test_loop_struct_condition_rejected(self):
        code = """
        data Point { x: i32 }
        act main() {
            let p = Point { x: 0 }
            loop p {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'loop <struct>', but check passed: {res.stdout}"

    def test_loop_pointer_condition_rejected(self):
        code = """
        act main() {
            let x: i32 = 10
            let p: @i32 = @x
            loop p {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'loop <pointer>', but check passed: {res.stdout}"

    def test_loop_null_condition_rejected(self):
        code = """
        act main() {
            loop null {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'loop null', but check passed: {res.stdout}"


# ==============================================================================
# 4. Valid Condition Control Group (Must Always Pass)
# ==============================================================================

class TestValidConditionsControlGroup:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_valid_if_bool_literal_true_accepted(self):
        code = """
        act main() {
            if true {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_valid_if_bool_literal_false_accepted(self):
        code = """
        act main() {
            if false {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_valid_if_bool_var_accepted(self):
        code = """
        act main() {
            let flag: bool = true
            if flag {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_valid_if_binary_comparison_accepted(self):
        code = """
        act main() {
            let x = 10
            if x > 5 {}
            if x == 10 {}
            if x != 0 {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_valid_if_logical_and_or_accepted(self):
        code = """
        act main() {
            let a = true
            let b = false
            if a and not b {}
            if a or b {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_valid_if_null_check_accepted(self):
        code = """
        act main() {
            let p: ?string = "hello"
            if p != null {}
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_valid_if_expr_accepted(self):
        code = """
        act main() {
            let cond: bool = true
            let x = if cond { 10 } else { 20 }
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_valid_loop_bool_condition_accepted(self):
        code = """
        act main() {
            mut done = false
            loop not done {
                done = true
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_valid_loop_count_accepted(self):
        code = """
        act main() {
            mut count = 0
            loop 5 {
                count += 1
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0

    def test_valid_loop_range_accepted(self):
        code = """
        act main() {
            mut sum = 0
            loop i in 0..5 {
                sum += i
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0


# ==============================================================================
# 5. Chained (`else if`) and Nested Condition Sites (Task 60.3)
# ==============================================================================

class TestChainedAndNestedConditionSites:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_if_else_if_int_condition_rejected(self):
        code = """
        act main() {
            if false {
            } else if 1 {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'else if 1', but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'i32'" in res.stdout

    def test_if_else_if_string_condition_rejected(self):
        code = """
        act main() {
            if false {
            } else if "bad" {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'else if \"bad\"', but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'string'" in res.stdout

    def test_if_else_if_struct_condition_rejected(self):
        code = """
        data Point {
            x: i32
            y: i32
        }
        act main() {
            let p = Point{ x: 1, y: 2 }
            if false {
            } else if p {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'else if <struct>', but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'Point'" in res.stdout

    def test_if_else_if_null_condition_rejected(self):
        code = """
        act main() {
            if false {
            } else if null {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'else if null', but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got '@void'" in res.stdout

    def test_if_multiple_else_if_chain_rejected_at_culprit(self):
        code = """
        act main() {
            let a = false
            let b = false
            if a {
            } else if b {
            } else if 42 {
            } else {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection in multi-chain else if, but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'i32'" in res.stdout

    def test_nested_if_in_then_branch_rejected(self):
        code = """
        act main() {
            if true {
                if 1 {
                }
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection in nested then if, but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'i32'" in res.stdout

    def test_nested_if_in_else_branch_rejected(self):
        code = """
        act main() {
            if false {
            } else {
                if "nested_bad" {
                }
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection in nested else if, but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'string'" in res.stdout

    def test_if_binary_arithmetic_condition_rejected(self):
        code = """
        act main() {
            let a = 1
            let b = 2
            if a + b {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of 'if a + b', but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'i32'" in res.stdout

    def test_if_expr_chained_else_if_int_rejected(self):
        code = """
        act main() {
            let x = if false { 1 } else if 2 { 3 } else { 4 }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of chained if-expr int, but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'i32'" in res.stdout

    def test_if_expr_chained_else_if_string_rejected(self):
        code = """
        act main() {
            let x = if false { 1 } else if "not_a_bool" { 2 } else { 3 }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of chained if-expr string, but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'string'" in res.stdout

    def test_if_expr_chained_else_if_null_rejected(self):
        code = """
        act main() {
            let x = if false { 1 } else if null { 2 } else { 3 }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of chained if-expr null, but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got '@void'" in res.stdout

    def test_if_expr_nested_in_then_rejected(self):
        code = """
        act main() {
            let x = if true {
                if 99 { 1 } else { 2 }
            } else {
                3
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of nested then if-expr, but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'i32'" in res.stdout

    def test_if_expr_nested_in_else_rejected(self):
        code = """
        act main() {
            let x = if false {
                1
            } else {
                if 3.14 { 2 } else { 3 }
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of nested else if-expr, but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'f32'" in res.stdout

    def test_nested_if_inside_loop_rejected(self):
        code = """
        act main() {
            loop {
                if 1 {
                    break
                }
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of if inside loop, but check passed: {res.stdout}"
        assert "Condition must be of type 'bool', got 'i32'" in res.stdout

    def test_valid_chained_else_if_statement_accepted(self):
        code = """
        act main() {
            let x = 10
            if x < 0 {
            } else if x == 10 {
            } else if x > 20 {
            } else {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected valid chained else if to pass, got: {res.stdout}"

    def test_valid_chained_else_if_expr_accepted(self):
        code = """
        act main() {
            let score = 85
            let grade = if score >= 90 { "A" } else if score >= 80 { "B" } else if score >= 70 { "C" } else { "F" }
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected valid chained if expr to pass, got: {res.stdout}"

    def test_valid_nested_if_statement_and_expr_accepted(self):
        code = """
        act main() {
            let a = true
            let b = false
            if a {
                if not b {
                    let val = if b { 1 } else { if a { 2 } else { 3 } }
                }
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected valid nested if stmt and expr to pass, got: {res.stdout}"


# ==============================================================================
# 6. Flow-Sensitive Narrowing & Condition Interactions (Task 60.4)
# ==============================================================================

class TestFlowSensitiveNarrowingConditionInteractions:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_if_not_null_narrows_pointer_in_then_branch(self):
        code = """
        data Node { num: i32 }
        act foo(p: ?@Node) -> i32 {
            if p != null {
                return p.num
            }
            return 0
        }
        act main() {}
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected narrowing in then branch to pass, got: {res.stdout}"

    def test_if_null_narrows_pointer_in_else_branch(self):
        code = """
        data Node { num: i32 }
        act foo(p: ?@Node) -> i32 {
            if p == null {
                return 0
            } else {
                return p.num
            }
        }
        act main() {}
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected narrowing in else branch to pass, got: {res.stdout}"

    def test_early_return_narrows_pointer_in_following_statements(self):
        code = """
        data Node { num: i32 }
        act foo(p: ?@Node) -> i32 {
            if p == null {
                return 0
            }
            return p.num
        }
        act main() {}
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected early-return narrowing to pass, got: {res.stdout}"

    def test_early_break_narrows_pointer_in_loop(self):
        code = """
        data Node { num: i32 }
        act foo(p: ?@Node) -> i32 {
            loop {
                if p == null {
                    break
                }
                return p.num
            }
            return 0
        }
        act main() {}
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected loop-break narrowing to pass, got: {res.stdout}"

    def test_early_continue_narrows_pointer_in_loop(self):
        code = """
        data Node { num: i32 }
        act foo(p: ?@Node) {
            loop 5 {
                if p == null {
                    continue
                }
                let v = p.num
            }
        }
        act main() {}
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected loop-continue narrowing to pass, got: {res.stdout}"

    def test_early_fail_narrows_pointer(self):
        code = """
        data Node { num: i32 }
        act foo(p: ?@Node) -> i32 or i32 {
            if p == null {
                fail 1
            }
            return p.num
        }
        act main() {}
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected fail-narrowing to pass, got: {res.stdout}"

    def test_conjunction_and_narrows_both_variables(self):
        code = """
        data Node { num: i32 }
        act foo(a: ?@Node, b: ?@Node) -> i32 {
            if a != null and b != null {
                return a.num + b.num
            }
            return 0
        }
        act main() {}
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected conjunction narrowing to pass, got: {res.stdout}"

    def test_if_expr_then_branch_narrowing(self):
        code = """
        data Node { num: i32 }
        act foo(p: ?@Node) -> i32 {
            let v = if p != null { p.num } else { 0 }
            return v
        }
        act main() {}
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected if-expr then narrowing to pass, got: {res.stdout}"

    def test_if_expr_else_branch_narrowing(self):
        code = """
        data Node { num: i32 }
        act foo(p: ?@Node) -> i32 {
            let v = if p == null { 0 } else { p.num }
            return v
        }
        act main() {}
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected if-expr else narrowing to pass, got: {res.stdout}"

    def test_reversed_null_comparison_narrows(self):
        code = """
        data Node { num: i32 }
        act foo(p: ?@Node) -> i32 {
            if null != p {
                return p.num
            }
            return 0
        }
        act main() {}
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected reversed null comparison to pass, got: {res.stdout}"

    def test_primitive_optional_narrowing(self):
        code = """
        act foo(x: ?i32) -> i32 {
            if x != null {
                let sum = x + 10
                return sum
            }
            return 0
        }
        act main() {}
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected primitive optional narrowing to pass, got: {res.stdout}"

    def test_optional_without_null_check_rejected_member_access(self):
        code = """
        data Node { num: i32 }
        act foo(p: ?@Node) -> i32 {
            return p.num
        }
        act main() {}
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection without unwrapping, but passed: {res.stdout}"
        assert "without unwrapping" in res.stdout

    def test_optional_in_else_branch_of_neq_null_rejected_member_access(self):
        code = """
        data Node { num: i32 }
        act foo(p: ?@Node) -> i32 {
            if p != null {
                return 0
            } else {
                return p.num
            }
        }
        act main() {}
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection in else branch of != null, but passed: {res.stdout}"
        assert "without unwrapping" in res.stdout

    def test_optional_in_then_branch_of_eq_null_rejected_member_access(self):
        code = """
        data Node { num: i32 }
        act foo(p: ?@Node) -> i32 {
            if p == null {
                return p.num
            } else {
                return 0
            }
        }
        act main() {}
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection in then branch of == null, but passed: {res.stdout}"
        assert "without unwrapping" in res.stdout

    def test_bare_optional_condition_rejected_not_truthy(self):
        code = """
        data Node { num: i32 }
        act main() {
            let p: ?@Node = null
            if p {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of bare optional condition, but passed: {res.stdout}"
        assert "Condition must be of type 'bool', got '?@Node'" in res.stdout

    def test_bare_primitive_optional_condition_rejected_not_truthy(self):
        code = """
        act main() {
            let opt_i: ?i32 = 42
            if opt_i {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of bare optional condition, but passed: {res.stdout}"
        assert "Condition must be of type 'bool', got '?i32'" in res.stdout

    def test_bare_optional_if_expr_condition_rejected_not_truthy(self):
        code = """
        data Node { val: i32 }
        act main() {
            let p: ?@Node = null
            let x = if p { 1 } else { 0 }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of bare optional condition in if-expr, but passed: {res.stdout}"
        assert "Condition must be of type 'bool', got '?@Node'" in res.stdout


# ==============================================================================
# 7. Codegen Defense & Negative Tests (Task 60.5)
# ==============================================================================

class TestCodegenDefenseAndConditionSafety:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_emit_c_rejects_int_statement_condition(self):
        code = """
        act main() {
            if 1 {}
        }
        """
        res = run_velo_emit_c(code)
        assert res.returncode != 0, f"Expected emit-c to fail on 'if 1', but succeeded: {res.stdout}"
        assert "Condition must be of type 'bool', got 'i32'" in res.stdout

    def test_emit_c_rejects_string_statement_condition(self):
        code = """
        act main() {
            if "hello" {}
        }
        """
        res = run_velo_emit_c(code)
        assert res.returncode != 0, f"Expected emit-c to fail on 'if \"hello\"', but succeeded: {res.stdout}"
        assert "Condition must be of type 'bool', got 'string'" in res.stdout

    def test_emit_c_rejects_struct_statement_condition(self):
        code = """
        data Point { x: i32, y: i32 }
        act main() {
            let p = Point{ x: 1, y: 2 }
            if p {}
        }
        """
        res = run_velo_emit_c(code)
        assert res.returncode != 0, f"Expected emit-c to fail on 'if <struct>', but succeeded: {res.stdout}"
        assert "Condition must be of type 'bool', got 'Point'" in res.stdout

    def test_emit_c_rejects_pointer_statement_condition(self):
        code = """
        data Point { x: i32, y: i32 }
        act main() {
            let p = Point{ x: 1, y: 2 }
            let ptr = @p
            if ptr {}
        }
        """
        res = run_velo_emit_c(code)
        assert res.returncode != 0, f"Expected emit-c to fail on 'if <ptr>', but succeeded: {res.stdout}"
        assert "Condition must be of type 'bool', got '@Point'" in res.stdout

    def test_emit_c_rejects_loop_float_condition(self):
        code = """
        act main() {
            loop 5.0 {}
        }
        """
        res = run_velo_emit_c(code)
        assert res.returncode != 0, f"Expected emit-c to fail on 'loop 5.0', but succeeded: {res.stdout}"
        assert "Loop expression must be an integer (count) or 'bool' (condition), got 'f32'" in res.stdout

    def test_emit_c_rejects_loop_string_condition(self):
        code = """
        act main() {
            loop "forever" {}
        }
        """
        res = run_velo_emit_c(code)
        assert res.returncode != 0, f"Expected emit-c to fail on 'loop <string>', but succeeded: {res.stdout}"
        assert "Loop expression must be an integer (count) or 'bool' (condition), got 'string'" in res.stdout

    def test_emit_c_rejects_if_expr_int_condition(self):
        code = """
        act main() {
            let x = if 1 { 10 } else { 20 }
        }
        """
        res = run_velo_emit_c(code)
        assert res.returncode != 0, f"Expected emit-c to fail on if-expr 'if 1', but succeeded: {res.stdout}"
        assert "Condition must be of type 'bool', got 'i32'" in res.stdout

    def test_emit_c_rejects_bare_optional_condition(self):
        code = """
        data Node { val: i32 }
        act main() {
            let p: ?@Node = null
            if p {}
        }
        """
        res = run_velo_emit_c(code)
        assert res.returncode != 0, f"Expected emit-c to fail on bare optional condition, but succeeded: {res.stdout}"
        assert "Condition must be of type 'bool', got '?@Node'" in res.stdout

    def test_emit_c_valid_condition_emits_clean_c(self):
        code = """
        act main() {
            let flag = true
            if flag {
                let a = 1
            }
        }
        """
        res = run_velo_emit_c(code)
        assert res.returncode == 0, f"Expected emit-c to succeed, got: {res.stdout}"
        assert "if (flag)" in res.stdout

    def test_emit_c_valid_flow_narrowed_condition_emits_clean_c(self):
        code = """
        data Node { num: i32 }
        act main() {
            mut n = Node{ num: 42 }
            let p: ?@Node = @n
            if p != null {
                let v = p.num
            }
        }
        """
        res = run_velo_emit_c(code)
        assert res.returncode == 0, f"Expected emit-c to succeed, got: {res.stdout}"
        assert "!= NULL" in res.stdout or "p != NULL" in res.stdout or "NULL" in res.stdout

    def test_emit_c_valid_condition_loop_emits_clean_c(self):
        code = """
        act main() {
            mut done = false
            loop not done {
                done = true
            }
        }
        """
        res = run_velo_emit_c(code)
        assert res.returncode == 0, f"Expected emit-c to succeed, got: {res.stdout}"
        assert "for (" in res.stdout



