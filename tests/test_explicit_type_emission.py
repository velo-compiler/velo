"""
Tests for Phase 80, Task 80.3:
Replacement of Trailing-Space Convention with Explicit Emission Helpers.

Verifies:
1. `emit_type_then_space` and `emit_type_str_then_space` are used for explicit C type emission.
2. `loop_var_c_type` produces `CType` with `needs_space = false`, proving trailing spaces are eliminated.
3. Declarations across all constructs (functions, parameters, struct fields, globals, locals, loops)
   emit clean C99 syntax with exactly one separating space and zero trailing-space dependencies.
4. Compiled programs run correctly and satisfy all runtime assertions.
"""

import os
import subprocess
import sys
from pathlib import Path
import pytest
from conftest import velo_exe, cc_env

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()
SRC_BACKEND = REPO_ROOT / "src" / "backend"


def get_build_env():
    return cc_env()


def test_structural_emit_type_helpers_adoption():
    """Verify that explicit emission helpers are defined and adopted across codegen files."""
    types_vl = (SRC_BACKEND / "codegen_types.vl").read_text(encoding="utf-8")
    assert "act emit_type_then_space(sb: @StringBuilder, ct: CType)" in types_vl
    assert "act emit_type_str_then_space(sb: @StringBuilder, type_name: string)" in types_vl

    array_vl = (SRC_BACKEND / "array_gen.vl").read_text(encoding="utf-8")
    assert "emit_type_str_then_space" in array_vl

    decl_vl = (SRC_BACKEND / "codegen_decl.vl").read_text(encoding="utf-8")
    assert "emit_type_str_then_space" in decl_vl

    c_vl = (SRC_BACKEND / "codegen_c.vl").read_text(encoding="utf-8")
    assert "emit_type_str_then_space" in c_vl

    stmt_vl = (SRC_BACKEND / "codegen_stmt.vl").read_text(encoding="utf-8")
    assert "emit_type_then_space" in stmt_vl
    assert "emit_type_str_then_space" in stmt_vl

    range_vl = (SRC_BACKEND / "range_gen.vl").read_text(encoding="utf-8")
    assert "emit_type_then_space" in range_vl


def test_structural_loop_var_c_type_no_trailing_space_convention():
    """Verify loop_var_c_type returns CType with needs_space: false."""
    lit_vl = (SRC_BACKEND / "codegen_lit.vl").read_text(encoding="utf-8")
    # All make_ctype calls in loop_var_c_type must specify false for needs_space
    lines = [line.strip() for line in lit_vl.splitlines() if "make_ctype(" in line]
    assert len(lines) >= 10
    for line in lines:
        assert line.endswith("false) }") or line.endswith("false)")


def test_emitted_c_exact_token_spacing(tmp_path):
    """Verify that emitted C has clean token separation without double spaces or glued identifiers."""
    src_file = tmp_path / "explicit_spacing.vl"
    src_code = """
data Point {
    x: i32
    y: i32
    label: string
}

let g_scale: i32 = 100

act compute_offset(p: @Point, delta: i32) -> i32 {
    let local_x: i32 = p.x
    let local_y: i32 = p.y
    mut total: i32 = 0
    loop i in 0..delta {
        total += i
    }
    return local_x + local_y + total + g_scale
}

act main() -> i32 {
    mut pt = Point{ x: 10, y: 20, label: "origin" }
    let res = compute_offset(@pt, 5)
    if res != 140 { return 1 }
    return 0
}
"""
    src_file.write_text(src_code, encoding="utf-8")
    c_file = tmp_path / "explicit_spacing.c"

    res = subprocess.run(
        [str(VELO_EXE), "emit-c", str(src_file), "-o", str(c_file)],
        capture_output=True,
        text=True,
        env=get_build_env(),
    )
    assert res.returncode == 0, f"emit-c failed: {res.stderr}\nstdout: {res.stdout}"

    c_code = c_file.read_text(encoding="utf-8")

    # Struct fields: int32_t x; int32_t y; const char* label;
    assert "int32_t x;" in c_code
    assert "int32_t y;" in c_code
    assert "const char* label;" in c_code

    # Global: int32_t g_scale
    assert "int32_t g_scale = 100;" in c_code

    # Function prototype and definition: int32_t compute_offset(Point* p, int32_t delta)
    assert "int32_t compute_offset(" in c_code
    assert "Point* p" in c_code
    assert "int32_t delta" in c_code

    # Local variable declarations
    assert "int32_t local_x = " in c_code
    assert "int32_t local_y = " in c_code
    assert "int32_t total = 0;" in c_code

    # Loop header for dynamic range
    assert "for (int32_t __start_i = " in c_code

    # Ensure no malformed double spaces in declarations
    assert "int32_t  x" not in c_code
    assert "int32_t  y" not in c_code
    assert "int32_t  local_x" not in c_code
    assert "int32_t  compute_offset" not in c_code


def test_compiled_program_execution(tmp_path):
    """Verify that a program exercising all refactored type emission paths compiles and runs."""
    src_file = tmp_path / "run_test.vl"
    exe_file = tmp_path / "run_test.exe"
    src_code = """
data Record {
    id: i64
    count: usize
    valid: bool
}

let g_base: i64 = 500i64

act process_record(rec: @Record, factor: i64) -> i64 {
    let local_id: i64 = rec.id
    let local_cnt: i64 = rec.count as i64
    mut acc: i64 = 0
    loop i in 0i64..factor {
        acc += i
    }
    return local_id + local_cnt + acc + g_base
}

act main() -> i32 {
    mut r = Record{ id: 1000i64, count: 5usize, valid: true }
    let ans = process_record(@r, 4i64)
    // 1000 + 5 + (0+1+2+3=6) + 500 = 1511
    if ans != 1511i64 { return 1 }
    return 0
}
"""
    src_file.write_text(src_code, encoding="utf-8")

    res = subprocess.run(
        [str(VELO_EXE), "build", str(src_file), "-o", str(exe_file)],
        capture_output=True,
        text=True,
        env=get_build_env(),
    )
    assert res.returncode == 0, f"build failed: {res.stderr}\nstdout: {res.stdout}"

    run_res = subprocess.run([str(exe_file)], capture_output=True, text=True)
    assert run_res.returncode == 0, f"execution failed with return code {run_res.returncode}"
