#!/usr/bin/env python3
"""Velo Language Server Protocol (LSP) Server — stdio JSON-RPC 2.0.

Provides standard LSP 3.17 server capabilities for IDEs and editors:
- Diagnostics via live unsaved buffer compilation
- Document symbols (outline for data, kind, act, aka)
- Hover documentation and type signatures
- Go-to-definition across local declarations and imported modules
- Autocompletion for keywords, types, and builtin modules (io, mem, fs, etc.)

Can be started via:
- `velo lsp`
- `python -m velo.lsp`
- `python velo.py lsp`
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

from velo.analysis import VeloAnalysis, _uri_to_path

SERVER_VERSION = "0.5.0"

CAPABILITIES = {
    "capabilities": {
        "textDocumentSync": 1,
        "documentSymbolProvider": True,
        "hoverProvider": True,
        "definitionProvider": True,
        "completionProvider": {"resolveProvider": False, "triggerCharacters": ["."]},
    },
    "serverInfo": {"name": "velo-lsp", "version": SERVER_VERSION},
}


class Protocol:
    def __init__(self, in_stream, out_stream):
        self.in_stream = in_stream
        self.out_stream = out_stream

    def read_message(self):
        headers = {}
        line = self.in_stream.readline()
        if not line:
            return None
        while line not in (b"\r\n", b"\n"):
            try:
                key, value = line.decode("ascii").split(":", 1)
            except (ValueError, UnicodeDecodeError):
                return None
            headers[key.strip().lower()] = value.strip()
            line = self.in_stream.readline()
            if not line:
                return None
        length = headers.get("content-length")
        if length is None:
            return None
        body = self.in_stream.read(int(length))
        if len(body) < int(length):
            return None
        try:
            return json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            self.log(f"malformed JSON body: {exc}")
            return None

    def send(self, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        frame = (f"Content-Length: {len(body)}\r\n\r\n").encode("ascii") + body
        self.out_stream.write(frame)
        self.out_stream.flush()

    @staticmethod
    def log(message: str) -> None:
        sys.stderr.write(f"[velo-lsp] {message}\n")
        sys.stderr.flush()


class Dispatcher:
    """Single-threaded request/notification dispatch over one open workspace."""

    def __init__(self, protocol: Protocol, repo_root: Optional[str] = None):
        self.protocol = protocol
        self.repo_root = repo_root or str(Path(__file__).resolve().parent.parent)
        self.analysis = VeloAnalysis(self.repo_root)
        self.shutdown_requested = False

    def respond(self, request_id, result=None, error=None):
        reply = {"jsonrpc": "2.0", "id": request_id}
        if error is not None:
            reply["error"] = error
        else:
            reply["result"] = result
        self.protocol.send(reply)

    def notify(self, method: str, params) -> None:
        self.protocol.send({"jsonrpc": "2.0", "method": method, "params": params})

    def publish(self, uri: str) -> None:
        payload = self.analysis.diagnostics(uri)
        self.notify("textDocument/publishDiagnostics", payload)

    # -- Request handlers ---------------------------------------------------

    def on_initialize(self, params):
        return CAPABILITIES

    def on_shutdown(self, params):
        self.shutdown_requested = True
        return None

    def did_open(self, params):
        td = params["textDocument"]
        self.analysis.open(td["uri"], _uri_to_path(td["uri"]), td["text"], td.get("version", 0))
        self.publish(td["uri"])

    def did_change(self, params):
        td = params["textDocument"]
        changes = params.get("contentChanges") or []
        if not changes:
            return
        self.analysis.change(td["uri"], changes[-1]["text"], td.get("version", 0))
        self.publish(td["uri"])

    def did_close(self, params):
        uri = params["textDocument"]["uri"]
        self.analysis.close(uri)
        self.notify("textDocument/publishDiagnostics", {"uri": uri, "diagnostics": []})

    def document_symbol(self, params):
        uri = params["textDocument"]["uri"]
        return self.analysis.document_symbols(uri)

    def hover(self, params):
        uri = params["textDocument"]["uri"]
        pos = params["position"]
        return self.analysis.hover(uri, pos["line"], pos["character"])

    def definition(self, params):
        uri = params["textDocument"]["uri"]
        pos = params["position"]
        return self.analysis.definition(uri, pos["line"], pos["character"])

    def completion(self, params):
        uri = params["textDocument"]["uri"]
        pos = params["position"]
        return self.analysis.completions(uri, pos["line"], pos["character"])

    HANDLERS = {
        "initialize": on_initialize,
        "shutdown": on_shutdown,
        "textDocument/didOpen": did_open,
        "textDocument/didChange": did_change,
        "textDocument/didClose": did_close,
        "textDocument/documentSymbol": document_symbol,
        "textDocument/hover": hover,
        "textDocument/definition": definition,
        "textDocument/completion": completion,
    }

    def dispatch(self, message) -> bool:
        """Handle one message; returns False when the exit notification arrives."""
        method = message.get("method")
        if not method:
            return True
        Protocol.log(f"recv {method}")
        if method == "exit":
            return False
        handler = self.HANDLERS.get(method)
        if handler is None and "id" in message:
            self.respond(message["id"], error={"code": -32601, "message": f"unhandled: {method}"})
            return True
        if handler is None:
            return True
        try:
            result = handler(self, message.get("params") or {})
        except FileNotFoundError as exc:
            Protocol.log(f"{method}: {exc}")
            if "id" in message:
                self.respond(message["id"], error={"code": -32603, "message": str(exc)})
            return True
        except Exception as exc:
            Protocol.log(f"{method}: {type(exc).__name__}: {exc}")
            if "id" in message:
                self.respond(message["id"], error={"code": -32603, "message": str(exc)})
            return True
        if "id" in message:
            self.respond(message["id"], result)
        return True


def run_server(repo_root: Optional[str] = None) -> int:
    """Run the stdio LSP server main loop."""
    if repo_root is None:
        repo_root = os.environ.get("VELO_LSP_REPO")
    if repo_root is None:
        repo_root = str(Path(__file__).resolve().parent.parent)

    protocol = Protocol(sys.stdin.buffer, sys.stdout.buffer)
    dispatcher = Dispatcher(protocol, repo_root)
    Protocol.log(f"starting velo-lsp {SERVER_VERSION} (repo: {repo_root})")
    while True:
        message = protocol.read_message()
        if message is None:
            Protocol.log("stdin closed; exiting")
            return 0
        if not dispatcher.dispatch(message):
            return 0


def main() -> int:
    repo_root = sys.argv[1] if len(sys.argv) > 1 else None
    return run_server(repo_root)


if __name__ == "__main__":
    sys.exit(main())
