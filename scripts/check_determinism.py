"""Verify SHA-256 fixed-point between Gen2 and Gen3 emit-c output."""
import subprocess, hashlib, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
src = str(ROOT / "src" / "main.vl")

def find_bin(name: str) -> str:
    # Check with .exe on Windows or without on POSIX; handle either existing
    candidates = [
        ROOT / "bin" / (name + ".exe" if sys.platform == "win32" else name),
        ROOT / "bin" / (name if sys.platform == "win32" else name + ".exe"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return str(candidates[0])

g2_path = find_bin("velo_gen2")
g3_path = find_bin("velo_gen3")

g2 = subprocess.run([g2_path, "emit-c", src], capture_output=True, cwd=str(ROOT))
g3 = subprocess.run([g3_path, "emit-c", src], capture_output=True, cwd=str(ROOT))

if g2.returncode != 0:
    print(f"Gen2 emit-c failed with code {g2.returncode}:\n{g2.stderr.decode('utf-8', errors='replace')}")
    sys.exit(g2.returncode)
if g3.returncode != 0:
    print(f"Gen3 emit-c failed with code {g3.returncode}:\n{g3.stderr.decode('utf-8', errors='replace')}")
    sys.exit(g3.returncode)

h2 = hashlib.sha256(g2.stdout).hexdigest()
h3 = hashlib.sha256(g3.stdout).hexdigest()
print(f"Gen2: {h2}")
print(f"Gen3: {h3}")
if h2 == h3:
    print("SHA-256 MATCH \u2713 \u2014 bootstrap chain is deterministic")
    sys.exit(0)
else:
    print("SHA-256 DIVERGED! Gen2 and Gen3 differ.")
    sys.exit(1)
