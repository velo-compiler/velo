import os
import subprocess
import tempfile
import pytest
from conftest import cc_dir, velo_exe

COMPILER = str(velo_exe())

def get_env():
    env = dict(os.environ)
    env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return env

def run_velo_source(code: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "test.vl")
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
        return subprocess.run(
            [COMPILER, "run", src],
            env=get_env(),
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            timeout=30,
        )

def build_velo_source(code: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "test.vl")
        out_bin = os.path.join(tmpdir, "test.exe")
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
        return subprocess.run(
            [COMPILER, "build", src, "-o", out_bin],
            env=get_env(),
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            timeout=30,
        )

def emit_c_source(code: str) -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "test.vl")
        out_c = os.path.join(tmpdir, "out.c")
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
        res = subprocess.run(
            [COMPILER, "emit-c", src, "-o", out_c],
            env=get_env(),
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            timeout=30,
        )
        assert res.returncode == 0, f"emit-c failed: {res.stdout}\n{res.stderr}"
        with open(out_c, "r", encoding="utf-8") as f:
            return f.read()

def test_wide_range_loop_emits_int64_and_correct_direction():
    # Verify Phase 53 Exit Criterion: loop i in 0..3000000000 does not wrap or invert
    code = """
act main() {
    loop i in 0..3000000000 {
        if i > 0 { break }
    }
}
"""
    c_source = emit_c_source(code)
    assert "for (int64_t" in c_source
    assert "3000000000LL" in c_source
    assert " < " in c_source

def test_wide_range_loop_execution_ascending():
    code = """
act main() {
    mut count: i64 = 0
    loop i in 3000000000..3000000005 {
        count += 1
    }
    io.println("COUNT={count}")
}
"""
    res = run_velo_source(code)
    assert res.returncode == 0, f"Execution failed: {res.stdout}\n{res.stderr}"
    assert "COUNT=5" in res.stdout

def test_wide_range_loop_execution_descending():
    # 3000000005..3000000000 must be detected as reverse loop (is_rev = true)
    code = """
act main() {
    mut count: i64 = 0
    loop i in 3000000005..3000000000 {
        count += 1
    }
    io.println("COUNT={count}")
}
"""
    res = run_velo_source(code)
    assert res.returncode == 0, f"Execution failed: {res.stdout}\n{res.stderr}"
    assert "COUNT=5" in res.stdout

def test_negative_range_loop_descending():
    # -5..-10 must be detected as reverse loop
    code = """
act main() {
    mut sum: i32 = 0
    loop i in -5..-10 {
        sum += i
    }
    io.println("SUM={sum}")
}
"""
    res = run_velo_source(code)
    assert res.returncode == 0, f"Execution failed: {res.stdout}\n{res.stderr}"
    # -5 + -6 + -7 + -8 + -9 = -35
    assert "SUM=-35" in res.stdout

def test_fixed_array_wide_index_rejected_at_compile_time():
    # 4294967298 would wrap to 2 in 32-bit int and silently pass for [5]i32
    code = """
act main() {
    let arr: [5]i32 = [10, 20, 30, 40, 50]
    let x = arr[4294967298]
}
"""
    res = build_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Array index out of bounds" in out

def test_fixed_array_negative_index_rejected_at_compile_time():
    code = """
act main() {
    let arr: [5]i32 = [10, 20, 30, 40, 50]
    let x = arr[-1]
}
"""
    res = build_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Array index out of bounds" in out

def test_fixed_array_wide_length_rejected_with_diagnostic():
    # 4294967297 exceeds 32-bit signed integer range (wrapped to 1 previously)
    code = """
act main() {
    let arr: [4294967297]i32 = [1]
}
"""
    res = build_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Fixed-size array length exceeds 32-bit integer range" in out

def test_enum_discriminant_wide_decimal_rejected():
    # 3000000000 exceeds 32-bit signed integer range
    code = """
kind Status {
    Active = 3000000000
}
act main() { }
"""
    res = build_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Enum discriminant exceeds 32-bit signed integer range" in out

def test_enum_discriminant_wide_hex_rejected():
    # 0x100000000 exceeds 32-bit signed integer range
    code = """
kind Status {
    Active = 0x100000000
}
act main() { }
"""
    res = build_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Enum discriminant exceeds 32-bit signed integer range" in out

def test_struct_align_wide_rejected():
    # 131072 exceeds max alignment 65536
    code = """
data Huge #align(131072) {
    x: i32
}
act main() { }
"""
    res = build_velo_source(code)
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert "Alignment value must be a positive integer <= 65536" in out

def test_range_loop_with_wide_variable_end():
    code = """
act main() {
    let limit: u64 = 3000000000_u64
    loop i in 0..limit {
        if i > 0_u64 { break }
    }
}
"""
    c_source = emit_c_source(code)
    assert "for (uint64_t" in c_source
    assert "limit" in c_source

