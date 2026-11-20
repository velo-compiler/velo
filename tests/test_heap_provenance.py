"""Phase 74.5: Tests for mem.realloc and mem.free provenance checks.

Security Invariant I74.5:
No Velo program can free or realloc a pointer not originating from mem.heap_alloc
without a deterministic fatal error.
1. Zone pointers passed to mem.free or mem.realloc fatal with named diagnostic.
2. Already-freed pointers (double-free or realloc after free) fatal with named diagnostic.
3. Invalid, stack, or foreign pointers fatal with named diagnostic.
4. mem.free(null) is safe no-op; mem.realloc(null, @T, count) allocates.
5. --unsafe-heap flag opts out of provenance overhead and checks.
"""
import subprocess
from pathlib import Path
import pytest
from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()


def get_env():
    import os
    env = os.environ.copy()
    if cc_dir() not in env.get("PATH", ""):
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return env


def _require_native():
    if not VELO_EXE.exists():
        pytest.skip("bin/velo not built")


def run_velo(args, tmp_path=None):
    return subprocess.run(
        [str(VELO_EXE)] + args,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
        timeout=120,
    )


def test_free_zone_pointer_fatal(tmp_path):
    """Calling mem.free on a zone arena pointer fatals deterministically."""
    _require_native()
    src = tmp_path / "free_zone.vl"
    src.write_text("""use std.io
use std.mem

act main() {
    zone {
        let p: @u8 = mem.alloc(@u8, 32)
        io.println("allocated in zone")
        mem.free(p)
        io.println("SHOULD NOT REACH")
    }
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode != 0
    assert "mem.free called with non-heap pointer (pointer is in zone arena)!" in res.stderr
    assert "SHOULD NOT REACH" not in res.stdout


def test_realloc_zone_pointer_fatal(tmp_path):
    """Calling mem.realloc on a zone arena pointer fatals deterministically."""
    _require_native()
    src = tmp_path / "realloc_zone.vl"
    src.write_text("""use std.io
use std.mem

act main() {
    zone {
        let p: @u8 = mem.alloc(@u8, 32)
        io.println("allocated in zone")
        let p2: @u8 = mem.realloc(p, @u8, 64)
        io.println("SHOULD NOT REACH")
    }
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode != 0
    assert "mem.realloc called with non-heap pointer (pointer is in zone arena)!" in res.stderr
    assert "SHOULD NOT REACH" not in res.stdout


def test_double_free_fatal(tmp_path):
    """Double-free fatals with 'mem.free called on already-freed pointer'."""
    _require_native()
    src = tmp_path / "double_free.vl"
    src.write_text("""use std.io
use std.mem

act main() {
    let p: @u8 = mem.heap_alloc(@u8, 32)
    io.println("first free")
    mem.free(p)
    io.println("second free")
    mem.free(p)
    io.println("SHOULD NOT REACH")
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode != 0
    assert "mem.free called on already-freed pointer (double free)!" in res.stderr
    assert "SHOULD NOT REACH" not in res.stdout


def test_realloc_already_freed_fatal(tmp_path):
    """Calling mem.realloc on an already-freed pointer fatals deterministically."""
    _require_native()
    src = tmp_path / "realloc_freed.vl"
    src.write_text("""use std.io
use std.mem

act main() {
    let p: @u8 = mem.heap_alloc(@u8, 32)
    io.println("freeing")
    mem.free(p)
    io.println("reallocating freed pointer")
    let p2: @u8 = mem.realloc(p, @u8, 64)
    io.println("SHOULD NOT REACH")
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode != 0
    assert "mem.realloc called on already-freed pointer!" in res.stderr
    assert "SHOULD NOT REACH" not in res.stdout


def test_free_stack_pointer_fatal(tmp_path):
    """Passing a stack pointer or invalid pointer to mem.free fatals."""
    _require_native()
    src = tmp_path / "free_stack.vl"
    src.write_text("""use std.io
use std.mem

act main() {
    mut x: i64 = 12345
    let p: @i64 = @x
    io.println("freeing stack address")
    mem.free(p)
    io.println("SHOULD NOT REACH")
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode != 0
    assert "mem.free called with invalid pointer (not a valid heap allocation)!" in res.stderr
    assert "SHOULD NOT REACH" not in res.stdout


def test_realloc_stack_pointer_fatal(tmp_path):
    """Passing a stack pointer or invalid pointer to mem.realloc fatals."""
    _require_native()
    src = tmp_path / "realloc_stack.vl"
    src.write_text("""use std.io
use std.mem

act main() {
    mut x: i64 = 12345
    let p: @i64 = @x
    io.println("reallocating stack address")
    let p2: @i64 = mem.realloc(p, @i64, 4)
    io.println("SHOULD NOT REACH")
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode != 0
    assert "mem.realloc called with invalid pointer (not a valid heap allocation)!" in res.stderr
    assert "SHOULD NOT REACH" not in res.stdout


def test_free_and_realloc_null(tmp_path):
    """mem.free(null) is safe no-op, mem.realloc(null, @T, count) allocates cleanly."""
    _require_native()
    src = tmp_path / "null_ops.vl"
    src.write_text("""use std.io
use std.mem

act main() {
    // 1. mem.free(null) no-op
    let null_ptr: @u8 = null
    mem.free(null_ptr)
    io.println("null free ok")

    // 2. mem.realloc(null, ...) allocates
    let p: @u8 = mem.realloc(null, @u8, 16)
    p[0] = 42
    p[15] = 99
    io.println("p[0]={p[0]} p[15]={p[15]}")
    mem.free(p)
    io.println("all done")
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode == 0, f"Failed: {res.stderr}"
    assert "null free ok" in res.stdout
    assert "p[0]=42 p[15]=99" in res.stdout
    assert "all done" in res.stdout


def test_valid_heap_lifecycle_debug_and_release(tmp_path):
    """Valid allocation, realloc growth, data preservation, and free work in debug and release."""
    _require_native()
    src = tmp_path / "lifecycle.vl"
    src.write_text("""use std.io
use std.mem

act main() {
    let p: @u8 = mem.heap_alloc(@u8, 8)
    p[0] = 10
    p[1] = 20
    p[7] = 70

    // Grow allocation from 8 to 64 bytes
    let grown: @u8 = mem.realloc(p, @u8, 64)
    // Verify data preserved
    io.println("preserved: {grown[0]} {grown[1]} {grown[7]}")

    grown[63] = 99
    io.println("grown[63]={grown[63]}")

    // Shrink allocation from 64 to 16 bytes
    let shrunk: @u8 = mem.realloc(grown, @u8, 16)
    io.println("shrunk preserved: {shrunk[0]} {shrunk[1]} {shrunk[7]}")

    mem.free(shrunk)
    io.println("lifecycle finished cleanly")
}
""", encoding="utf-8")

    # Debug mode
    res_dbg = run_velo(["run", "--debug", str(src)])
    assert res_dbg.returncode == 0, f"Debug failed: {res_dbg.stderr}"
    assert "preserved: 10 20 70" in res_dbg.stdout
    assert "grown[63]=99" in res_dbg.stdout
    assert "shrunk preserved: 10 20 70" in res_dbg.stdout
    assert "lifecycle finished cleanly" in res_dbg.stdout

    # Release mode
    res_rel = run_velo(["run", "--release", str(src)])
    assert res_rel.returncode == 0, f"Release failed: {res_rel.stderr}"
    assert "preserved: 10 20 70" in res_rel.stdout
    assert "grown[63]=99" in res_rel.stdout
    assert "shrunk preserved: 10 20 70" in res_rel.stdout
    assert "lifecycle finished cleanly" in res_rel.stdout


def test_unsafe_heap_opt_out(tmp_path):
    """--unsafe-heap defines VELO_UNSAFE_HEAP and bypasses provenance checks."""
    _require_native()
    src = tmp_path / "unsafe_test.vl"
    src.write_text("""use std.io
use std.mem

act main() {
    let p: @u8 = mem.heap_alloc(@u8, 16)
    p[0] = 77
    io.println("val={p[0]}")
    mem.free(p)
    io.println("freed cleanly")
}
""", encoding="utf-8")

    # 1. Test emit-c with --unsafe-heap contains #define VELO_UNSAFE_HEAP 1
    c_out = tmp_path / "unsafe_emit.c"
    res_emit = run_velo(["emit-c", "--unsafe-heap", str(src), "-o", str(c_out)])
    assert res_emit.returncode == 0, f"emit-c failed: {res_emit.stderr}"
    c_content = c_out.read_text(encoding="utf-8")
    assert "#define VELO_UNSAFE_HEAP 1" in c_content

    # 2. Test run with --unsafe-heap
    res_run = run_velo(["run", "--unsafe-heap", str(src)])
    assert res_run.returncode == 0, f"run with --unsafe-heap failed: {res_run.stderr}"
    assert "val=77" in res_run.stdout
    assert "freed cleanly" in res_run.stdout

    # 3. Test build with --unsafe-heap
    exe_out = tmp_path / "unsafe_build.exe"
    res_build = run_velo(["build", "--unsafe-heap", str(src), "-o", str(exe_out)])
    assert res_build.returncode == 0, f"build failed: {res_build.stderr}"
    res_built_exe = subprocess.run([str(exe_out)], capture_output=True, text=True, timeout=30)
    assert res_built_exe.returncode == 0
    assert "val=77" in res_built_exe.stdout
    assert "freed cleanly" in res_built_exe.stdout
