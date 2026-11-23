"""
Task 79.1: Error Code Registry & Diagnostic Code Emission.

Verifies:
1. docs/ERRORS.md exists and registers all error codes VELO-E0001 through VELO-E0020.
2. `velo explain <CODE>` returns valid explanations for every registered code.
3. Every registered error code in the registry is emitted by at least one test fixture.
4. Structured JSON diagnostic output carries the stable error code prefix.
"""

import os
import re
import subprocess
from pathlib import Path
import pytest
from conftest import cc_dir, velo_exe

pytestmark = pytest.mark.fast

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()
ERRORS_DOC = REPO_ROOT / "docs" / "ERRORS.md"


def get_env():
    env = os.environ.copy()
    if cc_dir() not in env.get("PATH", ""):
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return env


def test_errors_md_registry_inventory():
    """Asserts that docs/ERRORS.md exists and documents all 20 error codes."""
    assert ERRORS_DOC.is_file(), f"Missing error documentation: {ERRORS_DOC}"
    content = ERRORS_DOC.read_text(encoding="utf-8")
    for i in range(1, 21):
        code = f"VELO-E{i:04d}"
        assert code in content, f"Code {code} missing from docs/ERRORS.md"


def test_velo_explain_cli():
    """Tests that `velo explain <CODE>` works for all 20 registered codes and various aliases."""
    for i in range(1, 21):
        code = f"VELO-E{i:04d}"
        res = subprocess.run(
            [str(VELO_EXE), "explain", code],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=get_env()
        )
        assert res.returncode == 0, f"velo explain {code} failed with code {res.returncode}"
        assert code in res.stdout, f"Expected {code} in explain output: {res.stdout}"

    # Also test normalization: "E0001" and "0001"
    res_short = subprocess.run([str(VELO_EXE), "explain", "E0001"], capture_output=True, text=True, env=get_env())
    assert res_short.returncode == 0 and "VELO-E0001" in res_short.stdout

    res_num = subprocess.run([str(VELO_EXE), "explain", "0001"], capture_output=True, text=True, env=get_env())
    assert res_num.returncode == 0 and "VELO-E0001" in res_num.stdout


# Fixture matrix: (Code, Source code snippet, Extra CLI flags)
FIXTURE_MATRIX = [
    ("VELO-E0001", "act main() -> i32 { return foo }", []),
    ("VELO-E0002", "act f(a: i32) -> i32 { return a }\nact main() -> i32 { return f(1, 2) }", []),
    ("VELO-E0003", "act main() -> i32 { let a: [2]i32 = [1, 2]; return a[5] }", []),
    ("VELO-E0004", 'act main() -> i32 { let a: [2]i32 = [1, 2]; return a["bad"] }', []),
    ("VELO-E0005", "act main() -> i32 { return 10 / 0 }", []),
    ("VELO-E0006", "act main() -> i32 { return 10 % 0 }", []),
    ("VELO-E0007", "act main() -> i32 { let s = UnknownStruct { x: 1 }; return 0 }", []),
    ("VELO-E0008", "data Pt { x: i32 }\nact main() -> i32 { let p = Pt { x: 1, y: 2 }; return 0 }", []),
    ("VELO-E0009", "data Pt { x: i32, y: i32 }\nact main() -> i32 { let p = Pt { x: 1 }; return 0 }", []),
    ("VELO-E0010", 'act main() -> i32 { let a = [1, "two"]; return 0 }', []),
    ("VELO-E0011", "act main() -> i32 { let x = .NoSuchVariant; return 0 }", []),
    ("VELO-E0012", "kind Shape { Rect(w: f64, h: f64) }\nact main() -> i32 { let s = Shape.Rect(1.0); return 0 }", []),
    ("VELO-E0013", "act main() -> i32 { let t = (1, 2); return t.5 }", []),
    ("VELO-E0014", "act main() -> i32 { loop i in 0..10:0 { } return 0 }", []),
    ("VELO-E0015", "use std.coll\nact main() -> i32 { let s = shelf[null]; return 0 }", []),
    ("VELO-E0016", "act vf() {}\nact main() -> i32 { mut s: shelf[dyn] = shelf[1, \"two\"]; s.put(vf()); return 0 }", []),
    ("VELO-E0017", 'act main() -> i32 { let m = map["key": null]; return 0 }', []),
    ("VELO-E0018", "act main() -> i32 { let s = shelf[]; return 0 }", []),
    ("VELO-E0019", "act main() -> i32 { let r = ring[]; return 0 }", []),
    ("VELO-E0020", "act main() -> i32 { let p: @i32 = null; return p[0] }", ["--strict-safety"]),
]


@pytest.mark.parametrize("code, source, flags", FIXTURE_MATRIX)
def test_each_registered_error_code_is_emitted(tmp_path, code, source, flags):
    """Verifies that every code in the registry is emitted by at least one test fixture."""
    test_file = tmp_path / f"test_{code}.vl"
    test_file.write_text(source, encoding="utf-8")

    cmd = [str(VELO_EXE), "check", str(test_file)] + flags
    res = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=get_env()
    )
    assert res.returncode != 0, f"Expected check to fail for {code}, but passed:\n{res.stdout}"
    out = res.stdout + res.stderr
    assert f"[{code}]" in out, f"Error code [{code}] not found in output for fixture:\n{out}"


def test_json_diagnostics_preserves_error_code(tmp_path):
    """Verifies that `velo check --json` outputs diagnostics containing the error code."""
    import json
    test_file = tmp_path / "test_json_diag.vl"
    test_file.write_text("act main() -> i32 { return foo }", encoding="utf-8")

    cmd = [str(VELO_EXE), "check", str(test_file), "--json"]
    res = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=get_env()
    )
    assert res.returncode != 0
    report = json.loads(res.stdout)
    assert report["ok"] is False
    assert any("[VELO-E0001]" in d["message"] for d in report["diagnostics"])
