"""
tests/test_benchmark_results.py — Automated verification of benchmark generation
Tests:
  1. Verifies that benchmark/RESULTS.md exists, is generated, and contains
     machine/version headers and all 3 workloads across peer languages (Task 81.1).
  2. Verifies that benchmark/run_benchmark.py runs in quick mode and regenerates
     valid Markdown output with toolchain and system metadata.
"""

import os
import sys
import subprocess
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS_MD = os.path.join(REPO_ROOT, "benchmark", "RESULTS.md")
RUN_BENCHMARK_PY = os.path.join(REPO_ROOT, "benchmark", "run_benchmark.py")

def test_results_md_exists_and_valid():
    """benchmark/RESULTS.md must exist and contain the required multi-language sections."""
    assert os.path.exists(RESULTS_MD), f"Expected {RESULTS_MD} to exist"
    
    with open(RESULTS_MD, "r", encoding="utf-8") as f:
        content = f.read()

    # Title & Metadata
    assert "# 🏁 Velo Multi-Language Benchmark Report" in content
    assert "Automated Benchmark Output" in content
    assert "## 🖥️ Environment & Toolchain Specifications" in content
    assert "Host OS" in content
    assert "CPU Architecture" in content
    assert "Total System RAM" in content

    # Toolchain parity
    assert "Velo" in content
    assert "C (GCC)" in content
    assert "Rust" in content
    assert "Go" in content
    assert "Node.js" in content

    # Workload 1: HTTP
    assert "HTTP Server Workload" in content
    assert "Plaintext Endpoint (`/plaintext`)" in content
    assert "JSON REST Endpoint (`/json`)" in content

    # Workload 2: JSON Parsing
    assert "JSON Parsing & Aggregation Workload" in content
    assert "Execution Time (ms)" in content
    assert "Throughput (iter/s)" in content

    # Workload 3: File Scanning
    assert "Large File Scanning & Word Count Workload" in content
    assert "Scanning Speed (MB/s)" in content

    # Summary
    assert "Key Architectural Takeaways" in content

def test_run_benchmark_cli_help():
    """benchmark/run_benchmark.py must provide --help with CLI options."""
    res = subprocess.run([sys.executable, RUN_BENCHMARK_PY, "--help"], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0
    assert "--quick" in res.stdout
    assert "--skip-build" in res.stdout
    assert "--skip-http" in res.stdout
    assert "--output" in res.stdout

def test_run_benchmark_generator_quick(tmp_path):
    """Verifies that run_benchmark.py can regenerate markdown dynamically."""
    temp_output = str(tmp_path / "TEST_RESULTS.md")
    cmd = [
        sys.executable,
        RUN_BENCHMARK_PY,
        "--quick",
        "--skip-http",
        "--skip-build",
        "--output",
        temp_output
    ]
    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert res.returncode == 0, f"Benchmark runner failed: {res.stderr}\n{res.stdout}"
    assert os.path.exists(temp_output), "Expected test results output to be generated"

    with open(temp_output, "r", encoding="utf-8") as f:
        data = f.read()

    assert "# 🏁 Velo Multi-Language Benchmark Report" in data
    assert "Environment & Toolchain Specifications" in data
    assert "JSON Parsing & Aggregation Workload" in data
    assert "Large File Scanning & Word Count Workload" in data
