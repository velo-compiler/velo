import os
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest

def test_while_break_and_continue(tmp_path):
    source = tmp_path / "test_while.vl"
    source.write_text("""
use sys.io
act main() -> i32 {
    mut count = 0
    loop {
        count += 1
        if count == 7 {
            break
        }
    }
    mut odds = 0
    mut i = 0
    loop i < 10 {
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


# ==============================================================================
# Phase 61: `break` Inside `on` & Loop Interaction / Defer Cleanup (Task 61.1)
# ==============================================================================

ROOT_DIR = Path(__file__).parent.parent.resolve()
VELO_EXE = ROOT_DIR / "bin" / ("velo.exe" if os.name == "nt" else "velo")
if not VELO_EXE.exists() and (ROOT_DIR / "bin" / "velo.exe").exists():
    VELO_EXE = ROOT_DIR / "bin" / "velo.exe"


def build_and_run(source_code: str, timeout: float = 2.0) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile("w", suffix=".vl", delete=False) as f:
        f.write(source_code)
        f_name = f.name
    try:
        return subprocess.run([str(VELO_EXE), "run", f_name], capture_output=True, text=True, timeout=timeout)
    finally:
        Path(f_name).unlink(missing_ok=True)


class TestOnBreakLoopInteraction:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_on_break_defer_cleanup_in_loop(self):
        """Loop-scoped defer cleanups must run exactly once per executed iteration, not duplicate on break."""
        code = """
        use sys.io
        act main() -> i32 {
            mut cleaned = 0
            loop i in 0..5 {
                defer cleaned += 1
                on i {
                    2 => { break }
                    else => { }
                }
            }
            io.println("cleaned={cleaned}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "cleaned=3" in res.stdout

    def test_on_continue_defer_cleanup_in_loop(self):
        """Loop-scoped defer cleanups must run on continue inside `on`."""
        code = """
        use sys.io
        act main() -> i32 {
            mut cleaned = 0
            mut sum = 0
            loop i in 0..5 {
                defer cleaned += 1
                on i {
                    2 => { continue }
                    else => { }
                }
                sum += i
            }
            io.println("cleaned={cleaned}, sum={sum}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "cleaned=5, sum=8" in res.stdout

    def test_on_break_in_while_loop(self):
        """A `break` inside `on` inside a condition while-loop exits the while-loop."""
        code = """
        use sys.io
        act main() -> i32 {
            mut i = 0
            mut count = 0
            loop i < 10 {
                on i {
                    3 => { break }
                    else => { }
                }
                count += 1
                i += 1
            }
            io.println("count={count}, i={i}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "count=3, i=3" in res.stdout

    def test_on_break_in_nested_loops_exits_inner_only(self):
        """A `break` inside `on` inside an inner loop must only exit the inner loop, continuing outer loop."""
        code = """
        use sys.io
        act main() -> i32 {
            mut inner_count = 0
            loop r in 0..3 {
                loop c in 0..5 {
                    on c {
                        2 => { break }
                        else => { }
                    }
                    inner_count += 1
                }
            }
            io.println("inner_count={inner_count}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "inner_count=6" in res.stdout

    def test_on_break_memory_heap_cleanup(self):
        """Loop-scoped heap allocations must be cleaned up without double-free or leak on break inside `on`."""
        code = """
        use sys.io
        use sys.mem

        act main() -> i32 {
            let base = mem.heap_used()
            mut break_hit = 0
            mut iters = 0
            loop i in 0..5 {
                let buf = mem.alloc(@u8, 1024)
                defer mem.free(buf)
                on i {
                    2 => {
                        break_hit = 1
                        break
                    }
                    else => { }
                }
                iters += 1
            }
            let diff = mem.heap_used() - base
            io.println("iters={iters}, break_hit={break_hit}, diff={diff}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "iters=2, break_hit=1, diff=0" in res.stdout

    def test_on_break_case_and_loop_defer_lifo_order(self):
        """Case-scoped defer must run before loop-scoped defer in strict LIFO order on break."""
        code = """
        use sys.io
        act main() -> i32 {
            mut val = 0
            loop i in 0..5 {
                defer val = val * 10 + 1
                on i {
                    2 => {
                        defer val = val * 10 + 2
                        break
                    }
                    else => { }
                }
            }
            io.println("val={val}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "val=1121" in res.stdout

    def test_on_continue_case_and_loop_defer_lifo_order(self):
        """Case-scoped defer must run before loop-scoped defer in strict LIFO order on continue."""
        code = """
        use sys.io
        act main() -> i32 {
            mut val = 0
            loop i in 0..2 {
                defer val = val * 10 + 1
                on i {
                    0 => {
                        defer val = val * 10 + 2
                        continue
                    }
                    else => { }
                }
            }
            io.println("val={val}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "val=211" in res.stdout

    def test_on_break_inner_zone_cleaned_up(self):
        """Inner zone allocations inside a loop must pop and leave cleanly on break inside on."""
        code = """
        use sys.io
        use sys.mem

        act main() -> i32 {
            let base = mem.heap_used()
            mut iters = 0
            loop i in 0..5 {
                zone {
                    let buf = mem.alloc(@u8, 1024)
                    on i {
                        2 => { break }
                        else => { }
                    }
                    iters += 1
                }
            }
            let diff = mem.heap_used() - base
            io.println("iters={iters}, diff={diff}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "iters=2, diff=0" in res.stdout

    def test_on_break_outer_zone_preserved(self):
        """Outer zone enclosing a loop must remain intact when break inside on exits the loop."""
        code = """
        use sys.io
        use sys.mem

        act main() -> i32 {
            let base = mem.heap_used()
            mut iters = 0
            zone {
                let outer_buf = mem.alloc(@u8, 2048)
                loop i in 0..5 {
                    let inner_buf = mem.alloc(@u8, 512)
                    defer mem.free(inner_buf)
                    on i {
                        2 => { break }
                        else => { }
                    }
                    iters += 1
                }
                mem.free(outer_buf)
            }
            let diff = mem.heap_used() - base
            io.println("iters={iters}, diff={diff}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "iters=2, diff=0" in res.stdout

    def test_on_continue_heap_allocation_cleaned_up(self):
        """Loop-scoped heap allocations must be cleaned up on continue inside on without leaking."""
        code = """
        use sys.io
        use sys.mem

        act main() -> i32 {
            let base = mem.heap_used()
            mut sum = 0
            loop i in 0..5 {
                let buf = mem.alloc(@u8, 1024)
                defer mem.free(buf)
                on i {
                    2 => { continue }
                    else => { }
                }
                sum += i
            }
            let diff = mem.heap_used() - base
            io.println("sum={sum}, diff={diff}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "sum=8, diff=0" in res.stdout


