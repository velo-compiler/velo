"""
Tests for Phase 72 / Task 72.5:
Add `velo pkg tree` and `velo pkg verify` (read-only: recompute hashes and report drift).
`verify` is what CI calls.
"""

import hashlib
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


def create_git_upstream_repo(repo_dir: Path, tag: str = "v1.0.0") -> str:
    """Creates a local upstream Git repository with a Velo library and commits it."""
    repo_dir.mkdir(parents=True, exist_ok=True)
    env = get_base_env()
    subprocess.run(["git", "init"], cwd=str(repo_dir), check=True, capture_output=True, env=env)
    subprocess.run(["git", "config", "user.name", "Velo Git Test"], cwd=str(repo_dir), check=True, env=env)
    subprocess.run(["git", "config", "user.email", "test@velo.org"], cwd=str(repo_dir), check=True, env=env)

    pkg_file = repo_dir / "velo.pkg"
    pkg_file.write_text(
        'pkg {\n    name: "upstream_git_pkg"\n    version: "1.0.0"\n    entry: "main.vl"\n}\n',
        encoding="utf-8",
    )
    main_file = repo_dir / "main.vl"
    main_file.write_text("act upstream_func() -> i32 { return 42 }\n", encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=str(repo_dir), check=True, capture_output=True, env=env)
    subprocess.run(["git", "commit", "-m", "Release 1.0.0"], cwd=str(repo_dir), check=True, capture_output=True, env=env)

    if tag:
        subprocess.run(["git", "tag", tag], cwd=str(repo_dir), check=True, capture_output=True, env=env)

    rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo_dir), check=True, capture_output=True, text=True, encoding="utf-8", env=env)
    return rev.stdout.strip()


def test_pkg_tree_single_package_no_deps(tmp_path):
    """Verify that 'velo pkg tree' on a standalone package with no dependencies prints root and exits 0."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    pkg_dir = tmp_path / "standalone_app"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "main.vl").write_text("act main() -> i32 { return 0 }\n", encoding="utf-8")
    (pkg_dir / "velo.pkg").write_text(
        """pkg {
    name: "standalone_app"
    version: "1.2.3"
    entry: "main.vl"
}
""",
        encoding="utf-8",
    )

    res = subprocess.run(
        [str(VELO_EXE), "pkg", "tree", str(pkg_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res.returncode == 0, f"velo pkg tree failed:\n{res.stderr}\n{res.stdout}"
    assert "standalone_app v1.2.3" in res.stdout


def test_pkg_tree_with_installed_dependencies(tmp_path):
    """Verify that 'velo pkg tree' displays formatted dependency tree with versions and kinds."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    # Local dependency
    local_dir = tmp_path / "my_local_lib"
    local_dir.mkdir(parents=True, exist_ok=True)
    (local_dir / "main.vl").write_text("act local_helper() -> i32 { return 1 }\n", encoding="utf-8")
    (local_dir / "velo.pkg").write_text(
        """pkg {
    name: "my_local_lib"
    version: "0.5.0"
    entry: "main.vl"
}
""",
        encoding="utf-8",
    )

    # Git upstream dependency
    git_dir = tmp_path / "my_git_lib"
    create_git_upstream_repo(git_dir, tag="v1.0.0")

    app_dir = tmp_path / "consumer_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "main.vl").write_text("act main() -> i32 { return 0 }\n", encoding="utf-8")

    clean_local = str(local_dir).replace("\\", "/")
    clean_git = str(git_dir).replace("\\", "/")
    (app_dir / "velo.pkg").write_text(
        f"""pkg {{
    name: "consumer_app"
    version: "0.1.0"
    entry: "main.vl"
}}
deps {{
    my_local_lib: local "{clean_local}"
    upstream_git_pkg: git "{clean_git}" @ "v1.0.0"
}}
""",
        encoding="utf-8",
    )

    # Run pkg install first to fetch git dependency and create lockfile
    res_inst = subprocess.run(
        [str(VELO_EXE), "pkg", "install", str(app_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=60,
    )
    assert res_inst.returncode == 0, f"install failed:\n{res_inst.stderr}\n{res_inst.stdout}"

    # Run pkg tree
    res_tree = subprocess.run(
        [str(VELO_EXE), "pkg", "tree", str(app_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res_tree.returncode == 0, f"tree failed:\n{res_tree.stderr}\n{res_tree.stdout}"
    output = res_tree.stdout
    assert "consumer_app v0.1.0" in output
    assert "my_local_lib" in output
    assert "upstream_git_pkg" in output
    assert "local:" in output
    assert "git:" in output


def test_pkg_tree_shows_not_installed_status(tmp_path):
    """Verify that 'velo pkg tree' identifies uninstalled dependencies."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    app_dir = tmp_path / "uninstalled_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "main.vl").write_text("act main() -> i32 { return 0 }\n", encoding="utf-8")
    (app_dir / "velo.pkg").write_text(
        """pkg {
    name: "uninstalled_app"
    version: "1.0.0"
    entry: "main.vl"
}
deps {
    missing_dep: registry "^2.0.0"
}
""",
        encoding="utf-8",
    )

    res = subprocess.run(
        [str(VELO_EXE), "pkg", "tree", str(app_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res.returncode == 0
    assert "missing_dep" in res.stdout
    assert "not installed" in res.stdout


def test_pkg_tree_transitive_multi_level(tmp_path):
    """Verify that 'velo pkg tree' renders multi-level nested dependency graphs."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    # Level 2 leaf library
    leaf_dir = tmp_path / "leaf_lib"
    leaf_dir.mkdir(parents=True, exist_ok=True)
    (leaf_dir / "main.vl").write_text("act leaf() -> i32 { return 7 }\n", encoding="utf-8")
    (leaf_dir / "velo.pkg").write_text(
        """pkg {
    name: "leaf_lib"
    version: "0.9.1"
    entry: "main.vl"
}
""",
        encoding="utf-8",
    )

    # Level 1 middle library
    mid_dir = tmp_path / "mid_lib"
    mid_dir.mkdir(parents=True, exist_ok=True)
    (mid_dir / "main.vl").write_text("act mid() -> i32 { return 42 }\n", encoding="utf-8")
    clean_leaf = str(leaf_dir).replace("\\", "/")
    (mid_dir / "velo.pkg").write_text(
        f"""pkg {{
    name: "mid_lib"
    version: "1.5.0"
    entry: "main.vl"
}}
deps {{
    leaf_lib: local "{clean_leaf}"
}}
""",
        encoding="utf-8",
    )

    # Root app
    root_dir = tmp_path / "root_app"
    root_dir.mkdir(parents=True, exist_ok=True)
    (root_dir / "main.vl").write_text("act main() -> i32 { return 0 }\n", encoding="utf-8")
    clean_mid = str(mid_dir).replace("\\", "/")
    (root_dir / "velo.pkg").write_text(
        f"""pkg {{
    name: "root_app"
    version: "2.0.0"
    entry: "main.vl"
}}
deps {{
    mid_lib: local "{clean_mid}"
}}
""",
        encoding="utf-8",
    )

    res = subprocess.run(
        [str(VELO_EXE), "pkg", "tree", str(root_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res.returncode == 0
    lines = res.stdout.strip().splitlines()
    assert any("root_app v2.0.0" in l for l in lines)
    assert any("mid_lib v1.5.0" in l for l in lines)
    assert any("leaf_lib v0.9.1" in l for l in lines)


def test_pkg_tree_cycle_detection(tmp_path):
    """Verify that cyclic dependencies do not trigger an infinite loop and mark cycle (*)."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    node_a = tmp_path / "node_a"
    node_b = tmp_path / "node_b"
    node_a.mkdir(parents=True, exist_ok=True)
    node_b.mkdir(parents=True, exist_ok=True)

    clean_b = str(node_b).replace("\\", "/")
    clean_a = str(node_a).replace("\\", "/")

    (node_a / "main.vl").write_text("act a() -> i32 { return 1 }\n", encoding="utf-8")
    (node_a / "velo.pkg").write_text(
        f"""pkg {{
    name: "node_a"
    version: "1.0.0"
    entry: "main.vl"
}}
deps {{
    node_b: local "{clean_b}"
}}
""",
        encoding="utf-8",
    )

    (node_b / "main.vl").write_text("act b() -> i32 { return 2 }\n", encoding="utf-8")
    (node_b / "velo.pkg").write_text(
        f"""pkg {{
    name: "node_b"
    version: "1.0.0"
    entry: "main.vl"
}}
deps {{
    node_a: local "{clean_a}"
}}
""",
        encoding="utf-8",
    )

    res = subprocess.run(
        [str(VELO_EXE), "pkg", "tree", str(node_a)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res.returncode == 0
    assert "node_a" in res.stdout
    assert "node_b" in res.stdout
    assert "(*)" in res.stdout


def test_pkg_verify_success_clean_state(tmp_path):
    """Verify that 'velo pkg verify' returns 0 when all locked hashes and dependencies match."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    local_dir = tmp_path / "verified_lib"
    local_dir.mkdir(parents=True, exist_ok=True)
    (local_dir / "main.vl").write_text("act lib_func() -> i32 { return 99 }\n", encoding="utf-8")
    (local_dir / "velo.pkg").write_text(
        """pkg {
    name: "verified_lib"
    version: "1.0.0"
    entry: "main.vl"
}
""",
        encoding="utf-8",
    )

    app_dir = tmp_path / "verified_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "main.vl").write_text("act main() -> i32 { return 0 }\n", encoding="utf-8")
    clean_lib = str(local_dir).replace("\\", "/")
    (app_dir / "velo.pkg").write_text(
        f"""pkg {{
    name: "verified_app"
    version: "1.0.0"
    entry: "main.vl"
}}
deps {{
    verified_lib: local "{clean_lib}"
}}
""",
        encoding="utf-8",
    )

    # 1. Install to create velo.lock
    res_inst = subprocess.run(
        [str(VELO_EXE), "pkg", "install", str(app_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=60,
    )
    assert res_inst.returncode == 0

    # 2. Run read-only verify
    res_ver = subprocess.run(
        [str(VELO_EXE), "pkg", "verify", str(app_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res_ver.returncode == 0, f"verify failed:\n{res_ver.stderr}\n{res_ver.stdout}"
    assert "All 1 dependencies match velo.lock with zero drift." in res_ver.stdout


def test_pkg_verify_missing_lockfile_fails(tmp_path):
    """Verify that 'velo pkg verify' fails closed when velo.lock is missing."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    app_dir = tmp_path / "no_lock_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "main.vl").write_text("act main() -> i32 { return 0 }\n", encoding="utf-8")
    (app_dir / "velo.pkg").write_text(
        """pkg {
    name: "no_lock_app"
    version: "1.0.0"
    entry: "main.vl"
}
deps {
    some_dep: local "../dep"
}
""",
        encoding="utf-8",
    )

    res = subprocess.run(
        [str(VELO_EXE), "pkg", "verify", str(app_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res.returncode != 0
    assert "Lockfile not found" in res.stdout


def test_pkg_verify_detects_uninstalled_dependency_drift(tmp_path):
    """Verify that 'velo pkg verify' reports drift when a dependency is missing from disk."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    local_dir = tmp_path / "dep_to_delete"
    local_dir.mkdir(parents=True, exist_ok=True)
    (local_dir / "main.vl").write_text("act dummy() {}\n", encoding="utf-8")

    app_dir = tmp_path / "missing_dep_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "main.vl").write_text("act main() -> i32 { return 0 }\n", encoding="utf-8")
    clean_dep = str(local_dir).replace("\\", "/")
    (app_dir / "velo.pkg").write_text(
        f"""pkg {{
    name: "missing_dep_app"
    version: "1.0.0"
    entry: "main.vl"
}}
deps {{
    dep_to_delete: local "{clean_dep}"
}}
""",
        encoding="utf-8",
    )

    # Create lockfile
    subprocess.run([str(VELO_EXE), "pkg", "lock", str(app_dir)], check=True, cwd=str(REPO_ROOT), env=get_base_env())

    # Delete dependency directory
    shutil.rmtree(local_dir)

    res = subprocess.run(
        [str(VELO_EXE), "pkg", "verify", str(app_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res.returncode != 0
    assert "Drift detected: dependency 'dep_to_delete' is not installed on disk" in res.stdout


def test_pkg_verify_detects_tampered_content_hash_drift(tmp_path):
    """Verify that 'velo pkg verify' reports checksum drift when files are modified."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    local_dir = tmp_path / "dep_to_tamper"
    local_dir.mkdir(parents=True, exist_ok=True)
    main_file = local_dir / "main.vl"
    main_file.write_text("act original_func() -> i32 { return 1 }\n", encoding="utf-8")

    app_dir = tmp_path / "tampered_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "main.vl").write_text("act main() -> i32 { return 0 }\n", encoding="utf-8")
    clean_dep = str(local_dir).replace("\\", "/")
    (app_dir / "velo.pkg").write_text(
        f"""pkg {{
    name: "tampered_app"
    version: "1.0.0"
    entry: "main.vl"
}}
deps {{
    dep_to_tamper: local "{clean_dep}"
}}
""",
        encoding="utf-8",
    )

    subprocess.run([str(VELO_EXE), "pkg", "lock", str(app_dir)], check=True, cwd=str(REPO_ROOT), env=get_base_env())

    # Tamper with dependency file
    main_file.write_text("act tampered_func() -> i32 { return 999 }\n", encoding="utf-8")

    res = subprocess.run(
        [str(VELO_EXE), "pkg", "verify", str(app_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res.returncode != 0
    assert "Drift detected: checksum mismatch for dependency 'dep_to_tamper'" in res.stdout
    assert "Expected (velo.lock):" in res.stdout
    assert "Actual (disk):" in res.stdout


def test_pkg_verify_detects_missing_lock_entry_drift(tmp_path):
    """Verify that adding a dependency to manifest without updating lockfile triggers drift error."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    app_dir = tmp_path / "stale_lock_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "main.vl").write_text("act main() -> i32 { return 0 }\n", encoding="utf-8")
    app_pkg = app_dir / "velo.pkg"
    app_pkg.write_text(
        """pkg {
    name: "stale_lock_app"
    version: "1.0.0"
    entry: "main.vl"
}
""",
        encoding="utf-8",
    )

    # Generate lockfile with 0 dependencies
    subprocess.run([str(VELO_EXE), "pkg", "lock", str(app_dir)], check=True, cwd=str(REPO_ROOT), env=get_base_env())

    # Now add dependency to manifest
    app_pkg.write_text(
        """pkg {
    name: "stale_lock_app"
    version: "1.0.0"
    entry: "main.vl"
}
deps {
    new_unlocked_dep: local "../dummy"
}
""",
        encoding="utf-8",
    )

    res = subprocess.run(
        [str(VELO_EXE), "pkg", "verify", str(app_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res.returncode != 0
    assert "Drift detected: dependency 'new_unlocked_dep' is declared in manifest but missing from velo.lock" in res.stdout


def test_pkg_verify_detects_extra_lock_entry_drift(tmp_path):
    """Verify that removing a dependency from manifest while lockfile retains it triggers drift error."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    dep_dir = tmp_path / "extra_dep"
    dep_dir.mkdir(parents=True, exist_ok=True)
    (dep_dir / "main.vl").write_text("act foo() {}\n", encoding="utf-8")

    app_dir = tmp_path / "orphan_lock_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "main.vl").write_text("act main() -> i32 { return 0 }\n", encoding="utf-8")
    clean_dep = str(dep_dir).replace("\\", "/")
    app_pkg = app_dir / "velo.pkg"
    app_pkg.write_text(
        f"""pkg {{
    name: "orphan_lock_app"
    version: "1.0.0"
    entry: "main.vl"
}}
deps {{
    extra_dep: local "{clean_dep}"
}}
""",
        encoding="utf-8",
    )

    # Lock with dependency
    subprocess.run([str(VELO_EXE), "pkg", "lock", str(app_dir)], check=True, cwd=str(REPO_ROOT), env=get_base_env())

    # Remove dependency from manifest
    app_pkg.write_text(
        """pkg {
    name: "orphan_lock_app"
    version: "1.0.0"
    entry: "main.vl"
}
""",
        encoding="utf-8",
    )

    res = subprocess.run(
        [str(VELO_EXE), "pkg", "verify", str(app_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res.returncode != 0
    assert "Drift detected: package 'extra_dep' is present in velo.lock but not declared in manifest" in res.stdout


def test_pkg_verify_detects_version_requirement_drift(tmp_path):
    """Verify that changing a semver requirement in manifest without updating lock triggers drift error."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    dep_dir = tmp_path / "ver_dep"
    dep_dir.mkdir(parents=True, exist_ok=True)
    (dep_dir / "main.vl").write_text("act v() {}\n", encoding="utf-8")

    app_dir = tmp_path / "semver_drift_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "main.vl").write_text("act main() -> i32 { return 0 }\n", encoding="utf-8")
    app_pkg = app_dir / "velo.pkg"
    app_pkg.write_text(
        """pkg {
    name: "semver_drift_app"
    version: "1.0.0"
    entry: "main.vl"
}
deps {
    math_lib: registry "^1.0.0"
}
""",
        encoding="utf-8",
    )

    # Fake cache and lockfile with locked version 1.1.0
    cache_math = app_dir / ".velo_cache" / "deps" / "math_lib"
    cache_math.mkdir(parents=True, exist_ok=True)
    (cache_math / "main.vl").write_text("act math() {}\n", encoding="utf-8")
    pkg_content = 'pkg {\nname: "math_lib"\nversion: "1.1.0"\nentry: "main.vl"\n}\n'
    (cache_math / "velo.pkg").write_text(pkg_content, encoding="utf-8")

    # Compute actual disk hash
    h = hashlib.sha256((pkg_content + "act math() {}\n").encode("utf-8")).hexdigest()

    # Create lockfile directly offline
    (app_dir / "velo.lock").write_text(
        f"""# Generated by Velo Package Manager (velo.lock). DO NOT EDIT MANUALLY.
package "math_lib" = {{ source = "https://pkg.velolang.org", version = "1.1.0", hash = "sha256:{h}" }}
""",
        encoding="utf-8",
    )

    # Now change requirement in velo.pkg to ^2.0.0 (which 1.1.0 does not satisfy)
    app_pkg.write_text(
        """pkg {
    name: "semver_drift_app"
    version: "1.0.0"
    entry: "main.vl"
}
deps {
    math_lib: registry "^2.0.0"
}
""",
        encoding="utf-8",
    )

    res = subprocess.run(
        [str(VELO_EXE), "pkg", "verify", str(app_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res.returncode != 0
    assert "Drift detected: locked version '1.1.0' does not satisfy manifest requirement '^2.0.0'" in res.stdout


def test_pkg_verify_is_strictly_read_only(tmp_path):
    """Verify that 'velo pkg verify' does not create or mutate files on disk."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    local_dir = tmp_path / "ro_dep"
    local_dir.mkdir(parents=True, exist_ok=True)
    (local_dir / "main.vl").write_text("act ro() {}\n", encoding="utf-8")

    app_dir = tmp_path / "ro_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "main.vl").write_text("act main() -> i32 { return 0 }\n", encoding="utf-8")
    clean_dep = str(local_dir).replace("\\", "/")
    (app_dir / "velo.pkg").write_text(
        f"""pkg {{
    name: "ro_app"
    version: "1.0.0"
    entry: "main.vl"
}}
deps {{
    ro_dep: local "{clean_dep}"
}}
""",
        encoding="utf-8",
    )

    subprocess.run([str(VELO_EXE), "pkg", "lock", str(app_dir)], check=True, cwd=str(REPO_ROOT), env=get_base_env())
    lock_file = app_dir / "velo.lock"
    lock_mtime_before = lock_file.stat().st_mtime_ns
    lock_content_before = lock_file.read_bytes()

    # Run verify multiple times
    for _ in range(3):
        res = subprocess.run(
            [str(VELO_EXE), "pkg", "verify", str(app_dir)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=get_base_env(),
            timeout=30,
        )
        assert res.returncode == 0

    assert lock_file.read_bytes() == lock_content_before, "velo.lock must not be modified by verify"
    assert lock_file.stat().st_mtime_ns == lock_mtime_before, "velo.lock timestamp must not change during verify"
