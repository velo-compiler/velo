import os
import subprocess
import pytest
from pathlib import Path
from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()

def get_env():
    env = os.environ.copy()
    if cc_dir() not in env.get("PATH", ""):
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return env

def test_std_rand_core():
    test_vl = REPO_ROOT / "std" / "tests" / "rand" / "rand_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "OK: std.rand all tests passed" in res.stdout

def test_std_rand_module_import():
    test_vl = REPO_ROOT / "std" / "tests" / "rand_module_import_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.rand umbrella import all tests passed" in res.stdout

def test_std_rand_full_range_boundaries():
    test_code = """use std.rand
use std.io

act main() -> i32 {
    mut r = rng_seed(42 as u64)
    // u64 full range
    let u = rand_range_u64(@r, 0 as u64, 0xFFFFFFFFFFFFFFFF as u64)
    if u == (0 as u64) {
        let u2 = rand_range_u64(@r, 0 as u64, 0xFFFFFFFFFFFFFFFF as u64)
        if u2 == (0 as u64) { return 1 }
    }
    // i32 full range
    let i32_val = rand_range_i32(@r, -2147483648, 2147483647)
    // i64 full range
    let i64_val = rand_range_i64(@r, -9223372036854775807 - 1, 9223372036854775807)
    io.println_str("OK: boundaries passed")
    return 0
}
"""
    cache_dir = REPO_ROOT / ".velo_cache"
    cache_dir.mkdir(exist_ok=True)
    src_file = cache_dir / "test_rand_boundaries.vl"
    src_file.write_text(test_code, encoding="utf-8")
    try:
        res = subprocess.run(
            [str(VELO_EXE), "run", str(src_file)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=get_env()
        )
        assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
        assert "OK: boundaries passed" in res.stdout
    finally:
        if src_file.exists():
            src_file.unlink()

def test_std_rand_pcg64_statistical_quality():
    test_code = """use std.rand
use std.io

act main() -> i32 {
    mut r = rng_seed(42 as u64)
    mut sum_f: f64 = 0.0
    mut low_count: usize = 0
    let n: usize = 10000
    mut i: usize = 0
    loop i < n {
        let f = rand_f64(@r)
        sum_f = sum_f + f
        if f < 0.001 {
            low_count += 1
        }
        i += 1
    }
    let mean: f64 = sum_f / (n as f64)
    if mean < 0.485 or mean > 0.515 { return 1 }
    if low_count > 50 { return 2 }
    io.println_str("OK: statistical quality passed")
    return 0
}
"""
    cache_dir = REPO_ROOT / ".velo_cache"
    cache_dir.mkdir(exist_ok=True)
    src_file = cache_dir / "test_rand_stats.vl"
    src_file.write_text(test_code, encoding="utf-8")
    try:
        res = subprocess.run(
            [str(VELO_EXE), "run", str(src_file)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=get_env()
        )
        assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
        assert "OK: statistical quality passed" in res.stdout
    finally:
        if src_file.exists():
            src_file.unlink()



