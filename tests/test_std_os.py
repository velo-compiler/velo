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

def test_std_os_env():
    test_vl = REPO_ROOT / "std" / "tests" / "os" / "env_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.os.env tests succeeded" in res.stdout

def test_std_os_args():
    test_vl = REPO_ROOT / "std" / "tests" / "os" / "args_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.os.args tests succeeded" in res.stdout

def test_std_os_args_cli(tmp_path):
    test_vl = REPO_ROOT / "std" / "tests" / "os" / "args_cli_test.vl"
    out_exe = tmp_path / "args_cli_test.exe"
    build_res = subprocess.run(
        [str(VELO_EXE), "build", str(test_vl), "-o", str(out_exe)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert build_res.returncode == 0, f"build failed with code {build_res.returncode}:\n{build_res.stderr}\n{build_res.stdout}"

    # Execute with distinct CLI arguments
    run_res = subprocess.run(
        [str(out_exe), "alpha", "beta with spaces", "--output", "bin/foo.exe", "-v"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert run_res.returncode == 0, f"run failed with code {run_res.returncode}:\n{run_res.stderr}\n{run_res.stdout}"
    lines = [line.strip() for line in run_res.stdout.splitlines() if line.strip()]
    assert len(lines) == 6
    assert lines[0].endswith("args_cli_test.exe")
    assert lines[1] == "alpha"
    assert lines[2] == "beta with spaces"
    assert lines[3] == "--output"
    assert lines[4] == "bin/foo.exe"
    assert lines[5] == "-v"


def test_std_os_process():
    test_vl = REPO_ROOT / "std" / "tests" / "os" / "process_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.os.process tests succeeded" in res.stdout
