import subprocess
import pytest
from pathlib import Path

def _run_stage1(cmd: list) -> subprocess.CompletedProcess:
    full_cmd = ["python", "velo.py"] + cmd
    return subprocess.run(full_cmd, capture_output=True, text=True)

def _run_stage2(cmd: list) -> subprocess.CompletedProcess:
    velo_exe = Path("bin/velo.exe").resolve()
    if not velo_exe.exists():
        pytest.skip("bin/velo.exe not built yet")
    full_cmd = [str(velo_exe)] + cmd
    return subprocess.run(full_cmd, capture_output=True, text=True)

def test_optional_pointer_has_and_val(tmp_path):
    code = """
use std.io

data Node {
    val: i32
}

act main() {
    mut n = Node{ val: 42 }
    let p_null: ?@Node = null
    let p_some: ?@Node = @n

    if p_null.has {
        io.println("FAIL: p_null should not have value")
    } else {
        io.println("p_null has false OK")
    }

    if p_some.has {
        let unwrapped = p_some.val
        io.println("p_some has true OK: {unwrapped.val}")
    }
}
"""
    f = tmp_path / "test_opt_ptr.vl"
    f.write_text(code, encoding="utf-8")

    # Stage 1
    res1 = _run_stage1(["run", str(f)])
    assert res1.returncode == 0, f"Stage 1 failed: {res1.stderr}"
    assert "p_null has false OK" in res1.stdout
    assert "p_some has true OK: 42" in res1.stdout

    # Stage 2
    res2 = _run_stage2(["run", str(f)])
    assert res2.returncode == 0, f"Stage 2 failed: {res2.stderr}"
    assert "p_null has false OK" in res2.stdout
    assert "p_some has true OK: 42" in res2.stdout

def test_optional_coalescing(tmp_path):
    code = """
use std.io

data Node {
    val: i32
}

act main() {
    mut n1 = Node{ val: 10 }
    mut n_def = Node{ val: 99 }

    let opt_null: ?@Node = null
    let opt_val: ?@Node = @n1

    let res1 = opt_null ?? @n_def
    let res2 = opt_val ?? @n_def

    io.println("res1 val: {res1.val}")
    io.println("res2 val: {res2.val}")
}
"""
    f = tmp_path / "test_opt_coalesce.vl"
    f.write_text(code, encoding="utf-8")

    # Stage 1
    res1 = _run_stage1(["run", str(f)])
    assert res1.returncode == 0, f"Stage 1 failed: {res1.stderr}"
    assert "res1 val: 99" in res1.stdout
    assert "res2 val: 10" in res1.stdout

    # Stage 2
    res2 = _run_stage2(["run", str(f)])
    assert res2.returncode == 0, f"Stage 2 failed: {res2.stderr}"
    assert "res1 val: 99" in res2.stdout
    assert "res2 val: 10" in res2.stdout

def test_optional_unwrap_operator(tmp_path):
    code = """
use std.io

data Node {
    val: i32
}

act main() {
    mut n = Node{ val: 777 }
    let opt: ?@Node = @n
    let unwrapped = opt!
    io.println("unwrapped val: {unwrapped.val}")
}
"""
    f = tmp_path / "test_opt_unwrap.vl"
    f.write_text(code, encoding="utf-8")

    # Stage 1
    res1 = _run_stage1(["run", str(f)])
    assert res1.returncode == 0, f"Stage 1 failed: {res1.stderr}"
    assert "unwrapped val: 777" in res1.stdout

    # Stage 2
    res2 = _run_stage2(["run", str(f)])
    assert res2.returncode == 0, f"Stage 2 failed: {res2.stderr}"
    assert "unwrapped val: 777" in res2.stdout

def test_optional_postfix_syntax(tmp_path):
    code = """
use std.io

data Node {
    val: i32
}

act main() {
    mut n = Node{ val: 123 }
    let opt: @Node? = @n
    if opt.has {
        io.println("postfix syntax OK: {opt.val.val}")
    }
}
"""
    f = tmp_path / "test_opt_postfix.vl"
    f.write_text(code, encoding="utf-8")

    # Stage 1
    res1 = _run_stage1(["run", str(f)])
    assert res1.returncode == 0, f"Stage 1 failed: {res1.stderr}"
    assert "postfix syntax OK: 123" in res1.stdout

    # Stage 2
    res2 = _run_stage2(["run", str(f)])
    assert res2.returncode == 0, f"Stage 2 failed: {res2.stderr}"
    assert "postfix syntax OK: 123" in res2.stdout

def test_optional_value_types(tmp_path):
    code = """
use std.io

act main() {
    let opt_int_null: ?i32 = null
    let opt_int_val: ?i32 = 42

    let r1 = opt_int_null ?? 100
    let r2 = opt_int_val ?? 100

    io.println("val coalesced: {r1} and {r2}")
    if opt_int_val.has {
        io.println("val has OK: {opt_int_val.val}")
    }
    let unwrapped = opt_int_val!
    io.println("val unwrapped: {unwrapped}")
}
"""
    f = tmp_path / "test_opt_val_types.vl"
    f.write_text(code, encoding="utf-8")

    # Stage 1
    res1 = _run_stage1(["run", str(f)])
    assert res1.returncode == 0, f"Stage 1 failed: {res1.stderr}"
    assert "val coalesced: 100 and 42" in res1.stdout
    assert "val has OK: 42" in res1.stdout
    assert "val unwrapped: 42" in res1.stdout

    # Stage 2
    res2 = _run_stage2(["run", str(f)])
    assert res2.returncode == 0, f"Stage 2 failed: {res2.stderr}"
    assert "val coalesced: 100 and 42" in res2.stdout
    assert "val has OK: 42" in res2.stdout
    assert "val unwrapped: 42" in res2.stdout

def test_compile_error_member_access_without_unwrap(tmp_path):
    code = """
data Node {
    num: i32
}

act main() {
    mut n = Node{ num: 10 }
    let opt: ?@Node = @n
    let x = opt.num
}
"""
    f = tmp_path / "test_opt_error_access.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["check", str(f)])
    assert res1.returncode != 0
    assert "without unwrapping" in (res1.stderr + res1.stdout)

    res2 = _run_stage2(["check", str(f)])
    assert res2.returncode != 0
    assert "without unwrapping" in (res2.stderr + res2.stdout)

def test_compile_error_assign_optional_to_non_optional(tmp_path):
    code = """
data Node {
    val: i32
}

act main() {
    mut n = Node{ val: 10 }
    let opt: ?@Node = @n
    let reg: @Node = opt
}
"""
    f = tmp_path / "test_opt_error_assign.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["check", str(f)])
    assert res1.returncode != 0

    res2 = _run_stage2(["check", str(f)])
    assert res2.returncode != 0

def test_compile_error_assign_null_to_value_type(tmp_path):
    code = """
act main() {
    let x: i32 = null
}
"""
    f = tmp_path / "test_null_value_type.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["check", str(f)])
    assert res1.returncode != 0

    res2 = _run_stage2(["check", str(f)])
    assert res2.returncode != 0
