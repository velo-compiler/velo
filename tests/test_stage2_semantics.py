import unittest
import subprocess
import sys
from pathlib import Path
from conftest import velo_exe

class TestStage2Semantics(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.example = self.root_dir / "examples" / "12_stage2_semantics_test.vl"

    @unittest.skip("Historical Stage-1 milestone verification artifact demoted per Task 80.5; Stage-1 is retired")
    def test_run_stage2_semantics(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"run failed: {res.stderr}")
        self.assertIn("--- Velo Stage 2 Milestone 2.3: Semantic Analysis Verification ---", res.stdout)
        self.assertIn("Semantic analysis pass result: true", res.stdout)
        self.assertIn("Total semantic errors reported: 0", res.stdout)
        self.assertIn("Struct 'Point' registered successfully with 2 fields", res.stdout)
        self.assertIn("Field 'x' resolved to type: 'f32'", res.stdout)
        self.assertIn("Field 'y' resolved to type: 'f32'", res.stdout)
        self.assertIn("Function 'scale_point' registered with 2 params, return type: 'f32'", res.stdout)
        self.assertIn("Lexical scope successfully resolved variable 'local_var': type 'i32'", res.stdout)
        self.assertIn("Lexical scope popping verified: 'local_var' no longer accessible after scope exit.", res.stdout)
        self.assertIn("Negative test (type mismatch) successfully caught by analyzer!", res.stdout)
        self.assertIn("Bad code success status (expected false): false", res.stdout)
        self.assertIn("Bad code error count (expected >0): 1", res.stdout)
        self.assertIn("--- Milestone 2.3 Complete! ---", res.stdout)

    @unittest.skip("Historical Stage-1 milestone verification artifact demoted per Task 80.5; Stage-1 is retired")
    def test_emit_c_stage2_semantics(self):
        cmd = [sys.executable, str(self.velo_py), "emit-c", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
        self.assertIn("typedef struct SymbolTable SymbolTable;", res.stdout)
        self.assertIn("typedef struct Scope Scope;", res.stdout)
        self.assertIn("typedef struct StructSym StructSym;", res.stdout)
        self.assertIn("typedef struct FunctionSym FunctionSym;", res.stdout)
        self.assertIn("check_program((&st), prog)", res.stdout)

    def test_immutable_variable_reassignment_rejected(self):
        velo_bin = velo_exe()
        if not velo_bin.exists():
            self.skipTest("bin/velo.exe not built")
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".vl", delete=False) as f:
            f.write("act main() {\n    let num: i64 = 100\n    num = 50\n}\n")
            fname = f.name
        try:
            res = subprocess.run([str(velo_bin), "check", fname], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("cannot assign to immutable variable 'num'. Declare with 'mut num' to allow mutation.", res.stdout)
        finally:
            Path(fname).unlink(missing_ok=True)

    def test_immutable_variable_compound_assign_rejected(self):
        velo_bin = velo_exe()
        if not velo_bin.exists():
            self.skipTest("bin/velo.exe not built")
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".vl", delete=False) as f:
            f.write("act main() {\n    let counter: i32 = 0\n    counter += 1\n}\n")
            fname = f.name
        try:
            res = subprocess.run([str(velo_bin), "check", fname], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("cannot assign to immutable variable 'counter'. Declare with 'mut counter' to allow mutation.", res.stdout)
        finally:
            Path(fname).unlink(missing_ok=True)

    def test_immutable_struct_field_mutation_rejected(self):
        velo_bin = velo_exe()
        if not velo_bin.exists():
            self.skipTest("bin/velo.exe not built")
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".vl", delete=False) as f:
            f.write("data Point { x: f32, y: f32 }\nact main() {\n    let pt = Point{ x: 1.0, y: 2.0 }\n    pt.x = 5.0\n}\n")
            fname = f.name
        try:
            res = subprocess.run([str(velo_bin), "check", fname], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("cannot assign to field of immutable variable 'pt'. Declare with 'mut pt' to allow mutation.", res.stdout)
        finally:
            Path(fname).unlink(missing_ok=True)

    def test_mutable_variable_assignment_allowed(self):
        velo_bin = velo_exe()
        if not velo_bin.exists():
            self.skipTest("bin/velo.exe not built")
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".vl", delete=False) as f:
            f.write("act main() {\n    mut num: i64 = 100\n    num = 50\n    mut count: i32 = 0\n    count += 1\n}\n")
            fname = f.name
        try:
            res = subprocess.run([str(velo_bin), "check", fname], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(res.returncode, 0, f"Check failed: {res.stdout}")
        finally:
            Path(fname).unlink(missing_ok=True)

    def test_undeclared_identifier_rejected(self):
        velo_bin = velo_exe()
        if not velo_bin.exists():
            self.skipTest("bin/velo.exe not built")
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".vl", delete=False) as f:
            f.write("act main() {\n    let val = undeclared_identifier_xyz\n}\n")
            fname = f.name
        try:
            res = subprocess.run([str(velo_bin), "check", fname], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("Undeclared identifier", res.stdout)
        finally:
            Path(fname).unlink(missing_ok=True)

    def test_type_mismatch_rejected(self):
        velo_bin = velo_exe()
        if not velo_bin.exists():
            self.skipTest("bin/velo.exe not built")
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".vl", delete=False) as f:
            f.write("act main() {\n    let num: i32 = \"string value\"\n}\n")
            fname = f.name
        try:
            res = subprocess.run([str(velo_bin), "check", fname], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("Type mismatch", res.stdout)
        finally:
            Path(fname).unlink(missing_ok=True)

    def test_valid_semantics_check(self):
        velo_bin = velo_exe()
        if not velo_bin.exists():
            self.skipTest("bin/velo.exe not built")
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".vl", delete=False) as f:
            f.write("data Point { x: f32, y: f32 }\nact scale(p: @Point, f: f32) -> f32 {\n    return (p.x + p.y) * f\n}\nact main() {\n    let pt = Point{ x: 1.0, y: 2.0 }\n    let ans = scale(@pt, 2.5)\n}\n")
            fname = f.name
        try:
            res = subprocess.run([str(velo_bin), "check", fname], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(res.returncode, 0, f"Check failed: {res.stdout}")
        finally:
            Path(fname).unlink(missing_ok=True)

if __name__ == "__main__":
    unittest.main()
