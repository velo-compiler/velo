import os
import subprocess
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = REPO_ROOT / "bin" / "velo.exe"

def get_env():
    env = os.environ.copy()
    if r"C:\msys64\ucrt64\bin" not in env.get("PATH", ""):
        env["PATH"] = r"C:\msys64\ucrt64\bin;" + env.get("PATH", "")
    return env

def test_std_mem_page_alloc():
    test_vl = REPO_ROOT / "std" / "tests" / "mem" / "page_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.mem.page all assertions succeeded" in res.stdout

def test_std_mem_ops():
    test_vl = REPO_ROOT / "std" / "tests" / "mem" / "ops_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.mem.ops all assertions succeeded" in res.stdout

def test_platform_suffix_resolution():
    # Verify that emit-c on page_test.vl resolves page.vl to page_windows.vl on Windows
    test_vl = REPO_ROOT / "std" / "tests" / "mem" / "page_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "emit-c", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"emit-c failed:\n{res.stderr}"
    assert "VirtualAlloc" in res.stdout, "Expected VirtualAlloc from page_windows.vl to be included"
    assert "mmap" not in res.stdout, "mmap from page_linux.vl must not be included on Windows"

def test_std_mem_arena():
    test_vl = REPO_ROOT / "std" / "tests" / "mem" / "arena_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.mem.arena all assertions succeeded" in res.stdout

def test_std_mem_slab():
    test_vl = REPO_ROOT / "std" / "tests" / "mem" / "slab_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.mem.slab all assertions succeeded" in res.stdout





