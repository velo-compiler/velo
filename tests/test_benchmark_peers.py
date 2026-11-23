"""
tests/test_benchmark_peers.py — Regression verification of peer benchmark implementations
Tests:
  1. Verifies that all 15 peer implementations across 3 workloads (HTTP server,
     JSON parsing, and file scanning) exist in benchmark/.
  2. Verifies exact output parity across all 5 languages for file scanning.
  3. Verifies exact output parity across all 5 languages for JSON parsing.
  4. Verifies endpoint responses (/plaintext and /json) across all 5 HTTP servers.
"""

import os
import sys
import time
import socket
import subprocess
import pytest
from pathlib import Path
from tests.conftest import velo_exe, cc_env, is_windows

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_DIR = REPO_ROOT / "benchmark"
BOOTSTRAP_C = REPO_ROOT / "bootstrap.c"

EXT = ".exe" if is_windows() else ""

def test_peer_source_files_exist():
    """All 15 peer source implementations must exist in benchmark/."""
    expected = [
        "server_velo.vl", "server_c.c", "server_rust.rs", "server_go.go", "server_node.js",
        "json_velo.vl", "json_c.c", "json_rust.rs", "json_go.go", "json_node.js",
        "filescan_velo.vl", "filescan_c.c", "filescan_rust.rs", "filescan_go.go", "filescan_node.js"
    ]
    for filename in expected:
        path = BENCHMARK_DIR / filename
        assert path.exists(), f"Expected benchmark source file {filename} to exist"

def _run_peer(cmd: list) -> str:
    env = cc_env()
    res = subprocess.run(cmd, cwd=str(BENCHMARK_DIR), env=env, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert res.returncode == 0, f"Peer execution failed for {cmd}:\n{res.stderr}\n{res.stdout}"
    return res.stdout.strip()

def test_filescan_peers_parity():
    """All 5 file scanning peers must produce identical line, word, and byte counts on bootstrap.c."""
    if not BOOTSTRAP_C.exists():
        pytest.skip("bootstrap.c not found")

    target = str(BOOTSTRAP_C)
    expected_line = "Scanned: lines=76931, words=285222, bytes=3259543"

    peers = [
        [str(BENCHMARK_DIR / f"filescan_velo{EXT}"), target],
        [str(BENCHMARK_DIR / f"filescan_c{EXT}"), target],
        [str(BENCHMARK_DIR / f"filescan_rust{EXT}"), target],
        [str(BENCHMARK_DIR / f"filescan_go{EXT}"), target],
        ["node", str(BENCHMARK_DIR / "filescan_node.js"), target],
    ]

    for cmd in peers:
        exe = cmd[0] if cmd[0] != "node" else cmd[1]
        if not Path(exe).exists():
            continue
        out = _run_peer(cmd)
        assert expected_line in out, f"Output mismatch for {cmd[0]}: got '{out}', expected '{expected_line}'"

def test_json_peers_parity():
    """All 5 JSON parsing peers must produce identical aggregation values."""
    iters = 1000
    expected_line = f"Done {iters} iterations: active=7000, age=234000, score=622000"

    peers = [
        [str(BENCHMARK_DIR / f"json_velo{EXT}"), str(iters)],
        [str(BENCHMARK_DIR / f"json_c{EXT}"), str(iters)],
        [str(BENCHMARK_DIR / f"json_rust{EXT}"), str(iters)],
        [str(BENCHMARK_DIR / f"json_go{EXT}"), str(iters)],
        ["node", str(BENCHMARK_DIR / "json_node.js"), str(iters)],
    ]

    for cmd in peers:
        exe = cmd[0] if cmd[0] != "node" else cmd[1]
        if not Path(exe).exists():
            continue
        out = _run_peer(cmd)
        assert expected_line in out, f"Output mismatch for {cmd[0]}: got '{out}', expected '{expected_line}'"

def _http_get(port: int, path: str) -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5.0)
    try:
        s.connect(("127.0.0.1", port))
        req = f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\n\r\n"
        s.sendall(req.encode("ascii"))
        chunks = []
        while True:
            data = s.recv(4096)
            if not data:
                break
            chunks.append(data)
        return b"".join(chunks).decode("utf-8", errors="replace")
    finally:
        s.close()

def _wait_for_port(port: int, timeout: float = 5.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return True
        except OSError:
            time.sleep(0.05)
    return False

def test_http_server_peers():
    """All 5 HTTP server peers must respond properly to /plaintext and /json."""
    base_port = 8092
    servers = [
        ("Velo", [str(BENCHMARK_DIR / f"server_velo{EXT}"), str(base_port)]),
        ("C", [str(BENCHMARK_DIR / f"server_c{EXT}"), str(base_port)]),
        ("Rust", [str(BENCHMARK_DIR / f"server_rust{EXT}"), str(base_port)]),
        ("Go", [str(BENCHMARK_DIR / f"server_go{EXT}"), str(base_port)]),
        ("Node", ["node", str(BENCHMARK_DIR / "server_node.js"), str(base_port)]),
    ]

    for name, cmd in servers:
        exe = cmd[0] if name != "Node" else cmd[1]
        if not Path(exe).exists():
            continue

        env = cc_env()
        env["PORT"] = str(base_port)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, cwd=str(BENCHMARK_DIR))
        try:
            ready = _wait_for_port(base_port, timeout=4.0)
            assert ready, f"Server {name} failed to bind on port {base_port}"

            # 1. Plaintext endpoint
            resp_plain = _http_get(base_port, "/plaintext")
            assert "200 OK" in resp_plain, f"{name} /plaintext missing 200 OK"
            assert "Hello, World!" in resp_plain, f"{name} /plaintext missing body"

            # 2. JSON endpoint
            resp_json = _http_get(base_port, "/json")
            assert "200 OK" in resp_json, f"{name} /json missing 200 OK"
            assert '{"message":"Hello, World!","status":"ok"}' in resp_json, f"{name} /json missing body"
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
            time.sleep(0.2)
