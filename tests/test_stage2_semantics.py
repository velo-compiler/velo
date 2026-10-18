import unittest
import subprocess
import sys
from pathlib import Path

class TestStage2Semantics(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.example = self.root_dir / "examples" / "12_stage2_semantics_test.vl"

    def test_run_stage2_semantics(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True)
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

    def test_emit_c_stage2_semantics(self):
        cmd = [sys.executable, str(self.velo_py), "emit-c", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
        self.assertIn("typedef struct SymbolTable SymbolTable;", res.stdout)
        self.assertIn("typedef struct Scope Scope;", res.stdout)
        self.assertIn("typedef struct StructSym StructSym;", res.stdout)
        self.assertIn("typedef struct FunctionSym FunctionSym;", res.stdout)
        self.assertIn("check_program((&st), prog)", res.stdout)

if __name__ == "__main__":
    unittest.main()
