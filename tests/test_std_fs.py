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

def test_std_fs_stat():
    test_vl = REPO_ROOT / "std" / "tests" / "fs" / "stat_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.fs.stat all assertions succeeded" in res.stdout


def test_std_fs_ops():
    test_vl = REPO_ROOT / "std" / "tests" / "fs" / "ops_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.fs.ops all assertions succeeded" in res.stdout

def test_std_fs_dir():
    test_vl = REPO_ROOT / "std" / "tests" / "fs" / "dir_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.fs.dir all assertions succeeded" in res.stdout

def test_std_path_fs_module_imports():
    test_vl = REPO_ROOT / "std" / "tests" / "path_fs_module_import_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: use std.path and use std.fs native imports verified" in res.stdout


FS_OPS_TEST = REPO_ROOT / "std" / "tests" / "fs" / "ops_test.vl"


def run_fs_ops_in(sandbox):
    """Run the fs ops Velo test with `sandbox` as the working directory.

    `ops_test.vl` uses paths relative to the process cwd, so the sandbox IS the
    filesystem state the test sees. Running in a fresh temp directory means the
    test can never touch the developer's real `scratch/`: there is no ambient
    state to touch, and anything the test creates lands inside `sandbox`.
    """
    return subprocess.run(
        [str(VELO_EXE), "run", str(FS_OPS_TEST)],
        cwd=str(sandbox),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=get_env(),
        timeout=300,
    )


def test_std_fs_ops_needs_no_ambient_scratch(tmp_path):
    """Task 67.1/67.2: the test must create its own working directory.

    `std/tests/fs/ops_test.vl` writes under `scratch/...` but calls
    `fs_create_dir_str` for the leaves only. That maps to a plain
    `CreateDirectoryA` (std/fs/ops.vl:22-30), which does not create parents, so
    the suite fails unless `scratch/` already exists.

    It passed in this repository purely because an **untracked, empty**
    `scratch/` directory happened to be present in the working tree — a clean
    clone and a CI runner have no such directory, so the test was green on the
    developer's machine and red everywhere else.

    This runs in an empty temp cwd where no ambient `scratch/` can exist, which
    is the condition a clean checkout reproduces without risking the real one.
    """
    assert not (tmp_path / "scratch").exists(), "sandbox must start empty"
    res = run_fs_ops_in(tmp_path)
    blob = res.stdout + res.stderr
    assert res.returncode == 0, (
        "std.fs.ops needs an ambient scratch/ directory; run from a clean cwd:\n" + blob
    )
    assert "PASS: std.fs.ops all assertions succeeded" in res.stdout, blob


def test_std_fs_ops_cleans_up_after_itself(tmp_path):
    """Task 67.2: cleanup must remove the working directory it created.

    A test that leaves `scratch/` behind is what let the defect above hide in
    the first place: the first run creates the state that every later run
    depends on. The suite must be idempotent from nothing and leave nothing.
    """
    assert not (tmp_path / "scratch").exists(), "sandbox must start empty"
    run_fs_ops_in(tmp_path)
    leftover = sorted(p.name for p in tmp_path.iterdir() if p.name != ".velo_cache")
    assert not leftover, (
        "std.fs.ops left files behind in its working directory: "
        f"{leftover} (only .velo_cache, the compiler's own scratch, is allowed)"
    )


def test_std_fs_ops_does_not_touch_the_repository_scratch():
    """Guard the Task 67.1 security gate: the harness must not run in the repo.

    The sandboxed rows above are only trustworthy if they cannot reach the
    developer's real `scratch/`. This asserts the property that makes that
    true: the helper always executes with an explicit cwd that is not the
    repository root.
    """
    import inspect

    source = inspect.getsource(run_fs_ops_in)
    assert "cwd=str(sandbox)" in source, (
        "run_fs_ops_in must pin cwd to the sandbox, never inherit the repo root"
    )
    assert "cwd=str(REPO_ROOT)" not in source

