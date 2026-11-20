"""Phase 74.4: Tests for mem.overlaps, debug-mode overlap fatal in mem.copy, and mem.move.

Security Invariant I74.4:
No Velo program can reach memcpy/memmove/memset with overlapping regions through the safe surface.
mem.overlaps(a, b, len_a, len_b) -> bool
mem.copy asserts non-overlap in Debug builds (fatal with named message).
mem.move is the designated overlapping-safe primitive.
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


def test_mem_overlaps_truth_table(tmp_path):
    """mem.overlaps returns true for overlapping regions, false for disjoint/adjacent/zero."""
    _require_native()
    src = tmp_path / "overlaps_test.vl"
    src.write_text("""use std.io
use std.mem

act main() {
    let buf: @u8 = mem.heap_alloc(@u8, 64)
    // Pointer arithmetic via indexing / offset
    let p0: @u8 = buf
    let p5: @u8 = @buf[5]
    let p10: @u8 = @buf[10]
    let p20: @u8 = @buf[20]

    // 1. Overlapping: p0 [0..10) and p5 [5..15)
    let ov1: bool = mem.overlaps(p0, p5, 10, 10)
    if ov1 { io.println("ov1=true") } else { io.println("ov1=false") }

    // 2. Overlapping: p5 [5..15) and p0 [0..10) (reversed order)
    let ov2: bool = mem.overlaps(p5, p0, 10, 10)
    if ov2 { io.println("ov2=true") } else { io.println("ov2=false") }

    // 3. Overlapping: identical pointers p0 [0..10) and p0 [0..10)
    let ov3: bool = mem.overlaps(p0, p0, 10, 10)
    if ov3 { io.println("ov3=true") } else { io.println("ov3=false") }

    // 4. Overlapping: subset p0 [0..20) and p5 [5..10)
    let ov4: bool = mem.overlaps(p0, p5, 20, 5)
    if ov4 { io.println("ov4=true") } else { io.println("ov4=false") }

    // 5. Disjoint adjacent: p0 [0..10) and p10 [10..20)
    let ov5: bool = mem.overlaps(p0, p10, 10, 10)
    if ov5 { io.println("ov5=true") } else { io.println("ov5=false") }

    // 6. Disjoint adjacent: p10 [10..20) and p0 [0..10)
    let ov6: bool = mem.overlaps(p10, p0, 10, 10)
    if ov6 { io.println("ov6=true") } else { io.println("ov6=false") }

    // 7. Disjoint separated: p0 [0..10) and p20 [20..30)
    let ov7: bool = mem.overlaps(p0, p20, 10, 10)
    if ov7 { io.println("ov7=true") } else { io.println("ov7=false") }

    // 8. Zero length: p0 [0..0) and p0 [0..10)
    let ov8: bool = mem.overlaps(p0, p0, 0, 10)
    if ov8 { io.println("ov8=true") } else { io.println("ov8=false") }

    // 9. Null pointer: null and p0 [0..10)
    let ov9: bool = mem.overlaps(null, p0, 10, 10)
    if ov9 { io.println("ov9=true") } else { io.println("ov9=false") }

    mem.free(buf)
}
""", encoding="utf-8")

    res = run_velo(["run", str(src)])
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    lines = [line.strip() for line in res.stdout.strip().splitlines()]
    assert "ov1=true" in lines
    assert "ov2=true" in lines
    assert "ov3=true" in lines
    assert "ov4=true" in lines
    assert "ov5=false" in lines
    assert "ov6=false" in lines
    assert "ov7=false" in lines
    assert "ov8=false" in lines
    assert "ov9=false" in lines


def test_mem_copy_overlap_debug_fatal(tmp_path):
    """In Debug builds (--debug), overlapping mem.copy triggers a fatal error."""
    _require_native()
    src = tmp_path / "copy_overlap_debug.vl"
    src.write_text("""use std.io
use std.mem

act main() {
    let buf: @u8 = mem.heap_alloc(@u8, 32)
    let dest: @u8 = @buf[2]
    let src_ptr: @u8 = buf
    // dest [2..18) overlaps src [0..16)
    mem.copy(dest, src_ptr, 16)
    io.println("UNREACHABLE")
    mem.free(buf)
}
""", encoding="utf-8")

    res = run_velo(["run", str(src), "--debug"])
    assert res.returncode != 0, f"Expected fatal error, but process succeeded: {res.stdout}"
    assert "Velo Fatal Error: mem.copy destination and source overlap (use mem.move instead)!" in res.stderr
    assert "UNREACHABLE" not in res.stdout


def test_mem_copy_overlap_release_runs(tmp_path):
    """In Release builds (--release), mem.copy does not assert non-overlap (raw C memcpy behavior)."""
    _require_native()
    src = tmp_path / "copy_overlap_release.vl"
    src.write_text("""use std.io
use std.mem

act main() {
    let buf: @u8 = mem.heap_alloc(@u8, 32)
    let dest: @u8 = @buf[2]
    let src_ptr: @u8 = buf
    // dest [2..18) overlaps src [0..16)
    mem.copy(dest, src_ptr, 16)
    io.println("RELEASE_OK")
    mem.free(buf)
}
""", encoding="utf-8")

    res = run_velo(["run", str(src), "--release"])
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert "RELEASE_OK" in res.stdout
    assert "Velo Fatal Error: mem.copy destination and source overlap" not in res.stderr


def test_mem_move_handles_overlapping_regions(tmp_path):
    """mem.move is the designated overlapping-safe primitive and works in both Debug and Release."""
    _require_native()
    src = tmp_path / "move_overlap.vl"
    src.write_text("""use std.io
use std.mem

act main() {
    let buf: @u8 = mem.heap_alloc(@u8, 16)
    // Fill buf with 1, 2, 3, 4, 5...
    mut i: i32 = 0
    loop i < 16 {
        buf[i] = (i + 1) as u8
        i += 1
    }

    // Shift [0..4) forward to [2..6)
    let dest: @u8 = @buf[2]
    let src_ptr: @u8 = buf
    mem.move(dest, src_ptr, 4)

    // buf[0] should be 1, buf[1] should be 2, buf[2] should be 1, buf[3] should be 2, buf[4] should be 3, buf[5] should be 4
    let b0: i32 = buf[0] as i32
    let b1: i32 = buf[1] as i32
    let b2: i32 = buf[2] as i32
    let b3: i32 = buf[3] as i32
    let b4: i32 = buf[4] as i32
    let b5: i32 = buf[5] as i32
    io.println("vals={b0},{b1},{b2},{b3},{b4},{b5}")

    mem.free(buf)
}
""", encoding="utf-8")

    # Test in Debug mode
    res_dbg = run_velo(["run", str(src), "--debug"])
    assert res_dbg.returncode == 0, f"Debug stdout: {res_dbg.stdout}\nstderr: {res_dbg.stderr}"
    assert "vals=1,2,1,2,3,4" in res_dbg.stdout

    # Test in Release mode
    res_rel = run_velo(["run", str(src), "--release"])
    assert res_rel.returncode == 0, f"Release stdout: {res_rel.stdout}\nstderr: {res_rel.stderr}"
    assert "vals=1,2,1,2,3,4" in res_rel.stdout
