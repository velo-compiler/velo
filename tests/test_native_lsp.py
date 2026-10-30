"""Tests for Native Self-Hosted Velo Language Server (Phase 2, Task 2.1).

Verifies `velo lsp` stdio JSON-RPC 2.0 native binary:
1. Protocol framing: Content-Length header parsing and emission.
2. Lifecycle: initialize -> initialized -> shutdown -> exit.
3. Document Synchronization: textDocument/didOpen, didChange, didClose, didSave.
4. Unknown method error handling (JSON-RPC error -32601).
5. Clean shutdown and EOF exit handling.
"""

import json
import subprocess
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
VELO_BIN = REPO_ROOT / "bin" / ("velo.exe" if sys.platform == "win32" else "velo")


def spawn_native_lsp():
    assert VELO_BIN.exists(), f"Compiler binary not found at {VELO_BIN}"
    return subprocess.Popen(
        [str(VELO_BIN), "lsp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False
    )


def send_lsp_msg(proc, msg):
    body = json.dumps(msg).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    proc.stdin.write(header + body)
    proc.stdin.flush()


def recv_lsp_msg(proc, timeout=5):
    headers = {}
    line = proc.stdout.readline()
    while line not in (b"\r\n", b"\n"):
        if not line:
            return None
        decoded = line.decode("ascii", errors="replace")
        if ":" in decoded:
            k, v = decoded.split(":", 1)
            headers[k.strip().lower()] = v.strip()
        line = proc.stdout.readline()
    if "content-length" not in headers:
        return None
    length = int(headers["content-length"])
    body = proc.stdout.read(length)
    return json.loads(body.decode("utf-8"))


def test_native_lsp_lifecycle():
    """Verify initialize -> initialized -> shutdown -> exit lifecycle."""
    proc = spawn_native_lsp()

    # 1. Initialize
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "processId": 1234,
            "rootUri": "file:///c:/projects/easylang",
            "capabilities": {}
        }
    })
    init_res = recv_lsp_msg(proc)
    assert init_res is not None
    assert init_res.get("jsonrpc") == "2.0"
    assert init_res.get("id") == 1
    assert "result" in init_res
    caps = init_res["result"].get("capabilities", {})
    assert caps.get("textDocumentSync") == 1

    # 2. Initialized notification
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "method": "initialized",
        "params": {}
    })

    # 3. Shutdown request
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "shutdown"
    })
    shutdown_res = recv_lsp_msg(proc)
    assert shutdown_res is not None
    assert shutdown_res.get("id") == 2
    assert shutdown_res.get("result") is None

    # 4. Exit notification
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "method": "exit"
    })
    proc.stdin.close()
    proc.wait(timeout=5)
    assert proc.returncode == 0


def test_native_lsp_document_sync():
    """Verify textDocument/didOpen, didChange, and didClose sync without errors."""
    proc = spawn_native_lsp()

    # Initialize
    send_lsp_msg(proc, {"jsonrpc": "2.0", "id": 100, "method": "initialize", "params": {}})
    init_res = recv_lsp_msg(proc)
    assert init_res["id"] == 100

    uri = "file:///sample.vl"
    code_v1 = "act main() -> i32 { return 42 }\n"

    # didOpen
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "method": "textDocument/didOpen",
        "params": {
            "textDocument": {
                "uri": uri,
                "languageId": "velo",
                "version": 1,
                "text": code_v1
            }
        }
    })

    # didChange (Full text sync)
    code_v2 = "act main() -> i32 { return 100 }\n"
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "method": "textDocument/didChange",
        "params": {
            "textDocument": {
                "uri": uri,
                "version": 2
            },
            "contentChanges": [
                {"text": code_v2}
            ]
        }
    })

    # didSave
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "method": "textDocument/didSave",
        "params": {
            "textDocument": {"uri": uri}
        }
    })

    # didClose
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "method": "textDocument/didClose",
        "params": {
            "textDocument": {"uri": uri}
        }
    })

    # Unknown request
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "id": 101,
        "method": "unknown/customMethod",
        "params": {}
    })
    err_res = recv_lsp_msg(proc)
    assert err_res is not None
    assert err_res["id"] == 101
    assert "error" in err_res
    assert err_res["error"]["code"] == -32601

    # Shutdown and exit
    send_lsp_msg(proc, {"jsonrpc": "2.0", "id": 102, "method": "shutdown"})
    res = recv_lsp_msg(proc)
    assert res["id"] == 102

    send_lsp_msg(proc, {"jsonrpc": "2.0", "method": "exit"})
    proc.stdin.close()
    proc.wait(timeout=5)
    assert proc.returncode == 0


def test_native_lsp_eof_disconnect():
    """Verify server exits gracefully when client closes stdin pipe abruptly."""
    proc = spawn_native_lsp()

    send_lsp_msg(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    init_res = recv_lsp_msg(proc)
    assert init_res["id"] == 1

    # Abrupt disconnect
    proc.stdin.close()
    proc.wait(timeout=5)
    assert proc.returncode == 0

