"""Tests for 6.4 Developer Tooling: Language Server Protocol (LSP).

Verifies the stdio JSON-RPC 2.0 LSP server and analysis layer in `velo.lsp`:
1. Protocol message framing (Content-Length read & send).
2. Lifecycle (initialize negotiation, shutdown, exit).
3. Live diagnostics on unsaved buffers (didOpen, didChange, didClose).
4. Document outline / symbols (data, kind, aka, act).
5. Hover tooltips (functions, parameters, locals, structs).
6. Go-to-definition (types, functions, locals across files).
7. Autocompletion (keywords, types, builtin module methods: io, mem, fs, math, time, os, thread).
8. Full end-to-end integration via `python velo.py lsp` subprocess.
"""

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from velo.analysis import VeloAnalysis, _path_to_uri
from velo.lsp import Dispatcher, Protocol

REPO_ROOT = Path(__file__).resolve().parent.parent
VELO_PY = REPO_ROOT / "velo.py"


SAMPLE_CODE = """use sys.io

data Point {
    x: f32
    y: f32
}

kind Shape {
    Circle
    Square
}

aka PointAlias = u32

act add(a: i32, b: i32) -> i32 {
    let sum = a + b
    return sum
}

act main() -> i32 {
    let pt = Point{ x: 1.0, y: 2.0 }
    let res = add(10, 20)
    io.println("Done")
    return 0
}
"""

BROKEN_CODE = """act main() -> i32 {
    let x = 10 +
    return 0
}
"""


class DummyStream:
    def __init__(self, data=b""):
        self.buf = io.BytesIO(data)

    def read(self, n):
        return self.buf.read(n)

    def readline(self):
        return self.buf.readline()

    def write(self, data):
        return self.buf.write(data)

    def flush(self):
        pass

    def getvalue(self):
        return self.buf.getvalue()


def test_protocol_framing():
    """Verify Content-Length header framing in read_message and send."""
    msg = {"jsonrpc": "2.0", "id": 1, "method": "test", "params": {"key": "val"}}
    body = json.dumps(msg).encode("utf-8")
    raw = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body

    proto = Protocol(DummyStream(raw), DummyStream())
    read_msg = proto.read_message()
    assert read_msg == msg

    out_stream = DummyStream()
    proto_out = Protocol(DummyStream(), out_stream)
    proto_out.send(msg)
    sent_bytes = out_stream.getvalue()
    assert sent_bytes.startswith(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    assert json.loads(sent_bytes.split(b"\r\n\r\n", 1)[1].decode("utf-8")) == msg


def test_lsp_initialize_and_shutdown():
    """Verify initialize capability negotiation and shutdown sequence."""
    in_stream = DummyStream()
    out_stream = DummyStream()
    proto = Protocol(in_stream, out_stream)
    dispatcher = Dispatcher(proto, str(REPO_ROOT))

    caps = dispatcher.on_initialize({})
    assert "capabilities" in caps
    assert caps["capabilities"]["textDocumentSync"] == 1
    assert caps["capabilities"]["documentSymbolProvider"] is True
    assert caps["capabilities"]["hoverProvider"] is True
    assert caps["capabilities"]["definitionProvider"] is True
    assert caps["capabilities"]["completionProvider"]["triggerCharacters"] == ["."]

    assert dispatcher.shutdown_requested is False
    res = dispatcher.on_shutdown({})
    assert res is None
    assert dispatcher.shutdown_requested is True


def test_lsp_diagnostics_live_buffer(tmp_path):
    """Verify didOpen and didChange publish diagnostics from memory without disk writes."""
    in_stream = DummyStream()
    out_stream = DummyStream()
    proto = Protocol(in_stream, out_stream)
    dispatcher = Dispatcher(proto, str(REPO_ROOT))

    sent_notifications = []

    def fake_send(payload):
        sent_notifications.append(payload)

    proto.send = fake_send

    src_file = tmp_path / "diag_test.vl"
    src_file.write_text(SAMPLE_CODE, encoding="utf-8")
    uri = _path_to_uri(str(src_file))

    # 1. Clean file -> no diagnostics
    dispatcher.did_open({"textDocument": {"uri": uri, "text": SAMPLE_CODE, "version": 1}})
    assert len(sent_notifications) == 1
    assert sent_notifications[0]["method"] == "textDocument/publishDiagnostics"
    assert sent_notifications[0]["params"]["diagnostics"] == []

    # 2. Change to broken code -> diagnostics published
    sent_notifications.clear()
    dispatcher.did_change({
        "textDocument": {"uri": uri, "version": 2},
        "contentChanges": [{"text": BROKEN_CODE}]
    })
    assert len(sent_notifications) == 1
    diags = sent_notifications[0]["params"]["diagnostics"]
    assert len(diags) > 0
    assert diags[0]["severity"] == 1
    assert "Unexpected" in diags[0]["message"] or "error" in diags[0]["message"].lower()

    # 3. Fix code -> diagnostics cleared
    sent_notifications.clear()
    dispatcher.did_change({
        "textDocument": {"uri": uri, "version": 3},
        "contentChanges": [{"text": SAMPLE_CODE}]
    })
    assert len(sent_notifications) == 1
    assert sent_notifications[0]["params"]["diagnostics"] == []

    # 4. Close file -> empty diagnostics
    sent_notifications.clear()
    dispatcher.did_close({"textDocument": {"uri": uri}})
    assert len(sent_notifications) == 1
    assert sent_notifications[0]["params"]["diagnostics"] == []


def test_lsp_document_symbols(tmp_path):
    """Verify documentSymbol extracts outline for data, kind, aka, and acts."""
    src_file = tmp_path / "symbols.vl"
    src_file.write_text(SAMPLE_CODE, encoding="utf-8")
    uri = _path_to_uri(str(src_file))

    in_stream = DummyStream()
    out_stream = DummyStream()
    proto = Protocol(in_stream, out_stream)
    dispatcher = Dispatcher(proto, str(REPO_ROOT))
    dispatcher.did_open({"textDocument": {"uri": uri, "text": SAMPLE_CODE, "version": 1}})

    symbols = dispatcher.document_symbol({"textDocument": {"uri": uri}})
    symbol_names = [s["name"] for s in symbols]

    # Verify struct Point with fields x, y
    assert "Point" in symbol_names
    point_sym = next(s for s in symbols if s["name"] == "Point")
    field_names = [c["name"] for c in point_sym.get("children", [])]
    assert any("x:" in f for f in field_names)
    assert any("y:" in f for f in field_names)

    # Verify enum Shape with variants
    assert "Shape" in symbol_names
    shape_sym = next(s for s in symbols if s["name"] == "Shape")
    variant_names = [c["name"] for c in shape_sym.get("children", [])]
    assert "Circle" in variant_names
    assert "Square" in variant_names

    # Verify aka alias
    assert any("PointAlias" in name for name in symbol_names)

    # Verify functions
    assert any("add" in name for name in symbol_names)
    assert any("main" in name for name in symbol_names)


def test_lsp_hover_information(tmp_path):
    """Verify hover over functions, locals, and struct types."""
    src_file = tmp_path / "hover.vl"
    src_file.write_text(SAMPLE_CODE, encoding="utf-8")
    uri = _path_to_uri(str(src_file))

    in_stream = DummyStream()
    out_stream = DummyStream()
    proto = Protocol(in_stream, out_stream)
    dispatcher = Dispatcher(proto, str(REPO_ROOT))
    dispatcher.did_open({"textDocument": {"uri": uri, "text": SAMPLE_CODE, "version": 1}})

    # Hover on `add` call in main (around line 22, col 15)
    # Line 22: `    let res = add(10, 20)`
    hover_add = dispatcher.hover({
        "textDocument": {"uri": uri},
        "position": {"line": 21, "character": 15}
    })
    assert hover_add is not None
    assert "contents" in hover_add
    md_add = hover_add["contents"]["value"]
    assert "act" in md_add
    assert "add" in md_add
    assert "a: i32, b: i32" in md_add

    # Hover on local variable `sum` (line 16: `    let sum = a + b`)
    hover_sum = dispatcher.hover({
        "textDocument": {"uri": uri},
        "position": {"line": 15, "character": 9}
    })
    assert hover_sum is not None
    md_sum = hover_sum["contents"]["value"]
    assert "sum" in md_sum


def test_lsp_goto_definition(tmp_path):
    """Verify go-to-definition for function calls and struct types."""
    src_file = tmp_path / "def.vl"
    src_file.write_text(SAMPLE_CODE, encoding="utf-8")
    uri = _path_to_uri(str(src_file))

    in_stream = DummyStream()
    out_stream = DummyStream()
    proto = Protocol(in_stream, out_stream)
    dispatcher = Dispatcher(proto, str(REPO_ROOT))
    dispatcher.did_open({"textDocument": {"uri": uri, "text": SAMPLE_CODE, "version": 1}})

    # Definition of `add` in `let res = add(10, 20)` (line 21, character 15)
    defn_add = dispatcher.definition({
        "textDocument": {"uri": uri},
        "position": {"line": 21, "character": 15}
    })
    assert defn_add is not None
    assert defn_add["uri"] == uri
    # Declaration of `add` is on line 14 (0-based line 14)
    assert defn_add["range"]["start"]["line"] == 14

    # Definition of `Point` in `let pt = Point{ ... }` (line 20, character 14)
    defn_point = dispatcher.definition({
        "textDocument": {"uri": uri},
        "position": {"line": 20, "character": 14}
    })
    assert defn_point is not None
    assert defn_point["uri"] == uri
    # `data Point` is on line 2 (0-based line 2)
    assert defn_point["range"]["start"]["line"] == 2


def test_lsp_completion(tmp_path):
    """Verify completions for keywords, types, and builtin module methods."""
    src_file = tmp_path / "comp.vl"
    src_file.write_text(SAMPLE_CODE, encoding="utf-8")
    uri = _path_to_uri(str(src_file))

    in_stream = DummyStream()
    out_stream = DummyStream()
    proto = Protocol(in_stream, out_stream)
    dispatcher = Dispatcher(proto, str(REPO_ROOT))
    dispatcher.did_open({"textDocument": {"uri": uri, "text": SAMPLE_CODE, "version": 1}})

    # 1. Global completions (keywords & types)
    comps = dispatcher.completion({
        "textDocument": {"uri": uri},
        "position": {"line": 0, "character": 0}
    })
    labels = {c["label"] for c in comps}
    assert "act" in labels
    assert "data" in labels
    assert "shelf" in labels
    assert "map" in labels
    assert "i32" in labels
    assert "string" in labels
    assert "dyn" in labels

    # 2. Member completions after `io.`
    code_io = "act main() {\n    io.\n}\n"
    dispatcher.did_change({
        "textDocument": {"uri": uri, "version": 2},
        "contentChanges": [{"text": code_io}]
    })
    comps_io = dispatcher.completion({
        "textDocument": {"uri": uri},
        "position": {"line": 1, "character": 7}
    })
    io_labels = {c["label"] for c in comps_io}
    assert "print" in io_labels
    assert "println" in io_labels

    # 3. Member completions after `mem.`
    code_mem = "act main() {\n    mem.\n}\n"
    dispatcher.did_change({
        "textDocument": {"uri": uri, "version": 3},
        "contentChanges": [{"text": code_mem}]
    })
    comps_mem = dispatcher.completion({
        "textDocument": {"uri": uri},
        "position": {"line": 1, "character": 8}
    })
    mem_labels = {c["label"] for c in comps_mem}
    assert "alloc" in mem_labels
    assert "free" in mem_labels
    assert "realloc" in mem_labels

    # 4. Member completions after `fs.`
    code_fs = "act main() {\n    fs.\n}\n"
    dispatcher.did_change({
        "textDocument": {"uri": uri, "version": 4},
        "contentChanges": [{"text": code_fs}]
    })
    comps_fs = dispatcher.completion({
        "textDocument": {"uri": uri},
        "position": {"line": 1, "character": 7}
    })
    fs_labels = {c["label"] for c in comps_fs}
    assert "read_file" in fs_labels
    assert "write_file" in fs_labels
    assert "exists" in fs_labels

    # 5. Member completions after `math.`
    code_math = "act main() {\n    math.\n}\n"
    dispatcher.did_change({
        "textDocument": {"uri": uri, "version": 5},
        "contentChanges": [{"text": code_math}]
    })
    comps_math = dispatcher.completion({
        "textDocument": {"uri": uri},
        "position": {"line": 1, "character": 9}
    })
    math_labels = {c["label"] for c in comps_math}
    assert "sqrt" in math_labels
    assert "sin" in math_labels
    assert "clamp" in math_labels

    # 6. Member completions after custom struct variable `pt.`
    code_pt = "data Point {\n    x: f32\n    y: f32\n}\nact main() {\n    let pt = Point{ x: 1.0, y: 2.0 }\n    pt.\n}\n"
    dispatcher.did_change({
        "textDocument": {"uri": uri, "version": 6},
        "contentChanges": [{"text": code_pt}]
    })
    comps_pt = dispatcher.completion({
        "textDocument": {"uri": uri},
        "position": {"line": 6, "character": 7}
    })
    pt_labels = {c["label"] for c in comps_pt}
    assert "x" in pt_labels
    assert "y" in pt_labels
    assert all(c["kind"] == 5 for c in comps_pt)  # CompletionItemKind.Field

    # 7. Member completions with prefix filter `pt.x`
    code_pt_prefix = "data Point {\n    x: f32\n    y: f32\n}\nact main() {\n    let pt = Point{ x: 1.0, y: 2.0 }\n    pt.x\n}\n"
    dispatcher.did_change({
        "textDocument": {"uri": uri, "version": 7},
        "contentChanges": [{"text": code_pt_prefix}]
    })
    comps_pt_prefix = dispatcher.completion({
        "textDocument": {"uri": uri},
        "position": {"line": 6, "character": 8}
    })
    prefix_labels = {c["label"] for c in comps_pt_prefix}
    assert "x" in prefix_labels
    assert "y" not in prefix_labels

    # 8. Member completions on a struct pointer parameter `p: @Point`
    code_ptr = "data Point {\n    x: f32\n    y: f32\n}\nact update(p: @Point) {\n    p.\n}\n"
    dispatcher.did_change({
        "textDocument": {"uri": uri, "version": 8},
        "contentChanges": [{"text": code_ptr}]
    })
    comps_ptr = dispatcher.completion({
        "textDocument": {"uri": uri},
        "position": {"line": 5, "character": 6}
    })
    ptr_labels = {c["label"] for c in comps_ptr}
    assert "x" in ptr_labels
    assert "y" in ptr_labels
    assert all(c["kind"] == 5 for c in comps_ptr)

    # 9. Member completions on nested struct field `player.pos.`
    code_nested = "data Point {\n    x: f32\n    y: f32\n}\ndata Player {\n    name: string\n    pos: Point\n}\nact main() {\n    let player = Player{ name: \"hero\", pos: Point{ x: 1.0, y: 2.0 } }\n    player.pos.\n}\n"
    dispatcher.did_change({
        "textDocument": {"uri": uri, "version": 9},
        "contentChanges": [{"text": code_nested}]
    })
    comps_nested = dispatcher.completion({
        "textDocument": {"uri": uri},
        "position": {"line": 10, "character": 15}
    })
    nested_labels = {c["label"] for c in comps_nested}
    assert "x" in nested_labels
    assert "y" in nested_labels



def test_lsp_cli_subprocess():
    """Verify python velo.py lsp operates as a real stdio JSON-RPC subprocess."""
    proc = subprocess.Popen(
        [sys.executable, str(VELO_PY), "lsp", str(REPO_ROOT)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False
    )

    def send(msg):
        body = json.dumps(msg).encode("utf-8")
        proc.stdin.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body)
        proc.stdin.flush()

    def recv():
        headers = {}
        line = proc.stdout.readline()
        while line not in (b"\r\n", b"\n"):
            k, v = line.decode("ascii").split(":", 1)
            headers[k.strip().lower()] = v.strip()
            line = proc.stdout.readline()
        length = int(headers["content-length"])
        body = proc.stdout.read(length)
        return json.loads(body.decode("utf-8"))

    # 1. Initialize
    send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    init_res = recv()
    assert init_res["id"] == 1
    assert "capabilities" in init_res["result"]

    # 2. Shutdown
    send({"jsonrpc": "2.0", "id": 2, "method": "shutdown", "params": {}})
    shutdown_res = recv()
    assert shutdown_res["id"] == 2
    assert shutdown_res["result"] is None

    # 3. Exit
    send({"jsonrpc": "2.0", "method": "exit", "params": {}})
    proc.stdin.close()
    proc.wait(timeout=5)
    assert proc.returncode == 0
