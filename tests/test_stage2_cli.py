import os
import subprocess
from pathlib import Path
import pytest

from release_meta import expected_banner_line
from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()

@pytest.fixture(scope="session", autouse=True)
def ensure_velo_exe():
    """Ensure bin/velo.exe exists before running CLI tests."""
    if not VELO_EXE.exists():
        # Build it using the bootstrap python driver
        res = subprocess.run(
            ["python", "velo.py", "build", "src/main.vl", "-o", str(VELO_EXE)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True, encoding="utf-8", errors="replace"
        )
        assert res.returncode == 0, f"Failed to bootstrap bin/velo.exe:\n{res.stderr}"
    assert VELO_EXE.exists(), "bin/velo.exe must exist"

def run_velo(args):
    """Helper to run bin/velo.exe with MSYS2 GCC in PATH."""
    env = os.environ.copy()
    if cc_dir() not in env.get("PATH", ""):
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return subprocess.run(
        [str(VELO_EXE)] + args,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=env
    )

def test_cli_version():
    res = run_velo(["version"])
    assert res.returncode == 0
    assert expected_banner_line() in res.stdout

def test_cli_help():
    res = run_velo(["help"])
    assert res.returncode == 0
    assert "Usage:" in res.stdout
    assert "velo run <source.vl>" in res.stdout
    assert "velo build <source.vl>" in res.stdout
    assert "velo emit-c <source.vl>" in res.stdout

def test_cli_no_args():
    res = run_velo([])
    assert res.returncode == 0
    assert "Usage:" in res.stdout

def test_cli_emit_c():
    source_file = REPO_ROOT / "examples" / "01_hello.vl"
    res = run_velo(["emit-c", str(source_file)])
    assert res.returncode == 0
    assert '#include "velo_runtime.h"' in res.stdout
    assert "int main(int argc, char** argv)" in res.stdout
    assert "Hello, world!!" in res.stdout

def test_cli_run_hello():
    source_file = REPO_ROOT / "examples" / "01_hello.vl"
    res = run_velo(["run", str(source_file)])
    assert res.returncode == 0
    assert "Hello, world!!" in res.stdout

def test_cli_run_math():
    source_file = REPO_ROOT / "examples" / "02_math_and_logic.vl"
    res = run_velo(["run", str(source_file)])
    assert res.returncode == 0
    assert "While step: 0" in res.stdout
    assert "While step: 2" in res.stdout
    assert "Loop start at 0" in res.stdout
    assert "Loop middle step: 1" in res.stdout
    assert "Loop end at 4" in res.stdout
    assert "Fibonacci(7) = 13" in res.stdout
    assert "Milestone 2 Complete!" in res.stdout

def test_cli_string_interpolation_and_formatting():
    particles_file = REPO_ROOT / "examples" / "05_particles.vl"
    res = run_velo(["run", str(particles_file)])
    assert res.returncode == 0
    assert "Arena memory for particles: 120 bytes" in res.stdout
    assert "--- Frame 0 ---" in res.stdout
    assert "Particle[0]: pos=(0.00, 0.16), life=0.03" in res.stdout
    assert "Arena memory after simulation exit: 0 bytes" in res.stdout

def test_cli_build_and_run():
    source_file = REPO_ROOT / "examples" / "01_hello.vl"
    out_exe = REPO_ROOT / "bin" / "test_cli_hello.exe"
    if out_exe.exists():
        out_exe.unlink()

    res = run_velo(["build", str(source_file), "-o", str(out_exe)])
    assert res.returncode == 0
    assert "[Velo] Successfully built binary!" in res.stdout
    assert out_exe.exists()

    env = os.environ.copy()
    if cc_dir() not in env.get("PATH", ""):
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    run_res = subprocess.run([str(out_exe)], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    assert run_res.returncode == 0
    assert "Hello, world!!" in run_res.stdout

def test_cli_error_unknown_command():
    res = run_velo(["invalid_cmd"])
    assert res.returncode != 0
    assert "Unknown command" in res.stdout
