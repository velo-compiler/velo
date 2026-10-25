import unittest
import subprocess
import sys
import os
from pathlib import Path

class TestCcBackend(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.velo_exe = self.root_dir / "bin" / "velo.exe"
        self.cache_dir = self.root_dir / ".velo_cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.sample_src = self.cache_dir / "cc_test_sample.vl"
        self.sample_src.write_text(
            'use sys.io\n'
            'act main() -> i32 {\n'
            '    let a: i32 = 40\n'
            '    let b: i32 = 2\n'
            '    let c: i32 = a + b\n'
            '    io.println("cc answer: {c}")\n'
            '    return 0\n'
            '}\n',
            encoding="utf-8"
        )

    def test_stage1_build_and_run_cl(self):
        out_exe = self.cache_dir / "stage1_cl_test.exe"
        cmd = [sys.executable, str(self.velo_py), "build", str(self.sample_src), "--cc", "cl", "-o", str(out_exe)]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.root_dir))
        self.assertEqual(res.returncode, 0, f"Stage 1 build --cc cl failed: {res.stderr}\n{res.stdout}")
        self.assertTrue(out_exe.exists(), "Output executable not created by Stage 1 cl build")

        run_res = subprocess.run([str(out_exe)], capture_output=True, text=True)
        self.assertEqual(run_res.returncode, 0)
        self.assertIn("cc answer: 42", run_res.stdout)

    def test_stage1_run_cl(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.sample_src), "--cc", "cl"]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.root_dir))
        self.assertEqual(res.returncode, 0, f"Stage 1 run --cc cl failed: {res.stderr}\n{res.stdout}")
        self.assertIn("cc answer: 42", res.stdout)

    def test_stage2_build_and_run_cl(self):
        self.assertTrue(self.velo_exe.exists(), "bin/velo.exe does not exist")
        out_exe = self.cache_dir / "stage2_cl_test.exe"
        cmd = [str(self.velo_exe), "build", str(self.sample_src), "--cc", "cl", "-o", str(out_exe)]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.root_dir))
        self.assertEqual(res.returncode, 0, f"Stage 2 build --cc cl failed: {res.stderr}\n{res.stdout}")
        self.assertTrue(out_exe.exists(), "Output executable not created by Stage 2 cl build")

        run_res = subprocess.run([str(out_exe)], capture_output=True, text=True)
        self.assertEqual(run_res.returncode, 0)
        self.assertIn("cc answer: 42", run_res.stdout)

    def test_stage2_run_cl(self):
        self.assertTrue(self.velo_exe.exists(), "bin/velo.exe does not exist")
        cmd = [str(self.velo_exe), "run", str(self.sample_src), "--cc", "cl"]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.root_dir))
        self.assertEqual(res.returncode, 0, f"Stage 2 run --cc cl failed: {res.stderr}\n{res.stdout}")
        self.assertIn("cc answer: 42", res.stdout)

    def test_invalid_cc_backend(self):
        cmd_s1 = [sys.executable, str(self.velo_py), "run", str(self.sample_src), "--cc", "unknown_cc"]
        res_s1 = subprocess.run(cmd_s1, capture_output=True, text=True, cwd=str(self.root_dir))
        self.assertNotEqual(res_s1.returncode, 0)

        cmd_s2 = [str(self.velo_exe), "run", str(self.sample_src), "--cc", "unknown_cc"]
        res_s2 = subprocess.run(cmd_s2, capture_output=True, text=True, cwd=str(self.root_dir))
        self.assertNotEqual(res_s2.returncode, 0)
        self.assertIn("Unknown C compiler backend", res_s2.stdout)

    def test_default_cc_is_gcc(self):
        cmd_s1 = [sys.executable, str(self.velo_py), "run", str(self.sample_src)]
        res_s1 = subprocess.run(cmd_s1, capture_output=True, text=True, cwd=str(self.root_dir))
        self.assertEqual(res_s1.returncode, 0)
        self.assertIn("cc answer: 42", res_s1.stdout)

        cmd_s2 = [str(self.velo_exe), "run", str(self.sample_src)]
        res_s2 = subprocess.run(cmd_s2, capture_output=True, text=True, cwd=str(self.root_dir))
        self.assertEqual(res_s2.returncode, 0)
        self.assertIn("cc answer: 42", res_s2.stdout)

if __name__ == "__main__":
    unittest.main()
