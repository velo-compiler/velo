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

def test_std_url_encode():
    test_vl = REPO_ROOT / "std" / "tests" / "url" / "encode_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "OK: std.url encode tests passed" in res.stdout

def test_std_url_parse():
    test_vl = REPO_ROOT / "std" / "tests" / "url" / "parse_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "OK: std.url parse tests passed" in res.stdout

def test_std_url_query():
    test_vl = REPO_ROOT / "std" / "tests" / "url" / "query_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "OK: std.url query tests passed" in res.stdout

def test_std_url_format():
    test_vl = REPO_ROOT / "std" / "tests" / "url" / "format_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "OK: std.url format tests passed" in res.stdout

def test_std_url_module_import():
    test_vl = REPO_ROOT / "std" / "tests" / "url_module_import_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.url umbrella import all tests passed" in res.stdout

def test_std_url_query_del_expansion_safety():
    test_code = """use std.url
use std.io

act main() -> i32 {
    // 50 colons in value = 50 bytes in raw input, expands to 150 bytes (%3A) on re-encode
    let q = "del=1&val=::::::::::::::::::::::::::::::::::::::::::::::::::"
    let res = url_query_del(q, "del")
    let v = url_query_get(res, "val")
    if str.len(v) != 50 { return 1 }
    if url_query_has(res, "del") { return 2 }
    io.println_str("OK: expansion safety passed")
    return 0
}
"""
    cache_dir = REPO_ROOT / ".velo_cache"
    cache_dir.mkdir(exist_ok=True)
    src_file = cache_dir / "test_url_query_del_overflow.vl"
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
        assert "OK: expansion safety passed" in res.stdout
    finally:
        if src_file.exists():
            src_file.unlink()

