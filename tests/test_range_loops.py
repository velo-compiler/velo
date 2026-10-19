import subprocess
import sys
from pathlib import Path

def test_infinite_loop(tmp_path):
    source = tmp_path / "test_inf.vl"
    source.write_text("""
use sys.io

act main() -> i32 {
    mut count: i32 = 0
    loop {
        count += 1
        if it == 4 {
            break
        }
    }
    io.println("count={count}")
    return 0
}
""", encoding="utf-8")

    res_py = subprocess.run([sys.executable, "velo.py", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    assert "count=5" in res_py.stdout

    res_sh = subprocess.run(["bin/velo.exe", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "count=5" in res_sh.stdout


def test_count_loop(tmp_path):
    source = tmp_path / "test_count.vl"
    source.write_text("""
use sys.io

act main() -> i32 {
    mut sum: i32 = 0
    loop 5 {
        sum += it as i32
    }
    io.println("sum={sum}")
    return 0
}
""", encoding="utf-8")

    res_py = subprocess.run([sys.executable, "velo.py", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    assert "sum=10" in res_py.stdout

    res_sh = subprocess.run(["bin/velo.exe", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "sum=10" in res_sh.stdout


def test_condition_loop(tmp_path):
    source = tmp_path / "test_cond.vl"
    source.write_text("""
use sys.io

act main() -> i32 {
    mut n: i32 = 10
    mut it_sum: i32 = 0
    loop n > 5 {
        it_sum += it as i32
        n -= 1
    }
    io.println("n={n}, it_sum={it_sum}")
    return 0
}
""", encoding="utf-8")

    res_py = subprocess.run([sys.executable, "velo.py", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    assert "n=5, it_sum=10" in res_py.stdout

    res_sh = subprocess.run(["bin/velo.exe", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "n=5, it_sum=10" in res_sh.stdout


def test_range_step_and_reverse(tmp_path):
    source = tmp_path / "test_step_rev.vl"
    source.write_text("""
use sys.io

act main() -> i32 {
    mut fwd_step: i32 = 0
    loop i in 0..10:2 {
        fwd_step += i
    }

    mut rev_auto: i32 = 0
    loop 5..0 {
        rev_auto += it as i32
    }

    mut rev_step: i32 = 0
    loop 10..0:2 {
        rev_step += it as i32
    }

    io.println("fwd_step={fwd_step}, rev_auto={rev_auto}, rev_step={rev_step}")
    return 0
}
""", encoding="utf-8")

    # fwd_step: 0+2+4+6+8 = 20
    # rev_auto: 5+4+3+2+1 = 15
    # rev_step: 10+8+6+4+2 = 30
    res_py = subprocess.run([sys.executable, "velo.py", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    assert "fwd_step=20, rev_auto=15, rev_step=30" in res_py.stdout

    res_sh = subprocess.run(["bin/velo.exe", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "fwd_step=20, rev_auto=15, rev_step=30" in res_sh.stdout


def test_inclusive_ranges(tmp_path):
    source = tmp_path / "test_inc.vl"
    source.write_text("""
use sys.io

act main() -> i32 {
    mut inc_sum: i32 = 0
    loop i in 1..=5 {
        inc_sum += i
    }

    mut inc_step: i32 = 0
    loop i in 0..=10:2 {
        inc_step += i
    }

    mut inc_rev: i32 = 0
    loop i in 5..=1 {
        inc_rev += i
    }

    io.println("inc_sum={inc_sum}, inc_step={inc_step}, inc_rev={inc_rev}")
    return 0
}
""", encoding="utf-8")

    # inc_sum: 1+2+3+4+5 = 15
    # inc_step: 0+2+4+6+8+10 = 30
    # inc_rev: 5+4+3+2+1 = 15
    res_py = subprocess.run([sys.executable, "velo.py", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    assert "inc_sum=15, inc_step=30, inc_rev=15" in res_py.stdout

    res_sh = subprocess.run(["bin/velo.exe", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "inc_sum=15, inc_step=30, inc_rev=15" in res_sh.stdout
