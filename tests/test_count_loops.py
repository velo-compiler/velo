"""Phase 54: loop <count> vs <condition> classification test matrix (red baseline).

Audit ID: AUDIT-2026-11-03
Tests count loops across integer widths, expressions, zero/negative counts,
side effects, boolean condition loops, and compile-time rejection of invalid types.
"""

import os
import subprocess
import tempfile
import pytest

COMPILER = "bin/velo.exe"


def get_env():
    env = dict(os.environ)
    env["PATH"] = r"C:\msys64\ucrt64\bin;" + env.get("PATH", "")
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
            text=True,
            timeout=10.0,
        )
        if build_res.returncode != 0:
            return build_res
        try:
            return subprocess.run(
                [exe],
                capture_output=True,
                text=True,
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
            text=True,
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
            text=True,
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

