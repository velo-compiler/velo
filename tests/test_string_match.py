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

def test_string_match_std_suite():
    """Runs the full std/tests/string_match_test.vl battery."""
    res = _run_stage2(["run", "std/tests/string_match_test.vl"])
    assert res.returncode == 0, f"Failed: {res.stderr}\n{res.stdout}"
    assert "All string match in 'on' tests passed successfully!" in res.stdout

def test_string_match_type_mismatch(tmp_path):
    """Verifies that pattern type mismatch against subject reports compile error."""
    code = """
use std.io

act main() {
    let s = "hello"
    on s {
        42: io.println("num")
        else: io.println("other")
    }
}
"""
    f = tmp_path / "type_mismatch.vl"
    f.write_text(code, encoding="utf-8")
    res = _run_stage2(["check", str(f)])
    assert res.returncode != 0
    assert "Pattern type does not match subject type in 'on' statement" in (res.stdout + res.stderr)

