import subprocess
import pytest
from pathlib import Path

def _run_stage2(cmd: list) -> subprocess.CompletedProcess:
    velo_exe = Path("bin/velo.exe").resolve()
    if not velo_exe.exists():
        pytest.skip("bin/velo.exe not built yet")
    full_cmd = [str(velo_exe)] + cmd
    return subprocess.run(full_cmd, capture_output=True, text=True)

def test_if_expr_std_test():
    """Runs the full std/tests/if_expr_test.vl battery."""
    res = _run_stage2(["run", "std/tests/if_expr_test.vl"])
    assert res.returncode == 0, f"Failed: {res.stderr}\n{res.stdout}"
    assert "All if-else expression tests passed!" in res.stdout

def test_if_expr_incompatible_types(tmp_path):
    """Verifies that branches with incompatible types produce a semantic error."""
    code = """
use std.io

act main() {
    let x = if true { 42 } else { "mismatch" }
    io.println("val: {x}")
}
"""
    f = tmp_path / "incompat.vl"
    f.write_text(code, encoding="utf-8")
    res = _run_stage2(["check", str(f)])
    assert res.returncode != 0
    assert "Incompatible branch types in if-expression" in (res.stdout + res.stderr)

