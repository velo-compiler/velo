import unittest
import subprocess
import sys
from pathlib import Path

class TestMilestone1(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.example = self.root_dir / "examples" / "01_hello.vl"

    def test_emit_c(self):
        cmd = [sys.executable, str(self.velo_py), "emit-c", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
        self.assertIn('#include "velo_runtime.h"', res.stdout)
        self.assertIn('int main(int argc, char** argv)', res.stdout)
        self.assertIn('velo_io_println("Hello from Velo! High-velocity native code.");', res.stdout)

    def test_run_hello(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"run failed: {res.stderr}")
        self.assertIn("Hello from Velo! High-velocity native code.", res.stdout)

if __name__ == "__main__":
    unittest.main()
