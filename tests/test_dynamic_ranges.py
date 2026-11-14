"""
tests/test_dynamic_ranges.py — Test Matrix for Dynamic Endpoint Range Loops (Phase 56)

Audit ID: AUDIT-2026-11-05
Verifies range loop direction selection, iteration counts, and emitted C
when endpoints are runtime variables or dynamic expressions (n..0, n..m, 0..n, n..=0),
including mixed integer types, inclusive bounds, equal endpoints, and step increments.

Establishes the Red Baseline for Phase 56 (Task 56.1).
"""

import os
import subprocess
import sys
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
            pytest.fail(f"Execution timed out after {timeout}s (infinite loop detected): {e}")


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


def check_velo_source(source_code: str) -> subprocess.CompletedProcess:
    """Runs `bin/velo.exe check` to verify compile-time semantic analysis and diagnostics."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_path = Path(tmp_dir) / "test.vl"
        src_path.write_text(source_code, encoding="utf-8")

        return subprocess.run(
            ["bin/velo.exe", "check", str(src_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=Path.cwd()
        )


# ==============================================================================
# 1. Basic Dynamic Variable Ranges (n..0, n..m, 0..n)
# ==============================================================================

def test_dynamic_descending_var_to_literal():
    """Defect: `let n = 5; loop i in n..0` must iterate 5, 4, 3, 2, 1 (5 iterations)."""
    code = """
act main() -> i32 {
    let n: i32 = 5
    mut iters: i32 = 0
    mut last_i: i32 = -1
    loop i in n..0 {
        iters += 1
        last_i = i
    }
    assert(iters == 5)
    assert(last_i == 1)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_descending_var_to_var():
    """Defect: `let n = 5; let m = 0; loop i in n..m` must iterate 5, 4, 3, 2, 1 (5 iterations)."""
    code = """
act main() -> i32 {
    let n: i32 = 5
    let m: i32 = 0
    mut iters: i32 = 0
    mut last_i: i32 = -1
    loop i in n..m {
        iters += 1
        last_i = i
    }
    assert(iters == 5)
    assert(last_i == 1)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_ascending_literal_to_var():
    """Ascending dynamic: `let n = 5; loop i in 0..n` iterates 0, 1, 2, 3, 4 (5 iterations)."""
    code = """
act main() -> i32 {
    let n: i32 = 5
    mut iters: i32 = 0
    mut last_i: i32 = -1
    loop i in 0..n {
        iters += 1
        last_i = i
    }
    assert(iters == 5)
    assert(last_i == 4)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_ascending_var_to_var():
    """Ascending dynamic: `let n = 0; let m = 5; loop i in n..m` iterates 0, 1, 2, 3, 4 (5 iterations)."""
    code = """
act main() -> i32 {
    let n: i32 = 0
    let m: i32 = 5
    mut iters: i32 = 0
    mut last_i: i32 = -1
    loop i in n..m {
        iters += 1
        last_i = i
    }
    assert(iters == 5)
    assert(last_i == 4)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


# ==============================================================================
# 2. Inclusive Dynamic Ranges (n..=0, n..=m, 0..=n)
# ==============================================================================

def test_dynamic_descending_var_to_literal_inclusive():
    """Defect: `let n = 5; loop i in n..=0` must iterate 5, 4, 3, 2, 1, 0 (6 iterations)."""
    code = """
act main() -> i32 {
    let n: i32 = 5
    mut iters: i32 = 0
    mut last_i: i32 = -1
    loop i in n..=0 {
        iters += 1
        last_i = i
    }
    assert(iters == 6)
    assert(last_i == 0)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_descending_var_to_var_inclusive():
    """Defect: `let n = 5; let m = 0; loop i in n..=m` must iterate 5, 4, 3, 2, 1, 0 (6 iterations)."""
    code = """
act main() -> i32 {
    let n: i32 = 5
    let m: i32 = 0
    mut iters: i32 = 0
    mut last_i: i32 = -1
    loop i in n..=m {
        iters += 1
        last_i = i
    }
    assert(iters == 6)
    assert(last_i == 0)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_ascending_literal_to_var_inclusive():
    """Ascending inclusive: `let n = 5; loop i in 0..=n` iterates 0, 1, 2, 3, 4, 5 (6 iterations)."""
    code = """
act main() -> i32 {
    let n: i32 = 5
    mut iters: i32 = 0
    mut last_i: i32 = -1
    loop i in 0..=n {
        iters += 1
        last_i = i
    }
    assert(iters == 6)
    assert(last_i == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_ascending_var_to_var_inclusive():
    """Ascending inclusive: `let n = 0; let m = 5; loop i in n..=m` iterates 0, 1, 2, 3, 4, 5 (6 iterations)."""
    code = """
act main() -> i32 {
    let n: i32 = 0
    let m: i32 = 5
    mut iters: i32 = 0
    mut last_i: i32 = -1
    loop i in n..=m {
        iters += 1
        last_i = i
    }
    assert(iters == 6)
    assert(last_i == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


# ==============================================================================
# 3. Equal Dynamic Endpoints (n..n, n..=n)
# ==============================================================================

def test_dynamic_equal_endpoints_exclusive():
    """Equal endpoints exclusive: `let n = 5; loop i in n..n` executes exactly 0 iterations."""
    code = """
act main() -> i32 {
    let n: i32 = 5
    mut iters: i32 = 0
    loop i in n..n {
        iters += 1
    }
    assert(iters == 0)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_equal_endpoints_inclusive():
    """Equal endpoints inclusive: `let n = 5; loop i in n..=n` executes exactly 1 iteration (value 5)."""
    code = """
act main() -> i32 {
    let n: i32 = 5
    mut iters: i32 = 0
    mut last_i: i32 = -1
    loop i in n..=n {
        iters += 1
        last_i = i
    }
    assert(iters == 1)
    assert(last_i == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


# ==============================================================================
# 4. Stepped Dynamic Ranges (n..0:2, 0..n:2)
# ==============================================================================

def test_dynamic_descending_stepped():
    """Defect: `let n = 10; loop i in n..0:2` must iterate 10, 8, 6, 4, 2 (5 iterations)."""
    code = """
act main() -> i32 {
    let n: i32 = 10
    mut iters: i32 = 0
    mut last_i: i32 = -1
    loop i in n..0:2 {
        iters += 1
        last_i = i
    }
    assert(iters == 5)
    assert(last_i == 2)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_descending_stepped_inclusive():
    """Defect: `let n = 10; loop i in n..=0:2` must iterate 10, 8, 6, 4, 2, 0 (6 iterations)."""
    code = """
act main() -> i32 {
    let n: i32 = 10
    mut iters: i32 = 0
    mut last_i: i32 = -1
    loop i in n..=0:2 {
        iters += 1
        last_i = i
    }
    assert(iters == 6)
    assert(last_i == 0)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_ascending_stepped():
    """Ascending stepped: `let n = 10; loop i in 0..n:2` iterates 0, 2, 4, 6, 8 (5 iterations)."""
    code = """
act main() -> i32 {
    let n: i32 = 10
    mut iters: i32 = 0
    mut last_i: i32 = -1
    loop i in 0..n:2 {
        iters += 1
        last_i = i
    }
    assert(iters == 5)
    assert(last_i == 8)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_ascending_stepped_inclusive():
    """Ascending stepped inclusive: `let n = 10; loop i in 0..=n:2` iterates 0, 2, 4, 6, 8, 10 (6 iterations)."""
    code = """
act main() -> i32 {
    let n: i32 = 10
    mut iters: i32 = 0
    mut last_i: i32 = -1
    loop i in 0..=n:2 {
        iters += 1
        last_i = i
    }
    assert(iters == 6)
    assert(last_i == 10)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


# ==============================================================================
# 5. Wider Integer Types (i64, u32, u64, usize)
# ==============================================================================

def test_dynamic_i64_descending():
    """Defect: `let n: i64 = 5i64; loop i in n..0i64` must iterate 5, 4, 3, 2, 1 (5 iterations)."""
    code = """
act main() -> i32 {
    let n: i64 = 5i64
    mut iters: i32 = 0
    mut last_i: i64 = -1i64
    loop i in n..0i64 {
        iters += 1
        last_i = i
    }
    assert(iters == 5)
    assert(last_i == 1i64)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_i64_ascending():
    """Ascending i64: `let n: i64 = 5i64; loop i in 0i64..n` iterates 5 times."""
    code = """
act main() -> i32 {
    let n: i64 = 5i64
    mut iters: i32 = 0
    mut last_i: i64 = -1i64
    loop i in 0i64..n {
        iters += 1
        last_i = i
    }
    assert(iters == 5)
    assert(last_i == 4i64)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_u32_descending():
    """Defect: `let n: u32 = 5u32; loop i in n..0u32` must iterate 5, 4, 3, 2, 1 (5 iterations)."""
    code = """
act main() -> i32 {
    let n: u32 = 5u32
    mut iters: i32 = 0
    mut last_i: u32 = 0u32
    loop i in n..0u32 {
        iters += 1
        last_i = i
    }
    assert(iters == 5)
    assert(last_i == 1u32)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_u32_ascending():
    """Ascending u32: `let n: u32 = 5u32; loop i in 0u32..n` iterates 5 times."""
    code = """
act main() -> i32 {
    let n: u32 = 5u32
    mut iters: i32 = 0
    mut last_i: u32 = 0u32
    loop i in 0u32..n {
        iters += 1
        last_i = i
    }
    assert(iters == 5)
    assert(last_i == 4u32)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_u64_descending():
    """Defect: `let n: u64 = 5u64; loop i in n..0u64` must iterate 5, 4, 3, 2, 1 (5 iterations)."""
    code = """
act main() -> i32 {
    let n: u64 = 5u64
    mut iters: i32 = 0
    mut last_i: u64 = 0u64
    loop i in n..0u64 {
        iters += 1
        last_i = i
    }
    assert(iters == 5)
    assert(last_i == 1u64)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_u64_ascending():
    """Ascending u64: `let n: u64 = 5u64; loop i in 0u64..n` iterates 5 times."""
    code = """
act main() -> i32 {
    let n: u64 = 5u64
    mut iters: i32 = 0
    mut last_i: u64 = 0u64
    loop i in 0u64..n {
        iters += 1
        last_i = i
    }
    assert(iters == 5)
    assert(last_i == 4u64)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_usize_descending():
    """Defect: `let n: usize = 5usize; loop i in n..0usize` must iterate 5, 4, 3, 2, 1 (5 iterations)."""
    code = """
act main() -> i32 {
    let n: usize = 5usize
    mut iters: i32 = 0
    mut last_i: usize = 0usize
    loop i in n..0usize {
        iters += 1
        last_i = i
    }
    assert(iters == 5)
    assert(last_i == 1usize)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_usize_ascending():
    """Ascending usize: `let n: usize = 5usize; loop i in 0usize..n` iterates 5 times."""
    code = """
act main() -> i32 {
    let n: usize = 5usize
    mut iters: i32 = 0
    mut last_i: usize = 0usize
    loop i in 0usize..n {
        iters += 1
        last_i = i
    }
    assert(iters == 5)
    assert(last_i == 4usize)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


# ==============================================================================
# 6. Sign-Crossing Dynamic Ranges (-3..3, 3..-3)
# ==============================================================================

def test_dynamic_sign_crossing_descending():
    """Defect: `let n = 3; let m = -3; loop i in n..m` must iterate 3, 2, 1, 0, -1, -2 (6 iters, sum 3)."""
    code = """
act main() -> i32 {
    let n: i32 = 3
    let m: i32 = -3
    mut iters: i32 = 0
    mut sum: i32 = 0
    loop i in n..m {
        iters += 1
        sum += i
    }
    assert(iters == 6)
    assert(sum == 3)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_sign_crossing_descending_inclusive():
    """Defect: `let n = 3; let m = -3; loop i in n..=m` must iterate 3, 2, 1, 0, -1, -2, -3 (7 iters, sum 0)."""
    code = """
act main() -> i32 {
    let n: i32 = 3
    let m: i32 = -3
    mut iters: i32 = 0
    mut sum: i32 = 0
    loop i in n..=m {
        iters += 1
        sum += i
    }
    assert(iters == 7)
    assert(sum == 0)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_sign_crossing_ascending():
    """Ascending sign crossing: `let n = -3; let m = 3; loop i in n..m` iterates 6 iters (sum -3)."""
    code = """
act main() -> i32 {
    let n: i32 = -3
    let m: i32 = 3
    mut iters: i32 = 0
    mut sum: i32 = 0
    loop i in n..m {
        iters += 1
        sum += i
    }
    assert(iters == 6)
    assert(sum == -3)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_sign_crossing_ascending_inclusive():
    """Ascending sign crossing inclusive: `let n = -3; let m = 3; loop i in n..=m` iterates 7 iters (sum 0)."""
    code = """
act main() -> i32 {
    let n: i32 = -3
    let m: i32 = 3
    mut iters: i32 = 0
    mut sum: i32 = 0
    loop i in n..=m {
        iters += 1
        sum += i
    }
    assert(iters == 7)
    assert(sum == 0)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


# ==============================================================================
# 7. Anonymous Dynamic Ranges (loop n..0, loop 0..n)
# ==============================================================================

def test_dynamic_anonymous_descending():
    """Defect: `let n = 5; loop n..0` must iterate exactly 5 times."""
    code = """
act main() -> i32 {
    let n: i32 = 5
    mut iters: i32 = 0
    loop n..0 {
        iters += 1
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_anonymous_ascending():
    """Anonymous ascending: `let n = 5; loop 0..n` iterates exactly 5 times."""
    code = """
act main() -> i32 {
    let n: i32 = 5
    mut iters: i32 = 0
    loop 0..n {
        iters += 1
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


# ==============================================================================
# 8. Diagnostic Probe: Emitted C Inspection for Dynamic Ranges
# ==============================================================================

def test_emitted_c_dynamic_descending_runtime_direction():
    """Verify emitted C lowers dynamic direction selection using __rev temporary."""
    code = """
act main() -> i32 {
    let n: i32 = 5
    loop i in n..0 { }
    return 0
}
"""
    c_code = emit_c_velo_source(code)
    assert "__rev_i = (__start_i > __end_i)" in c_code
    assert "__rev_i ? (i > __end_i) : (i < __end_i)" in c_code
    assert "__rev_i ? (i--) : (i++)" in c_code


def test_emitted_c_dynamic_var_to_var_runtime_direction():
    """Verify emitted C lowers dynamic direction selection for variable to variable bounds."""
    code = """
act main() -> i32 {
    let n: i32 = 5
    let m: i32 = 0
    loop i in n..m { }
    return 0
}
"""
    c_code = emit_c_velo_source(code)
    assert "__start_i = (n)" in c_code and "__end_i = (m)" in c_code
    assert "__rev_i = (__start_i > __end_i)" in c_code
    assert "__rev_i ? (i > __end_i) : (i < __end_i)" in c_code


# ==============================================================================
# 9. Endpoint Expressions Evaluated Exactly Once (Side Effect & TOCTOU Immunity)
# ==============================================================================

def test_dynamic_endpoint_function_call_evaluated_once_start():
    """Start expression with function call side effect is evaluated exactly once."""
    code = """
mut start_calls: i32 = 0

act get_start() -> i32 {
    start_calls += 1
    return 1
}

act main() -> i32 {
    mut count: i32 = 0
    loop i in get_start()..5 {
        count += 1
    }
    assert(start_calls == 1)
    assert(count == 4)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_endpoint_function_call_evaluated_once_end():
    """End expression with function call side effect is evaluated exactly once, not on each iteration."""
    code = """
mut end_calls: i32 = 0

act get_end() -> i32 {
    end_calls += 1
    return 5
}

act main() -> i32 {
    mut count: i32 = 0
    loop i in 0..get_end() {
        count += 1
    }
    assert(end_calls == 1)
    assert(count == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_endpoint_function_call_evaluated_once_inclusive_end():
    """Inclusive end expression with function call is evaluated exactly once."""
    code = """
mut end_calls: i32 = 0

act get_end() -> i32 {
    end_calls += 1
    return 5
}

act main() -> i32 {
    mut count: i32 = 0
    loop i in 0..=get_end() {
        count += 1
    }
    assert(end_calls == 1)
    assert(count == 6)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_step_function_call_evaluated_once():
    """Step expression with function call is evaluated exactly once, not on each iteration."""
    code = """
mut step_calls: i32 = 0

act get_step() -> i32 {
    step_calls += 1
    return 2
}

act main() -> i32 {
    mut count: i32 = 0
    loop i in 0..10 : get_step() {
        count += 1
    }
    assert(step_calls == 1)
    assert(count == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_endpoint_mutation_mid_loop_toctou_immune():
    """Mutating the variable used in end bound mid-loop does not alter loop termination."""
    code = """
act main() -> i32 {
    mut limit: i32 = 5
    mut count: i32 = 0
    loop i in 0..limit {
        count += 1
        limit = 0
    }
    assert(count == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_step_mutation_mid_loop_toctou_immune():
    """Mutating the variable used in step mid-loop does not alter the stride."""
    code = """
act main() -> i32 {
    mut step_val: i32 = 1
    mut count: i32 = 0
    loop i in 0..10 : step_val {
        count += 1
        step_val = 100
    }
    assert(count == 10)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_endpoint_both_start_and_end_side_effects():
    """Both start and end expressions evaluate in lexical order exactly once."""
    code = """
mut call_order: i32 = 0
mut start_order: i32 = 0
mut end_order: i32 = 0

act eval_start() -> i32 {
    call_order += 1
    start_order = call_order
    return 2
}

act eval_end() -> i32 {
    call_order += 1
    end_order = call_order
    return 6
}

act main() -> i32 {
    mut sum: i32 = 0
    loop i in eval_start()..eval_end() {
        sum += i
    }
    assert(start_order == 1)
    assert(end_order == 2)
    assert(sum == 14)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_dynamic_endpoint_nested_loops_single_evaluation():
    """Nested dynamic loops evaluate outer bound once and inner bound once per outer iteration."""
    code = """
mut outer_calls: i32 = 0
mut inner_calls: i32 = 0

act get_outer() -> i32 {
    outer_calls += 1
    return 3
}

act get_inner() -> i32 {
    inner_calls += 1
    return 2
}

act main() -> i32 {
    mut total: i32 = 0
    loop i in 0..get_outer() {
        loop j in 0..get_inner() {
            total += 1
        }
    }
    assert(outer_calls == 1)
    assert(inner_calls == 3)
    assert(total == 6)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_emitted_c_endpoint_hoisting_temps():
    """Verify C99 emission declares __start_i, __end_i, __rev_i, and loop var in loop header."""
    code = """
act main() -> i32 {
    let a: i32 = 10
    let b: i32 = 20
    loop i in a..b { }
    return 0
}
"""
    c_code = emit_c_velo_source(code)
    assert "for (int32_t __start_i = (a), __end_i = (b), __rev_i = (__start_i > __end_i), i = __start_i; __rev_i ? (i > __end_i) : (i < __end_i); __rev_i ? (i--) : (i++))" in c_code


def test_emitted_c_stepped_hoisting_temps():
    """Verify C99 emission declares __start_i, __end_i, __step_i, __rev_i, and loop var in loop header."""
    code = """
act main() -> i32 {
    let a: i32 = 10
    let b: i32 = 20
    let s: i32 = 2
    loop i in a..b:s { }
    return 0
}
"""
    c_code = emit_c_velo_source(code)
    assert "for (int32_t __start_i = (a), __end_i = (b), __step_i = (s), __rev_i = (__start_i > __end_i), i = __start_i; __rev_i ? (i > __end_i) : (i < __end_i); __rev_i ? (i -= __step_i) : (i += __step_i))" in c_code


# ==============================================================================
# 10. Mixed-Type Endpoint Compatibility & Promotion (Task 56.5)
# ==============================================================================

def test_mixed_type_i32_u32_rejected():
    """Security Gate: Mixing signed i32 variable with unsigned u32 variable is rejected."""
    code = """
act main() -> i32 {
    let a: i32 = 0
    let b: u32 = 10
    loop i in a..b { }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Cannot mix signed 'i32' and unsigned 'u32'" in out


def test_mixed_type_u32_i32_rejected():
    """Security Gate: Mixing unsigned u32 variable with signed i32 variable is rejected."""
    code = """
act main() -> i32 {
    let a: u32 = 10
    let b: i32 = 0
    loop i in a..b { }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Cannot mix unsigned 'u32' and signed 'i32'" in out


def test_mixed_type_i64_u64_rejected():
    """Security Gate: Mixing signed i64 variable with unsigned u64 variable is rejected."""
    code = """
act main() -> i32 {
    let a: i64 = 0
    let b: u64 = 10
    loop i in a..b { }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Cannot mix signed 'i64' and unsigned 'u64'" in out


def test_mixed_type_u64_i64_rejected():
    """Security Gate: Mixing unsigned u64 variable with signed i64 variable is rejected."""
    code = """
act main() -> i32 {
    let a: u64 = 10
    let b: i64 = 0
    loop i in a..b { }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Cannot mix unsigned 'u64' and signed 'i64'" in out


def test_mixed_type_usize_literal_zero_accepted():
    """Unsuffixed literal 0 adapts to usize target type without diagnostic."""
    code = """
act main() -> i32 {
    let n: usize = 5
    mut iters: i32 = 0
    loop i in n..0 {
        iters += 1
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_mixed_type_literal_zero_usize_accepted():
    """Unsuffixed literal 0 adapts to ascending usize target type without diagnostic."""
    code = """
act main() -> i32 {
    let n: usize = 5
    mut iters: i32 = 0
    loop i in 0..n {
        iters += 1
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_mixed_type_explicit_cast_accepted():
    """Explicit cast resolves signed/unsigned difference safely."""
    code = """
act main() -> i32 {
    let a: i32 = 0
    let b: u32 = 5
    mut iters: i32 = 0
    loop i in (a as u32)..b {
        iters += 1
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_mixed_type_same_signedness_widening_i32_i64():
    """Same signedness i32 and i64 safely widens to i64."""
    code = """
act main() -> i32 {
    let a: i32 = 0
    let b: i64 = 5
    mut iters: i32 = 0
    loop i in a..b {
        iters += 1
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_mixed_type_same_signedness_widening_descending_i64_i32():
    """Same signedness i64 and i32 descending safely widens to i64."""
    code = """
act main() -> i32 {
    let a: i64 = 5
    let b: i32 = 0
    mut iters: i32 = 0
    loop i in a..b {
        iters += 1
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_mixed_type_same_signedness_widening_u32_u64():
    """Same signedness u32 and u64 safely widens to u64."""
    code = """
act main() -> i32 {
    let a: u32 = 0
    let b: u64 = 5
    mut iters: i32 = 0
    loop i in a..b {
        iters += 1
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


# ==============================================================================
# 11. Emitted-C and Runtime Matrix Cross-Verification (Task 56.6)
# ==============================================================================

@pytest.mark.parametrize(
    "start,end,inclusive,expected_iters,expected_first,expected_last,expected_sum",
    [
        # Ascending exclusive / inclusive
        (0, 5, False, 5, 0, 4, 10),
        (0, 5, True, 6, 0, 5, 15),
        # Descending exclusive / inclusive
        (5, 0, False, 5, 5, 1, 15),
        (5, 0, True, 6, 5, 0, 15),
        # Equal endpoints
        (5, 5, False, 0, None, None, 0),
        (5, 5, True, 1, 5, 5, 5),
        # Negative bounds ascending
        (-5, 0, False, 5, -5, -1, -15),
        (-5, 0, True, 6, -5, 0, -15),
        # Negative bounds descending
        (0, -5, False, 5, 0, -4, -10),
        (0, -5, True, 6, 0, -5, -15),
        # Sign-crossing descending
        (3, -3, False, 6, 3, -2, 3),
        (3, -3, True, 7, 3, -3, 0),
        # Sign-crossing ascending
        (-3, 3, False, 6, -3, 2, -3),
        (-3, 3, True, 7, -3, 3, 0),
    ]
)
def test_matrix_emitted_c_and_runtime_dynamic_ranges(
    start, end, inclusive, expected_iters, expected_first, expected_last, expected_sum
):
    """Matrix row cross-verification: checks emitted C structure and runtime execution."""
    op = "..=" if inclusive else ".."
    code = f"""
act main() -> i32 {{
    let a: i32 = {start}
    let b: i32 = {end}
    mut iters: i32 = 0
    mut first_val: i32 = 9999
    mut last_val: i32 = 9999
    mut total: i32 = 0
    loop i in a{op}b {{
        if iters == 0 {{
            first_val = i
        }}
        last_val = i
        iters += 1
        total += i
    }}
    assert(iters == {expected_iters})
    assert(total == {expected_sum})
"""
    if expected_iters > 0:
        code += f"""
    assert(first_val == {expected_first})
    assert(last_val == {expected_last})
"""
    code += """
    return 0
}
"""
    # 1. Assert emitted C contains dynamic direction branch, relational comparison, and step increment
    c_code = emit_c_velo_source(code)
    assert "__start_i = (a)" in c_code
    assert "__end_i = (b)" in c_code
    assert "__rev_i = (__start_i > __end_i)" in c_code
    if inclusive:
        assert "__rev_i ? (i >= __end_i) : (i <= __end_i)" in c_code
    else:
        assert "__rev_i ? (i > __end_i) : (i < __end_i)" in c_code
    assert "__rev_i ? (i--) : (i++)" in c_code

    # 2. Assert runtime execution matches expected bounds and counts without timeout
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


@pytest.mark.parametrize(
    "start,end,step,inclusive,expected_iters,expected_first,expected_last,expected_sum",
    [
        # Ascending stepped divisible
        (0, 10, 2, False, 5, 0, 8, 20),
        (0, 10, 2, True, 6, 0, 10, 30),
        # Descending stepped divisible
        (10, 0, 2, False, 5, 10, 2, 30),
        (10, 0, 2, True, 6, 10, 0, 30),
        # Ascending stepped exact boundary
        (0, 9, 3, False, 3, 0, 6, 9),
        (0, 9, 3, True, 4, 0, 9, 18),
        # Descending stepped exact boundary
        (9, 0, 3, False, 3, 9, 3, 18),
        (9, 0, 3, True, 4, 9, 0, 18),
        # Ascending stepped non-divisible
        (0, 10, 3, False, 4, 0, 9, 18),
        (0, 10, 3, True, 4, 0, 9, 18),
        # Descending stepped non-divisible
        (10, 0, 3, False, 4, 10, 1, 22),
        (10, 0, 3, True, 4, 10, 1, 22),
        # Stepped equal endpoints
        (10, 10, 2, False, 0, None, None, 0),
        (10, 10, 2, True, 1, 10, 10, 10),
        # Negative bounds stepped
        (-10, 0, 3, False, 4, -10, -1, -22),
        (0, -10, 3, False, 4, 0, -9, -18),
    ]
)
def test_matrix_emitted_c_and_runtime_stepped_dynamic_ranges(
    start, end, step, inclusive, expected_iters, expected_first, expected_last, expected_sum
):
    """Matrix row cross-verification for stepped ranges: emitted C step and runtime execution."""
    op = "..=" if inclusive else ".."
    code = f"""
act main() -> i32 {{
    let a: i32 = {start}
    let b: i32 = {end}
    let s: i32 = {step}
    mut iters: i32 = 0
    mut first_val: i32 = 9999
    mut last_val: i32 = 9999
    mut total: i32 = 0
    loop i in a{op}b:s {{
        if iters == 0 {{
            first_val = i
        }}
        last_val = i
        iters += 1
        total += i
    }}
    assert(iters == {expected_iters})
    assert(total == {expected_sum})
"""
    if expected_iters > 0:
        code += f"""
    assert(first_val == {expected_first})
    assert(last_val == {expected_last})
"""
    code += """
    return 0
}
"""
    # 1. Assert emitted C contains step temporary and ternary stepping
    c_code = emit_c_velo_source(code)
    assert "__start_i = (a)" in c_code
    assert "__end_i = (b)" in c_code
    assert "__step_i = (s)" in c_code
    assert "__rev_i = (__start_i > __end_i)" in c_code
    if inclusive:
        assert "__rev_i ? (i >= __end_i) : (i <= __end_i)" in c_code
    else:
        assert "__rev_i ? (i > __end_i) : (i < __end_i)" in c_code
    assert "__rev_i ? (i -= __step_i) : (i += __step_i)" in c_code

    # 2. Assert runtime execution matches
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_matrix_emitted_c_and_runtime_wide_i64():
    """Verify emitted C int64_t and runtime execution for 64-bit signed ranges."""
    code = """
act main() -> i32 {
    let a: i64 = 5000000000
    let b: i64 = 4999999995
    mut iters: i32 = 0
    mut first_val: i64 = 0
    mut last_val: i64 = 0
    loop i in a..b {
        if iters == 0 {
            first_val = i
        }
        last_val = i
        iters += 1
    }
    assert(iters == 5)
    assert(first_val == 5000000000)
    assert(last_val == 4999999996)
    return 0
}
"""
    c_code = emit_c_velo_source(code)
    assert "int64_t __start_i = (a), __end_i = (b), __rev_i = (__start_i > __end_i), i = __start_i" in c_code
    assert "__rev_i ? (i > __end_i) : (i < __end_i)" in c_code
    assert "__rev_i ? (i--) : (i++)" in c_code

    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_matrix_emitted_c_and_runtime_wide_u64():
    """Verify emitted C uint64_t and runtime execution for 64-bit unsigned ranges."""
    code = """
act main() -> i32 {
    let a: u64 = 5000000005
    let b: u64 = 5000000000
    mut iters: i32 = 0
    mut first_val: u64 = 0
    mut last_val: u64 = 0
    loop i in a..b {
        if iters == 0 {
            first_val = i
        }
        last_val = i
        iters += 1
    }
    assert(iters == 5)
    assert(first_val == 5000000005)
    assert(last_val == 5000000001)
    return 0
}
"""
    c_code = emit_c_velo_source(code)
    assert "uint64_t __start_i = (a), __end_i = (b), __rev_i = (__start_i > __end_i), i = __start_i" in c_code
    assert "__rev_i ? (i > __end_i) : (i < __end_i)" in c_code
    assert "__rev_i ? (i--) : (i++)" in c_code

    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_matrix_emitted_c_and_runtime_wide_usize_stepped():
    """Verify emitted C size_t and runtime execution for stepped usize ranges."""
    code = """
act main() -> i32 {
    let a: usize = 10usize
    let b: usize = 0usize
    let s: usize = 2usize
    mut iters: i32 = 0
    mut first_val: usize = 0usize
    mut last_val: usize = 0usize
    loop i in a..b:s {
        if iters == 0 {
            first_val = i
        }
        last_val = i
        iters += 1
    }
    assert(iters == 5)
    assert(first_val == 10usize)
    assert(last_val == 2usize)
    return 0
}
"""
    c_code = emit_c_velo_source(code)
    assert "size_t __start_i = (a), __end_i = (b), __step_i = (s), __rev_i = (__start_i > __end_i), i = __start_i" in c_code
    assert "__rev_i ? (i -= __step_i) : (i += __step_i)" in c_code

    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


# ==============================================================================
# 12. Security and Negative Gate Validation (Task 56.7)
# ==============================================================================

def test_negative_dynamic_float_start_rejected():
    """Security Invariant: Float start endpoint must fail closed at velo check."""
    code = """
act main() -> i32 {
    let start: f32 = 1.5
    loop i in start..10 { }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Range loop start endpoint must be an integer type, got 'f32'" in out


def test_negative_dynamic_float_end_rejected():
    """Security Invariant: Float end endpoint must fail closed at velo check."""
    code = """
act main() -> i32 {
    let end: f64 = 10.5
    loop i in 0..end { }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Range loop end endpoint must be an integer type, got 'f64'" in out


def test_negative_dynamic_string_start_rejected():
    """Security Invariant: String start endpoint must fail closed at velo check."""
    code = """
act main() -> i32 {
    let s: string = "hello"
    loop i in s..10 { }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Range loop start endpoint must be an integer type, got 'string'" in out


def test_negative_dynamic_string_end_rejected():
    """Security Invariant: String end endpoint must fail closed at velo check."""
    code = """
act main() -> i32 {
    let s: string = "world"
    loop i in 0..s { }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Range loop end endpoint must be an integer type, got 'string'" in out


def test_negative_dynamic_struct_start_rejected():
    """Security Invariant: Custom struct start endpoint must fail closed at velo check."""
    code = """
data Point { x: i32, y: i32 }
act main() -> i32 {
    let p = Point{ x: 0, y: 0 }
    loop i in p..10 { }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Range loop start endpoint must be an integer type, got 'Point'" in out


def test_negative_dynamic_struct_end_rejected():
    """Security Invariant: Custom struct end endpoint must fail closed at velo check."""
    code = """
data Point { x: i32, y: i32 }
act main() -> i32 {
    let p = Point{ x: 10, y: 10 }
    loop i in 0..p { }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Range loop end endpoint must be an integer type, got 'Point'" in out


def test_negative_dynamic_float_step_rejected():
    """Security Invariant: Float step expression must fail closed at velo check."""
    code = """
act main() -> i32 {
    let s: f32 = 2.5
    loop i in 0..10:s { }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Range loop step must be an integer type, got 'f32'" in out


def test_negative_dynamic_string_step_rejected():
    """Security Invariant: String step expression must fail closed at velo check."""
    code = """
act main() -> i32 {
    let s: string = "two"
    loop i in 0..10:s { }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Range loop step must be an integer type, got 'string'" in out


def test_negative_zero_step_unsuffixed_rejected():
    """Security Invariant: Literal zero step must fail closed with positive step diagnostic."""
    code = """
act main() -> i32 {
    let n: i32 = 10
    loop i in 0..n:0 { }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Range loop step must be greater than zero" in out


def test_negative_zero_step_suffixed_rejected():
    """Security Invariant: Suffixed zero steps (0u64, 0i32, 0usize) must fail closed."""
    for zero_str in ["0i32", "0u32", "0i64", "0u64", "0usize", "0x0", "0b0"]:
        code = f"""
act main() -> i32 {{
    let n: i32 = 10
    loop i in 0..n:{zero_str} {{ }}
    return 0
}}
"""
        res = check_velo_source(code)
        assert res.returncode != 0, f"Expected rejection for step {zero_str}"
        out = res.stdout + res.stderr
        assert "Range loop step must be greater than zero" in out


def test_negative_negative_step_rejected():
    """Security Invariant: Negative step literal must fail closed with positive step diagnostic."""
    code = """
act main() -> i32 {
    let n: i32 = 10
    loop i in 0..n:-2 { }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Range loop step must be greater than zero" in out


def test_negative_endpoint_literal_overflow_64bit_rejected():
    """Security Invariant: Literals exceeding 64-bit maximum fail closed at compile time."""
    code = """
act main() -> i32 {
    let a: i32 = 0
    loop i in a..99999999999999999999999999 { }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "exceeds 64-bit unsigned maximum" in out


def test_negative_endpoint_literal_overflow_i32_rejected():
    """Security Invariant: Explicitly suffixed literal overflowing i32 fails closed."""
    code = """
act main() -> i32 {
    let a: i32 = 0
    loop i in a..3000000000i32 { }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Integer literal out of range for type 'i32'" in out


def test_negative_endpoint_literal_overflow_u32_rejected():
    """Security Invariant: Explicitly suffixed literal overflowing u32 fails closed."""
    code = """
act main() -> i32 {
    let a: u32 = 0
    loop i in a..5000000000u32 { }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Integer literal out of range for type 'u32'" in out


def test_negative_unsigned_negative_end_literal_rejected():
    """Security Invariant: Negative literal endpoint for unsigned range fails closed."""
    code = """
act main() -> i32 {
    let a: u32 = 0
    loop i in a..-5 { }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Range loop endpoint cannot be negative for unsigned type 'u32'" in out


def test_negative_unsigned_negative_start_literal_rejected():
    """Security Invariant: Negative literal start endpoint for unsigned range fails closed."""
    code = """
act main() -> i32 {
    let a: usize = 0usize
    loop i in -1..a { }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Range loop endpoint cannot be negative for unsigned type 'usize'" in out


def test_negative_boolean_endpoint_rejected():
    """Security Invariant: Boolean endpoint must fail closed at velo check."""
    code = """
act main() -> i32 {
    let b: bool = true
    loop i in b..10 { }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Range loop start endpoint must be an integer type, got 'bool'" in out






