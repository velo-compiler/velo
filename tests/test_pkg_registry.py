"""
Tests for Phase 72 / Task 72.2:
Implement registry kind against a minimal HTTP index:
<registry>/<name>/index.json listing version -> {url, sha256}.
Enforces transport security (TLS required by default, plaintext HTTP disallowed
without --insecure flag, --insecure emits prominent warning).
"""

import http.server
import json
import os
import shutil
import socketserver
import subprocess
import threading
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


class MockRegistryServer:
    def __init__(self):
        self.routes = {}
        self.server = None
        self.thread = None
        self.port = None

    def set_route(self, path: str, status_code: int, content_type: str, body: bytes):
        self.routes[path] = (status_code, content_type, body)

    def start(self):
        routes = self.routes

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path in routes:
                    code, ctype, body = routes[self.path]
                    self.send_response(code)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_response(404)
                    self.send_header("Content-Type", "text/plain")
                    msg = b"Not Found"
                    self.send_header("Content-Length", str(len(msg)))
                    self.end_headers()
                    self.wfile.write(msg)

            def log_message(self, format, *args):
                pass  # suppress logging during tests

        self.server = socketserver.TCPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()


@pytest.fixture
def mock_registry():
    server = MockRegistryServer()
    server.start()
    yield server
    server.stop()


def run_registry_probe(
    dep_name: str,
    dep_version: str,
    insecure: bool,
    registry_override: str,
    m_dir: str,
    env=None,
) -> tuple[int, str]:
    """Runs a Velo probe program calling manifest_resolve_dep_full."""
    clean_override = registry_override.replace("\\", "/")
    clean_mdir = m_dir.replace("\\", "/")
    insecure_str = "true" if insecure else "false"
    probe_code = f"""use std.io
use "../src/common/manifest.vl"

act main() -> i32 {{
    mut dep = DependencySpec{{
        name: "{dep_name}",
        kind: "registry",
        source: "{dep_version}",
        tag: "",
        next: null
    }}
    let loc = manifest_resolve_dep_full("{clean_mdir}", @dep, {insecure_str}, "{clean_override}")
    if loc.has_error {{
        println_str("STATUS:ERROR")
        println_str("ERR:" + loc.error_msg)
        return 1
    }}
    println_str("STATUS:OK")
    println_str("PATH:" + loc.path)
    println_str("COMMIT:" + loc.commit)
    println_str("VERSION:" + loc.version)
    println_str("ARCHIVE_URL:" + loc.archive_url)
    println_str("EXPECTED_HASH:" + loc.expected_hash)
    return 0
}}
"""
    probe_name = f"_tmp_reg_probe_{dep_name.replace('.', '_').replace('/', '_')}"
    probe_path = REPO_ROOT / "tests" / f"{probe_name}.vl"
    probe_exe = REPO_ROOT / "tests" / f"{probe_name}.exe"
    probe_path.write_text(probe_code, encoding="utf-8")

    try:
        build_env = get_base_env()
        build_res = subprocess.run(
            [str(VELO_EXE), "build", str(probe_path), "-o", str(probe_exe)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=build_env,
            timeout=60,
        )
        if build_res.returncode != 0:
            return build_res.returncode, build_res.stdout + build_res.stderr

        run_env = env if env is not None else get_base_env()
        res = subprocess.run(
            [str(probe_exe)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=run_env,
            timeout=60,
        )
        return res.returncode, res.stdout + res.stderr
    finally:
        if probe_path.exists():
            probe_path.unlink()
        if probe_exe.exists():
            probe_exe.unlink()


def test_registry_resolve_success_nested_versions(tmp_path, mock_registry):
    """Test registry resolution against index.json with nested 'versions' object."""
    index_data = {
        "name": "math_pkg",
        "versions": {
            "1.2.0": {
                "url": "https://example.com/downloads/math_pkg-1.2.0.tar.gz",
                "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            }
        },
    }
    mock_registry.set_route(
        "/math_pkg/index.json",
        200,
        "application/json",
        json.dumps(index_data).encode("utf-8"),
    )

    reg_url = f"http://127.0.0.1:{mock_registry.port}"
    code, out = run_registry_probe(
        dep_name="math_pkg",
        dep_version="1.2.0",
        insecure=True,
        registry_override=reg_url,
        m_dir=str(tmp_path),
    )

    assert code == 0, f"Expected 0, got {code}:\n{out}"
    assert "STATUS:OK" in out
    assert "VERSION:1.2.0" in out
    assert "COMMIT:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" in out
    assert "ARCHIVE_URL:https://example.com/downloads/math_pkg-1.2.0.tar.gz" in out
    assert "EXPECTED_HASH:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" in out
    assert f"PATH:{str(tmp_path / '.velo_cache' / 'deps' / 'math_pkg').replace(chr(92), '/')}" in out.replace("\\", "/")
    # Transport security warning must be printed when cleartext HTTP is used with --insecure
    assert "[Velo Warning] Insecure connection to" in out
    assert "cleartext HTTP used." in out


def test_registry_resolve_success_flat_versions(tmp_path, mock_registry):
    """Test registry resolution against index.json with flat version mapping."""
    index_data = {
        "2.0.1": {
            "url": "https://example.com/downloads/flat_pkg-2.0.1.tar.gz",
            "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        }
    }
    mock_registry.set_route(
        "/flat_pkg/index.json",
        200,
        "application/json",
        json.dumps(index_data).encode("utf-8"),
    )

    reg_url = f"http://127.0.0.1:{mock_registry.port}"
    code, out = run_registry_probe(
        dep_name="flat_pkg",
        dep_version="2.0.1",
        insecure=True,
        registry_override=reg_url,
        m_dir=str(tmp_path),
    )

    assert code == 0, f"Expected 0, got {code}:\n{out}"
    assert "STATUS:OK" in out
    assert "VERSION:2.0.1" in out
    assert "ARCHIVE_URL:https://example.com/downloads/flat_pkg-2.0.1.tar.gz" in out
    assert "EXPECTED_HASH:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" in out


def test_registry_plaintext_http_disallowed_without_insecure(tmp_path, mock_registry):
    """Test that cleartext HTTP registry URLs fail closed when --insecure is false."""
    reg_url = f"http://127.0.0.1:{mock_registry.port}"
    code, out = run_registry_probe(
        dep_name="any_pkg",
        dep_version="1.0.0",
        insecure=False,
        registry_override=reg_url,
        m_dir=str(tmp_path),
    )

    assert code == 1, f"Expected 1, got {code}:\n{out}"
    assert "STATUS:ERROR" in out
    assert "[Velo Error] Plaintext HTTP registry URL" in out
    assert "is disallowed without explicit --insecure flag." in out


def test_registry_insecure_warning_on_https(tmp_path):
    """Test that specifying --insecure on an HTTPS registry emits a certificate verification warning."""
    # We point to an unreachable port to quickly trigger fetch error after the warning is printed
    reg_url = "https://127.0.0.1:65534"
    code, out = run_registry_probe(
        dep_name="sec_pkg",
        dep_version="1.0.0",
        insecure=True,
        registry_override=reg_url,
        m_dir=str(tmp_path),
    )

    assert "[Velo Warning] TLS certificate verification disabled via --insecure for registry 'https://127.0.0.1:65534/sec_pkg/index.json'." in out


def test_registry_version_not_found(tmp_path, mock_registry):
    """Test that requesting a version absent from index.json fails closed with actionable error."""
    index_data = {
        "versions": {
            "1.0.0": {
                "url": "https://example.com/pkg-1.0.0.tar.gz",
                "sha256": "112233",
            }
        }
    }
    mock_registry.set_route(
        "/some_pkg/index.json",
        200,
        "application/json",
        json.dumps(index_data).encode("utf-8"),
    )

    reg_url = f"http://127.0.0.1:{mock_registry.port}"
    code, out = run_registry_probe(
        dep_name="some_pkg",
        dep_version="2.0.0",
        insecure=True,
        registry_override=reg_url,
        m_dir=str(tmp_path),
    )

    assert code == 1, f"Expected 1, got {code}:\n{out}"
    assert "STATUS:ERROR" in out
    assert "Version '2.0.0' of package 'some_pkg' not found in registry index" in out


def test_registry_404_package_not_found(tmp_path, mock_registry):
    """Test that a 404 response for package index fails closed."""
    reg_url = f"http://127.0.0.1:{mock_registry.port}"
    code, out = run_registry_probe(
        dep_name="nonexistent_pkg",
        dep_version="1.0.0",
        insecure=True,
        registry_override=reg_url,
        m_dir=str(tmp_path),
    )

    assert code == 1, f"Expected 1, got {code}:\n{out}"
    assert "STATUS:ERROR" in out
    assert "Failed to fetch registry index from" in out


def test_registry_missing_url_field(tmp_path, mock_registry):
    """Test that index entry missing 'url' field fails closed."""
    index_data = {
        "versions": {
            "1.0.0": {
                "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            }
        }
    }
    mock_registry.set_route(
        "/bad_entry/index.json",
        200,
        "application/json",
        json.dumps(index_data).encode("utf-8"),
    )

    reg_url = f"http://127.0.0.1:{mock_registry.port}"
    code, out = run_registry_probe(
        dep_name="bad_entry",
        dep_version="1.0.0",
        insecure=True,
        registry_override=reg_url,
        m_dir=str(tmp_path),
    )

    assert code == 1, f"Expected 1, got {code}:\n{out}"
    assert "STATUS:ERROR" in out
    assert "Registry index entry for 'bad_entry@1.0.0' is missing 'url' field" in out


def test_registry_missing_sha256_field(tmp_path, mock_registry):
    """Test that index entry missing 'sha256' field fails closed."""
    index_data = {
        "versions": {
            "1.0.0": {
                "url": "https://example.com/bad.tar.gz",
            }
        }
    }
    mock_registry.set_route(
        "/bad_sha/index.json",
        200,
        "application/json",
        json.dumps(index_data).encode("utf-8"),
    )

    reg_url = f"http://127.0.0.1:{mock_registry.port}"
    code, out = run_registry_probe(
        dep_name="bad_sha",
        dep_version="1.0.0",
        insecure=True,
        registry_override=reg_url,
        m_dir=str(tmp_path),
    )

    assert code == 1, f"Expected 1, got {code}:\n{out}"
    assert "STATUS:ERROR" in out
    assert "Registry index entry for 'bad_sha@1.0.0' is missing 'sha256' field" in out


def test_registry_invalid_json(tmp_path, mock_registry):
    """Test that malformed JSON in index fails closed."""
    mock_registry.set_route(
        "/corrupt/index.json",
        200,
        "application/json",
        b"{ not valid json ...",
    )

    reg_url = f"http://127.0.0.1:{mock_registry.port}"
    code, out = run_registry_probe(
        dep_name="corrupt",
        dep_version="1.0.0",
        insecure=True,
        registry_override=reg_url,
        m_dir=str(tmp_path),
    )

    assert code == 1, f"Expected 1, got {code}:\n{out}"
    assert "STATUS:ERROR" in out
    assert "Invalid JSON in registry index from" in out


def test_registry_via_velo_registry_env(tmp_path, mock_registry):
    """Test that VELO_REGISTRY environment variable is honored when registry_override is empty."""
    index_data = {
        "versions": {
            "3.1.4": {
                "url": "https://example.com/env_pkg.tar.gz",
                "sha256": "feedface0011223344",
            }
        }
    }
    mock_registry.set_route(
        "/env_pkg/index.json",
        200,
        "application/json",
        json.dumps(index_data).encode("utf-8"),
    )

    env = get_base_env()
    env["VELO_REGISTRY"] = f"http://127.0.0.1:{mock_registry.port}"

    code, out = run_registry_probe(
        dep_name="env_pkg",
        dep_version="3.1.4",
        insecure=True,
        registry_override="",
        m_dir=str(tmp_path),
        env=env,
    )

    assert code == 0, f"Expected 0, got {code}:\n{out}"
    assert "STATUS:OK" in out
    assert "VERSION:3.1.4" in out
    assert "ARCHIVE_URL:https://example.com/env_pkg.tar.gz" in out
    assert "EXPECTED_HASH:feedface0011223344" in out


def test_registry_missing_curl_actionable_error(tmp_path):
    """Test that missing curl executable produces an actionable error message."""
    no_curl_env = get_base_env()
    filtered_path = [p for p in no_curl_env.get("PATH", "").split(os.pathsep) if not (Path(p) / "curl.exe").exists() and not (Path(p) / "curl").exists()]
    no_curl_env["PATH"] = os.pathsep.join(filtered_path)

    code, out = run_registry_probe(
        dep_name="any_pkg",
        dep_version="1.0.0",
        insecure=True,
        registry_override="https://pkg.velolang.org",
        m_dir=str(tmp_path),
        env=no_curl_env,
    )

    assert code == 1, f"Expected 1, got {code}:\n{out}"
    assert "STATUS:ERROR" in out
    assert "'curl' executable not found in PATH" in out
    assert "Please install Curl and ensure it is available in your PATH." in out
