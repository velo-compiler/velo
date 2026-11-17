import os
import sys
import subprocess
import unittest
from pathlib import Path
from conftest import cc_dir, velo_exe

class TestDocsAndComments(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.velo_exe = velo_exe()
        self.example = self.root_dir / "examples" / "15_docs_and_comments.vl"
        self.env = os.environ.copy()
        if cc_dir() not in self.env.get("PATH", ""):
            self.env["PATH"] = cc_dir() + ";" + self.env.get("PATH", "")

    def test_stage1_run_docs_and_comments(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=self.env)
        self.assertEqual(res.returncode, 0, f"Stage 1 run failed: {res.stderr}")
        self.assertIn("=== Milestone 1.2: Comments & Documentation Test ===", res.stdout)
        self.assertIn("Vector 1: (3.00, 4.00)", res.stdout)
        self.assertIn("Vector 2: (2.00, 5.00)", res.stdout)
        self.assertIn("Dot product: 26.00", res.stdout)
        self.assertIn("Puts: Native C call works!", res.stdout)
        self.assertIn("All nested comment tests passed successfully!", res.stdout)

    def test_self_hosted_run_docs_and_comments(self):
        self.assertTrue(self.velo_exe.exists(), "velo.exe must exist")
        cmd = [str(self.velo_exe), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=self.env)
        self.assertEqual(res.returncode, 0, f"Self-hosted run failed: {res.stderr}")
        self.assertIn("=== Milestone 1.2: Comments & Documentation Test ===", res.stdout)
        self.assertIn("Vector 1: (3.00, 4.00)", res.stdout)
        self.assertIn("Vector 2: (2.00, 5.00)", res.stdout)
        self.assertIn("Dot product: 26.00", res.stdout)
        self.assertIn("Puts: Native C call works!", res.stdout)
        self.assertIn("All nested comment tests passed successfully!", res.stdout)

    def test_stage1_doc_generator(self):
        cmd = [sys.executable, str(self.velo_py), "doc", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=self.env)
        self.assertEqual(res.returncode, 0, f"Stage 1 doc failed: {res.stderr}")
        self.assertIn("# API Reference:", res.stdout)
        self.assertIn("## Data Structures", res.stdout)
        self.assertIn("### `data Vector2D`", res.stdout)
        self.assertIn("> 2D Vector coordinate blueprint.", res.stdout)
        self.assertIn("> Used for spatial transforms and rendering math.", res.stdout)
        self.assertIn("| `x` | `f32` |", res.stdout)
        self.assertIn("| `y` | `f32` |", res.stdout)
        self.assertIn("## Functions", res.stdout)
        self.assertIn("### `act make_vector(x: f32, y: f32) -> Vector2D`", res.stdout)
        self.assertIn("> Creates a new 2D vector initialized with coordinates (x, y).", res.stdout)
        self.assertIn("### `act dot_product(a: Vector2D, b: Vector2D) -> f32`", res.stdout)
        self.assertIn("> Computes the dot product of two 2D vectors.", res.stdout)
        self.assertIn("## External C Interfaces", res.stdout)
        self.assertIn("* `extern act puts(str: string) -> i32`", res.stdout)

    def test_self_hosted_doc_generator(self):
        cmd = [str(self.velo_exe), "doc", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=self.env)
        self.assertEqual(res.returncode, 0, f"Self-hosted doc failed: {res.stderr}")
        self.assertIn("# API Reference:", res.stdout)
        self.assertIn("## Data Structures", res.stdout)
        self.assertIn("### `data Vector2D`", res.stdout)
        self.assertIn("> 2D Vector coordinate blueprint.", res.stdout)
        self.assertIn("> Used for spatial transforms and rendering math.", res.stdout)
        self.assertIn("| `x` | `f32` |", res.stdout)
        self.assertIn("| `y` | `f32` |", res.stdout)
        self.assertIn("## Functions", res.stdout)
        self.assertIn("### `act make_vector(x: f32, y: f32) -> Vector2D`", res.stdout)
        self.assertIn("> Creates a new 2D vector initialized with coordinates (x, y).", res.stdout)
        self.assertIn("### `act dot_product(a: Vector2D, b: Vector2D) -> f32`", res.stdout)
        self.assertIn("> Computes the dot product of two 2D vectors.", res.stdout)
        self.assertIn("## External C Interfaces", res.stdout)
        self.assertIn("* `extern act puts(str: string) -> i32`", res.stdout)

    def test_self_hosted_doc_file_output(self):
        out_file = self.root_dir / ".velo_cache" / "test_api_docs.md"
        if out_file.exists():
            out_file.unlink()
        cmd = [str(self.velo_exe), "doc", str(self.example), "-o", str(out_file)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=self.env)
        self.assertEqual(res.returncode, 0, f"Self-hosted doc with -o failed: {res.stderr}")
        self.assertTrue(out_file.exists(), "Output markdown file must be created")
        content = out_file.read_text(encoding="utf-8")
        self.assertIn("# API Reference:", content)
        self.assertIn("### `data Vector2D`", content)
        self.assertIn("### `act make_vector(x: f32, y: f32) -> Vector2D`", content)
        out_file.unlink()

if __name__ == "__main__":
    unittest.main()
