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

def test_emitted_c_dynamic_descending_proves_ascending_defect():
    """Diagnostic Probe: Proves that `loop i in n..0` hoists endpoints into temporaries but still emits ascending condition `i < __end_i; i++`."""
    code = """
act main() -> i32 {
    let n: i32 = 5
    loop i in n..0 { }
    return 0
}
"""
    c_code = emit_c_velo_source(code)
    # Task 56.3 hoists start and end into temporaries.
    # The remaining defect (to be solved in Task 56.4) is that condition is still ascending 'i < __end_i' and 'i++'.
    has_hoisted_temps = "__start_i = (n)" in c_code and "__end_i = (0)" in c_code
    has_ascending_defect = "i < __end_i" in c_code and "i++" in c_code
    assert has_hoisted_temps and has_ascending_defect, (
        f"Expected hoisted temps with baseline defect 'i < __end_i; i++' in emitted C, got:\n{c_code}"
    )


def test_emitted_c_dynamic_var_to_var_proves_ascending_defect():
    """Diagnostic Probe: Proves that `loop i in n..m` hoists endpoints into temporaries but still emits ascending condition."""
    code = """
act main() -> i32 {
    let n: i32 = 5
    let m: i32 = 0
    loop i in n..m { }
    return 0
}
"""
    c_code = emit_c_velo_source(code)
    has_hoisted_temps = "__start_i = (n)" in c_code and "__end_i = (m)" in c_code
    has_ascending_defect = "i < __end_i" in c_code and "i++" in c_code
    assert has_hoisted_temps and has_ascending_defect, (
        f"Expected hoisted temps with baseline defect 'i < __end_i; i++' in emitted C, got:\n{c_code}"
    )


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
    """Verify C99 emission declares __start_i, __end_i, and loop var in loop header."""
    code = """
act main() -> i32 {
    let a: i32 = 10
    let b: i32 = 20
    loop i in a..b { }
    return 0
}
"""
    c_code = emit_c_velo_source(code)
    assert "for (int32_t __start_i = (a), __end_i = (b), i = __start_i; i < __end_i; i++)" in c_code


def test_emitted_c_stepped_hoisting_temps():
    """Verify C99 emission declares __start_i, __end_i, __step_i, and loop var in loop header."""
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
    assert "for (int32_t __start_i = (a), __end_i = (b), __step_i = (s), i = __start_i; i < __end_i; i += __step_i)" in c_code


