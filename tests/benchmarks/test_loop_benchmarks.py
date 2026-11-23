"""
tests/benchmarks/test_loop_benchmarks.py — Loop Performance Cliff Microbenchmarks (Task 81.5)

Promoted from tests/test_loop_performance.py into the nightly benchmark tier.
Tests loop execution speed across 20M iterations to detect performance cliffs.
"""

import os
import sys
import shutil
import tempfile
import subprocess
from pathlib import Path

import pytest
from tests.conftest import velo_exe, cc_dir, is_windows

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VELO_EXE = velo_exe()
N = 20_000_000

pytestmark = [
    pytest.mark.bench,
    pytest.mark.skipif(not VELO_EXE.exists(), reason="bin/velo.exe not built"),
]

def get_build_env():
    env = dict(os.environ)
    ucrt_bin = cc_dir()
    if os.path.exists(ucrt_bin) and ucrt_bin not in env.get("PATH", ""):
        env["PATH"] = ucrt_bin + ";" + env.get("PATH", "")
    return env

def build_temp(source: str, name: str):
    """Build source in a temp dir and return (exe_path, tmpdir)."""
    tmp = tempfile.mkdtemp()
    src = Path(tmp) / f"{name}.vl"
    exe = Path(tmp) / (f"{name}.exe" if is_windows() else name)
    src.write_text(source, encoding="utf-8", newline="\n")
    res = subprocess.run(
        [str(VELO_EXE), "build", str(src), "-o", str(exe)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
        env=get_build_env(),
    )
    assert res.returncode == 0, f"build failed:\n{res.stdout}\n{res.stderr}"
    return exe, tmp

def time_binary(exe: Path, runs: int = 5) -> float:
    """Best-of-runs wall time in seconds; best-of rejects scheduler noise."""
    import time
    best = None
    for _ in range(runs):
        start = time.perf_counter()
        res = subprocess.run([str(exe)], capture_output=True, timeout=120)
        elapsed = time.perf_counter() - start
        assert res.returncode == 0, f"benchmark binary failed: {res.stderr!r}"
        if best is None or elapsed < best:
            best = elapsed
    return best

ACCUMULATE_BODY = (
    "    mut acc: i64 = 0\n"
    f"    let n: i32 = {N}\n"
)

def test_inclusive_loop_has_no_performance_cliff():
    """An inclusive loop must not be dramatically slower than an exclusive one."""
    exclusive, dir_a = build_temp(
        "use std.io\n"
        "act main() -> i32 {\n" + ACCUMULATE_BODY +
        "    loop i in 0..n { acc += i as i64 }\n"
        "    io.println_i64(acc)\n"
        "    return 0\n"
        "}\n",
        "bench_exclusive",
    )
    inclusive, dir_b = build_temp(
        "use std.io\n"
        "act main() -> i32 {\n" + ACCUMULATE_BODY +
        "    loop i in 0..=n { acc += i as i64 }\n"
        "    io.println_i64(acc)\n"
        "    return 0\n"
        "}\n",
        "bench_inclusive",
    )
    try:
        t_excl = time_binary(exclusive)
        t_incl = time_binary(inclusive)
    finally:
        shutil.rmtree(dir_a, ignore_errors=True)
        shutil.rmtree(dir_b, ignore_errors=True)

    ratio = t_incl / t_excl if t_excl else float("inf")
    assert ratio < 2.0, (
        f"inclusive loop is {ratio:.2f}x the exclusive loop "
        f"(exclusive {t_excl*1000:.0f} ms, inclusive {t_incl*1000:.0f} ms) at {N} iterations"
    )

def test_stepped_inclusive_loop_has_no_performance_cliff():
    """The step-aware terminator must not degrade stepped loops either."""
    plain, dir_a = build_temp(
        "use std.io\n"
        "act main() -> i32 {\n" + ACCUMULATE_BODY +
        "    loop i in 0..n:4 { acc += i as i64 }\n"
        "    io.println_i64(acc)\n"
        "    return 0\n"
        "}\n",
        "bench_stepless",
    )
    inclusive, dir_b = build_temp(
        "use std.io\n"
        "act main() -> i32 {\n" + ACCUMULATE_BODY +
        "    loop i in 0..=n:4 { acc += i as i64 }\n"
        "    io.println_i64(acc)\n"
        "    return 0\n"
        "}\n",
        "bench_stepped",
    )
    try:
        t_plain = time_binary(plain)
        t_incl = time_binary(inclusive)
    finally:
        shutil.rmtree(dir_a, ignore_errors=True)
        shutil.rmtree(dir_b, ignore_errors=True)

    ratio = t_incl / t_plain if t_plain else float("inf")
    assert ratio < 2.0, (
        f"stepped inclusive loop is {ratio:.2f}x the stepped exclusive loop "
        f"(plain {t_plain*1000:.0f} ms, inclusive {t_incl*1000:.0f} ms)"
    )
