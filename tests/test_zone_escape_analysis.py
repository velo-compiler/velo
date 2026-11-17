import subprocess
import pytest
from pathlib import Path
from conftest import velo_exe

def _run_stage1(cmd: list) -> subprocess.CompletedProcess:
    full_cmd = ["python", "velo.py"] + cmd
    return subprocess.run(full_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

def _run_stage2(cmd: list) -> subprocess.CompletedProcess:
    velo_bin = Path(str(velo_exe())).resolve()
    if not velo_bin.exists():
        pytest.skip("bin/velo.exe not built yet")
    full_cmd = [str(velo_bin)] + cmd
    return subprocess.run(full_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

def test_zone_pointer_return_rejected(tmp_path):
    code = """
use sys.mem

act bad_return() -> @i32 {
    zone {
        let p: @i32 = mem.alloc(@i32, 1)
        return p
    }
}
act main() {}
"""
    f = tmp_path / "bad_return.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["emit-c", str(f)])
    assert res1.returncode != 0
    assert "cannot return pointer allocated inside lexical zone" in (res1.stderr + res1.stdout)

    res2 = _run_stage2(["emit-c", str(f)])
    assert res2.returncode != 0
    assert "cannot return pointer allocated inside lexical zone" in (res2.stderr + res2.stdout)

def test_zone_pointer_direct_return_rejected(tmp_path):
    code = """
use sys.mem

act bad_direct_return() -> @i32 {
    zone {
        return mem.alloc(@i32, 1)
    }
}
act main() {}
"""
    f = tmp_path / "bad_direct_return.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["emit-c", str(f)])
    assert res1.returncode != 0
    assert "cannot return pointer allocated inside lexical zone" in (res1.stderr + res1.stdout)

    res2 = _run_stage2(["emit-c", str(f)])
    assert res2.returncode != 0
    assert "cannot return pointer allocated inside lexical zone" in (res2.stderr + res2.stdout)

def test_zone_pointer_assign_to_outer_rejected(tmp_path):
    code = """
use sys.mem

act bad_assign() {
    mut outer: @i32 = null
    zone {
        let inner: @i32 = mem.alloc(@i32, 1)
        outer = inner
    }
}
act main() {}
"""
    f = tmp_path / "bad_assign.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["emit-c", str(f)])
    assert res1.returncode != 0
    assert "zone-allocated pointer escapes into outer variable 'outer'" in (res1.stderr + res1.stdout)

    res2 = _run_stage2(["emit-c", str(f)])
    assert res2.returncode != 0
    assert "zone-allocated pointer escapes into outer variable 'outer'" in (res2.stderr + res2.stdout)

def test_zone_pointer_direct_alloc_to_outer_rejected(tmp_path):
    code = """
use sys.mem

act bad_direct_assign() {
    mut outer: @i32 = null
    zone {
        outer = mem.alloc(@i32, 1)
    }
}
act main() {}
"""
    f = tmp_path / "bad_direct_assign.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["emit-c", str(f)])
    assert res1.returncode != 0
    assert "zone-allocated pointer escapes into outer variable 'outer'" in (res1.stderr + res1.stdout)

    res2 = _run_stage2(["emit-c", str(f)])
    assert res2.returncode != 0
    assert "zone-allocated pointer escapes into outer variable 'outer'" in (res2.stderr + res2.stdout)

def test_zone_nested_escape_rejected(tmp_path):
    code = """
use sys.mem

act bad_nested() {
    zone {
        mut mid: @i32 = null
        zone {
            let inner: @i32 = mem.alloc(@i32, 1)
            mid = inner
        }
    }
}
act main() {}
"""
    f = tmp_path / "bad_nested.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["emit-c", str(f)])
    assert res1.returncode != 0
    assert "zone-allocated pointer escapes into outer variable 'mid'" in (res1.stderr + res1.stdout)

    res2 = _run_stage2(["emit-c", str(f)])
    assert res2.returncode != 0
    assert "zone-allocated pointer escapes into outer variable 'mid'" in (res2.stderr + res2.stdout)

def test_local_variable_address_return_rejected(tmp_path):
    code = """
act bad_return_local() -> @i32 {
    mut x: i32 = 100
    return @x
}
act main() {}
"""
    f = tmp_path / "bad_return_local.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["emit-c", str(f)])
    assert res1.returncode != 0
    assert "cannot return address of local variable 'x'" in (res1.stderr + res1.stdout)

    res2 = _run_stage2(["emit-c", str(f)])
    assert res2.returncode != 0
    assert "cannot return address of local variable 'x'" in (res2.stderr + res2.stdout)

def test_local_variable_address_assign_to_outer_rejected(tmp_path):
    code = """
act bad_assign_local() {
    mut p: @i32 = null
    zone {
        mut x: i32 = 100
        p = @x
    }
}
act main() {}
"""
    f = tmp_path / "bad_assign_local.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["emit-c", str(f)])
    assert res1.returncode != 0
    assert "cannot assign address of local variable 'x' to outer variable 'p'" in (res1.stderr + res1.stdout)

    res2 = _run_stage2(["emit-c", str(f)])
    assert res2.returncode != 0
    assert "cannot assign address of local variable 'x' to outer variable 'p'" in (res2.stderr + res2.stdout)

def test_valid_zone_operations_accepted(tmp_path):
    code = """
use sys.mem
use sys.io

act get_primitive_val() -> i32 {
    zone {
        let p: @i32 = mem.alloc(@i32, 1)
        p[0] = 42
        return p[0]
    }
}

act get_null_ptr() -> @i32 {
    zone {
        return null
    }
}

act pass_through(p: @i32) -> @i32 {
    zone {
        return p
    }
}

act same_zone() {
    zone {
        mut a: @i32 = null
        let b: @i32 = mem.alloc(@i32, 1)
        a = b
    }
}

act heap_escape() -> @i32 {
    zone {
        let h: @i32 = mem.heap_alloc(@i32, 1)
        h[0] = 999
        return h
    }
}

act main() {
    let v = get_primitive_val()
    io.println("val: {v}")

    let n = get_null_ptr()
    let pt = pass_through(n)

    same_zone()

    let h = heap_escape()
    io.println("heap: {h[0]}")
    mem.free(h as @u8)
}
"""
    f = tmp_path / "valid_zone.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["run", str(f)])
    assert res1.returncode == 0, f"Stage 1 failed: {res1.stderr}"
    assert "val: 42" in res1.stdout
    assert "heap: 999" in res1.stdout

    res2 = _run_stage2(["run", str(f)])
    assert res2.returncode == 0, f"Stage 2 failed: {res2.stderr + res2.stdout}"
    assert "val: 42" in res2.stdout
    assert "heap: 999" in res2.stdout
