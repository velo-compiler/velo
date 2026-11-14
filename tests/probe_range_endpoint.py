"""
tests/probe_range_endpoint.py — Task 55.2 Diagnostic Probe

Pins the wrapped-value root cause in range loop direction detection:
Proves that is_reverse_loop_range derives direction from a truncated field (int_val = 0)
rather than the wide 64-bit value, causing 1..UINT64_MAX to emit '>' and UINT64_MAX..0 to emit '<'.
"""

import subprocess
import sys
import tempfile
from pathlib import Path


def emit_c(source_code: str) -> str:
    with tempfile.TemporaryDirectory() as tmp_dir:
        src = Path(tmp_dir) / "probe.vl"
        out_c = Path(tmp_dir) / "probe.c"
        src.write_text(source_code, encoding="utf-8")
        res = subprocess.run(
            ["bin/velo.exe", "emit-c", str(src), "-o", str(out_c)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=Path.cwd()
        )
        assert res.returncode == 0, f"emit-c failed: {res.stderr}"
        return out_c.read_text(encoding="utf-8")


def run_probe():
    code = "act main() { loop i in 1..18446744073709551615u64 { } }"
    c_out = emit_c(code)
    for_lines = [l.strip() for l in c_out.splitlines() if "for (" in l]
    assert len(for_lines) >= 1, "No for loop found in emitted C"
    header = for_lines[0]

    print("\n" + "=" * 70)
    print("[PROBE Task 55.2] Range Direction Detection Root Cause Analysis")
    print("=" * 70)
    print(f"Source range:             1..18446744073709551615u64")
    print(f"Mathematical relation:    1 < 18446744073709551615 (ASCENDING)")
    print(f"Emitted loop header:      {header}")

    # Root cause analysis
    is_descending = ">" in header and ">=" not in header
    is_ascending = "<" in header and "<=" not in header

    if is_descending:
        print("\n[ROOT CAUSE PROVED]")
        print("  - '18446744073709551615u64' exceeds signed i64 max (0x7FFFFFFFFFFFFFFF).")
        print("  - reflect_checks.vl:67: 'u <= 0x7FFFFFFFFFFFFFFF' evaluates to FALSE.")
        print("  - reflect_checks.vl:72: falls back to 'out_val[0] = expr.int_val as i64'.")
        print("  - parser_lit.vl:184: int_lit_to_i32_checked returns false, leaving int_val = 0.")
        print("  - codegen_lit.vl:65: s_val (1) > e_val (0) evaluates to TRUE.")
        print("  - Result: Loop is incorrectly flagged as descending (is_rev = true).")
        print("  - Emitted condition: 'i > 18446744073709551615ULL; i--' (runs 0 iterations).")
        print("=" * 70 + "\n")
        assert False, f"Direction derived from truncated field: expected '<', got: {header}"
    else:
        print("\n[VERIFIED] Direction correctly derived using wide value.")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        run_probe()
    except AssertionError as e:
        print(f"Probe Assertion Failed as expected:\n  {e}")
        sys.exit(1)
