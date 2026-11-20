"""Phase 73.1: Tests asserting MD5 is not reachable from the std.crypto umbrella,
and is strictly isolated in std.crypto.legacy for backward compatibility and interoperability only.

Security Invariant I73.4:
MD5 and future legacy primitives are not reachable from the default std.crypto umbrella;
they live in std.crypto.legacy.
"""
import subprocess
from pathlib import Path
import pytest
from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()


def get_env():
    import os
    env = os.environ.copy()
    if cc_dir() not in env.get("PATH", ""):
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return env


def _require_native():
    if not VELO_EXE.exists():
        pytest.skip("bin/velo not built")


def run_velo(args):
    return subprocess.run(
        [str(VELO_EXE)] + args,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
        timeout=60,
    )


def test_md5_hash_str_not_reachable_from_crypto_umbrella(tmp_path):
    """Calling md5_hash_str with only 'use std.crypto' fails at compile time."""
    _require_native()
    src = tmp_path / "umbrella_no_md5.vl"
    src.write_text("""use std.crypto
use std.io

act main() {
    let m = md5_hash_str("test")
    io.println(m)
}
""", encoding="utf-8")
    res = run_velo(["check", str(src)])
    assert res.returncode != 0
    assert "undefined" in res.stdout.lower() or "undefined" in res.stderr.lower() or "error" in res.stdout.lower()


def test_md5_init_not_reachable_from_crypto_umbrella(tmp_path):
    """Accessing Md5State or md5_init with only 'use std.crypto' fails at compile time."""
    _require_native()
    src = tmp_path / "umbrella_no_md5_init.vl"
    src.write_text("""use std.crypto

act main() {
    mut s: Md5State
    md5_init(@s)
}
""", encoding="utf-8")
    res = run_velo(["check", str(src)])
    assert res.returncode != 0


def test_md5_reachable_with_explicit_legacy_import(tmp_path):
    """Explicitly importing 'use std.crypto.legacy' enables MD5 for interoperability."""
    _require_native()
    src = tmp_path / "legacy_md5.vl"
    src.write_text("""use std.crypto.legacy
use std.io

act main() {
    let m = md5_hash_str("velo")
    io.println("md5={m}")
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode == 0, f"Failed: {res.stderr}"
    assert "md5=939c04836f9dda50950db42092831eec" in res.stdout


def test_crypto_and_legacy_can_be_imported_together(tmp_path):
    """A program importing both std.crypto and std.crypto.legacy compiles and runs."""
    _require_native()
    src = tmp_path / "both_imports.vl"
    src.write_text("""use std.crypto
use std.crypto.legacy
use std.io

act main() {
    let s = sha256_hash_str("velo")
    let m = md5_hash_str("velo")
    io.println("sha={s}")
    io.println("md5={m}")
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode == 0, f"Failed: {res.stderr}"
    assert "sha=cd1e45e8b94d27b2562ab5ae45b4bff61e2bc89d9ca4ffe117e70aa5ac8ef1eb" in res.stdout
    assert "md5=939c04836f9dda50950db42092831eec" in res.stdout


def test_crypto_umbrella_source_excludes_md5():
    """Static audit: std/crypto.vl must NOT import md5.vl."""
    crypto_vl = REPO_ROOT / "std" / "crypto.vl"
    assert crypto_vl.exists(), "std/crypto.vl must exist"
    content = crypto_vl.read_text(encoding="utf-8")
    assert "md5" not in content, "std/crypto.vl must not import or mention md5"
    assert "sha256" in content
    assert "hmac" in content
    assert "rand" in content
    assert "crc32" in content


def test_legacy_vl_has_interoperability_warning_doc_comment():
    """Static audit: std/crypto/legacy.vl must carry warning that it is for interoperability only."""
    legacy_vl = REPO_ROOT / "std" / "crypto" / "legacy.vl"
    assert legacy_vl.exists(), "std/crypto/legacy.vl must exist"
    content = legacy_vl.read_text(encoding="utf-8")
    assert "interoperability" in content.lower()
    assert "broken" in content.lower() or "deprecated" in content.lower()
    assert 'use "md5.vl"' in content
