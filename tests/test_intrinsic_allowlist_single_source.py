"""Tests for Single-Source Intrinsic Allowlist Table (Task 80.1 / I80.1).

Verifies that:
1. `src/common/intrinsics.vl` is the single authoritative source of truth for `sys.*` intrinsic namespaces.
2. `src/backend/driver.vl`, `src/lsp/analysis.vl`, and `src/backend/pretty_recon.vl` all import `intrinsics.vl`.
3. Zero hardcoded "sys.io" strings exist in driver.vl, analysis.vl, or pretty_recon.vl.
4. Compiler driver and LSP analysis treat all canonical intrinsic namespaces consistently without filesystem lookup.
5. Unknown non-intrinsic namespaces (e.g. `use sys.unknown`) fail file resolution as expected.
"""

import json
import os
import re
import subprocess
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


class TestIntrinsicAllowlistSingleSource(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_exe = velo_exe()
        self.env = os.environ.copy()
        if cc_dir() not in self.env.get("PATH", ""):
            self.env["PATH"] = cc_dir() + ";" + self.env.get("PATH", "")

    def test_single_source_imports(self):
        """Verify that driver.vl, analysis.vl, and pretty_recon.vl all import intrinsics.vl."""
        driver_path = self.root_dir / "src" / "backend" / "driver.vl"
        analysis_path = self.root_dir / "src" / "lsp" / "analysis.vl"
        recon_path = self.root_dir / "src" / "backend" / "pretty_recon.vl"
        intrinsics_path = self.root_dir / "src" / "common" / "intrinsics.vl"

        self.assertTrue(intrinsics_path.exists(), "src/common/intrinsics.vl must exist")

        driver_src = driver_path.read_text(encoding="utf-8")
        analysis_src = analysis_path.read_text(encoding="utf-8")
        recon_src = recon_path.read_text(encoding="utf-8")

        self.assertIn("intrinsics.vl", driver_src, "driver.vl must import intrinsics.vl")
        self.assertIn("is_intrinsic_namespace", driver_src, "driver.vl must call is_intrinsic_namespace")

        self.assertIn("intrinsics.vl", analysis_src, "analysis.vl must import intrinsics.vl")
        self.assertIn("is_intrinsic_namespace", analysis_src, "analysis.vl must call is_intrinsic_namespace")

        self.assertIn("intrinsics.vl", recon_src, "pretty_recon.vl must import intrinsics.vl")
        self.assertIn("is_intrinsic_namespace", recon_src, "pretty_recon.vl must call is_intrinsic_namespace")

    def test_zero_hardcoded_sys_io_occurrences(self):
        """Verify that grep -c 'sys.io' yields 0 in driver.vl, analysis.vl, and pretty_recon.vl (Exit Criterion)."""
        target_files = [
            self.root_dir / "src" / "backend" / "driver.vl",
            self.root_dir / "src" / "lsp" / "analysis.vl",
            self.root_dir / "src" / "backend" / "pretty_recon.vl",
        ]
        pattern = re.compile(r'"sys\.io"')
        for tf in target_files:
            content = tf.read_text(encoding="utf-8")
            matches = pattern.findall(content)
            self.assertEqual(len(matches), 0, f"Found hardcoded 'sys.io' in {tf.relative_to(self.root_dir)}")

    def test_intrinsics_table_contents(self):
        """Verify src/common/intrinsics.vl defines canonical 8 sys.* namespaces and their members."""
        intrinsics_src = (self.root_dir / "src" / "common" / "intrinsics.vl").read_text(encoding="utf-8")
        expected_namespaces = [
            "sys.io", "sys.mem", "sys.fs", "sys.thread",
            "sys.math", "sys.time", "sys.os", "sys.simd"
        ]
        for ns in expected_namespaces:
            self.assertIn(f'"{ns}"', intrinsics_src, f"Missing namespace {ns} in intrinsics.vl")

        self.assertIn("act intrinsic_namespaces", intrinsics_src)
        self.assertIn("act intrinsic_members", intrinsics_src)
        self.assertIn("act is_intrinsic_namespace", intrinsics_src)
        self.assertIn("act is_intrinsic_member", intrinsics_src)

    def test_driver_compiles_standard_intrinsics(self):
        """Verify driver compiles code importing standard intrinsics without file resolution error."""
        self.assertTrue(self.velo_exe.exists(), "velo.exe must exist")
        scratch = self.root_dir / ".velo_cache" / "test_driver_intrinsics.vl"
        out_exe = self.root_dir / ".velo_cache" / "test_driver_intrinsics.exe"

        code = (
            "use sys.io\n"
            "use sys.mem\n"
            "use sys.math\n"
            "act main() -> i32 {\n"
            "    return 0\n"
            "}\n"
        )
        scratch.write_text(code, encoding="utf-8", newline="\n")

        try:
            cmd = [str(self.velo_exe), "build", str(scratch), "-o", str(out_exe)]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=self.env)
            self.assertEqual(res.returncode, 0, f"Compilation failed: {res.stderr}\n{res.stdout}")
            self.assertTrue(out_exe.exists())
        finally:
            if scratch.exists():
                scratch.unlink()
            if out_exe.exists():
                out_exe.unlink()

    def test_driver_rejects_unknown_sys_namespace(self):
        """Verify unknown sys.* namespace triggers file resolution failure."""
        self.assertTrue(self.velo_exe.exists(), "velo.exe must exist")
        scratch = self.root_dir / ".velo_cache" / "test_unknown_sys.vl"

        code = (
            "use sys.unknown_module\n"
            "act main() -> i32 {\n"
            "    return 0\n"
            "}\n"
        )
        scratch.write_text(code, encoding="utf-8", newline="\n")

        try:
            cmd = [str(self.velo_exe), "build", str(scratch)]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=self.env)
            self.assertNotEqual(res.returncode, 0, "Unknown sys module should fail to resolve")
            self.assertTrue(
                "Source file does not exist" in res.stdout or "Failed to read source file" in res.stdout or "Source file does not exist" in res.stderr or "Failed to read source file" in res.stderr,
                f"Expected file resolution error in output: {res.stdout}\n{res.stderr}"
            )
        finally:
            if scratch.exists():
                scratch.unlink()

    def test_lsp_diagnostics_on_intrinsics(self):
        """Verify LSP server publishes zero errors for files importing standard intrinsics."""
        self.assertTrue(self.velo_exe.exists(), "velo.exe must exist")
        proc = spawn_native_lsp(self.velo_exe)
        uri = "file:///test_lsp_intrinsics.vl"
        code = (
            "use sys.io\n"
            "use sys.mem\n"
            "act main() -> i32 {\n"
            "    return 0\n"
            "}\n"
        )

        try:
            send_lsp_msg(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
            init_res = recv_lsp_msg(proc)
            self.assertEqual(init_res["id"], 1)

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
            self.assertEqual(len(diag["params"]["diagnostics"]), 0, f"Unexpected diagnostics: {diag}")
        finally:
            send_lsp_msg(proc, {"jsonrpc": "2.0", "id": 99, "method": "shutdown"})
            recv_lsp_msg(proc)
            send_lsp_msg(proc, {"jsonrpc": "2.0", "method": "exit"})
            proc.wait(timeout=2)


if __name__ == "__main__":
    unittest.main()
