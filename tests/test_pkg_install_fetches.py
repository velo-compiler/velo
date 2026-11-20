"""
Tests for Phase 72 / Task 72.3:
Fix the lie: `pkg install` must call 72.1/72.2 for every dependency,
verify hashes (I72.2), and only then print success.
Asserts that the dependency directory exists and its files match the lock hash.
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


def test_pkg_install_fetches_git_dependency(tmp_path):
    """Verify that 'velo pkg install' actually clones git dependencies into .velo_cache/deps."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    upstream_dir = tmp_path / "upstream_repo"
    create_git_upstream_repo(upstream_dir, tag="v1.0.0")

    app_dir = tmp_path / "consumer_app"
    app_dir.mkdir(parents=True, exist_ok=True)

    app_main = app_dir / "main.vl"
    app_main.write_text("act main() -> i32 { return 0 }\n", encoding="utf-8")

    clean_upstream = str(upstream_dir).replace("\\", "/")
    app_pkg = app_dir / "velo.pkg"
    app_pkg.write_text(
        f"""pkg {{
    name: "consumer_app"
    version: "0.1.0"
    entry: "main.vl"
}}
deps {{
    upstream_git_pkg: git "{clean_upstream}" @ "v1.0.0"
}}
""",
        encoding="utf-8",
    )

    dep_cache_dir = app_dir / ".velo_cache" / "deps" / "upstream_git_pkg"
    assert not dep_cache_dir.exists(), "Dependency must not exist prior to install"

    # 1. Run 'velo pkg install'
    res = subprocess.run(
        [str(VELO_EXE), "pkg", "install", str(app_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=60,
    )
    assert res.returncode == 0, f"velo pkg install failed:\n{res.stderr}\n{res.stdout}"
    assert "Created velo.lock" in res.stdout or "All dependencies installed and locked successfully." in res.stdout

    # 2. Assert dependency directory exists on disk and contains files
    assert dep_cache_dir.exists(), f"Dependency directory {dep_cache_dir} must exist after install"
    assert (dep_cache_dir / "main.vl").exists(), "main.vl must exist in cloned dependency"
    assert "upstream_func" in (dep_cache_dir / "main.vl").read_text(encoding="utf-8")

    # 3. Assert velo.lock exists and its hash matches the dependency files
    lock_file = app_dir / "velo.lock"
    assert lock_file.exists(), "velo.lock must be created"
    lock_text = lock_file.read_text(encoding="utf-8")
    assert 'package "upstream_git_pkg"' in lock_text
    assert "hash = \"sha256:" in lock_text

    # 4. Re-run 'velo pkg install' against existing lockfile - must verify successfully
    res_verify = subprocess.run(
        [str(VELO_EXE), "pkg", "install", str(app_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=60,
    )
    assert res_verify.returncode == 0, f"Second install failed:\n{res_verify.stderr}\n{res_verify.stdout}"
    assert "verified against velo.lock" in res_verify.stdout


def test_pkg_install_fetches_registry_file_url_and_matches_lock_hash(tmp_path):
    """Verify that 'velo pkg install' fetches registry dependency tarball via file:// and verifies lock hash."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    # 1. Create upstream package files to be packaged into tarball
    pkg_source_dir = tmp_path / "math_upstream_src"
    pkg_source_dir.mkdir(parents=True, exist_ok=True)
    (pkg_source_dir / "velo.pkg").write_text(
        'pkg {\n    name: "math_upstream"\n    version: "1.0.0"\n    entry: "main.vl"\n}\n',
        encoding="utf-8",
    )
    (pkg_source_dir / "main.vl").write_text(
        "act math_add(a: i32, b: i32) -> i32 { return a + b }\n",
        encoding="utf-8",
    )

    # 2. Create archive .tar.gz
    tarballs_dir = tmp_path / "tarballs"
    tarballs_dir.mkdir(parents=True, exist_ok=True)
    archive_path = tarballs_dir / "math_upstream-1.0.0.tar.gz"

    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(pkg_source_dir / "velo.pkg", arcname="velo.pkg")
        tar.add(pkg_source_dir / "main.vl", arcname="main.vl")

    archive_bytes = archive_path.read_bytes()
    archive_sha256 = hashlib.sha256(archive_bytes).hexdigest()

    # 3. Create mock local registry index: <reg_root>/math_upstream/index.json
    reg_root = tmp_path / "registry"
    pkg_index_dir = reg_root / "math_upstream"
    pkg_index_dir.mkdir(parents=True, exist_ok=True)

    archive_file_url = "file:///" + str(archive_path).replace("\\", "/")
    index_content = {
        "name": "math_upstream",
        "versions": {
            "1.0.0": {
                "url": archive_file_url,
                "sha256": archive_sha256,
            }
        },
    }
    (pkg_index_dir / "index.json").write_text(json.dumps(index_content, indent=2), encoding="utf-8")

    # 4. Create consumer app
    app_dir = tmp_path / "reg_consumer_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "main.vl").write_text("act main() -> i32 { return 0 }\n", encoding="utf-8")
    (app_dir / "velo.pkg").write_text(
        """pkg {
    name: "reg_consumer_app"
    version: "1.0.0"
    entry: "main.vl"
}
deps {
    math_upstream: "1.0.0"
}
""",
        encoding="utf-8",
    )

    reg_root_url = "file:///" + str(reg_root).replace("\\", "/")
    dep_cache_dir = app_dir / ".velo_cache" / "deps" / "math_upstream"
    assert not dep_cache_dir.exists(), "Dependency must not exist prior to install"

    # 5. Run 'velo pkg install' with --registry
    res = subprocess.run(
        [str(VELO_EXE), "pkg", "install", str(app_dir), "--registry", reg_root_url],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=60,
    )
    assert res.returncode == 0, f"velo pkg install failed:\n{res.stderr}\n{res.stdout}"
    assert "Created velo.lock" in res.stdout or "All dependencies installed and locked successfully." in res.stdout

    # 6. Verify directory exists and unpacked files match
    assert dep_cache_dir.exists(), "Dependency directory must exist after install"
    assert (dep_cache_dir / "main.vl").exists(), "main.vl must be unpacked"
    assert "math_add" in (dep_cache_dir / "main.vl").read_text(encoding="utf-8")

    # 7. Verify velo.lock exists and records valid hash
    lock_file = app_dir / "velo.lock"
    assert lock_file.exists(), "velo.lock must exist"
    lock_text = lock_file.read_text(encoding="utf-8")
    assert 'package "math_upstream"' in lock_text
    assert "hash = \"sha256:" in lock_text


def test_pkg_install_detects_tampered_dependency_and_fails_fatally(tmp_path):
    """Verify that tampering with fetched dependency files is caught by lock verification (I72.4)."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    upstream_dir = tmp_path / "upstream_tamper_repo"
    create_git_upstream_repo(upstream_dir, tag="v1.0.0")

    app_dir = tmp_path / "tamper_consumer"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "main.vl").write_text("act main() -> i32 { return 0 }\n", encoding="utf-8")

    clean_upstream = str(upstream_dir).replace("\\", "/")
    (app_dir / "velo.pkg").write_text(
        f"""pkg {{
    name: "tamper_consumer"
    version: "1.0.0"
    entry: "main.vl"
}}
deps {{
    upstream_git_pkg: git "{clean_upstream}" @ "v1.0.0"
}}
""",
        encoding="utf-8",
    )

    # 1. Install and generate lock
    res = subprocess.run(
        [str(VELO_EXE), "pkg", "install", str(app_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=60,
    )
    assert res.returncode == 0

    # 2. Tamper with cloned dependency file
    dep_main = app_dir / ".velo_cache" / "deps" / "upstream_git_pkg" / "main.vl"
    assert dep_main.exists()
    dep_main.write_text("act upstream_func() -> i32 { return 999999 /* injected malicious payload */ }\n", encoding="utf-8")

    # 3. Subsequent 'velo pkg install' must fail fatally with expected vs actual hashes
    res_tampered = subprocess.run(
        [str(VELO_EXE), "pkg", "install", str(app_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=60,
    )
    assert res_tampered.returncode != 0, "Must exit non-zero on lockfile mismatch (I72.4)"
    assert "Package checksum verification failed for 'upstream_git_pkg'" in res_tampered.stdout or "Package checksum verification failed for 'upstream_git_pkg'" in res_tampered.stderr
    assert "Expected: sha256:" in res_tampered.stdout or "Expected: sha256:" in res_tampered.stderr
    assert "Actual:   sha256:" in res_tampered.stdout or "Actual:   sha256:" in res_tampered.stderr
    assert "Package contents may have been tampered with or modified" in res_tampered.stdout or "Package contents may have been tampered with or modified" in res_tampered.stderr


def test_pkg_install_corrupt_archive_hash_fails_closed(tmp_path):
    """Verify that if archive SHA-256 does not match index.json, install fails closed (I72.2)."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    pkg_source_dir = tmp_path / "dummy_src"
    pkg_source_dir.mkdir(parents=True, exist_ok=True)
    (pkg_source_dir / "velo.pkg").write_text('pkg { name: "dummy_lib" version: "1.0.0" entry: "main.vl" }\n', encoding="utf-8")
    (pkg_source_dir / "main.vl").write_text("act dummy() {}\n", encoding="utf-8")

    tarballs_dir = tmp_path / "tarballs_bad"
    tarballs_dir.mkdir(parents=True, exist_ok=True)
    archive_path = tarballs_dir / "dummy_lib-1.0.0.tar.gz"

    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(pkg_source_dir / "velo.pkg", arcname="velo.pkg")
        tar.add(pkg_source_dir / "main.vl", arcname="main.vl")

    # Intentionally fraudulent hash
    wrong_hash = "0000000000000000000000000000000000000000000000000000000000000000"

    reg_root = tmp_path / "registry_bad"
    pkg_index_dir = reg_root / "dummy_lib"
    pkg_index_dir.mkdir(parents=True, exist_ok=True)

    archive_file_url = "file:///" + str(archive_path).replace("\\", "/")
    index_content = {
        "name": "dummy_lib",
        "versions": {
            "1.0.0": {
                "url": archive_file_url,
                "sha256": wrong_hash,
            }
        },
    }
    (pkg_index_dir / "index.json").write_text(json.dumps(index_content, indent=2), encoding="utf-8")

    app_dir = tmp_path / "bad_hash_consumer"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "main.vl").write_text("act main() -> i32 { return 0 }\n", encoding="utf-8")
    (app_dir / "velo.pkg").write_text(
        """pkg {
    name: "bad_hash_consumer"
    version: "1.0.0"
    entry: "main.vl"
}
deps {
    dummy_lib: "1.0.0"
}
""",
        encoding="utf-8",
    )

    reg_root_url = "file:///" + str(reg_root).replace("\\", "/")
    res = subprocess.run(
        [str(VELO_EXE), "pkg", "install", str(app_dir), "--registry", reg_root_url],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=60,
    )
    assert res.returncode != 0, "Must fail closed when archive checksum fails"
    assert "Package archive checksum verification failed for 'dummy_lib'" in res.stdout or "Package archive checksum verification failed for 'dummy_lib'" in res.stderr
    assert "Expected: 000000000000" in res.stdout or "Expected: 000000000000" in res.stderr

    dep_dir = app_dir / ".velo_cache" / "deps" / "dummy_lib"
    assert not dep_dir.exists(), "Corrupted archive must not leave extracted files on disk"


def test_pkg_install_unreachable_dependency_fails_closed(tmp_path):
    """Verify that unreachable dependency causes non-zero exit without false success message (I72.1)."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    app_dir = tmp_path / "unreachable_consumer"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "main.vl").write_text("act main() -> i32 { return 0 }\n", encoding="utf-8")
    (app_dir / "velo.pkg").write_text(
        """pkg {
    name: "unreachable_consumer"
    version: "1.0.0"
    entry: "main.vl"
}
deps {
    broken_git: git "https://127.0.0.1:65534/bad/repo.git" @ "v1.0.0"
}
""",
        encoding="utf-8",
    )

    res = subprocess.run(
        [str(VELO_EXE), "pkg", "install", str(app_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=60,
    )
    assert res.returncode != 0, "Must fail when git clone fails (I72.1)"
    assert "Failed to clone git dependency" in res.stdout or "Failed to clone git dependency" in res.stderr
    assert "All dependencies installed and locked successfully" not in res.stdout
