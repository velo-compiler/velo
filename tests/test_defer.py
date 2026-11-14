"""
tests/test_defer.py — Defer Lifecycle & Block Scoping Test Matrix (Phase 58)

Audit ID: AUDIT-2026-11-07
Severity: P0 — use-after-free, double-free, and memory leaks
Covers:
- Function body defers (normal exit and early return in LIFO order)
- Block-scoped defers in `if`, `else`, `on` (match), and nested blocks
- Loop iteration cleanup (per-iteration defers, `break`, `continue`)
- Unwinding on early exits (`return`, `fail`, `or return`)
- Security gates: exactly-once execution, `mem.heap_used()` returns to baseline, no double-free

Establishes the Red Baseline for Phase 58 (Task 58.1).
"""

import os
import subprocess
import tempfile
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = REPO_ROOT / "bin" / "velo.exe"


def get_build_env():
    """Returns an environment with ucrt64 GCC in PATH for compiling generated C."""
    env = dict(os.environ)
    ucrt_bin = r"C:\msys64\ucrt64\bin"
    if os.path.exists(ucrt_bin) and ucrt_bin not in env.get("PATH", ""):
        env["PATH"] = ucrt_bin + ";" + env.get("PATH", "")
    return env


def run_velo_source(source_code: str, timeout: float = 3.0) -> subprocess.CompletedProcess:
    """Compiles Velo source to an executable using bin/velo.exe build, then executes directly."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_path = Path(tmp_dir) / "test.vl"
        exe_path = Path(tmp_dir) / "test.exe"
        src_path.write_text(source_code, encoding="utf-8")

        build_res = subprocess.run(
            [str(VELO_EXE), "build", str(src_path), "-o", str(exe_path)],
            capture_output=True,
            text=True,
            env=get_build_env(),
            timeout=10.0,
        )
        if build_res.returncode != 0:
            return build_res

        run_res = subprocess.run(
            [str(exe_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return run_res


def test_defer_matrix_std_test_vl():
    """Runs the full standalone defer lifecycle matrix suite in std/tests/mem/defer_test.vl."""
    test_vl = REPO_ROOT / "std" / "tests" / "mem" / "defer_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_build_env(),
        timeout=15.0,
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.mem.defer all assertions succeeded" in res.stdout


def test_defer_function_scope_normal_exit():
    """Function-level defers must run in reverse declaration order (LIFO) on normal return."""
    src = """
use sys.io
use sys.mem

act helper(p_order: @i32) {
    p_order[0] = 0
    let p: @i32 = mem.heap_alloc(@i32, 4)
    defer mem.free(p)
    defer p_order[0] = p_order[0] * 10 + 1
    defer p_order[0] = p_order[0] * 10 + 2
}

act main() -> i32 {
    let base = mem.heap_used()
    mut order: i32 = 0
    helper(@order)
    let leaked: usize = mem.heap_used() - base
    io.println("order={order}")
    io.println("leaked={leaked}")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "order=21" in res.stdout
    assert "leaked=0" in res.stdout


def test_defer_function_scope_early_return():
    """Function-level defers must run in reverse declaration order (LIFO) on early return."""
    src = """
use sys.io
use sys.mem

act helper(p_order: @i32, trigger: bool) {
    p_order[0] = 0
    let p: @i32 = mem.heap_alloc(@i32, 4)
    defer mem.free(p)
    defer p_order[0] = p_order[0] * 10 + 1
    if trigger {
        defer p_order[0] = p_order[0] * 10 + 2
        return
    }
    defer p_order[0] = p_order[0] * 10 + 3
}

act main() -> i32 {
    let base = mem.heap_used()
    mut order: i32 = 0
    helper(@order, true)
    let leaked: usize = mem.heap_used() - base
    io.println("order={order}")
    io.println("leaked={leaked}")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "order=21" in res.stdout
    assert "leaked=0" in res.stdout


def test_defer_if_block_local_variable_scoping():
    """Defers declared inside an `if` block referencing block-local variables must compile and run at `}`."""
    src = """
use sys.io
use sys.mem

act main() -> i32 {
    let base = mem.heap_used()
    mut freed = false
    if true {
        let p: @i32 = mem.heap_alloc(@i32, 4)
        defer {
            mem.free(p)
        }
        p[0] = 42
    }
    // At this point, the if block has closed: p must be freed
    let after_if = mem.heap_used()
    let leaked: usize = after_if - base
    io.println("leaked={leaked}")
    return 0
}
"""
    # Note: Using individual single defer statement matching Velo syntax
    src_clean = """
use sys.io
use sys.mem

act main() -> i32 {
    let base = mem.heap_used()
    if true {
        let p: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p)
        p[0] = 42
    }
    let after_if = mem.heap_used()
    let leaked: usize = after_if - base
    io.println("leaked={leaked}")
    return 0
}
"""
    res = run_velo_source(src_clean)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "leaked=0" in res.stdout


def test_defer_if_executes_before_subsequent_statements():
    """Statements after an `if` block must see the `if` block's defers already executed."""
    src = """
use sys.io
use sys.mem

act main() -> i32 {
    mut step: i32 = 10
    if true {
        defer step += 5
    }
    // step must be 15 right here, not after main returns
    io.println("step_after_if={step}")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "step_after_if=15" in res.stdout


def test_defer_if_untaken_branch_never_runs():
    """A defer inside an untaken `if false` branch must never run."""
    src = """
use sys.io
use sys.mem

act main() -> i32 {
    mut ran: bool = false
    if false {
        defer ran = true
    }
    if ran {
        io.println("FAIL: untaken defer executed")
        return 1
    }
    io.println("PASS: untaken defer skipped")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "PASS: untaken defer skipped" in res.stdout


def test_defer_else_block_scoping():
    """Defers declared inside an `else` block must compile, access else-local variables, and run at `}`."""
    src = """
use sys.io
use sys.mem

act main() -> i32 {
    let base = mem.heap_used()
    mut order: i32 = 100
    if false {
        let p_bad: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p_bad)
        defer order += 999
    } else {
        let p: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p)
        defer order += 7
        p[0] = 77
    }
    io.println("order={order}")
    let leaked: usize = mem.heap_used() - base
    io.println("leaked={leaked}")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "order=107" in res.stdout
    assert "leaked=0" in res.stdout


def test_defer_match_on_arm_scoping():
    """Defers declared inside an `on` match arm must run at the closing `}` of that arm."""
    src = """
use sys.io
use sys.mem

act main() -> i32 {
    let base = mem.heap_used()
    mut order: i32 = 300
    let tag: i32 = 2
    on tag {
        1 => {
            let p1: @i32 = mem.heap_alloc(@i32, 4)
            defer mem.free(p1)
            defer order += 10
        }
        2 => {
            let p2: @i32 = mem.heap_alloc(@i32, 4)
            defer mem.free(p2)
            defer order += 20
        }
        _ => {
            order += 50
        }
    }
    io.println("order={order}")
    let leaked: usize = mem.heap_used() - base
    io.println("leaked={leaked}")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "order=320" in res.stdout
    assert "leaked=0" in res.stdout


def test_defer_loop_iteration_per_iteration_cleanup():
    """Defers in a loop body must execute at the end of each iteration without leaking memory."""
    src = """
use sys.io
use sys.mem

act main() -> i32 {
    let base = mem.heap_used()
    mut cleanups: i32 = 0
    loop 3 {
        let p: @i32 = mem.heap_alloc(@i32, 16)
        defer mem.free(p)
        defer cleanups += 1
        p[0] = 99
    }
    io.println("cleanups={cleanups}")
    let leaked: usize = mem.heap_used() - base
    io.println("leaked={leaked}")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "cleanups=3" in res.stdout
    assert "leaked=0" in res.stdout


def test_defer_loop_break_cleanup():
    """When `break` executes, the current iteration's defers must run once before breaking."""
    src = """
use sys.io
use sys.mem

act main() -> i32 {
    let base = mem.heap_used()
    mut cleanups: i32 = 0
    loop 5 {
        let p: @i32 = mem.heap_alloc(@i32, 8)
        defer mem.free(p)
        defer cleanups += 1
        if it == 2 {
            break
        }
    }
    io.println("cleanups={cleanups}")
    let leaked: usize = mem.heap_used() - base
    io.println("leaked={leaked}")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "cleanups=3" in res.stdout
    assert "leaked=0" in res.stdout


def test_defer_loop_continue_cleanup():
    """When `continue` executes, the current iteration's defers must run once before continuing."""
    src = """
use sys.io
use sys.mem

act main() -> i32 {
    let base = mem.heap_used()
    mut cleanups: i32 = 0
    loop 3 {
        let p: @i32 = mem.heap_alloc(@i32, 8)
        defer mem.free(p)
        defer cleanups += 1
        if it == 1 {
            continue
        }
    }
    io.println("cleanups={cleanups}")
    let leaked: usize = mem.heap_used() - base
    io.println("leaked={leaked}")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "cleanups=3" in res.stdout
    assert "leaked=0" in res.stdout


def test_defer_nested_blocks_scoping():
    """Nested blocks must unwind their defers at their respective block endings."""
    src = """
use sys.io
use sys.mem

act main() -> i32 {
    let base = mem.heap_used()
    mut order: i32 = 0
    if true {
        let p1: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p1)
        defer order = order * 10 + 1
        if true {
            let p2: @i32 = mem.heap_alloc(@i32, 4)
            defer mem.free(p2)
            defer order = order * 10 + 2
        }
        // At this point, inner block closed: order must be 2
        io.println("inner_order={order}")
    }
    // At this point, outer block closed: order must be 21
    io.println("outer_order={order}")
    let leaked: usize = mem.heap_used() - base
    io.println("leaked={leaked}")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "inner_order=2" in res.stdout
    assert "outer_order=21" in res.stdout
    assert "leaked=0" in res.stdout


def test_defer_early_return_unwinds_only_active_blocks():
    """Early return from a nested block must unwind active blocks in LIFO order and skip unreached defers."""
    src = """
use sys.io
use sys.mem

act helper(p_order: @i32) -> i32 {
    let p_fn: @i32 = mem.heap_alloc(@i32, 4)
    defer mem.free(p_fn)
    defer p_order[0] = p_order[0] * 10 + 1
    if true {
        let p_if: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p_if)
        defer p_order[0] = p_order[0] * 10 + 2
        loop 3 {
            let p_lp: @i32 = mem.heap_alloc(@i32, 4)
            defer mem.free(p_lp)
            defer p_order[0] = p_order[0] * 10 + 3
            if it == 0 {
                return 42
            }
        }
        defer p_order[0] = p_order[0] * 10 + 8
    }
    defer p_order[0] = p_order[0] * 10 + 9
    return 0
}

act main() -> i32 {
    let base = mem.heap_used()
    mut order: i32 = 0
    let ret = helper(@order)
    io.println("ret={ret}")
    io.println("order={order}")
    let leaked: usize = mem.heap_used() - base
    io.println("leaked={leaked}")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "ret=42" in res.stdout
    assert "order=321" in res.stdout
    assert "leaked=0" in res.stdout


def test_defer_fail_outcome_unwinding():
    """Algebraic outcome `fail` must unwind active blocks in LIFO order before returning."""
    src = """
use sys.io
use sys.mem

act helper(p_order: @i32) -> i32 or string {
    let p_fn: @i32 = mem.heap_alloc(@i32, 4)
    defer mem.free(p_fn)
    defer p_order[0] = p_order[0] * 10 + 1
    if true {
        let p_if: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p_if)
        defer p_order[0] = p_order[0] * 10 + 2
        fail "failed!"
        defer p_order[0] = p_order[0] * 10 + 8
    }
    return 100
}

act main() -> i32 {
    let base = mem.heap_used()
    mut order: i32 = 0
    let res = helper(@order)
    if res.ok {
        io.println("FAIL: expected error")
        return 1
    }
    io.println("err={res.as.err}")
    io.println("order={order}")
    let leaked: usize = mem.heap_used() - base
    io.println("leaked={leaked}")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "err=failed!" in res.stdout
    assert "order=21" in res.stdout
    assert "leaked=0" in res.stdout


def test_defer_or_return_unwinding():
    """An `or return` failure inside a nested block must unwind active blocks in LIFO order."""
    src = """
use sys.io
use sys.mem

act fail_call() -> i32 or string {
    fail "callee failed"
}

act helper(p_order: @i32) -> i32 or string {
    let p_fn: @i32 = mem.heap_alloc(@i32, 4)
    defer mem.free(p_fn)
    defer p_order[0] = p_order[0] * 10 + 1
    if true {
        let p_if: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p_if)
        defer p_order[0] = p_order[0] * 10 + 2
        let val: i32 = fail_call() or return
        defer p_order[0] = p_order[0] * 10 + 8
    }
    return 0
}

act main() -> i32 {
    let base = mem.heap_used()
    mut order: i32 = 0
    let res = helper(@order)
    if res.ok {
        io.println("FAIL: expected error")
        return 1
    }
    io.println("err={res.as.err}")
    io.println("order={order}")
    let leaked: usize = mem.heap_used() - base
    io.println("leaked={leaked}")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "err=callee failed" in res.stdout
    assert "order=21" in res.stdout
    assert "leaked=0" in res.stdout


def test_defer_security_gate_heap_zero_and_no_double_free():
    """Security gate: assert exactly-once execution, mem.heap_used() == 0, and no double-free across complex flow."""
    src = """
use sys.io
use sys.mem

act test_lifecycle() -> bool {
    let base = mem.heap_used()
    mut exec_count: i32 = 0

    // 1. Loop with break and continue
    loop 4 {
        let p_loop: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p_loop)
        defer exec_count += 1
        if it == 0 {
            continue
        }
        if it == 2 {
            break
        }
    }
    // it=0 ran & continued (+1), it=1 ran (+1), it=2 ran & broke (+1) => 3
    if exec_count != 3 {
        io.println("FAIL: loop exec_count mismatch: {exec_count}")
        return false
    }
    if mem.heap_used() != base {
        io.println("FAIL: loop leaked memory")
        return false
    }

    // 2. If block
    if true {
        let p_if: @i32 = mem.heap_alloc(@i32, 8)
        defer mem.free(p_if)
        defer exec_count += 10
    }
    if exec_count != 13 {
        io.println("FAIL: if exec_count mismatch: {exec_count}")
        return false
    }
    if mem.heap_used() != base {
        io.println("FAIL: if leaked memory")
        return false
    }

    return true
}

act main() -> i32 {
    let base = mem.heap_used()
    if not test_lifecycle() {
        return 1
    }
    if mem.heap_used() != base {
        io.println("FAIL: leaked memory at end of test")
        return 1
    }
    io.println("PASS: security gate zero leaks and no double free")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "PASS: security gate zero leaks and no double free" in res.stdout
