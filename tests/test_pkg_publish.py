"""
Tests for Phase 72 / Task 72.6:
Add `velo pkg publish` that tars the manifest's declared `src/` and `std/` subsets,
computes the hash, and prints the index entry to paste.
No upload servers, no accounts - publishing is a pull request to a registry repository.
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


def test_pkg_publish_default_options(tmp_path):
    """Verify that 'velo pkg publish' archives src/ and velo.pkg, computes SHA-256, and prints index entry."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    pkg_dir = tmp_path / "math_lib"
    src_dir = pkg_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    (pkg_dir / "velo.pkg").write_text(
        """pkg {
    name: "math_lib"
    version: "1.0.0"
    entry: "src/main.vl"
}
""",
        encoding="utf-8",
    )
    (src_dir / "main.vl").write_text("act add(a: i32, b: i32) -> i32 { return a + b }\n", encoding="utf-8")

    res = subprocess.run(
        [str(VELO_EXE), "pkg", "publish", str(pkg_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res.returncode == 0, f"publish failed:\n{res.stderr}\n{res.stdout}"

    expected_tar = pkg_dir / "dist" / "math_lib-1.0.0.tar.gz"
    assert expected_tar.exists(), f"Tarball must be created at {expected_tar}"

    # Calculate actual tarball hash
    tar_bytes = expected_tar.read_bytes()
    expected_sha = hashlib.sha256(tar_bytes).hexdigest()

    assert expected_sha in res.stdout
    assert "Successfully packaged 'math_lib' v1.0.0" in res.stdout
    assert "Paste this entry into math_lib/index.json under \"versions\":" in res.stdout
    assert '"1.0.0": {' in res.stdout
    assert f'"sha256": "{expected_sha}"' in res.stdout
    assert "https://pkg.velolang.org/tarballs/math_lib-1.0.0.tar.gz" in res.stdout

    # Inspect tarball contents
    with tarfile.open(expected_tar, "r:gz") as tar:
        names = tar.getnames()
        assert "velo.pkg" in names
        assert "src" in names or "src/main.vl" in names


def test_pkg_publish_custom_out_tarball(tmp_path):
    """Verify that 'velo pkg publish --out <path>' writes tarball to custom location."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    pkg_dir = tmp_path / "custom_out_pkg"
    src_dir = pkg_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "velo.pkg").write_text(
        """pkg {
    name: "custom_out_pkg"
    version: "2.1.0"
    entry: "src/main.vl"
}
""",
        encoding="utf-8",
    )
    (src_dir / "main.vl").write_text("act answer() -> i32 { return 42 }\n", encoding="utf-8")

    custom_tar = tmp_path / "custom_releases" / "custom_archive.tar.gz"

    res = subprocess.run(
        [str(VELO_EXE), "pkg", "publish", str(pkg_dir), "-o", str(custom_tar)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res.returncode == 0
    assert custom_tar.exists(), "Custom tarball must be created at specified path"
    actual_sha = hashlib.sha256(custom_tar.read_bytes()).hexdigest()
    assert actual_sha in res.stdout


def test_pkg_publish_custom_url_and_registry(tmp_path):
    """Verify that 'velo pkg publish' respects --url and --registry overrides."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    pkg_dir = tmp_path / "url_override_pkg"
    src_dir = pkg_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "velo.pkg").write_text(
        """pkg {
    name: "url_override_pkg"
    version: "0.5.0"
    entry: "src/main.vl"
}
""",
        encoding="utf-8",
    )
    (src_dir / "main.vl").write_text("act dummy() {}\n", encoding="utf-8")

    # Test --url
    res_url = subprocess.run(
        [str(VELO_EXE), "pkg", "publish", str(pkg_dir), "--url", "https://cdn.myhost.com/files/pkg-0.5.0.tar.gz"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res_url.returncode == 0
    assert '"url": "https://cdn.myhost.com/files/pkg-0.5.0.tar.gz"' in res_url.stdout

    # Test --registry
    res_reg = subprocess.run(
        [str(VELO_EXE), "pkg", "publish", str(pkg_dir), "--registry", "https://my-registry.example.org"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res_reg.returncode == 0
    assert "https://my-registry.example.org/tarballs/url_override_pkg-0.5.0.tar.gz" in res_reg.stdout


def test_pkg_publish_json_flag(tmp_path):
    """Verify that 'velo pkg publish --json' outputs structured machine-readable JSON."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    pkg_dir = tmp_path / "json_pkg"
    src_dir = pkg_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "velo.pkg").write_text(
        """pkg {
    name: "json_pkg"
    version: "3.0.1"
    entry: "src/main.vl"
}
""",
        encoding="utf-8",
    )
    (src_dir / "main.vl").write_text("act run() {}\n", encoding="utf-8")

    res = subprocess.run(
        [str(VELO_EXE), "pkg", "publish", str(pkg_dir), "--json"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res.returncode == 0
    data = json.loads(res.stdout.strip())
    assert data["name"] == "json_pkg"
    assert data["version"] == "3.0.1"
    assert "archive" in data
    assert "url" in data
    assert len(data["sha256"]) == 64


def test_pkg_publish_packages_std_subset(tmp_path):
    """Verify that 'velo pkg publish' packages std/ subset when present."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    pkg_dir = tmp_path / "std_lib_pkg"
    std_dir = pkg_dir / "std" / "extra"
    std_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "velo.pkg").write_text(
        """pkg {
    name: "std_lib_pkg"
    version: "1.0.0"
    entry: "std/extra/tool.vl"
}
""",
        encoding="utf-8",
    )
    (std_dir / "tool.vl").write_text("act helper() -> i32 { return 1 }\n", encoding="utf-8")

    res = subprocess.run(
        [str(VELO_EXE), "pkg", "publish", str(pkg_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res.returncode == 0

    tar_path = pkg_dir / "dist" / "std_lib_pkg-1.0.0.tar.gz"
    assert tar_path.exists()
    with tarfile.open(tar_path, "r:gz") as tar:
        names = tar.getnames()
        assert "velo.pkg" in names
        assert any("std" in n for n in names)


def test_pkg_publish_fails_on_missing_manifest(tmp_path):
    """Verify fail-closed error when manifest is not found."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir(parents=True, exist_ok=True)

    res = subprocess.run(
        [str(VELO_EXE), "pkg", "publish", str(empty_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res.returncode != 0
    assert "Package manifest not found" in res.stdout


def test_pkg_publish_fails_on_invalid_semver(tmp_path):
    """Verify fail-closed error when package version is not valid SemVer."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    pkg_dir = tmp_path / "bad_semver_pkg"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "main.vl").write_text("act main() {}\n", encoding="utf-8")
    (pkg_dir / "velo.pkg").write_text(
        """pkg {
    name: "bad_semver_pkg"
    version: "1.0"
    entry: "main.vl"
}
""",
        encoding="utf-8",
    )

    res = subprocess.run(
        [str(VELO_EXE), "pkg", "publish", str(pkg_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res.returncode != 0
    assert "Invalid semver version '1.0'" in res.stdout


def test_pkg_publish_fails_when_no_source_files_exist(tmp_path):
    """Verify fail-closed error when package has no source files to package."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    pkg_dir = tmp_path / "no_src_pkg"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "velo.pkg").write_text(
        """pkg {
    name: "no_src_pkg"
    version: "1.0.0"
    entry: "missing_entry.vl"
}
""",
        encoding="utf-8",
    )

    res = subprocess.run(
        [str(VELO_EXE), "pkg", "publish", str(pkg_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res.returncode != 0
    assert "Package contains no declared source files" in res.stdout


def test_pkg_publish_roundtrip_with_pkg_install(tmp_path):
    """End-to-end integration: publish a library, construct index.json from published output, and install it in a consumer app."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    # 1. Author and publish library
    lib_dir = tmp_path / "published_math"
    src_dir = lib_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (lib_dir / "velo.pkg").write_text(
        """pkg {
    name: "published_math"
    version: "1.2.0"
    entry: "src/main.vl"
}
""",
        encoding="utf-8",
    )
    (src_dir / "main.vl").write_text("act add(a: i32, b: i32) -> i32 { return a + b }\n", encoding="utf-8")

    res_pub = subprocess.run(
        [str(VELO_EXE), "pkg", "publish", str(lib_dir), "--json"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res_pub.returncode == 0
    pub_info = json.loads(res_pub.stdout.strip())
    tar_path = Path(pub_info["archive"])
    tar_sha = pub_info["sha256"]
    assert tar_path.exists()

    # 2. Create static file:// registry layout with index.json
    reg_root = tmp_path / "mock_registry"
    pkg_index_dir = reg_root / "published_math"
    pkg_index_dir.mkdir(parents=True, exist_ok=True)

    clean_tar_url = "file:///" + str(tar_path).replace("\\", "/")
    index_data = {
        "name": "published_math",
        "versions": {
            "1.2.0": {
                "url": clean_tar_url,
                "sha256": tar_sha,
            }
        },
    }
    (pkg_index_dir / "index.json").write_text(json.dumps(index_data, indent=2), encoding="utf-8")

    # 3. Create consumer app referencing published_math from registry
    app_dir = tmp_path / "consumer_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "main.vl").write_text("act main() -> i32 { return 0 }\n", encoding="utf-8")
    (app_dir / "velo.pkg").write_text(
        """pkg {
    name: "consumer_app"
    version: "0.1.0"
    entry: "main.vl"
}
deps {
    published_math: "^1.0.0"
}
""",
        encoding="utf-8",
    )

    clean_reg_url = "file:///" + str(reg_root).replace("\\", "/")

    # 4. Install dependency
    res_inst = subprocess.run(
        [str(VELO_EXE), "pkg", "install", str(app_dir), "--registry", clean_reg_url, "--insecure"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=60,
    )
    assert res_inst.returncode == 0, f"install failed:\n{res_inst.stderr}\n{res_inst.stdout}"

    installed_dir = app_dir / ".velo_cache" / "deps" / "published_math"
    assert installed_dir.exists(), "Installed dependency directory must exist"
    assert (installed_dir / "src" / "main.vl").exists(), "Published source file must be extracted"

    # 5. Verify zero drift with read-only verify
    res_ver = subprocess.run(
        [str(VELO_EXE), "pkg", "verify", str(app_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_base_env(),
        timeout=30,
    )
    assert res_ver.returncode == 0
    assert "All 1 dependencies match velo.lock with zero drift." in res_ver.stdout
