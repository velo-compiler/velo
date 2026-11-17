import unittest
import subprocess
import sys
from pathlib import Path

class TestStage2Parser(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.example = self.root_dir / "examples" / "11_stage2_parser_test.vl"

    def test_run_stage2_parser(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"run failed: {res.stderr}")
        self.assertIn("--- Velo Stage 2 Milestone 2.2: Native Parser Verification ---", res.stdout)
        self.assertIn("Total declarations parsed: 3", res.stdout)
        self.assertIn("Decl[0]: Struct 'data Point' with 2 fields", res.stdout)
        self.assertIn("Decl[1]: Extern 'extern act clock' -> 'i64'", res.stdout)
        self.assertIn("Decl[2]: Function 'act compute' -> 'f32' with 2 params", res.stdout)
        self.assertIn("Param: 'p' of type '@Point'", res.stdout)
        self.assertIn("Param: 'delta' of type 'f32'", res.stdout)
        self.assertIn("Function body contains 6 top-level statements in block", res.stdout)
        self.assertIn("Parser error status: false", res.stdout)
        self.assertIn("--- Milestone 2.2 Complete! ---", res.stdout)

    def test_emit_c_stage2_parser(self):
        cmd = [sys.executable, str(self.velo_py), "emit-c", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
        self.assertIn("typedef struct Parser Parser;", res.stdout)
        self.assertIn("typedef struct ExprNode ExprNode;", res.stdout)
        self.assertIn("typedef struct StmtNode StmtNode;", res.stdout)
        self.assertIn("typedef struct ProgramNode ProgramNode;", res.stdout)
        self.assertIn("parse_program((&p))", res.stdout)

if __name__ == "__main__":
    unittest.main()
