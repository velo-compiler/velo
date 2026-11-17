import subprocess
import pytest
from pathlib import Path
from conftest import velo_exe

def _run_stage2(cmd: list) -> subprocess.CompletedProcess:
    velo_bin = Path(str(velo_exe())).resolve()
    if not velo_bin.exists():
        pytest.skip("bin/velo.exe not built yet")
    full_cmd = [str(velo_bin)] + cmd
    return subprocess.run(full_cmd, capture_output=True, text=True)

def test_string_concat_std_suite():
    """Runs the full std/tests/string_concat_test.vl battery."""
    res = _run_stage2(["run", "std/tests/string_concat_test.vl"])
    assert res.returncode == 0, f"Failed: {res.stderr}\n{res.stdout}"
    assert "All string concatenation tests passed successfully!" in res.stdout

def test_string_concat_mixed_type_rejections(tmp_path):
    """Verifies that mixing string and non-string with '+' reports compile error."""
    code_int_str = """
use std.io

act main() {
    let s = "number: " + 42
    io.println(s)
}
"""
    f = tmp_path / "mixed_int_str.vl"
    f.write_text(code_int_str, encoding="utf-8")
    res = _run_stage2(["check", str(f)])
    assert res.returncode != 0
    assert "cannot apply '+' to string operands" in (res.stdout + res.stderr)

def test_string_sub_rejection(tmp_path):
    """Verifies that subtracting strings reports compile error."""
    code_sub = """
use std.io

act main() {
    let a = "hello"
    let b = "lo"
    let c = a - b
    io.println(c)
}
"""
    f = tmp_path / "str_sub.vl"
    f.write_text(code_sub, encoding="utf-8")
    res = _run_stage2(["check", str(f)])
    assert res.returncode != 0
    assert "cannot apply '-' to string operands" in (res.stdout + res.stderr)

