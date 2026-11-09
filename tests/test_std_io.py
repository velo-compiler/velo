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

def test_std_io_handle():
    test_vl = REPO_ROOT / "std" / "tests" / "io" / "handle_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.io.handle all assertions succeeded" in res.stdout

def test_std_io_buffered_writer():
    test_vl = REPO_ROOT / "std" / "tests" / "io" / "buffered_writer_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.io.buffered_writer all assertions succeeded" in res.stdout

def test_std_io_print():
    test_vl = REPO_ROOT / "std" / "tests" / "io" / "print_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.io.print all assertions succeeded" in res.stdout

def test_std_io_print_integration():
    test_vl = REPO_ROOT / "std" / "tests" / "io" / "print_integration_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "STD_IO_PRINT_OK" in res.stdout
    assert "123456" in res.stdout
    assert "3.14" in res.stdout
    assert "true" in res.stdout
    assert "STD_IO_EPRINT_OK" in res.stderr

def test_std_io_buffered_reader():
    test_vl = REPO_ROOT / "std" / "tests" / "io" / "buffered_reader_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.io.buffered_reader all assertions succeeded" in res.stdout

def test_std_io_print_exit_flush():
    test_vl = REPO_ROOT / "std" / "tests" / "io" / "print_exit_flush_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "UNFLUSHED_STDOUT_DATA" in res.stdout
    assert "UNFLUSHED_STDERR_DATA" in res.stderr


