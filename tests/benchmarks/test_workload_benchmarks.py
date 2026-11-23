"""
tests/benchmarks/test_workload_benchmarks.py — Systems Workload Performance Tier (Task 81.5)

Executes file scanning and JSON processing microbenchmarks to ensure throughput
meets minimum acceptable velocity thresholds without regression cliffs.
"""

import time
import subprocess
from pathlib import Path

import pytest
from tests.conftest import velo_exe, is_windows

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BENCHMARK_DIR = REPO_ROOT / "benchmark"
BOOTSTRAP_C = REPO_ROOT / "bootstrap.c"
EXT = ".exe" if is_windows() else ""

pytestmark = [
    pytest.mark.bench,
]

def test_filescan_throughput_cliff():
    """Velo file scanning must process bootstrap.c at >= 30 MB/s."""
    exe = BENCHMARK_DIR / f"filescan_velo{EXT}"
    if not exe.exists() or not BOOTSTRAP_C.exists():
        pytest.skip("filescan_velo binary or bootstrap.c not found")

    file_size_mb = BOOTSTRAP_C.stat().st_size / (1024.0 * 1024.0)

    # Best of 3 runs
    times = []
    for _ in range(3):
        t0 = time.perf_counter()
        res = subprocess.run(
            [str(exe), str(BOOTSTRAP_C)],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        elapsed = time.perf_counter() - t0
        assert res.returncode == 0
        assert "lines=76931" in res.stdout
        times.append(elapsed)

    best_time = min(times)
    throughput_mb_s = file_size_mb / best_time
    assert throughput_mb_s >= 30.0, f"File scanning throughput cliff: {throughput_mb_s:.1f} MB/s < 30 MB/s"

def test_json_parsing_throughput_cliff():
    """Velo JSON parsing must process structured records at >= 1,000 iter/s."""
    exe = BENCHMARK_DIR / f"json_velo{EXT}"
    if not exe.exists():
        pytest.skip("json_velo binary not found")

    iters = 2000
    t0 = time.perf_counter()
    res = subprocess.run(
        [str(exe), str(iters)],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    elapsed = time.perf_counter() - t0
    assert res.returncode == 0
    assert "Done 2000 iterations" in res.stdout

    iter_per_sec = iters / elapsed
    assert iter_per_sec >= 1000.0, f"JSON parsing throughput cliff: {iter_per_sec:.1f} iter/s < 1,000 iter/s"
