import unittest
import subprocess
import sys
import os
import shutil
from pathlib import Path

class TestStage2Codegen(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.example = self.root_dir / "examples" / "13_stage2_codegen_test.vl"
        self.cache_dir = self.root_dir / ".velo_cache"

    def _find_gcc(self) -> str:
        gcc_path = shutil.which("gcc")
        if not gcc_path and sys.platform == "win32":
            for candidate in [
                r"C:\msys64\ucrt64\bin\gcc.exe",
                r"C:\msys64\mingw64\bin\gcc.exe",
            ]:
                if os.path.exists(candidate):
                    return candidate
        return gcc_path or "gcc"

    def test_run_stage2_codegen(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"run failed: {res.stderr}")
        self.assertIn("--- Velo Stage 2 Milestone 2.4: Native C99 Code Generator Verification ---", res.stdout)
        self.assertIn("AST parsed and semantic check passed: true", res.stdout)
        self.assertIn("typedef struct Point Point;", res.stdout)
        self.assertIn("float add_coords(Point* p, float delta);", res.stdout)
        self.assertIn("return ((p->x + p->y) + delta);", res.stdout)
        self.assertIn("Generated C source written to disk: true", res.stdout)
        self.assertIn("--- Milestone 2.4 Complete! ---", res.stdout)

    def test_compile_and_run_generated_c(self):
        # 1. Run the Velo codegen script to generate the C file
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        subprocess.run(cmd, capture_output=True, text=True, check=True)

        c_file = self.cache_dir / "stage2_generated.c"
        self.assertTrue(c_file.exists(), "stage2_generated.c was not created")

        # 2. Compile with GCC
        gcc = self._find_gcc()
        exe_file = self.cache_dir / "test_stage2_unit.exe"
        env = os.environ.copy()
        gcc_bin_dir = str(Path(gcc).parent.resolve())
        env["PATH"] = f"{gcc_bin_dir}{os.pathsep}{env.get('PATH', '')}"

        compile_cmd = [
            gcc,
            "-O2",
            "-std=c99",
            str(c_file),
            f"-I{self.root_dir / 'velo' / 'runtime'}",
            "-o",
            str(exe_file)
        ]
        res = subprocess.run(compile_cmd, capture_output=True, text=True, env=env)
        self.assertEqual(res.returncode, 0, f"GCC compilation failed: {res.stderr}")

        # 3. Execute the binary
        run_res = subprocess.run([str(exe_file)], capture_output=True, text=True)
        self.assertEqual(run_res.returncode, 0, f"Execution failed: {run_res.stderr}")
        self.assertIn("Computed result successfully!", run_res.stdout)

if __name__ == "__main__":
    unittest.main()
