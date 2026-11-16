import os
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest

def test_on_multi_value_and_else(tmp_path):
    source = tmp_path / "test_on_multi.vl"
    source.write_text("""
use sys.io

act classify(val: i32) -> string {
    on val {
        1 => {
            return "one"
        }
        2, 3 => {
            return "two_or_three"
        }
        4, 5, 6 => {
            return "four_to_six"
        }
        else => {
            return "other"
        }
    }
}

act main() -> i32 {
    let r1 = classify(1)
    let r2 = classify(2)
    let r3 = classify(3)
    let r5 = classify(5)
    let r9 = classify(9)
    io.println("r1={r1}, r2={r2}, r3={r3}, r5={r5}, r9={r9}")
    return 0
}
""", encoding="utf-8")

    # Python stage 1
    res_py = subprocess.run([sys.executable, "velo.py", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    assert "r1=one, r2=two_or_three, r3=two_or_three, r5=four_to_six, r9=other" in res_py.stdout

    # Self-hosted stage 2
    res_sh = subprocess.run(["bin/velo.exe", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "r1=one, r2=two_or_three, r3=two_or_three, r5=four_to_six, r9=other" in res_sh.stdout


def test_on_compact_arms(tmp_path):
    source = tmp_path / "test_on_compact.vl"
    source.write_text("""
use sys.io

act get_speed(gear: i32) -> i32 {
    on gear {
        1 => return 15
        2 => return 30
        3, 4 => return 65
        else => return 0
    }
}

act main() -> i32 {
    let g1 = get_speed(1)
    let g3 = get_speed(3)
    let g4 = get_speed(4)
    let g9 = get_speed(9)
    io.println("g1={g1}, g3={g3}, g4={g4}, g9={g9}")
    return 0
}
""", encoding="utf-8")

    # Python stage 1
    res_py = subprocess.run([sys.executable, "velo.py", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    assert "g1=15, g3=65, g4=65, g9=0" in res_py.stdout

    # Self-hosted stage 2
    res_sh = subprocess.run(["bin/velo.exe", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "g1=15, g3=65, g4=65, g9=0" in res_sh.stdout


def test_on_single_statement_and_wildcard(tmp_path):
    source = tmp_path / "test_wildcard.vl"
    source.write_text("""
use sys.io

act main() -> i32 {
    mut score: i32 = 0
    loop i in 0..6 {
        on i {
            0 => score += 1
            1, 2 => score += 10
            3 => score += 100
            _ => score += 1000
        }
    }
    io.println("final_score={score}")
    return 0
}
""", encoding="utf-8")

    # Python stage 1
    res_py = subprocess.run([sys.executable, "velo.py", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    # i=0: +1, i=1: +10, i=2: +10, i=3: +100, i=4: +1000, i=5: +1000 => 2121
    assert "final_score=2121" in res_py.stdout

    # Self-hosted stage 2
    res_sh = subprocess.run(["bin/velo.exe", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "final_score=2121" in res_sh.stdout


def test_match_is_regular_identifier(tmp_path):
    source = tmp_path / "test_identifiers.vl"
    source.write_text("""
use sys.io

act main() -> i32 {
    let match: i32 = 42
    let val: i32 = 58
    let total = match + val
    io.println("total={total}")
    return 0
}
""", encoding="utf-8")

    # Python stage 1
    res_py = subprocess.run([sys.executable, "velo.py", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    assert "total=100" in res_py.stdout

    # Self-hosted stage 2
    res_sh = subprocess.run(["bin/velo.exe", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "total=100" in res_sh.stdout


def test_example_19_execution():
    example_path = Path("examples/19_match_switch.vl")
    assert example_path.exists()

    # Stage 1
    res_py = subprocess.run([sys.executable, "velo.py", "run", str(example_path)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    assert "Status 200: OK" in res_py.stdout
    assert "Score 10: A+" in res_py.stdout
    assert "Total points across iterations 0..4 = 50" in res_py.stdout
    assert "Action for key 2 = attack" in res_py.stdout

    # Stage 2
    res_sh = subprocess.run(["bin/velo.exe", "run", str(example_path)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "Status 200: OK" in res_sh.stdout
    assert "Score 10: A+" in res_sh.stdout
    assert "Total points across iterations 0..4 = 50" in res_sh.stdout
    assert "Action for key 2 = attack" in res_sh.stdout


def test_case_keyword_removed(tmp_path):
    source = tmp_path / "test_case_removed.vl"
    source.write_text("""
act main() -> i32 {
    let x = 1
    on x {
        case 1 => return 0
        else => return 1
    }
}
""", encoding="utf-8")

    # Both Python compiler and native binary must reject 'case 1 =>'
    res_py = subprocess.run([sys.executable, "velo.py", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode != 0

    res_sh = subprocess.run(["bin/velo.exe", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode != 0


# ==============================================================================
# Phase 61: `break` and `continue` Control-Flow Matrix (Task 61.1 Red Baseline)
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


def run_velo_check(source_code: str) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile("w", suffix=".vl", delete=False) as f:
        f.write(source_code)
        f_name = f.name
    try:
        return subprocess.run([str(VELO_EXE), "check", f_name], capture_output=True, text=True)
    finally:
        Path(f_name).unlink(missing_ok=True)


class TestOnControlFlowMatrix:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo not built")

    def test_break_inside_on_exits_range_loop(self):
        """A `break` inside an `on` case must exit the enclosing loop, not just the match switch."""
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
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "iters=3" in res.stdout

    def test_break_inside_on_first_case(self):
        """A `break` in the first case must terminate the loop immediately on iteration 0."""
        code = """
        use sys.io
        act main() -> i32 {
            mut iters = 0
            loop i in 0..10 {
                on i {
                    0 => { break }
                    1 => { }
                    else => { }
                }
                iters += 1
            }
            io.println("iters={iters}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "iters=0" in res.stdout

    def test_break_inside_on_middle_case(self):
        """A `break` in a middle case must exit the loop at that specific iteration."""
        code = """
        use sys.io
        act main() -> i32 {
            mut iters = 0
            loop i in 0..10 {
                on i {
                    0, 1 => { }
                    2 => { break }
                    3, 4 => { }
                    else => { }
                }
                iters += 1
            }
            io.println("iters={iters}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "iters=2" in res.stdout

    def test_break_inside_on_last_case(self):
        """A `break` in the last explicit case must exit the loop at that iteration."""
        code = """
        use sys.io
        act main() -> i32 {
            mut iters = 0
            loop i in 0..10 {
                on i {
                    0 => { }
                    1 => { }
                    4 => { break }
                    else => { }
                }
                iters += 1
            }
            io.println("iters={iters}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "iters=4" in res.stdout

    def test_break_inside_on_else_case(self):
        """A `break` in the `else` (default) arm must exit the loop on the first unmatched value."""
        code = """
        use sys.io
        act main() -> i32 {
            mut iters = 0
            loop i in 0..10 {
                on i {
                    0, 1 => { }
                    else => { break }
                }
                iters += 1
            }
            io.println("iters={iters}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "iters=2" in res.stdout

    def test_break_inside_nested_on(self):
        """A `break` inside a nested `on` must bind to and exit the enclosing loop."""
        code = """
        use sys.io
        act main() -> i32 {
            mut iters = 0
            loop i in 0..10 {
                on i {
                    2 => {
                        let sub = 100
                        on sub {
                            100 => { break }
                            else => { }
                        }
                    }
                    else => { }
                }
                iters += 1
            }
            io.println("iters={iters}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "iters=2" in res.stdout

    def test_break_inside_tagged_union_on(self):
        """A `break` inside an `on` matching a tagged union must exit the enclosing loop."""
        code = """
        use sys.io
        kind Mode {
            Run
            Halt
        }
        act main() -> i32 {
            mut iters = 0
            loop i in 0..5 {
                mut m: Mode = Mode.Run
                if i == 2 {
                    m = Mode.Halt
                }
                on m {
                    .Halt => { break }
                    .Run => { }
                }
                iters += 1
            }
            io.println("iters={iters}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "iters=2" in res.stdout

    def test_continue_inside_on_skips_loop_tail(self):
        """A `continue` inside an `on` arm skips subsequent statements in the loop body."""
        code = """
        use sys.io
        act main() -> i32 {
            mut sum = 0
            loop i in 0..5 {
                on i {
                    2 => { continue }
                    else => { }
                }
                sum += 10
            }
            io.println("sum={sum}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "sum=40" in res.stdout

    def test_continue_inside_nested_on(self):
        """A `continue` inside a nested `on` continues the enclosing loop."""
        code = """
        use sys.io
        act main() -> i32 {
            mut sum = 0
            loop i in 0..5 {
                on i {
                    2 => {
                        let sub = 50
                        on sub {
                            50 => { continue }
                            else => { }
                        }
                    }
                    else => { }
                }
                sum += 10
            }
            io.println("sum={sum}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "sum=40" in res.stdout

    def test_break_inside_on_outside_loop_rejected(self):
        """A `break` inside an `on` outside a loop must be rejected (compile or build error)."""
        code = """
        act main() -> i32 {
            let x = 1
            on x {
                1 => { break }
                else => { }
            }
            return 0
        }
        """
        chk = run_velo_check(code)
        run = build_and_run(code, timeout=2.0)
        # In a sound type checker, `break` outside a loop is illegal:
        # either `velo check` fails, or compilation fails:
        assert chk.returncode != 0 or run.returncode != 0, "break outside loop inside on must be rejected"


