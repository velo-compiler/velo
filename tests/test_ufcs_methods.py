import unittest
import subprocess
import sys
from pathlib import Path

class TestUFCSMethods(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.example = self.root_dir / "examples" / "24_ufcs_methods.vl"

    def test_run_ufcs_methods(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"run failed: {res.stderr}\nSTDOUT:\n{res.stdout}")
        self.assertIn("Initial length_sq: 25.00", res.stdout)
        self.assertIn("After scale(2.0): x=6.00, y=8.00", res.stdout)
        self.assertIn("Scaled length_sq: 100.00", res.stdout)
        self.assertIn("After pv.scale(0.5): x=3.00, y=4.00", res.stdout)
        self.assertIn("Length via pointer receiver: 25.00", res.stdout)
        self.assertIn("Chained add: x=6.00, y=8.00", res.stdout)
        self.assertIn("7.square() = 49", res.stdout)
        self.assertIn("Button clicked! Tag = 42", res.stdout)
        self.assertIn("Generic Box unwrap: 999", res.stdout)
        self.assertIn("=== UFCS Method Syntax: SUCCESS ===", res.stdout)

    def test_emit_c_ufcs_methods(self):
        cmd = [sys.executable, str(self.velo_py), "emit-c", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
        self.assertIn("scale((&v), 2.0", res.stdout)
        self.assertIn("scale(pv, 0.5", res.stdout)
        self.assertIn("length_sq((*pv))", res.stdout)
        self.assertIn("unwrap_i32((&b))", res.stdout)

if __name__ == "__main__":
    unittest.main()
