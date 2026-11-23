"""
tests/test_error_recovery.py

Error-recovery assertions for the Velo compiler.
Asserts that after any single-error input:
1. The diagnostic list is non-empty (at least one user-facing diagnostic emitted).
2. The output contains NO internal "backend:" or "reached codegen" messages.
3. The process exit code is in the documented set {0, 1} (specifically 1 for error).

Phase 82 / Task 82.4
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List

import pytest
from conftest import cc_env, require_velo_exe

REPO_ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_PATTERNS = [
    "backend:",
    "reached codegen",
    "internal compiler error",
    "Segmentation fault",
    "STATUS_ACCESS_VIOLATION",
    "STATUS_STACK_OVERFLOW",
    "STATUS_INTEGER_DIVIDE_BY_ZERO",
    "STATUS_HEAP_CORRUPTION",
    "STATUS_ILLEGAL_INSTRUCTION",
]

CRASH_EXIT_CODES = {
    -1073741819,  # 0xC0000005
    -1073741571,  # 0xC00000FD
    -1073741676,  # 0xC0000094
    -1073740940,  # 0xC0000374
    -1073741795,  # 0xC000001D
    -2147483645,  # 0x80000003
    3221225477,
    3221225725,
    3221225620,
    3221226356,
    139,
    134,
    136,
}


@dataclass(frozen=True)
class ErrorCase:
    case_id: str
    category: str
    source: str
    strict_safety: bool = False


ERROR_CASES: List[ErrorCase] = [
    # -------------------------------------------------------------------------
    # 1. Lexer Errors
    # -------------------------------------------------------------------------
    ErrorCase(
        "lex_unclosed_string",
        "lexer",
        'act main() -> i32 { let s = "unclosed string;\nreturn 0; }',
    ),
    ErrorCase(
        "lex_truncated_char",
        "lexer",
        "act main() -> i32 { let c = '",
    ),
    ErrorCase(
        "lex_unclosed_block_comment",
        "lexer",
        "/* unclosed comment\nact main() -> i32 { return 0; }",
    ),
    ErrorCase(
        "lex_unclosed_raw_string",
        "lexer",
        'act main() -> i32 { let r = r"unclosed raw;\nreturn 0; }',
    ),
    ErrorCase(
        "lex_invalid_char",
        "lexer",
        "act main() -> i32 { let x = @#$?; return 0; }",
    ),

    # -------------------------------------------------------------------------
    # 2. Parser / Syntax Errors
    # -------------------------------------------------------------------------
    ErrorCase(
        "parse_unclosed_brace",
        "syntax",
        "act main() -> i32 { return 0;",
    ),
    ErrorCase(
        "parse_unclosed_paren",
        "syntax",
        "act main() -> i32 { let x = (1 + 2; return x; }",
    ),
    ErrorCase(
        "parse_missing_return_type_arrow",
        "syntax",
        "act main() i32 { return 0; }",
    ),
    ErrorCase(
        "parse_unexpected_token_in_let",
        "syntax",
        "act main() -> i32 { let = 1; return 0; }",
    ),
    ErrorCase(
        "parse_stray_closing_brace",
        "syntax",
        "act main() -> i32 { return 0; }\n}",
    ),
    ErrorCase(
        "parse_empty_file",
        "syntax",
        "",
    ),
    ErrorCase(
        "parse_comments_only",
        "syntax",
        "// Only a comment here\n/* and another comment */\n",
    ),

    # -------------------------------------------------------------------------
    # 3. Scope & Declaration Errors
    # -------------------------------------------------------------------------
    ErrorCase(
        "sem_undeclared_variable",
        "scope",
        "act main() -> i32 { return undeclared_identifier_xyz; }",
    ),
    ErrorCase(
        "sem_undeclared_type",
        "scope",
        "act main() -> UnknownTypeNode { return 0; }",
    ),
    ErrorCase(
        "sem_duplicate_variable",
        "scope",
        "act main() -> i32 { let x = 1;\nlet x = 2;\nreturn x; }",
    ),
    ErrorCase(
        "sem_duplicate_struct",
        "scope",
        "struct Foo { x: i32 }\nstruct Foo { y: i32 }\nact main() -> i32 { return 0; }",
    ),

    # -------------------------------------------------------------------------
    # 4. Type System & Semantics Errors
    # -------------------------------------------------------------------------
    ErrorCase(
        "type_return_mismatch",
        "type_check",
        'act main() -> i32 { return "hello"; }',
    ),
    ErrorCase(
        "type_binary_mismatch",
        "type_check",
        'act main() -> i32 { let x: i32 = 10 + "invalid"; return x; }',
    ),
    ErrorCase(
        "type_mutate_immutable",
        "type_check",
        "act main() -> i32 { let x = 1; x = 2; return x; }",
    ),
    ErrorCase(
        "type_unknown_struct_field",
        "type_check",
        "struct Pt { x: i32 }\nact main() -> i32 { let p = Pt { x: 1 }; return p.nonexistent; }",
    ),
    ErrorCase(
        "type_missing_struct_field",
        "type_check",
        "struct Pt { x: i32, y: i32 }\nact main() -> i32 { let p = Pt { x: 1 }; return p.x; }",
    ),
    ErrorCase(
        "type_struct_field_mismatch",
        "type_check",
        'struct Pt { x: i32 }\nact main() -> i32 { let p = Pt { x: "str" }; return p.x; }',
    ),
    ErrorCase(
        "type_arg_count_too_few",
        "type_check",
        "act add(a: i32, b: i32) -> i32 { return a + b; }\nact main() -> i32 { return add(1); }",
    ),
    ErrorCase(
        "type_arg_count_too_many",
        "type_check",
        "act add(a: i32, b: i32) -> i32 { return a + b; }\nact main() -> i32 { return add(1, 2, 3); }",
    ),
    ErrorCase(
        "type_arg_mismatch",
        "type_check",
        'act add(a: i32, b: i32) -> i32 { return a + b; }\nact main() -> i32 { return add(1, "str"); }',
    ),
    ErrorCase(
        "type_constant_zero_div",
        "type_check",
        "act main() -> i32 { return 100 / 0; }",
    ),

    # -------------------------------------------------------------------------
    # 5. Control Flow & Loop Jumps (Unbound break/continue defense-in-depth)
    # -------------------------------------------------------------------------
    ErrorCase(
        "ctrl_unbound_break",
        "control_flow",
        "act main() -> i32 { break; return 0; }",
    ),
    ErrorCase(
        "ctrl_unbound_continue",
        "control_flow",
        "act main() -> i32 { continue; return 0; }",
    ),
    ErrorCase(
        "ctrl_defer_return_violation",
        "control_flow",
        "act main() -> i32 { defer return 42; return 0; }",
    ),
    ErrorCase(
        "ctrl_defer_break_violation",
        "control_flow",
        "act main() -> i32 { loop true { defer break; break; } return 0; }",
    ),

    # -------------------------------------------------------------------------
    # 6. Safety & Strict Safety
    # -------------------------------------------------------------------------
    ErrorCase(
        "safe_raw_deref_without_unsafe",
        "safety",
        "act main() -> i32 { let p: @i32 = null; return *p; }",
        strict_safety=True,
    ),
]


def assert_error_recovery_guarantees(
    res: subprocess.CompletedProcess,
    case: ErrorCase,
    mode: str,
):
    """Enforce the three Task 82.4 error recovery guarantees."""
    combined_output = f"{res.stdout}\n{res.stderr}".strip()

    # Guarantee 1: Exit code is in the documented set {0, 1}; specifically 1 for error.
    assert res.returncode not in CRASH_EXIT_CODES, (
        f"Mode '{mode}' CRASHED on {case.case_id} with exit code {res.returncode}!"
    )
    assert res.returncode == 1, (
        f"Mode '{mode}' expected exit code 1 on error input {case.case_id}, got {res.returncode}!"
    )

    # Guarantee 2: Diagnostic list is non-empty.
    assert len(combined_output) > 0, (
        f"Mode '{mode}' exited with code 1 on {case.case_id} but produced NO diagnostic output!"
    )
    assert "[Velo Error]" in combined_output or "error:" in combined_output, (
        f"Mode '{mode}' output on {case.case_id} did not contain an error diagnostic:\n{combined_output}"
    )

    # Guarantee 3: Output contains NO internal backend or ICE messages.
    for forbidden in FORBIDDEN_PATTERNS:
        assert forbidden.lower() not in combined_output.lower(), (
            f"Mode '{mode}' leaked internal message '{forbidden}' on {case.case_id}:\n{combined_output}"
        )


@pytest.mark.parametrize("case", ERROR_CASES, ids=lambda c: c.case_id)
def test_error_recovery_check(tmp_path: Path, case: ErrorCase):
    """Verify error recovery guarantees under 'velo check'."""
    velo = require_velo_exe()
    src_file = tmp_path / f"{case.case_id}.vl"
    src_file.write_text(case.source, encoding="utf-8")

    cmd = [str(velo), "check"]
    if case.strict_safety:
        cmd.append("--strict-safety")
    cmd.append(str(src_file))

    res = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=cc_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    assert_error_recovery_guarantees(res, case, "check")


@pytest.mark.parametrize("case", ERROR_CASES, ids=lambda c: c.case_id)
def test_error_recovery_emit_c(tmp_path: Path, case: ErrorCase):
    """Verify error recovery guarantees under 'velo emit-c'."""
    velo = require_velo_exe()
    src_file = tmp_path / f"{case.case_id}.vl"
    src_file.write_text(case.source, encoding="utf-8")

    cmd = [str(velo), "emit-c"]
    if case.strict_safety:
        cmd.append("--strict-safety")
    cmd.append(str(src_file))

    res = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=cc_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    assert_error_recovery_guarantees(res, case, "emit-c")


@pytest.mark.parametrize("case", ERROR_CASES, ids=lambda c: c.case_id)
def test_error_recovery_check_json(tmp_path: Path, case: ErrorCase):
    """Verify error recovery produces well-formed non-empty JSON diagnostic list under 'velo check --json'."""
    velo = require_velo_exe()
    src_file = tmp_path / f"{case.case_id}.vl"
    src_file.write_text(case.source, encoding="utf-8")

    cmd = [str(velo), "check", "--json"]
    if case.strict_safety:
        cmd.append("--strict-safety")
    cmd.append(str(src_file))

    res = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=cc_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )

    # Process exit code must be in documented set {0, 1}
    assert res.returncode not in CRASH_EXIT_CODES
    assert res.returncode == 1, f"Expected exit code 1, got {res.returncode}"

    # JSON output must be valid JSON object with ok: false and diagnostics array
    raw_json = res.stdout.strip()
    assert len(raw_json) > 0, "velo check --json produced empty stdout!"
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        pytest.fail(f"velo check --json output is not valid JSON:\n{raw_json}\nError: {exc}")

    assert isinstance(data, dict), f"Expected JSON object, got {type(data)}"
    assert data.get("ok") is False, f"Expected ok: false on error input, got {data}"
    diags = data.get("diagnostics", [])
    assert len(diags) > 0, f"Expected non-empty diagnostic list for {case.case_id}, got empty list!"

    # No internal backend messages leaked in messages
    for diag in diags:
        msg = diag.get("message", "")
        for forbidden in FORBIDDEN_PATTERNS:
            assert forbidden.lower() not in msg.lower(), (
                f"JSON diagnostic leaked internal message '{forbidden}': {msg}"
            )
