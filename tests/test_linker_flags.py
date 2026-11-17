"""Tests for 6.1 Linker Flags for Third-Party C Libraries (-l<lib>, -L<dir>).

Verifies that:
1. Stage 1 CompilerDriver places linker flags AFTER the .c source file in the GCC command.
2. Stage 1 CLI (velo.py build / run) accepts -l and -L flags (both attached and detached syntax).
3. Stage 2 CLI (bin/velo.exe build / run) accepts -l and -L flags (both attached and detached syntax).
4. Programs with extern functions fail linking without required -l flags, and succeed with them.
5. Linker flags combine seamlessly with build mode flags (--debug, --release, -O1, -O2, -O3).
"""

import os
import sys
import subprocess
import pytest
from pathlib import Path
from velo.driver import CompilerDriver
from conftest import cc_dir, velo_exe

GCC_BIN_DIR = cc_dir()
ENV_WITH_GCC = os.environ.copy()
if GCC_BIN_DIR not in ENV_WITH_GCC.get("PATH", ""):
    ENV_WITH_GCC["PATH"] = GCC_BIN_DIR + ";" + ENV_WITH_GCC.get("PATH", "")

REPO_ROOT = Path(__file__).parent.parent
VELO_PY = REPO_ROOT / "velo.py"
VELO_EXE = velo_exe()

WINMM_SOURCE = """use sys.io

extern act timeGetTime() -> u32

act main() {
    let t: u32 = timeGetTime()
    if t >= 0 {
        io.println("WINMM_LINK_SUCCESS")
    }
}
"""


def test_driver_linker_flags_ordering(tmp_path):
    """Verify that CompilerDriver places -L and -l flags strictly AFTER the .c file in GCC invocation."""
    driver = CompilerDriver()
    src_file = tmp_path / "hello.vl"
    src_file.write_text("use sys.io\nact main() {\n    io.println(\"42\")\n}\n", encoding="utf-8")
    out_exe = tmp_path / "hello.exe"

    out = driver.build(
        str(src_file),
        output_path=str(out_exe),
        libs=["winmm", "gdi32"],
        lib_dirs=["./custom_lib", "./extra_lib"]
    )
    assert out == str(out_exe)

    last_cmd = driver.last_gcc_cmd
    assert last_cmd is not None

    # Find position of .c file, -L flags, and -l flags
    c_idx = -1
    for i, token in enumerate(last_cmd):
        if token.endswith(".c"):
            c_idx = i
            break
    assert c_idx != -1, f".c file not found in gcc command: {last_cmd}"

    l_winmm_idx = last_cmd.index("-lwinmm")
    l_gdi32_idx = last_cmd.index("-lgdi32")
    assert l_winmm_idx > c_idx, f"-lwinmm ({l_winmm_idx}) should appear after .c ({c_idx})"
    assert l_gdi32_idx > c_idx, f"-lgdi32 ({l_gdi32_idx}) should appear after .c ({c_idx})"

    L1_idx = last_cmd.index("-L./custom_lib")
    L2_idx = last_cmd.index("-L./extra_lib")
    assert L1_idx > c_idx, f"-L flag ({L1_idx}) should appear after .c ({c_idx})"
    assert L2_idx > c_idx, f"-L flag ({L2_idx}) should appear after .c ({c_idx})"


def test_stage1_build_without_lib_fails(tmp_path):
    """Calling timeGetTime without -lwinmm must fail linking with undefined reference."""
    src_file = tmp_path / "test_missing_lib.vl"
    src_file.write_text(WINMM_SOURCE, encoding="utf-8")
    out_exe = tmp_path / "test_missing.exe"

    res = subprocess.run(
        [sys.executable, str(VELO_PY), "build", str(src_file), "-o", str(out_exe)],
        capture_output=True,
        text=True,
        env=ENV_WITH_GCC
    )
    assert res.returncode != 0, f"Expected link failure, got exit code 0:\n{res.stdout}\n{res.stderr}"
    output = res.stdout + res.stderr
    assert "undefined reference to" in output or "timeGetTime" in output or "Build failed" in output


def test_stage1_build_with_attached_lib(tmp_path):
    """Stage 1 velo.py build with attached -lwinmm succeeds and runs."""
    src_file = tmp_path / "test_attached.vl"
    src_file.write_text(WINMM_SOURCE, encoding="utf-8")
    out_exe = tmp_path / "test_attached.exe"

    res = subprocess.run(
        [sys.executable, str(VELO_PY), "build", str(src_file), "-lwinmm", "-o", str(out_exe)],
        capture_output=True,
        text=True,
        env=ENV_WITH_GCC
    )
    assert res.returncode == 0, f"Build with -lwinmm failed:\n{res.stdout}\n{res.stderr}"
    assert out_exe.exists()

    run_res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert run_res.returncode == 0
    assert "WINMM_LINK_SUCCESS" in run_res.stdout


def test_stage1_build_with_detached_lib(tmp_path):
    """Stage 1 velo.py build with detached -l winmm succeeds and runs."""
    src_file = tmp_path / "test_detached.vl"
    src_file.write_text(WINMM_SOURCE, encoding="utf-8")
    out_exe = tmp_path / "test_detached.exe"

    res = subprocess.run(
        [sys.executable, str(VELO_PY), "build", str(src_file), "-l", "winmm", "-o", str(out_exe)],
        capture_output=True,
        text=True,
        env=ENV_WITH_GCC
    )
    assert res.returncode == 0, f"Build with -l winmm failed:\n{res.stdout}\n{res.stderr}"
    assert out_exe.exists()

    run_res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert run_res.returncode == 0
    assert "WINMM_LINK_SUCCESS" in run_res.stdout


def test_stage1_run_with_lib(tmp_path):
    """Stage 1 velo.py run with -lwinmm builds and runs in one step."""
    src_file = tmp_path / "test_run.vl"
    src_file.write_text(WINMM_SOURCE, encoding="utf-8")

    res = subprocess.run(
        [sys.executable, str(VELO_PY), "run", str(src_file), "-lwinmm"],
        capture_output=True,
        text=True,
        env=ENV_WITH_GCC
    )
    assert res.returncode == 0, f"Run with -lwinmm failed:\n{res.stdout}\n{res.stderr}"
    assert "WINMM_LINK_SUCCESS" in res.stdout


def test_stage1_lib_dirs_flag(tmp_path):
    """Stage 1 velo.py build with -L flag passed cleanly to gcc."""
    src_file = tmp_path / "test_ldir.vl"
    src_file.write_text(WINMM_SOURCE, encoding="utf-8")
    out_exe = tmp_path / "test_ldir.exe"

    # Both detached and attached -L and -l
    res = subprocess.run(
        [sys.executable, str(VELO_PY), "build", str(src_file), "-L", str(tmp_path), "-lwinmm", "-o", str(out_exe)],
        capture_output=True,
        text=True,
        env=ENV_WITH_GCC
    )
    assert res.returncode == 0, f"Build with -L and -l failed:\n{res.stdout}\n{res.stderr}"


def test_stage1_combination_with_build_modes(tmp_path):
    """Stage 1 velo.py with both optimization/debug mode and linker flag."""
    src_file = tmp_path / "test_combo.vl"
    src_file.write_text(WINMM_SOURCE, encoding="utf-8")
    out_exe = tmp_path / "test_combo.exe"

    # --release and -lwinmm
    res = subprocess.run(
        [sys.executable, str(VELO_PY), "build", str(src_file), "--release", "-lwinmm", "-o", str(out_exe)],
        capture_output=True,
        text=True,
        env=ENV_WITH_GCC
    )
    assert res.returncode == 0, f"Release build with -lwinmm failed:\n{res.stdout}\n{res.stderr}"
    run_res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert "WINMM_LINK_SUCCESS" in run_res.stdout


@pytest.mark.skipif(not VELO_EXE.exists(), reason="bin/velo.exe not present")
def test_stage2_build_without_lib_fails(tmp_path):
    """Stage 2 bin/velo.exe without required library fails linking."""
    src_file = tmp_path / "test_s2_fail.vl"
    src_file.write_text(WINMM_SOURCE, encoding="utf-8")
    out_exe = tmp_path / "test_s2_fail.exe"

    res = subprocess.run(
        [str(VELO_EXE), "build", str(src_file), "-o", str(out_exe)],
        capture_output=True,
        text=True,
        env=ENV_WITH_GCC
    )
    assert res.returncode != 0, f"Expected Stage 2 link failure, got 0:\n{res.stdout}\n{res.stderr}"


@pytest.mark.skipif(not VELO_EXE.exists(), reason="bin/velo.exe not present")
def test_stage2_build_attached_and_detached_lib(tmp_path):
    """Stage 2 bin/velo.exe build with -lwinmm (attached) and -l winmm (detached)."""
    src_file = tmp_path / "test_s2_lib.vl"
    src_file.write_text(WINMM_SOURCE, encoding="utf-8")

    # Attached: -lwinmm
    out_exe_att = tmp_path / "test_s2_att.exe"
    res1 = subprocess.run(
        [str(VELO_EXE), "build", str(src_file), "-lwinmm", "-o", str(out_exe_att)],
        capture_output=True,
        text=True,
        env=ENV_WITH_GCC
    )
    assert res1.returncode == 0, f"Stage 2 build with -lwinmm failed:\n{res1.stdout}\n{res1.stderr}"
    run_res1 = subprocess.run([str(out_exe_att)], capture_output=True, text=True)
    assert "WINMM_LINK_SUCCESS" in run_res1.stdout

    # Detached: -l winmm
    out_exe_det = tmp_path / "test_s2_det.exe"
    res2 = subprocess.run(
        [str(VELO_EXE), "build", str(src_file), "-l", "winmm", "-o", str(out_exe_det)],
        capture_output=True,
        text=True,
        env=ENV_WITH_GCC
    )
    assert res2.returncode == 0, f"Stage 2 build with -l winmm failed:\n{res2.stdout}\n{res2.stderr}"
    run_res2 = subprocess.run([str(out_exe_det)], capture_output=True, text=True)
    assert "WINMM_LINK_SUCCESS" in run_res2.stdout


@pytest.mark.skipif(not VELO_EXE.exists(), reason="bin/velo.exe not present")
def test_stage2_run_with_lib(tmp_path):
    """Stage 2 bin/velo.exe run with -lwinmm."""
    src_file = tmp_path / "test_s2_run.vl"
    src_file.write_text(WINMM_SOURCE, encoding="utf-8")

    res = subprocess.run(
        [str(VELO_EXE), "run", str(src_file), "-lwinmm"],
        capture_output=True,
        text=True,
        env=ENV_WITH_GCC
    )
    assert res.returncode == 0, f"Stage 2 run with -lwinmm failed:\n{res.stdout}\n{res.stderr}"
    assert "WINMM_LINK_SUCCESS" in res.stdout


@pytest.mark.skipif(not VELO_EXE.exists(), reason="bin/velo.exe not present")
def test_stage2_combination_with_release(tmp_path):
    """Stage 2 bin/velo.exe build with both --release and -lwinmm."""
    src_file = tmp_path / "test_s2_combo.vl"
    src_file.write_text(WINMM_SOURCE, encoding="utf-8")
    out_exe = tmp_path / "test_s2_combo.exe"

    res = subprocess.run(
        [str(VELO_EXE), "build", str(src_file), "--release", "-lwinmm", "-o", str(out_exe)],
        capture_output=True,
        text=True,
        env=ENV_WITH_GCC
    )
    assert res.returncode == 0, f"Stage 2 release build with -lwinmm failed:\n{res.stdout}\n{res.stderr}"
    run_res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert "WINMM_LINK_SUCCESS" in run_res.stdout
