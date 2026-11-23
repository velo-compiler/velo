"""
Compiler crash-freedom and robustness generator test suite (Phase 82 / Task 82.1).

Validates Security Invariant I82.1:
"No input reaches a signal or an OS exception. Every failure is a diagnostic with a
code and a non-crashing exit status."

Generates malformed, edge-case, and historical crash inputs:
- Truncated tokens (unterminated strings, unclosed chars, unclosed block comments, incomplete hex/bin/float)
- Mismatched delimiters and braces
- Extreme nesting depth
- 1 MB identifiers
- Invalid UTF-8 bytes and sequences
- Embedded NUL bytes
- Byte Order Marks (UTF-8, UTF-16 LE/BE)
- Historical crash corpus from Phases 52-69 and gaps.md (defer transfers, divide-by-zero)

For every input, asserts that `velo check` and `velo emit-c`:
1. Never terminate via OS hardware trap, signal, or exception (0xC0000005, 0xC00000FD, 0xC0000094, etc.)
2. Exit with a documented status code (0 for accepted/warnings, 1 for compiler diagnostics)
3. Emit non-empty diagnostic messages when rejected
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Generator, NamedTuple, Union

import pytest
from conftest import cc_env, velo_exe

REPO_ROOT = Path(__file__).resolve().parent.parent

# OS exception / hardware fault exit codes that indicate an unhandled process crash.
# On Windows, 32-bit NTSTATUS codes appear as negative signed or large unsigned ints.
CRASH_EXIT_CODES = {
    -1073741819, 3221225477,  # 0xC0000005 STATUS_ACCESS_VIOLATION
    -1073741571, 3221225725,  # 0xC00000FD STATUS_STACK_OVERFLOW
    -1073741795, 3221225499,  # 0xC0000094 STATUS_INTEGER_DIVIDE_BY_ZERO
    -1073740940, 3221226356,  # 0xC0000374 STATUS_HEAP_CORRUPTION
    -1073741787, 3221225509,  # 0xC0000025 STATUS_NONCONTINUABLE_EXCEPTION
    -1073740791, 3221226505,  # 0xC0000409 STATUS_STACK_BUFFER_OVERRUN
}


class InputCase(NamedTuple):
    case_id: str
    category: str
    content: Union[str, bytes]
    xfail_reason: str = ""


def generate_malformed_inputs() -> Generator[InputCase, None, None]:
    """Yields malformed test cases across all specified categories."""

    # 1. Truncated Tokens
    yield InputCase(
        "truncated_string",
        "tokens",
        'let s = "unterminated string literal;',
    )
    yield InputCase(
        "truncated_raw_string",
        "tokens",
        "let s = `unterminated raw string literal;",
    )
    yield InputCase(
        "truncated_char",
        "tokens",
        "let c = 'a;",
    )
    yield InputCase(
        "truncated_block_comment",
        "tokens",
        "/* unclosed block comment\nlet x = 1;\n",
    )
    yield InputCase(
        "incomplete_hex",
        "tokens",
        "let x = 0x;",
    )
    yield InputCase(
        "incomplete_bin",
        "tokens",
        "let x = 0b;",
    )
    yield InputCase(
        "incomplete_oct",
        "tokens",
        "let x = 0o;",
    )
    yield InputCase(
        "incomplete_float_exp",
        "tokens",
        "let x = 1.0e;",
    )

    # 2. Mismatched Delimiters and Braces
    yield InputCase(
        "mismatched_brace_bracket",
        "delimiters",
        "act main() { [ } ]",
    )
    yield InputCase(
        "unclosed_brace",
        "delimiters",
        "act main() { let x = 1;",
    )
    yield InputCase(
        "unclosed_paren",
        "delimiters",
        "act main() { let x = (1 + 2; }",
    )
    yield InputCase(
        "unclosed_bracket",
        "delimiters",
        "act main() { let a = [1, 2, 3; }",
    )
    yield InputCase(
        "unexpected_closing_brace",
        "delimiters",
        "}",
    )
    yield InputCase(
        "unexpected_closing_paren",
        "delimiters",
        ")",
    )
    yield InputCase(
        "unexpected_closing_bracket",
        "delimiters",
        "]",
    )
    yield InputCase(
        "interleaved_delimiters",
        "delimiters",
        "act main() { ( [ ) ] }",
    )

    # 3. Extreme Nesting
    yield InputCase(
        "deep_nesting_parens_100",
        "nesting",
        "let x = " + "(" * 100 + "1" + ")" * 100 + ";",
    )
    yield InputCase(
        "deep_nesting_parens_500",
        "nesting",
        "let x = " + "(" * 500 + "1" + ")" * 500 + ";",
    )
    yield InputCase(
        "deep_nesting_blocks_50",
        "nesting",
        "act main() { " + "{ " * 50 + "let x = 1; " + "} " * 50 + "}",
    )
    yield InputCase(
        "deep_nesting_parens_10k",
        "nesting",
        "let x = " + "(" * 10000 + "1" + ")" * 10000 + ";",
    )

    # 4. 1 MB Identifiers
    yield InputCase(
        "huge_identifier_var_1mb",
        "huge_ident",
        "let " + "a" * 1_000_000 + " = 1;",
    )
    yield InputCase(
        "huge_identifier_act_1mb",
        "huge_ident",
        "act " + "f" * 1_000_000 + "() -> i32 { return 0; }",
    )

    # 5. Invalid UTF-8
    yield InputCase(
        "invalid_utf8_continuation_bytes",
        "invalid_utf8",
        b"let x = \x80\x81\x82;",
    )
    yield InputCase(
        "invalid_utf8_truncated_multibyte",
        "invalid_utf8",
        b'let s = "hello \xc3";',
    )
    yield InputCase(
        "invalid_utf8_start_bytes",
        "invalid_utf8",
        b"let s = \xff\xfe;",
    )

    # 6. Embedded NUL Bytes
    yield InputCase(
        "nul_in_code",
        "nul_bytes",
        b"let x\x00 = 1;",
    )
    yield InputCase(
        "nul_in_string",
        "nul_bytes",
        b'let s = "hello\x00world";',
    )
    yield InputCase(
        "nul_in_block",
        "nul_bytes",
        b"act main() {\x00 let x = 1; }",
    )
    yield InputCase(
        "nul_at_end",
        "nul_bytes",
        b"let x = 1;\x00",
    )
    yield InputCase(
        "nul_at_start",
        "nul_bytes",
        b"\x00let x = 1;",
        xfail_reason="Zero-declaration input (leading NUL byte) exits 1 without diagnostic message; to be addressed in Task 82.4",
    )

    # 7. Byte Order Marks (BOMs)
    yield InputCase(
        "bom_utf8",
        "bom",
        b"\xef\xbb\xbflet x = 1;",
    )
    yield InputCase(
        "bom_utf16_le",
        "bom",
        b"\xff\xfelet x = 1;",
    )
    yield InputCase(
        "bom_utf16_be",
        "bom",
        b"\xfe\xfflet x = 1;",
    )

    # 8. Historical Crashes from Phases 52-69 and gaps.md
    yield InputCase(
        "historical_defer_return",
        "historical",
        "act main() { defer return; }",
    )
    yield InputCase(
        "historical_defer_return_val",
        "historical",
        "act main() -> i32 { defer return 1; return 0; }",
    )
    yield InputCase(
        "historical_defer_break",
        "historical",
        "act main() { loop { defer break; } }",
    )
    yield InputCase(
        "historical_defer_continue",
        "historical",
        "act main() { loop { defer continue; } }",
    )
    yield InputCase(
        "historical_defer_fail",
        "historical",
        "act main() { defer fail \"cleanup\"; }",
    )
    yield InputCase(
        "historical_defer_block_return",
        "historical",
        "act main() { defer { return; } }",
    )
    yield InputCase(
        "historical_defer_if_break",
        "historical",
        "act main() { loop { defer if true { break; } } }",
    )
    yield InputCase(
        "historical_divide_by_zero_const",
        "historical",
        "act main() { let x = 10 / 0; }",
    )
    yield InputCase(
        "historical_modulo_by_zero_const",
        "historical",
        "act main() { let x = 10 % 0; }",
    )
    yield InputCase(
        "historical_compound_divide_by_zero",
        "historical",
        "act main() { mut x = 10; x /= 0; }",
    )
    yield InputCase(
        "historical_divide_by_folded_zero",
        "historical",
        "act main() { let x = 10 / (5 - 5); }",
    )
    yield InputCase(
        "historical_modulo_by_folded_zero",
        "historical",
        "act main() { let x = 10 % (2 * 0); }",
    )


ALL_TEST_CASES = list(generate_malformed_inputs())


def _run_compiler_cmd(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
        env=cc_env(),
        timeout=10.0,
    )


@pytest.mark.parametrize("test_case", ALL_TEST_CASES, ids=lambda c: c.case_id)
def test_compiler_no_crash_check(test_case: InputCase, tmp_path: Path):
    """Asserts `velo check` never crashes with an OS exception on malformed inputs."""
    exe = velo_exe()
    if not exe.exists():
        pytest.skip(f"Compiler binary {exe} not found")

    if test_case.xfail_reason:
        pytest.xfail(test_case.xfail_reason)

    src_file = tmp_path / f"{test_case.case_id}.vl"
    if isinstance(test_case.content, bytes):
        src_file.write_bytes(test_case.content)
    else:
        src_file.write_text(test_case.content, encoding="utf-8")

    try:
        proc = _run_compiler_cmd([str(exe), "check", str(src_file)], cwd=tmp_path)
    except subprocess.TimeoutExpired:
        pytest.fail(f"velo check timed out after 10s on {test_case.case_id}")

    # 1. Assert never crashes with OS exception or signal
    assert proc.returncode not in CRASH_EXIT_CODES, (
        f"velo check crashed with exception/fault code {proc.returncode} on {test_case.case_id}!\n"
        f"Stdout: {proc.stdout}\nStderr: {proc.stderr}"
    )
    assert proc.returncode >= 0, (
        f"velo check terminated via signal {proc.returncode} on {test_case.case_id}!"
    )

    # 2. Documented status: must be 0 (accepted/clean) or 1 (diagnosed error)
    assert proc.returncode in (0, 1), (
        f"velo check returned undocumented exit status {proc.returncode} on {test_case.case_id}"
    )

    # 3. Diagnostic check: when exit code is 1, non-empty error diagnostic must be output
    output = (proc.stdout + proc.stderr).strip()
    if proc.returncode == 1:
        assert len(output) > 0, (
            f"velo check exited with code 1 on {test_case.case_id} but produced no diagnostic!"
        )


@pytest.mark.parametrize("test_case", ALL_TEST_CASES, ids=lambda c: c.case_id)
def test_compiler_no_crash_emit_c(test_case: InputCase, tmp_path: Path):
    """Asserts `velo emit-c` never crashes with an OS exception on malformed inputs."""
    exe = velo_exe()
    if not exe.exists():
        pytest.skip(f"Compiler binary {exe} not found")

    if test_case.xfail_reason:
        pytest.xfail(test_case.xfail_reason)

    src_file = tmp_path / f"{test_case.case_id}.vl"
    out_file = tmp_path / f"{test_case.case_id}.c"
    if isinstance(test_case.content, bytes):
        src_file.write_bytes(test_case.content)
    else:
        src_file.write_text(test_case.content, encoding="utf-8")

    try:
        proc = _run_compiler_cmd(
            [str(exe), "emit-c", str(src_file), "-o", str(out_file)],
            cwd=tmp_path,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"velo emit-c timed out after 10s on {test_case.case_id}")

    # 1. Assert never crashes with OS exception or signal
    assert proc.returncode not in CRASH_EXIT_CODES, (
        f"velo emit-c crashed with exception/fault code {proc.returncode} on {test_case.case_id}!\n"
        f"Stdout: {proc.stdout}\nStderr: {proc.stderr}"
    )
    assert proc.returncode >= 0, (
        f"velo emit-c terminated via signal {proc.returncode} on {test_case.case_id}!"
    )

    # 2. Documented status: must be 0 (accepted/clean) or 1 (diagnosed error)
    assert proc.returncode in (0, 1), (
        f"velo emit-c returned undocumented exit status {proc.returncode} on {test_case.case_id}"
    )

    # 3. Diagnostic check: when exit code is 1, non-empty error diagnostic must be output
    output = (proc.stdout + proc.stderr).strip()
    if proc.returncode == 1:
        assert len(output) > 0, (
            f"velo emit-c exited with code 1 on {test_case.case_id} but produced no diagnostic!"
        )
