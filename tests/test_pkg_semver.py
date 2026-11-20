"""
Tests for Phase 72 / Task 72.4:
Add semver: parse MAJOR.MINOR.PATCH, support '=', '^', '~', and '>=' in manifests,
reject ambiguous ranges with a diagnostic, and select highest matching version.
"""

import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path
import pytest

from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()


def get_base_env():
    env = os.environ.copy()
    if cc_dir() and cc_dir() not in env.get("PATH", ""):
        env["PATH"] = cc_dir() + os.pathsep + env.get("PATH", "")
    return env


def run_semver_probe(version_str: str, req_str: str) -> tuple[int, str]:
    """Runs a Velo probe calling semver_matches and semver_parse_req."""
    probe_code = f"""use std.io
use "../src/common/semver.vl"

act main() -> i32 {{
    let req = semver_parse_req("{req_str}")
    if !req.is_valid {{
        println_str("STATUS:INVALID_REQ")
        println_str("ERR:" + req.error_msg)
        return 2
    }}
    let matched = semver_matches("{version_str}", "{req_str}")
    if matched {{
        println_str("STATUS:MATCH")
        return 0
    }} else {{
        println_str("STATUS:NO_MATCH")
        return 1
    }}
}}
"""
    clean_name = f"probe_{version_str.replace('.', '_')}_{req_str.replace('^', 'caret_').replace('~', 'tilde_').replace('>=', 'gte_').replace('=', 'eq_').replace(' ', '_').replace('*', 'star_').replace('-', '_').replace('<', 'lt_').replace('>', 'gt_')}"
    probe_path = REPO_ROOT / "tests" / f"_tmp_{clean_name}.vl"
    probe_path.write_text(probe_code, encoding="utf-8")

    try:
        res = subprocess.run(
            [str(VELO_EXE), "run", str(probe_path)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=get_base_env(),
            timeout=60,
        )
        return res.returncode, res.stdout + res.stderr
    finally:
        if probe_path.exists():
            probe_path.unlink()


def run_registry_semver_resolve(dep_name: str, req_str: str, index_dict: dict, tmp_path: Path) -> tuple[int, str]:
    """Resolves a dependency requirement against a local mock index via file:// URL."""
    reg_root = tmp_path / "mock_reg"
    pkg_index_dir = reg_root / dep_name
    pkg_index_dir.mkdir(parents=True, exist_ok=True)
    (pkg_index_dir / "index.json").write_text(json.dumps(index_dict, indent=2), encoding="utf-8")

    reg_url = "file:///" + str(reg_root).replace("\\", "/")
    probe_code = f"""use std.io
use "../src/common/manifest.vl"

act main() -> i32 {{
    mut dep = DependencySpec{{
        name: "{dep_name}",
        kind: "registry",
        source: "{req_str}",
        tag: "",
        next: null
    }}
    let loc = manifest_resolve_dep_full("{str(tmp_path).replace(chr(92), '/')}", @dep, false, "{reg_url}")
    if loc.has_error {{
        println_str("STATUS:ERROR")
        println_str("ERR:" + loc.error_msg)
        return 1
    }}
    println_str("STATUS:OK")
    println_str("RESOLVED_VERSION:" + loc.version)
    println_str("ARCHIVE_URL:" + loc.archive_url)
    println_str("EXPECTED_HASH:" + loc.expected_hash)
    return 0
}}
"""
    probe_path = REPO_ROOT / "tests" / f"_tmp_reg_semver_{dep_name}.vl"
    probe_path.write_text(probe_code, encoding="utf-8")

    try:
        res = subprocess.run(
            [str(VELO_EXE), "run", str(probe_path)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=get_base_env(),
            timeout=60,
        )
        return res.returncode, res.stdout + res.stderr
    finally:
        if probe_path.exists():
            probe_path.unlink()


# -----------------------------------------------------------------------------
# Unit Tests for Operators: '=', '^', '~', '>='
# -----------------------------------------------------------------------------

def test_semver_exact_operator():
    """Verify '=' exact version operator."""
    code, out = run_semver_probe("1.2.3", "= 1.2.3")
    assert code == 0 and "STATUS:MATCH" in out

    code, out = run_semver_probe("1.2.3", "=1.2.3")
    assert code == 0 and "STATUS:MATCH" in out

    code, out = run_semver_probe("1.2.3", "1.2.3")
    assert code == 0 and "STATUS:MATCH" in out

    code, out = run_semver_probe("1.2.4", "= 1.2.3")
    assert code == 1 and "STATUS:NO_MATCH" in out

    code, out = run_semver_probe("2.0.0", "= 1.2.3")
    assert code == 1 and "STATUS:NO_MATCH" in out


def test_semver_caret_operator():
    """Verify '^' caret operator matching rules across major, minor, and patch levels."""
    # Standard major >= 1: allows minor and patch bumps, disallows major bump
    code, out = run_semver_probe("1.2.3", "^1.2.3")
    assert code == 0 and "STATUS:MATCH" in out

    code, out = run_semver_probe("1.2.4", "^1.2.3")
    assert code == 0 and "STATUS:MATCH" in out

    code, out = run_semver_probe("1.5.0", "^1.2.3")
    assert code == 0 and "STATUS:MATCH" in out

    code, out = run_semver_probe("2.0.0", "^1.2.3")
    assert code == 1 and "STATUS:NO_MATCH" in out

    code, out = run_semver_probe("1.2.2", "^1.2.3")
    assert code == 1 and "STATUS:NO_MATCH" in out

    # 0.minor level: allows patch bumps, disallows minor bump
    code, out = run_semver_probe("0.2.3", "^0.2.3")
    assert code == 0 and "STATUS:MATCH" in out

    code, out = run_semver_probe("0.2.9", "^0.2.3")
    assert code == 0 and "STATUS:MATCH" in out

    code, out = run_semver_probe("0.3.0", "^0.2.3")
    assert code == 1 and "STATUS:NO_MATCH" in out

    # 0.0.patch level: exact match only
    code, out = run_semver_probe("0.0.4", "^0.0.4")
    assert code == 0 and "STATUS:MATCH" in out

    code, out = run_semver_probe("0.0.5", "^0.0.4")
    assert code == 1 and "STATUS:NO_MATCH" in out


def test_semver_tilde_operator():
    """Verify '~' tilde operator matching rules (allows patch bumps, disallows minor bumps)."""
    code, out = run_semver_probe("1.2.3", "~1.2.3")
    assert code == 0 and "STATUS:MATCH" in out

    code, out = run_semver_probe("1.2.8", "~1.2.3")
    assert code == 0 and "STATUS:MATCH" in out

    code, out = run_semver_probe("1.3.0", "~1.2.3")
    assert code == 1 and "STATUS:NO_MATCH" in out

    code, out = run_semver_probe("1.2.2", "~1.2.3")
    assert code == 1 and "STATUS:NO_MATCH" in out


def test_semver_gte_operator():
    """Verify '>=' operator matching rules."""
    code, out = run_semver_probe("1.2.3", ">= 1.2.3")
    assert code == 0 and "STATUS:MATCH" in out

    code, out = run_semver_probe("1.5.0", ">= 1.2.3")
    assert code == 0 and "STATUS:MATCH" in out

    code, out = run_semver_probe("3.0.0", ">= 1.2.3")
    assert code == 0 and "STATUS:MATCH" in out

    code, out = run_semver_probe("1.2.2", ">= 1.2.3")
    assert code == 1 and "STATUS:NO_MATCH" in out

    code, out = run_semver_probe("0.9.9", ">= 1.2.3")
    assert code == 1 and "STATUS:NO_MATCH" in out


# -----------------------------------------------------------------------------
# Ambiguous and Invalid Range Rejection
# -----------------------------------------------------------------------------

def test_semver_rejects_conflicting_operators():
    """Verify that multiple conflicting operators like '^~' or '>=^' are rejected with diagnostic."""
    code, out = run_semver_probe("1.0.0", "^~1.0.0")
    assert code == 2 and "STATUS:INVALID_REQ" in out
    assert "conflicting multiple prefix operators" in out

    code, out = run_semver_probe("1.0.0", ">=^1.0.0")
    assert code == 2 and "STATUS:INVALID_REQ" in out
    assert "conflicting multiple prefix operators" in out


def test_semver_rejects_wildcard_and_unsupported_operators():
    """Verify that wildcards (*, 1.x) and ambiguous operators (<>, ==) are rejected."""
    code, out = run_semver_probe("1.0.0", "*")
    assert code == 2 and "STATUS:INVALID_REQ" in out
    assert "ambiguous range operator" in out

    code, out = run_semver_probe("1.0.0", "<> 1.0.0")
    assert code == 2 and "STATUS:INVALID_REQ" in out

    code, out = run_semver_probe("1.0.0", "== 1.0.0")
    assert code == 2 and "STATUS:INVALID_REQ" in out


def test_semver_rejects_malformed_version_strings():
    """Verify that four-component numbers, letters, and empty strings fail closed."""
    code, out = run_semver_probe("1.0.0", "1.2.3.4")
    assert code == 2 and "STATUS:INVALID_REQ" in out
    assert "malformed version string" in out

    code, out = run_semver_probe("1.0.0", "alpha_beta")
    assert code == 2 and "STATUS:INVALID_REQ" in out

    code, out = run_semver_probe("1.0.0", "1..3")
    assert code == 2 and "STATUS:INVALID_REQ" in out


# -----------------------------------------------------------------------------
# Registry Index Resolution & Maximal Version Selection
# -----------------------------------------------------------------------------

def test_registry_resolution_selects_highest_matching_semver(tmp_path):
    """Verify that registry resolution selects the highest matching version satisfying a requirement."""
    index_data = {
        "name": "math_multi",
        "versions": {
            "1.0.0": {"url": "https://example.com/math-1.0.0.tar.gz", "sha256": "aaa1"},
            "1.1.0": {"url": "https://example.com/math-1.1.0.tar.gz", "sha256": "aaa2"},
            "1.2.5": {"url": "https://example.com/math-1.2.5.tar.gz", "sha256": "aaa3"},
            "2.0.0": {"url": "https://example.com/math-2.0.0.tar.gz", "sha256": "aaa4"},
        },
    }

    # 1. '^1.0.0' should select highest 1.x -> '1.2.5'
    code, out = run_registry_semver_resolve("math_multi", "^1.0.0", index_data, tmp_path)
    assert code == 0, f"Expected 0, got {code}:\n{out}"
    assert "STATUS:OK" in out
    assert "RESOLVED_VERSION:1.2.5" in out
    assert "EXPECTED_HASH:aaa3" in out

    # 2. '~1.1.0' should select highest 1.1.x -> '1.1.0' (since 1.2.5 is a minor bump)
    code, out = run_registry_semver_resolve("math_multi", "~1.1.0", index_data, tmp_path)
    assert code == 0
    assert "RESOLVED_VERSION:1.1.0" in out
    assert "EXPECTED_HASH:aaa2" in out

    # 3. '>= 1.1.0' should select highest overall >= 1.1.0 -> '2.0.0'
    code, out = run_registry_semver_resolve("math_multi", ">= 1.1.0", index_data, tmp_path)
    assert code == 0
    assert "RESOLVED_VERSION:2.0.0" in out
    assert "EXPECTED_HASH:aaa4" in out

    # 4. '= 1.0.0' should select exact '1.0.0'
    code, out = run_registry_semver_resolve("math_multi", "= 1.0.0", index_data, tmp_path)
    assert code == 0
    assert "RESOLVED_VERSION:1.0.0" in out
    assert "EXPECTED_HASH:aaa1" in out


def test_registry_resolution_rejects_ambiguous_range_in_manifest(tmp_path):
    """Verify that an ambiguous range in manifest triggers a diagnostic with supported operators."""
    index_data = {
        "versions": {
            "1.0.0": {"url": "https://example.com/pkg.tar.gz", "sha256": "1111"},
        }
    }
    code, out = run_registry_semver_resolve("bad_range_pkg", "^~1.0.0", index_data, tmp_path)
    assert code == 1
    assert "STATUS:ERROR" in out
    assert "[Velo Error] Invalid or ambiguous semver requirement '^~1.0.0' for dependency 'bad_range_pkg'." in out
    assert "Supported operators are '=', '^', '~', and '>='" in out


def test_registry_resolution_no_matching_version_found(tmp_path):
    """Verify that when no available versions satisfy requirement, resolution fails closed."""
    index_data = {
        "versions": {
            "1.0.0": {"url": "https://example.com/pkg-1.0.0.tar.gz", "sha256": "1111"},
            "1.1.0": {"url": "https://example.com/pkg-1.1.0.tar.gz", "sha256": "2222"},
        }
    }
    code, out = run_registry_semver_resolve("no_match_pkg", "^2.0.0", index_data, tmp_path)
    assert code == 1
    assert "STATUS:ERROR" in out
    assert "Version '^2.0.0' of package 'no_match_pkg' not found in registry index" in out


# -----------------------------------------------------------------------------
# End-to-End velo pkg install with SemVer
# -----------------------------------------------------------------------------

def test_pkg_install_semver_caret_selects_highest_compatible(tmp_path):
    """Verify that 'velo pkg install' resolves and installs the highest compatible SemVer."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    # 1. Create two packages: 1.0.0 and 1.1.0
    tarballs_dir = tmp_path / "tarballs"
    tarballs_dir.mkdir(parents=True, exist_ok=True)

    def make_tarball(ver: str, ret_val: int) -> tuple[Path, str]:
        src_dir = tmp_path / f"src_{ver}"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "velo.pkg").write_text(f'pkg {{ name: "semver_lib" version: "{ver}" entry: "main.vl" }}\n', encoding="utf-8")
        (src_dir / "main.vl").write_text(f"act get_val() -> i32 {{ return {ret_val} }}\n", encoding="utf-8")
        archive = tarballs_dir / f"semver_lib-{ver}.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(src_dir / "velo.pkg", arcname="velo.pkg")
            tar.add(src_dir / "main.vl", arcname="main.vl")
        import hashlib
        return archive, hashlib.sha256(archive.read_bytes()).hexdigest()

    arch1, sha1 = make_tarball("1.0.0", 100)
    arch2, sha2 = make_tarball("1.1.0", 200)

    reg_root = tmp_path / "registry"
    pkg_index_dir = reg_root / "semver_lib"
    pkg_index_dir.mkdir(parents=True, exist_ok=True)
    index_content = {
        "name": "semver_lib",
        "versions": {
            "1.0.0": {"url": "file:///" + str(arch1).replace("\\", "/"), "sha256": sha1},
            "1.1.0": {"url": "file:///" + str(arch2).replace("\\", "/"), "sha256": sha2},
        },
    }
    (pkg_index_dir / "index.json").write_text(json.dumps(index_content, indent=2), encoding="utf-8")

    # 2. Consumer manifest requires ^1.0.0 -> must install 1.1.0!
    app_dir = tmp_path / "consumer_semver_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "main.vl").write_text("act main() -> i32 { return 0 }\n", encoding="utf-8")
    (app_dir / "velo.pkg").write_text(
        """pkg {
    name: "consumer_semver_app"
    version: "1.0.0"
    entry: "main.vl"
}
deps {
    semver_lib: "^1.0.0"
}
""",
        encoding="utf-8",
    )

    reg_url = "file:///" + str(reg_root).replace("\\", "/")
    res = subprocess.run(
        [str(VELO_EXE), "pkg", "install", str(app_dir), "--registry", reg_url],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=60,
    )
    assert res.returncode == 0, f"Install failed:\n{res.stderr}\n{res.stdout}"

    # 3. Assert installed version is 1.1.0 (highest compatible)
    installed_main = app_dir / ".velo_cache" / "deps" / "semver_lib" / "main.vl"
    assert installed_main.exists()
    assert "return 200" in installed_main.read_text(encoding="utf-8")

    # 4. Assert velo.lock recorded 1.1.0
    lock_file = app_dir / "velo.lock"
    assert lock_file.exists()
    assert 'version = "1.1.0"' in lock_file.read_text(encoding="utf-8")
