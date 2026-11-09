import os
import sys
import subprocess
import unittest
from pathlib import Path

class TestLiteralFormatting(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.velo_exe = self.root_dir / "bin" / "velo.exe"
        self.example = self.root_dir / "examples" / "16_literal_formatting.vl"
        self.env = os.environ.copy()
        if r"C:\msys64\ucrt64\bin" not in self.env.get("PATH", ""):
            self.env["PATH"] = r"C:\msys64\ucrt64\bin;" + self.env.get("PATH", "")

    def test_stage1_run_literal_formatting(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, env=self.env)
        self.assertEqual(res.returncode, 0, f"Stage 1 run failed: {res.stderr}")
        self.assertIn("Hex 0xFF: 255", res.stdout)
        self.assertIn("Binary 0b1010: 10", res.stdout)
        self.assertIn("Binary 0b1100_0011: 195", res.stdout)
        self.assertIn("Octal 0o755: 493", res.stdout)
        self.assertIn("One million 1_000_000: 1000000", res.stdout)
        self.assertIn("Scientific 2.5e3: 2500.00", res.stdout)
        self.assertIn("Explicit suffix 255u8: 255", res.stdout)
        self.assertIn("Explicit suffix 500i64: 500", res.stdout)
        self.assertIn("Explicit suffix 1000usize: 1000", res.stdout)
        self.assertIn("Explicit suffix 3.14f32: 3.14", res.stdout)
        self.assertIn("Explicit suffix 10.5f64: 10.50", res.stdout)
        self.assertIn("All literal formatting tests passed successfully!", res.stdout)

    def test_self_hosted_run_literal_formatting(self):
        self.assertTrue(self.velo_exe.exists(), "velo.exe must exist")
        cmd = [str(self.velo_exe), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, env=self.env)
        self.assertEqual(res.returncode, 0, f"Self-hosted run failed: {res.stderr}")
        self.assertIn("Hex 0xFF: 255", res.stdout)
        self.assertIn("Binary 0b1010: 10", res.stdout)
        self.assertIn("Binary 0b1100_0011: 195", res.stdout)
        self.assertIn("Octal 0o755: 493", res.stdout)
        self.assertIn("One million 1_000_000: 1000000", res.stdout)
        self.assertIn("Scientific 2.5e3: 2500.00", res.stdout)
        self.assertIn("Explicit suffix 255u8: 255", res.stdout)
        self.assertIn("Explicit suffix 500i64: 500", res.stdout)
        self.assertIn("Explicit suffix 1000usize: 1000", res.stdout)
        self.assertIn("Explicit suffix 3.14f32: 3.14", res.stdout)
        self.assertIn("Explicit suffix 10.5f64: 10.50", res.stdout)
        self.assertIn("All literal formatting tests passed successfully!", res.stdout)

    def test_emit_c_literal_formatting(self):
        cmd = [str(self.velo_exe), "emit-c", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, env=self.env)
        self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
        self.assertIn("0xFF", res.stdout)
        self.assertIn("0xAABBCCDD", res.stdout)
        self.assertIn("1000000", res.stdout)
        self.assertIn("1e-4f", res.stdout)
        self.assertIn("2.5e3f", res.stdout)
        self.assertIn("255U", res.stdout)
        self.assertIn("500LL", res.stdout)
        self.assertIn("1000ULL", res.stdout)
        self.assertIn("10.5", res.stdout)

    def test_range_loop_not_broken_by_float_scan(self):
        # Verify 0..5 range loop continues to compile and execute properly
        code = "use sys.io\nact main() {\n    mut sum = 0\n    loop i in 0..5 {\n        sum += i\n    }\n    io.println(\"Sum: {sum}\")\n}\n"
        src_path = self.root_dir / ".velo_cache" / "test_range.vl"
        src_path.write_text(code, encoding="utf-8")
        cmd = [str(self.velo_exe), "run", str(src_path)]
        res = subprocess.run(cmd, capture_output=True, text=True, env=self.env)
        self.assertEqual(res.returncode, 0, f"Range loop execution failed: {res.stderr}")
        self.assertIn("Sum: 10", res.stdout)
        src_path.unlink()

    def test_decimal_leading_zeros_execution(self):
        code = """use sys.io
act main() {
    let a = 099
    let b = 017
    let c = 007
    let d = 00
    let e = 0_0
    let f = 0_17
    let g = 017_u64
    let h = 0x00FF
    let i = 0.5
    io.println("a: {a}")
    io.println("b: {b}")
    io.println("c: {c}")
    io.println("d: {d}")
    io.println("e: {e}")
    io.println("f: {f}")
    io.println("g: {g}")
    io.println("h: {h}")
    io.println("i: {i}")
}
"""
        src_path = self.root_dir / ".velo_cache" / "test_leading_zeros.vl"
        src_path.write_text(code, encoding="utf-8")
        try:
            cmd = [str(self.velo_exe), "run", str(src_path)]
            res = subprocess.run(cmd, capture_output=True, text=True, env=self.env)
            self.assertEqual(res.returncode, 0, f"Run failed: {res.stderr}")
            self.assertIn("a: 99", res.stdout)
            self.assertIn("b: 17", res.stdout)
            self.assertIn("c: 7", res.stdout)
            self.assertIn("d: 0", res.stdout)
            self.assertIn("e: 0", res.stdout)
            self.assertIn("f: 17", res.stdout)
            self.assertIn("g: 17", res.stdout)
            self.assertIn("h: 255", res.stdout)

            # Also verify emit-c output format
            cmd_emit = [str(self.velo_exe), "emit-c", str(src_path)]
            res_emit = subprocess.run(cmd_emit, capture_output=True, text=True, env=self.env)
            self.assertEqual(res_emit.returncode, 0, f"emit-c failed: {res_emit.stderr}")
            # Ensure C source does not have leading zero decimal literals (e.g. 017 or 099)
            self.assertIn("int32_t a = 99;", res_emit.stdout)
            self.assertIn("int32_t b = 17;", res_emit.stdout)
            self.assertIn("int32_t c = 7;", res_emit.stdout)
            self.assertIn("int32_t d = 0;", res_emit.stdout)
            self.assertIn("int32_t e = 0;", res_emit.stdout)
            self.assertIn("int32_t f = 17;", res_emit.stdout)
            self.assertIn("uint64_t g = 17ULL;", res_emit.stdout)
            self.assertIn("0x00FF", res_emit.stdout)
        finally:
            if src_path.exists():
                src_path.unlink()

if __name__ == "__main__":
    unittest.main()
