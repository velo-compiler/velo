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
from conftest import velo_exe

ROOT_DIR = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()
if not VELO_EXE.exists() and (velo_exe()).exists():
    VELO_EXE = velo_exe()

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


# ==============================================================================
# Task 62.2: loop-depth tracking must be balanced on every path
# ==============================================================================

DEPTH_SHAPES = [
    (
        "loop-inside-on",
        """act main() -> i32 {
    on 1 {
        1 => {
            loop i in 0..3 {
                if i == 1 { break }
            }
        }
        else => { }
    }
    return 0
}
""",
    ),
    (
        "on-inside-loop-break-and-continue",
        """act main() -> i32 {
    loop i in 0..5 {
        on i {
            1 => { continue }
            3 => { break }
            else => { }
        }
    }
    return 0
}
""",
    ),
    (
        "early-return-inside-loop",
        """act find(n: i32) -> i32 {
    loop i in 0..10 {
        if i == n { return i }
    }
    return -1
}

act main() -> i32 {
    return find(3)
}
""",
    ),
    (
        "loop-then-second-loop",
        """act main() -> i32 {
    loop i in 0..3 {
        break
    }
    loop j in 0..3 {
        continue
    }
    return 0
}
""",
    ),
    (
        "deeply-nested-loops",
        """act main() -> i32 {
    loop a in 0..2 {
        loop b in 0..2 {
            loop c in 0..2 {
                if c == 1 { continue }
                if b == 1 { break }
            }
        }
    }
    return 0
}
""",
    ),
    (
        "loop-in-zone-in-unsafe",
        """act main() -> i32 {
    unsafe {
        zone {
            loop i in 0..3 {
                break
            }
        }
    }
    return 0
}
""",
    ),
]


@pytest.mark.parametrize(
    "ident,source",
    DEPTH_SHAPES,
    ids=[row[0] for row in DEPTH_SHAPES],
)
def test_loop_depth_balances_on_every_path(tmp_path, ident, source):
    """A balanced counter must never reject a validly nested break/continue."""
    _require_native()
    path = _write(tmp_path, f"{ident}.vl", source)
    result = _check(path)
    blob = result.stdout + result.stderr
    assert result.returncode == 0, blob
    assert not any(m in blob for m in (BREAK, CONTINUE)), blob


def test_depth_does_not_leak_out_of_a_loop(tmp_path):
    """A statement after a closed loop must not inherit its depth."""
    _require_native()
    path = _write(tmp_path, "leak_after_loop.vl", """act main() {
    loop i in 0..3 {
        break
    }
    break
}
""")
    result = _check(path)
    blob = result.stdout + result.stderr
    assert result.returncode != 0, blob
    assert BREAK in blob, blob


def test_depth_does_not_leak_out_of_a_function(tmp_path):
    """Depth must reset at function entry: a later function starts at zero."""
    _require_native()
    path = _write(tmp_path, "leak_across_funcs.vl", """act first() {
    loop i in 0..3 {
        break
    }
}

act second() {
    continue
}
""")
    result = _check(path)
    blob = result.stdout + result.stderr
    assert result.returncode != 0, blob
    assert CONTINUE in blob, blob


def test_depth_resets_after_early_return_in_loop(tmp_path):
    """An early `return` inside a loop must not leave stale depth behind."""
    _require_native()
    path = _write(tmp_path, "leak_after_early_return.vl", """act first(n: i32) -> i32 {
    loop i in 0..10 {
        if i == n { return i }
    }
    return -1
}

act second() {
    break
}
""")
    result = _check(path)
    blob = result.stdout + result.stderr
    assert result.returncode != 0, blob
    assert BREAK in blob, blob


# ==============================================================================
# Task 62.4: codegen defense in depth
# ==============================================================================

INTERNAL_BREAK = "internal compiler error: unbound break reached codegen"
INTERNAL_CONTINUE = "internal compiler error: unbound continue reached codegen"


@pytest.mark.parametrize(
    "ident,source,message,line",
    INVALID_ROWS,
    ids=[row[0] for row in INVALID_ROWS],
)
def test_codegen_defense_is_never_reached_from_source(tmp_path, ident, source, message, line):
    """The checker owns the rule, so emission must never see an unbound jump.

    Reaching the backend now means an internal invariant broke, which is why the
    lane reports an internal compiler error rather than a backend diagnostic.
    Every source-level case must stop in semantic analysis first.
    """
    _require_native()
    path = _write(tmp_path, f"{ident}_def.vl", source)
    result = _check(path)
    blob = result.stdout + result.stderr

    assert result.returncode != 0, blob
    assert message in blob, blob
    assert "internal compiler error" not in blob, (
        "the checker must reject this before any emission lane:\n" + blob
    )
    assert INTERNAL_BREAK not in blob and INTERNAL_CONTINUE not in blob, blob


def test_backend_no_longer_owns_the_diagnostic(tmp_path):
    """The old user-facing backend wording must be gone from the emission lane."""
    _require_native()
    path = _write(tmp_path, "no_backend_wording.vl", """act main() {
    break
}
""")
    result = _check(path)
    blob = result.stdout + result.stderr
    assert result.returncode != 0, blob
    assert "backend:" not in blob, blob
    assert "semantic:" in blob, blob


def test_defense_messages_are_internal_not_user_facing(tmp_path):
    """Guard the wording contract: the emit-lane strings say 'internal compiler error'."""
    source = (ROOT_DIR / "src" / "backend" / "codegen_stmt.vl").read_text(encoding="utf-8")
    assert INTERNAL_BREAK in source, "break defense missing from codegen_stmt.vl"
    assert INTERNAL_CONTINUE in source, "continue defense missing from codegen_stmt.vl"
    assert 'report_error("backend", stmt.line, stmt.col, "break statement not within a loop")' not in source
    assert 'report_error("backend", stmt.line, stmt.col, "continue statement not within a loop")' not in source


# ==============================================================================
# Task 62.5: security/regression gate and documentation
# ==============================================================================

SECURITY_BUILD_SOURCES = [
    (
        "break-in-main",
        """act main() {
    break
}
""",
        BREAK,
    ),
    (
        "continue-in-on",
        """act inspect_value(val: i32) {
    on val {
        1 => { continue }
        else => { }
    }
}
""",
        CONTINUE,
    ),
    (
        "unbound-jump-does-not-emit-c",
        """act main() {
    loop i in 0..2 {
        break
    }
    break
}
""",
        BREAK,
    ),
]


@pytest.mark.parametrize(
    "ident,source,message",
    SECURITY_BUILD_SOURCES,
    ids=[row[0] for row in SECURITY_BUILD_SOURCES],
)
def test_rejected_programs_never_produce_a_binary(tmp_path, ident, source, message):
    """`run`, `build`, and `emit-c` must all refuse, with no crash and no artifact."""
    _require_native()
    path = _write(tmp_path, f"{ident}.vl", source)
    exe = tmp_path / f"{ident}.exe"
    c_out = tmp_path / f"{ident}.c"

    built = subprocess.run(
        [str(VELO_EXE), "build", str(path), "-o", str(exe)],
        capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    blob = built.stdout + built.stderr
    assert built.returncode != 0, blob
    assert message in blob, blob
    assert "Successfully built" not in blob, blob
    assert not exe.exists(), "no binary may be produced for a rejected program"

    emitted = subprocess.run(
        [str(VELO_EXE), "emit-c", str(path), "-o", str(c_out)],
        capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    emit_blob = emitted.stdout + emitted.stderr
    assert emitted.returncode != 0, emit_blob
    assert not c_out.exists(), "no translation unit may be written for a rejected program"

    ran = subprocess.run(
        [str(VELO_EXE), "run", str(path)],
        capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    run_blob = ran.stdout + ran.stderr
    assert ran.returncode != 0, run_blob
    assert "Successfully built" not in run_blob, run_blob


@pytest.mark.parametrize(
    "ident,source,message",
    SECURITY_BUILD_SOURCES,
    ids=[row[0] for row in SECURITY_BUILD_SOURCES],
)
def test_rejection_is_a_clean_diagnostic_not_a_crash(tmp_path, ident, source, message):
    """No compiler crash: exit code is the ordinary 1, never an NTSTATUS value."""
    _require_native()
    path = _write(tmp_path, f"{ident}_crash.vl", source)
    result = _check(path)
    blob = result.stdout + result.stderr
    assert result.returncode == 1, f"expected clean exit 1, got {result.returncode}\n{blob}"
    assert "Traceback" not in blob, blob
    assert message in blob, blob


def test_werror_build_has_no_unbound_jump_corpus(tmp_path):
    """Every invalid row is rejected before emission, so no C can be gcc-compiled."""
    _require_native()
    for ident, source, message, line in INVALID_ROWS:
        path = _write(tmp_path, f"werror_{ident}.vl", source)
        c_out = tmp_path / f"werror_{ident}.c"
        emitted = subprocess.run(
            [str(VELO_EXE), "emit-c", str(path), "-o", str(c_out)],
            capture_output=True, text=True, encoding="utf-8", timeout=120,
        )
        assert emitted.returncode != 0, f"{ident}: emit-c succeeded\n{emitted.stdout}{emitted.stderr}"
        assert not c_out.exists(), f"{ident}: translation unit written"


def test_error_message_assertions_are_exact(tmp_path):
    """Both wordings must be byte-exact so downstream tooling can match on them."""
    _require_native()
    break_path = _write(tmp_path, "wording_break.vl", """act main() {
    break
}
""")
    continue_path = _write(tmp_path, "wording_continue.vl", """act main() {
    continue
}
""")

    b = _check(break_path)
    assert b.returncode != 0
    assert "break statement not within a loop" in (b.stdout + b.stderr)
    assert "brk statement" not in (b.stdout + b.stderr)

    c = _check(continue_path)
    assert c.returncode != 0
    assert "continue statement not within a loop" in (c.stdout + c.stderr)


def test_specification_documents_the_rule():
    """Docs must state the rule generally, not only for `on` arms."""
    spec = (ROOT_DIR / "docs" / "SPECIFICATION.md").read_text(encoding="utf-8")
    assert "break statement not within a loop" in spec
    assert "continue statement not within a loop" in spec
    assert "semantic analysis" in spec
    assert "resets at every function boundary" in spec
    # The example block must show the non-`on` contexts too.
    assert "zone {" in spec
    assert "unsafe {" in spec


def test_specification_example_matches_compiler(tmp_path):
    """The §7.3 example 5/6 block must compile to exactly the annotated diagnostics."""
    _require_native()
    path = _write(tmp_path, "spec_ex5.vl", """act scan() {
    if true {
        break
    }
    {
        continue
    }
    zone {
        break
    }
    unsafe {
        continue
    }
    loop i in 0..3 {
        break
    }
    break
}

act count_down() {
    loop i in 0..3 { break }
}

act scan_again() {
    continue
}
""")
    result = _check(path, "--json")
    assert result.returncode != 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    seen = [(d["line"], d["col"], d["message"]) for d in report["diagnostics"]]

    assert seen == [
        (3, 9, BREAK),
        (6, 9, CONTINUE),
        (9, 9, BREAK),
        (12, 9, CONTINUE),
        (17, 5, BREAK),
        (25, 5, CONTINUE),
    ], seen
    # Line 15 (`break` inside the loop) must not be among them.
    assert not any(line == 15 for line, _, _ in seen), seen



