"""
Compiler recursion depth bounding and diagnostic tests (Phase 82 / Task 82.2).

Validates Security Invariant I82.2:
"Recursion in lexer, parser, and checker is depth-bounded with a named diagnostic."

Tests boundary conditions at limit-1, limit, and limit+1 for:
1. Lexer: nested block comments (`/* ... */`), limit = 128.
   - 127 nested comments: pass (exit 0)
   - 128 nested comments: pass (exit 0)
   - 129 nested comments: fail with VELO-E0021 (exit 1)
2. Parser: nested grouped expressions (`((...1...))`), limit = 256.
   - 254 nested parens (depth 255): pass (exit 0)
   - 255 nested parens (depth 256): pass (exit 0)
   - 256 nested parens (depth 257): fail with VELO-E0021 (exit 1)
3. Checker: nested block statement scopes (`{ { { ... } } }`), limit = 128.
   - 126 nested blocks inside act main (depth 127): pass (exit 0)
   - 127 nested blocks inside act main (depth 128): pass (exit 0)
   - 128 nested blocks inside act main (depth 129): fail with VELO-E0021 (exit 1)
"""

import os
import subprocess
from pathlib import Path

import pytest
from conftest import cc_env, velo_exe

REPO_ROOT = Path(__file__).resolve().parent.parent

CRASH_EXIT_CODES = {
    -1073741819, 3221225477,  # 0xC0000005 STATUS_ACCESS_VIOLATION
    -1073741571, 3221225725,  # 0xC00000FD STATUS_STACK_OVERFLOW
    -1073741795, 3221225499,  # 0xC0000094 STATUS_INTEGER_DIVIDE_BY_ZERO
    -1073740940, 3221226356,  # 0xC0000374 STATUS_HEAP_CORRUPTION
    -1073741787, 3221225509,  # 0xC0000025 STATUS_NONCONTINUABLE_EXCEPTION
    -1073740791, 3221226505,  # 0xC0000409 STATUS_STACK_BUFFER_OVERRUN
}


def _run_cmd(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
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


# ---------------------------------------------------------------------------
# 1. Lexer Depth Limits (limit = 128)
# ---------------------------------------------------------------------------

def _gen_lexer_comment(depth: int) -> str:
    """Produces a valid program wrapped in N nested block comments."""
    return ("/* " * depth) + "let x = 1;" + (" */" * depth) + "\nlet y = 2;\n"


@pytest.mark.parametrize(
    "depth,expected_ok",
    [
        (127, True),   # limit - 1
        (128, True),   # limit
        (129, False),  # limit + 1
    ],
    ids=["lexer_127_pass", "lexer_128_pass", "lexer_129_fail"],
)
def test_lexer_comment_depth_limits_check(depth: int, expected_ok: bool, tmp_path: Path):
    exe = velo_exe()
    if not exe.exists():
        pytest.skip(f"Compiler binary {exe} not found")

    src = tmp_path / f"lex_depth_{depth}.vl"
    src.write_text(_gen_lexer_comment(depth), encoding="utf-8")

    proc = _run_cmd([str(exe), "check", str(src)], cwd=tmp_path)
    assert proc.returncode not in CRASH_EXIT_CODES
    assert proc.returncode >= 0

    if expected_ok:
        assert proc.returncode == 0, f"Lexer depth {depth} should pass but exited {proc.returncode}: {proc.stdout}"
    else:
        assert proc.returncode == 1, f"Lexer depth {depth} should fail but exited {proc.returncode}"
        output = proc.stdout + proc.stderr
        assert "VELO-E0021" in output, f"Missing VELO-E0021 in: {output}"
        assert "Recursion depth limit exceeded" in output, f"Missing explanation in: {output}"


@pytest.mark.parametrize(
    "depth,expected_ok",
    [
        (127, True),
        (128, True),
        (129, False),
    ],
    ids=["lexer_emit_127_pass", "lexer_emit_128_pass", "lexer_emit_129_fail"],
)
def test_lexer_comment_depth_limits_emit_c(depth: int, expected_ok: bool, tmp_path: Path):
    exe = velo_exe()
    if not exe.exists():
        pytest.skip(f"Compiler binary {exe} not found")

    src = tmp_path / f"lex_depth_{depth}.vl"
    out_c = tmp_path / f"lex_depth_{depth}.c"
    src.write_text(_gen_lexer_comment(depth), encoding="utf-8")

    proc = _run_cmd([str(exe), "emit-c", str(src), "-o", str(out_c)], cwd=tmp_path)
    assert proc.returncode not in CRASH_EXIT_CODES
    assert proc.returncode >= 0

    if expected_ok:
        assert proc.returncode == 0
        assert out_c.exists()
    else:
        assert proc.returncode == 1
        output = proc.stdout + proc.stderr
        assert "VELO-E0021" in output


# ---------------------------------------------------------------------------
# 2. Parser Depth Limits (limit = 256)
# ---------------------------------------------------------------------------

def _gen_parser_parens(parens: int) -> str:
    """Produces an expression with N nested parentheses."""
    return "let x = " + ("(" * parens) + "1" + (")" * parens) + ";\n"


@pytest.mark.parametrize(
    "parens,expected_ok",
    [
        (254, True),   # outer (1) + 254 inner = depth 255 (limit - 1)
        (255, True),   # outer (1) + 255 inner = depth 256 (limit)
        (256, False),  # outer (1) + 256 inner = depth 257 (limit + 1)
    ],
    ids=["parser_255_pass", "parser_256_pass", "parser_257_fail"],
)
def test_parser_expression_depth_limits_check(parens: int, expected_ok: bool, tmp_path: Path):
    exe = velo_exe()
    if not exe.exists():
        pytest.skip(f"Compiler binary {exe} not found")

    src = tmp_path / f"parse_depth_{parens}.vl"
    src.write_text(_gen_parser_parens(parens), encoding="utf-8")

    proc = _run_cmd([str(exe), "check", str(src)], cwd=tmp_path)
    assert proc.returncode not in CRASH_EXIT_CODES
    assert proc.returncode >= 0

    if expected_ok:
        assert proc.returncode == 0, f"Parser parens {parens} should pass but exited {proc.returncode}: {proc.stdout}"
    else:
        assert proc.returncode == 1, f"Parser parens {parens} should fail but exited {proc.returncode}"
        output = proc.stdout + proc.stderr
        assert "VELO-E0021" in output, f"Missing VELO-E0021 in: {output}"
        assert "Recursion depth limit exceeded" in output


@pytest.mark.parametrize(
    "parens,expected_ok",
    [
        (254, True),
        (255, True),
        (256, False),
    ],
    ids=["parser_emit_255_pass", "parser_emit_256_pass", "parser_emit_257_fail"],
)
def test_parser_expression_depth_limits_emit_c(parens: int, expected_ok: bool, tmp_path: Path):
    exe = velo_exe()
    if not exe.exists():
        pytest.skip(f"Compiler binary {exe} not found")

    src = tmp_path / f"parse_depth_{parens}.vl"
    out_c = tmp_path / f"parse_depth_{parens}.c"
    src.write_text(_gen_parser_parens(parens), encoding="utf-8")

    proc = _run_cmd([str(exe), "emit-c", str(src), "-o", str(out_c)], cwd=tmp_path)
    assert proc.returncode not in CRASH_EXIT_CODES
    assert proc.returncode >= 0

    if expected_ok:
        assert proc.returncode == 0
        assert out_c.exists()
    else:
        assert proc.returncode == 1
        output = proc.stdout + proc.stderr
        assert "VELO-E0021" in output


# ---------------------------------------------------------------------------
# 3. Checker Depth Limits (limit = 128)
# ---------------------------------------------------------------------------

def _gen_checker_blocks(nested_blocks: int) -> str:
    """Produces act main with N nested block scopes."""
    return (
        "act main() -> i32 {\n"
        + ("    { " * nested_blocks)
        + "return 0;"
        + (" }" * nested_blocks)
        + "\n}\n"
    )


@pytest.mark.parametrize(
    "nested_blocks,expected_ok",
    [
        (126, True),   # fn body (1) + 126 nested = depth 127 (limit - 1)
        (127, True),   # fn body (1) + 127 nested = depth 128 (limit)
        (128, False),  # fn body (1) + 128 nested = depth 129 (limit + 1)
    ],
    ids=["checker_127_pass", "checker_128_pass", "checker_129_fail"],
)
def test_checker_block_depth_limits_check(nested_blocks: int, expected_ok: bool, tmp_path: Path):
    exe = velo_exe()
    if not exe.exists():
        pytest.skip(f"Compiler binary {exe} not found")

    src = tmp_path / f"check_depth_{nested_blocks}.vl"
    src.write_text(_gen_checker_blocks(nested_blocks), encoding="utf-8")

    proc = _run_cmd([str(exe), "check", str(src)], cwd=tmp_path)
    assert proc.returncode not in CRASH_EXIT_CODES
    assert proc.returncode >= 0

    if expected_ok:
        assert proc.returncode == 0, f"Checker blocks {nested_blocks} should pass but exited {proc.returncode}: {proc.stdout}"
    else:
        assert proc.returncode == 1, f"Checker blocks {nested_blocks} should fail but exited {proc.returncode}"
        output = proc.stdout + proc.stderr
        assert "VELO-E0021" in output, f"Missing VELO-E0021 in: {output}"
        assert "Recursion depth limit exceeded" in output


@pytest.mark.parametrize(
    "nested_blocks,expected_ok",
    [
        (126, True),
        (127, True),
        (128, False),
    ],
    ids=["checker_emit_127_pass", "checker_emit_128_pass", "checker_emit_129_fail"],
)
def test_checker_block_depth_limits_emit_c(nested_blocks: int, expected_ok: bool, tmp_path: Path):
    exe = velo_exe()
    if not exe.exists():
        pytest.skip(f"Compiler binary {exe} not found")

    src = tmp_path / f"check_depth_{nested_blocks}.vl"
    out_c = tmp_path / f"check_depth_{nested_blocks}.c"
    src.write_text(_gen_checker_blocks(nested_blocks), encoding="utf-8")

    proc = _run_cmd([str(exe), "emit-c", str(src), "-o", str(out_c)], cwd=tmp_path)
    assert proc.returncode not in CRASH_EXIT_CODES
    assert proc.returncode >= 0

    if expected_ok:
        assert proc.returncode == 0
        assert out_c.exists()
    else:
        assert proc.returncode == 1
        output = proc.stdout + proc.stderr
        assert "VELO-E0021" in output
