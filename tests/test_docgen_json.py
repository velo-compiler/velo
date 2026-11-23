"""Tests for Structured JSON Documentation (`velo doc --json`) and LSP Hover Doc Comment Integration (Task 79.8).
"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from conftest import cc_dir, velo_exe


def spawn_native_lsp(bin_path):
    return subprocess.Popen(
        [str(bin_path), "lsp"],
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


def recv_lsp_msg(proc):
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


class TestDocgenJson(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_exe = velo_exe()
        self.example = self.root_dir / "examples" / "15_docs_and_comments.vl"
        self.env = os.environ.copy()
        if cc_dir() not in self.env.get("PATH", ""):
            self.env["PATH"] = cc_dir() + ";" + self.env.get("PATH", "")

    def test_doc_json_stdout(self):
        """Verify `velo doc <file> --json` emits structured JSON to stdout."""
        self.assertTrue(self.velo_exe.exists(), "velo.exe must exist")
        cmd = [str(self.velo_exe), "doc", str(self.example), "--json"]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=self.env)
        self.assertEqual(res.returncode, 0, f"velo doc --json failed: {res.stderr}")

        data = json.loads(res.stdout)
        self.assertIn("file", data)
        self.assertIn("data", data)
        self.assertIn("acts", data)
        self.assertIn("externs", data)

        # Verify struct metadata
        structs = {s["name"]: s for s in data["data"]}
        self.assertIn("Vector2D", structs)
        vec = structs["Vector2D"]
        self.assertIn("Vector coordinate blueprint", vec["doc"])
        self.assertEqual(len(vec["fields"]), 2)
        field_names = [f["name"] for f in vec["fields"]]
        self.assertIn("x", field_names)
        self.assertIn("y", field_names)

        # Verify function metadata
        acts = {a["name"]: a for a in data["acts"]}
        self.assertIn("make_vector", acts)
        mv = acts["make_vector"]
        self.assertIn("Creates a new 2D vector", mv["doc"])
        self.assertEqual(mv["return_type"], "Vector2D")
        self.assertEqual(len(mv["params"]), 2)
        self.assertEqual(mv["params"][0]["name"], "x")
        self.assertEqual(mv["params"][0]["type"], "f32")

        self.assertIn("dot_product", acts)
        dp = acts["dot_product"]
        self.assertIn("Computes the dot product", dp["doc"])
        self.assertEqual(dp["return_type"], "f32")

        # Verify extern metadata
        externs = {e["name"]: e for e in data["externs"]}
        self.assertIn("puts", externs)
        puts = externs["puts"]
        self.assertEqual(puts["return_type"], "i32")
        self.assertEqual(len(puts["params"]), 1)
        self.assertEqual(puts["params"][0]["name"], "str")

    def test_doc_json_file_output(self):
        """Verify `velo doc <file> -o <out.json> --json` writes valid JSON to file."""
        self.assertTrue(self.velo_exe.exists(), "velo.exe must exist")
        out_file = self.root_dir / ".velo_cache" / "test_docgen_api.json"
        if out_file.exists():
            out_file.unlink()

        cmd = [str(self.velo_exe), "doc", str(self.example), "-o", str(out_file), "--json"]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=self.env)
        self.assertEqual(res.returncode, 0, f"velo doc -o --json failed: {res.stderr}")
        self.assertTrue(out_file.exists(), "Output JSON file must exist")

        content = out_file.read_text(encoding="utf-8")
        data = json.loads(content)
        self.assertIn("data", data)
        self.assertIn("acts", data)
        out_file.unlink()

    def test_lsp_hover_includes_doc_comments(self):
        """Verify LSP hover includes doc comments for functions and structs."""
        self.assertTrue(self.velo_exe.exists(), "velo.exe must exist")
        proc = spawn_native_lsp(self.velo_exe)
        uri = "file:///test_lsp_doc_hover.vl"

        code = (
            "/// 2D Point structure for geometry\n"
            "data Point {\n"
            "    x: i32\n"
            "    y: i32\n"
            "}\n\n"
            "/**\n"
            " * Computes distance between points\n"
            " */\n"
            "act dist(a: Point, b: Point) -> i32 {\n"
            "    return 0\n"
            "}\n\n"
            "act main() -> i32 {\n"
            "    let p1: Point = Point { x: 0, y: 0 }\n"
            "    let p2: Point = Point { x: 3, y: 4 }\n"
            "    let d = dist(p1, p2)\n"
            "    return d\n"
            "}\n"
        )

        try:
            # 1. Initialize
            send_lsp_msg(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
            init_res = recv_lsp_msg(proc)
            self.assertEqual(init_res["id"], 1)

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
            self.assertEqual(diag["method"], "textDocument/publishDiagnostics")

            # 3. Hover on dist call (line 16, character 14: let d = dist(p1, p2))
            send_lsp_msg(proc, {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "textDocument/hover",
                "params": {
                    "textDocument": {"uri": uri},
                    "position": {"line": 16, "character": 14}
                }
            })
            h_dist = recv_lsp_msg(proc)
            self.assertEqual(h_dist["id"], 2)
            self.assertIsNotNone(h_dist["result"])
            val_dist = h_dist["result"]["contents"]["value"]
            self.assertIn("dist(a: Point, b: Point) -> i32", val_dist)
            self.assertIn("Computes distance between points", val_dist)

            # 4. Hover on Point struct declaration (line 1, character 6: data Point {)
            send_lsp_msg(proc, {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "textDocument/hover",
                "params": {
                    "textDocument": {"uri": uri},
                    "position": {"line": 1, "character": 6}
                }
            })
            h_pt = recv_lsp_msg(proc)
            self.assertEqual(h_pt["id"], 3)
            self.assertIsNotNone(h_pt["result"])
            val_pt = h_pt["result"]["contents"]["value"]
            self.assertIn("**data** `Point`", val_pt)
            self.assertIn("2D Point structure for geometry", val_pt)

        finally:
            send_lsp_msg(proc, {"jsonrpc": "2.0", "id": 99, "method": "shutdown"})
            recv_lsp_msg(proc)
            send_lsp_msg(proc, {"jsonrpc": "2.0", "method": "exit"})
            proc.wait(timeout=2)


if __name__ == "__main__":
    unittest.main()
