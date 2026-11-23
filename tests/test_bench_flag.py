"""
tests/test_bench_flag.py — Automated verification of benchmark tier & --bench flag (Task 81.5)
Tests:
  1. Microbenchmarks in tests/benchmarks/ are skipped by default in PR test runs.
  2. Microbenchmarks in tests/benchmarks/ execute when --bench is explicitly supplied.
  3. Loop performance cliff tests in tests/test_loop_performance.py are gated behind --bench.
"""

import sys
import subprocess
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_benchmarks_skipped_without_flag():
    """Running pytest on tests/benchmarks/ without --bench must skip all benchmarks."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/benchmarks/test_workload_benchmarks.py",
        "-v",
        "-rs"
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0
    assert "skipped" in res.stdout.lower()
    assert "Benchmark tier: run with pytest --bench" in res.stdout

def test_loop_performance_cliff_skipped_without_flag():
    """Loop performance tests in test_loop_performance.py must be skipped without --bench."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_loop_performance.py",
        "-k", "cliff",
        "-v",
        "-rs"
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0
    assert "skipped" in res.stdout.lower()
    assert "Benchmark tier: run with pytest --bench" in res.stdout

def test_benchmarks_run_with_flag():
    """Running pytest with --bench must execute the benchmark tier."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/benchmarks/test_workload_benchmarks.py",
        "--bench",
        "-v"
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0
    assert "PASSED" in res.stdout
    assert "test_filescan_throughput_cliff PASSED" in res.stdout
    assert "test_json_parsing_throughput_cliff PASSED" in res.stdout
