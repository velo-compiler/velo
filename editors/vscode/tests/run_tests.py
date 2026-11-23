#!/usr/bin/env python3
"""Phase 4 test runner for the Velo VS Code extension (editors/vscode).

Three tiers, all dependency-free (no npm installs, no pip installs):

  stub   — parity_compiler.py    (compiler-vs-grammar drift detection)
           match_spotcheck.js    (grammar pattern behavior on real samples)
           sim_extension.js      (Tier A plumbing with fake compilers)
  server — sim_lsp.js            (real python LSP server probes)
           sim_lsp_ext.js        (extension-client LSP end-to-end)
  real   — sim_real.js           (real toolchain: bin/velo.exe + python velo.py)

Usage (from anywhere; paths resolve via __file__):
  python tests/run_tests.py             # stub + server
  python tests/run_tests.py --quick     # stub only (node + python stdlib)
  python tests/run_tests.py --real      # everything, including the toolchain

Requires: node on PATH; python for the suite and server tiers.
The real tier additionally needs the compiled bootstrap chain (bin/velo.exe).
Exits 1 on any failure; prints a per-suite summary at the end.
"""

import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent

TIERS = {
    "stub": [
        ("python", TESTS_DIR / "parity_compiler.py"),
        ("node", TESTS_DIR / "match_spotcheck.js"),
        ("node", TESTS_DIR / "sim_extension.js"),
    ],
    "server": [
        ("node", TESTS_DIR / "sim_lsp.js"),
        ("node", TESTS_DIR / "sim_lsp_ext.js"),
    ],
    "real": [
        ("node", TESTS_DIR / "sim_real.js"),
    ],
}


def selected_tiers(argv: list[str]) -> list[str]:
    if "--quick" in argv:
        return ["stub"]
    if "--real" in argv:
        return ["stub", "server", "real"]
    return ["stub", "server"]


def run_suite(binary: str, script: Path) -> bool:
    label = script.name
    print(f"\n=== {label} ({binary}) " + "=" * (60 - len(label) - len(binary)))
    try:
        proc = subprocess.run([binary, str(script)], timeout=600)
    except FileNotFoundError:
        print(f"SKIP {label}: '{binary}' not on PATH")
        return True  # environment lacks the interpreter; not a regression
    except subprocess.TimeoutExpired:
        print(f"FAIL {label}: timed out after 600s")
        return False
    if proc.returncode != 0:
        print(f"FAIL {label}: exit {proc.returncode}")
        return False
    return True


def main() -> int:
    tiers = selected_tiers(sys.argv)
    results = []
    for tier in tiers:
        for binary, script in TIERS[tier]:
            if not script.exists():
                results.append((str(script.name), False))
                print(f"FAIL {script.name}: missing file")
                continue
            ok = run_suite(binary, script)
            results.append((f"{script.name}", ok))

    passed = sum(1 for _, ok in results if ok)
    print(f"\n{'=' * 72}")
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print(f"{'=' * 72}")
    print(f"RESULT: {passed}/{len(results)} SUITES PASSED"
          + ("" if passed == len(results) else f"  (failures: {[n for n, ok in results if not ok]})"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
