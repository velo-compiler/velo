"""
Phase 69 red baseline: deferred transfer statements must be rejected, not crash.

`defer` takes a *statement*, so `defer return`, `defer break`, `defer continue`
and `defer fail` parse fine. They then kill the Stage-2 compiler with a stack
overflow (`0xC00000FD`, exit `-1073741571`) and **no diagnostic at all** —
`velo check` and `velo emit-c` both die, so a user gets no line, no message, and
no hint that the `defer` is the problem.

Measured on the pre-fix compiler:

    defer return            -> exit -1073741571
    defer return 1          -> exit -1073741571
    defer break   (in loop) -> exit -1073741571
    defer continue(in loop) -> exit -1073741571
    defer fail "x" (or fn)  -> exit -1073741571
    defer { return 1 }      -> exit -1073741571
    defer if true { break } -> exit -1073741571
    defer io.println(1)     -> exit 0   (fine)

So the class is exactly "a transfer statement reached through a defer", including
transfers nested inside a block or `if` within the defer. Non-transfer defers are
unaffected and must stay accepted.

Why reject instead of define semantics: a deferred `return` would have to change
the function's result at cleanup time, after the real return value has already
been computed, and a deferred `break` would target a loop that has already been
left. Neither has a coherent meaning, `std/` and `src/` contain zero uses, and
the language already has a precedent for owning a control-flow rule in the
checker rather than the backend (Phase 62: `break`/`continue` outside a loop).
Go sidesteps the same question by making `defer` take a call rather than a
statement.

Every row asserts three things, because any one alone is insufficient:

* the compiler does not crash (exit is never the stack-overflow code);
* `velo check` fails, so the rule is owned by the semantic lane;
* the diagnostic names the deferred transfer, so the user can act on it.

A row that only asserted "not 0" would pass on the pre-fix compiler, since a
stack overflow is also not 0.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = REPO_ROOT / "bin" / ("velo.exe" if sys.platform == "win32" else "velo")

CRASH_CODE = -1073741571
CRASH_CODE_UNSIGNED = 3221225725


def get_build_env():
    env = dict(os.environ)
    ucrt_bin = r"C:\msys64\ucrt64\bin"
    if os.path.exists(ucrt_bin) and ucrt_bin not in env.get("PATH", ""):
        env["PATH"] = ucrt_bin + ";" + env.get("PATH", "")
    return env


def check(source: str) -> subprocess.CompletedProcess:
    """Runs `velo check` on the source and returns the completed process."""
    if not VELO_EXE.exists():
        pytest.skip(f"{VELO_EXE} is not built")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "probe.vl"
        src.write_text(source, encoding="utf-8", newline="\n")
        return subprocess.run(
            [str(VELO_EXE), "check", str(src)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(REPO_ROOT),
            env=get_build_env(),
            timeout=60.0,
        )


def emit_c(source: str) -> subprocess.CompletedProcess:
    """Runs `velo emit-c` on the source; the codegen lane must also not die."""
    if not VELO_EXE.exists():
        pytest.skip(f"{VELO_EXE} is not built")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "probe.vl"
        out = Path(tmp) / "probe.c"
        src.write_text(source, encoding="utf-8", newline="\n")
        return subprocess.run(
            [str(VELO_EXE), "emit-c", str(src), "-o", str(out)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(REPO_ROOT),
            env=get_build_env(),
            timeout=60.0,
        )


def assert_not_a_crash(res: subprocess.CompletedProcess, label: str) -> None:
    assert res.returncode not in (CRASH_CODE, CRASH_CODE_UNSIGNED), (
        f"{label}: the compiler crashed with a stack overflow "
        f"(exit {res.returncode}) instead of reporting a diagnostic"
    )


REJECTED_CASES = [
    (
        "defer_return_void",
        "act main() {\n    defer return\n    return\n}\n",
        "return",
    ),
    (
        "defer_return_value",
        "act main() -> i32 {\n    defer return 1\n    return 0\n}\n",
        "return",
    ),
    (
        "defer_break_in_loop",
        "act main() -> i32 {\n    loop i in 0..2 { defer break }\n    return 0\n}\n",
        "break",
    ),
    (
        "defer_continue_in_loop",
        "act main() -> i32 {\n    loop i in 0..2 { defer continue }\n    return 0\n}\n",
        "continue",
    ),
    (
        "defer_fail_in_or_function",
        'act f() -> i32 or string {\n    defer fail "boom"\n    return 0\n}\n'
        "act main() -> i32 { return 0 }\n",
        "fail",
    ),
    (
        "defer_return_nested_in_block",
        "act main() -> i32 {\n    defer { return 1 }\n    return 0\n}\n",
        "return",
    ),
    (
        "defer_break_nested_in_if",
        "act main() -> i32 {\n    loop i in 0..2 { defer if true { break } }\n    return 0\n}\n",
        "break",
    ),
]


@pytest.mark.parametrize("label,source,keyword", REJECTED_CASES)
def test_deferred_transfer_is_rejected_not_crashed(label, source, keyword):
    """A deferred transfer must produce a semantic error naming the keyword."""
    res = check(source)
    assert_not_a_crash(res, label)
    assert res.returncode != 0, (
        f"{label}: a deferred `{keyword}` was accepted; it has no meaning and "
        f"would change control flow at cleanup time"
    )
    combined = (res.stdout + res.stderr).lower()
    assert "defer" in combined, (
        f"{label}: the diagnostic does not mention `defer`, so the user cannot "
        f"tell what to change:\n{res.stdout}{res.stderr}"
    )
    assert keyword in combined, (
        f"{label}: the diagnostic does not name `{keyword}`:\n{res.stdout}{res.stderr}"
    )


@pytest.mark.parametrize("label,source,keyword", REJECTED_CASES)
def test_deferred_transfer_does_not_crash_the_codegen_lane(label, source, keyword):
    """`emit-c` must also survive: a checker-only fix that still crashes in the
    backend would leave `velo build` broken for the same program."""
    res = emit_c(source)
    assert_not_a_crash(res, f"emit-c {label}")
    assert res.returncode != 0, (
        f"emit-c {label}: a deferred `{keyword}` reached the backend and was "
        f"lowered instead of rejected"
    )


ACCEPTED_CASES = [
    (
        "defer_call",
        "act main() -> i32 {\n    defer io.println(1)\n    return 0\n}\n",
    ),
    (
        "defer_var_decl",
        "act main() -> i32 {\n    defer let x = 1\n    return 0\n}\n",
    ),
    (
        "defer_assignment",
        "act main() -> i32 {\n    mut v = 0\n    defer v = 1\n    return v\n}\n",
    ),
    (
        "defer_nested_block_of_plain_stmts",
        "act main() -> i32 {\n    defer { io.println(1) }\n    return 0\n}\n",
    ),
    (
        "defer_if_of_plain_stmts",
        "act main() -> i32 {\n    defer if true { io.println(1) }\n    return 0\n}\n",
    ),
]


@pytest.mark.parametrize("label,source", ACCEPTED_CASES)
def test_non_transfer_defers_stay_accepted(label, source):
    """The rule must reject transfers only; ordinary deferred work still checks.

    This is the row that stops a too-broad fix: rejecting every deferred
    statement would pass all the rejection rows above and silently delete the
    feature.
    """
    res = check(source)
    assert_not_a_crash(res, label)
    assert res.returncode == 0, (
        f"{label}: a legitimate deferred statement was rejected:\n{res.stdout}{res.stderr}"
    )
