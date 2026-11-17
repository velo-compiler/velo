import unittest
import subprocess
import sys
from pathlib import Path

class TestMilestone21(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.example = self.root_dir / "examples" / "06_heap_and_defer.vl"

    def test_run_heap_and_defer(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"run failed: {res.stderr}")
        self.assertIn("--- Velo Milestone 2.1: Persistent Heap & Defer ---", res.stdout)
        self.assertIn("Initial active heap: 0 bytes", res.stdout)
        self.assertIn("Active heap memory allocated: 120 bytes", res.stdout)
        self.assertIn("Early exit condition met! Returning now...", res.stdout)
        self.assertIn("[defer 2] buf2 freed", res.stdout)
        self.assertIn("[defer 1] buf1 freed", res.stdout)
        self.assertIn("Heap after early exit: 0 bytes (zero leaks!)", res.stdout)
        self.assertIn("Final active heap: 0 bytes (zero leaks!)", res.stdout)
        self.assertIn("Null pointer check passed: empty_ptr == null", res.stdout)
        self.assertIn("--- Milestone 2.1 Complete! ---", res.stdout)

    def test_emit_c_heap_and_defer(self):
        cmd = [sys.executable, str(self.velo_py), "emit-c", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
        self.assertIn("velo_heap_alloc(sizeof(i32), (size_t)(10))", res.stdout)
        self.assertIn("velo_heap_alloc(sizeof(i32), (size_t)(20))", res.stdout)
        self.assertIn("velo_heap_free((void*)(buf2))", res.stdout)
        self.assertIn("velo_heap_free((void*)(buf1))", res.stdout)
        self.assertIn("void* empty_ptr = NULL;", res.stdout)

if __name__ == "__main__":
    unittest.main()
