"""tests/test_fallback_diagnostics.py — Task 79.2: Remove internal-fallback diagnostics.

Guarantees:
- Every former internal-fallback diagnostic (e.g. 'reached codegen', 'backend:')
  is caught by compile-time semantic analysis and emitted as a proper [Velo Error] semantic:
  diagnostic.
- Zero 'report_error("backend"' calls exist across the compiler codebase.
- No 'reached codegen' or 'backend:' errors are reachable from any source fixture.
"""
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
VELO_BIN = REPO_ROOT / "bin" / "velo.exe"


def run_velo_compile(tmp_path: Path, source: str, stem: str = "probe") -> subprocess.CompletedProcess:
    src_file = tmp_path / f"{stem}.vl"
    src_file.write_text(source, encoding="utf-8")
    return subprocess.run(
        [str(VELO_BIN), "build", str(src_file)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def test_zero_backend_report_error_calls_in_src():
    """Verify that no report_error('backend'...) calls remain in compiler source."""
    src_dir = REPO_ROOT / "src"
    matches = []
    for vl_file in src_dir.rglob("*.vl"):
        lines = vl_file.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines, 1):
            if 'report_error("backend"' in line:
                matches.append(f"{vl_file.relative_to(REPO_ROOT)}:{idx}: {line.strip()}")
    assert not matches, f"Found unexpected backend report_error calls:\n" + "\n".join(matches)


@pytest.mark.parametrize(
    "name,source,expected_msg",
    [
        (
            "io_println_i64_no_import",
            "act main() -> i32 { io.println_i64(42); return 0 }\n",
            "unknown io member 'println_i64'",
        ),
        (
            "io_println_str_no_import",
            'act main() -> i32 { io.println_str("hello"); return 0 }\n',
            "unknown io member 'println_str'",
        ),
        (
            "dyn_in_io_println",
            'use sys.io\nact main() -> i32 {\n    let bad = shelf[5, "s"]\n    io.println(bad[0])\n    return 0\n}\n',
            "shelf[dyn] unbox: raw dyn values must be cast (as) to a concrete type first",
        ),
        (
            "dyn_in_interp_var",
            'use sys.io\nact main() -> i32 {\n    let bad = shelf[5, "s"]\n    let v = bad[0]\n    io.println("v {v}")\n    return 0\n}\n',
            "shelf[dyn] unbox: raw dyn values must be cast (as) to a concrete type first",
        ),
        (
            "if_expr_cond_not_bool",
            "act main() -> i32 { let x = if 123 { 1 } else { 2 }; return x }\n",
            "Condition must be of type 'bool', got 'i32'",
        ),
        (
            "if_stmt_cond_not_bool",
            "act main() -> i32 { if 123 { return 1 } return 0 }\n",
            "Condition must be of type 'bool', got 'i32'",
        ),
        (
            "loop_stmt_cond_not_bool",
            'act main() -> i32 { loop "not_bool" { return 1 } return 0 }\n',
            "Loop expression must be an integer (count) or 'bool' (condition), got 'string'",
        ),
        (
            "range_step_zero",
            "act main() -> i32 { loop i in 0..10:0 { } return 0 }\n",
            "Range loop step must be greater than zero",
        ),
        (
            "io_print_extra_args",
            "act main() -> i32 { io.print(1, 2); return 0 }\n",
            "io.print expects at most 1 argument",
        ),
        (
            "unknown_mem_member",
            "act main() -> i32 { mem.unknown_method(); return 0 }\n",
            "unknown mem member 'unknown_method'",
        ),
        (
            "unknown_str_member",
            'act main() -> i32 { str.unknown_method("foo"); return 0 }\n',
            "unknown str member 'unknown_method'",
        ),
        (
            "unbound_break",
            "act main() -> i32 { break; return 0 }\n",
            "break statement not within a loop",
        ),
        (
            "unbound_continue",
            "act main() -> i32 { continue; return 0 }\n",
            "continue statement not within a loop",
        ),
    ],
)
def test_each_former_fallback_emits_semantic_and_never_backend(tmp_path: Path, name: str, source: str, expected_msg: str):
    res = run_velo_compile(tmp_path, source, stem=name)
    combined = res.stdout + res.stderr
    assert res.returncode != 0, f"Expected compilation failure for {name}, got success:\n{combined}"

    # Invariant: Diagnostic must be emitted at 'semantic' stage
    assert "semantic:" in combined, f"Expected [Velo Error] semantic: in output for {name}:\n{combined}"

    # Invariant: Must match expected error message
    assert expected_msg in combined, f"Expected '{expected_msg}' in output for {name}:\n{combined}"

    # Invariant: Must NEVER leak 'backend:' or 'reached codegen' or 'internal compiler error'
    assert "backend:" not in combined, f"Unexpected 'backend:' diagnostic leaked for {name}:\n{combined}"
    assert "reached codegen" not in combined, f"Unexpected 'reached codegen' leaked for {name}:\n{combined}"
    assert "internal compiler error" not in combined, f"Unexpected internal error leaked for {name}:\n{combined}"
