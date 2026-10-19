import unittest
import subprocess
import sys
from pathlib import Path

class TestEnumsAndUnions(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.example = self.root_dir / "examples" / "21_enums_and_unions.vl"

    def test_run_enums_and_unions(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"run failed: {res.stderr}\nSTDOUT:\n{res.stdout}")
        self.assertIn("Facing North", res.stdout)
        self.assertIn("Facing East", res.stdout)
        self.assertIn("HTTP status is OK (200)", res.stdout)
        self.assertIn("Event: Quit application", res.stdout)
        self.assertIn("Event: KeyDown = 65", res.stdout)
        self.assertIn("Event: Click button 1 at (120.50, 340.00)", res.stdout)
        self.assertIn("All Enum & Tagged Union tests passed successfully!", res.stdout)

    def test_emit_c_enums_and_unions(self):
        cmd = [sys.executable, str(self.velo_py), "emit-c", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
        self.assertIn("typedef int32_t Direction;", res.stdout)
        self.assertIn("Direction_North = 0,", res.stdout)
        self.assertIn("HttpStatus_Ok = 200,", res.stdout)
        self.assertIn("HttpStatus_NotFound = 404,", res.stdout)
        self.assertIn("typedef struct Event Event;", res.stdout)
        self.assertIn("typedef struct Event_Click_Payload", res.stdout)
        self.assertIn("int32_t kind;", res.stdout)
        self.assertIn("switch (e.kind)", res.stdout)

if __name__ == "__main__":
    unittest.main()
