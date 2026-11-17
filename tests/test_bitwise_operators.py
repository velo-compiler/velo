import os
import sys
import subprocess
import unittest
from pathlib import Path
from conftest import cc_dir, velo_exe

class TestBitwiseOperators(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.velo_exe = velo_exe()
        self.example = self.root_dir / "examples" / "14_bitwise_operators.vl"
        self.env = os.environ.copy()
        if cc_dir() not in self.env.get("PATH", ""):
            self.env["PATH"] = cc_dir() + ";" + self.env.get("PATH", "")

    def test_stage1_run_bitwise(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=self.env)
        self.assertEqual(res.returncode, 0, f"Stage 1 run failed: {res.stderr}")
        self.assertIn("a & b = 8", res.stdout)
        self.assertIn("a | b = 14", res.stdout)
        self.assertIn("a ^ b = 6", res.stdout)
        self.assertIn("a << 2 = 48", res.stdout)
        self.assertIn("a >> 1 = 6", res.stdout)
        self.assertIn("~a = -13", res.stdout)
        self.assertIn("After x <<= 3: 8", res.stdout)
        self.assertIn("After x |= 3: 11", res.stdout)
        self.assertIn("After x &= 9: 9", res.stdout)
        self.assertIn("After x ^= 5: 12", res.stdout)
        self.assertIn("After x >>= 2: 3", res.stdout)
        self.assertIn("Player collision mask: 5", res.stdout)
        self.assertIn("Player can collide with ENEMY: true", res.stdout)
        self.assertIn("Player can collide with BULLET: false", res.stdout)
        self.assertIn("Player collision with ENEMY disabled: true", res.stdout)

    def test_self_hosted_run_bitwise(self):
        self.assertTrue(self.velo_exe.exists(), "velo.exe must exist")
        cmd = [str(self.velo_exe), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=self.env)
        self.assertEqual(res.returncode, 0, f"Self-hosted run failed: {res.stderr}")
        self.assertIn("a & b = 8", res.stdout)
        self.assertIn("a | b = 14", res.stdout)
        self.assertIn("a ^ b = 6", res.stdout)
        self.assertIn("a << 2 = 48", res.stdout)
        self.assertIn("a >> 1 = 6", res.stdout)
        self.assertIn("~a = -13", res.stdout)
        self.assertIn("After x <<= 3: 8", res.stdout)
        self.assertIn("After x |= 3: 11", res.stdout)
        self.assertIn("After x &= 9: 9", res.stdout)
        self.assertIn("After x ^= 5: 12", res.stdout)
        self.assertIn("After x >>= 2: 3", res.stdout)
        self.assertIn("Player collision mask: 5", res.stdout)
        self.assertIn("Player can collide with ENEMY: true", res.stdout)
        self.assertIn("Player can collide with BULLET: false", res.stdout)
        self.assertIn("Player collision with ENEMY disabled: true", res.stdout)

    def test_emit_c_bitwise_operators(self):
        cmd = [str(self.velo_exe), "emit-c", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=self.env)
        self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
        self.assertIn("&", res.stdout)
        self.assertIn("|", res.stdout)
        self.assertIn("^", res.stdout)
        self.assertIn("~", res.stdout)
        self.assertIn("<<", res.stdout)
        self.assertIn(">>", res.stdout)
        self.assertIn("&=", res.stdout)
        self.assertIn("|=", res.stdout)
        self.assertIn("^=", res.stdout)
        self.assertIn("<<=", res.stdout)
        self.assertIn(">>=", res.stdout)

if __name__ == "__main__":
    unittest.main()
