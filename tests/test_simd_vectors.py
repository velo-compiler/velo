import json
import os
import subprocess
import sys
import pytest
from conftest import velo_exe

def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)

def _run_stage1(args):
    return subprocess.run(
        [sys.executable, "velo.py"] + args,
        capture_output=True,
        text=True, encoding="utf-8", errors="replace"
    )

def _run_stage2(args):
    if not os.path.exists(str(velo_exe())):
        pytest.skip("bin/velo.exe not built; skipping native stage 2 test")
    return subprocess.run(
        [str(velo_exe())] + args,
        capture_output=True,
        text=True, encoding="utf-8", errors="replace"
    )

POSITIVE_SIMD_EXECUTION = """use sys.io
use sys.mem

aka Vec4 = f32x4
aka IVec4 = i32x4

data Particle {
    pos: f32x4
    vel: Vec4
    flags: IVec4
}

act transform(v: f32x4) -> f32x4 {
    let p = (@v) as @f32
    return f32x4(p[0] * 2.0, p[1] * 2.0, p[2] * 2.0, p[3] * 2.0)
}

act main() -> i32 {
    let v = f32x4(10.0, 20.0, 30.0, 40.0)
    let s = f32x4_splat(7.5)
    let iv = i32x4(100, -200, 300, -400)
    let isplat = i32x4_splat(88)

    // Verify 16-byte alignment
    assert(((@v) as usize) % 16 == 0, "f32x4 16-byte alignment")
    assert(((@s) as usize) % 16 == 0, "f32x4_splat 16-byte alignment")
    assert(((@iv) as usize) % 16 == 0, "i32x4 16-byte alignment")
    assert(((@isplat) as usize) % 16 == 0, "i32x4_splat 16-byte alignment")

    // Verify data preservation in memory lanes
    let pv = (@v) as @f32
    assert(pv[0] == 10.0 and pv[1] == 20.0 and pv[2] == 30.0 and pv[3] == 40.0, "f32x4 lanes")

    let ps = (@s) as @f32
    assert(ps[0] == 7.5 and ps[1] == 7.5 and ps[2] == 7.5 and ps[3] == 7.5, "f32x4_splat lanes")

    let piv = (@iv) as @i32
    assert(piv[0] == 100 and piv[1] == -200 and piv[2] == 300 and piv[3] == -400, "i32x4 lanes")

    let pis = (@isplat) as @i32
    assert(pis[0] == 88 and pis[1] == 88 and pis[2] == 88 and pis[3] == 88, "i32x4_splat lanes")

    // Verify function parameter passing and return
    let res = transform(v)
    let pres = (@res) as @f32
    assert(pres[0] == 20.0 and pres[1] == 40.0 and pres[2] == 60.0 and pres[3] == 80.0, "transform return")

    // Verify struct fields with SIMD vectors
    let p = Particle{ pos: f32x4(1.0, 2.0, 3.0, 4.0), vel: f32x4_splat(0.5), flags: i32x4(1, 2, 3, 4) }
    let ppos = (@p.pos) as @f32
    assert(ppos[0] == 1.0 and ppos[1] == 2.0 and ppos[2] == 3.0 and ppos[3] == 4.0, "particle pos")
    let pvel = (@p.vel) as @f32
    assert(pvel[0] == 0.5 and pvel[1] == 0.5 and pvel[2] == 0.5 and pvel[3] == 0.5, "particle vel")
    let pflags = (@p.flags) as @i32
    assert(pflags[0] == 1 and pflags[1] == 2 and pflags[2] == 3 and pflags[3] == 4, "particle flags")

    // Verify zone memory allocation 16-byte alignment
    zone {
        let arena_v = mem.alloc(@f32x4, 4)
        assert(((arena_v as usize) % 16) == 0, "mem.alloc f32x4 16-byte alignment")
    }

    // Verify heap memory allocation 16-byte alignment
    let heap_v = mem.heap_alloc(@f32x4, 4)
    assert(((heap_v as usize) % 16) == 0, "mem.heap_alloc f32x4 16-byte alignment")
    mem.free(heap_v as @void)

    io.println("SIMD vectors passed successfully")
    return 0
}
"""

NEGATIVE_F32X4_ARITY_FEW = """use sys.io
act main() -> i32 {
    let v = f32x4(1.0, 2.0, 3.0)
    return 0
}
"""

NEGATIVE_F32X4_ARITY_MANY = """use sys.io
act main() -> i32 {
    let v = f32x4(1.0, 2.0, 3.0, 4.0, 5.0)
    return 0
}
"""

NEGATIVE_F32X4_ARG_STRING = """use sys.io
act main() -> i32 {
    let v = f32x4(1.0, 2.0, "bad", 4.0)
    return 0
}
"""

NEGATIVE_F32X4_SPLAT_ARITY = """use sys.io
act main() -> i32 {
    let v = f32x4_splat(1.0, 2.0)
    return 0
}
"""

NEGATIVE_F32X4_SPLAT_ARG = """use sys.io
act main() -> i32 {
    let v = f32x4_splat("bad")
    return 0
}
"""

NEGATIVE_I32X4_ARITY = """use sys.io
act main() -> i32 {
    let v = i32x4(1, 2)
    return 0
}
"""

NEGATIVE_I32X4_ARG_FLOAT = """use sys.io
act main() -> i32 {
    let v = i32x4(1, 2, 3.5, 4)
    return 0
}
"""

NEGATIVE_I32X4_SPLAT_ARITY = """use sys.io
act main() -> i32 {
    let v = i32x4_splat(1, 2)
    return 0
}
"""

NEGATIVE_I32X4_SPLAT_ARG_FLOAT = """use sys.io
act main() -> i32 {
    let v = i32x4_splat(1.5)
    return 0
}
"""

POSITIVE_SIMD_OPS_EXECUTION = """use sys.io

act main() -> i32 {
    // 1. f32x4 arithmetic
    let a = f32x4(10.0, 20.0, 30.0, 40.0)
    let b = f32x4(2.0, 4.0, 5.0, 8.0)
    let sum_f = a + b
    let diff_f = a - b
    let mul_f = a * b
    let div_f = a / b
    let neg_f = -a

    assert(sum_f.x == 12.0 and sum_f.y == 24.0 and sum_f.z == 35.0 and sum_f.w == 48.0, "f32x4 add")
    assert(diff_f.x == 8.0 and diff_f.y == 16.0 and diff_f.z == 25.0 and diff_f.w == 32.0, "f32x4 sub")
    assert(mul_f.x == 20.0 and mul_f.y == 80.0 and mul_f.z == 150.0 and mul_f.w == 320.0, "f32x4 mul")
    assert(div_f.x == 5.0 and div_f.y == 5.0 and div_f.z == 6.0 and div_f.w == 5.0, "f32x4 div")
    assert(neg_f.x == -10.0 and neg_f.y == -20.0 and neg_f.z == -30.0 and neg_f.w == -40.0, "f32x4 neg")

    // 2. i32x4 arithmetic
    let ia = i32x4(10, -20, 30, -40)
    let ib = i32x4(5, 5, 2, -2)
    let sum_i = ia + ib
    let diff_i = ia - ib
    let mul_i = ia * ib
    let neg_i = -ia

    assert(sum_i.x == 15 and sum_i.y == -15 and sum_i.z == 32 and sum_i.w == -42, "i32x4 add")
    assert(diff_i.x == 5 and diff_i.y == -25 and diff_i.z == 28 and diff_i.w == -38, "i32x4 sub")
    assert(mul_i.x == 50 and mul_i.y == -100 and mul_i.z == 60 and mul_i.w == 80, "i32x4 mul")
    assert(neg_i.x == -10 and neg_i.y == 20 and neg_i.z == -30 and neg_i.w == 40, "i32x4 neg")

    // 3. Equality
    let eq1 = f32x4(1.0, 2.0, 3.0, 4.0)
    let eq2 = f32x4(1.0, 2.0, 3.0, 4.0)
    let eq3 = f32x4(1.0, 2.0, 3.0, 5.0)
    assert(eq1 == eq2, "f32x4 eq true")
    assert(!(eq1 == eq3), "f32x4 eq false")
    assert(eq1 != eq3, "f32x4 neq true")
    assert(!(eq1 != eq2), "f32x4 neq false")

    let ieq1 = i32x4(1, 2, 3, 4)
    let ieq2 = i32x4(1, 2, 3, 4)
    let ieq3 = i32x4(1, 2, 3, 9)
    assert(ieq1 == ieq2, "i32x4 eq true")
    assert(!(ieq1 == ieq3), "i32x4 eq false")
    assert(ieq1 != ieq3, "i32x4 neq true")
    assert(!(ieq1 != ieq2), "i32x4 neq false")

    // 4. Index expressions and dynamic lane access
    assert(a[0] == 10.0 and a[1] == 20.0 and a[2] == 30.0 and a[3] == 40.0, "f32x4 literal indexing")
    loop i in 0..4 {
        assert(a[i] == (i as f32 + 1.0) * 10.0, "f32x4 dynamic loop indexing")
    }

    assert(ia[0] == 10 and ia[1] == -20 and ia[2] == 30 and ia[3] == -40, "i32x4 literal indexing")

    // 5. Lane mutation
    mut mut_v = f32x4(1.0, 2.0, 3.0, 4.0)
    mut_v.x = 100.0
    mut_v.y = 200.0
    mut_v.z = 300.0
    mut_v.w = 400.0
    assert(mut_v.x == 100.0 and mut_v.y == 200.0 and mut_v.z == 300.0 and mut_v.w == 400.0, "member assign")

    mut_v[1] = 999.0
    assert(mut_v[1] == 999.0, "index assign")
    mut_v[1] += 1.0
    assert(mut_v[1] == 1000.0, "index compound assign")
    mut_v.x += 50.0
    assert(mut_v.x == 150.0, "member compound assign")

    // 6. Pointer lane access and mutation
    let pv = @mut_v
    assert(pv.x == 150.0, "ptr member read")
    assert(pv[1] == 1000.0, "ptr index read")
    pv.z = 777.0
    assert(mut_v.z == 777.0, "ptr member write")
    pv[3] = 888.0
    assert(mut_v.w == 888.0, "ptr index write")

    // 7. Vector compound assignments
    mut vcomp = f32x4(1.0, 2.0, 3.0, 4.0)
    vcomp += f32x4(10.0, 20.0, 30.0, 40.0)
    assert(vcomp.x == 11.0 and vcomp.y == 22.0 and vcomp.z == 33.0 and vcomp.w == 44.0, "vector +=")
    vcomp -= f32x4(1.0, 2.0, 3.0, 4.0)
    assert(vcomp.x == 10.0 and vcomp.y == 20.0 and vcomp.z == 30.0 and vcomp.w == 40.0, "vector -=")
    vcomp *= f32x4_splat(2.0)
    assert(vcomp.x == 20.0 and vcomp.y == 40.0 and vcomp.z == 60.0 and vcomp.w == 80.0, "vector *=")
    vcomp /= f32x4_splat(4.0)
    assert(vcomp.x == 5.0 and vcomp.y == 10.0 and vcomp.z == 15.0 and vcomp.w == 20.0, "vector /=")

    mut ivcomp = i32x4(1, 2, 3, 4)
    ivcomp += i32x4(10, 20, 30, 40)
    assert(ivcomp.x == 11 and ivcomp.y == 22 and ivcomp.z == 33 and ivcomp.w == 44, "i32x4 +=")
    ivcomp -= i32x4(1, 2, 3, 4)
    assert(ivcomp.x == 10 and ivcomp.y == 20 and ivcomp.z == 30 and ivcomp.w == 40, "i32x4 -=")
    ivcomp *= i32x4_splat(3)
    assert(ivcomp.x == 30 and ivcomp.y == 60 and ivcomp.z == 90 and ivcomp.w == 120, "i32x4 *=")

    io.println("SIMD vector arithmetic and lane ops passed successfully")
    return 0
}
"""

NEGATIVE_SIMD_UNKNOWN_MEMBER = """use sys.io
act main() -> i32 {
    let v = f32x4(1.0, 2.0, 3.0, 4.0)
    let x = v.foo
    return 0
}
"""

NEGATIVE_SIMD_BAD_INDEX = """use sys.io
act main() -> i32 {
    let v = f32x4(1.0, 2.0, 3.0, 4.0)
    let x = v["hello"]
    return 0
}
"""

NEGATIVE_SIMD_MISMATCH_OP = """use sys.io
act main() -> i32 {
    let v = f32x4(1.0, 2.0, 3.0, 4.0)
    let iv = i32x4(1, 2, 3, 4)
    let sum = v + iv
    return 0
}
"""

NEGATIVE_SIMD_I32_DIV = """use sys.io
act main() -> i32 {
    let iv1 = i32x4(1, 2, 3, 4)
    let iv2 = i32x4(1, 2, 3, 4)
    let d = iv1 / iv2
    return 0
}
"""

NEGATIVE_SIMD_BAD_UNARY = """use sys.io
act main() -> i32 {
    let v = f32x4(1.0, 2.0, 3.0, 4.0)
    let n = !v
    return 0
}
"""

NEGATIVE_SIMD_UNKNOWN_MEMBER_FUNC = """use sys.simd
act main() -> i32 {
    let x = simd.foo(1)
    return 0
}
"""

NEGATIVE_SIMD_BARE_CONSTANT = """use sys.simd
act main() -> i32 {
    let x = simd.dot
    return 0
}
"""

NEGATIVE_SIMD_DOT_ARITY = """use sys.simd
act main() -> i32 {
    let x = simd.dot(f32x4_splat(1.0))
    return 0
}
"""

NEGATIVE_SIMD_DOT_ARG_TYPE = """use sys.simd
act main() -> i32 {
    let x = simd.dot(f32x4_splat(1.0), "bad")
    return 0
}
"""

NEGATIVE_SIMD_SQRT_ARITY = """use sys.simd
act main() -> i32 {
    let x = simd.sqrt(f32x4_splat(1.0), f32x4_splat(2.0))
    return 0
}
"""

NEGATIVE_SIMD_SQRT_ARG_TYPE = """use sys.simd
act main() -> i32 {
    let x = simd.sqrt("bad")
    return 0
}
"""

NEGATIVE_SIMD_MIN_ARG_TYPE = """use sys.simd
act main() -> i32 {
    let x = simd.min("bad", "bad")
    return 0
}
"""

NEGATIVE_SIMD_MIN_MISMATCH_TYPES = """use sys.simd
act main() -> i32 {
    let x = simd.min(f32x4_splat(1.0), i32x4_splat(1))
    return 0
}
"""


def test_stage1_simd_execution(tmp_path):
    src = _write(tmp_path, "test_simd.vl", POSITIVE_SIMD_EXECUTION)
    res = _run_stage1(["run", src])
    assert res.returncode == 0, f"Stage 1 failed: {res.stdout}\n{res.stderr}"
    assert "SIMD vectors passed successfully" in res.stdout

def test_stage2_simd_execution(tmp_path):
    src = _write(tmp_path, "test_simd.vl", POSITIVE_SIMD_EXECUTION)
    res = _run_stage2(["run", src])
    assert res.returncode == 0, f"Stage 2 failed: {res.stdout}\n{res.stderr}"
    assert "SIMD vectors passed successfully" in res.stdout

def test_stage1_simd_ops_execution(tmp_path):
    src = _write(tmp_path, "test_simd_ops.vl", POSITIVE_SIMD_OPS_EXECUTION)
    res = _run_stage1(["run", src])
    assert res.returncode == 0, f"Stage 1 ops failed: {res.stdout}\n{res.stderr}"
    assert "SIMD vector arithmetic and lane ops passed successfully" in res.stdout

def test_stage2_simd_ops_execution(tmp_path):
    src = _write(tmp_path, "test_simd_ops.vl", POSITIVE_SIMD_OPS_EXECUTION)
    res = _run_stage2(["run", src])
    assert res.returncode == 0, f"Stage 2 ops failed: {res.stdout}\n{res.stderr}"
    assert "SIMD vector arithmetic and lane ops passed successfully" in res.stdout

def test_stage1_simd_math_execution():
    res = _run_stage1(["run", "examples/36_simd_math.vl"])
    assert res.returncode == 0, f"Stage 1 math failed: {res.stdout}\n{res.stderr}"
    assert "Benchmark completed successfully." in res.stdout

def test_stage2_simd_math_execution():
    res = _run_stage2(["run", "examples/36_simd_math.vl"])
    assert res.returncode == 0, f"Stage 2 math failed: {res.stdout}\n{res.stderr}"
    assert "Benchmark completed successfully." in res.stdout

@pytest.mark.parametrize("source,expected_snippet", [
    (NEGATIVE_F32X4_ARITY_FEW, "f32x4 constructor expects exactly 4 arguments: (x, y, z, w)"),
    (NEGATIVE_F32X4_ARITY_MANY, "f32x4 constructor expects exactly 4 arguments: (x, y, z, w)"),
    (NEGATIVE_F32X4_ARG_STRING, "f32x4 constructor arguments must be float or integer (got string)"),
    (NEGATIVE_F32X4_SPLAT_ARITY, "f32x4_splat constructor expects exactly 1 argument: (val)"),
    (NEGATIVE_F32X4_SPLAT_ARG, "f32x4_splat constructor argument must be float or integer (got string)"),
    (NEGATIVE_I32X4_ARITY, "i32x4 constructor expects exactly 4 arguments: (x, y, z, w)"),
    (NEGATIVE_I32X4_ARG_FLOAT, "i32x4 constructor arguments must be integer (got f32)"),
    (NEGATIVE_I32X4_SPLAT_ARITY, "i32x4_splat constructor expects exactly 1 argument: (val)"),
    (NEGATIVE_I32X4_SPLAT_ARG_FLOAT, "i32x4_splat constructor argument must be integer (got f32)"),
    (NEGATIVE_SIMD_UNKNOWN_MEMBER, "unknown SIMD vector member 'foo' (available: x, y, z, w)"),
    (NEGATIVE_SIMD_BAD_INDEX, "SIMD vector index must be an integer (got string)"),
    (NEGATIVE_SIMD_MISMATCH_OP, "mismatched operand types for SIMD binary operator '+': f32x4 and i32x4"),
    (NEGATIVE_SIMD_I32_DIV, "integer vector division is not supported"),
    (NEGATIVE_SIMD_BAD_UNARY, "unary operator '!' not supported for SIMD vector type f32x4"),
    (NEGATIVE_SIMD_UNKNOWN_MEMBER_FUNC, "unknown simd member 'foo' (functions: dot, min, max, sqrt are available)"),
    (NEGATIVE_SIMD_BARE_CONSTANT, "unknown simd constant 'dot' (simd functions are: dot, min, max, sqrt) (functions need parens: simd.dot(...))"),
    (NEGATIVE_SIMD_DOT_ARITY, "simd.dot expects exactly 2 arguments: (f32x4 a, f32x4 b)"),
    (NEGATIVE_SIMD_DOT_ARG_TYPE, "simd.dot expects f32x4 arguments (got string)"),
    (NEGATIVE_SIMD_SQRT_ARITY, "simd.sqrt expects exactly 1 argument: (f32x4 a)"),
    (NEGATIVE_SIMD_SQRT_ARG_TYPE, "simd.sqrt expects f32x4 argument (got string)"),
    (NEGATIVE_SIMD_MIN_ARG_TYPE, "simd.min expects f32x4 or i32x4 arguments (got string)"),
    (NEGATIVE_SIMD_MIN_MISMATCH_TYPES, "simd.min expects matching operand types (got f32x4 and i32x4)"),
])
def test_stage1_negative_simd_diagnostics(tmp_path, source, expected_snippet):
    src = _write(tmp_path, "neg_test.vl", source)
    res = _run_stage1(["run", src])
    assert res.returncode != 0, f"Expected non-zero returncode for invalid SIMD call, got {res.returncode}"
    combined = res.stdout + res.stderr
    assert expected_snippet in combined, f"Expected '{expected_snippet}' in Stage 1 error output:\n{combined}"

@pytest.mark.parametrize("source,expected_snippet", [
    (NEGATIVE_F32X4_ARITY_FEW, "f32x4 constructor expects exactly 4 arguments: (x, y, z, w)"),
    (NEGATIVE_F32X4_ARITY_MANY, "f32x4 constructor expects exactly 4 arguments: (x, y, z, w)"),
    (NEGATIVE_F32X4_ARG_STRING, "f32x4 constructor arguments must be float or integer (got string)"),
    (NEGATIVE_F32X4_SPLAT_ARITY, "f32x4_splat constructor expects exactly 1 argument: (val)"),
    (NEGATIVE_F32X4_SPLAT_ARG, "f32x4_splat constructor argument must be float or integer (got string)"),
    (NEGATIVE_I32X4_ARITY, "i32x4 constructor expects exactly 4 arguments: (x, y, z, w)"),
    (NEGATIVE_I32X4_ARG_FLOAT, "i32x4 constructor arguments must be integer (got f32)"),
    (NEGATIVE_I32X4_SPLAT_ARITY, "i32x4_splat constructor expects exactly 1 argument: (val)"),
    (NEGATIVE_I32X4_SPLAT_ARG_FLOAT, "i32x4_splat constructor argument must be integer (got f32)"),
    (NEGATIVE_SIMD_UNKNOWN_MEMBER, "unknown SIMD vector member 'foo' (available: x, y, z, w)"),
    (NEGATIVE_SIMD_BAD_INDEX, "SIMD vector index must be an integer (got string)"),
    (NEGATIVE_SIMD_MISMATCH_OP, "mismatched operand types for SIMD binary operator '+': f32x4 and i32x4"),
    (NEGATIVE_SIMD_I32_DIV, "integer vector division is not supported"),
    (NEGATIVE_SIMD_BAD_UNARY, "unary operator '!' not supported for SIMD vector type f32x4"),
    (NEGATIVE_SIMD_UNKNOWN_MEMBER_FUNC, "unknown simd member 'foo' (functions: dot, min, max, sqrt are available)"),
    (NEGATIVE_SIMD_BARE_CONSTANT, "unknown simd constant 'dot' (simd functions are: dot, min, max, sqrt) (functions need parens: simd.dot(...))"),
    (NEGATIVE_SIMD_DOT_ARITY, "simd.dot expects exactly 2 arguments: (f32x4 a, f32x4 b)"),
    (NEGATIVE_SIMD_DOT_ARG_TYPE, "simd.dot expects f32x4 arguments (got string)"),
    (NEGATIVE_SIMD_SQRT_ARITY, "simd.sqrt expects exactly 1 argument: (f32x4 a)"),
    (NEGATIVE_SIMD_SQRT_ARG_TYPE, "simd.sqrt expects f32x4 argument (got string)"),
    (NEGATIVE_SIMD_MIN_ARG_TYPE, "simd.min expects f32x4 or i32x4 arguments (got string)"),
    (NEGATIVE_SIMD_MIN_MISMATCH_TYPES, "simd.min expects matching operand types (got f32x4 and i32x4)"),
])
def test_stage2_negative_simd_diagnostics(tmp_path, source, expected_snippet):
    src = _write(tmp_path, "neg_test.vl", source)
    res = _run_stage2(["run", src])
    assert res.returncode != 0, f"Expected non-zero returncode for invalid SIMD call, got {res.returncode}"
    combined = res.stdout + res.stderr
    assert expected_snippet in combined, f"Expected '{expected_snippet}' in Stage 2 error output:\n{combined}"

def test_check_cli_json_simd_diagnostics(tmp_path):
    src_valid = _write(tmp_path, "valid.vl", POSITIVE_SIMD_EXECUTION)
    res1 = _run_stage1(["check", src_valid, "--json"])
    assert res1.returncode == 0
    report1 = json.loads(res1.stdout)
    assert report1["ok"] is True
    assert len(report1["diagnostics"]) == 0

    res2 = _run_stage2(["check", src_valid, "--json"])
    assert res2.returncode == 0
    report2 = json.loads(res2.stdout)
    assert report2["ok"] is True
    assert len(report2["diagnostics"]) == 0

    src_ops_valid = _write(tmp_path, "valid_ops.vl", POSITIVE_SIMD_OPS_EXECUTION)
    res1_ops = _run_stage1(["check", src_ops_valid, "--json"])
    assert res1_ops.returncode == 0
    report1_ops = json.loads(res1_ops.stdout)
    assert report1_ops["ok"] is True
    assert len(report1_ops["diagnostics"]) == 0

    res2_ops = _run_stage2(["check", src_ops_valid, "--json"])
    assert res2_ops.returncode == 0
    report2_ops = json.loads(res2_ops.stdout)
    assert report2_ops["ok"] is True
    assert len(report2_ops["diagnostics"]) == 0

    src_invalid = _write(tmp_path, "invalid.vl", NEGATIVE_F32X4_ARG_STRING)
    res1_inv = _run_stage1(["check", src_invalid, "--json"])
    assert res1_inv.returncode != 0
    report1_inv = json.loads(res1_inv.stdout)
    assert report1_inv["ok"] is False
    assert len(report1_inv["diagnostics"]) > 0
    assert "f32x4 constructor arguments must be float or integer (got string)" in report1_inv["diagnostics"][0]["message"]

    res2_inv = _run_stage2(["check", src_invalid, "--json"])
    assert res2_inv.returncode != 0
    report2_inv = json.loads(res2_inv.stdout)
    assert report2_inv["ok"] is False
    assert len(report2_inv["diagnostics"]) > 0
    assert "f32x4 constructor arguments must be float or integer (got string)" in report2_inv["diagnostics"][0]["message"]

    src_member_inv = _write(tmp_path, "invalid_member.vl", NEGATIVE_SIMD_UNKNOWN_MEMBER)
    res1_mem = _run_stage1(["check", src_member_inv, "--json"])
    assert res1_mem.returncode != 0
    report1_mem = json.loads(res1_mem.stdout)
    assert report1_mem["ok"] is False
    assert "unknown SIMD vector member 'foo' (available: x, y, z, w)" in report1_mem["diagnostics"][0]["message"]

    res2_mem = _run_stage2(["check", src_member_inv, "--json"])
    assert res2_mem.returncode != 0
    report2_mem = json.loads(res2_mem.stdout)
    assert report2_mem["ok"] is False
    assert "unknown SIMD vector member 'foo' (available: x, y, z, w)" in report2_mem["diagnostics"][0]["message"]

    src_simd_math = "examples/36_simd_math.vl"
    res1_math = _run_stage1(["check", src_simd_math, "--json"])
    assert res1_math.returncode == 0
    report1_math = json.loads(res1_math.stdout)
    assert report1_math["ok"] is True
    assert len(report1_math["diagnostics"]) == 0

    res2_math = _run_stage2(["check", src_simd_math, "--json"])
    assert res2_math.returncode == 0
    report2_math = json.loads(res2_math.stdout)
    assert report2_math["ok"] is True
    assert len(report2_math["diagnostics"]) == 0

    src_simd_dot_inv = _write(tmp_path, "invalid_dot.vl", NEGATIVE_SIMD_DOT_ARG_TYPE)
    res1_dot = _run_stage1(["check", src_simd_dot_inv, "--json"])
    assert res1_dot.returncode != 0
    report1_dot = json.loads(res1_dot.stdout)
    assert report1_dot["ok"] is False
    assert "simd.dot expects f32x4 arguments (got string)" in report1_dot["diagnostics"][0]["message"]

    res2_dot = _run_stage2(["check", src_simd_dot_inv, "--json"])
    assert res2_dot.returncode != 0
    report2_dot = json.loads(res2_dot.stdout)
    assert report2_dot["ok"] is False
    assert "simd.dot expects f32x4 arguments (got string)" in report2_dot["diagnostics"][0]["message"]

