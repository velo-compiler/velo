import unittest
import subprocess
import os
import sys
import shutil
from pathlib import Path
from conftest import velo_exe

class TestVeloProfiling(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_exe = velo_exe()
        self.assertTrue(self.velo_exe.exists(), "bin/velo.exe does not exist")
        self.cache_dir = self.root_dir / ".velo_cache" / "prof_tests"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # Ensure gmon.out is cleaned before tests
        self.gmon_file = Path("gmon.out")
        if self.gmon_file.exists():
            try:
                self.gmon_file.unlink()
            except Exception:
                pass

    def tearDown(self):
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir, ignore_errors=True)
        if self.gmon_file.exists():
            try:
                self.gmon_file.unlink()
            except Exception:
                pass

    def test_profile_flag_documented_in_usage(self):
        res = subprocess.run([str(self.velo_exe), "help"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0)
        self.assertIn("--profile", res.stdout)
        self.assertIn("velo run", res.stdout)
        self.assertIn("velo build", res.stdout)

    def test_conflicting_build_modes_diagnosed(self):
        test_file = self.cache_dir / "conflict.vl"
        test_file.write_text("act main() -> i32 { return 0 }\n", encoding="utf-8", newline="\n")

        # --debug and --profile together
        res1 = subprocess.run([str(self.velo_exe), "build", str(test_file), "--debug", "--profile"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res1.returncode, 1)
        self.assertIn("Cannot combine conflicting build modes", res1.stdout)

        # --release and --profile together
        res2 = subprocess.run([str(self.velo_exe), "build", str(test_file), "--release", "--profile"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res2.returncode, 1)
        self.assertIn("Cannot combine conflicting build modes", res2.stdout)

    def test_build_profile_generates_gmon_out(self):
        test_file = self.cache_dir / "compute.vl"
        sample_code = (
            "use sys.io\n"
            "act calculate_sum(limit: i32) -> i64 {\n"
            "    mut s: i64 = 0\n"
            "    mut i: i32 = 0\n"
            "    loop i < limit {\n"
            "        s += i as i64\n"
            "        i += 1\n"
            "    }\n"
            "    return s\n"
            "}\n"
            "act main() -> i32 {\n"
            "    let total = calculate_sum(100000)\n"
            "    io.println(\"total: {total}\")\n"
            "    return 0\n"
            "}\n"
        )
        test_file.write_text(sample_code, encoding="utf-8", newline="\n")

        out_exe = self.cache_dir / "compute.exe"
        res_build = subprocess.run([str(self.velo_exe), "build", str(test_file), "--profile", "-o", str(out_exe)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res_build.returncode, 0, f"Build --profile failed: {res_build.stdout}\n{res_build.stderr}")
        self.assertTrue(out_exe.exists())

        # Run the compiled binary
        res_run = subprocess.run([str(out_exe)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res_run.returncode, 0)
        self.assertIn("total: 4999950000", res_run.stdout)

        # On GCC/Clang with -pg, gmon.out is written on exit
        self.assertTrue(self.gmon_file.exists(), "gmon.out must be generated when running a binary built with --profile")
        self.assertGreater(self.gmon_file.stat().st_size, 0, "gmon.out must be non-empty")

    def test_run_profile_generates_gmon_out(self):
        test_file = self.cache_dir / "runner_prof.vl"
        sample_code = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    mut count: i32 = 0\n"
            "    loop count < 50000 {\n"
            "        count += 1\n"
            "    }\n"
            "    io.println(\"done: {count}\")\n"
            "    return 0\n"
            "}\n"
        )
        test_file.write_text(sample_code, encoding="utf-8", newline="\n")

        res_run = subprocess.run([str(self.velo_exe), "run", str(test_file), "--profile"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res_run.returncode, 0, f"Run --profile failed: {res_run.stdout}\n{res_run.stderr}")
        self.assertIn("done: 50000", res_run.stdout)

        self.assertTrue(self.gmon_file.exists(), "gmon.out must be generated when running via velo run --profile")

    def test_profile_cache_isolation(self):
        test_file = self.cache_dir / "isolated.vl"
        sample_code = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    io.println(\"cached test\")\n"
            "    return 0\n"
            "}\n"
        )
        test_file.write_text(sample_code, encoding="utf-8", newline="\n")

        # 1. Run without --profile (should not produce gmon.out)
        res_norm = subprocess.run([str(self.velo_exe), "run", str(test_file)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res_norm.returncode, 0)
        self.assertFalse(self.gmon_file.exists(), "Normal build should not generate gmon.out")

        # 2. Run with --profile (must produce gmon.out and not reuse normal cache artifact)
        res_prof = subprocess.run([str(self.velo_exe), "run", str(test_file), "--profile"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res_prof.returncode, 0)
        self.assertTrue(self.gmon_file.exists(), "Profile build must produce gmon.out")

if __name__ == "__main__":
    unittest.main()
