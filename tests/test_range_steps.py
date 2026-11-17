"""
tests/test_range_steps.py — Range Loop Step Validation & Zero-Step Matrix (Phase 63)

Audit ID: AUDIT-2026-11-12
Severity: P0 — infinite loop
Depends on: Phases 53, 54, 55, 56
Blocks: Phase 68

Covers:
- Literal zero steps (:0, :+0, :-0, :0u32, :(0)) compile-time rejection
- Float steps (:0.0) type-checking rejection
- Negative literal steps (:-1) compile-time rejection
- Dynamic zero and negative steps runtime termination & defense
- Valid positive steps (ascending, descending, inclusive, dynamic, large step)

Establishes the Red Baseline for Phase 63 (Task 63.1).
"""

import os
import subprocess
import tempfile
from pathlib import Path
import pytest
from conftest import cc_dir, velo_exe

ROOT_DIR = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()
if not VELO_EXE.exists() and (velo_exe()).exists():
    VELO_EXE = velo_exe()


def get_build_env():
    env = dict(os.environ)
    if os.name == "nt":
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return env


def run_velo_check(source_code: str) -> subprocess.CompletedProcess:
    """Helper to run `velo check` on a temporary source file."""
    with tempfile.NamedTemporaryFile("w", suffix=".vl", delete=False) as f:
        f.write(source_code)
        f_name = f.name
    try:
        res = subprocess.run([str(VELO_EXE), "check", f_name], capture_output=True, text=True, encoding="utf-8", errors="replace")
        return res
    finally:
        Path(f_name).unlink(missing_ok=True)


def run_velo_emit_c(source_code: str) -> subprocess.CompletedProcess:
    """Helper to run `velo emit-c` on a temporary source file."""
    with tempfile.NamedTemporaryFile("w", suffix=".vl", delete=False) as f:
        f.write(source_code)
        f_name = f.name
    c_out = f_name + ".c"
    try:
        res = subprocess.run([str(VELO_EXE), "emit-c", f_name, "-o", c_out], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if res.returncode == 0 and Path(c_out).exists():
            res.stdout = Path(c_out).read_text(encoding="utf-8")
        return res
    finally:
        Path(f_name).unlink(missing_ok=True)
        Path(c_out).unlink(missing_ok=True)


def build_and_run_code(source_code: str, timeout: float = 1.0) -> subprocess.CompletedProcess:
    """Helper to build and run code, returning CompletedProcess or raising TimeoutExpired."""
    with tempfile.NamedTemporaryFile("w", suffix=".vl", delete=False) as f:
        f.write(source_code)
        src_path = f.name
    exe_path = src_path + (".exe" if os.name == "nt" else "")
    try:
        build_res = subprocess.run(
            [str(VELO_EXE), "build", src_path, "-o", exe_path],
            env=get_build_env(),
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        if build_res.returncode != 0:
            return build_res
        run_res = subprocess.run(
            [exe_path],
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            timeout=timeout,
        )
        return run_res
    finally:
        Path(src_path).unlink(missing_ok=True)
        Path(exe_path).unlink(missing_ok=True)


# ==============================================================================
# 1. Compile-Time Literal & Type Step Rejection
# ==============================================================================

class TestLiteralStepCompileRejection:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_literal_zero_step_rejected_compile_time(self):
        code = """
        act main() {
            loop i in 0..10:0 {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of ':0', but check passed: {res.stdout}"
        assert "Range loop step must be greater than zero" in res.stdout

    def test_literal_negative_zero_step_rejected_compile_time(self):
        code = """
        act main() {
            loop i in 0..10:-0 {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of ':-0', but check passed: {res.stdout}"
        assert "Range loop step must be greater than zero" in res.stdout

    def test_literal_positive_zero_step_rejected_compile_time(self):
        code = """
        act main() {
            loop i in 0..10:+0 {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of ':+0', but check passed: {res.stdout}"

    def test_literal_negative_step_rejected_compile_time(self):
        code = """
        act main() {
            loop i in 0..10:-1 {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of ':-1', but check passed: {res.stdout}"
        assert "Range loop step must be greater than zero" in res.stdout

    def test_literal_typed_zero_step_rejected_compile_time(self):
        code = """
        act main() {
            loop i in 0..10:0u32 {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of ':0u32', but check passed: {res.stdout}"
        assert "Range loop step must be greater than zero" in res.stdout

    def test_literal_grouped_zero_step_rejected_compile_time(self):
        code = """
        act main() {
            loop i in 0..10:(0) {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of ':(0)', but check passed: {res.stdout}"
        assert "Range loop step must be greater than zero" in res.stdout

    def test_literal_float_zero_step_rejected_compile_time(self):
        code = """
        act main() {
            loop i in 0..10:0.0 {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of float step, but check passed: {res.stdout}"
        assert "Range loop step must be an integer type, got 'f32'" in res.stdout

    def test_dynamic_float_step_rejected_compile_time(self):
        code = """
        act main() {
            let s: f32 = 0.0
            loop i in 0..10:s {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of float var step, but check passed: {res.stdout}"
        assert "Range loop step must be an integer type, got 'f32'" in res.stdout

    def test_anonymous_range_zero_step_rejected_compile_time(self):
        code = """
        act main() {
            loop 0..10:0 {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of anonymous ':0', but check passed: {res.stdout}"
        assert "Range loop step must be greater than zero" in res.stdout

    def test_literal_zero_step_in_descending_range_rejected_compile_time(self):
        code = """
        act main() {
            loop i in 10..0:0 {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of descending ':0', but check passed: {res.stdout}"
        assert "Range loop step must be greater than zero" in res.stdout

    def test_constant_expression_zero_step_rejected_compile_time(self):
        code = """
        act main() {
            loop i in 0..10:(1 - 1) {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0, f"Expected rejection of ':(1 - 1)', but check passed: {res.stdout}"
        assert "Range loop step must be greater than zero" in res.stdout

    def test_constant_expr_multiplication_zero_step_rejected(self):
        code = """
        act main() {
            loop i in 0..10:(2 * 0) {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Range loop step must be greater than zero" in res.stdout

    def test_constant_expr_division_zero_step_rejected(self):
        code = """
        act main() {
            loop i in 0..10:(0 / 5) {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Range loop step must be greater than zero" in res.stdout

    def test_constant_expr_bitwise_and_zero_step_rejected(self):
        code = """
        act main() {
            loop i in 0..10:(0 & 15) {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Range loop step must be greater than zero" in res.stdout

    def test_constant_expr_shift_left_zero_step_rejected(self):
        code = """
        act main() {
            loop i in 0..10:(0 << 4) {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Range loop step must be greater than zero" in res.stdout

    def test_constant_expr_cast_zero_step_rejected(self):
        code = """
        act main() {
            loop i in 0..10:(0 as i32) {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Range loop step must be greater than zero" in res.stdout

    def test_constant_expr_cast_zero_u32_step_rejected(self):
        code = """
        act main() {
            loop i in 0..10:(0 as u32) {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Range loop step must be greater than zero" in res.stdout

    def test_constant_expr_cast_zero_i64_step_rejected(self):
        code = """
        act main() {
            loop i in 0..10:(0 as i64) {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Range loop step must be greater than zero" in res.stdout

    def test_constant_expr_negative_binary_step_rejected(self):
        code = """
        act main() {
            loop i in 0..10:(5 - 10) {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Range loop step must be greater than zero" in res.stdout

    def test_constant_expr_negative_cast_step_rejected(self):
        code = """
        act main() {
            loop i in 0..10:(-1 as i32) {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Range loop step must be greater than zero" in res.stdout

    def test_constant_expr_nested_subtraction_zero_step_rejected(self):
        code = """
        act main() {
            loop i in 0..10:((5 - 3) - 2) {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode != 0
        assert "Range loop step must be greater than zero" in res.stdout

    def test_constant_expr_valid_positive_addition_passes(self):
        code = """
        act main() {
            loop i in 0..10:(1 + 2) {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected valid positive step (1 + 2) to pass, got: {res.stdout}"

    def test_constant_expr_valid_positive_division_passes(self):
        code = """
        act main() {
            loop i in 0..10:(10 / 2) {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected valid positive step (10 / 2) to pass, got: {res.stdout}"

    def test_constant_expr_valid_double_negative_passes(self):
        code = """
        act main() {
            loop i in 0..10:(-(-1)) {
            }
        }
        """
        res = run_velo_check(code)
        assert res.returncode == 0, f"Expected valid positive step -(-1) to pass, got: {res.stdout}"


# ==============================================================================
# 2. Dynamic Zero & Negative Steps (Red Baseline: Must Fail Fast, Never Hang)
# ==============================================================================

class TestDynamicRangeStepExecution:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_dynamic_zero_step_fails_fast_runtime(self):
        code = """
        use std.io

        act main() -> i32 {
            let s: i32 = 0
            loop i in 0..10:s {
                io.println(i)
            }
            return 0
        }
        """
        try:
            res = build_and_run_code(code, timeout=1.0)
            assert res.returncode != 0, f"Expected dynamic zero step to fail with error, but exited {res.returncode}"
            assert "Range loop step must be greater than zero" in res.stderr
            assert "0" not in res.stdout, "Expected no partial iterations before step check"
        except subprocess.TimeoutExpired:
            pytest.fail("Dynamic zero step hung: infinite loop detected (timed out)")

    def test_dynamic_negative_step_fails_fast_runtime(self):
        code = """
        use std.io

        act main() -> i32 {
            let s: i32 = -1
            loop i in 0..10:s {
                io.println(i)
            }
            return 0
        }
        """
        try:
            res = build_and_run_code(code, timeout=1.0)
            assert res.returncode != 0, f"Expected dynamic negative step to fail with error, but exited {res.returncode}"
            assert "Range loop step must be greater than zero" in res.stderr
            assert "0" not in res.stdout, "Expected no partial iterations before step check"
        except subprocess.TimeoutExpired:
            pytest.fail("Dynamic negative step hung: infinite loop detected (timed out)")

    def test_dynamic_descending_negative_step_fails_fast_runtime(self):
        code = """
        use std.io

        act main() -> i32 {
            let s: i32 = -2
            loop i in 10..0:s {
                io.println(i)
            }
            return 0
        }
        """
        try:
            res = build_and_run_code(code, timeout=1.0)
            assert res.returncode != 0, f"Expected dynamic descending negative step to fail with error, but exited {res.returncode}"
            assert "Range loop step must be greater than zero" in res.stderr
            assert "10" not in res.stdout, "Expected no partial iterations before step check"
        except subprocess.TimeoutExpired:
            pytest.fail("Dynamic descending negative step hung: infinite loop detected (timed out)")

    def test_dynamic_unsigned_zero_step_fails_fast_runtime(self):
        code = """
        use std.io

        act main() -> i32 {
            let s: u32 = 0u32
            loop i in 0..10:s {
                io.println(i)
            }
            return 0
        }
        """
        try:
            res = build_and_run_code(code, timeout=1.0)
            assert res.returncode != 0, f"Expected dynamic unsigned zero step to fail with error, but exited {res.returncode}"
            assert "Range loop step must be greater than zero" in res.stderr
            assert "0" not in res.stdout, "Expected no partial iterations before step check"
        except subprocess.TimeoutExpired:
            pytest.fail("Dynamic unsigned zero step hung: infinite loop detected (timed out)")

    def test_dynamic_i64_zero_step_fails_fast_runtime(self):
        code = """
        use std.io

        act main() -> i32 {
            let s: i64 = 0
            loop i in 0..10:s {
                io.println(i)
            }
            return 0
        }
        """
        try:
            res = build_and_run_code(code, timeout=1.0)
            assert res.returncode != 0, f"Expected dynamic i64 zero step to fail with error, but exited {res.returncode}"
            assert "Range loop step must be greater than zero" in res.stderr
            assert "0" not in res.stdout, "Expected no partial iterations before step check"
        except subprocess.TimeoutExpired:
            pytest.fail("Dynamic i64 zero step hung: infinite loop detected (timed out)")

    def test_constant_expr_zero_step_fails_fast_runtime(self):
        code = """
        use std.io

        act main() -> i32 {
            loop i in 0..10:(2 - 2) {
                io.println(i)
            }
            return 0
        }
        """
        try:
            res = build_and_run_code(code, timeout=1.0)
            assert res.returncode != 0, f"Expected (2 - 2) zero step to fail with error, but exited {res.returncode}"
        except subprocess.TimeoutExpired:
            pytest.fail("Constant expression zero step hung: infinite loop detected (timed out)")

    def test_dynamic_anonymous_range_zero_step_fails_fast_runtime(self):
        code = """
        use std.io

        act main() -> i32 {
            let s: i32 = 0
            loop 0..10:s {
                io.println("UNREACHABLE")
            }
            return 0
        }
        """
        try:
            res = build_and_run_code(code, timeout=1.0)
            assert res.returncode != 0, f"Expected anonymous zero step to fail, but exited {res.returncode}"
            assert "Range loop step must be greater than zero" in res.stderr
            assert "UNREACHABLE" not in res.stdout
        except subprocess.TimeoutExpired:
            pytest.fail("Anonymous dynamic zero step hung: infinite loop detected (timed out)")

    def test_dynamic_zero_step_no_side_effects_before_check(self):
        code = """
        use std.io

        act main() -> i32 {
            mut side_effect: i32 = 0
            let s: i32 = 0
            loop i in 0..10:s {
                side_effect += 1
                io.println("ran iteration {i}")
            }
            io.println("final side_effect={side_effect}")
            return 0
        }
        """
        try:
            res = build_and_run_code(code, timeout=1.0)
            assert res.returncode != 0
            assert "Range loop step must be greater than zero" in res.stderr
            assert "ran iteration" not in res.stdout
            assert "final side_effect" not in res.stdout
        except subprocess.TimeoutExpired:
            pytest.fail("Dynamic zero step hung: infinite loop detected (timed out)")


# ==============================================================================
# 3. Control Group: Valid Positive Steps (Must Pass Cleanly)
# ==============================================================================

class TestValidRangeStepControlGroup:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_valid_positive_step_ascending(self):
        code = """
        use std.io

        act main() -> i32 {
            mut sum: i32 = 0
            mut count: i32 = 0
            loop i in 0..10:2 {
                sum += i
                count += 1
            }
            io.println("sum={sum}, count={count}")
            return 0
        }
        """
        res = build_and_run_code(code, timeout=2.0)
        assert res.returncode == 0, f"Run failed: {res.stderr}\n{res.stdout}"
        assert "sum=20, count=5" in res.stdout

    def test_valid_positive_step_descending(self):
        code = """
        use std.io

        act main() -> i32 {
            mut sum: i32 = 0
            mut count: i32 = 0
            loop i in 10..0:2 {
                sum += i
                count += 1
            }
            io.println("sum={sum}, count={count}")
            return 0
        }
        """
        res = build_and_run_code(code, timeout=2.0)
        assert res.returncode == 0, f"Run failed: {res.stderr}\n{res.stdout}"
        assert "sum=30, count=5" in res.stdout

    def test_valid_positive_step_inclusive(self):
        code = """
        use std.io

        act main() -> i32 {
            mut sum: i32 = 0
            mut count: i32 = 0
            loop i in 0..=10:2 {
                sum += i
                count += 1
            }
            io.println("sum={sum}, count={count}")
            return 0
        }
        """
        res = build_and_run_code(code, timeout=2.0)
        assert res.returncode == 0, f"Run failed: {res.stderr}\n{res.stdout}"
        assert "sum=30, count=6" in res.stdout

    def test_valid_dynamic_positive_step_ascending(self):
        code = """
        use std.io

        act main() -> i32 {
            let s: i32 = 3
            mut sum: i32 = 0
            mut count: i32 = 0
            loop i in 0..10:s {
                sum += i
                count += 1
            }
            io.println("sum={sum}, count={count}")
            return 0
        }
        """
        res = build_and_run_code(code, timeout=2.0)
        assert res.returncode == 0, f"Run failed: {res.stderr}\n{res.stdout}"
        assert "sum=18, count=4" in res.stdout

    def test_valid_dynamic_positive_step_descending(self):
        code = """
        use std.io

        act main() -> i32 {
            let s: i32 = 3
            mut sum: i32 = 0
            mut count: i32 = 0
            loop i in 10..0:s {
                sum += i
                count += 1
            }
            io.println("sum={sum}, count={count}")
            return 0
        }
        """
        res = build_and_run_code(code, timeout=2.0)
        assert res.returncode == 0, f"Run failed: {res.stderr}\n{res.stdout}"
        assert "sum=22, count=4" in res.stdout

    def test_valid_step_equal_to_range_length(self):
        code = """
        use std.io

        act main() -> i32 {
            mut sum: i32 = 0
            mut count: i32 = 0
            loop i in 0..5:5 {
                sum += i
                count += 1
            }
            io.println("sum={sum}, count={count}")
            return 0
        }
        """
        res = build_and_run_code(code, timeout=2.0)
        assert res.returncode == 0, f"Run failed: {res.stderr}\n{res.stdout}"
        assert "sum=0, count=1" in res.stdout

    def test_valid_step_larger_than_range_length(self):
        code = """
        use std.io

        act main() -> i32 {
            mut sum: i32 = 0
            mut count: i32 = 0
            loop i in 0..5:10 {
                sum += i
                count += 1
            }
            io.println("sum={sum}, count={count}")
            return 0
        }
        """
        res = build_and_run_code(code, timeout=2.0)
        assert res.returncode == 0, f"Run failed: {res.stderr}\n{res.stdout}"
        assert "sum=0, count=1" in res.stdout

    def test_valid_anonymous_range_step(self):
        code = """
        use std.io

        act main() -> i32 {
            mut sum: i32 = 0
            mut count: i32 = 0
            loop 0..10:2 {
                sum += it as i32
                count += 1
            }
            io.println("sum={sum}, count={count}")
            return 0
        }
        """
        res = build_and_run_code(code, timeout=2.0)
        assert res.returncode == 0, f"Run failed: {res.stderr}\n{res.stdout}"
        assert "sum=20, count=5" in res.stdout


# ==============================================================================
# 4. Codegen Defense & Zero-Step Increment Verification (Task 63.4 & 63.5)
# ==============================================================================

class TestNoZeroStepEmittedAndCodegenDefense:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_emit_c_never_emits_literal_increment_zero(self):
        code = """
        use std.io

        act main() -> i32 {
            loop i in 0..10:2 {
                io.println(i)
            }
            loop j in 10..0:2 {
                io.println(j)
            }
            return 0
        }
        """
        res = run_velo_emit_c(code)
        assert res.returncode == 0
        assert "+= 0" not in res.stdout
        assert "-= 0" not in res.stdout
        assert "+= (0)" not in res.stdout
        assert "-= (0)" not in res.stdout

    def test_emit_c_defense_in_depth_rejects_zero_step(self):
        code = """
        act main() {
            loop i in 0..10:0 { }
        }
        """
        res = run_velo_emit_c(code)
        assert res.returncode != 0
        assert "+= 0" not in res.stdout

    def test_emit_c_defense_in_depth_rejects_constant_zero_step(self):
        code = """
        act main() {
            loop i in 0..10:(1 - 1) { }
        }
        """
        res = run_velo_emit_c(code)
        assert res.returncode != 0
        assert "+= 0" not in res.stdout

    def test_emit_c_dynamic_step_contains_fail_fast_guard(self):
        code = """
        act main() -> i32 {
            let s: i32 = 2
            loop i in 0..10:s { }
            return 0
        }
        """
        res = run_velo_emit_c(code)
        assert res.returncode == 0
        assert "if (__step_i <= 0) { velo_panic_range_step(" in res.stdout
        assert "+= 0" not in res.stdout

    def test_emit_c_unsigned_dynamic_step_contains_zero_guard(self):
        code = """
        act main() -> i32 {
            let s: u32 = 2u32
            loop i in 0u32..10u32:s { }
            return 0
        }
        """
        res = run_velo_emit_c(code)
        assert res.returncode == 0
        assert "if (__step_i == 0) { velo_panic_range_step(" in res.stdout
        assert "+= 0" not in res.stdout

    def test_emit_c_anonymous_dynamic_step_contains_guard(self):
        code = """
        act main() -> i32 {
            let s: i32 = 2
            loop 0..10:s { }
            return 0
        }
        """
        res = run_velo_emit_c(code)
        assert res.returncode == 0
        assert "if (__step_it <= 0) { velo_panic_range_step(" in res.stdout

