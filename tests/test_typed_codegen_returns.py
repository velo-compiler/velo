"""
Tests for Phase 80, Task 80.2 & 80.3:
Typed Codegen Returns via CType & Elimination of Trailing-Space Conventions.

Verifies:
1. `loop_var_c_type` returns a typed `CType` value with {name, width, is_signed, needs_space}.
2. Trailing-space string conventions ("int32_t ") are eliminated in favor of typed CType and ctype_render.
3. Emitted C for all loop types and induction widths (i8, u8, i16, u16, i32, u32, i64, u64, usize, isize, default)
   has clean token formatting: `for (<type> <var> = ...)` without double spaces or glued identifiers.
4. Emitted C runs correctly and passes all runtime assertions.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = REPO_ROOT / "bin" / "velo.exe"
CODEGEN_LIT_VL = REPO_ROOT / "src" / "backend" / "codegen_lit.vl"
CODEGEN_TYPES_VL = REPO_ROOT / "src" / "backend" / "codegen_types.vl"


def get_build_env():
    env = dict(os.environ)
    ucrt_bin = r"C:\msys64\ucrt64\bin"
    if os.path.exists(ucrt_bin) and ucrt_bin not in env.get("PATH", ""):
        env["PATH"] = ucrt_bin + ";" + env.get("PATH", "")
    return env


def test_structural_no_trailing_space_in_codegen_lit():
    """Verify that loop_var_c_type in codegen_lit.vl returns CType and contains no trailing-space strings."""
    content = CODEGEN_LIT_VL.read_text(encoding="utf-8")
    assert "act loop_var_c_type(type_name: string) -> CType" in content
    assert '"int32_t "' not in content
    assert '"int64_t "' not in content
    assert '"uint64_t "' not in content
    assert '"size_t "' not in content
    assert '"ptrdiff_t "' not in content
    assert '"uint32_t "' not in content
    assert '"int16_t "' not in content
    assert '"uint16_t "' not in content
    assert '"int8_t "' not in content
    assert '"uint8_t "' not in content


def test_structural_ctype_definition_in_codegen_types():
    """Verify that CType and its emission helpers are defined in codegen_types.vl."""
    content = CODEGEN_TYPES_VL.read_text(encoding="utf-8")
    assert "data CType {" in content
    assert "name: string" in content
    assert "width: i32" in content
    assert "is_signed: bool" in content
    assert "needs_space: bool" in content
    assert "act make_ctype(" in content
    assert "act ctype_render(" in content
    assert "act emit_type_then_space(" in content
    assert "act primitive_type_to_ctype(" in content


def test_loop_matrix_emitted_c_syntax(tmp_path):
    """Verify emitted C headers across all loop forms and induction widths."""
    src_file = tmp_path / "loop_matrix.vl"
    src_code = """
act test_static_loops() {
    mut s: i64 = 0
    loop i in 0i8..5i8 { s += i as i64 }
    loop i in 0u8..5u8 { s += i as i64 }
    loop i in 0i16..5i16 { s += i as i64 }
    loop i in 0u16..5u16 { s += i as i64 }
    loop i in 0i32..5i32 { s += i as i64 }
    loop i in 0u32..5u32 { s += i as i64 }
    loop i in 0i64..5i64 { s += i }
    loop i in 0u64..5u64 { s += i as i64 }
    loop i in 0usize..5usize { s += i as i64 }
    loop i in 0isize..5isize { s += i as i64 }
    loop i in 0..5 { s += i as i64 }
}

act test_dynamic_loops(a: i32, b: i32) {
    mut s: i32 = 0
    loop i in a..b { s += i }
}

act test_count_and_condition() {
    mut cnt: i32 = 0
    loop 5 { cnt += 1 }
    mut ok: bool = true
    loop ok {
        cnt += 1
        ok = false
    }
    loop {
        cnt += 1
        break
    }
}

act main() -> i32 {
    test_static_loops()
    test_dynamic_loops(1, 10)
    test_count_and_condition()
    return 0
}
"""
    src_file.write_text(src_code, encoding="utf-8")
    c_file = tmp_path / "loop_matrix.c"

    res = subprocess.run(
        [str(VELO_EXE), "emit-c", str(src_file), "-o", str(c_file)],
        capture_output=True,
        text=True,
        env=get_build_env(),
    )
    assert res.returncode == 0, f"emit-c failed: {res.stderr}\nstdout: {res.stdout}"

    c_code = c_file.read_text(encoding="utf-8")

    # Assert exact C header token spacing for every induction width
    # Note: per W1 floor (SPEC 7.2 item 9), 8-bit and 16-bit ranges widen to int32_t induction
    assert "for (int32_t i = 0" in c_code
    assert "for (uint32_t i = 0" in c_code
    assert "for (int64_t i = 0" in c_code
    assert "for (uint64_t i = 0" in c_code
    assert "for (size_t i = 0" in c_code
    assert "for (ptrdiff_t i = 0" in c_code

    # Assert no missing space or double space artifacts
    assert "for (int32_ti" not in c_code
    assert "for (int32_t  i" not in c_code
    assert "for (int64_ti" not in c_code
    assert "for (int64_t  i" not in c_code

    # Assert dynamic range loop header
    assert "for (int32_t __start_i =" in c_code


def test_loop_matrix_execution(tmp_path):
    """Verify that loop programs with all widths compile and execute correctly."""
    src_file = tmp_path / "loop_exec.vl"
    exe_file = tmp_path / "loop_exec.exe"
    src_code = """
act main() -> i32 {
    mut s: i64 = 0
    loop i in 0i8..5i8 { s += i as i64 }
    loop i in 0u8..5u8 { s += i as i64 }
    loop i in 0i16..5i16 { s += i as i64 }
    loop i in 0u16..5u16 { s += i as i64 }
    loop i in 0i32..5i32 { s += i as i64 }
    loop i in 0u32..5u32 { s += i as i64 }
    loop i in 0i64..5i64 { s += i }
    loop i in 0u64..5u64 { s += i as i64 }
    loop i in 0usize..5usize { s += i as i64 }
    loop i in 0isize..5isize { s += i as i64 }
    loop i in 0..5 { s += i as i64 }
    // 11 loops each summing 0+1+2+3+4 = 10 -> total 110
    if s != 110 { return 1 }

    mut cnt: i32 = 0
    loop 10 { cnt += 1 }
    if cnt != 10 { return 2 }

    mut dyn_s: i32 = 0
    let a = 1
    let b = 5
    loop i in a..b { dyn_s += i }
    // 1+2+3+4 = 10
    if dyn_s != 10 { return 3 }

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
    assert run_res.returncode == 0, f"Execution failed with return code {run_res.returncode}"
