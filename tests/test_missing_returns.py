import os
import sys
import subprocess
import unittest
import tempfile
from pathlib import Path
from conftest import cc_dir, velo_exe

class TestMissingReturns(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.velo_exe = velo_exe()
        self.env = os.environ.copy()
        if cc_dir() not in self.env.get("PATH", ""):
            self.env["PATH"] = cc_dir() + ";" + self.env.get("PATH", "")

    def _check_program_fails(self, code: str, expected_snippet: str):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "test_missing.vl"
            src_file.write_text(code, encoding="utf-8")

            # Stage 1 (Python)
            res1 = subprocess.run([sys.executable, str(self.velo_py), "check", str(src_file)],
                                  capture_output=True, text=True, env=self.env)
            self.assertNotEqual(res1.returncode, 0, f"Stage 1 should fail check but succeeded:\nSTDOUT:\n{res1.stdout}\nSTDERR:\n{res1.stderr}")
            combined_err1 = res1.stdout + res1.stderr
            self.assertIn(expected_snippet, combined_err1)

            # Stage 2 (Self-hosted)
            res2 = subprocess.run([str(self.velo_exe), "check", str(src_file)],
                                  capture_output=True, text=True, env=self.env)
            self.assertNotEqual(res2.returncode, 0, f"Stage 2 should fail check but succeeded:\nSTDOUT:\n{res2.stdout}\nSTDERR:\n{res2.stderr}")
            combined_err2 = res2.stdout + res2.stderr
            self.assertIn(expected_snippet, combined_err2)

    def _check_program_passes(self, code: str):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "test_valid.vl"
            src_file.write_text(code, encoding="utf-8")

            # Stage 1 (Python)
            res1 = subprocess.run([sys.executable, str(self.velo_py), "check", str(src_file)],
                                  capture_output=True, text=True, env=self.env)
            self.assertEqual(res1.returncode, 0, f"Stage 1 failed check:\nSTDOUT:\n{res1.stdout}\nSTDERR:\n{res1.stderr}")

            # Stage 2 (Self-hosted)
            res2 = subprocess.run([str(self.velo_exe), "check", str(src_file)],
                                  capture_output=True, text=True, env=self.env)
            self.assertEqual(res2.returncode, 0, f"Stage 2 failed check:\nSTDOUT:\n{res2.stdout}\nSTDERR:\n{res2.stderr}")

    def test_missing_return_in_if_without_else(self):
        code = """
act pick(flag: bool) -> i32 {
    if flag { return 7 }
}
act main() {}
"""
        self._check_program_fails(code, "missing return statement on control path in function 'pick'")

    def test_missing_return_in_else_if_without_final_else(self):
        code = """
act compute(x: i32) -> i32 {
    if x == 1 {
        return 10
    } else if x == 2 {
        return 20
    }
}
act main() {}
"""
        self._check_program_fails(code, "missing return statement on control path in function 'compute'")

    def test_valid_return_in_if_else(self):
        code = """
act pick(flag: bool) -> i32 {
    if flag {
        return 7
    } else {
        return 8
    }
}
act main() {}
"""
        self._check_program_passes(code)

    def test_empty_return_in_non_void_function(self):
        code = """
act pick(flag: bool) -> i32 {
    return
}
act main() {}
"""
        self._check_program_fails(code, "A function returning a value must return an expression")

    def test_match_missing_variant(self):
        code = """
kind Status {
    Ok
    Err
}

act handle(s: Status) -> i32 {
    on s {
        Status.Ok => { return 1 }
    }
}
act main() {}
"""
        self._check_program_fails(code, "missing return statement on control path in function 'handle'")

    def test_match_all_variants_covered(self):
        code = """
kind Status {
    Ok
    Err
}

act handle(s: Status) -> i32 {
    on s {
        Status.Ok => { return 1 }
        Status.Err => { return 2 }
    }
}
act main() {}
"""
        self._check_program_passes(code)

    def test_match_with_default(self):
        code = """
kind Status {
    Ok
    Err
}

act handle(s: Status) -> i32 {
    on s {
        Status.Ok => { return 1 }
        _ => { return 0 }
    }
}
act main() {}
"""
        self._check_program_passes(code)

    def test_void_function_and_main_no_return_allowed(self):
        code = """
act do_nothing() {
    let x = 1
}

act do_void() -> void {
    let y = 2
}

act main() {
    do_nothing()
    do_void()
}
"""
        self._check_program_passes(code)

    def test_os_exit_counts_as_return(self):
        code = """
act terminate() -> i32 {
    os.exit(1)
}
act main() {}
"""
        self._check_program_passes(code)

if __name__ == "__main__":
    unittest.main()

