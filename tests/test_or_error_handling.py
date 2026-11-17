import subprocess
import pytest
from pathlib import Path
from conftest import velo_exe

def _run_stage1(cmd: list) -> subprocess.CompletedProcess:
    full_cmd = ["python", "velo.py"] + cmd
    return subprocess.run(full_cmd, capture_output=True, text=True)

def _run_stage2(cmd: list) -> subprocess.CompletedProcess:
    velo_bin = Path(str(velo_exe())).resolve()
    if not velo_bin.exists():
        pytest.skip("bin/velo.exe not built yet")
    full_cmd = [str(velo_bin)] + cmd
    return subprocess.run(full_cmd, capture_output=True, text=True)

def test_or_success_and_fail_return(tmp_path):
    code = """
use std.io

act parse_port(s: string) -> i32 or string {
    if s == "8080" {
        return 8080
    }
    fail "invalid port"
}

act main() {
    let r1 = parse_port("8080")
    if r1.ok {
        io.println("r1 ok: {r1.val}")
    } else {
        io.println("r1 err: {r1.err}")
    }

    let r2 = parse_port("bad")
    if r2.ok {
        io.println("r2 ok: {r2.val}")
    } else {
        io.println("r2 err: {r2.err}")
    }
}
"""
    f = tmp_path / "test_basic_or.vl"
    f.write_text(code, encoding="utf-8")

    # Stage 1
    res1 = _run_stage1(["run", str(f)])
    assert res1.returncode == 0, f"Stage 1 failed: {res1.stderr}"
    assert "r1 ok: 8080" in res1.stdout
    assert "r2 err: invalid port" in res1.stdout

    # Stage 2
    res2 = _run_stage2(["run", str(f)])
    assert res2.returncode == 0, f"Stage 2 failed: {res2.stderr}"
    assert "r1 ok: 8080" in res2.stdout
    assert "r2 err: invalid port" in res2.stdout

def test_or_fallback_expression(tmp_path):
    code = """
use std.io

act parse_port(s: string) -> i32 or string {
    if s == "8080" {
        return 8080
    }
    fail "invalid port"
}

act main() {
    let p1 = parse_port("8080") or 3000
    let p2 = parse_port("unknown") or 3000
    io.println("p1: {p1}, p2: {p2}")
}
"""
    f = tmp_path / "test_fallback.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["run", str(f)])
    assert res1.returncode == 0, f"Stage 1 failed: {res1.stderr}"
    assert "p1: 8080, p2: 3000" in res1.stdout

    res2 = _run_stage2(["run", str(f)])
    assert res2.returncode == 0, f"Stage 2 failed: {res2.stderr}"
    assert "p1: 8080, p2: 3000" in res2.stdout

def test_or_return_propagation(tmp_path):
    code = """
use std.io

act parse_port(s: string) -> i32 or string {
    if s == "9090" {
        return 9090
    }
    fail "not a number"
}

act start_server(s: string) -> string or string {
    let port = parse_port(s) or return
    return "running on port"
}

act main() {
    let ok_res = start_server("9090")
    if ok_res.ok {
        io.println("server: {ok_res.val}")
    }

    let err_res = start_server("invalid")
    if not err_res.ok {
        io.println("failed: {err_res.err}")
    }
}
"""
    f = tmp_path / "test_propagation.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["run", str(f)])
    assert res1.returncode == 0, f"Stage 1 failed: {res1.stderr}"
    assert "server: running on port" in res1.stdout
    assert "failed: not a number" in res1.stdout

    res2 = _run_stage2(["run", str(f)])
    assert res2.returncode == 0, f"Stage 2 failed: {res2.stderr}"
    assert "server: running on port" in res2.stdout
    assert "failed: not a number" in res2.stdout

def test_or_return_with_defer(tmp_path):
    code = """
use std.io

act step() -> i32 or string {
    fail "oops"
}

act run_task() -> i32 or string {
    defer io.println("defer executed")
    let x = step() or return
    return x
}

act main() {
    let r = run_task()
    if not r.ok {
        io.println("handled: {r.err}")
    }
}
"""
    f = tmp_path / "test_defer.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["run", str(f)])
    assert res1.returncode == 0, f"Stage 1 failed: {res1.stderr}"
    assert "defer executed\nhandled: oops" in res1.stdout.replace("\r\n", "\n")

    res2 = _run_stage2(["run", str(f)])
    assert res2.returncode == 0, f"Stage 2 failed: {res2.stderr}"
    assert "defer executed\nhandled: oops" in res2.stdout.replace("\r\n", "\n")

def test_fail_outside_or_function_rejected(tmp_path):
    code = """
act normal_func() -> i32 {
    fail "cannot fail"
    return 0
}
act main() {}
"""
    f = tmp_path / "test_reject.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["emit-c", str(f)])
    assert res1.returncode != 0
    assert "'fail' can only be used in a function returning an 'or' type" in res1.stderr

    res2 = _run_stage2(["emit-c", str(f)])
    assert res2.returncode != 0

def test_or_return_outside_or_function_rejected(tmp_path):
    code = """
act parse() -> i32 or string {
    fail "err"
}

act normal_func() -> i32 {
    let x = parse() or return
    return x
}
act main() {}
"""
    f = tmp_path / "test_reject2.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["emit-c", str(f)])
    assert res1.returncode != 0
    assert "'or return' can only be used in a function returning an 'or' type" in res1.stderr

    res2 = _run_stage2(["emit-c", str(f)])
    assert res2.returncode != 0
