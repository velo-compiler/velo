"""Phase 62: `break`/`continue` outside a loop must be rejected *by the checker*.

Red baseline (Task 62.1). `docs/SPECIFICATION.md` 9 defines `velo check` as
"lex, parse, semantic analysis, monomorphization (no codegen)", and
`type_checker_stmt.vl` returns immediately for `STMT_BREAK`/`STMT_CONTINUE`
without tracking loop depth. The rule is therefore enforced only by the backend
lane (`codegen_stmt.vl`, `report_error("backend", ...)`), so today an
out-of-loop `break` yields:

    [Velo Error] backend:2:5 - break statement not within a loop
    [Velo Error] Code generation failed with 1 errors.

instead of a semantic diagnostic. These tests pin the contract the phase must
satisfy: the diagnostic originates in the source file at the offending
statement, no emission lane runs, and the valid loop rows keep compiling.

The task's "nested function" row is documented here as unsupported: Velo has no
nested `act` declarations (parser: "Expected '(' after 'act'"), so the row is
asserted as a parse error rather than a loop-context case.
"""
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).parent.parent.resolve()
VELO_EXE = ROOT_DIR / "bin" / ("velo.exe" if os.name == "nt" else "velo")
if not VELO_EXE.exists() and (ROOT_DIR / "bin" / "velo.exe").exists():
    VELO_EXE = ROOT_DIR / "bin" / "velo.exe"

BREAK = "break statement not within a loop"
CONTINUE = "continue statement not within a loop"

# (id, source, expected keyword, 1-based line of the offending statement)
INVALID_ROWS = [
    (
        "main-direct-break",
        """act main() {
    break
}
""",
        BREAK,
        2,
    ),
    (
        "main-direct-continue",
        """act main() {
    continue
}
""",
        CONTINUE,
        2,
    ),
    (
        "if-break",
        """act main() {
    if true {
        break
    }
}
""",
        BREAK,
        3,
    ),
    (
        "if-else-continue",
        """act main() -> i32 {
    if true {
        return 0
    } else {
        continue
    }
}
""",
        CONTINUE,
        5,
    ),
    (
        "on-arm-break",
        """act inspect_value(val: i32) {
    on val {
        1 => { break }
        else => { }
    }
}
""",
        BREAK,
        3,
    ),
    (
        "plain-block-break",
        """act main() {
    {
        break
    }
}
""",
        BREAK,
        3,
    ),
    (
        "zone-continue",
        """act main() {
    zone {
        continue
    }
}
""",
        CONTINUE,
        3,
    ),
    (
        "unsafe-break",
        """act main() {
    unsafe {
        break
    }
}
""",
        BREAK,
        3,
    ),
    (
        "stale-depth-same-function",
        """act main() {
    loop i in 0..3 {
        break
    }
    break
}
""",
        BREAK,
        5,
    ),
    (
        "stale-depth-previous-function",
        """act count_down() {
    loop i in 0..3 {
        break
    }
}

act main() {
    continue
}
""",
        CONTINUE,
        8,
    ),
]

# (id, source, expected stdout substring when executed)
VALID_ROWS = [
    (
        "unconditional-loop-break",
        """use sys.io
act main() -> i32 {
    mut n = 0
    loop {
        n += 1
        if n == 4 { break }
    }
    io.println("n={n}")
    return 0
}
""",
        "n=4",
    ),
    (
        "count-loop-continue",
        """use sys.io
act main() -> i32 {
    mut sum = 0
    loop 5 {
        if it == 2 { continue }
        sum += it as i32
    }
    io.println("sum={sum}")
    return 0
}
""",
        "sum=8",
    ),
    (
        "range-loop-break",
        """use sys.io
act main() -> i32 {
    mut hit = -1
    loop i in 0..10 {
        if i == 3 { hit = i; break }
    }
    io.println("hit={hit}")
    return 0
}
""",
        "hit=3",
    ),
    (
        "condition-loop-break",
        """use sys.io
act main() -> i32 {
    mut i = 0
    loop i < 10 {
        if i == 2 { break }
        i += 1
    }
    io.println("i={i}")
    return 0
}
""",
        "i=2",
    ),
    (
        "nested-loops-break-inner-only",
        """use sys.io
act main() -> i32 {
    mut inner = 0
    loop r in 0..3 {
        loop c in 0..5 {
            if c == 2 { break }
            inner += 1
        }
    }
    io.println("inner={inner}")
    return 0
}
""",
        "inner=6",
    ),
    (
        "on-inside-loop-break",
        """use sys.io
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
""",
        "iters=3",
    ),
    (
        "zone-inside-loop-continue",
        """use sys.io
act main() -> i32 {
    mut sum = 0
    loop i in 0..4 {
        zone {
            if i == 1 { continue }
            sum += i
        }
    }
    io.println("sum={sum}")
    return 0
}
""",
        "sum=5",
    ),
    (
        "unsafe-inside-loop-break",
        """use sys.io
act main() -> i32 {
    mut n = 0
    loop {
        unsafe { n += 1 }
        if n == 2 { break }
    }
    io.println("n={n}")
    return 0
}
""",
        "n=2",
    ),
]


def _require_native():
    if not VELO_EXE.exists():
        pytest.skip("bin/velo not built")


def _write(tmp_path, name, content):
    p = tmp_path / name
    with open(p, "w", newline="\n", encoding="utf-8") as fh:
        fh.write(content)
    return p


def _check(path, *extra):
    return subprocess.run(
        [str(VELO_EXE), "check", str(path), *extra],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    "ident,source,message,line",
    INVALID_ROWS,
    ids=[row[0] for row in INVALID_ROWS],
)
def test_out_of_loop_is_rejected_by_the_checker(tmp_path, ident, source, message, line):
    """The checker must own this rule: no emission lane may be reached."""
    _require_native()
    path = _write(tmp_path, f"{ident}.vl", source)
    result = _check(path)
    blob = result.stdout + result.stderr

    assert result.returncode != 0, blob
    assert message in blob, blob
    assert "Code generation failed" not in blob, (
        "the backend lane must never see an unbound break/continue:\n" + blob
    )
    assert "backend:" not in blob, (
        "diagnostic lane must be semantic, not backend:\n" + blob
    )


@pytest.mark.parametrize(
    "ident,source,message,line",
    INVALID_ROWS,
    ids=[row[0] for row in INVALID_ROWS],
)
def test_diagnostic_points_at_the_offending_statement(tmp_path, ident, source, message, line):
    _require_native()
    path = _write(tmp_path, f"{ident}_pos.vl", source)
    result = _check(path, "--json")
    assert result.returncode != 0, result.stdout + result.stderr
    report = json.loads(result.stdout)

    matching = [d for d in report["diagnostics"] if d["message"] == message]
    assert matching, report["diagnostics"]
    first = matching[0]
    assert first["file"] == str(path), f"diagnostic must name the source file: {first}"
    assert first["line"] == line, f"expected line {line}, got {first}"
    assert first["severity"] == "error"


@pytest.mark.parametrize(
    "ident,source,expected",
    VALID_ROWS,
    ids=[row[0] for row in VALID_ROWS],
)
def test_loops_still_accept_break_and_continue(tmp_path, ident, source, expected):
    """Over-blocking guard: every bounded loop row stays valid and runs."""
    _require_native()
    path = _write(tmp_path, f"{ident}.vl", source)
    checked = _check(path)
    blob = checked.stdout + checked.stderr
    assert checked.returncode == 0, blob
    assert "Check passed" in blob

    ran = subprocess.run(
        [str(VELO_EXE), "run", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert expected in ran.stdout


def test_nested_function_is_not_supported(tmp_path):
    """The matrix row "in a nested function" is unreachable: `act` cannot nest."""
    _require_native()
    path = _write(tmp_path, "nested_act.vl", """act main() {
    act inner() {
        break
    }
}
""")
    result = _check(path)
    blob = result.stdout + result.stderr
    assert result.returncode != 0, blob
    assert "Expected '(' after 'act'" in blob, blob
