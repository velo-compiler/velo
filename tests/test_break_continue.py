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


def get_build_env():
    """Returns an environment with ucrt64 GCC in PATH for compiling generated C."""
    env = dict(os.environ)
    ucrt_bin = r"C:\msys64\ucrt64\bin"
    if os.path.exists(ucrt_bin):
        env["PATH"] = ucrt_bin + ";" + env.get("PATH", "")
    return env


def get_gcc_bin():
    if os.name == "nt":
        ucrt_gcc = r"C:\msys64\ucrt64\bin\gcc.exe"
        if os.path.exists(ucrt_gcc):
            return ucrt_gcc
        return "gcc.exe"
    return os.environ.get("CC", "gcc")


def compile_and_run_werror(source_code: str, timeout: float = 2.0) -> subprocess.CompletedProcess:
    gcc_bin = get_gcc_bin()
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_path = Path(tmp_dir) / "test.vl"
        c_path = Path(tmp_dir) / "test.c"
        exe_path = Path(tmp_dir) / ("test.exe" if os.name == "nt" else "test")
        src_path.write_text(source_code, encoding="utf-8")

        emit_res = subprocess.run(
            [str(VELO_EXE), "emit-c", str(src_path), "-o", str(c_path)],
            capture_output=True,
            text=True,
            env=get_build_env(),
            timeout=timeout,
        )
        assert emit_res.returncode == 0, f"emit-c failed: {emit_res.stderr}\n{emit_res.stdout}"

        gcc_cmd = [
            gcc_bin,
            "-std=c99",
            "-Wall",
            "-Werror",
            "-Wno-unknown-pragmas",
            "-Wno-unused-parameter",
            "-I", str(ROOT_DIR / "runtime"),
            "-I", str(ROOT_DIR / "velo" / "runtime"),
            str(c_path),
            "-o", str(exe_path),
        ]
        gcc_res = subprocess.run(
            gcc_cmd,
            capture_output=True,
            text=True,
            env=get_build_env(),
            timeout=timeout,
        )
        assert gcc_res.returncode == 0, f"gcc -Werror failed: {gcc_res.stderr}\n{gcc_res.stdout}"
        return subprocess.run([str(exe_path)], capture_output=True, text=True, timeout=timeout)


def build_and_run(source_code: str, timeout: float = 2.0) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile("w", suffix=".vl", delete=False) as f:
        f.write(source_code)
        f_name = f.name
    try:
        return subprocess.run([str(VELO_EXE), "run", f_name], capture_output=True, text=True, timeout=timeout, env=get_build_env())
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


class TestOnControlFlowWarningsAndSecurityGate:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")
        gcc_bin = get_gcc_bin()
        try:
            check_gcc = subprocess.run([gcc_bin, "--version"], capture_output=True, env=get_build_env())
            if check_gcc.returncode != 0:
                pytest.skip("C compiler not available")
        except Exception:
            pytest.skip("C compiler not available")

    def test_werror_break_inside_on(self):
        """Compiling `break` inside `on` under -Wall -Werror produces zero compiler warnings."""
        code = """
        use sys.io
        act main() -> i32 {
            mut iters = 0
            loop i in 0..10 {
                on i {
                    3 => { break }
                    else => { }
                }
                iters += 1
            }
            io.println("iters={iters}")
            return 0
        }
        """
        res = compile_and_run_werror(code, timeout=2.0)
        assert res.returncode == 0
        assert "iters=3" in res.stdout

    def test_werror_continue_inside_on(self):
        """Compiling `continue` inside `on` under -Wall -Werror produces zero compiler warnings."""
        code = """
        use sys.io
        act main() -> i32 {
            mut sum = 0
            loop i in 0..5 {
                on i {
                    2 => { continue }
                    else => { }
                }
                sum += i
            }
            io.println("sum={sum}")
            return 0
        }
        """
        res = compile_and_run_werror(code, timeout=2.0)
        assert res.returncode == 0
        assert "sum=8" in res.stdout

    def test_werror_loop_without_break_or_continue(self):
        """Unused loop labels with __attribute__((unused)) emit zero -Wunused-label warnings under -Wall -Werror."""
        code = """
        use sys.io
        act main() -> i32 {
            mut count = 0
            loop i in 0..10 {
                count += 1
            }
            io.println("count={count}")
            return 0
        }
        """
        res = compile_and_run_werror(code, timeout=2.0)
        assert res.returncode == 0
        assert "count=10" in res.stdout

    def test_werror_nested_on_and_defers(self):
        """Multi-level nested on with loop defers compiles cleanly with -Wall -Werror and zero leaks."""
        code = """
        use sys.io
        use sys.mem

        act main() -> i32 {
            let base = mem.heap_used()
            mut iters = 0
            loop i in 0..5 {
                let buf = mem.alloc(@u8, 512)
                defer mem.free(buf)
                on i {
                    2 => {
                        let sub = 10
                        on sub {
                            10 => { break }
                            else => { }
                        }
                    }
                    else => { }
                }
                iters += 1
            }
            let diff = mem.heap_used() - base
            io.println("iters={iters}, diff={diff}")
            return 0
        }
        """
        res = compile_and_run_werror(code, timeout=2.0)
        assert res.returncode == 0
        assert "iters=2, diff=0" in res.stdout



