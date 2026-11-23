"""
Resource ceilings and limit bounding tests (Phase 82 / Task 82.5).

Validates Security Invariant I82.5:
"Resource ceilings bound source file size, token count, AST depth, and error count."

Ceilings tested:
1. Maximum source file size (16 MB ceiling -> VELO-E0022)
2. Maximum token count (500,000 tokens ceiling -> VELO-E0022)
3. Maximum AST depth (expression nesting 256, block nesting 256 / 128 -> VELO-E0021)
4. Maximum error count (stop after 50 errors and print "too many errors emitted; stopping now")
"""

import json
import subprocess
from pathlib import Path

import pytest
from conftest import cc_env, velo_exe

CRASH_EXIT_CODES = {
    -1073741819, 3221225477,  # 0xC0000005 STATUS_ACCESS_VIOLATION
    -1073741571, 3221225725,  # 0xC00000FD STATUS_STACK_OVERFLOW
    -1073741795, 3221225499,  # 0xC0000094 STATUS_INTEGER_DIVIDE_BY_ZERO
    -1073740940, 3221226356,  # 0xC0000374 STATUS_HEAP_CORRUPTION
    -1073741787, 3221225509,  # 0xC0000025 STATUS_NONCONTINUABLE_EXCEPTION
    -1073740791, 3221226505,  # 0xC0000409 STATUS_STACK_BUFFER_OVERRUN
}


def _run_cmd(cmd: list[str], cwd: Path, timeout: float = 20.0) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
        env=cc_env(),
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# 1. Maximum Source File Size (16 MB)
# ---------------------------------------------------------------------------

def test_source_file_size_exceeds_limit(tmp_path: Path):
    exe = velo_exe()
    if not exe.exists():
        pytest.skip(f"Compiler binary {exe} not found")

    # 16 MB is 16,777,216 bytes. Exceed it by 64 bytes.
    limit = 16 * 1024 * 1024
    padding = b" " * (limit + 64 - 15)
    src_content = b"let a: i32 = 1;\n" + padding

    src = tmp_path / "oversized.vl"
    src.write_bytes(src_content)

    proc = _run_cmd([str(exe), "check", str(src)], cwd=tmp_path)
    assert proc.returncode not in CRASH_EXIT_CODES
    assert proc.returncode == 1
    output = proc.stdout + proc.stderr
    assert "VELO-E0022" in output
    assert "source file exceeds maximum size of 16 MB" in output

    out_c = tmp_path / "oversized.c"
    proc_emit = _run_cmd([str(exe), "emit-c", str(src), "-o", str(out_c)], cwd=tmp_path)
    assert proc_emit.returncode not in CRASH_EXIT_CODES
    assert proc_emit.returncode == 1
    output_emit = proc_emit.stdout + proc_emit.stderr
    assert "VELO-E0022" in output_emit
    assert "source file exceeds maximum size of 16 MB" in output_emit


def test_source_file_size_under_limit(tmp_path: Path):
    exe = velo_exe()
    if not exe.exists():
        pytest.skip(f"Compiler binary {exe} not found")

    # 1 MB source file padded with whitespace: well under 16 MB limit.
    padding = " " * (1024 * 1024)
    src_content = f"let a: i32 = 1;\n{padding}let b: i32 = 2;\n"

    src = tmp_path / "one_mb.vl"
    src.write_text(src_content, encoding="utf-8")

    proc = _run_cmd([str(exe), "check", str(src)], cwd=tmp_path)
    assert proc.returncode not in CRASH_EXIT_CODES
    assert proc.returncode == 0, f"Expected 0 but got {proc.returncode}: {proc.stdout} {proc.stderr}"


# ---------------------------------------------------------------------------
# 2. Maximum Token Count (500,000 tokens)
# ---------------------------------------------------------------------------

def test_token_count_exceeds_limit(tmp_path: Path):
    exe = velo_exe()
    if not exe.exists():
        pytest.skip(f"Compiler binary {exe} not found")

    # `let x = 1;\n` produces 5 tokens: TOK_LET, TOK_IDENT, TOK_EQUAL, TOK_INT, TOK_SEMICOLON
    # 105,000 repetitions = 525,000 tokens, exceeding the 500,000 ceiling.
    # Note: total file size is ~1.26 MB, so file size is well under 16 MB.
    lines = ["let x0 = 1;"] * 105000
    src_content = "\n".join(lines) + "\n"

    src = tmp_path / "too_many_tokens.vl"
    src.write_text(src_content, encoding="utf-8")

    proc = _run_cmd([str(exe), "check", str(src)], cwd=tmp_path, timeout=30.0)
    assert proc.returncode not in CRASH_EXIT_CODES
    assert proc.returncode == 1
    output = proc.stdout + proc.stderr
    assert "VELO-E0022" in output
    assert "token count exceeds limit of 500,000 tokens" in output

    out_c = tmp_path / "too_many_tokens.c"
    proc_emit = _run_cmd([str(exe), "emit-c", str(src), "-o", str(out_c)], cwd=tmp_path, timeout=30.0)
    assert proc_emit.returncode not in CRASH_EXIT_CODES
    assert proc_emit.returncode == 1
    output_emit = proc_emit.stdout + proc_emit.stderr
    assert "VELO-E0022" in output_emit
    assert "token count exceeds limit of 500,000 tokens" in output_emit


def test_token_count_under_limit(tmp_path: Path):
    exe = velo_exe()
    if not exe.exists():
        pytest.skip(f"Compiler binary {exe} not found")

    # 1,000 declarations = ~5,000 tokens, well under 500,000
    lines = [f"let x{i}: i32 = {i};" for i in range(1000)]
    src_content = "\n".join(lines) + "\n"

    src = tmp_path / "tokens_ok.vl"
    src.write_text(src_content, encoding="utf-8")

    proc = _run_cmd([str(exe), "check", str(src)], cwd=tmp_path)
    assert proc.returncode not in CRASH_EXIT_CODES
    assert proc.returncode == 0


# ---------------------------------------------------------------------------
# 3. Maximum AST Depth Ceilings (Expression: 256, Block: 256 / 128)
# ---------------------------------------------------------------------------

def test_ast_expression_depth_ceiling(tmp_path: Path):
    exe = velo_exe()
    if not exe.exists():
        pytest.skip(f"Compiler binary {exe} not found")

    # Depth 256: 255 nested parens -> passes
    pass_content = "let x = " + ("(" * 254) + "1" + (")" * 254) + ";\n"
    src_pass = tmp_path / "expr_depth_pass.vl"
    src_pass.write_text(pass_content, encoding="utf-8")

    proc = _run_cmd([str(exe), "check", str(src_pass)], cwd=tmp_path)
    assert proc.returncode == 0

    # Depth 257: 256 nested parens -> fails with VELO-E0021
    fail_content = "let x = " + ("(" * 256) + "1" + (")" * 256) + ";\n"
    src_fail = tmp_path / "expr_depth_fail.vl"
    src_fail.write_text(fail_content, encoding="utf-8")

    proc = _run_cmd([str(exe), "check", str(src_fail)], cwd=tmp_path)
    assert proc.returncode not in CRASH_EXIT_CODES
    assert proc.returncode == 1
    output = proc.stdout + proc.stderr
    assert "VELO-E0021" in output
    assert "expression nesting depth exceeds limit of 256" in output


def test_ast_statement_block_depth_ceiling(tmp_path: Path):
    exe = velo_exe()
    if not exe.exists():
        pytest.skip(f"Compiler binary {exe} not found")

    # In type checker: block depth limit is 128.
    # 127 nested blocks inside act main (depth 128): passes
    pass_blocks = "act main() -> i32 {\n" + ("    { " * 127) + "return 0;" + (" }" * 127) + "\n}\n"
    src_pass = tmp_path / "stmt_block_pass.vl"
    src_pass.write_text(pass_blocks, encoding="utf-8")

    proc = _run_cmd([str(exe), "check", str(src_pass)], cwd=tmp_path)
    assert proc.returncode == 0

    # 128 nested blocks inside act main (depth 129): fails with VELO-E0021
    fail_blocks = "act main() -> i32 {\n" + ("    { " * 128) + "return 0;" + (" }" * 128) + "\n}\n"
    src_fail = tmp_path / "stmt_block_fail.vl"
    src_fail.write_text(fail_blocks, encoding="utf-8")

    proc = _run_cmd([str(exe), "check", str(src_fail)], cwd=tmp_path)
    assert proc.returncode not in CRASH_EXIT_CODES
    assert proc.returncode == 1
    output = proc.stdout + proc.stderr
    assert "VELO-E0021" in output
    assert "block nesting depth exceeds limit of 128" in output

    # In parser: block depth limit is 256.
    # 257 nested blocks: parser fails with limit 256 before checker
    fail_blocks_257 = "act main() -> i32 {\n" + ("    { " * 257) + "return 0;" + (" }" * 257) + "\n}\n"
    src_fail_257 = tmp_path / "stmt_block_257.vl"
    src_fail_257.write_text(fail_blocks_257, encoding="utf-8")

    proc = _run_cmd([str(exe), "check", str(src_fail_257)], cwd=tmp_path)
    assert proc.returncode not in CRASH_EXIT_CODES
    assert proc.returncode == 1
    output = proc.stdout + proc.stderr
    assert "VELO-E0021" in output
    assert "block nesting depth exceeds limit of 256" in output


# ---------------------------------------------------------------------------
# 4. Maximum Error Count (50 errors ceiling + stop message)
# ---------------------------------------------------------------------------

def test_error_count_ceiling_text(tmp_path: Path):
    exe = velo_exe()
    if not exe.exists():
        pytest.skip(f"Compiler binary {exe} not found")

    # Generate 100 redeclaration errors in the same scope
    lines = ["let x: i32 = 0;"]
    for i in range(1, 101):
        lines.append(f"let x: i32 = {i};")
    src_content = "\n".join(lines) + "\n"

    src = tmp_path / "many_errors.vl"
    src.write_text(src_content, encoding="utf-8")

    proc = _run_cmd([str(exe), "check", str(src)], cwd=tmp_path)
    assert proc.returncode not in CRASH_EXIT_CODES
    assert proc.returncode == 1
    output = proc.stdout + proc.stderr

    # Must contain the stop message
    assert "too many errors emitted; stopping now" in output

    # Exactly 50 individual errors are printed, followed by the stopping line
    # and the terminal summary line (52 total [Velo Error] lines vs 101 without ceiling).
    error_count = output.count("[Velo Error]")
    assert error_count == 52, f"Expected 52 [Velo Error] lines (50 errors + 1 stop + 1 summary), got {error_count}"

    # Verify that the 50th error is emitted, but the 51st error (line 52) is silenced
    assert "semantic:51:1" in output
    assert "semantic:52:1" not in output


def test_error_count_ceiling_json(tmp_path: Path):
    exe = velo_exe()
    if not exe.exists():
        pytest.skip(f"Compiler binary {exe} not found")

    lines = ["let x: i32 = 0;"]
    for i in range(1, 101):
        lines.append(f"let x: i32 = {i};")
    src_content = "\n".join(lines) + "\n"

    src = tmp_path / "many_errors_json.vl"
    src.write_text(src_content, encoding="utf-8")

    proc = _run_cmd([str(exe), "check", "--json", str(src)], cwd=tmp_path)
    assert proc.returncode not in CRASH_EXIT_CODES
    assert proc.returncode == 1

    data = json.loads(proc.stdout)
    diagnostics = data.get("diagnostics", [])

    # Total diagnostics in JSON should be capped at 51 (50 errors + 1 stopping message)
    assert len(diagnostics) == 51, f"Expected 51 diagnostics, got {len(diagnostics)}"
    last_diag = diagnostics[-1]
    assert "too many errors emitted; stopping now" in last_diag.get("message", "")
    assert last_diag.get("severity") == "error"


def test_error_count_ceiling_emit_c(tmp_path: Path):
    exe = velo_exe()
    if not exe.exists():
        pytest.skip(f"Compiler binary {exe} not found")

    lines = ["let x: i32 = 0;"]
    for i in range(1, 101):
        lines.append(f"let x: i32 = {i};")
    src_content = "\n".join(lines) + "\n"

    src = tmp_path / "many_errors_emit.vl"
    out_c = tmp_path / "many_errors_emit.c"
    src.write_text(src_content, encoding="utf-8")

    proc = _run_cmd([str(exe), "emit-c", str(src), "-o", str(out_c)], cwd=tmp_path)
    assert proc.returncode not in CRASH_EXIT_CODES
    assert proc.returncode == 1
    output = proc.stdout + proc.stderr

    assert "too many errors emitted; stopping now" in output
    error_count = output.count("[Velo Error]")
    assert error_count == 52, f"Expected 52 [Velo Error] lines (50 errors + 1 stop + 1 summary), got {error_count}"

    # Verify that the 50th error is emitted, but the 51st error (line 52) is silenced
    assert "semantic:51:1" in output
    assert "semantic:52:1" not in output
