import unittest
import subprocess
import sys
from pathlib import Path

class TestMilestone4(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.example = self.root_dir / "examples" / "04_zone_memory.vl"

    def test_run_zone_memory_and_ffi(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"run failed: {res.stderr}")
        self.assertIn("Arena memory before zone: 0 bytes", res.stdout)
        self.assertIn("Arena memory inside zone: 800 bytes", res.stdout)
        self.assertIn("First point: (10.00, 20.00)", res.stdout)
        self.assertIn("Last point: (10.00, 20.00)", res.stdout)
        self.assertIn("Arena memory after zone exit: 0 bytes", res.stdout)

    def test_emit_c_has_zone_push_and_pop(self):
        cmd = [sys.executable, str(self.velo_py), "emit-c", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
        self.assertIn("velo_zone_push();", res.stdout)
        self.assertIn("velo_zone_pop(", res.stdout)
        self.assertIn("velo_mem_alloc(sizeof(Point)", res.stdout)

if __name__ == "__main__":
    unittest.main()
