"""
Unit and integration test suite for Phase 50 / Task 50.1:
Package supply chain integrity, cryptographic lockfile (velo.lock) verification,
tampering rejection, and repository SECURITY.md policy.
"""

import os
import sys
import subprocess
from pathlib import Path
import pytest

from release_meta import read_version
from conftest import velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()
SECURITY_MD = REPO_ROOT / "SECURITY.md"
def test_security_policy_document_exists():
    """Verify that SECURITY.md exists at repository root and defines complete disclosure policies."""
    assert SECURITY_MD.exists(), "SECURITY.md must exist in repository root"
    content = SECURITY_MD.read_text(encoding="utf-8")

    # Required sections
    assert "# Security Policy" in content
    assert "## Supported Versions" in content
    assert "## Reporting a Vulnerability" in content
    assert "## Response & Triage SLAs" in content
    assert "## Coordinated Disclosure Policy" in content
    assert "## Security Architecture & Invariants" in content

    # Key security commitments
    assert f"Velo v{read_version().split('.')[0]}.x" in content
    assert "security@velolang.org" in content
    assert "48 hours" in content
    assert "14 calendar days" in content
    assert "30 calendar days" in content
    assert "90-day" in content
    assert "velo.lock" in content
    assert "SHA-256" in content

def test_pkg_lock_generation_and_checksum_verification(tmp_path):
    """Verify that 'velo pkg lock' creates velo.lock and 'velo pkg install' verifies checksums."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo not built")

    pkg_dir = tmp_path / "test_pkg_app"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    deps_dir = pkg_dir / "deps" / "math_lib"
    deps_dir.mkdir(parents=True, exist_ok=True)

    # 1. Create a local dependency package
    dep_main = deps_dir / "main.vl"
    dep_main.write_text(
        "act add_nums(a: i32, b: i32) -> i32 {\n"
        "    return a + b\n"
        "}\n",
        encoding="utf-8"
    )

    # 2. Create app entry and velo.pkg manifest
    app_main = pkg_dir / "main.vl"
    app_main.write_text(
        "use std.io\n"
        'act main() -> i32 {\n'
        '    println_str("Hello from packaged app!")\n'
        '    return 0\n'
        '}\n',
        encoding="utf-8"
    )

    velo_pkg = pkg_dir / "velo.pkg"
    velo_pkg.write_text(
        'pkg "test_pkg_app" {\n'
        '    name: "test_pkg_app"\n'
        '    version: "1.0.0"\n'
        '    entry: "main.vl"\n'
        '}\n'
        'deps {\n'
        '    math_lib: local "deps/math_lib"\n'
        '}\n',
        encoding="utf-8"
    )

    # 3. Generate velo.lock with 'velo pkg lock'
    res_lock = subprocess.run([str(VELO_EXE), "pkg", "lock", str(pkg_dir)], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res_lock.returncode == 0, f"velo pkg lock failed:\n{res_lock.stderr}\n{res_lock.stdout}"
    assert "Successfully generated velo.lock" in res_lock.stdout

    lock_file = pkg_dir / "velo.lock"
    assert lock_file.exists(), "velo.lock was not created"
    lock_content = lock_file.read_text(encoding="utf-8")
    assert 'package "math_lib"' in lock_content
    assert 'hash = "sha256:' in lock_content

    # 4. Verify that 'velo pkg install' verifies without modification
    res_install = subprocess.run([str(VELO_EXE), "pkg", "install", str(pkg_dir)], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res_install.returncode == 0, f"velo pkg install failed:\n{res_install.stderr}\n{res_install.stdout}"
    assert "verified against velo.lock" in res_install.stdout

    # 5. Verify that 'velo pkg check' passes with valid lockfile
    res_check = subprocess.run([str(VELO_EXE), "pkg", "check", str(pkg_dir)], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res_check.returncode == 0, f"velo pkg check failed:\n{res_check.stderr}\n{res_check.stdout}"
    assert "Verified velo.lock checksums" in res_check.stdout

def test_pkg_detects_tampered_dependency_contents(tmp_path):
    """Verify that tampering with dependency contents causes checksum verification failure."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo not built")

    pkg_dir = tmp_path / "tamper_test_app"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    deps_dir = pkg_dir / "deps" / "crypto_helper"
    deps_dir.mkdir(parents=True, exist_ok=True)

    dep_main = deps_dir / "main.vl"
    dep_main.write_text(
        "act get_secret() -> i32 {\n"
        "    return 42\n"
        "}\n",
        encoding="utf-8"
    )

    app_main = pkg_dir / "main.vl"
    app_main.write_text(
        "act main() -> i32 { return 0 }\n",
        encoding="utf-8"
    )

    velo_pkg = pkg_dir / "velo.pkg"
    velo_pkg.write_text(
        'pkg "tamper_app" {\n'
        '    name: "tamper_app"\n'
        '    version: "1.0.0"\n'
        '    entry: "main.vl"\n'
        '}\n'
        'deps {\n'
        '    crypto_helper: local "deps/crypto_helper"\n'
        '}\n',
        encoding="utf-8"
    )

    # 1. Generate lockfile
    res_lock = subprocess.run([str(VELO_EXE), "pkg", "lock", str(pkg_dir)], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res_lock.returncode == 0

    # 2. Tamper with the dependency file
    dep_main.write_text(
        "act get_secret() -> i32 {\n"
        "    return 9999  // Tampered by unauthorized attacker\n"
        "}\n",
        encoding="utf-8"
    )

    # 3. 'velo pkg install' must reject tampered dependency
    res_install_tampered = subprocess.run([str(VELO_EXE), "pkg", "install", str(pkg_dir)], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res_install_tampered.returncode != 0
    assert "Package checksum verification failed for 'crypto_helper'" in res_install_tampered.stdout or "Package checksum verification failed for 'crypto_helper'" in res_install_tampered.stderr
    assert "Package contents may have been tampered with or modified" in res_install_tampered.stdout or "Package contents may have been tampered with or modified" in res_install_tampered.stderr

    # 4. 'velo pkg check' must also reject tampered dependency
    res_check_tampered = subprocess.run([str(VELO_EXE), "pkg", "check", str(pkg_dir)], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res_check_tampered.returncode != 0
    assert "Package checksum verification failed" in res_check_tampered.stdout or "Package checksum verification failed" in res_check_tampered.stderr

    # 5. 'velo pkg update' must update lockfile to accept new contents
    res_update = subprocess.run([str(VELO_EXE), "pkg", "update", str(pkg_dir)], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res_update.returncode == 0
    assert "Successfully updated velo.lock" in res_update.stdout

    # 6. Now install must succeed with updated lock
    res_reinstall = subprocess.run([str(VELO_EXE), "pkg", "install", str(pkg_dir)], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res_reinstall.returncode == 0
    assert "verified against velo.lock" in res_reinstall.stdout

def test_pkg_help_manual_documents_security_commands():
    """Verify that 'velo pkg help' and 'velo help' document lock, install, and update commands."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo not built")

    res_pkg_help = subprocess.run([str(VELO_EXE), "pkg", "help"], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res_pkg_help.returncode == 0
    assert "velo pkg lock" in res_pkg_help.stdout
    assert "velo pkg install" in res_pkg_help.stdout
    assert "velo pkg update" in res_pkg_help.stdout

    res_cli_help = subprocess.run([str(VELO_EXE), "help"], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res_cli_help.returncode == 0
    assert "velo pkg lock" in res_cli_help.stdout
    assert "velo pkg install" in res_cli_help.stdout
    assert "velo pkg update" in res_cli_help.stdout

