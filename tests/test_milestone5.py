import unittest
import subprocess
import sys
from pathlib import Path

class TestMilestone5(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.example = self.root_dir / "examples" / "05_particles.vl"

    def test_run_particles_simulation(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"run failed: {res.stderr}")
        self.assertIn("--- Velo Milestone 5: 2D Particle Simulation ---", res.stdout)
        self.assertIn("Arena memory for particles: 120 bytes", res.stdout)
        self.assertIn("--- Frame 0 ---", res.stdout)
        self.assertIn("--- Frame 1 ---", res.stdout)
        self.assertIn("--- Frame 2 ---", res.stdout)
        self.assertIn("Arena memory after simulation exit: 0 bytes", res.stdout)
        self.assertIn("Milestone 5 Complete! Stage 1 Fully Verified!", res.stdout)

    def test_emit_c_particle_structures(self):
        cmd = [sys.executable, str(self.velo_py), "emit-c", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
        self.assertIn("typedef struct Vec2 Vec2;", res.stdout)
        self.assertIn("typedef struct Particle Particle;", res.stdout)
        self.assertIn("p->pos.x += (p->vel.x * dt);", res.stdout)
        self.assertIn("velo_zone_pop(", res.stdout)

if __name__ == "__main__":
    unittest.main()
