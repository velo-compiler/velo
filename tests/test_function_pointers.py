import unittest
import subprocess
import sys
from pathlib import Path

class TestFunctionPointers(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.example = self.root_dir / "examples" / "23_function_pointers.vl"

    def test_run_function_pointers(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"run failed: {res.stderr}\nSTDOUT:\n{res.stdout}")
        self.assertIn("Direct call op_add(10, 20): 30", res.stdout)
        self.assertIn("Direct call op_mul(10, 20): 200", res.stdout)
        self.assertIn("apply_binary(7, 8, add): 15", res.stdout)
        self.assertIn("apply_binary(7, 8, multiply): 56", res.stdout)
        self.assertIn("Named handler: Button 101 ('Submit') was clicked!", res.stdout)
        self.assertIn("Anonymous handler: Button 101 clicked anonymously!", res.stdout)
        self.assertIn("apply_binary with inline act: 60", res.stdout)
        self.assertIn("=== Function Pointers Test Complete ===", res.stdout)

    def test_emit_c_function_pointers(self):
        cmd = [sys.executable, str(self.velo_py), "emit-c", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
        self.assertIn("typedef i32 (*velo_act_i32_i32_to_i32)(i32, i32);", res.stdout)
        self.assertIn("typedef void (*velo_act_ptr_Button_to_void)(Button*);", res.stdout)
        self.assertIn("velo_act_ptr_Button_to_void on_click;", res.stdout)
        self.assertIn("_velo_anon_act_0", res.stdout)
        self.assertIn("_velo_anon_act_1", res.stdout)

if __name__ == "__main__":
    unittest.main()
