"""Tests for 6.2 Optimization Flags & Build Modes across Stage 1 and Stage 2."""
import os
import subprocess
import sys
import pytest

from velo.driver import CompilerDriver
from conftest import velo_exe

SIMPLE_PROGRAM = """use sys.io

act main() -> i32 {
    io.println("build mode test")
    return 0
}
"""

def _write(tmp_path, name, content):
    p = tmp_path / name
    with open(p, "w", newline="\n", encoding="utf-8") as fh:
        fh.write(content)
    return str(p).replace("\\", "/")

def _run_stage1(args):
    cmd = [sys.executable, "velo.py"] + args
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

def _run_native(args):
    cmd = [str(velo_exe())] + args
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


# ---------------- Stage 1 CompilerDriver Unit Tests ----------------

def test_driver_default_flags(tmp_path):
    src = _write(tmp_path, "prog.vl", SIMPLE_PROGRAM)
    driver = CompilerDriver()
    out = tmp_path / "prog_default.exe"
    exe = driver.build(src, str(out))
    assert os.path.exists(exe)
    assert "-O2" in driver.last_gcc_cmd
    assert "-g" not in driver.last_gcc_cmd
    assert "-flto" not in driver.last_gcc_cmd

    res = subprocess.run([exe], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert res.returncode == 0
    assert "build mode test" in res.stdout


def test_driver_debug_flags(tmp_path):
    src = _write(tmp_path, "prog.vl", SIMPLE_PROGRAM)
    driver = CompilerDriver()
    out = tmp_path / "prog_debug.exe"
    exe = driver.build(src, str(out), debug=True)
    assert os.path.exists(exe)
    assert "-O0" in driver.last_gcc_cmd
    assert "-g" in driver.last_gcc_cmd
    assert "-flto" not in driver.last_gcc_cmd

    res = subprocess.run([exe], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert res.returncode == 0
    assert "build mode test" in res.stdout


def test_driver_release_flags(tmp_path):
    src = _write(tmp_path, "prog.vl", SIMPLE_PROGRAM)
    driver = CompilerDriver()
    out = tmp_path / "prog_release.exe"
    exe = driver.build(src, str(out), release=True)
    assert os.path.exists(exe)
    assert "-O3" in driver.last_gcc_cmd
    assert "-flto" in driver.last_gcc_cmd
    assert "-g" not in driver.last_gcc_cmd

    res = subprocess.run([exe], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert res.returncode == 0
    assert "build mode test" in res.stdout


def test_driver_custom_opt_level(tmp_path):
    src = _write(tmp_path, "prog.vl", SIMPLE_PROGRAM)
    driver = CompilerDriver()
    out = tmp_path / "prog_opt1.exe"
    exe = driver.build(src, str(out), opt_level="1")
    assert os.path.exists(exe)
    assert "-O1" in driver.last_gcc_cmd
    assert "-g" not in driver.last_gcc_cmd
    assert "-flto" not in driver.last_gcc_cmd


def test_driver_conflict_raises(tmp_path):
    src = _write(tmp_path, "prog.vl", SIMPLE_PROGRAM)
    driver = CompilerDriver()
    with pytest.raises(ValueError, match="Cannot specify both --debug and --release"):
        driver.build(src, debug=True, release=True)


# ---------------- Stage 1 CLI Tests ----------------

def test_stage1_cli_build_and_run_debug(tmp_path):
    src = _write(tmp_path, "prog.vl", SIMPLE_PROGRAM)
    out = tmp_path / "stage1_dbg.exe"
    res_build = _run_stage1(["build", src, "--debug", "-o", str(out)])
    assert res_build.returncode == 0
    assert os.path.exists(out)

    res_run = subprocess.run([str(out)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert res_run.returncode == 0
    assert "build mode test" in res_run.stdout

    res_cli_run = _run_stage1(["run", src, "--debug"])
    assert res_cli_run.returncode == 0
    assert "build mode test" in res_cli_run.stdout


def test_stage1_cli_build_and_run_release(tmp_path):
    src = _write(tmp_path, "prog.vl", SIMPLE_PROGRAM)
    out = tmp_path / "stage1_rel.exe"
    res_build = _run_stage1(["build", src, "--release", "-o", str(out)])
    assert res_build.returncode == 0
    assert os.path.exists(out)

    res_run = subprocess.run([str(out)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert res_run.returncode == 0
    assert "build mode test" in res_run.stdout

    res_cli_run = _run_stage1(["run", src, "--release"])
    assert res_cli_run.returncode == 0
    assert "build mode test" in res_cli_run.stdout


def test_stage1_cli_conflict(tmp_path):
    src = _write(tmp_path, "prog.vl", SIMPLE_PROGRAM)
    res_b = _run_stage1(["build", src, "--debug", "--release"])
    assert res_b.returncode == 1
    assert "[Velo Error] Cannot specify both --debug and --release" in res_b.stderr

    res_r = _run_stage1(["run", src, "--debug", "--release"])
    assert res_r.returncode == 1
    assert "[Velo Error] Cannot specify both --debug and --release" in res_r.stderr


# ---------------- Stage 2 Native CLI Tests ----------------

def test_native_cli_build_and_run_debug(tmp_path):
    if not os.path.exists(str(velo_exe())):
        pytest.skip("bin/velo.exe not built; skipping native test")
    src = _write(tmp_path, "prog.vl", SIMPLE_PROGRAM)
    out = tmp_path / "native_dbg.exe"
    res_build = _run_native(["build", src, "--debug", "-o", str(out)])
    assert res_build.returncode == 0
    assert os.path.exists(out)

    res_run = subprocess.run([str(out)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert res_run.returncode == 0
    assert "build mode test" in res_run.stdout

    res_cli_run = _run_native(["run", src, "--debug"])
    assert res_cli_run.returncode == 0
    assert "build mode test" in res_cli_run.stdout


def test_native_cli_build_and_run_release(tmp_path):
    if not os.path.exists(str(velo_exe())):
        pytest.skip("bin/velo.exe not built; skipping native test")
    src = _write(tmp_path, "prog.vl", SIMPLE_PROGRAM)
    out = tmp_path / "native_rel.exe"
    res_build = _run_native(["build", src, "--release", "-o", str(out)])
    assert res_build.returncode == 0
    assert os.path.exists(out)

    res_run = subprocess.run([str(out)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert res_run.returncode == 0
    assert "build mode test" in res_run.stdout

    res_cli_run = _run_native(["run", src, "--release"])
    assert res_cli_run.returncode == 0
    assert "build mode test" in res_cli_run.stdout


def test_native_cli_conflict(tmp_path):
    if not os.path.exists(str(velo_exe())):
        pytest.skip("bin/velo.exe not built; skipping native test")
    src = _write(tmp_path, "prog.vl", SIMPLE_PROGRAM)
    res_b = _run_native(["build", src, "--debug", "--release"])
    assert res_b.returncode == 1
    out_b = res_b.stdout + res_b.stderr
    assert "[Velo Error] Cannot specify both --debug and --release" in out_b

    res_r = _run_native(["run", src, "--debug", "--release"])
    assert res_r.returncode == 1
    out_r = res_r.stdout + res_r.stderr
    assert "[Velo Error] Cannot specify both --debug and --release" in out_r


def test_native_cli_size_comparison(tmp_path):
    if not os.path.exists(str(velo_exe())):
        pytest.skip("bin/velo.exe not built; skipping native test")
    src = _write(tmp_path, "prog.vl", SIMPLE_PROGRAM)
    out_dbg = tmp_path / "dbg.exe"
    out_rel = tmp_path / "rel.exe"

    res_d = _run_native(["build", src, "--debug", "-o", str(out_dbg)])
    res_r = _run_native(["build", src, "--release", "-o", str(out_rel)])
    assert res_d.returncode == 0 and res_r.returncode == 0

    s_dbg = os.path.getsize(out_dbg)
    s_rel = os.path.getsize(out_rel)
    # Debug binary contains debug symbols and unoptimized code; release has LTO and -O3
    assert s_dbg > s_rel
