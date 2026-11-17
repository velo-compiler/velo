import unittest
import subprocess
import sys
from pathlib import Path

class TestMilestone3(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.example = self.root_dir / "examples" / "03_pointers.vl"

    def test_run_pointers_and_structs(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"run failed: {res.stderr}")
        self.assertIn("Initial Point: (10.00, 20.00)", res.stdout)
        self.assertIn("Point after move: (15.50, 17.50)", res.stdout)
        self.assertIn("Point after direct ptr.x: (100.00, 17.50)", res.stdout)
        self.assertIn("Original score: 42", res.stdout)
        self.assertIn("Modified score via p_score.@: 99", res.stdout)

    def test_emit_c_has_struct_and_arrow(self):
        cmd = [sys.executable, str(self.velo_py), "emit-c", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
        # Verify typedef struct Point
        self.assertIn("typedef struct Point Point;", res.stdout)
        self.assertIn("struct Point {", res.stdout)
        # Verify auto-dereference (->) was emitted for pointer
        self.assertIn("p->x += dx;", res.stdout)
        self.assertIn("ptr->x = 100.0f;", res.stdout)
        # Verify direct dereference (*p_score)
        self.assertIn("(*p_score) = 99;", res.stdout)

if __name__ == "__main__":
    unittest.main()
