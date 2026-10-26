import json
import os
import subprocess
import sys
import pytest

def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)

def _run_stage1(args):
    return subprocess.run(
        [sys.executable, "velo.py"] + args,
        capture_output=True,
        text=True
    )

def _run_stage2(args):
    if not os.path.exists("bin/velo.exe"):
        pytest.skip("bin/velo.exe not built; skipping native stage 2 test")
    return subprocess.run(
        ["bin/velo.exe"] + args,
        capture_output=True,
        text=True
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
