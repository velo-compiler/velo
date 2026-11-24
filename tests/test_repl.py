"""
Task 79.4: Interactive Velo REPL Tests (`velo repl`).

Verifies:
1. `velo repl` launches interactive read-eval-print loop with standard banner and prompt.
2. Direct expression evaluation (integers, strings, math, etc.).
3. Stateful multi-line session persistence (variables declared with `let` and `mut`).
4. In-place variable mutations (`+=`, `-=`, etc.).
5. REPL built-in commands: `:help`, `:vars`, `:reset`, `:quit`, `:q`, `:exit`.
6. Graceful error recovery: syntax/type errors report diagnostics without corrupting session state.
7. Clean EOF handling.
8. Module imports (`use ...`) at REPL session level.
9. CLI usage manual registers `velo repl`.
"""

import os
import subprocess
from pathlib import Path
import pytest
from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()


def get_env():
    env = os.environ.copy()
    if cc_dir() not in env.get("PATH", ""):
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return env


def run_repl(input_text: str):
    """Executes `velo repl` passing input_text through stdin."""
    return subprocess.run(
        [str(VELO_EXE), "repl"],
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
        cwd=str(REPO_ROOT),
    )


def test_repl_banner_and_exit():
    """Verifies banner, prompt, and clean exit via :q."""
    res = run_repl(":q\n")
    assert res.returncode == 0
    assert "Velo REPL v" in res.stdout
    assert "velo> " in res.stdout
    assert "Goodbye!" in res.stdout


def test_repl_help_and_exit_aliases():
    """Verifies :help output and exit command aliases."""
    res_help = run_repl(":help\n:exit\n")
    assert res_help.returncode == 0
    assert ":help" in res_help.stdout
    assert ":reset" in res_help.stdout
    assert ":vars" in res_help.stdout
    assert ":quit" in res_help.stdout
    assert "Goodbye!" in res_help.stdout

    res_quit = run_repl(":quit\n")
    assert res_quit.returncode == 0
    assert "Goodbye!" in res_quit.stdout


def test_repl_arithmetic_and_string_expressions():
    """Verifies single-expression evaluation for arithmetic and strings."""
    script = (
        "10 * 5 + 2\n"
        '"velo" + " " + "lang"\n'
        ":q\n"
    )
    res = run_repl(script)
    assert res.returncode == 0
    assert "52" in res.stdout
    assert "velo lang" in res.stdout


def test_repl_stateful_session():
    """Verifies variable declarations persist across lines."""
    script = (
        "let a = 15\n"
        "let b = 25\n"
        "a + b\n"
        ":vars\n"
        ":q\n"
    )
    res = run_repl(script)
    assert res.returncode == 0
    assert "40" in res.stdout
    assert "let a = 15" in res.stdout
    assert "let b = 25" in res.stdout


def test_repl_variable_mutation():
    """Verifies mut variables and compound assignments persist."""
    script = (
        "mut counter = 10\n"
        "counter += 7\n"
        "counter\n"
        ":q\n"
    )
    res = run_repl(script)
    assert res.returncode == 0
    assert "17" in res.stdout


def test_repl_session_reset():
    """Verifies :reset clears session variables and imports."""
    script = (
        "let x = 100\n"
        ":reset\n"
        ":vars\n"
        ":q\n"
    )
    res = run_repl(script)
    assert res.returncode == 0
    assert "[Velo REPL] Session reset." in res.stdout
    assert "No active session state." in res.stdout


def test_repl_error_recovery():
    """Verifies compiler errors do not corrupt prior or subsequent valid evaluations."""
    script = (
        "let ok_val = 5\n"
        "invalid %$# syntax\n"
        "ok_val * 10\n"
        ":q\n"
    )
    res = run_repl(script)
    assert res.returncode == 0
    assert "[Velo Error]" in res.stdout
    assert "50" in res.stdout


def test_repl_eof_handling():
    """Verifies EOF (Ctrl+D / closed pipe) exits cleanly with code 0."""
    res = run_repl("40 + 2\n")
    assert res.returncode == 0
    assert "42" in res.stdout
    assert "Goodbye!" in res.stdout


def test_repl_module_import():
    """Verifies importing modules at REPL level."""
    script = (
        "use std.coll\n"
        "let s = shelf[1, 2, 3, 4]\n"
        "s.len\n"
        ":q\n"
    )
    res = run_repl(script)
    assert res.returncode == 0
    assert "4" in res.stdout


def test_repl_usage_help():
    """Verifies that `velo help` mentions `velo repl`."""
    res = subprocess.run(
        [str(VELO_EXE), "help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
        cwd=str(REPO_ROOT),
    )
    assert res.returncode == 0
    assert "velo repl" in res.stdout
