"""Tests for Native Self-Hosted Velo Language Server (Phase 3: Developer Experience & Tooling).

Verifies `velo lsp` stdio JSON-RPC 2.0 native binary:
1. Server Capabilities: completionProvider, renameProvider, codeActionProvider in initialize response.
2. Auto-Completion (textDocument/completion):
   - Global keywords, types, and top-level symbols
   - Builtin module member completions (io., mem., math., fs., etc.)
   - Custom struct field dot-completion (pt.x, pt.y)
   - Prefix filtering (pt.x vs pt.y)
   - Pointer parameter dot-completion (p: @Point -> p.)
3. Symbol Renaming:
   - textDocument/prepareRename on valid identifier returns accurate token range
   - textDocument/prepareRename on keyword/whitespace returns null
   - textDocument/rename on local variable produces accurate WorkspaceEdit updating all occurrences
4. Auto-Import Code Action (textDocument/codeAction):
   - Unimported namespace usage (e.g. io.println) offers QuickFix to add 'use std.io'
   - Clean code with imports already present returns empty actions
"""

import json
import subprocess
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
VELO_BIN = REPO_ROOT / "bin" / ("velo.exe" if sys.platform == "win32" else "velo")


def spawn_native_lsp():
    if not VELO_BIN.exists():
        pytest.skip(f"Compiler binary not found at {VELO_BIN}")
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


def test_native_lsp_phase3_capabilities():
    """Verify Phase 3 capabilities in initialize response."""
    proc = spawn_native_lsp()
    try:
        send_lsp_msg(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"processId": 1234, "capabilities": {}}
        })
        res = recv_lsp_msg(proc)
        assert res is not None
        caps = res["result"]["capabilities"]
        assert caps.get("completionProvider") == {"triggerCharacters": ["."], "resolveProvider": False}
        assert caps.get("renameProvider") == {"prepareProvider": True}
        assert caps.get("codeActionProvider") is True
    finally:
        send_lsp_msg(proc, {"jsonrpc": "2.0", "id": 2, "method": "shutdown"})
        recv_lsp_msg(proc)
        send_lsp_msg(proc, {"jsonrpc": "2.0", "method": "exit"})
        proc.wait(timeout=2)


def test_native_lsp_completion_globals_and_builtins():
    """Verify global completions and builtin module completions."""
    proc = spawn_native_lsp()
    uri = "file:///c:/projects/easylang/test_comp.vl"
    try:
        # Initialize
        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"processId": 1234, "capabilities": {}}
        })
        recv_lsp_msg(proc)

        # 1. Global completions
        code1 = "act main() {\n}\n"
        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "method": "textDocument/didOpen",
            "params": {"textDocument": {"uri": uri, "text": code1, "version": 1}}
        })
        # Discard published diagnostics notification
        recv_lsp_msg(proc)

        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "id": 10, "method": "textDocument/completion",
            "params": {"textDocument": {"uri": uri}, "position": {"line": 0, "character": 0}}
        })
        comp_res = recv_lsp_msg(proc)
        assert comp_res is not None
        labels = {item["label"] for item in comp_res["result"]}
        assert "act" in labels
        assert "data" in labels
        assert "fail" in labels
        assert "or" in labels
        assert "let" in labels
        assert "mut" in labels
        assert "i32" in labels
        assert "string" in labels

        # 2. Module dot completions: io.
        code_io = "act main() {\n    io.\n}\n"
        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "method": "textDocument/didChange",
            "params": {
                "textDocument": {"uri": uri, "version": 2},
                "contentChanges": [{"text": code_io}]
            }
        })
        recv_lsp_msg(proc)  # diagnostics

        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "id": 11, "method": "textDocument/completion",
            "params": {"textDocument": {"uri": uri}, "position": {"line": 1, "character": 7}}
        })
        res_io = recv_lsp_msg(proc)
        assert res_io is not None
        labels_io = {item["label"] for item in res_io["result"]}
        assert "print" in labels_io
        assert "println" in labels_io

        # 3. Module dot completions: mem.
        code_mem = "act main() {\n    mem.\n}\n"
        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "method": "textDocument/didChange",
            "params": {
                "textDocument": {"uri": uri, "version": 3},
                "contentChanges": [{"text": code_mem}]
            }
        })
        recv_lsp_msg(proc)  # diagnostics

        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "id": 12, "method": "textDocument/completion",
            "params": {"textDocument": {"uri": uri}, "position": {"line": 1, "character": 8}}
        })
        res_mem = recv_lsp_msg(proc)
        assert res_mem is not None
        labels_mem = {item["label"] for item in res_mem["result"]}
        assert "alloc" in labels_mem
        assert "free" in labels_mem
        assert "heap_alloc" in labels_mem

        # 4. Module dot completions: math.
        code_math = "act main() {\n    math.\n}\n"
        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "method": "textDocument/didChange",
            "params": {
                "textDocument": {"uri": uri, "version": 4},
                "contentChanges": [{"text": code_math}]
            }
        })
        recv_lsp_msg(proc)  # diagnostics

        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "id": 13, "method": "textDocument/completion",
            "params": {"textDocument": {"uri": uri}, "position": {"line": 1, "character": 9}}
        })
        res_math = recv_lsp_msg(proc)
        assert res_math is not None
        labels_math = {item["label"] for item in res_math["result"]}
        assert "sqrt" in labels_math
        assert "sin" in labels_math
        assert "clamp" in labels_math
        assert "PI" in labels_math
    finally:
        send_lsp_msg(proc, {"jsonrpc": "2.0", "id": 99, "method": "shutdown"})
        recv_lsp_msg(proc)
        send_lsp_msg(proc, {"jsonrpc": "2.0", "method": "exit"})
        proc.wait(timeout=2)


def test_native_lsp_completion_struct_fields():
    """Verify custom struct dot completions and prefix filtering."""
    proc = spawn_native_lsp()
    uri = "file:///c:/projects/easylang/test_struct_comp.vl"
    code = (
        "data Point {\n"
        "    x: f32\n"
        "    y: f32\n"
        "}\n"
        "act update(p: @Point) {\n"
        "    p.\n"
        "}\n"
        "act main() {\n"
        "    let pt = Point{ x: 1.0, y: 2.0 }\n"
        "    pt.\n"
        "    pt.x\n"
        "}\n"
    )
    try:
        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"processId": 1234, "capabilities": {}}
        })
        recv_lsp_msg(proc)

        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "method": "textDocument/didOpen",
            "params": {"textDocument": {"uri": uri, "text": code, "version": 1}}
        })
        recv_lsp_msg(proc)  # diagnostics

        # 1. Complete on local variable `pt.` (line 9, char 7)
        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "id": 20, "method": "textDocument/completion",
            "params": {"textDocument": {"uri": uri}, "position": {"line": 9, "character": 7}}
        })
        res_pt = recv_lsp_msg(proc)
        assert res_pt is not None
        items_pt = res_pt["result"]
        pt_labels = {item["label"] for item in items_pt}
        assert "x" in pt_labels
        assert "y" in pt_labels
        assert all(item["kind"] == 5 for item in items_pt)  # CompletionItemKind.Field

        # 2. Complete on pointer param `p.` (line 5, char 6)
        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "id": 21, "method": "textDocument/completion",
            "params": {"textDocument": {"uri": uri}, "position": {"line": 5, "character": 6}}
        })
        res_p = recv_lsp_msg(proc)
        assert res_p is not None
        p_labels = {item["label"] for item in res_p["result"]}
        assert "x" in p_labels
        assert "y" in p_labels

        # 3. Prefix filter on `pt.x` (line 10, char 8)
        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "id": 22, "method": "textDocument/completion",
            "params": {"textDocument": {"uri": uri}, "position": {"line": 10, "character": 8}}
        })
        res_filter = recv_lsp_msg(proc)
        assert res_filter is not None
        filter_labels = {item["label"] for item in res_filter["result"]}
        assert "x" in filter_labels
        assert "y" not in filter_labels
    finally:
        send_lsp_msg(proc, {"jsonrpc": "2.0", "id": 99, "method": "shutdown"})
        recv_lsp_msg(proc)
        send_lsp_msg(proc, {"jsonrpc": "2.0", "method": "exit"})
        proc.wait(timeout=2)


def test_native_lsp_rename():
    """Verify prepareRename and rename functionality."""
    proc = spawn_native_lsp()
    uri = "file:///c:/projects/easylang/test_rename.vl"
    code = (
        "act compute(val: i32) -> i32 {\n"
        "    mut total = val\n"
        "    total = total + 10\n"
        "    return total\n"
        "}\n"
    )
    try:
        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"processId": 1234, "capabilities": {}}
        })
        recv_lsp_msg(proc)

        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "method": "textDocument/didOpen",
            "params": {"textDocument": {"uri": uri, "text": code, "version": 1}}
        })
        recv_lsp_msg(proc)  # diagnostics

        # 1. prepareRename on variable `total` (line 1, char 9)
        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "id": 30, "method": "textDocument/prepareRename",
            "params": {"textDocument": {"uri": uri}, "position": {"line": 1, "character": 9}}
        })
        prep_res = recv_lsp_msg(proc)
        assert prep_res is not None
        assert prep_res["result"] == {"start": {"line": 1, "character": 8}, "end": {"line": 1, "character": 13}}

        # 2. prepareRename on keyword `mut` (line 1, char 5) -> returns null
        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "id": 31, "method": "textDocument/prepareRename",
            "params": {"textDocument": {"uri": uri}, "position": {"line": 1, "character": 5}}
        })
        prep_kw = recv_lsp_msg(proc)
        assert prep_kw is not None
        assert prep_kw["result"] is None

        # 3. Rename `total` to `sum`
        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "id": 32, "method": "textDocument/rename",
            "params": {
                "textDocument": {"uri": uri},
                "position": {"line": 1, "character": 9},
                "newName": "sum"
            }
        })
        rename_res = recv_lsp_msg(proc)
        assert rename_res is not None
        assert "changes" in rename_res["result"]
        edits = rename_res["result"]["changes"][uri]
        # `total` appears 4 times in compute() (1x decl, 2x line 2 assign+add, 1x return)
        assert len(edits) == 4
        for e in edits:
            assert e["newText"] == "sum"
            assert e["range"]["end"]["character"] - e["range"]["start"]["character"] == 5
    finally:
        send_lsp_msg(proc, {"jsonrpc": "2.0", "id": 99, "method": "shutdown"})
        recv_lsp_msg(proc)
        send_lsp_msg(proc, {"jsonrpc": "2.0", "method": "exit"})
        proc.wait(timeout=2)


def test_native_lsp_code_action_auto_import():
    """Verify auto-import QuickFix codeAction suggestions."""
    proc = spawn_native_lsp()
    uri = "file:///c:/projects/easylang/test_action.vl"
    code_missing = (
        "act main() {\n"
        "    io.println(\"hello world\")\n"
        "}\n"
    )
    code_imported = (
        "use std.io\n"
        "act main() {\n"
        "    io.println(\"hello world\")\n"
        "}\n"
    )
    try:
        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"processId": 1234, "capabilities": {}}
        })
        recv_lsp_msg(proc)

        # 1. Missing import -> suggests QuickFix 'use std.io'
        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "method": "textDocument/didOpen",
            "params": {"textDocument": {"uri": uri, "text": code_missing, "version": 1}}
        })
        recv_lsp_msg(proc)  # diagnostics

        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "id": 40, "method": "textDocument/codeAction",
            "params": {
                "textDocument": {"uri": uri},
                "range": {"start": {"line": 1, "character": 4}, "end": {"line": 1, "character": 14}},
                "context": {"diagnostics": []}
            }
        })
        action_res = recv_lsp_msg(proc)
        assert action_res is not None
        actions = action_res["result"]
        assert len(actions) == 1
        act = actions[0]
        assert act["title"] == "Add 'use std.io'"
        assert act["kind"] == "quickfix"
        edit = act["edit"]["changes"][uri][0]
        assert edit["newText"] == "use std.io\n"
        assert edit["range"] == {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}}

        # 2. Already imported -> returns empty actions
        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "method": "textDocument/didChange",
            "params": {
                "textDocument": {"uri": uri, "version": 2},
                "contentChanges": [{"text": code_imported}]
            }
        })
        recv_lsp_msg(proc)  # diagnostics

        send_lsp_msg(proc, {
            "jsonrpc": "2.0", "id": 41, "method": "textDocument/codeAction",
            "params": {
                "textDocument": {"uri": uri},
                "range": {"start": {"line": 2, "character": 4}, "end": {"line": 2, "character": 14}},
                "context": {"diagnostics": []}
            }
        })
        clean_res = recv_lsp_msg(proc)
        assert clean_res is not None
        assert clean_res["result"] == []
    finally:
        send_lsp_msg(proc, {"jsonrpc": "2.0", "id": 99, "method": "shutdown"})
        recv_lsp_msg(proc)
        send_lsp_msg(proc, {"jsonrpc": "2.0", "method": "exit"})
        proc.wait(timeout=2)

