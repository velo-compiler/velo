"""Verify SHA-256 fixed-point between Gen2 and Gen3 emit-c output.

Release-gate script: both compilers must produce byte-identical C for
`src/main.vl`. A match is the proof that the bootstrap chain has reached a
fixed point and that `bootstrap.c` can be regenerated safely.

ENCODING CONTRACT
-----------------
This script's output is encoding-independent. It prints ASCII only, so it
cannot raise `UnicodeEncodeError` on a cp1252 console, a latin-1 CI runner,
or a UTF-8 terminal: the status text is identical everywhere and no locale
detection is involved. Do not reintroduce non-ASCII glyphs (for example a
check mark or an em dash) in any message: on Windows the default console
codec is cp1252, and the resulting `UnicodeEncodeError` arrives *after* the
hashes have already matched, turning a successful determinism check into a
CI failure.

Run it from the repository root: `python scripts/check_determinism.py`.
Exit status is 0 when Gen2 and Gen3 agree and non-zero otherwise.
"""
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = str(ROOT / "src" / "main.vl")


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


def emit_c(path: str, label: str):
    """Run `emit-c` and return its stdout bytes, or exit with its status."""
    proc = subprocess.run([path, "emit-c", SRC], capture_output=True, cwd=str(ROOT))
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace")
        print(f"{label} emit-c failed with code {proc.returncode}:\n{stderr}")
        sys.exit(proc.returncode)
    return proc.stdout


def main() -> int:
    g2_out = emit_c(find_bin("velo_gen2"), "Gen2")
    g3_out = emit_c(find_bin("velo_gen3"), "Gen3")

    h2 = hashlib.sha256(g2_out).hexdigest()
    h3 = hashlib.sha256(g3_out).hexdigest()
    print(f"Gen2: {h2}")
    print(f"Gen3: {h3}")

    if h2 == h3:
        # ASCII only: see the ENCODING CONTRACT above.
        print("SHA-256 MATCH - bootstrap chain is deterministic")
        return 0
    print("SHA-256 DIVERGED! Gen2 and Gen3 differ.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
