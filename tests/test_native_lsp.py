"""Tests for Native Self-Hosted Velo Language Server (Phase 2, Task 2.1 & 2.2).

Verifies `velo lsp` stdio JSON-RPC 2.0 native binary:
1. Protocol framing: Content-Length header parsing and emission.
2. Lifecycle: initialize -> initialized -> shutdown -> exit.
3. Document Synchronization: textDocument/didOpen, didChange, didClose, didSave.
4. Live In-Memory Diagnostics (Zero Disk I/O):
   - Syntax error reporting on unsaved buffers
   - Semantic type-check error reporting
   - Diagnostic clearance upon fixing errors
   - Empty diagnostics publication on didClose
5. Unknown method error handling (JSON-RPC error -32601).
6. Clean shutdown and EOF exit handling.
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
    """Verify textDocument/didOpen, didChange, didSave, and didClose sync without errors."""
    proc = spawn_native_lsp()

    # Initialize
    send_lsp_msg(proc, {"jsonrpc": "2.0", "id": 100, "method": "initialize", "params": {}})
    init_res = recv_lsp_msg(proc)
    assert init_res["id"] == 100

    uri = "file:///sample.vl"
    code_v1 = "act main() -> i32 { return 42 }\n"

    # didOpen -> server publishes diagnostics (empty for clean code)
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
    diag_open = recv_lsp_msg(proc)
    assert diag_open["method"] == "textDocument/publishDiagnostics"
    assert diag_open["params"]["uri"] == uri
    assert diag_open["params"]["diagnostics"] == []

    # didChange (Full text sync) -> server publishes diagnostics
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
    diag_change = recv_lsp_msg(proc)
    assert diag_change["method"] == "textDocument/publishDiagnostics"
    assert diag_change["params"]["uri"] == uri
    assert diag_change["params"]["diagnostics"] == []

    # didSave -> server publishes diagnostics
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "method": "textDocument/didSave",
        "params": {
            "textDocument": {"uri": uri}
        }
    })
    diag_save = recv_lsp_msg(proc)
    assert diag_save["method"] == "textDocument/publishDiagnostics"
    assert diag_save["params"]["uri"] == uri

    # didClose -> server publishes empty diagnostics
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "method": "textDocument/didClose",
        "params": {
            "textDocument": {"uri": uri}
        }
    })
    diag_close = recv_lsp_msg(proc)
    assert diag_close["method"] == "textDocument/publishDiagnostics"
    assert diag_close["params"]["diagnostics"] == []

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


def test_native_lsp_live_diagnostics():
    """Verify live in-memory diagnostics for syntax errors, type errors, and error clearing."""
    proc = spawn_native_lsp()

    # Initialize
    send_lsp_msg(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    init_res = recv_lsp_msg(proc)
    assert init_res["id"] == 1

    uri = "file:///in_memory_test.vl"

    # 1. didOpen with syntax error (trailing + without operand)
    broken_syntax = "act main() -> i32 {\n    let x = 10 +\n    return 0\n}\n"
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "method": "textDocument/didOpen",
        "params": {
            "textDocument": {
                "uri": uri,
                "languageId": "velo",
                "version": 1,
                "text": broken_syntax
            }
        }
    })
    diag_res1 = recv_lsp_msg(proc)
    assert diag_res1["method"] == "textDocument/publishDiagnostics"
    assert diag_res1["params"]["uri"] == uri
    diags1 = diag_res1["params"]["diagnostics"]
    assert len(diags1) > 0, "Expected syntax error diagnostic on broken code"
    d1 = diags1[0]
    assert d1["severity"] == 1
    assert d1["source"] == "velo"
    assert d1["range"]["start"]["line"] >= 0

    # 2. didChange with semantic type error (string assigned to i32)
    broken_type = "act main() -> i32 {\n    let x: i32 = \"not an int\"\n    return x\n}\n"
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "method": "textDocument/didChange",
        "params": {
            "textDocument": {
                "uri": uri,
                "version": 2
            },
            "contentChanges": [
                {"text": broken_type}
            ]
        }
    })
    diag_res2 = recv_lsp_msg(proc)
    assert diag_res2["method"] == "textDocument/publishDiagnostics"
    diags2 = diag_res2["params"]["diagnostics"]
    assert len(diags2) > 0, "Expected semantic type error diagnostic"
    d2 = diags2[0]
    assert d2["severity"] == 1
    assert "Type mismatch" in d2["message"]

    # 3. didChange fixing the error
    clean_code = "act main() -> i32 {\n    let x: i32 = 42\n    return x\n}\n"
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "method": "textDocument/didChange",
        "params": {
            "textDocument": {
                "uri": uri,
                "version": 3
            },
            "contentChanges": [
                {"text": clean_code}
            ]
        }
    })
    diag_res3 = recv_lsp_msg(proc)
    assert diag_res3["method"] == "textDocument/publishDiagnostics"
    assert diag_res3["params"]["diagnostics"] == [], "Expected zero diagnostics on clean code"

    # 4. didClose clears diagnostics
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "method": "textDocument/didClose",
        "params": {
            "textDocument": {"uri": uri}
        }
    })
    diag_res4 = recv_lsp_msg(proc)
    assert diag_res4["method"] == "textDocument/publishDiagnostics"
    assert diag_res4["params"]["diagnostics"] == []

    # Shutdown and exit
    send_lsp_msg(proc, {"jsonrpc": "2.0", "id": 2, "method": "shutdown"})
    recv_lsp_msg(proc)
    send_lsp_msg(proc, {"jsonrpc": "2.0", "method": "exit"})
    proc.stdin.close()
    proc.wait(timeout=5)
    assert proc.returncode == 0


def test_native_lsp_document_symbols():
    """Verify hierarchical document symbols for structs, enums, type aliases, and functions."""
    proc = spawn_native_lsp()

    # 1. Initialize
    send_lsp_msg(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    init_res = recv_lsp_msg(proc)
    assert init_res["id"] == 1
    caps = init_res["result"].get("capabilities", {})
    assert caps.get("documentSymbolProvider") is True

    code = """data Vector3 {
    x: f64
    y: f64
    z: f64 = 0.0
}

kind Color {
    Red
    Green
    Blue
}

aka VecAlias = Vector3

act add_vectors(a: Vector3, b: Vector3) -> Vector3 {
    return Vector3 { x: a.x + b.x, y: a.y + b.y, z: a.z + b.z }
}

extern act c_puts(s: string) -> i32
"""
    uri = "file:///symbols_test.vl"

    # 2. didOpen -> consume diagnostics
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "method": "textDocument/didOpen",
        "params": {
            "textDocument": {
                "uri": uri,
                "languageId": "velo",
                "version": 1,
                "text": code
            }
        }
    })
    diag = recv_lsp_msg(proc)
    assert diag["method"] == "textDocument/publishDiagnostics"

    # 3. documentSymbol request
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "textDocument/documentSymbol",
        "params": {
            "textDocument": {"uri": uri}
        }
    })
    sym_res = recv_lsp_msg(proc)
    assert sym_res["id"] == 2
    symbols = sym_res["result"]
    assert len(symbols) == 5, f"Expected 5 symbols, got {len(symbols)}"

    # Struct: Vector3
    s_vec = next((s for s in symbols if s["name"] == "Vector3"), None)
    assert s_vec is not None
    assert s_vec["kind"] == 23
    assert s_vec["detail"] == "data"
    assert len(s_vec["children"]) == 3
    assert s_vec["children"][0]["name"] == "x: f64"
    assert s_vec["children"][0]["kind"] == 8

    # Enum: Color
    s_color = next((s for s in symbols if s["name"] == "Color"), None)
    assert s_color is not None
    assert s_color["kind"] == 10
    assert s_color["detail"] == "kind"
    assert len(s_color["children"]) == 3
    assert s_color["children"][0]["name"] == "Red"
    assert s_color["children"][0]["kind"] == 22

    # Type alias: VecAlias
    s_alias = next((s for s in symbols if "VecAlias" in s["name"]), None)
    assert s_alias is not None
    assert s_alias["kind"] == 26
    assert s_alias["name"] == "aka VecAlias = Vector3"

    # Act: add_vectors
    s_act = next((s for s in symbols if s["name"].startswith("add_vectors(")), None)
    assert s_act is not None
    assert s_act["kind"] == 12
    assert s_act["name"] == "add_vectors(a: Vector3, b: Vector3) -> Vector3"

    # Extern: c_puts
    s_ext = next((s for s in symbols if s["name"] == "c_puts"), None)
    assert s_ext is not None
    assert s_ext["kind"] == 12
    assert s_ext["detail"] == "extern"

    # 4. Unknown document returns empty array
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "textDocument/documentSymbol",
        "params": {
            "textDocument": {"uri": "file:///non_existent_file.vl"}
        }
    })
    empty_res = recv_lsp_msg(proc)
    assert empty_res["id"] == 3
    assert empty_res["result"] == []

    # 5. Shutdown and exit
    send_lsp_msg(proc, {"jsonrpc": "2.0", "id": 4, "method": "shutdown"})
    recv_lsp_msg(proc)
    send_lsp_msg(proc, {"jsonrpc": "2.0", "method": "exit"})
    proc.stdin.close()
    proc.wait(timeout=5)
    assert proc.returncode == 0


def test_native_lsp_hover():
    """Verify rich Markdown hover for functions, locals, parameters, and structs."""
    proc = spawn_native_lsp()

    # 1. Initialize
    send_lsp_msg(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    init_res = recv_lsp_msg(proc)
    assert init_res["id"] == 1
    caps = init_res["result"].get("capabilities", {})
    assert caps.get("hoverProvider") is True

    code = """data Point {
    x: i32
    y: i32
}

aka PointRef = Point

act create_point(px: i32, py: i32) -> Point {
    return Point { x: px, y: py }
}

act main() -> i32 {
    let p: Point = create_point(10, 20)
    return 0
}
"""
    uri = "file:///hover_test.vl"

    # 2. didOpen
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "method": "textDocument/didOpen",
        "params": {
            "textDocument": {
                "uri": uri,
                "languageId": "velo",
                "version": 1,
                "text": code
            }
        }
    })
    diag = recv_lsp_msg(proc)
    assert diag["method"] == "textDocument/publishDiagnostics"

    # 3. Hover on act call: create_point on line 12 (0-based)
    # "    let p: Point = create_point(10, 20)" -> create_point starts at char 19
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "textDocument/hover",
        "params": {
            "textDocument": {"uri": uri},
            "position": {"line": 12, "character": 22}
        }
    })
    h_act = recv_lsp_msg(proc)
    assert h_act["id"] == 2
    assert h_act["result"] is not None
    val_act = h_act["result"]["contents"]["value"]
    assert "create_point(px: i32, py: i32) -> Point" in val_act
    assert "hover_test.vl:8" in val_act

    # 4. Hover on local variable: p on line 12 (character 8)
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "textDocument/hover",
        "params": {
            "textDocument": {"uri": uri},
            "position": {"line": 12, "character": 8}
        }
    })
    h_local = recv_lsp_msg(proc)
    assert h_local["id"] == 3
    assert h_local["result"] is not None
    val_local = h_local["result"]["contents"]["value"]
    assert "local **p**: Point" in val_local

    # 5. Hover on act parameter: px on line 9 (character 21 in "return Point { x: px, y: py }")
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "textDocument/hover",
        "params": {
            "textDocument": {"uri": uri},
            "position": {"line": 8, "character": 22}
        }
    })
    h_param = recv_lsp_msg(proc)
    assert h_param["id"] == 4
    assert h_param["result"] is not None
    val_param = h_param["result"]["contents"]["value"]
    assert "param **px**: i32" in val_param

    # 6. Hover on struct name: Point on line 0 (character 6 in "data Point {")
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "textDocument/hover",
        "params": {
            "textDocument": {"uri": uri},
            "position": {"line": 0, "character": 6}
        }
    })
    h_struct = recv_lsp_msg(proc)
    assert h_struct["id"] == 5
    assert h_struct["result"] is not None
    val_struct = h_struct["result"]["contents"]["value"]
    assert "**data** `Point`" in val_struct
    assert "x: i32" in val_struct

    # 7. Hover on whitespace -> returns null
    send_lsp_msg(proc, {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "textDocument/hover",
        "params": {
            "textDocument": {"uri": uri},
            "position": {"line": 1, "character": 0}
        }
    })
    h_null = recv_lsp_msg(proc)
    assert h_null["id"] == 6
    assert h_null["result"] is None

    # 8. Shutdown and exit
    send_lsp_msg(proc, {"jsonrpc": "2.0", "id": 7, "method": "shutdown"})
    recv_lsp_msg(proc)
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
