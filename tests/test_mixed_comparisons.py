import os
import sys
import subprocess
import unittest
import tempfile
from pathlib import Path

class TestMixedComparisons(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.velo_exe = self.root_dir / "bin" / "velo.exe"
        self.env = os.environ.copy()
        if r"C:\msys64\ucrt64\bin" not in self.env.get("PATH", ""):
            self.env["PATH"] = r"C:\msys64\ucrt64\bin;" + self.env.get("PATH", "")

    def _test_program(self, code: str, expected_output: str):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "test_cmp.vl"
            src_file.write_text(code, encoding="utf-8")

            # Stage 1 (Python)
            res1 = subprocess.run([sys.executable, str(self.velo_py), "run", str(src_file)],
                                  capture_output=True, text=True, env=self.env)
            self.assertEqual(res1.returncode, 0, f"Stage 1 failed:\nSTDOUT:\n{res1.stdout}\nSTDERR:\n{res1.stderr}")
            self.assertIn(expected_output, res1.stdout)

            # Stage 2 (Self-hosted)
            res2 = subprocess.run([str(self.velo_exe), "run", str(src_file)],
                                  capture_output=True, text=True, env=self.env)
            self.assertEqual(res2.returncode, 0, f"Stage 2 failed:\nSTDOUT:\n{res2.stdout}\nSTDERR:\n{res2.stderr}")
            self.assertIn(expected_output, res2.stdout)

    def test_signed_vs_unsigned_compares(self):
        code = """
act main() -> i32 {
    let a: i32 = -1
    let b: u32 = 1
    if not (a < b) { return 1 }
    if not (a <= b) { return 2 }
    if (a > b) { return 3 }
    if (a >= b) { return 4 }
    if (a == b) { return 5 }
    if not (a != b) { return 6 }

    let c: u32 = 1
    let d: i32 = -1
    if (c < d) { return 7 }
    if (c <= d) { return 8 }
    if not (c > d) { return 9 }
    if not (c >= d) { return 10 }
    if (c == d) { return 11 }
    if not (c != d) { return 12 }

    let umax: u32 = 4294967295 as u32
    if (a == umax) { return 13 }
    if not (a != umax) { return 14 }
    if not (a < umax) { return 15 }
    if not (a <= umax) { return 16 }
    if (a > umax) { return 17 }
    if (a >= umax) { return 18 }

    let p: i32 = 10
    let q: u32 = 10
    if not (p == q) { return 19 }
    if (p != q) { return 20 }
    if not (p <= q) { return 21 }
    if not (p >= q) { return 22 }
    if (p < q) { return 23 }
    if (p > q) { return 24 }

    io.println("MIXED_CMP_ALL_PASSED")
    return 0
}
"""
        self._test_program(code, "MIXED_CMP_ALL_PASSED")

    def test_64bit_mixed_compares(self):
        code = """
act main() -> i32 {
    let s: i64 = -1
    let u: u64 = 100
    if not (s < u) { return 1 }
    if (s > u) { return 2 }
    if (s == u) { return 3 }
    if not (s != u) { return 4 }

    if (u < s) { return 5 }
    if not (u > s) { return 6 }
    if (u == s) { return 7 }
    if not (u != s) { return 8 }

    io.println("64BIT_CMP_PASSED")
    return 0
}
"""
        self._test_program(code, "64BIT_CMP_PASSED")

    def test_side_effects_evaluated_once(self):
        code = """
mut g_left_calls: i32 = 0
mut g_right_calls: i32 = 0

act get_left() -> i32 {
    g_left_calls += 1
    return -1
}

act get_right() -> u32 {
    g_right_calls += 1
    return 5 as u32
}

act main() -> i32 {
    let ok = get_left() < get_right()
    if not ok { return 1 }
    if g_left_calls != 1 { return 2 }
    if g_right_calls != 1 { return 3 }
    io.println("SIDE_EFFECTS_OK")
    return 0
}
"""
        self._test_program(code, "SIDE_EFFECTS_OK")

    def test_codegen_emits_wrappers(self):
        code = """
act main() -> i32 {
    let a: i32 = -1
    let b: u32 = 1
    if a < b { return 0 }
    return 1
}
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "emit.vl"
            src_file.write_text(code, encoding="utf-8")
            res = subprocess.run([str(self.velo_exe), "emit-c", str(src_file)],
                                 capture_output=True, text=True, env=self.env)
            self.assertEqual(res.returncode, 0)
            self.assertIn("velo_cmp_lt_s_u", res.stdout)

