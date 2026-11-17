import os
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest
from conftest import velo_exe

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
    res_sh = subprocess.run([str(velo_exe()), "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
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
    res_sh = subprocess.run([str(velo_exe()), "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
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
    res_sh = subprocess.run([str(velo_exe()), "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
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
    res_sh = subprocess.run([str(velo_exe()), "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
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
    res_sh = subprocess.run([str(velo_exe()), "run", str(example_path)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
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

    res_sh = subprocess.run([str(velo_exe()), "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode != 0


# ==============================================================================
# Phase 61: `break` and `continue` Control-Flow Matrix (Task 61.1 Red Baseline)
# ==============================================================================

ROOT_DIR = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()
if not VELO_EXE.exists() and (velo_exe()).exists():
    VELO_EXE = velo_exe()


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

    def test_continue_inside_on_first_case(self):
        """A `continue` in the first case skips remainder of iteration 0 and advances to 1."""
        code = """
        use sys.io
        act main() -> i32 {
            mut sum = 0
            loop i in 0..5 {
                on i {
                    0 => { continue }
                    else => { }
                }
                sum += i
            }
            io.println("sum={sum}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        # i=0 skipped; i=1, 2, 3, 4 summed = 10
        assert "sum=10" in res.stdout

    def test_continue_inside_on_last_case(self):
        """A `continue` in the last explicit case skips remainder of that iteration."""
        code = """
        use sys.io
        act main() -> i32 {
            mut sum = 0
            loop i in 0..5 {
                on i {
                    0 => { }
                    1 => { }
                    4 => { continue }
                    else => { }
                }
                sum += i
            }
            io.println("sum={sum}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        # i=4 skipped; i=0, 1, 2, 3 summed = 6
        assert "sum=6" in res.stdout

    def test_continue_inside_on_else_case(self):
        """A `continue` in the `else` case skips remainder of all unmatched iterations."""
        code = """
        use sys.io
        act main() -> i32 {
            mut tail_hits = 0
            loop i in 0..6 {
                on i {
                    0, 1 => { }
                    else => { continue }
                }
                tail_hits += 1
            }
            io.println("tail_hits={tail_hits}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        # Only i=0 and i=1 execute tail; 2, 3, 4, 5 hit continue
        assert "tail_hits=2" in res.stdout

    def test_continue_inside_on_in_nested_loops_continues_inner_only(self):
        """A `continue` inside `on` in an inner loop continues only the inner loop."""
        code = """
        use sys.io
        act main() -> i32 {
            mut inner_tails = 0
            loop r in 0..3 {
                loop c in 0..4 {
                    on c {
                        1, 3 => { continue }
                        else => { }
                    }
                    inner_tails += 1
                }
            }
            io.println("inner_tails={inner_tails}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        # Each row executes c=0, 2 (2 times). 3 rows * 2 = 6.
        assert "inner_tails=6" in res.stdout

    def test_continue_inside_on_advances_implicit_it(self):
        """A `continue` inside `on` properly advances the iteration counter."""
        code = """
        use sys.io
        act main() -> i32 {
            mut iters = 0
            loop 5 {
                on it {
                    1, 3 => { continue }
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
        # it=0, 2, 4 hit tail (+3); it=1, 3 continue
        assert "iters=3" in res.stdout

    def test_continue_inside_tagged_union_on(self):
        """A `continue` inside an `on` matching a tagged union continues the enclosing loop."""
        code = """
        use sys.io
        kind Task {
            Skip
            Do
        }
        act main() -> i32 {
            mut done = 0
            loop i in 0..4 {
                mut t: Task = Task.Do
                if i % 2 == 1 {
                    t = Task.Skip
                }
                on t {
                    .Skip => { continue }
                    .Do => { }
                }
                done += 1
            }
            io.println("done={done}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        # i=0 (Do), i=1 (Skip), i=2 (Do), i=3 (Skip) => done=2
        assert "done=2" in res.stdout

    def test_continue_inside_on_outside_loop_rejected(self):
        """A `continue` inside an `on` outside a loop must be rejected at compile/build time."""
        code = """
        act main() -> i32 {
            let x = 1
            on x {
                1 => { continue }
                else => { }
            }
            return 0
        }
        """
        chk = run_velo_check(code)
        run = build_and_run(code, timeout=2.0)
        assert chk.returncode != 0 or run.returncode != 0, "continue outside loop inside on must be rejected"

    def test_continue_inside_on_no_fallthrough(self):
        """`continue` inside an `on` arm must not fall through to the next case."""
        code = """
        use sys.io
        act main() -> i32 {
            mut hit_next = 0
            loop i in 0..3 {
                on i {
                    1 => { continue }
                    2 => { hit_next += 1 }
                    else => { }
                }
            }
            io.println("hit_next={hit_next}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        # hit_next should only be incremented when i == 2 (hit_next=1), not when i == 1
        assert "hit_next=1" in res.stdout

    def test_nested_three_level_on_break(self):
        """A `break` inside three levels of nested `on` blocks binds to and exits the enclosing loop."""
        code = """
        use sys.io
        act main() -> i32 {
            mut iters = 0
            loop i in 0..10 {
                on i {
                    3 => {
                        let a = 1
                        on a {
                            1 => {
                                let b = 2
                                on b {
                                    2 => { break }
                                    else => { }
                                }
                            }
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
        assert "iters=3" in res.stdout

    def test_nested_three_level_on_continue(self):
        """A `continue` inside three levels of nested `on` blocks continues the enclosing loop."""
        code = """
        use sys.io
        act main() -> i32 {
            mut sum = 0
            loop i in 0..5 {
                on i {
                    2 => {
                        let a = 10
                        on a {
                            10 => {
                                let b = 20
                                on b {
                                    20 => { continue }
                                    else => { }
                                }
                            }
                            else => { }
                        }
                    }
                    else => { }
                }
                sum += i
            }
            io.println("sum={sum}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "sum=8" in res.stdout

    def test_nested_loops_with_nested_on_break_inner(self):
        """In nested loops each with `on`, `break` in the inner `on` exits only the inner loop."""
        code = """
        use sys.io
        act main() -> i32 {
            mut outer_count = 0
            mut inner_count = 0
            loop r in 0..4 {
                on r {
                    3 => { break }
                    else => { }
                }
                outer_count += 1
                loop c in 0..5 {
                    on c {
                        1 => {
                            let k = 9
                            on k {
                                9 => { break }
                                else => { }
                            }
                        }
                        else => { }
                    }
                    inner_count += 1
                }
            }
            io.println("outer={outer_count}, inner={inner_count}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "outer=3, inner=3" in res.stdout

    def test_nested_loops_with_nested_on_continue_inner(self):
        """In nested loops each with `on`, `continue` in the inner `on` continues only the inner loop."""
        code = """
        use sys.io
        act main() -> i32 {
            mut inner_sum = 0
            loop r in 0..3 {
                loop c in 0..4 {
                    on c {
                        1 => {
                            let sub = 42
                            on sub {
                                42 => { continue }
                                else => { }
                            }
                        }
                        else => { }
                    }
                    inner_sum += 1
                }
            }
            io.println("inner_sum={inner_sum}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "inner_sum=9" in res.stdout

    def test_nested_on_else_arm_break(self):
        """A `break` inside an `else` (default) arm of a nested `on` exits the enclosing loop."""
        code = """
        use sys.io
        act main() -> i32 {
            mut iters = 0
            loop i in 0..6 {
                on i {
                    2 => {
                        let unknown_val = 999
                        on unknown_val {
                            1, 2, 3 => { }
                            else => { break }
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

    def test_nested_on_else_arm_continue(self):
        """A `continue` inside an `else` (default) arm of a nested `on` continues the enclosing loop."""
        code = """
        use sys.io
        act main() -> i32 {
            mut tail_hits = 0
            loop i in 0..4 {
                on i {
                    1 => {
                        let unknown_val = 888
                        on unknown_val {
                            10 => { }
                            else => { continue }
                        }
                    }
                    else => { }
                }
                tail_hits += 1
            }
            io.println("tail_hits={tail_hits}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "tail_hits=3" in res.stdout

    def test_nested_on_no_fallthrough_between_cases(self):
        """Cases in outer and nested `on` must not fall through into adjacent arms."""
        code = """
        use sys.io
        act main() -> i32 {
            mut log = 0
            loop i in 0..4 {
                on i {
                    0 => {
                        log = log * 10 + 1
                    }
                    1 => {
                        log = log * 10 + 2
                        let sub = 1
                        on sub {
                            1 => { log = log * 10 + 3 }
                            else => { }
                        }
                    }
                    2 => {
                        log = log * 10 + 4
                        break
                    }
                    3 => {
                        log = log * 10 + 5
                    }
                    else => { }
                }
            }
            io.println("log={log}")
            return 0
        }
        """
        res = build_and_run(code, timeout=2.0)
        assert res.returncode == 0
        assert "log=1234" in res.stdout

    def test_nested_tagged_union_inside_integer_on_break(self):
        """A `break` inside a tagged union `on` nested inside an integer `on` exits the enclosing loop."""
        code = """
        use sys.io
        kind Command {
            Step
            Stop
        }
        act main() -> i32 {
            mut iters = 0
            loop i in 0..5 {
                on i {
                    2 => {
                        mut cmd: Command = Command.Stop
                        on cmd {
                            .Stop => { break }
                            .Step => { }
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

    def test_nested_integer_on_inside_tagged_union_on_continue(self):
        """A `continue` inside an integer `on` nested inside a tagged union `on` continues the enclosing loop."""
        code = """
        use sys.io
        kind Signal {
            Green
            Yellow
            Red
        }
        act main() -> i32 {
            mut sum = 0
            loop i in 0..5 {
                mut sig: Signal = Signal.Green
                if i == 1 {
                    sig = Signal.Yellow
                }
                on sig {
                    .Yellow => {
                        let code = 100
                        on code {
                            100 => { continue }
                            else => { }
                        }
                    }
                    .Green, .Red => { }
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




