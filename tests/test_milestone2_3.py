import unittest
import subprocess
import sys
import tempfile
from pathlib import Path
from velo.driver import CompilerDriver

class TestMilestone23(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.entry_file = self.root_dir / "examples" / "08_multifile" / "main.vl"
        self.driver = CompilerDriver()

    def test_run_multifile(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.entry_file)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"run failed: {res.stderr}")
        self.assertIn("--- Velo Milestone 2.3: Multi-File Imports ---", res.stdout)
        self.assertIn("Sum of vectors: (16.00, 16.00)", res.stdout)
        self.assertIn("Scaled vector: (32.00, 32.00)", res.stdout)
        self.assertIn("Stats: count=42, score=99.50", res.stdout)
        self.assertIn("--- Milestone 2.3 Complete! ---", res.stdout)

    def test_emit_c_multifile_structure(self):
        cmd = [sys.executable, str(self.velo_py), "emit-c", str(self.entry_file)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
        self.assertIn("typedef struct Vector2 Vector2;", res.stdout)
        self.assertIn("typedef struct Stats Stats;", res.stdout)
        self.assertIn("Vector2 add_vectors(Vector2 v1, Vector2 v2);", res.stdout)
        self.assertIn("Vector2 scale_vector(Vector2 v, f32 factor);", res.stdout)
        self.assertIn("const Vector2 sum = add_vectors(a, b);", res.stdout)

    def test_circular_import_resilience(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            file_a = tmp_path / "mod_a.vl"
            file_b = tmp_path / "mod_b.vl"
            file_main = tmp_path / "main.vl"

            file_a.write_text(
                'use "mod_b.vl"\n'
                'act func_a() -> i32 { return 10 }\n',
                encoding="utf-8"
            )

            file_b.write_text(
                'use "mod_a.vl"\n'
                'act func_b() -> i32 { return 20 }\n',
                encoding="utf-8"
            )

            file_main.write_text(
                'use sys.io\n'
                'use "mod_a.vl"\n'
                'act main() {\n'
                '    let total = func_a() + func_b()\n'
                '    io.println("Total: {total}")\n'
                '}\n',
                encoding="utf-8"
            )

            c_code = self.driver.compile_to_c(str(file_main))
            self.assertIn("func_a(", c_code)
            self.assertIn("func_b(", c_code)

    def test_missing_import_error(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_bad = Path(tmp_dir) / "bad.vl"
            file_bad.write_text('use "non_existent_module.vl"\nact main() {}', encoding="utf-8")

            with self.assertRaises(FileNotFoundError):
                self.driver.compile_to_c(str(file_bad))

if __name__ == "__main__":
    unittest.main()
