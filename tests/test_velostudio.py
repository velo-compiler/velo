"""
Automated Test Suite for VeloStudio
Tests SQLite3 C-FFI query subsystem, sample relational database creation,
table schema inspection, query execution, CSV export, and dual-compiler builds.
"""

import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VELO_EXE = ROOT / "bin" / "velo.exe"
UCRT64_BIN = Path(r"C:\msys64\ucrt64\bin")

def get_env() -> dict:
    env = os.environ.copy()
    if UCRT64_BIN.exists():
        env["PATH"] = str(UCRT64_BIN) + os.pathsep + env.get("PATH", "")
    return env


class TestVeloStudio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = get_env()

    def test_native_in_engine_tests_stage2(self):
        """Run native Velo tests via Stage 2 compiler: bin/velo.exe test."""
        cmd = [
            str(VELO_EXE),
            "test",
            "apps/velostudio/test_velostudio.vl",
            "-l",
            "sqlite3",
        ]
        res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=self.env)
        self.assertEqual(res.returncode, 0, f"velo.exe test failed:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}")
        self.assertIn("2 passed; 0 failed", res.stdout)

    def test_native_in_engine_tests_stage1(self):
        """Run native Velo tests via Stage 1 Python compiler: python velo.py test."""
        cmd = [
            "python",
            "velo.py",
            "test",
            "apps/velostudio/test_velostudio.vl",
            "-l",
            "sqlite3",
        ]
        res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=self.env)
        self.assertEqual(res.returncode, 0, f"python velo.py test failed:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}")
        self.assertIn("2 passed; 0 failed", res.stdout)

    def test_build_velostudio_binary(self):
        """Verify standalone GUI binary build with Raylib and SQLite3."""
        out_exe = ROOT / "bin" / "velostudio.exe"
        cmd = [
            str(VELO_EXE),
            "build",
            "apps/velostudio/main.vl",
            "-o",
            str(out_exe),
            "-l", "raylib",
            "-l", "opengl32",
            "-l", "gdi32",
            "-l", "winmm",
            "-l", "sqlite3",
        ]
        res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=self.env)
        self.assertEqual(res.returncode, 0, f"Compilation failed:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}")
        self.assertTrue(out_exe.exists(), "velostudio.exe was not created")
        # Ensure executable is a compact native binary (< 500 KB)
        size = out_exe.stat().st_size
        self.assertLess(size, 500 * 1024, f"velostudio.exe binary unexpectedly large: {size} bytes")


if __name__ == "__main__":
    unittest.main()
