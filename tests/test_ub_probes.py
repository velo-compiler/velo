"""Phase 74.7: Regression tests for all probes in Phase 74 Evidence table.

Evidence Table Mapping:
Row 1: Signed overflow emitted as plain C -> probe 'x: i32 = 2147483647; x = x + 1'
       Tested: wraps to -2147483648 with -fwrapv in debug/release; anti-UB optimization preserved.
Row 2: Divide by zero kills process with no diagnostic -> probe 'x = 1 / x where x == 0'
       Tested: traps with 'Velo Fatal Error: division by zero at' and exit code 1; compile-time rejected.
Row 3: Dynamic index into fixed array unchecked -> probe 'mut buf: [4]i32; mut i: i32 = 7; buf[i] = 1'
       Tested: traps with 'Velo Fatal Error: array index out of bounds: 7 (len 4)!'; compile-time rejected for const.
Row 4: Compiler-source UB (docs/gaps_archive.md:181):
       - Overlapping mem.copy: asserted in debug mode (use mem.move); mem.move handles overlaps.
       - Non-heap/zone/stack pointer to mem.free/realloc: traps with provenance error; double-free traps.
       - Allocation size count * sizeof overflow: traps with 'Allocation size overflow'.
Row 5: Sanitizer verification: scripts/bootstrap_sanitized.sh, build_modes.md, and ci.yml.
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


# -----------------------------------------------------------------------------
# Row 1: Signed Integer Overflow Probe
# -----------------------------------------------------------------------------

@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_probe_row1_signed_integer_overflow_wraparound(tmp_path, mode):
    """Evidence Row 1 probe: x: i32 = 2147483647; x = x + 1 wraps to -2147483648."""
    _require_native()
    src = tmp_path / "probe_row1.vl"
    src.write_text("""use std.io

act main() {
    mut x: i32 = 2147483647
    x = x + 1
    io.println("x={x}")

    // Anti-UB optimizer assumption check: x + 1 must be less than x
    if x < 2147483647 {
        io.println("anti-ub-ok")
    }

    // 64-bit overflow probe
    mut y: i64 = 9223372036854775807
    y = y + 1
    io.println("y={y}")
}
""", encoding="utf-8")
    res = run_velo(["run", mode, str(src)])
    assert res.returncode == 0, f"Failed in {mode}: {res.stderr}"
    assert "x=-2147483648" in res.stdout
    assert "anti-ub-ok" in res.stdout
    assert "y=-9223372036854775808" in res.stdout


# -----------------------------------------------------------------------------
# Row 2: Divide by Zero Probes
# -----------------------------------------------------------------------------

@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_probe_row2_divide_by_zero_runtime_fatal(tmp_path, mode):
    """Evidence Row 2 probe: x = 1 / x where x == 0 traps with Velo fatal diagnostic."""
    _require_native()
    src = tmp_path / "probe_row2.vl"
    src.write_text("""use std.io

act main() {
    mut x: i32 = 0
    let y = 1 / x
    io.println("SHOULD NOT REACH y={y}")
}
""", encoding="utf-8")
    res = run_velo(["run", mode, str(src)])
    assert res.returncode != 0
    assert "Velo Fatal Error: division by zero at" in res.stderr
    assert "SHOULD NOT REACH" not in res.stdout


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_probe_row2_modulo_by_zero_runtime_fatal(tmp_path, mode):
    """Dynamic modulo by zero traps with Velo fatal diagnostic."""
    _require_native()
    src = tmp_path / "probe_row2_mod.vl"
    src.write_text("""use std.io

act main() {
    mut x: i32 = 0
    let y = 100 % x
    io.println("SHOULD NOT REACH y={y}")
}
""", encoding="utf-8")
    res = run_velo(["run", mode, str(src)])
    assert res.returncode != 0
    assert "Velo Fatal Error: division by zero at" in res.stderr
    assert "SHOULD NOT REACH" not in res.stdout


def test_probe_row2_compile_time_div_zero_rejected(tmp_path):
    """Compile-time constant division by zero is rejected during semantic analysis."""
    _require_native()
    src = tmp_path / "probe_row2_const.vl"
    src.write_text("""use std.io

act main() {
    let y = 42 / 0
    io.println("y={y}")
}
""", encoding="utf-8")
    res = run_velo(["check", str(src)])
    assert res.returncode != 0
    assert "division by zero" in res.stdout.lower() or "division by zero" in res.stderr.lower()


# -----------------------------------------------------------------------------
# Row 3: Dynamic Index into Fixed-Size Array Probes
# -----------------------------------------------------------------------------

@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_probe_row3_dynamic_array_index_write_oob_fatal(tmp_path, mode):
    """Evidence Row 3 probe: mut buf: [4]i32; mut i: i32 = 7; buf[i] = 1 traps with Velo fatal."""
    _require_native()
    src = tmp_path / "probe_row3_write.vl"
    src.write_text("""use std.io

act main() {
    mut buf: [4]i32
    mut i: i32 = 7
    buf[i] = 1
    io.println("no trap")
}
""", encoding="utf-8")
    res = run_velo(["run", mode, str(src)])
    assert res.returncode != 0
    assert "Velo Fatal Error: array index out of bounds: 7 (len 4)!" in res.stderr
    assert "no trap" not in res.stdout


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_probe_row3_dynamic_array_index_read_oob_fatal(tmp_path, mode):
    """Reading with dynamic out-of-bounds index traps with Velo fatal."""
    _require_native()
    src = tmp_path / "probe_row3_read.vl"
    src.write_text("""use std.io

act main() {
    mut buf: [4]i32
    mut i: i32 = 7
    let val = buf[i]
    io.println("no trap val={val}")
}
""", encoding="utf-8")
    res = run_velo(["run", mode, str(src)])
    assert res.returncode != 0
    assert "Velo Fatal Error: array index out of bounds: 7 (len 4)!" in res.stderr
    assert "no trap" not in res.stdout


def test_probe_row3_constant_array_index_oob_rejected_at_compile_time(tmp_path):
    """Constant literal array index buf[7] is rejected at compile time."""
    _require_native()
    src = tmp_path / "probe_row3_const.vl"
    src.write_text("""act main() {
    mut buf: [4]i32
    buf[7] = 1
}
""", encoding="utf-8")
    res = run_velo(["check", str(src)])
    assert res.returncode != 0
    assert "out of bounds" in res.stdout.lower() or "out of bounds" in res.stderr.lower()


def test_probe_row3_unsafe_array_index_opt_out(tmp_path):
    """--unsafe-array-index bypasses runtime guard for parity with shelf."""
    _require_native()
    src = tmp_path / "probe_row3_unsafe.vl"
    src.write_text("""use std.io

act main() {
    mut buf: [4]i32
    mut i: i32 = 2
    buf[i] = 99
    io.println("val={buf[i]}")
}
""", encoding="utf-8")
    res = run_velo(["run", "--unsafe-array-index", str(src)])
    assert res.returncode == 0
    assert "val=99" in res.stdout


# -----------------------------------------------------------------------------
# Row 4: Compiler-Source UB Probes (docs/gaps_archive.md:181)
# -----------------------------------------------------------------------------

def test_probe_row4_overlapping_mem_copy_debug_fatal(tmp_path):
    """Overlapping mem.copy in debug mode traps with fatal diagnostic."""
    _require_native()
    src = tmp_path / "probe_row4_overlap.vl"
    src.write_text("""use std.io
use std.mem

act main() {
    let buf: @u8 = mem.heap_alloc(@u8, 32)
    let p0: @u8 = buf
    let p5: @u8 = @buf[5]
    io.println("calling overlapping mem.copy")
    mem.copy(p5, p0, 10)
    io.println("SHOULD NOT REACH")
}
""", encoding="utf-8")
    res = run_velo(["run", "--debug", str(src)])
    assert res.returncode != 0
    assert "mem.copy destination and source overlap (use mem.move instead)!" in res.stderr
    assert "SHOULD NOT REACH" not in res.stdout


def test_probe_row4_mem_move_handles_overlapping_regions(tmp_path):
    """mem.move safely handles overlapping memory shift."""
    _require_native()
    src = tmp_path / "probe_row4_move.vl"
    src.write_text("""use std.io
use std.mem

act main() {
    let buf: @u8 = mem.heap_alloc(@u8, 32)
    buf[0] = 1
    buf[1] = 2
    buf[2] = 3
    buf[3] = 4

    let p0: @u8 = buf
    let p1: @u8 = @buf[1]
    mem.move(p1, p0, 4)
    io.println("moved: {buf[1]} {buf[2]} {buf[3]} {buf[4]}")
    mem.free(buf)
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode == 0, f"Failed: {res.stderr}"
    assert "moved: 1 2 3 4" in res.stdout


def test_probe_row4_free_zone_pointer_provenance_fatal(tmp_path):
    """Calling mem.free on a zone arena pointer traps with provenance fatal."""
    _require_native()
    src = tmp_path / "probe_row4_zone_free.vl"
    src.write_text("""use std.io
use std.mem

act main() {
    zone {
        let p: @u8 = mem.alloc(@u8, 16)
        mem.free(p)
        io.println("SHOULD NOT REACH")
    }
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode != 0
    assert "mem.free called with non-heap pointer (pointer is in zone arena)!" in res.stderr
    assert "SHOULD NOT REACH" not in res.stdout


def test_probe_row4_double_free_fatal(tmp_path):
    """Double-free traps with 'already-freed pointer (double free)!'."""
    _require_native()
    src = tmp_path / "probe_row4_double_free.vl"
    src.write_text("""use std.io
use std.mem

act main() {
    let p: @u8 = mem.heap_alloc(@u8, 16)
    mem.free(p)
    mem.free(p)
    io.println("SHOULD NOT REACH")
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode != 0
    assert "mem.free called on already-freed pointer (double free)!" in res.stderr
    assert "SHOULD NOT REACH" not in res.stdout


def test_probe_row4_allocation_size_overflow_fatal(tmp_path):
    """Allocation size overflow (count * sizeof) traps with fatal diagnostic."""
    _require_native()
    src = tmp_path / "probe_row4_size_overflow.vl"
    src.write_text("""use std.io
use std.mem

act main() {
    // 0xFFFFFFFFFFFFFFFF count of u64 will overflow size_t
    let huge_count: usize = 18446744073709551615usize
    let p: @u64 = mem.heap_alloc(@u64, huge_count)
    io.println("SHOULD NOT REACH")
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode != 0
    assert "Allocation size overflow" in res.stderr
    assert "SHOULD NOT REACH" not in res.stdout


# -----------------------------------------------------------------------------
# Row 5: Sanitizer Verification Probes
# -----------------------------------------------------------------------------

def test_probe_row5_sanitizer_bootstrap_script_exists():
    """scripts/bootstrap_sanitized.sh exists and carries sanitizer flags."""
    script = REPO_ROOT / "scripts" / "bootstrap_sanitized.sh"
    assert script.exists(), "scripts/bootstrap_sanitized.sh must exist"
    content = script.read_text(encoding="utf-8")
    assert "-fsanitize=address,undefined" in content
    assert "-fno-sanitize-recover=all" in content
    assert "VELO_CFLAGS" in content
    assert "VELO_LDFLAGS" in content


def test_probe_row5_sanitizer_local_doc_section_exists():
    """docs/build_sheets/build_modes.md documents sanitizer-local packages."""
    doc = REPO_ROOT / "docs" / "build_sheets" / "build_modes.md"
    assert doc.exists()
    content = doc.read_text(encoding="utf-8")
    assert "sanitizer-local" in content
    assert "libasan8" in content
    assert "libubsan1" in content


def test_probe_row5_ci_workflow_has_sanitizer_lane():
    """ci.yml defines a sanitizer lane invoking bootstrap_sanitized.sh."""
    ci = REPO_ROOT / ".github" / "workflows" / "ci.yml"
    assert ci.exists()
    content = ci.read_text(encoding="utf-8")
    assert "sanitizer:" in content
    assert "bootstrap_sanitized.sh" in content
