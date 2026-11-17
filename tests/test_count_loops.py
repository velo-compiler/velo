"""Phase 54: loop <count> vs <condition> classification test matrix (red baseline).

Audit ID: AUDIT-2026-11-03
Tests count loops across integer widths, expressions, zero/negative counts,
side effects, boolean condition loops, and compile-time rejection of invalid types.
"""

import os
import subprocess
import tempfile
import pytest
from conftest import cc_dir, velo_exe

COMPILER = str(velo_exe())


def get_env():
    env = dict(os.environ)
    env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return env


def run_velo_source(code: str, timeout: float = 1.0) -> subprocess.CompletedProcess:
    """Compiles and executes Velo code, enforcing a strict timeout to catch infinite loops."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "test.vl")
        exe = os.path.join(tmpdir, "test_bin.exe")
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
        build_res = subprocess.run(
            [COMPILER, "build", src, "-o", exe],
            env=get_env(),
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            timeout=10.0,
        )
        if build_res.returncode != 0:
            return build_res
        try:
            return subprocess.run(
                [exe],
                capture_output=True,
                text=True, encoding="utf-8", errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            pytest.fail(f"Execution timed out ({timeout}s) - infinite loop detected: {e}")


def check_velo_source(code: str) -> subprocess.CompletedProcess:
    """Runs `velo check` to verify compile-time semantic analysis and diagnostics."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "test.vl")
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
        return subprocess.run(
            [COMPILER, "check", src],
            env=get_env(),
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            timeout=10.0,
        )


def emit_c_velo_source(code: str) -> str:
    """Runs `velo emit-c` and returns generated C code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "test.vl")
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
        res = subprocess.run(
            [COMPILER, "emit-c", src],
            env=get_env(),
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            timeout=10.0,
        )
        assert res.returncode == 0, f"emit-c failed:\n{res.stderr}\n{res.stdout}"
        return res.stdout


# ==============================================================================
# 1. Integer Widths for Count Variables
# ==============================================================================

@pytest.mark.parametrize("itype", [
    "i8", "i16", "i32", "i64",
    "u8", "u16", "u32", "u64",
    "isize", "usize",
])
def test_count_loop_variable_integer_widths(itype):
    """Verifies that `loop c` where c is any integer type iterates c times."""
    code = f"""
act main() -> i32 {{
    let c: {itype} = 3
    mut count: i32 = 0
    loop c {{
        count += 1
    }}
    assert(count == 3)
    return 0
}}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0, f"Failed for {itype}:\n{res.stdout}\n{res.stderr}"


# ==============================================================================
# 2. Integer Literals and Suffixed Literals
# ==============================================================================

def test_count_loop_unsuffixed_literal():
    """Verifies unsuffixed literal `loop 5` executes 5 times."""
    code = """
act main() -> i32 {
    mut count: i32 = 0
    loop 5 {
        count += 1
    }
    assert(count == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


@pytest.mark.parametrize("suffix", [
    "u8", "u16", "u32", "u64",
    "i8", "i16", "i32", "i64",
])
def test_count_loop_suffixed_literal(suffix):
    """Verifies suffixed literal `loop 4<suffix>` executes 4 times."""
    code = f"""
act main() -> i32 {{
    mut count: i32 = 0
    loop 4{suffix} {{
        count += 1
    }}
    assert(count == 4)
    return 0
}}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


# ==============================================================================
# 3. Non-Literal Expressions, Zero/Negative Counts, and Side Effects
# ==============================================================================

def test_count_loop_arithmetic_expression():
    """Verifies non-literal expression `loop n + 1` executes (n + 1) times."""
    code = """
act main() -> i32 {
    let n: i32 = 2
    mut count: i32 = 0
    loop n + 1 {
        count += 1
    }
    assert(count == 3)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0, f"Expected 3 iterations:\n{res.stdout}\n{res.stderr}"


def test_count_loop_complex_binary_expression():
    """Verifies complex expression `loop a * b` executes (a * b) times."""
    code = """
act main() -> i32 {
    let a: i32 = 2
    let b: i32 = 3
    mut count: i32 = 0
    loop a * b {
        count += 1
    }
    assert(count == 6)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_count_loop_literal_zero():
    """Verifies literal count of 0 terminates immediately (0 iterations)."""
    code = """
act main() -> i32 {
    mut count: i32 = 0
    loop 0 {
        count += 1
    }
    assert(count == 0)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_count_loop_variable_zero():
    """Verifies variable count of 0 (u64) terminates immediately."""
    code = """
act main() -> i32 {
    let z: u64 = 0
    mut count: i32 = 0
    loop z {
        count += 1
    }
    assert(count == 0)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_count_loop_literal_negative():
    """Verifies negative literal count `loop -1` terminates immediately (0 iterations)."""
    code = """
act main() -> i32 {
    mut count: i32 = 0
    loop -1 {
        count += 1
    }
    assert(count == 0)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_count_loop_side_effects_evaluated_once():
    """Security Invariant: Count expression with side effects must be evaluated exactly once."""
    code = """
mut g_calls: i32 = 0

act get_count() -> i32 {
    g_calls += 1
    return 3
}

act main() -> i32 {
    mut count: i32 = 0
    loop get_count() {
        count += 1
    }
    assert(g_calls == 1)
    assert(count == 3)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


# ==============================================================================
# 4. Valid Boolean Condition Loops
# ==============================================================================

def test_condition_loop_bool_variable():
    """Verifies boolean condition loop terminates when condition becomes false."""
    code = """
act main() -> i32 {
    mut flag = true
    mut count: i32 = 0
    loop flag {
        count += 1
        flag = false
    }
    assert(count == 1)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_condition_loop_bool_literal_false():
    """Verifies `loop false` terminates immediately without executing body."""
    code = """
act main() -> i32 {
    mut count: i32 = 0
    loop false {
        count += 1
    }
    assert(count == 0)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_condition_loop_relational_expression():
    """Verifies comparison expression `loop x > 0` executes condition loop."""
    code = """
act main() -> i32 {
    mut x: i32 = 5
    mut count: i32 = 0
    loop x > 0 {
        count += 1
        x -= 1
    }
    assert(count == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_condition_loop_logical_expression():
    """Verifies compound boolean expression `loop a > 0 and b > 0`."""
    code = """
act main() -> i32 {
    mut a: i32 = 3
    mut b: i32 = 5
    mut count: i32 = 0
    loop a > 0 and b > 0 {
        count += 1
        a -= 1
        b -= 1
    }
    assert(count == 3)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_condition_loop_maintains_it_counter():
    """Verifies that `it` counter is accessible and increments in condition loops."""
    code = """
act main() -> i32 {
    mut x: i32 = 3
    mut last_it: i32 = 0
    loop x > 0 {
        last_it = it as i32
        x -= 1
    }
    assert(last_it == 2)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


# ==============================================================================
# 5. Invalid Types Rejected at Compile Time (Security Invariants)
# ==============================================================================

def test_invalid_loop_float_literal_rejected():
    """Security Invariant: `loop 5.0` must be rejected at compile-time."""
    code = "act main() { loop 5.0 { } }"
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for float literal loop"
    assert "error" in res.stdout.lower() or "error" in res.stderr.lower()


def test_invalid_loop_float_variable_rejected():
    """Security Invariant: `loop f` where f is f32 must be rejected at compile-time."""
    code = "act main() { let f: f32 = 5.0\nloop f { } }"
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for f32 loop expression"
    assert "error" in res.stdout.lower() or "error" in res.stderr.lower()


def test_invalid_loop_string_literal_rejected():
    """Security Invariant: `loop \"x\"` must be rejected at compile-time."""
    code = 'act main() { loop "x" { } }'
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for string literal loop"
    assert "error" in res.stdout.lower() or "error" in res.stderr.lower()


def test_invalid_loop_string_variable_rejected():
    """Security Invariant: `loop s` where s is string must be rejected at compile-time."""
    code = 'act main() { let s: string = "hello"\nloop s { } }'
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for string variable loop"
    assert "error" in res.stdout.lower() or "error" in res.stderr.lower()


def test_invalid_loop_struct_rejected():
    """Security Invariant: `loop struct_val` must be rejected at compile-time."""
    code = """
data Point { x: i32, y: i32 }
act main() {
    let p = Point { x: 1, y: 2 }
    loop p { }
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for struct loop expression"
    assert "error" in res.stdout.lower() or "error" in res.stderr.lower()


def test_invalid_loop_pointer_rejected():
    """Security Invariant: `loop ptr` must not use pointer truthiness; must be rejected."""
    code = """
act main() {
    let x: i32 = 10
    let ptr = @x
    loop ptr { }
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for pointer loop expression"
    assert "error" in res.stdout.lower() or "error" in res.stderr.lower()


# ==============================================================================
# 6. Emitted C Syntax Independence (Task 54.3 Verification)
# ==============================================================================

@pytest.mark.parametrize("name,code,expected_pattern", [
    ("literal_int", "act main() { loop 5 { } }", "__cnt = (5)"),
    ("literal_u64", "act main() { loop 5u64 { } }", "__cnt = (5ULL)"),
    ("variable_u64", "act main() { let c: u64 = 3\nloop c { } }", "__cnt = (c)"),
    ("variable_u8", "act main() { let c: u8 = 3\nloop c { } }", "__cnt = (c)"),
    ("variable_i16", "act main() { let c: i16 = 3\nloop c { } }", "__cnt = (c)"),
    ("variable_isize", "act main() { let c: isize = 3\nloop c { } }", "__cnt = (c)"),
    ("binary_expr", "act main() { let n = 2\nloop n + 1 { } }", "__cnt = ((n + 1))"),
    ("complex_expr", "act main() { let a = 2\nlet b = 3\nloop a * b { } }", "__cnt = ((a * b))"),
    ("bool_var", "act main() { mut b = true\nloop b { } }", "; (b);"),
    ("bool_cmp", "act main() { mut x = 5\nloop x > 0 { x -= 1 } }", "; ((x > 0));"),
])
def test_loop_classification_emitted_c_syntax_independent(name, code, expected_pattern):
    """Verifies that loop classification in emitted C is type-directed and syntax-independent."""
    c_out = emit_c_velo_source(code)
    for_lines = [l.strip() for l in c_out.splitlines() if "for (" in l]
    assert len(for_lines) >= 1, f"No for loop generated:\n{c_out}"
    matched = any(expected_pattern in l for l in for_lines)
    assert matched, f"Pattern {expected_pattern!r} not found in loop headers:\n{for_lines}"


# ==============================================================================
# 7. Advanced Condition Loop Tests (Task 54.6 Verification)
# ==============================================================================

def test_condition_loop_nested_condition():
    """Verifies nested condition loops execute cleanly with proper variable scoping."""
    code = """
act main() -> i32 {
    mut outer: i32 = 3
    mut count: i32 = 0
    loop outer > 0 {
        mut inner: i32 = 2
        loop inner > 0 {
            count += 1
            inner -= 1
        }
        outer -= 1
    }
    assert(count == 6)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_condition_loop_nested_in_count_loop():
    """Verifies a condition loop nested inside a count loop executes cleanly."""
    code = """
act main() -> i32 {
    mut total: i32 = 0
    loop 3 {
        mut k: i32 = 4
        loop k > 0 {
            total += 1
            k -= 1
        }
    }
    assert(total == 12)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_count_loop_nested_in_condition_loop():
    """Verifies a count loop nested inside a condition loop executes cleanly."""
    code = """
act main() -> i32 {
    mut outer: i32 = 3
    mut total: i32 = 0
    loop outer > 0 {
        loop 4 {
            total += 1
        }
        outer -= 1
    }
    assert(total == 12)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_condition_loop_function_call():
    """Verifies condition loop driven by a function returning bool."""
    code = """
mut g_val: i32 = 0

act has_more() -> bool {
    g_val += 1
    return g_val <= 5
}

act main() -> i32 {
    mut it_count: i32 = 0
    loop has_more() {
        it_count += 1
    }
    assert(it_count == 5)
    assert(g_val == 6)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_condition_loop_it_values_accumulation():
    """Verifies `it` starts at 0 and increments strictly by 1 on each iteration."""
    code = """
act main() -> i32 {
    mut x: i32 = 5
    mut it_sum: i32 = 0
    loop x > 0 {
        it_sum += (it as i32)
        x -= 1
    }
    assert(it_sum == 10)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_condition_loop_nested_it_shadowing():
    """Verifies inner loop's `it` properly shadows outer loop's `it`."""
    code = """
act main() -> i32 {
    mut outer_iters: i32 = 0
    mut inner_it_sum: i32 = 0
    mut x: i32 = 2
    loop x > 0 {
        outer_iters += 1
        mut y: i32 = 3
        loop y > 0 {
            inner_it_sum += (it as i32)
            y -= 1
        }
        x -= 1
    }
    assert(outer_iters == 2)
    assert(inner_it_sum == 6)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_condition_loop_break():
    """Verifies `break` terminates a condition loop immediately."""
    code = """
act main() -> i32 {
    mut x: i32 = 10
    mut it_at_break: i32 = -1
    loop x > 0 {
        if (it as i32) == 3 {
            it_at_break = (it as i32)
            break
        }
        x -= 1
    }
    assert(it_at_break == 3)
    assert(x == 7)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_condition_loop_continue():
    """Verifies `continue` advances `it` and proceeds to next iteration."""
    code = """
act main() -> i32 {
    mut x: i32 = 5
    mut evens_it_sum: i32 = 0
    loop x > 0 {
        x -= 1
        if (it as i32) % 2 != 0 {
            continue
        }
        evens_it_sum += (it as i32)
    }
    assert(evens_it_sum == 6)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_condition_loop_not_operator():
    """Verifies condition loop with logical negation `not done`."""
    code = """
act main() -> i32 {
    mut done: bool = false
    mut count: i32 = 0
    loop not done {
        count += 1
        if count == 4 {
            done = true
        }
    }
    assert(count == 4)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


# ==============================================================================
# 8. Side-Effect, Boundary, and Security Tests (Task 54.7 Verification)
# ==============================================================================

def test_count_loop_stateful_function_call():
    """Verifies that a stateful function call in the count is called exactly once and controls iteration count."""
    code = """
mut g_counter: i32 = 0

act calc_limit() -> i32 {
    g_counter += 10
    return g_counter
}

act main() -> i32 {
    mut iterations: i32 = 0
    loop calc_limit() {
        iterations += 1
    }
    assert(g_counter == 10)
    assert(iterations == 10)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_count_loop_function_returning_u64():
    """Verifies function returning u64 works as count expression."""
    code = """
act get_u64_count() -> u64 {
    return 4u64
}

act main() -> i32 {
    mut count: i32 = 0
    loop get_u64_count() {
        count += 1
    }
    assert(count == 4)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_count_loop_u64_above_int32_max_with_break():
    """Verifies that u64 count loop above INT32_MAX (e.g. 3000000000u64) uses uint64_t induction variable and terminates cleanly."""
    code = """
act main() -> i32 {
    let large_count: u64 = 3000000000u64
    mut iters: i32 = 0
    loop large_count {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_count_loop_u64_above_int32_max_emitted_c():
    """Verifies emitted C for u64 count loop above INT32_MAX uses uint64_t induction and count."""
    code = """
act main() {
    let large_count: u64 = 3000000000u64
    loop large_count { }
}
"""
    c_out = emit_c_velo_source(code)
    assert "for (uint64_t it = 0, __cnt = (large_count); it < __cnt; it++)" in c_out


def test_count_loop_nested_count_loops():
    """Verifies nested count loops execute expected product of iterations and shadow it properly."""
    code = """
act main() -> i32 {
    mut total: i32 = 0
    mut outer_it_sum: i32 = 0
    loop 3 {
        outer_it_sum += (it as i32)
        mut inner_it_sum: i32 = 0
        loop 4 {
            inner_it_sum += (it as i32)
            total += 1
        }
        assert(inner_it_sum == 6)
    }
    assert(outer_it_sum == 3)
    assert(total == 12)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_count_loop_deeply_nested():
    """Verifies 3-level nested count loops with different widths (u8, i16, u64)."""
    code = """
act main() -> i32 {
    mut count: i32 = 0
    loop 2u8 {
        loop 3i16 {
            loop 4u64 {
                count += 1
            }
        }
    }
    assert(count == 24)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_count_loop_break():
    """Verifies break terminates count loop early."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop 10 {
        if (it as i32) == 4 {
            break
        }
        iters += 1
    }
    assert(iters == 4)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_count_loop_continue():
    """Verifies continue skips remainder of loop body while properly incrementing it counter in count loops."""
    code = """
act main() -> i32 {
    mut evens_sum: i32 = 0
    loop 6 {
        if (it as i32) % 2 != 0 {
            continue
        }
        evens_sum += (it as i32)
    }
    assert(evens_sum == 6)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_count_loop_boundary_single_iteration():
    """Verifies count loop with count 1 runs exactly once."""
    code = """
act main() -> i32 {
    mut visited: i32 = 0
    loop 1 {
        visited += 1
        assert((it as i32) == 0)
    }
    assert(visited == 1)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_count_loop_variable_negative():
    """Verifies variable with negative integer terminates immediately (0 iterations)."""
    code = """
act main() -> i32 {
    let n: i32 = -10
    mut visited: i32 = 0
    loop n {
        visited += 1
    }
    assert(visited == 0)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_invalid_loop_address_of_pointer_rejected():
    """Security Invariant: `loop @x` must be rejected at compile-time."""
    code = """
act main() {
    let x: i32 = 10
    loop @x { }
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for pointer loop expression"
    assert "error" in res.stdout.lower() or "error" in res.stderr.lower()



