"""Verify SHA-256 fixed-point between Gen2 and Gen3 emit-c output."""
import subprocess, hashlib, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
src = str(ROOT / "src" / "main.vl")

g2 = subprocess.run([str(ROOT / "bin" / "velo_gen2.exe"), "emit-c", src],
                    capture_output=True, cwd=str(ROOT))
g3 = subprocess.run([str(ROOT / "bin" / "velo_gen3.exe"), "emit-c", src],
                    capture_output=True, cwd=str(ROOT))

h2 = hashlib.sha256(g2.stdout).hexdigest()
h3 = hashlib.sha256(g3.stdout).hexdigest()
print(f"Gen2: {h2}")
print(f"Gen3: {h3}")
if h2 == h3:
    print("SHA-256 MATCH ✓ — bootstrap chain is deterministic")
    sys.exit(0)
else:
    print("SHA-256 DIVERGED! Gen2 and Gen3 differ.")
    sys.exit(1)
