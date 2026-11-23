"""
tests/test_compile_speed.py — Automated verification for compile speed monitoring & regression gate (Task 81.3)
Tests:
  1. CLI help output and arguments.
  2. Regression evaluation function across threshold boundaries.
  3. Regression gate passing when slowdown <= threshold.
  4. Regression gate failing (exit code 1) when slowdown > threshold.
  5. JSON history recording and serialization.
"""

import os
import sys
import json
import subprocess
import pytest
from pathlib import Path
from benchmark.compile_speed import evaluate_regression

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPILE_SPEED_PY = REPO_ROOT / "benchmark" / "compile_speed.py"

def test_compile_speed_help():
    """compile_speed.py must support --help and document all key parameters."""
    res = subprocess.run(
        [sys.executable, str(COMPILE_SPEED_PY), "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    assert res.returncode == 0
    assert "--check-regression" in res.stdout
    assert "--threshold" in res.stdout
    assert "--baseline-sec" in res.stdout
    assert "--history-file" in res.stdout

def test_evaluate_regression_logic():
    """evaluate_regression must correctly identify regressions relative to threshold."""
    # 1. Faster build (negative diff)
    regressed, pct, msg = evaluate_regression(current_clean_sec=15.0, baseline_sec=20.0, threshold_pct=20.0)
    assert not regressed
    assert pct == -25.0
    assert "[PASS]" in msg

    # 2. Mild slowdown within threshold (+10% <= 20%)
    regressed, pct, msg = evaluate_regression(current_clean_sec=22.0, baseline_sec=20.0, threshold_pct=20.0)
    assert not regressed
    assert abs(pct - 10.0) < 0.01
    assert "[PASS]" in msg

    # 3. Severe regression exceeding threshold (+30% > 20%)
    regressed, pct, msg = evaluate_regression(current_clean_sec=26.0, baseline_sec=20.0, threshold_pct=20.0)
    assert regressed
    assert abs(pct - 30.0) < 0.01
    assert "[REGRESSION FAILURE]" in msg

    # 4. No baseline available
    regressed, pct, msg = evaluate_regression(current_clean_sec=20.0, baseline_sec=0.0, threshold_pct=20.0)
    assert not regressed
    assert "No baseline timing available" in msg

def test_compile_speed_gate_passes_within_threshold():
    """Runner must exit 0 when slowdown is within the allowed threshold."""
    cmd = [
        sys.executable,
        str(COMPILE_SPEED_PY),
        "--mock-clean-sec", "22.0",
        "--baseline-sec", "20.0",
        "--threshold", "20.0",
        "--check-regression",
        "--no-record"
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0
    assert "[PASS]" in res.stdout
    assert "+10.0%" in res.stdout

def test_compile_speed_gate_fails_on_regression():
    """Runner must exit 1 when slowdown exceeds the threshold and --check-regression is passed."""
    cmd = [
        sys.executable,
        str(COMPILE_SPEED_PY),
        "--mock-clean-sec", "28.0",
        "--baseline-sec", "20.0",
        "--threshold", "20.0",
        "--check-regression",
        "--no-record"
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 1
    assert "[REGRESSION FAILURE]" in res.stdout
    assert "+40.0%" in res.stdout

def test_compile_speed_history_persistence(tmp_path):
    """Runner must record performance metrics and history to specified JSON file."""
    history_file = tmp_path / "custom_speed_history.json"
    cmd = [
        sys.executable,
        str(COMPILE_SPEED_PY),
        "--mock-clean-sec", "18.5",
        "--mock-incremental-sec", "0.4",
        "--history-file", str(history_file)
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0
    assert history_file.exists()

    with open(history_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "runs" in data
    assert len(data["runs"]) == 1
    entry = data["runs"][0]
    assert entry["clean_sec"] == 18.5
    assert entry["incremental_sec"] == 0.4
    assert entry["total_loc"] > 0
    assert entry["clean_loc_per_sec"] > 0
    assert "commit" in entry
    assert "timestamp" in entry
