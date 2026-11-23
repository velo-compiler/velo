"""
tests/test_fuzz_transpiler.py

Tests for the AFL / libFuzzer C-transpiler target and corpus.
Phase 82 / Task 82.3 (Invariant I82.3)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import cc_dir, cc_env, cc_path, require_velo_exe, velo_exe

REPO_ROOT = Path(__file__).resolve().parent.parent
FUZZ_DIR = REPO_ROOT / "tests" / "fuzz"
FUZZ_TARGET_C = FUZZ_DIR / "fuzz_transpiler.c"
CORPUS_DIR = FUZZ_DIR / "corpus" / "transpiler"
BOOTSTRAP_C = REPO_ROOT / "bootstrap.c"


def get_fuzz_env() -> dict[str, str]:
    """Return environment with C compiler directory prepended to PATH."""
    env = cc_env()
    d = cc_dir()
    if d:
        env["PATH"] = f"{d}{os.pathsep}{env.get('PATH', '')}"
    return env

CRASH_EXIT_CODES = {
    -1073741819,  # 0xC0000005: STATUS_ACCESS_VIOLATION
    -1073741571,  # 0xC00000FD: STATUS_STACK_OVERFLOW
    -1073741676,  # 0xC0000094: STATUS_INTEGER_DIVIDE_BY_ZERO
    -1073740940,  # 0xC0000374: STATUS_HEAP_CORRUPTION
    -1073741795,  # 0xC000001D: STATUS_ILLEGAL_INSTRUCTION
    -2147483645,  # 0x80000003: STATUS_BREAKPOINT
    3221225477,   # 0xC0000005 unsigned
    3221225725,   # 0xC00000FD unsigned
    3221225620,   # 0xC0000094 unsigned
    3221226356,   # 0xC0000374 unsigned
    139,          # Linux SIGSEGV
    134,          # Linux SIGABRT
    136,          # Linux SIGFPE
}


def test_fuzz_target_source_structural():
    """Verify fuzz_transpiler.c structural integrity and exported interface."""
    assert FUZZ_TARGET_C.exists(), f"Missing {FUZZ_TARGET_C}"
    content = FUZZ_TARGET_C.read_text(encoding="utf-8")
    assert "LLVMFuzzerTestOneInput" in content
    assert "LLVMFuzzerInitialize" in content
    assert "compile_source_to_c_all_opts" in content
    assert "velo_zone_push" in content
    assert "velo_zone_pop" in content
    assert "diag_collector_clear" in content


def test_fuzz_corpus_inventory():
    """Verify the committed fuzz corpus contains valid and malformed seeds."""
    assert CORPUS_DIR.exists(), f"Corpus directory {CORPUS_DIR} does not exist"
    corpus_files = list(CORPUS_DIR.glob("*.vl"))
    assert len(corpus_files) >= 10, f"Expected >= 10 corpus seeds, found {len(corpus_files)}"

    valid_files = [f for f in corpus_files if "valid" in f.name]
    malformed_files = [f for f in corpus_files if "malformed" in f.name]
    assert len(valid_files) >= 5, "Expected at least 5 valid seed files"
    assert len(malformed_files) >= 5, "Expected at least 5 malformed seed files"


@pytest.fixture(scope="module")
def built_fuzz_target(tmp_path_factory) -> Path:
    """Build the standalone fuzz_transpiler executable once for testing."""
    build_dir = tmp_path_factory.mktemp("fuzz_build")
    out_exe = build_dir / ("fuzz_transpiler.exe" if sys.platform == "win32" else "fuzz_transpiler")
    obj_bootstrap = build_dir / "bootstrap_lib.o"

    cc = cc_path()
    env = get_fuzz_env()

    # Step 1: compile bootstrap.c into object with main renamed
    res_obj = subprocess.run(
        [
            cc,
            "-O1",
            "-c",
            "-Dmain=velo_compiler_main",
            "-I",
            str(REPO_ROOT / "runtime"),
            "-I",
            str(REPO_ROOT / "velo" / "runtime"),
            str(BOOTSTRAP_C),
            "-o",
            str(obj_bootstrap),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert res_obj.returncode == 0, f"Failed to compile bootstrap_lib.o:\n{res_obj.stderr}"
    assert obj_bootstrap.exists()

    # Step 2: compile and link fuzz_transpiler.c
    res_link = subprocess.run(
        [
            cc,
            "-O2",
            "-I",
            str(REPO_ROOT / "runtime"),
            str(FUZZ_TARGET_C),
            str(obj_bootstrap),
            "-o",
            str(out_exe),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert res_link.returncode == 0, f"Failed to link fuzz_transpiler:\n{res_link.stderr}"
    assert out_exe.exists()
    return out_exe


def test_fuzz_transpiler_corpus_execution(built_fuzz_target: Path):
    """Run each seed in tests/fuzz/corpus/transpiler through fuzz_transpiler."""
    env = get_fuzz_env()
    corpus_files = sorted(CORPUS_DIR.glob("*.vl"))
    assert corpus_files, "No corpus files found"

    for file_path in corpus_files:
        res = subprocess.run(
            [str(built_fuzz_target), "--silent", str(file_path)],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        assert res.returncode not in CRASH_EXIT_CODES, (
            f"Fuzz target crashed on {file_path.name} with exit code {res.returncode}!"
        )
        assert res.returncode == 0, (
            f"Fuzz target returned {res.returncode} on {file_path.name}:\n{res.stderr}\n{res.stdout}"
        )


def test_fuzz_transpiler_mutation_budget(built_fuzz_target: Path):
    """Run the standalone mutation fuzzer for a 2-second budget to ensure crash-freedom."""
    env = get_fuzz_env()
    seed = CORPUS_DIR / "01_valid_hello.vl"
    res = subprocess.run(
        [str(built_fuzz_target), "--silent", "--budget", "2", str(seed)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
    )
    assert res.returncode not in CRASH_EXIT_CODES
    assert res.returncode == 0, f"Mutation fuzzer failed:\n{res.stderr}\n{res.stdout}"


@pytest.mark.parametrize("corpus_file", sorted(CORPUS_DIR.glob("*.vl")), ids=lambda f: f.name)
def test_corpus_files_through_velo_compiler(corpus_file: Path):
    """Assert that velo emit-c never crashes on any committed fuzz corpus input."""
    velo = require_velo_exe()
    res = subprocess.run(
        [str(velo), "emit-c", str(corpus_file)],
        cwd=str(REPO_ROOT),
        env=get_fuzz_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    assert res.returncode not in CRASH_EXIT_CODES, (
        f"velo emit-c crashed on corpus file {corpus_file.name} with code {res.returncode}!"
    )
    assert res.returncode in (0, 1), (
        f"Unexpected exit code {res.returncode} on {corpus_file.name}:\n{res.stderr}\n{res.stdout}"
    )
