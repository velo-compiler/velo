"""
Tests for binary-relative stdlib resolution (Phase 70 / Task 70.9).

`resolve_std_module_path` in `src/backend/driver.vl` must resolve standard library
modules relative to the running compiler binary (`velo_host_exe_path()`) when
invoked from directories unrelated to the repository or stdlib location, and
when standard environment variables (VELO_STD, VELO_HOME, USERPROFILE, HOME)
do not point to stdlib.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from conftest import cc_dir, require_velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()


def _isolated_env(tmp_dir: Path) -> dict:
    env = os.environ.copy()
    directory = cc_dir()
    if directory and directory not in env.get("PATH", ""):
        env["PATH"] = directory + os.pathsep + env.get("PATH", "")
    env.pop("VELO_STD", None)
    env.pop("VELO_HOME", None)
    # Mask user profiles so fallback does not pick up ~/.velo
    env["USERPROFILE"] = str(tmp_dir)
    env["HOME"] = str(tmp_dir)
    return env


def test_emit_c_resolves_std_fs_from_unrelated_directory(tmp_path):
    velo_exe = require_velo_exe()
    src = tmp_path / "app.vl"
    src.write_text(
        'use std.fs\n\nact main() -> i32 {\n    let exists = fs_exists("test.txt")\n    return 0\n}\n',
        encoding="utf-8",
    )
    out_c = tmp_path / "app.c"

    res = subprocess.run(
        [str(velo_exe), "emit-c", str(src), "-o", str(out_c)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_isolated_env(tmp_path),
        timeout=30,
    )
    assert res.returncode == 0, f"emit-c failed:\nstdout:\n{res.stdout}\nstderr:\n{res.stderr}"
    assert out_c.exists(), "Expected app.c to be generated"
    content = out_c.read_text(encoding="utf-8")
    assert "fs_exists" in content


def test_emit_c_resolves_multiple_std_modules_from_unrelated_directory(tmp_path):
    velo_exe = require_velo_exe()
    src = tmp_path / "multi.vl"
    src.write_text(
        'use std.fs\nuse std.io\nuse std.crypto\n\nact main() -> i32 {\n    return 0\n}\n',
        encoding="utf-8",
    )
    out_c = tmp_path / "multi.c"

    res = subprocess.run(
        [str(velo_exe), "emit-c", str(src), "-o", str(out_c)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_isolated_env(tmp_path),
        timeout=30,
    )
    assert res.returncode == 0, f"emit-c failed:\nstdout:\n{res.stdout}\nstderr:\n{res.stderr}"
    assert out_c.exists(), "Expected multi.c to be generated"


def test_build_and_run_from_unrelated_directory(tmp_path):
    velo_exe = require_velo_exe()
    src = tmp_path / "run_app.vl"
    src.write_text(
        'use std.fs\n\nact main() -> i32 {\n    let exists = fs_exists("nonexistent_file_xyz.txt")\n    if exists { return 1 }\n    return 0\n}\n',
        encoding="utf-8",
    )
    out_bin = tmp_path / ("run_app.exe" if os.name == "nt" else "run_app")

    res = subprocess.run(
        [str(velo_exe), "build", str(src), "-o", str(out_bin)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_isolated_env(tmp_path),
        timeout=60,
    )
    assert res.returncode == 0, f"build failed:\nstdout:\n{res.stdout}\nstderr:\n{res.stderr}"
    assert out_bin.exists(), "Expected binary to be built"

    run_res = subprocess.run(
        [str(out_bin)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert run_res.returncode == 0, f"Execution failed with return code {run_res.returncode}"
