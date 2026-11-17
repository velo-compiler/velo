import subprocess
import pytest
from pathlib import Path
from conftest import velo_exe

def _run_stage2(cmd: list) -> subprocess.CompletedProcess:
    velo_bin = Path(str(velo_exe())).resolve()
    if not velo_bin.exists():
        pytest.skip("bin/velo.exe not built yet")
    full_cmd = [str(velo_bin)] + cmd
    return subprocess.run(full_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

def test_fixed_array_std_suite():
    """Runs the full std/tests/fixed_array_test.vl battery."""
    res = _run_stage2(["run", "std/tests/fixed_array_test.vl"])
    assert res.returncode == 0, f"Failed: {res.stderr}\n{res.stdout}"
    assert "All fixed-size stack array tests passed successfully!" in res.stdout

def test_fixed_array_out_of_bounds_rejection(tmp_path):
    """Verifies that out-of-bounds indexing on fixed array reports compile error."""
    code = """
use std.io

act main() {
    mut buf: [16]u8
    buf[16] = 1 as u8
}
"""
    f = tmp_path / "oob.vl"
    f.write_text(code, encoding="utf-8")
    res = _run_stage2(["check", str(f)])
    assert res.returncode != 0
    assert "Array index out of bounds" in (res.stdout + res.stderr)

def test_fixed_array_immutable_mutation_rejection(tmp_path):
    """Verifies that mutating an element of an immutable array reports compile error."""
    code = """
use std.io

act main() {
    let arr: [4]i32 = [1, 2, 3, 4]
    arr[0] = 99
}
"""
    f = tmp_path / "immut.vl"
    f.write_text(code, encoding="utf-8")
    res = _run_stage2(["check", str(f)])
    assert res.returncode != 0
    assert "cannot assign to element of immutable variable 'arr'" in (res.stdout + res.stderr)

def test_fixed_array_zero_size_rejection(tmp_path):
    """Verifies that zero-size array reports parse error."""
    code = """
use std.io

act main() {
    mut buf: [0]u8
}
"""
    f = tmp_path / "zero_size.vl"
    f.write_text(code, encoding="utf-8")
    res = _run_stage2(["check", str(f)])
    assert res.returncode != 0
    assert "Fixed-size array length must be greater than zero" in (res.stdout + res.stderr)

