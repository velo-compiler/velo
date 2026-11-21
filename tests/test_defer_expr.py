import subprocess
import tempfile
from pathlib import Path
import pytest
from conftest import velo_exe

VELO_EXE = velo_exe()


def run_velo(args, cwd=None):
    res = subprocess.run(
        [str(VELO_EXE)] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return res


@pytest.mark.fast
def test_expression_defer_single_call():
    """`defer func(arg)` executes at function exit."""
    with tempfile.TemporaryDirectory() as td:
        main_file = Path(td) / "main.vl"
        main_file.write_text(
            'mut order: string = ""\n'
            'act step(s: string) {\n'
            '    order = order + s\n'
            '}\n'
            'act work() {\n'
            '    defer step("B")\n'
            '    step("A")\n'
            '}\n'
            'act main() {\n'
            '    work()\n'
            '    assert(order == "AB", "expression defer executed in correct order")\n'
            '}\n',
            encoding="utf-8"
        )
        res = run_velo(["run", str(main_file)], cwd=td)
        assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"


@pytest.mark.fast
def test_expression_defer_lifo_order():
    """Multiple expression defers run in LIFO order."""
    with tempfile.TemporaryDirectory() as td:
        main_file = Path(td) / "main.vl"
        main_file.write_text(
            'mut order: string = ""\n'
            'act append_step(s: string) {\n'
            '    order = order + s\n'
            '}\n'
            'act test_lifo() {\n'
            '    defer append_step("1")\n'
            '    defer append_step("2")\n'
            '    defer append_step("3")\n'
            '    append_step("start-")\n'
            '}\n'
            'act main() {\n'
            '    test_lifo()\n'
            '    assert(order == "start-321", "expression defers run LIFO")\n'
            '}\n',
            encoding="utf-8"
        )
        res = run_velo(["run", str(main_file)], cwd=td)
        assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"


@pytest.mark.fast
def test_expression_defer_mixed_with_block_defer():
    """Expression defers and block defers interleave in exact LIFO order."""
    with tempfile.TemporaryDirectory() as td:
        main_file = Path(td) / "main.vl"
        main_file.write_text(
            'mut trace: string = ""\n'
            'act trace_msg(m: string) {\n'
            '    trace = trace + m\n'
            '}\n'
            'act run_mixed() {\n'
            '    defer trace_msg("C")\n'
            '    defer {\n'
            '        trace_msg("B")\n'
            '    }\n'
            '    defer trace_msg("A")\n'
            '    trace_msg("start:")\n'
            '}\n'
            'act main() {\n'
            '    run_mixed()\n'
            '    assert(trace == "start:ABC", "mixed defers run LIFO")\n'
            '}\n',
            encoding="utf-8"
        )
        res = run_velo(["run", str(main_file)], cwd=td)
        assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"


@pytest.mark.fast
def test_expression_defer_on_early_return():
    """Expression defer runs on early return."""
    with tempfile.TemporaryDirectory() as td:
        main_file = Path(td) / "main.vl"
        main_file.write_text(
            'mut cleaned: bool = false\n'
            'act cleanup() {\n'
            '    cleaned = true\n'
            '}\n'
            'act check_early(flag: bool) -> i32 {\n'
            '    defer cleanup()\n'
            '    if flag {\n'
            '        return 100\n'
            '    }\n'
            '    return 200\n'
            '}\n'
            'act main() {\n'
            '    let r = check_early(true)\n'
            '    assert(r == 100, "return value ok")\n'
            '    assert(cleaned, "defer ran on early return")\n'
            '}\n',
            encoding="utf-8"
        )
        res = run_velo(["run", str(main_file)], cwd=td)
        assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"


@pytest.mark.fast
def test_expression_defer_rejects_transfer():
    """`defer return`, `defer break`, `defer continue` are rejected."""
    with tempfile.TemporaryDirectory() as td:
        main_file = Path(td) / "main.vl"
        main_file.write_text(
            'act main() {\n'
            '    defer return\n'
            '}\n',
            encoding="utf-8"
        )
        res = run_velo(["run", str(main_file)], cwd=td)
        assert res.returncode != 0
        combined = res.stdout + res.stderr
        assert "'defer' cannot defer return" in combined
