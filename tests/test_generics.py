import unittest
import subprocess
import sys
from pathlib import Path

class TestGenerics(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.example = self.root_dir / "examples" / "22_generics.vl"

    def test_run_generics(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"run failed: {res.stderr}\nSTDOUT:\n{res.stdout}")
        self.assertIn("Box value: 42", res.stdout)
        self.assertIn("Pair key: score, val: 100", res.stdout)
        self.assertIn("Option Some: Velo Generics", res.stdout)
        self.assertIn("Option None", res.stdout)
        self.assertIn("min(15, 25) = 15", res.stdout)
        self.assertIn("min[f32](3.14, 2.71) is less than 3: true", res.stdout)
        self.assertIn("Before swap: x=111, y=222", res.stdout)
        self.assertIn("After swap: x=222, y=111", res.stdout)
        self.assertIn("=== Generics Verification Complete ===", res.stdout)

    def test_emit_c_generics(self):
        cmd = [sys.executable, str(self.velo_py), "emit-c", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
        self.assertIn("typedef struct Box_i32 Box_i32;", res.stdout)
        self.assertIn("typedef struct Pair_string_i32 Pair_string_i32;", res.stdout)
        self.assertIn("typedef struct Option_string Option_string;", res.stdout)
        self.assertIn("i32 min_i32(i32 a, i32 b);", res.stdout)
        self.assertIn("f32 min_f32(f32 a, f32 b);", res.stdout)
        self.assertIn("void swap_i32(i32* a, i32* b);", res.stdout)

if __name__ == "__main__":
    unittest.main()
