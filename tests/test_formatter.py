import unittest
import subprocess
import os
import shutil
from pathlib import Path
from conftest import velo_exe

class TestVeloFormatter(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_exe = velo_exe()
        self.assertTrue(self.velo_exe.exists(), "bin/velo.exe does not exist")
        self.cache_dir = self.root_dir / ".velo_cache" / "fmt_tests"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir, ignore_errors=True)

    def test_fmt_help_flag(self):
        res = subprocess.run([str(self.velo_exe), "fmt", "--help"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Usage: velo fmt [path] [--check]", res.stdout)
        self.assertIn("--check", res.stdout)

    def test_fmt_check_fails_on_unformatted(self):
        test_file = self.cache_dir / "unformatted.vl"
        test_file.write_text("act foo(a:i32,b:i32)->i32{return a+b}\n", encoding="utf-8")

        res = subprocess.run([str(self.velo_exe), "fmt", str(test_file), "--check"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 1, "Expected exit code 1 for unformatted file")
        self.assertIn("File is not formatted", res.stdout)
        self.assertIn("Diff at line", res.stdout)

    def test_fmt_in_place_and_subsequent_check(self):
        test_file = self.cache_dir / "format_me.vl"
        raw_code = (
            "use std.io\n"
            "act calculate(a:i32,b:i32)->i32{\n"
            "mut res:i32=a+b*2\n"
            "if res>10{\n"
            "io.println(\"large\")\n"
            "}else{\n"
            "io.println(\"small\")\n"
            "}\n"
            "return res\n"
            "}\n"
        )
        test_file.write_text(raw_code, encoding="utf-8")

        # 1. Format in-place
        res_fmt = subprocess.run([str(self.velo_exe), "fmt", str(test_file)], capture_output=True, text=True)
        self.assertEqual(res_fmt.returncode, 0, f"velo fmt failed: {res_fmt.stderr}")
        self.assertIn("Formatted:", res_fmt.stdout)

        # 2. Check content
        formatted_text = test_file.read_text(encoding="utf-8")
        expected_text = (
            "use std.io\n"
            "act calculate(a: i32, b: i32) -> i32 {\n"
            "    mut res: i32 = a + b * 2\n"
            "    if res > 10 {\n"
            "        io.println(\"large\")\n"
            "    } else {\n"
            "        io.println(\"small\")\n"
            "    }\n"
            "    return res\n"
            "}\n"
        )
        self.assertEqual(formatted_text, expected_text)

        # 3. Subsequent check returns 0
        res_check = subprocess.run([str(self.velo_exe), "fmt", str(test_file), "--check"], capture_output=True, text=True)
        self.assertEqual(res_check.returncode, 0, f"Expected 0 on formatted file: {res_check.stdout}")
        self.assertIn("File is properly formatted", res_check.stdout)

    def test_fmt_idempotency_second_pass(self):
        test_file = self.cache_dir / "idempotent.vl"
        sample_code = (
            "// Header doc comment\n"
            "use std.io\n"
            "\n"
            "data Point {\n"
            "    x: i32\n"
            "    y: i32\n"
            "}\n"
            "\n"
            "act make_point(px: i32, py: i32) -> Point {\n"
            "    if px < 0 { return Point{ x: 0, y: 0 } }\n"
            "    return Point{ x: px, y: py }\n"
            "}\n"
        )
        test_file.write_text(sample_code, encoding="utf-8")

        # Pass 1
        subprocess.run([str(self.velo_exe), "fmt", str(test_file)], check=True)
        pass1_text = test_file.read_text(encoding="utf-8")

        # Pass 2
        subprocess.run([str(self.velo_exe), "fmt", str(test_file)], check=True)
        pass2_text = test_file.read_text(encoding="utf-8")

        self.assertEqual(pass1_text, pass2_text, "Formatting must be strictly idempotent")

    def test_fmt_preserves_comments(self):
        test_file = self.cache_dir / "comments.vl"
        raw_code = (
            "/// Module doc comment\n"
            "use std.io\n"
            "\n"
            "/* Multi-line\n"
            " * block comment */\n"
            "act run() -> i32 {\n"
            "    let x = 10 // trailing inline comment\n"
            "    // Standalone comment inside block\n"
            "    return x\n"
            "}\n"
        )
        test_file.write_text(raw_code, encoding="utf-8")

        subprocess.run([str(self.velo_exe), "fmt", str(test_file)], check=True)
        formatted = test_file.read_text(encoding="utf-8")

        self.assertIn("/// Module doc comment", formatted)
        self.assertIn("/* Multi-line\n * block comment */", formatted)
        self.assertIn("let x = 10 // trailing inline comment", formatted)
        self.assertIn("    // Standalone comment inside block", formatted)

    def test_fmt_directory_recursive(self):
        sub1 = self.cache_dir / "sub1"
        sub2 = self.cache_dir / "sub2"
        sub1.mkdir(parents=True, exist_ok=True)
        sub2.mkdir(parents=True, exist_ok=True)

        f1 = sub1 / "a.vl"
        f2 = sub2 / "b.vl"
        f1.write_text("act a()->i32{return 1}\n", encoding="utf-8")
        f2.write_text("act b()->i32{return 2}\n", encoding="utf-8")

        # Format entire directory
        res = subprocess.run([str(self.velo_exe), "fmt", str(self.cache_dir)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

        # Verify both formatted
        res_check = subprocess.run([str(self.velo_exe), "fmt", str(self.cache_dir), "--check"], capture_output=True, text=True)
        self.assertEqual(res_check.returncode, 0)
        self.assertIn("All files properly formatted", res_check.stdout)

    def test_fmt_execution_semantic_preservation(self):
        test_file = self.cache_dir / "run_test.vl"
        raw_code = (
            "use sys.io\n"
            "act main()->i32{\n"
            "let a=20\n"
            "let b=22\n"
            "let sum=a+b\n"
            "io.println(\"formatted sum: {sum}\")\n"
            "return 0\n"
            "}\n"
        )
        test_file.write_text(raw_code, encoding="utf-8")

        # Format
        subprocess.run([str(self.velo_exe), "fmt", str(test_file)], check=True)

        # Run with velo run
        res = subprocess.run([str(self.velo_exe), "run", str(test_file)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"velo run failed: {res.stderr}")
        self.assertIn("formatted sum: 42", res.stdout)

if __name__ == "__main__":
    unittest.main()

