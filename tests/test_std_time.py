import os
import re
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

def test_std_time_clock():
    test_vl = REPO_ROOT / "std" / "tests" / "time" / "clock_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.time.clock all tests passed" in res.stdout

def test_std_time_duration():
    test_vl = REPO_ROOT / "std" / "tests" / "time" / "duration_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.time.duration all tests passed" in res.stdout

def test_std_time_sleep():
    test_vl = REPO_ROOT / "std" / "tests" / "time" / "sleep_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.time.sleep all tests passed" in res.stdout

def test_std_time_calendar():
    test_vl = REPO_ROOT / "std" / "tests" / "time" / "calendar_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.time.calendar all tests passed" in res.stdout

def test_std_time_module_import():
    test_vl = REPO_ROOT / "std" / "tests" / "time_module_import_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: use std.time umbrella module verified" in res.stdout

def test_std_time_tz():
    test_vl = REPO_ROOT / "std" / "tests" / "time" / "tz_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.time.tz all tests passed" in res.stdout

def test_tz_variants_expose_the_same_public_api():
    pattern = re.compile(r"^(?:view\s+)?act (\w+)\(", re.MULTILINE)
    variants = ["windows", "linux", "macos"]
    exported = {}
    for var in variants:
        p = REPO_ROOT / "std" / "time" / f"tz_{var}.vl"
        assert p.exists(), f"Missing variant file: {p}"
        acts = set(pattern.findall(p.read_text(encoding="utf-8")))
        exported[var] = acts

    baseline = exported["windows"]
    for var in ["linux", "macos"]:
        diff_missing = baseline - exported[var]
        diff_extra = exported[var] - baseline
        assert not diff_missing, f"Variant '{var}' missing acts present in windows: {diff_missing}"
        assert not diff_extra, f"Variant '{var}' has extra acts not in windows: {diff_extra}"

def test_std_time_umbrella_import(tmp_path):
    src = tmp_path / "test_umbrella.vl"
    src.write_text("""
use std.io
use std.time

act main() -> i32 {
    let u = tz_utc()
    if u.offset != 0 { return 1 }
    let sys = tz_sys()
    let now = time_now_local()
    if now.year < 2026 { return 2 }
    let tokyo = tz_make("JST", 32400)
    let tokyo_dt = time_to_local(@now, @tokyo)
    if tokyo_dt.year < 2026 { return 3 }
    io.println("PASS_UMBRELLA")
    return 0
}
""", encoding="utf-8")
    res = subprocess.run(
        [str(VELO_EXE), "run", str(src)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS_UMBRELLA" in res.stdout
