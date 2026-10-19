import subprocess
import sys
from pathlib import Path

def test_while_break_and_continue(tmp_path):
    source = tmp_path / "test_while.vl"
    source.write_text("""
use sys.io
act main() -> i32 {
    mut count = 0
    while true {
        count += 1
        if count == 7 {
            break
        }
    }
    mut odds = 0
    mut i = 0
    while i < 10 {
        i += 1
        if i % 2 == 0 {
            continue
        }
        odds += i
    }
    io.println("count={count}, odds={odds}")
    return 0
}
""", encoding="utf-8")

    # Python stage 1
    res_py = subprocess.run([sys.executable, "velo.py", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    assert "count=7, odds=25" in res_py.stdout

    # Self-hosted stage 2
    res_sh = subprocess.run(["bin/velo.exe", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "count=7, odds=25" in res_sh.stdout

def test_range_loop_break_and_continue(tmp_path):
    source = tmp_path / "test_loop.vl"
    source.write_text("""
use sys.io
act main() -> i32 {
    mut b = -1
    loop i in 0..100 {
        if i == 42 {
            b = i
            break
        }
    }
    mut sum = 0
    loop i in 0..10 {
        if i == 5 {
            continue
        }
        sum += i
    }
    io.println("b={b}, sum={sum}")
    return 0
}
""", encoding="utf-8")

    # Python stage 1
    res_py = subprocess.run([sys.executable, "velo.py", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    assert "b=42, sum=40" in res_py.stdout

    # Self-hosted stage 2
    res_sh = subprocess.run(["bin/velo.exe", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "b=42, sum=40" in res_sh.stdout

def test_nested_loops_break(tmp_path):
    source = tmp_path / "test_nested.vl"
    source.write_text("""
use sys.io
act main() -> i32 {
    mut total = 0
    loop r in 0..4 {
        loop c in 0..10 {
            if c == 3 {
                break
            }
            total += 1
        }
    }
    io.println("total={total}")
    return 0
}
""", encoding="utf-8")

    # Python stage 1
    res_py = subprocess.run([sys.executable, "velo.py", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    assert "total=12" in res_py.stdout

    # Self-hosted stage 2
    res_sh = subprocess.run(["bin/velo.exe", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "total=12" in res_sh.stdout

def test_example_18_e2e():
    example_path = "examples/18_break_continue.vl"

    res_py = subprocess.run([sys.executable, "velo.py", "run", example_path], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    assert "[SUCCESS] Milestone 2.1: Loop Controls (break & continue) Verified!" in res_py.stdout

    res_sh = subprocess.run(["bin/velo.exe", "run", example_path], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "[SUCCESS] Milestone 2.1: Loop Controls (break & continue) Verified!" in res_sh.stdout
