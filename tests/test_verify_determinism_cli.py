"""
Tests for native compiler --verify-determinism flag and bootstrap.c budget monitoring (Task 80.6).
"""
import subprocess
import sys
from pathlib import Path
import pytest
from conftest import velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
SRC_MAIN = REPO_ROOT / "src" / "main.vl"


def test_cli_usage_shows_verify_determinism():
    """Verify that velo help/usage displays --verify-determinism."""
    bin_path = velo_exe()
    if not bin_path.exists():
        pytest.skip("bin/velo.exe not built")
    proc = subprocess.run([str(bin_path)], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO_ROOT))
    assert "--verify-determinism" in proc.stdout


def test_verify_determinism_execution():
    """Verify that velo build src/main.vl --verify-determinism executes and reports SHA-256 match."""
    bin_path = velo_exe()
    if not bin_path.exists():
        pytest.skip("bin/velo.exe not built")
    proc = subprocess.run(
        [str(bin_path), "build", str(SRC_MAIN), "--verify-determinism"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    assert proc.returncode == 0, f"build --verify-determinism failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    assert "Gen2:" in proc.stdout
    assert "Gen3:" in proc.stdout
    assert "SHA-256 MATCH - bootstrap chain is deterministic" in proc.stdout
    assert "[Velo Budget] bootstrap.c:" in proc.stdout


def test_emit_c_bootstrap_budget_report():
    """Verify that emit-c -o bootstrap.c reports the budget status."""
    bin_path = velo_exe()
    if not bin_path.exists():
        pytest.skip("bin/velo.exe not built")
    proc = subprocess.run(
        [str(bin_path), "emit-c", str(SRC_MAIN), "-o", "bootstrap.c"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    assert proc.returncode == 0, f"emit-c failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    assert "[Velo Budget] bootstrap.c:" in proc.stdout
