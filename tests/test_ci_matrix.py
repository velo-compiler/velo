"""
Unit and integration tests for Task 49.1:
Multi-platform continuous integration matrix, POSIX bootstrap scripts,
and cross-platform determinism verification.
"""

import os
import sys
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"
BOOTSTRAP_SH = REPO_ROOT / "scripts" / "bootstrap.sh"
BOOTSTRAP_BAT = REPO_ROOT / "scripts" / "bootstrap.bat"
CHECK_DET = REPO_ROOT / "scripts" / "check_determinism.py"
VELO_EXE = REPO_ROOT / "bin" / ("velo.exe" if sys.platform == "win32" else "velo")

def test_ci_workflow_exists_and_configured():
    """Verify that .github/workflows/ci.yml exists and contains all required matrix configurations."""
    assert CI_YML.exists(), ".github/workflows/ci.yml must exist"
    content = CI_YML.read_text(encoding="utf-8")

    # Workflow triggers
    assert "push:" in content
    assert "pull_request:" in content

    # Matrix platforms
    assert "ubuntu-22.04" in content
    assert "ubuntu-24.04" in content
    assert "macos-14" in content
    assert "macos-15" in content
    assert "windows-2022" in content

    # Matrix compilers
    assert "gcc" in content
    assert "clang" in content
    assert "cl.exe" in content or "--cc cl" in content

    # Bootstrap & test steps
    assert "scripts/bootstrap.sh --full" in content or "scripts/bootstrap.sh" in content
    assert "scripts\\bootstrap.bat" in content
    assert "check_determinism.py" in content
    assert "pytest tests -q" in content

def test_bootstrap_sh_structure():
    """Verify that scripts/bootstrap.sh has the correct structure, permissions, and POSIX commands."""
    assert BOOTSTRAP_SH.exists(), "scripts/bootstrap.sh must exist"
    content = BOOTSTRAP_SH.read_text(encoding="utf-8")

    # POSIX shebang and flags
    assert content.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in content

    # Compiler probe and compilation flags
    assert "gcc" in content
    assert "clang" in content
    assert "-std=c99" in content
    assert "-O2" in content
    assert "-I runtime" in content
    assert "-lm" in content
    assert "-lpthread" in content

    # Self-hosting bootstrap steps
    assert "bin/velo build src/main.vl -o bin/velo_gen2" in content
    assert "bin/velo_gen2 build src/main.vl -o bin/velo_gen3" in content
    assert "check_determinism.py" in content
    assert "--quick" in content or "-q" in content
    assert "--full" in content

def test_bootstrap_bat_structure():
    """Verify that scripts/bootstrap.bat supports --full for 3-stage self-hosting verification."""
    assert BOOTSTRAP_BAT.exists(), "scripts/bootstrap.bat must exist"
    content = BOOTSTRAP_BAT.read_text(encoding="utf-8")

    assert "bootstrap.c" in content
    assert "--full" in content
    assert "bin\\velo.exe build src/main.vl -o bin\\velo_gen2.exe" in content
    assert "bin\\velo_gen2.exe build src/main.vl -o bin\\velo_gen3.exe" in content
    assert "check_determinism.py" in content

def test_check_determinism_script_runs():
    """Verify that scripts/check_determinism.py executes and confirms SHA-256 fixed-point determinism."""
    assert CHECK_DET.exists(), "scripts/check_determinism.py must exist"
    res = subprocess.run([sys.executable, str(CHECK_DET)], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0, f"check_determinism.py failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "SHA-256 MATCH" in res.stdout

def test_velo_accepts_clang_compiler_flag():
    """Verify that Velo CLI accepts --cc clang without rejecting it as an unknown backend."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo not built")
    
    # Check help text
    res_help = subprocess.run([str(VELO_EXE), "help"], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res_help.returncode == 0
    assert "--cc gcc|clang|cl" in res_help.stdout

    # Test invalid vs accepted cc backend diagnostic
    res_unknown = subprocess.run([str(VELO_EXE), "check", "examples/01_hello.vl", "--cc", "bad_compiler"], cwd=str(REPO_ROOT), capture_output=True, text=True)
    # When --cc is passed to check/build, bad_compiler error should mention clang
    res_build_bad = subprocess.run([str(VELO_EXE), "build", "examples/01_hello.vl", "--cc", "bad_compiler"], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert "Expected 'gcc', 'clang', or 'cl'" in res_build_bad.stdout or "Expected 'gcc', 'clang', or 'cl'" in res_build_bad.stderr

