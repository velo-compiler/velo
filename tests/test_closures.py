"""
Phase 77 / Task 77.2: Closures, Anonymous Functions & Fat-Arrow Syntax.

Tests the syntax chosen in Task 77.2:
- Single-expression fat-arrow form: `act(params...) => expr`
- Fat-arrow with explicit return type: `act(params...) -> Ret => expr`
- Full block anonymous function: `act(params...) [-> Ret] { body }`
- Named fat-arrow functions: `act name(params...) [-> Ret] => expr`
- Higher-order function callbacks
- Clean async callback signatures (no `user_data: @void`)
"""

import subprocess
import pytest
from conftest import velo_exe, REPO_ROOT

pytestmark = pytest.mark.fast

VELO_EXE = velo_exe()


def run_velo_source(tmp_path, code: str):
    src_file = tmp_path / "test_prog.vl"
    src_file.write_text(code, encoding="utf-8")
    res = subprocess.run(
        [str(VELO_EXE), "run", str(src_file)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return res


def test_fat_arrow_inferred_ret(tmp_path):
    code = """
use std.io

act main() -> i32 {
    let doubler = act(x: i32) => x * 2
    let res = doubler(21)
    if res != 42 { return 1 }
    io.println_str("OK")
    return 0
}
"""
    res = run_velo_source(tmp_path, code)
    assert res.returncode == 0, f"Error: {res.stderr}\n{res.stdout}"
    assert "OK" in res.stdout


def test_fat_arrow_explicit_ret(tmp_path):
    code = """
use std.io

act main() -> i32 {
    let add_hundred = act(x: i32) -> i32 => x + 100
    let res = add_hundred(42)
    if res != 142 { return 1 }
    io.println_str("OK")
    return 0
}
"""
    res = run_velo_source(tmp_path, code)
    assert res.returncode == 0, f"Error: {res.stderr}\n{res.stdout}"
    assert "OK" in res.stdout


def test_fat_arrow_multi_arg(tmp_path):
    code = """
use std.io

act main() -> i32 {
    let adder = act(a: i32, b: i32) => a + b
    let res = adder(20, 22)
    if res != 42 { return 1 }
    io.println_str("OK")
    return 0
}
"""
    res = run_velo_source(tmp_path, code)
    assert res.returncode == 0, f"Error: {res.stderr}\n{res.stdout}"
    assert "OK" in res.stdout


def test_block_form_anonymous_act(tmp_path):
    code = """
use std.io

act main() -> i32 {
    let calc = act(x: i32) -> i32 {
        mut y = x * 2
        y = y + 10
        return y
    }
    let res = calc(16)
    if res != 42 { return 1 }
    io.println_str("OK")
    return 0
}
"""
    res = run_velo_source(tmp_path, code)
    assert res.returncode == 0, f"Error: {res.stderr}\n{res.stdout}"
    assert "OK" in res.stdout


def test_higher_order_function_callback(tmp_path):
    code = """
use std.io

act apply_fn(val: i32, f: act(i32) -> i32) -> i32 {
    return f(val)
}

act main() -> i32 {
    let res = apply_fn(6, act(n: i32) => n * 7)
    if res != 42 { return 1 }
    io.println_str("OK")
    return 0
}
"""
    res = run_velo_source(tmp_path, code)
    assert res.returncode == 0, f"Error: {res.stderr}\n{res.stdout}"
    assert "OK" in res.stdout


def test_named_fat_arrow_function(tmp_path):
    code = """
use std.io

act square(x: i32) => x * x
act cube(x: i32) -> i32 => x * x * x

act main() -> i32 {
    let s = square(5)
    let c = cube(3)
    if s != 25 or c != 27 { return 1 }
    io.println_str("OK")
    return 0
}
"""
    res = run_velo_source(tmp_path, code)
    assert res.returncode == 0, f"Error: {res.stderr}\n{res.stdout}"
    assert "OK" in res.stdout


def test_void_fat_arrow_action(tmp_path):
    code = """
use std.io

act main() -> i32 {
    let log_msg = act(msg: string) => io.println_str(msg)
    log_msg("OK: void fat-arrow")
    return 0
}
"""
    res = run_velo_source(tmp_path, code)
    assert res.returncode == 0, f"Error: {res.stderr}\n{res.stdout}"
    assert "OK: void fat-arrow" in res.stdout


def test_examples_39_closures():
    example_path = REPO_ROOT / "examples" / "39_closures.vl"
    assert example_path.exists()
    res = subprocess.run(
        [str(VELO_EXE), "run", str(example_path)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    assert res.returncode == 0, f"Error running 39_closures.vl:\n{res.stderr}\n{res.stdout}"
    assert "OK: Closures and anonymous acts executed successfully" in res.stdout
