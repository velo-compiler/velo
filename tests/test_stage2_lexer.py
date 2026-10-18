import unittest
import subprocess
import sys
from pathlib import Path

class TestStage2Lexer(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.example = self.root_dir / "examples" / "10_stage2_lexer_test.vl"

    def test_run_stage2_lexer(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"run failed: {res.stderr}")
        self.assertIn("--- Velo Stage 2 Milestone 2.1: Native Lexer Verification ---", res.stdout)
        self.assertIn("Successfully tokenized sample Velo source code!", res.stdout)
        self.assertIn("Total tokens produced: 35", res.stdout)
        self.assertIn("Token[0]: kind=21 (data), len=4, line=1", res.stdout)
        self.assertIn("Token 0 name: data", res.stdout)
        self.assertIn("Token 1 name: IDENTIFIER", res.stdout)
        self.assertIn("Token 2 name: {", res.stdout)
        self.assertIn("--- Milestone 2.1 Complete! ---", res.stdout)

    def test_emit_c_stage2_lexer(self):
        cmd = [sys.executable, str(self.velo_py), "emit-c", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
        self.assertIn("typedef struct Lexer Lexer;", res.stdout)
        self.assertIn("typedef struct Token Token;", res.stdout)
        self.assertIn("tokenize((&lex));", res.stdout)

if __name__ == "__main__":
    unittest.main()
