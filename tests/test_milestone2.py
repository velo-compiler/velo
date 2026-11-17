import unittest
import subprocess
import sys
from pathlib import Path

class TestMilestone2(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.example = self.root_dir / "examples" / "02_math_and_logic.vl"

    def test_run_math_and_logic(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"run failed: {res.stderr}")
        self.assertIn("While step: 0", res.stdout)
        self.assertIn("While step: 2", res.stdout)
        self.assertIn("Loop start at 0", res.stdout)
        self.assertIn("Loop middle step: 2", res.stdout)
        self.assertIn("Loop end at 4", res.stdout)
        self.assertIn("Fibonacci(7) = 13", res.stdout)

    def test_emit_c_has_const_and_loops(self):
        cmd = [sys.executable, str(self.velo_py), "emit-c", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
        # Verify const was emitted for immutable variable
        self.assertIn("const i32 total_steps = 5;", res.stdout)
        # Verify mutable variable
        self.assertIn("i32 counter = 0;", res.stdout)
        # Verify for-loop range
        self.assertIn("for (i64 i = (0); i < (total_steps); ++i)", res.stdout)

if __name__ == "__main__":
    unittest.main()
