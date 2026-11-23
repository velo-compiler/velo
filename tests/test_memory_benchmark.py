"""
tests/test_memory_benchmark.py — Regression verification for peak RSS profiler and memory claims (Task 81.4)
Tests:
  1. CLI help output and arguments of benchmark/memory.py.
  2. Core measure_peak_rss_mb function execution on current platform.
  3. Validation of generated benchmark/MEMORY_RESULTS.md.
  4. Assertion that README.md has replaced the unverified '< 64KB' claim with measured figures.
  5. JSON output export verification.
"""

import os
import sys
import json
import subprocess
import pytest
from pathlib import Path
from benchmark.memory import measure_peak_rss_mb

REPO_ROOT = Path(__file__).resolve().parent.parent
MEMORY_PY = REPO_ROOT / "benchmark" / "memory.py"
MEMORY_MD = REPO_ROOT / "benchmark" / "MEMORY_RESULTS.md"
README_MD = REPO_ROOT / "README.md"

def test_memory_py_cli_help():
    """memory.py must support --help and document all key parameters."""
    res = subprocess.run(
        [sys.executable, str(MEMORY_PY), "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    assert res.returncode == 0
    assert "--quick" in res.stdout
    assert "--skip-compiler" in res.stdout
    assert "--output" in res.stdout
    assert "--json-output" in res.stdout

def test_measure_peak_rss_mb_execution():
    """measure_peak_rss_mb must measure process peak memory and capture output cleanly."""
    cmd = [sys.executable, "-c", "import time; x = [0] * 500000; print('MEM_OK')"]
    peak_mb, code, stdout = measure_peak_rss_mb(cmd)
    assert code == 0
    assert "MEM_OK" in stdout
    assert peak_mb > 0.0

def test_memory_results_md_valid():
    """benchmark/MEMORY_RESULTS.md must exist and contain empirical multi-workload tables."""
    assert MEMORY_MD.exists(), f"Expected {MEMORY_MD} to exist"
    content = MEMORY_MD.read_text(encoding="utf-8")

    assert "# 🧠 Velo Memory Footprint & Peak RSS Audit" in content
    assert "Minimal CLI Baseline (Hello World)" in content
    assert "Real-World Systems Workloads (Peak RSS)" in content
    assert "File Scan" in content
    assert "JSON Parsing & Aggregation" in content
    assert "Async HTTP Server" in content
    assert "Self-Hosted Compiler Analysis Footprint" in content
    assert "Empirical Findings & Claims Correction" in content
    assert "Velo 2.0" in content

def test_readme_64kb_claim_replaced():
    """README.md must not contain the unverified '< 64KB' claim, but measured numbers."""
    content = README_MD.read_text(encoding="utf-8")
    assert "< 64KB" not in content, "README.md still contains unverified '< 64KB' claim"
    assert "< 64 KB" not in content, "README.md still contains unverified '< 64 KB' claim"
    assert "Lean Memory Footprint" in content
    assert "~4 MB" in content or "4 MB" in content

def test_memory_suite_json_export(tmp_path):
    """memory.py must export structured JSON memory metrics."""
    json_path = tmp_path / "memory_audit.json"
    temp_md = tmp_path / "temp_memory.md"
    cmd = [
        sys.executable,
        str(MEMORY_PY),
        "--quick",
        "--skip-compiler",
        "--output", str(temp_md),
        "--json-output", str(json_path)
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Memory runner failed:\n{res.stderr}\n{res.stdout}"
    assert json_path.exists()

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "minimal_cli" in data
    assert "filescan" in data
    assert "json_parsing" in data
    assert "http_server" in data
