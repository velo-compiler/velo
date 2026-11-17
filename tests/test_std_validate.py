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

def test_std_validate_core():
    test_vl = REPO_ROOT / "std" / "tests" / "validate" / "validate_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "std.validate tests: ALL PASSED" in res.stdout

def test_std_validate_module_import():
    test_vl = REPO_ROOT / "std" / "tests" / "validate_module_import_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.validate umbrella import all tests passed" in res.stdout

def test_std_validate_fqdn_domain():
    test_code = """use std.validate
use std.io

act main() -> i32 {
    if not validate_domain("example.com.") { return 1 }
    if not validate_domain("sub.example.co.uk.") { return 2 }
    if validate_domain("example.") { return 3 }
    if validate_domain("example.c.") { return 4 }
    io.println_str("OK: fqdn domain validation passed")
    return 0
}
"""
    cache_dir = REPO_ROOT / ".velo_cache"
    cache_dir.mkdir(exist_ok=True)
    src_file = cache_dir / "test_validate_fqdn.vl"
    src_file.write_text(test_code, encoding="utf-8")
    try:
        res = subprocess.run(
            [str(VELO_EXE), "run", str(src_file)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            env=get_env()
        )
        assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
        assert "OK: fqdn domain validation passed" in res.stdout
    finally:
        if src_file.exists():
            src_file.unlink()

