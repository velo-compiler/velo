import unittest
import subprocess
import sys
from pathlib import Path

class TestMilestone22(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.example = self.root_dir / "examples" / "07_file_io.vl"

    def test_run_file_io(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"run failed: {res.stderr}")
        self.assertIn("--- Velo Milestone 2.2: Standard File I/O ---", res.stdout)
        self.assertIn("File exists before write: false", res.stdout)
        self.assertIn("Successfully wrote payload to: velo_fs_test_temp.txt", res.stdout)
        self.assertIn("File exists after write: true", res.stdout)
        self.assertIn("File size in bytes: 34", res.stdout)
        self.assertIn("Heap with read buffer active: 35 bytes", res.stdout)
        self.assertIn("Read file content: Velo Native File System I/O Works!", res.stdout)
        self.assertIn("Content match verified: read content == sample payload!", res.stdout)
        self.assertIn("Heap after buffer freed: 0 bytes (zero leaks!)", res.stdout)
        self.assertIn("Missing file read returned null as expected", res.stdout)
        self.assertIn("File exists after removal: false", res.stdout)
        self.assertIn("--- Milestone 2.2 Complete! ---", res.stdout)

    def test_emit_c_file_io_primitives(self):
        cmd = [sys.executable, str(self.velo_py), "emit-c", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
        self.assertIn("velo_fs_exists(test_file)", res.stdout)
        self.assertIn("velo_fs_write_file(test_file, sample_payload)", res.stdout)
        self.assertIn("velo_fs_size(test_file)", res.stdout)
        self.assertIn("velo_fs_read_file(test_file)", res.stdout)
        self.assertIn("velo_fs_remove(test_file)", res.stdout)
        self.assertIn("strcmp(content, sample_payload) == 0", res.stdout)

if __name__ == "__main__":
    unittest.main()
