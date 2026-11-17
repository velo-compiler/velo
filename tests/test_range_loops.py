import os
import subprocess
import sys
from pathlib import Path
import pytest
from conftest import cc_dir, velo_exe

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

    res_sh = subprocess.run([str(velo_exe()), "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
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

    res_sh = subprocess.run([str(velo_exe()), "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
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

    res_sh = subprocess.run([str(velo_exe()), "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
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

    res_sh = subprocess.run([str(velo_exe()), "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
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

    res_sh = subprocess.run([str(velo_exe()), "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "inc_sum=15, inc_step=30, inc_rev=15" in res_sh.stdout


def test_count_loop_variable_and_expression(tmp_path):
    """Phase 54: Verifies loop with an expression like n + 1 iterates (n + 1) times."""
    source = tmp_path / "test_count_expr.vl"
    source.write_text("""
use sys.io

act main() -> i32 {
    let n: i32 = 3
    mut sum: i32 = 0
    loop n + 1 {
        sum += 1
    }
    io.println("sum={sum}")
    return 0
}
""", encoding="utf-8")

    exe = tmp_path / "test_count_expr.exe"
    env = dict(os.environ)
    env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    build_res = subprocess.run([str(velo_exe()), "build", str(source), "-o", str(exe)], env=env, capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert build_res.returncode == 0
    try:
        res_sh = subprocess.run([str(exe)], capture_output=True, text=True, encoding="utf-8", timeout=1.0)
        assert res_sh.returncode == 0
        assert "sum=4" in res_sh.stdout
    except subprocess.TimeoutExpired as e:
        pytest.fail(f"Loop timed out (infinite loop detected): {e}")


def test_large_endpoint_range_loop_baseline(tmp_path):
    """Phase 55: Baseline check for large endpoint ranges around 3 billion and wide endpoints."""
    source = tmp_path / "test_large_range.vl"
    source.write_text("""
use sys.io

act main() -> i32 {
    mut asc_iters: i32 = 0
    loop i in 0..3000000000 {
        asc_iters += 1
        if asc_iters == 3 {
            break
        }
    }

    mut desc_iters: i32 = 0
    loop i in 3000000000..0 {
        desc_iters += 1
        if desc_iters == 3 {
            break
        }
    }

    io.println("asc={asc_iters}, desc={desc_iters}")
    return 0
}
""", encoding="utf-8")

    exe = tmp_path / "test_large_range.exe"
    env = dict(os.environ)
    env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    build_res = subprocess.run([str(velo_exe()), "build", str(source), "-o", str(exe)], env=env, capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert build_res.returncode == 0
    try:
        res_sh = subprocess.run([str(exe)], capture_output=True, text=True, encoding="utf-8", timeout=2.0)
        assert res_sh.returncode == 0
        assert "asc=3, desc=3" in res_sh.stdout
    except subprocess.TimeoutExpired as e:
        pytest.fail(f"Loop timed out: {e}")




def test_dynamic_range_loop_baseline(tmp_path):
    """Phase 56: Baseline check for dynamic range loops with variable endpoints."""
    source = tmp_path / "test_dyn_range.vl"
    source.write_text("""
use sys.io

act main() -> i32 {
    let n: i32 = 5
    mut asc_iters: i32 = 0
    loop i in 0..n {
        asc_iters += 1
    }

    mut desc_iters: i32 = 0
    loop i in n..0 {
        desc_iters += 1
    }

    io.println("asc={asc_iters}, desc={desc_iters}")
    return 0
}
""", encoding="utf-8")

    exe = tmp_path / "test_dyn_range.exe"
    env = dict(os.environ)
    env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    build_res = subprocess.run([str(velo_exe()), "build", str(source), "-o", str(exe)], env=env, capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert build_res.returncode == 0
    try:
        res_sh = subprocess.run([str(exe)], capture_output=True, text=True, encoding="utf-8", timeout=2.0)
        assert res_sh.returncode == 0
        assert "asc=5" in res_sh.stdout
        # Phase 56 Task 56.4: descending dynamic range n..0 now executes 5 iterations
        assert "desc=5" in res_sh.stdout
    except subprocess.TimeoutExpired as e:
        pytest.fail(f"Loop timed out: {e}")


def test_range_step_zero_rejected(tmp_path):
    """Phase 63: Literal zero step (:0) must be rejected at compile time."""
    source = tmp_path / "test_step_zero.vl"
    source.write_text("""
act main() -> i32 {
    loop i in 0..10:0 {
    }
    return 0
}
""", encoding="utf-8")

    res = subprocess.run([str(velo_exe()), "check", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res.returncode != 0
    assert "Range loop step must be greater than zero" in res.stdout


def test_range_step_dynamic_zero_baseline(tmp_path):
    """Phase 63: Dynamic zero step must fail fast at runtime, not hang in an infinite loop (red baseline)."""
    source = tmp_path / "test_dyn_zero_step.vl"
    source.write_text("""
use sys.io

act main() -> i32 {
    let s: i32 = 0
    loop i in 0..10:s {
        io.println(i)
    }
    return 0
}
""", encoding="utf-8")

    exe = tmp_path / "test_dyn_zero_step.exe"
    env = dict(os.environ)
    env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    build_res = subprocess.run([str(velo_exe()), "build", str(source), "-o", str(exe)], env=env, capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert build_res.returncode == 0
    try:
        res_sh = subprocess.run([str(exe)], capture_output=True, text=True, encoding="utf-8", timeout=1.0)
        assert res_sh.returncode != 0, f"Expected dynamic zero step to fail with error, but exited {res_sh.returncode}"
        assert "Range loop step must be greater than zero" in res_sh.stderr
        assert "0" not in res_sh.stdout, "Expected no partial iterations before step check"
    except subprocess.TimeoutExpired as e:
        pytest.fail(f"Loop timed out (infinite loop detected on dynamic zero step): {e}")

