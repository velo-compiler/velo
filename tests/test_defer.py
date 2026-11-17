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
from conftest import cc_dir, cc_path, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()
if not VELO_EXE.exists() and (velo_exe()).exists():
    VELO_EXE = velo_exe()


def get_build_env():
    """Returns an environment with ucrt64 GCC in PATH for compiling generated C."""
    env = dict(os.environ)
    ucrt_bin = cc_dir()
    if os.path.exists(ucrt_bin):
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
    io.println("err={res.err}")
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
    io.println("err={res.err}")
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


def test_block_scope_marker_primitives_in_emitted_compiler_c():
    """Verify that the compiler C output defines block marker primitives in DeferNode."""
    bootstrap_c = (REPO_ROOT / "bootstrap.c").read_text(encoding="utf-8")
    assert "bool is_block;" in bootstrap_c
    assert "push_block_scope" in bootstrap_c
    assert "pop_block_scope" in bootstrap_c
    assert "block_scope_depth" in bootstrap_c
    assert "count_block_defers" in bootstrap_c
    assert "cur_d->is_block" in bootstrap_c


def test_block_scope_stack_balance_and_isolation_probe():
    """Internal probe: verify that block markers isolate nested scopes and push/pop is strictly balanced."""
    src = """
use sys.io
use sys.mem

data ProbeNode {
    is_block: bool
    is_loop: bool
    val: i32
    next: @ProbeNode
}

act push_block(stack: @@ProbeNode) -> @ProbeNode {
    let prev = stack.@
    mut bd: @ProbeNode = mem.heap_alloc(@ProbeNode, 1)
    bd.is_block = true
    bd.is_loop = false
    bd.val = 0
    bd.next = stack.@
    stack.@ = bd
    return prev
}

act pop_block(stack: @@ProbeNode, prev: @ProbeNode) {
    stack.@ = prev
}

act push_defer(stack: @@ProbeNode, val: i32) {
    mut d: @ProbeNode = mem.heap_alloc(@ProbeNode, 1)
    d.is_block = false
    d.is_loop = false
    d.val = val
    d.next = stack.@
    stack.@ = d
}

act probe_depth(stack: @@ProbeNode) -> i32 {
    if stack == null { return 0 }
    mut cur = stack.@
    mut cnt: i32 = 0
    loop cur != null {
        if cur.is_block or cur.is_loop { cnt += 1 }
        cur = cur.next
    }
    return cnt
}

act probe_count_innermost(stack: @@ProbeNode) -> i32 {
    if stack == null { return 0 }
    mut cur = stack.@
    mut cnt: i32 = 0
    loop cur != null and not cur.is_block and not cur.is_loop {
        cnt += 1
        cur = cur.next
    }
    return cnt
}

act main() -> i32 {
    mut stack: @ProbeNode = null

    // 0. Base: depth = 0, count = 0
    if probe_depth(@stack) != 0 or probe_count_innermost(@stack) != 0 {
        io.println("FAIL: initial state")
        return 1
    }

    // 1. Enter Outer Scope (Block 1)
    let p1 = push_block(@stack)
    if probe_depth(@stack) != 1 or probe_count_innermost(@stack) != 0 {
        io.println("FAIL: block 1 entered")
        return 1
    }
    push_defer(@stack, 10)
    push_defer(@stack, 11)
    if probe_depth(@stack) != 1 or probe_count_innermost(@stack) != 2 {
        io.println("FAIL: block 1 defers count")
        return 1
    }

    // 2. Enter Inner Scope (Block 2)
    let p2 = push_block(@stack)
    if probe_depth(@stack) != 2 or probe_count_innermost(@stack) != 0 {
        io.println("FAIL: block 2 isolation (must be 0)")
        return 1
    }
    push_defer(@stack, 20)
    if probe_depth(@stack) != 2 or probe_count_innermost(@stack) != 1 {
        io.println("FAIL: block 2 defers count")
        return 1
    }

    // 3. Enter Deep Scope (Block 3)
    let p3 = push_block(@stack)
    if probe_depth(@stack) != 3 or probe_count_innermost(@stack) != 0 {
        io.println("FAIL: block 3 isolation")
        return 1
    }

    // 4. Pop Deep Scope (Block 3)
    pop_block(@stack, p3)
    if probe_depth(@stack) != 2 or probe_count_innermost(@stack) != 1 {
        io.println("FAIL: restored block 2")
        return 1
    }

    // 5. Pop Inner Scope (Block 2)
    pop_block(@stack, p2)
    if probe_depth(@stack) != 1 or probe_count_innermost(@stack) != 2 {
        io.println("FAIL: restored block 1")
        return 1
    }

    // 6. Pop Outer Scope (Block 1)
    pop_block(@stack, p1)
    if probe_depth(@stack) != 0 or probe_count_innermost(@stack) != 0 {
        io.println("FAIL: restored initial")
        return 1
    }

    io.println("PASS: block markers balanced and scopes isolated")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "PASS: block markers balanced and scopes isolated" in res.stdout


def test_defer_plain_block_local_pointer_and_werror():
    """Security gate: emit cleanups before closing '}', compile emitted C with -Werror to ensure no out-of-scope references."""
    src = """
use sys.io
use sys.mem

act main() -> i32 {
    let base = mem.heap_used()
    mut order: i32 = 0

    // 1. Plain block scope
    {
        let p_plain: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p_plain)
        defer order += 10
        p_plain[0] = 42
    }
    // Plain block closed: p_plain must be freed and order incremented
    if order != 10 {
        io.println("FAIL: plain block defer did not run at '}'")
        return 1
    }
    let after_plain = mem.heap_used()
    if after_plain != base {
        io.println("FAIL: plain block leaked memory")
        return 1
    }

    // 2. If block scope
    if true {
        let p_if: @i32 = mem.heap_alloc(@i32, 8)
        defer mem.free(p_if)
        defer order += 5
        p_if[0] = 84
    }
    if order != 15 {
        io.println("FAIL: if block defer did not run at '}'")
        return 1
    }
    let after_if = mem.heap_used()
    if after_if != base {
        io.println("FAIL: if block leaked memory")
        return 1
    }

    io.println("PASS: plain and if block local pointers freed cleanly")
    return 0
}
"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_path = Path(tmp_dir) / "test_werror.vl"
        c_path = Path(tmp_dir) / "test_werror.c"
        exe_path = Path(tmp_dir) / "test_werror.exe"
        src_path.write_text(src, encoding="utf-8")

        # Emit C
        emit_res = subprocess.run(
            [str(VELO_EXE), "emit-c", str(src_path), "-o", str(c_path)],
            capture_output=True,
            text=True,
            env=get_build_env(),
            timeout=10.0,
        )
        assert emit_res.returncode == 0, f"emit-c failed: {emit_res.stderr}\n{emit_res.stdout}"

        # Compile with -Werror
        gcc_bin = cc_path() if os.path.exists(cc_path()) else "gcc"
        gcc_cmd = [
            gcc_bin,
            "-std=c99",
            "-Werror",
            "-Wno-unknown-pragmas",
            "-I", str(REPO_ROOT / "runtime"),
            "-I", str(REPO_ROOT / "velo" / "runtime"),
            str(c_path),
            "-lws2_32",
            "-ladvapi32",
            "-o", str(exe_path),
        ]
        gcc_res = subprocess.run(
            gcc_cmd,
            capture_output=True,
            text=True,
            env=get_build_env(),
            cwd=str(REPO_ROOT),
            timeout=10.0,
        )
        assert gcc_res.returncode == 0, f"gcc -Werror failed: {gcc_res.stderr}\n{gcc_res.stdout}"

        # Run executable
        run_res = subprocess.run([str(exe_path)], capture_output=True, text=True, timeout=5.0)
        assert run_res.returncode == 0, f"run failed: {run_res.stderr}\n{run_res.stdout}"
        assert "PASS: plain and if block local pointers freed cleanly" in run_res.stdout


def test_defer_nested_plain_and_if_blocks_with_local_pointers():
    """Verify arbitrary nested combinations of plain blocks and if blocks with block-local pointers."""
    src = """
use sys.io
use sys.mem

act main() -> i32 {
    let base = mem.heap_used()
    mut trace: i32 = 0

    {
        let p1: @i32 = mem.heap_alloc(@i32, 2)
        defer mem.free(p1)
        defer trace = trace * 10 + 1
        if true {
            let p2: @i32 = mem.heap_alloc(@i32, 2)
            defer mem.free(p2)
            defer trace = trace * 10 + 2
            {
                let p3: @i32 = mem.heap_alloc(@i32, 2)
                defer mem.free(p3)
                defer trace = trace * 10 + 3
            }
            if trace != 3 {
                io.println("FAIL: innermost plain block")
                return 1
            }
        }
        if trace != 32 {
            io.println("FAIL: inner if block")
            return 1
        }
    }
    if trace != 321 {
        io.println("FAIL: outer plain block")
        return 1
    }

    let leaked: usize = mem.heap_used() - base
    if leaked != 0 {
        io.println("FAIL: leaked memory")
        return 1
    }
    io.println("PASS: nested plain and if block defers LIFO verified")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "PASS: nested plain and if block defers LIFO verified" in res.stdout


def test_defer_loop_leak_repro_audit_baseline():
    """Exact audit repro AUDIT-2026-11-07: loop 10 with defer mem.free(p) must maintain zero heap growth."""
    src = """
use sys.io
use sys.mem

act main() -> i32 {
    let base = mem.heap_used()
    loop 10 {
        let p: @i32 = mem.heap_alloc(@i32, 1)
        defer mem.free(p)
        p[0] = 7
    }
    let after_loop = mem.heap_used()
    let leaked: usize = after_loop - base
    if leaked != 0 {
        io.println("FAIL: loop leaked memory: {leaked}")
        return 1
    }
    io.println("PASS: loop leak repro zero heap growth")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "PASS: loop leak repro zero heap growth" in res.stdout


def test_defer_loop_nested_loops_with_breaks_and_continues():
    """Nested loops with defers, inner break and outer continue, ensuring accurate cleanup and zero leaks."""
    src = """
use sys.io
use sys.mem

act main() -> i32 {
    let base = mem.heap_used()
    mut outer_count: i32 = 0
    mut inner_count: i32 = 0

    loop 4 {
        let p_out: @i32 = mem.heap_alloc(@i32, 2)
        defer mem.free(p_out)
        defer outer_count += 1

        if it == 0 {
            continue
        }

        loop 3 {
            let p_in: @i32 = mem.heap_alloc(@i32, 2)
            defer mem.free(p_in)
            defer inner_count += 1
            if it == 1 {
                break
            }
        }
    }

    // Outer loop ran 4 times (all 4 iterations cleaned up): outer_count == 4
    // Iter 0: continued before inner loop (0 inner)
    // Iter 1: inner ran it=0 (+1), it=1 broke (+1) => 2
    // Iter 2: inner ran it=0 (+1), it=1 broke (+1) => 2
    // Iter 3: inner ran it=0 (+1), it=1 broke (+1) => 2
    // Total inner: 6
    if outer_count != 4 {
        io.println("FAIL: outer_count mismatch: {outer_count}")
        return 1
    }
    if inner_count != 6 {
        io.println("FAIL: inner_count mismatch: {inner_count}")
        return 1
    }

    let leaked: usize = mem.heap_used() - base
    if leaked != 0 {
        io.println("FAIL: nested loops leaked memory: {leaked}")
        return 1
    }
    io.println("PASS: nested loops with break and continue cleaned up cleanly")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "PASS: nested loops with break and continue cleaned up cleanly" in res.stdout


def test_defer_loop_infinite_with_conditional_break():
    """Infinite loop 'loop' with conditional break must unwind the breaking iteration and leave zero leaks."""
    src = """
use sys.io
use sys.mem

act main() -> i32 {
    let base = mem.heap_used()
    mut iterations: i32 = 0

    loop {
        let p: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p)
        defer iterations += 1
        p[0] = it

        if it == 5 {
            break
        }
    }

    // it ran for 0, 1, 2, 3, 4, 5 (6 iterations)
    if iterations != 6 {
        io.println("FAIL: iterations mismatch: {iterations}")
        return 1
    }

    let leaked: usize = mem.heap_used() - base
    if leaked != 0 {
        io.println("FAIL: infinite loop break leaked: {leaked}")
        return 1
    }
    io.println("PASS: infinite loop break cleaned up cleanly")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "PASS: infinite loop break cleaned up cleanly" in res.stdout


def test_defer_loop_shelf_iteration_cleanup():
    """Shelf collection iteration loop with per-iteration defers must clean up every iteration."""
    src = """
use sys.io
use sys.mem

act main() -> i32 {
    mut xs: shelf[i32] = shelf[10, 20, 30]
    let base = mem.heap_used()
    mut cleanups: i32 = 0

    loop x of xs {
        let p: @i32 = mem.heap_alloc(@i32, 2)
        defer mem.free(p)
        defer cleanups += 1
        p[0] = x
    }

    if cleanups != 3 {
        io.println("FAIL: shelf cleanups mismatch")
        return 1
    }

    let leaked: usize = mem.heap_used() - base
    if leaked != 0 {
        io.println("FAIL: shelf loop leaked: {leaked}")
        return 1
    }
    io.println("PASS: shelf loop per-iteration cleanups verified")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "PASS: shelf loop per-iteration cleanups verified" in res.stdout


def test_defer_early_exit_multi_level_return():
    """Verify return from 4-level nested blocks unwinds in exact LIFO order and frees all allocations."""
    src = """
use sys.io
use sys.mem

act helper(p_order: @i32) -> i32 {
    let p0: @i32 = mem.heap_alloc(@i32, 4)
    defer mem.free(p0)
    defer p_order[0] = p_order[0] * 10 + 1

    if true {
        let p1: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p1)
        defer p_order[0] = p_order[0] * 10 + 2

        {
            let p2: @i32 = mem.heap_alloc(@i32, 4)
            defer mem.free(p2)
            defer p_order[0] = p_order[0] * 10 + 3

            if true {
                let p3: @i32 = mem.heap_alloc(@i32, 4)
                defer mem.free(p3)
                defer p_order[0] = p_order[0] * 10 + 4

                return 42

                defer p_order[0] = p_order[0] * 10 + 9
            }
            defer p_order[0] = p_order[0] * 10 + 8
        }
        defer p_order[0] = p_order[0] * 10 + 7
    }
    defer p_order[0] = p_order[0] * 10 + 6
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
    assert "order=4321" in res.stdout
    assert "leaked=0" in res.stdout


def test_defer_early_exit_multi_level_fail():
    """Verify fail from 4-level nested blocks unwinds in exact LIFO order and delivers error string."""
    src = """
use sys.io
use sys.mem

act helper(p_order: @i32) -> i32 or string {
    let p0: @i32 = mem.heap_alloc(@i32, 4)
    defer mem.free(p0)
    defer p_order[0] = p_order[0] * 10 + 1

    if true {
        let p1: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p1)
        defer p_order[0] = p_order[0] * 10 + 2

        {
            let p2: @i32 = mem.heap_alloc(@i32, 4)
            defer mem.free(p2)
            defer p_order[0] = p_order[0] * 10 + 3

            if true {
                let p3: @i32 = mem.heap_alloc(@i32, 4)
                defer mem.free(p3)
                defer p_order[0] = p_order[0] * 10 + 4

                fail "deep failure"

                defer p_order[0] = p_order[0] * 10 + 9
            }
            defer p_order[0] = p_order[0] * 10 + 8
        }
        defer p_order[0] = p_order[0] * 10 + 7
    }
    defer p_order[0] = p_order[0] * 10 + 6
    return 0
}

act main() -> i32 {
    let base = mem.heap_used()
    mut order: i32 = 0
    let res = helper(@order)
    if res.ok {
        io.println("FAIL: expected error outcome")
        return 1
    }
    io.println("err={res.err}")
    io.println("order={order}")
    let leaked: usize = mem.heap_used() - base
    io.println("leaked={leaked}")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "err=deep failure" in res.stdout
    assert "order=4321" in res.stdout
    assert "leaked=0" in res.stdout


def test_defer_early_exit_multi_level_or_return():
    """Verify `or return` from 4-level nested blocks unwinds in exact LIFO order and delivers error string."""
    src = """
use sys.io
use sys.mem

act callee() -> i32 or string {
    fail "nested callee failure"
}

act helper(p_order: @i32) -> i32 or string {
    let p0: @i32 = mem.heap_alloc(@i32, 4)
    defer mem.free(p0)
    defer p_order[0] = p_order[0] * 10 + 1

    if true {
        let p1: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p1)
        defer p_order[0] = p_order[0] * 10 + 2

        {
            let p2: @i32 = mem.heap_alloc(@i32, 4)
            defer mem.free(p2)
            defer p_order[0] = p_order[0] * 10 + 3

            if true {
                let p3: @i32 = mem.heap_alloc(@i32, 4)
                defer mem.free(p3)
                defer p_order[0] = p_order[0] * 10 + 4

                let v: i32 = callee() or return

                defer p_order[0] = p_order[0] * 10 + 9
            }
            defer p_order[0] = p_order[0] * 10 + 8
        }
        defer p_order[0] = p_order[0] * 10 + 7
    }
    defer p_order[0] = p_order[0] * 10 + 6
    return 0
}

act main() -> i32 {
    let base = mem.heap_used()
    mut order: i32 = 0
    let res = helper(@order)
    if res.ok {
        io.println("FAIL: expected error outcome")
        return 1
    }
    io.println("err={res.err}")
    io.println("order={order}")
    let leaked: usize = mem.heap_used() - base
    io.println("leaked={leaked}")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "err=nested callee failure" in res.stdout
    assert "order=4321" in res.stdout
    assert "leaked=0" in res.stdout


def test_defer_early_exit_nested_blocks_inside_loop_break_and_continue():
    """Verify break/continue inside nested blocks within a loop unwind inner blocks up to loop boundary only."""
    src = """
use sys.io
use sys.mem

act main() -> i32 {
    let base = mem.heap_used()
    mut outer_defer_ran: bool = false
    mut unwind_order: i32 = 0

    // Outer block defer
    defer outer_defer_ran = true

    loop 3 {
        let p_lp: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p_lp)
        defer unwind_order = unwind_order * 10 + 1

        if it == 0 {
            // Nested block 1
            {
                let p_bk: @i32 = mem.heap_alloc(@i32, 4)
                defer mem.free(p_bk)
                defer unwind_order = unwind_order * 10 + 2

                if true {
                    let p_deep: @i32 = mem.heap_alloc(@i32, 4)
                    defer mem.free(p_deep)
                    defer unwind_order = unwind_order * 10 + 3

                    // continue from 3 levels deep: must unwind 3 -> 2 -> 1, but NOT outer_defer!
                    continue
                }
            }
        }

        if it == 1 {
            // Nested block 1
            {
                let p_bk2: @i32 = mem.heap_alloc(@i32, 4)
                defer mem.free(p_bk2)
                defer unwind_order = unwind_order * 10 + 4

                if true {
                    let p_deep2: @i32 = mem.heap_alloc(@i32, 4)
                    defer mem.free(p_deep2)
                    defer unwind_order = unwind_order * 10 + 5

                    // break from 3 levels deep: must unwind 5 -> 4 -> 1, but NOT outer_defer!
                    break
                }
            }
        }
    }

    // Outer defer must NOT have run yet!
    if outer_defer_ran {
        io.println("FAIL: outer defer ran prematurely during break/continue")
        return 1
    }

    // Iteration 0 (continue): 3, then 2, then 1 => 321
    // Iteration 1 (break): 5, then 4, then 1 => 321541
    io.println("order={unwind_order}")

    let leaked: usize = mem.heap_used() - base
    io.println("leaked={leaked}")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "order=321541" in res.stdout
    assert "leaked=0" in res.stdout


def test_defer_if_else_chain_branch_isolation():
    """Defers in if/else if/else must only execute for the taken branch, with zero sibling leakage."""
    src = """
use sys.io
use sys.mem

act run_branch(branch: i32, p_order: @i32) {
    if branch == 1 {
        let p1: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p1)
        defer p_order[0] = p_order[0] * 10 + 1
        p_order[0] = p_order[0] * 10 + 4
    } else if branch == 2 {
        let p2: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p2)
        defer p_order[0] = p_order[0] * 10 + 2
        p_order[0] = p_order[0] * 10 + 5
    } else {
        let p3: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p3)
        defer p_order[0] = p_order[0] * 10 + 3
        p_order[0] = p_order[0] * 10 + 6
    }
}

act main() -> i32 {
    let base = mem.heap_used()

    // Test branch 1
    mut order1: i32 = 0
    run_branch(1, @order1)
    // body wrote 4, then defer wrote 1 => 41
    if order1 != 41 {
        io.println("FAIL: branch 1 mismatch: {order1}")
        return 1
    }

    // Test branch 2
    mut order2: i32 = 0
    run_branch(2, @order2)
    // body wrote 5, then defer wrote 2 => 52
    if order2 != 52 {
        io.println("FAIL: branch 2 mismatch: {order2}")
        return 1
    }

    // Test branch 3 (else)
    mut order3: i32 = 0
    run_branch(3, @order3)
    // body wrote 6, then defer wrote 3 => 63
    if order3 != 63 {
        io.println("FAIL: branch 3 mismatch: {order3}")
        return 1
    }

    let leaked: usize = mem.heap_used() - base
    if leaked != 0 {
        io.println("FAIL: leaked: {leaked}")
        return 1
    }

    io.println("PASS: if/else branch isolation verified")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "PASS: if/else branch isolation verified" in res.stdout


def test_defer_match_tagged_union_variant_arms_scoping():
    """Defers inside tagged union pattern arms must execute at arm closing '}' before break."""
    src = """
use sys.io
use sys.mem

kind Action {
    Stop
    Walk(steps: i32)
    Teleport(x: i32, y: i32)
}

act run_action(act_val: Action, p_order: @i32) {
    on act_val {
        .Stop => {
            let p0: @i32 = mem.heap_alloc(@i32, 4)
            defer mem.free(p0)
            defer p_order[0] = p_order[0] * 10 + 1
            p_order[0] = p_order[0] * 10 + 9
        }
        .Walk(steps) => {
            let p1: @i32 = mem.heap_alloc(@i32, 4)
            defer mem.free(p1)
            defer p_order[0] = p_order[0] * 10 + 2
            p_order[0] = p_order[0] * 10 + steps
        }
        .Teleport(x, y) => {
            let p2: @i32 = mem.heap_alloc(@i32, 4)
            defer mem.free(p2)
            defer p_order[0] = p_order[0] * 10 + 3
            p_order[0] = p_order[0] * 10 + (x + y)
        }
    }
}

act main() -> i32 {
    let base = mem.heap_used()

    // 1. Stop variant
    mut order0: i32 = 0
    run_action(Action.Stop, @order0)
    // body wrote 9, defer wrote 1 => 91
    if order0 != 91 {
        io.println("FAIL: stop variant order mismatch: {order0}")
        return 1
    }

    // 2. Walk variant
    mut order1: i32 = 0
    run_action(Action.Walk(5), @order1)
    // body wrote 5, defer wrote 2 => 52
    if order1 != 52 {
        io.println("FAIL: walk variant order mismatch: {order1}")
        return 1
    }

    // 3. Teleport variant
    mut order2: i32 = 0
    run_action(Action.Teleport(3, 4), @order2)
    // body wrote 7, defer wrote 3 => 73
    if order2 != 73 {
        io.println("FAIL: teleport variant order mismatch: {order2}")
        return 1
    }

    let leaked: usize = mem.heap_used() - base
    if leaked != 0 {
        io.println("FAIL: leaked: {leaked}")
        return 1
    }

    io.println("PASS: tagged union variant arms scoping verified")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "PASS: tagged union variant arms scoping verified" in res.stdout


def test_defer_match_string_pattern_arms_scoping():
    """Defers inside string match arms must execute at arm closing '}' without leaking."""
    src = """
use sys.io
use sys.mem

act match_command(cmd: string, p_order: @i32) {
    on cmd {
        "start" => {
            let p: @i32 = mem.heap_alloc(@i32, 4)
            defer mem.free(p)
            defer p_order[0] = p_order[0] * 10 + 1
            p_order[0] = p_order[0] * 10 + 4
        }
        "pause", "stop" => {
            let p: @i32 = mem.heap_alloc(@i32, 4)
            defer mem.free(p)
            defer p_order[0] = p_order[0] * 10 + 2
            p_order[0] = p_order[0] * 10 + 5
        }
        else => {
            let p: @i32 = mem.heap_alloc(@i32, 4)
            defer mem.free(p)
            defer p_order[0] = p_order[0] * 10 + 3
            p_order[0] = p_order[0] * 10 + 6
        }
    }
}

act main() -> i32 {
    let base = mem.heap_used()

    mut order1: i32 = 0
    match_command("start", @order1)
    if order1 != 41 {
        io.println("FAIL: start mismatch: {order1}")
        return 1
    }

    mut order2: i32 = 0
    match_command("stop", @order2)
    if order2 != 52 {
        io.println("FAIL: stop mismatch: {order2}")
        return 1
    }

    mut order3: i32 = 0
    match_command("unknown", @order3)
    if order3 != 63 {
        io.println("FAIL: default mismatch: {order3}")
        return 1
    }

    let leaked: usize = mem.heap_used() - base
    if leaked != 0 {
        io.println("FAIL: string match leaked: {leaked}")
        return 1
    }

    io.println("PASS: string match arms scoping verified")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "PASS: string match arms scoping verified" in res.stdout


def test_defer_branch_early_exit_no_double_emission_and_sibling_safety():
    """Branch with early return runs its defers once, without executing sibling branch defers."""
    src = """
use sys.io
use sys.mem

act helper(take_early: bool, p_order: @i32) -> i32 {
    let p_fn: @i32 = mem.heap_alloc(@i32, 4)
    defer mem.free(p_fn)
    defer p_order[0] = p_order[0] * 10 + 1

    if take_early {
        let p_if: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p_if)
        defer p_order[0] = p_order[0] * 10 + 2
        return 100
        defer p_order[0] = p_order[0] * 10 + 9
    } else {
        let p_else: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p_else)
        defer p_order[0] = p_order[0] * 10 + 3
    }

    defer p_order[0] = p_order[0] * 10 + 8
    return 200
}

act main() -> i32 {
    let base = mem.heap_used()

    // Pass 1: early exit taken in 'if'
    mut order1: i32 = 0
    let ret1 = helper(true, @order1)
    if ret1 != 100 {
        io.println("FAIL: ret1 mismatch")
        return 1
    }
    // 'if' defer (2) then fn defer (1) => 21; else defer (3) must NOT have run!
    if order1 != 21 {
        io.println("FAIL: order1 mismatch: {order1}")
        return 1
    }

    // Pass 2: normal exit through 'else'
    mut order2: i32 = 0
    let ret2 = helper(false, @order2)
    if ret2 != 200 {
        io.println("FAIL: ret2 mismatch")
        return 1
    }
    // 'else' defer (3), then post-if defer (8), then fn defer (1) => 381
    if order2 != 381 {
        io.println("FAIL: order2 mismatch: {order2}")
        return 1
    }

    let leaked: usize = mem.heap_used() - base
    if leaked != 0 {
        io.println("FAIL: leaked: {leaked}")
        return 1
    }

    io.println("PASS: branch early exit no double emission and sibling safe")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "PASS: branch early exit no double emission and sibling safe" in res.stdout


def test_defer_allocation_free_balance_probe():
    """Stress test allocation and free balance across loops, breaks, continues, and branching.
    Verifies that mem.heap_used() - base == 0 and exactly balanced allocations/frees.
    """
    src = """
use sys.io
use sys.mem

data Tracker {
    alloc_count: i32
    free_count: i32
}

act do_work(t: @Tracker, iter: i32) {
    let p1: @i32 = mem.heap_alloc(@i32, 4)
    t.alloc_count += 1
    defer mem.free(p1)
    defer t.free_count += 1

    if iter % 2 == 0 {
        let p_even: @i32 = mem.heap_alloc(@i32, 4)
        t.alloc_count += 1
        defer mem.free(p_even)
        defer t.free_count += 1
        p_even[0] = iter
    } else {
        let p_odd: @i32 = mem.heap_alloc(@i32, 4)
        t.alloc_count += 1
        defer mem.free(p_odd)
        defer t.free_count += 1
        p_odd[0] = iter * 2
    }

    mut inner_k: i32 = 0
    loop inner_k < 3 {
        let p_loop: @i32 = mem.heap_alloc(@i32, 4)
        t.alloc_count += 1
        defer mem.free(p_loop)
        defer t.free_count += 1
        if inner_k == 1 and iter % 3 == 0 {
            inner_k += 1
            continue
        }
        if inner_k == 2 and iter % 5 == 0 {
            break
        }
        inner_k += 1
    }
}

act main() -> i32 {
    let base = mem.heap_used()
    mut t: Tracker
    t.alloc_count = 0
    t.free_count = 0

    mut i: i32 = 0
    loop i < 50 {
        do_work(@t, i)
        i += 1
    }

    let leaked: usize = mem.heap_used() - base
    if leaked != 0 {
        io.println("FAIL: leaked: {leaked}")
        return 1
    }
    if t.alloc_count != t.free_count {
        io.println("FAIL: alloc/free count mismatch: alloc={t.alloc_count}, free={t.free_count}")
        return 1
    }
    if t.alloc_count == 0 {
        io.println("FAIL: no allocations performed")
        return 1
    }

    io.println("PASS: allocation free balance probe succeeded count={t.alloc_count}")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "PASS: allocation free balance probe succeeded" in res.stdout


def test_defer_uaf_prevention_parent_child_lifo():
    """Use-after-free probe: Parent owns pointer to Child.
    LIFO defer execution guarantees Child is freed before Parent.
    If execution order were inverted (FIFO), freeing Child after freeing Parent
    would trigger a heap-use-after-free under ASan.
    """
    src = """
use sys.io
use sys.mem

data ChildNode {
    val: i32
}

data ParentNode {
    child: @ChildNode
    tag: i32
}

act run_parent_child_lifecycle(p_order: @i32) {
    // 1. Allocate Parent
    let p_parent: @ParentNode = mem.heap_alloc(@ParentNode, 1)
    p_parent.tag = 999
    // Deferred free of parent must happen SECOND
    defer mem.free(p_parent)
    defer p_order[0] = p_order[0] * 10 + 2

    // 2. Allocate Child and link to Parent
    let p_child: @ChildNode = mem.heap_alloc(@ChildNode, 1)
    p_child.val = 42
    p_parent.child = p_child

    // Deferred free of child must happen FIRST (LIFO) while parent is still valid
    defer mem.free(p_child)
    defer p_order[0] = p_order[0] * 10 + 1
}

act main() -> i32 {
    let base = mem.heap_used()
    mut order: i32 = 0
    run_parent_child_lifecycle(@order)

    // LIFO order: child defer (1), parent defer (2) => order becomes 12
    if order != 12 {
        io.println("FAIL: expected order 12, got: {order}")
        return 1
    }

    let leaked: usize = mem.heap_used() - base
    if leaked != 0 {
        io.println("FAIL: leaked memory: {leaked}")
        return 1
    }

    io.println("PASS: uaf prevention parent child lifo succeeded")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "PASS: uaf prevention parent child lifo succeeded" in res.stdout


def test_defer_double_free_prevention_loop_break():
    """Double-free probe: Loop iteration allocates heap memory and registers defer free,
    then executes 'break'. The break unrolls loop defers. Loop exit block must NOT
    re-emit loop defers. If double-emission occurred, double-free would crash under ASan.
    """
    src = """
use sys.io
use sys.mem

act loop_with_break_free(p_cleanups: @i32) -> i32 {
    let p_outer: @i32 = mem.heap_alloc(@i32, 4)
    defer mem.free(p_outer)
    defer p_cleanups[0] += 1

    mut i: i32 = 0
    loop i < 10 {
        let p_iter: @i32 = mem.heap_alloc(@i32, 4)
        p_iter[0] = i * 10
        defer mem.free(p_iter)
        defer p_cleanups[0] += 1

        if i == 3 {
            // Break must free p_iter exactly once, and NOT free p_outer yet
            break
        }
        i += 1
    }

    // p_outer is still valid and un-freed here
    return 42
}

act main() -> i32 {
    let base = mem.heap_used()
    mut cleanups: i32 = 0
    let res = loop_with_break_free(@cleanups)

    if res != 42 {
        io.println("FAIL: res expected 42")
        return 1
    }
    // 4 iterations ran (i=0, 1, 2, 3), each freeing p_iter once (4 frees),
    // plus 1 free for p_outer = 5 total frees
    if cleanups != 5 {
        io.println("FAIL: cleanups count expected 5, got: {cleanups}")
        return 1
    }

    let leaked: usize = mem.heap_used() - base
    if leaked != 0 {
        io.println("FAIL: leaked: {leaked}")
        return 1
    }

    io.println("PASS: double free prevention loop break succeeded")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "PASS: double free prevention loop break succeeded" in res.stdout


def test_defer_double_free_prevention_early_return_in_branches():
    """Double-free probe: If/else branch tree with heap allocations and deferred frees
    where some branches return early and others fall through.
    Verifies that no deferred free is emitted in duplicate.
    """
    src = """
use sys.io
use sys.mem

act branching_frees(branch: i32, p_frees: @i32) -> i32 {
    let p_fn: @i32 = mem.heap_alloc(@i32, 4)
    defer mem.free(p_fn)
    defer p_frees[0] += 1

    if branch == 1 {
        let p1: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p1)
        defer p_frees[0] += 1
        return 11
    } else if branch == 2 {
        let p2: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p2)
        defer p_frees[0] += 1
        // Fallthrough out of if/else
    } else {
        let p3: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p3)
        defer p_frees[0] += 1
        return 33
    }

    let p_post: @i32 = mem.heap_alloc(@i32, 4)
    defer mem.free(p_post)
    defer p_frees[0] += 1
    return 22
}

act main() -> i32 {
    let base = mem.heap_used()

    // Pass 1: early return in branch 1 (p1 freed + p_fn freed = 2)
    mut frees1: i32 = 0
    let r1 = branching_frees(1, @frees1)
    if r1 != 11 or frees1 != 2 {
        io.println("FAIL: pass 1 r1={r1}, frees1={frees1}")
        return 1
    }

    // Pass 2: fallthrough in branch 2 (p2 freed at branch exit, p_post freed at fn exit, p_fn freed at fn exit = 3)
    mut frees2: i32 = 0
    let r2 = branching_frees(2, @frees2)
    if r2 != 22 or frees2 != 3 {
        io.println("FAIL: pass 2 r2={r2}, frees2={frees2}")
        return 1
    }

    // Pass 3: early return in branch 3 (p3 freed + p_fn freed = 2)
    mut frees3: i32 = 0
    let r3 = branching_frees(3, @frees3)
    if r3 != 33 or frees3 != 2 {
        io.println("FAIL: pass 3 r3={r3}, frees3={frees3}")
        return 1
    }

    let leaked: usize = mem.heap_used() - base
    if leaked != 0 {
        io.println("FAIL: leaked: {leaked}")
        return 1
    }

    io.println("PASS: double free prevention branches succeeded")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "PASS: double free prevention branches succeeded" in res.stdout


def test_defer_double_free_prevention_tagged_union_arm():
    """Double-free probe: Tagged union match arm allocates heap memory and registers defer free,
    then reaches arm end (breaking to match exit). Verifies arm cleanup runs once and does not
    conflict with outer function defer cleanups.
    """
    src = """
use sys.io
use sys.mem

kind ValKind {
    None
    Integer(n: i32)
    Text(s: string)
}

act match_with_frees(v: ValKind, p_frees: @i32) -> i32 {
    let p_outer: @i32 = mem.heap_alloc(@i32, 4)
    defer mem.free(p_outer)
    defer p_frees[0] += 1

    mut result: i32 = 0
    on v {
        .Integer(n) => {
            let p_arm: @i32 = mem.heap_alloc(@i32, 4)
            p_arm[0] = n * 2
            defer mem.free(p_arm)
            defer p_frees[0] += 1
            result = p_arm[0]
        }
        .Text(s) => {
            let p_text: @i32 = mem.heap_alloc(@i32, 4)
            defer mem.free(p_text)
            defer p_frees[0] += 1
            result = 77
        }
        .None => {
            result = 0
        }
    }

    return result
}

act main() -> i32 {
    let base = mem.heap_used()

    mut frees: i32 = 0
    let r1 = match_with_frees(ValKind.Integer(21), @frees)
    if r1 != 42 or frees != 2 {
        io.println("FAIL: match Integer r1={r1}, frees={frees}")
        return 1
    }

    let r2 = match_with_frees(ValKind.None, @frees)
    // None has no arm allocation, only p_outer (1 free => frees=3)
    if r2 != 0 or frees != 3 {
        io.println("FAIL: match None r2={r2}, frees={frees}")
        return 1
    }

    let leaked: usize = mem.heap_used() - base
    if leaked != 0 {
        io.println("FAIL: leaked: {leaked}")
        return 1
    }

    io.println("PASS: double free prevention tagged union arm succeeded")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "PASS: double free prevention tagged union arm succeeded" in res.stdout


def test_defer_matrix_asan_ubsan_coverage():
    """Verifies that the defer test matrix runs cleanly under AddressSanitizer and
    UndefinedBehaviorSanitizer when available, and verifies zero leaks via mem.heap_used().
    On POSIX (Ubuntu/Clang in CI), this executes with full ASan/UBSan instrumentation.
    On Windows without libasan, it verifies exact zero-leak heap accounting.
    """
    test_vl = REPO_ROOT / "std" / "tests" / "mem" / "defer_test.vl"
    assert test_vl.exists(), "defer_test.vl missing"

    # If VELO_CFLAGS is set with sanitizer (as in CI sanitizer job), run_velo_source and velo run
    # will compile under ASan/UBSan automatically via driver_cc.
    env = get_build_env()
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        timeout=20.0,
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.mem.defer all assertions succeeded" in res.stdout

    # Verify no sanitizer violation strings appeared in stderr or stdout
    output = res.stdout + res.stderr
    assert "AddressSanitizer" not in output
    assert "UndefinedBehaviorSanitizer" not in output
    assert "runtime error:" not in output
    assert "leak-sanitizer" not in output
    assert "attempting double-free" not in output
    assert "heap-use-after-free" not in output


def test_defer_step2_specification_examples():
    """Compiles and executes the verified concrete code examples documented in
    docs/STEP2_SPECIFICATION.md Section 2.2.8.
    Verifies that all specification examples compile and run cleanly with 0 leaks.
    """
    src = """
use sys.io
use sys.mem

kind Action {
    Quit
    Process(data: i32)
}

// 1. Function Scope (LIFO Execution)
act example_function_lifo(p_order: @i32) {
    defer p_order[0] = p_order[0] * 10 + 3
    defer p_order[0] = p_order[0] * 10 + 2
    defer p_order[0] = p_order[0] * 10 + 1
}

// 2. Conditional Branch Scoping & Sibling Isolation
act example_branch_scoping(flag: bool) -> i32 {
    let p_fn: @i32 = mem.heap_alloc(@i32, 4)
    defer mem.free(p_fn)

    if flag {
        let p_branch: @i32 = mem.heap_alloc(@i32, 4)
        defer mem.free(p_branch)
        p_branch[0] = 42
    } // p_branch is freed HERE at closing brace!

    return 0
}

// 3. Tagged Union Pattern Match Arms
act example_match_arm_scoping(a: Action, p_res: @i32) {
    on a {
        .Process(v) => {
            let p_arm: @i32 = mem.heap_alloc(@i32, 4)
            defer mem.free(p_arm)
            p_arm[0] = v * 2
            p_res[0] = p_arm[0]
        } // p_arm is freed HERE before break out of match!
        .Quit => {
            p_res[0] = 0
        }
    }
}

// 4. Loop Iteration Boundaries, Break, and Continue
act example_loop_iteration_cleanup() {
    mut i: i32 = 0
    loop i < 100 {
        let buf: @u8 = mem.heap_alloc(@u8, 1024)
        defer mem.free(buf)

        if i == 50 {
            i += 1
            continue
        }
        if i == 80 {
            break
        }
        i += 1
    }
}

// 5. Early-Exit Multi-Level Unwinding
act example_early_exit_unwind(trigger: bool) -> i32 {
    let p_fn: @i32 = mem.heap_alloc(@i32, 4)
    p_fn[0] = 32
    defer mem.free(p_fn)

    if trigger {
        let p_if: @i32 = mem.heap_alloc(@i32, 4)
        p_if[0] = 10
        defer mem.free(p_if)
        return p_fn[0] + p_if[0] // Evaluates return expr (42), frees p_if, frees p_fn, returns
    }

    return p_fn[0]
}

act main() -> i32 {
    let base = mem.heap_used()

    // 1. Verify function LIFO
    mut order: i32 = 0
    example_function_lifo(@order)
    if order != 123 {
        io.println("FAIL: lifo order expected 123, got: {order}")
        return 1
    }

    // 2. Verify branch scoping
    let r_branch = example_branch_scoping(true)
    if r_branch != 0 {
        io.println("FAIL: branch scoping return mismatch")
        return 1
    }

    // 3. Verify match arm scoping
    mut match_res: i32 = 0
    example_match_arm_scoping(Action.Process(21), @match_res)
    if match_res != 42 {
        io.println("FAIL: match arm scoping result mismatch: {match_res}")
        return 1
    }

    // 4. Verify loop iteration cleanup with continue and break
    example_loop_iteration_cleanup()

    // 5. Verify early-exit multi-level unwinding
    let r_early = example_early_exit_unwind(true)
    if r_early != 42 {
        io.println("FAIL: early exit result expected 42, got: {r_early}")
        return 1
    }

    let leaked: usize = mem.heap_used() - base
    if leaked != 0 {
        io.println("FAIL: leaked: {leaked}")
        return 1
    }

    io.println("PASS: STEP2_SPECIFICATION examples verified successfully")
    return 0
}
"""
    res = run_velo_source(src)
    assert res.returncode == 0, f"failed: {res.stdout}\n{res.stderr}"
    assert "PASS: STEP2_SPECIFICATION examples verified successfully" in res.stdout







