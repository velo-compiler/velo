import unittest
import subprocess
import sys
from pathlib import Path

class TestMilestone24(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.entry_file = self.root_dir / "examples" / "09_self_hosting_readiness" / "main.vl"

    def test_run_self_hosting_readiness(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.entry_file)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"run failed: {res.stderr}")
        self.assertIn("--- Velo Milestone 2.4: Self-Hosting Readiness Test ---", res.stdout)
        self.assertIn("Target file exists on disk: true", res.stdout)
        self.assertIn("Target file size: 85 bytes", res.stdout)
        self.assertIn("Active heap during tokenization: 86 bytes", res.stdout)
        self.assertIn("--- Lexer Summary ---", res.stdout)
        self.assertIn("Total characters processed: 85", res.stdout)
        self.assertIn("Total tokens identified: 27", res.stdout)
        self.assertIn("Active heap after defer cleanup: 0 bytes (zero leaks!)", res.stdout)
        self.assertIn("--- Self-Hosting Readiness: 100% PASSED! ---", res.stdout)
        self.assertIn("--- Stage 1 and Step 2 Complete! Ready for Stage 2 (Self-Hosting)! ---", res.stdout)

    def test_emit_c_readiness_pipeline(self):
        cmd = [sys.executable, str(self.velo_py), "emit-c", str(self.entry_file)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
        self.assertIn("typedef struct Token Token;", res.stdout)
        self.assertIn("typedef struct LexerSummary LexerSummary;", res.stdout)
        self.assertIn("LexerSummary tokenize_source(const char* content, i32 len);", res.stdout)
        self.assertIn("velo_fs_read_file(", res.stdout)
        self.assertIn("velo_heap_free((void*)(source));", res.stdout)

if __name__ == "__main__":
    unittest.main()
