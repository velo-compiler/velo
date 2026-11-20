"""
Tests for Phase 72 / Task 72.1:
Implement manifest_resolve_dep(dep) -> DepLocation for local and git kinds.
Verifies git clone --depth 1 --branch <tag> <url>, git rev-parse HEAD,
actionable missing-git error, and fail-closed local resolution.
"""

import os
import shutil
import subprocess
import tempfile
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


def create_local_git_repo(repo_dir: Path, tag: str = None) -> str:
    """Initializes a local git repo, commits a file, optionally creates a tag, and returns HEAD SHA."""
    repo_dir.mkdir(parents=True, exist_ok=True)
    env = get_base_env()
    # Configure author so git commit succeeds in isolated temp environments
    subprocess.run(["git", "init"], cwd=str(repo_dir), check=True, capture_output=True, env=env)
    subprocess.run(["git", "config", "user.name", "Velo Test"], cwd=str(repo_dir), check=True, env=env)
    subprocess.run(["git", "config", "user.email", "test@velo.org"], cwd=str(repo_dir), check=True, env=env)

    # Create dummy package file
    pkg_file = repo_dir / "velo.pkg"
    pkg_file.write_text(
        'pkg {\n    name: "git_dep_pkg"\n    version: "1.0.0"\n    entry: "main.vl"\n}\n',
        encoding="utf-8",
    )
    main_file = repo_dir / "main.vl"
    main_file.write_text("act dep_hello() -> string { return \"hello from git\" }\n", encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=str(repo_dir), check=True, capture_output=True, env=env)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(repo_dir), check=True, capture_output=True, env=env)

    if tag:
        subprocess.run(["git", "tag", tag], cwd=str(repo_dir), check=True, capture_output=True, env=env)

    rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo_dir), check=True, capture_output=True, text=True, env=env)
    return rev.stdout.strip()


def run_resolve_probe(dep_name: str, dep_kind: str, dep_source: str, dep_tag: str, m_dir: str, env=None) -> tuple[int, str]:
    """Runs a Velo program that calls manifest_resolve_dep_in and outputs results."""
    clean_source = dep_source.replace("\\", "/")
    clean_mdir = m_dir.replace("\\", "/")
    probe_code = f"""use std.io
use "../src/common/manifest.vl"

act main() -> i32 {{
    mut dep = DependencySpec{{
        name: "{dep_name}",
        kind: "{dep_kind}",
        source: "{clean_source}",
        tag: "{dep_tag}",
        next: null
    }}
    let loc = manifest_resolve_dep_in("{clean_mdir}", @dep)
    if loc.has_error {{
        println_str("STATUS:ERROR")
        println_str("ERR:" + loc.error_msg)
        return 1
    }}
    println_str("STATUS:OK")
    println_str("PATH:" + loc.path)
    println_str("COMMIT:" + loc.commit)
    println_str("VERSION:" + loc.version)
    return 0
}}
"""
    probe_path = REPO_ROOT / "tests" / f"_tmp_probe_{dep_name.replace('.', '_').replace('/', '_')}.vl"
    probe_path.write_text(probe_code, encoding="utf-8")

    try:
        run_env = env if env is not None else get_base_env()
        res = subprocess.run(
            [str(VELO_EXE), "run", str(probe_path)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=run_env,
            timeout=60,
        )
        return res.returncode, res.stdout + res.stderr
    finally:
        if probe_path.exists():
            probe_path.unlink()


def test_resolve_local_dependency_success(tmp_path):
    """Verify that a valid local dependency resolves successfully with no error."""
    lib_dir = tmp_path / "my_local_lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    pkg_file = lib_dir / "velo.pkg"
    pkg_file.write_text('pkg { name: "my_local_lib" version: "0.1.0" entry: "main.vl" }\n', encoding="utf-8")

    code, out = run_resolve_probe("my_local_lib", "local", str(lib_dir), "", str(tmp_path))
    assert code == 0, f"Expected 0, got {code}:\n{out}"
    assert "STATUS:OK" in out
    assert f"PATH:{str(lib_dir).replace(chr(92), '/')}" in out.replace("\\", "/")
    assert "VERSION:local" in out


def test_resolve_local_dependency_missing(tmp_path):
    """Verify that a missing local dependency fails closed with actionable error."""
    missing_path = tmp_path / "nonexistent_lib_xyz"
    code, out = run_resolve_probe("missing_lib", "local", str(missing_path), "", str(tmp_path))
    assert code == 1, f"Expected 1, got {code}:\n{out}"
    assert "STATUS:ERROR" in out
    assert "not found at path" in out


def test_resolve_git_dependency_with_tag(tmp_path):
    """Verify git dependency cloning with --branch <tag> and capturing git rev-parse HEAD."""
    repo_dir = tmp_path / "upstream_repo"
    expected_head = create_local_git_repo(repo_dir, tag="v1.2.3")

    consumer_dir = tmp_path / "consumer_app"
    consumer_dir.mkdir(parents=True, exist_ok=True)

    code, out = run_resolve_probe("upstream_lib", "git", str(repo_dir), "v1.2.3", str(consumer_dir))
    assert code == 0, f"Expected 0, got {code}:\n{out}"
    assert "STATUS:OK" in out
    assert "VERSION:v1.2.3" in out
    assert f"COMMIT:{expected_head}" in out

    cloned_dir = consumer_dir / ".velo_cache" / "deps" / "upstream_lib"
    assert cloned_dir.exists(), f"Cloned directory {cloned_dir} must exist"
    assert (cloned_dir / "main.vl").exists(), "Cloned files must be present"


def test_resolve_git_dependency_without_tag(tmp_path):
    """Verify git dependency cloning without a tag defaults to HEAD commit as version."""
    repo_dir = tmp_path / "upstream_repo_notag"
    expected_head = create_local_git_repo(repo_dir)

    consumer_dir = tmp_path / "consumer_app2"
    consumer_dir.mkdir(parents=True, exist_ok=True)

    code, out = run_resolve_probe("notag_lib", "git", str(repo_dir), "", str(consumer_dir))
    assert code == 0, f"Expected 0, got {code}:\n{out}"
    assert "STATUS:OK" in out
    assert f"COMMIT:{expected_head}" in out
    assert f"VERSION:{expected_head}" in out


def test_resolve_git_dependency_missing_git_actionable_error(tmp_path):
    """Verify that when 'git' executable is absent from PATH, resolution fails closed with actionable message."""
    repo_dir = tmp_path / "dummy_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Construct an environment where git cannot be found
    no_git_env = get_base_env()
    # Strip paths containing git
    filtered_path = [p for p in no_git_env.get("PATH", "").split(os.pathsep) if "git" not in p.lower()]
    no_git_env["PATH"] = os.pathsep.join(filtered_path)

    code, out = run_resolve_probe("dummy_dep", "git", str(repo_dir), "", str(tmp_path), env=no_git_env)
    assert code == 1, f"Expected 1, got {code}:\n{out}"
    assert "STATUS:ERROR" in out
    assert "'git' executable not found in PATH" in out
    assert "Please install Git and ensure it is available in your PATH." in out


def test_resolve_git_dependency_invalid_url(tmp_path):
    """Verify that an invalid/unreachable git URL fails closed with actionable error."""
    code, out = run_resolve_probe("broken_git", "git", "https://127.0.0.1:65534/bad/repo.git", "", str(tmp_path))
    assert code == 1, f"Expected 1, got {code}:\n{out}"
    assert "STATUS:ERROR" in out
    assert "Failed to clone git dependency" in out


def test_resolve_invalid_dependency_name_traversal(tmp_path):
    """Verify that dependency names with directory traversal characters are rejected."""
    code, out = run_resolve_probe("../escaped_dep", "local", "some_path", "", str(tmp_path))
    assert code == 1, f"Expected 1, got {code}:\n{out}"
    assert "STATUS:ERROR" in out
    assert "Invalid dependency name" in out


def test_resolve_registry_dependency_unsupported(tmp_path):
    """Verify that registry dependencies produce a clear unsupported diagnostic pending Task 72.2."""
    code, out = run_resolve_probe("reg_dep", "registry", "1.0.0", "", str(tmp_path))
    assert code == 1, f"Expected 1, got {code}:\n{out}"
    assert "STATUS:ERROR" in out
    assert "Registry dependencies are not yet supported (Phase 72.2)" in out
