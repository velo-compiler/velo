"""Phase 52: closed-set, arity, type, and result-spell checks for io.*.

Task 52.2 pins the member allowlist: the checker must accept exactly the
members declared by std/io/print.vl and reject every other io.* member with a
diagnostic that lists the valid set. Task 52.3 adds the per-member arity and
argument-type walls plus the precise result spells (void, bool, handles).
"""
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = REPO_ROOT / "bin" / "velo.exe"
CONFORMANCE_VL = REPO_ROOT / "std" / "tests" / "io" / "print_api_conformance_test.vl"


def get_env():
    env = os.environ.copy()
    if r"C:\msys64\ucrt64\bin" not in env.get("PATH", ""):
        env["PATH"] = r"C:\msys64\ucrt64\bin;" + env.get("PATH", "")
    return env


# One row per top-level act declared in std/io/print.vl. The value is the
# argument list used by the acceptance probe. Keep this table in sync with the
# file; the diagnostic test below also asserts every name is published.
IO_MEMBER_ARGS = {
    # Standard output (print / println)
    "print": '"x"',
    "println": '"x"',
    "print_str": '"x"',
    "println_str": '"x"',
    "println_empty": "",
    "print_byte": "0 as u8",
    "println_byte": "0 as u8",
    "print_i64": "0 as i64",
    "println_i64": "0 as i64",
    "print_u64": "0 as u64",
    "println_u64": "0 as u64",
    "print_f64": "0.0 as f64, 0 as i32",
    "println_f64": "0.0 as f64, 0 as i32",
    "print_bool": "true",
    "println_bool": "true",
    # Standard error (eprint / eprintln)
    "eprint": "s",
    "eprintln": "s",
    "eprint_str": '"x"',
    "eprintln_str": '"x"',
    "eprintln_empty": "",
    "eprint_byte": "0 as u8",
    "eprintln_byte": "0 as u8",
    "eprint_i64": "0 as i64",
    "eprintln_i64": "0 as i64",
    "eprint_u64": "0 as u64",
    "eprintln_u64": "0 as u64",
    "eprint_f64": "0.0 as f64, 0 as i32",
    "eprintln_f64": "0.0 as f64, 0 as i32",
    "eprint_bool": "true",
    "eprintln_bool": "true",
    # Generic stream API (fprint / fprintln)
    "fprint": "w, s",
    "fprintln": "w, s",
    "fprint_str": 'w, "x"',
    "fprintln_str": 'w, "x"',
    "fprintln_empty": "w",
    "fprint_byte": "w, 0 as u8",
    "fprintln_byte": "w, 0 as u8",
    "fprint_i64": "w, 0 as i64",
    "fprintln_i64": "w, 0 as i64",
    "fprint_u64": "w, 0 as u64",
    "fprintln_u64": "w, 0 as u64",
    "fprint_f64": "w, 0.0 as f64, 0 as i32",
    "fprintln_f64": "w, 0.0 as f64, 0 as i32",
    "fprint_bool": "w, true",
    "fprintln_bool": "w, true",
    # Lifecycle helpers (also top-level acts in print.vl)
    "io_ensure_atexit": "",
    "io_get_stdout_writer": "",
    "io_get_stderr_writer": "",
    "io_get_fmt_buf": "",
    "io_flush_stdout": "",
    "io_flush_stderr": "",
    "io_flush_all": "",
    "io_print_cleanup": "",
}


def run_check(source, tmp_path, name):
    probe = tmp_path / name
    probe.write_text(source, encoding="utf-8", newline="\n")
    return subprocess.run(
        [str(VELO_EXE), "check", str(probe)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
    )


def test_io_closed_set_accepts_every_declared_member(tmp_path):
    lines = [
        "use std.io",
        "use std.str.slice",
        "",
        "act main() {",
        '    let s = slice_from_str("x")',
        "    let w = io_get_stdout_writer()",
    ]
    for member, args in IO_MEMBER_ARGS.items():
        lines.append(f"    io.{member}({args})")
    lines.append("}")
    source = "\n".join(lines) + "\n"

    res = run_check(source, tmp_path, "io_all_members.vl")
    assert res.returncode == 0, (
        "velo check rejected a declared io member:\n"
        f"stdout: {res.stdout}\nstderr: {res.stderr}"
    )


def test_io_unknown_member_rejected_and_lists_valid_members(tmp_path):
    source = "use std.io\n\nact main() {\n    io.does_not_exist()\n}\n"
    res = run_check(source, tmp_path, "io_unknown_member.vl")

    assert res.returncode != 0, (
        "velo check accepted an unknown io member:\n"
        f"stdout: {res.stdout}\nstderr: {res.stderr}"
    )
    combined = res.stdout + res.stderr
    assert "unknown io member 'does_not_exist'" in combined, (
        f"missing closed-set diagnostic:\n{combined}"
    )
    listed_match = re.search(r"\(functions: (.*)\)", combined)
    assert listed_match is not None, f"diagnostic has no member list:\n{combined}"
    listed = [name.strip() for name in listed_match.group(1).split(",")]
    assert len(listed) == len(set(listed)), f"duplicate names in diagnostic:\n{combined}"
    assert set(listed) == set(IO_MEMBER_ARGS), (
        "diagnostic list does not match the accepted set:\n"
        f"missing: {sorted(set(IO_MEMBER_ARGS) - set(listed))}\n"
        f"extra: {sorted(set(listed) - set(IO_MEMBER_ARGS))}"
    )


def test_io_unknown_member_with_argument_rejected(tmp_path):
    source = "use std.io\n\nact main() {\n    io.also_missing(123)\n}\n"
    res = run_check(source, tmp_path, "io_unknown_member_arg.vl")

    assert res.returncode != 0, (
        "velo check accepted an unknown io member with an argument:\n"
        f"stdout: {res.stdout}\nstderr: {res.stderr}"
    )
    assert "also_missing" in (res.stdout + res.stderr)


# ---------------------------------------------------------------------------
# Task 52.3: arity and argument-type walls.
# ---------------------------------------------------------------------------

ARITY_REJECTS = [
    # The intrinsic accepts zero or one argument, never two.
    'io.println("a", "b")',
    'io.print("a", "b")',
    # One-argument stdlib members.
    "io.println_str()",
    'io.println_str("a", "b")',
    "io.print_str()",
    "io.println_empty(1)",
    "io.print_byte()",
    # Two-argument members.
    "io.print_f64(1.0)",
    "io.print_f64(1.0, 2, 3)",
    # Three-argument members.
    "io.fprint()",
    "io.fprint_str(w)",
    'io.fprint_str(w, "x", "y")',
    "io.fprintln_empty(w, w)",
]


@pytest.mark.parametrize("call", ARITY_REJECTS)
def test_io_arity_mismatch_rejected(call, tmp_path):
    source = (
        "use std.io\n\n"
        "act main() {\n"
        "    let w = io_get_stdout_writer()\n"
        f"    {call}\n"
        "}\n"
    )
    res = run_check(source, tmp_path, "io_arity.vl")

    assert res.returncode != 0, (
        f"velo check accepted an arity mismatch: {call}\n"
        f"stdout: {res.stdout}\nstderr: {res.stderr}"
    )
    combined = res.stdout + res.stderr
    assert "expects" in combined and "argument" in combined, (
        f"diagnostic does not mention the argument mismatch:\n{combined}"
    )
    assert call.split("(", 1)[0].split(".", 1)[1] in combined, (
        f"diagnostic does not name the member in {call}:\n{combined}"
    )


TYPE_REJECTS = [
    # String positions accept exactly string.
    ("io.println_str(123)", "expects string (got i32)"),
    ("io.println_str(true)", "expects string (got bool)"),
    ("io.fprint_str(w, 123)", "expects string (got i32)"),
    # u8 byte positions reject bool/float and out-of-range literals.
    ("io.print_byte(true)", "expects u8 (got bool)"),
    ("io.print_byte(1.5)", "expects u8 (got f32)"),
    ("io.print_byte(256)", "out of range for type 'u8'"),
    ("io.print_byte(-1)", "out of range for type 'u8'"),
    # i64 positions reject float/bool; no implicit float->int.
    ("io.print_i64(1.5)", "expects i64 (got f32)"),
    ("io.print_i64(true)", "expects i64 (got bool)"),
    # u64 positions reject negative literals (no wrap).
    ("io.print_u64(-1)", "out of range for type 'u64'"),
    # f64 positions reject ints (no implicit int->float at the io boundary).
    ("io.print_f64(1, 2)", "expects f64 (got i32)"),
    ("io.print_f64(1.0, true)", "expects i32 (got bool)"),
    ("io.fprint_f64(w, \"x\", 2)", "expects f64 (got string)"),
    ("io.fprint_f64(w, 1.0, true)", "expects i32 (got bool)"),
    # bool positions reject ints (no implicit bool<->int).
    ("io.print_bool(1)", "expects bool (got i32)"),
    # The stream handle is its own type.
    ('io.fprint_str("not a writer", "x")', "expects @BufferedWriter (got string)"),
]


@pytest.mark.parametrize("call,expected", TYPE_REJECTS)
def test_io_wrong_argument_type_rejected(call, expected, tmp_path):
    source = (
        "use std.io\n\n"
        "act main() {\n"
        "    let w = io_get_stdout_writer()\n"
        f"    {call}\n"
        "}\n"
    )
    res = run_check(source, tmp_path, "io_type.vl")

    assert res.returncode != 0, (
        f"velo check accepted a wrong argument type: {call}\n"
        f"stdout: {res.stdout}\nstderr: {res.stderr}"
    )
    combined = res.stdout + res.stderr
    assert expected in combined, (
        f"diagnostic for {call} does not contain {expected!r}:\n{combined}"
    )


def test_io_unsuffixed_literals_adapt_at_the_boundary(tmp_path):
    """In-range unsuffixed literals adapt; the walls stay explicit casts."""
    source = (
        "use std.io\n\n"
        "act main() {\n"
        "    io.print_byte(65)\n"
        "    io.println_i64(-42)\n"
        "    io.print_u64(42)\n"
        "    io.print_f64(3.14159, 2)\n"
        "    io.print_bool(true)\n"
        "}\n"
    )
    res = run_check(source, tmp_path, "io_literal_adapt.vl")

    assert res.returncode == 0, (
        "velo check rejected in-range unsuffixed literals:\n"
        f"stdout: {res.stdout}\nstderr: {res.stderr}"
    )


def test_io_intrinsics_accept_zero_or_one_value(tmp_path):
    """print/println stay value-formatting intrinsics (zero or one arg)."""
    source = (
        "use std.io\n\n"
        "act main() {\n"
        "    io.println()\n"
        "    io.print()\n"
        "    io.println(123)\n"
        "    io.print(true)\n"
        "    io.println(3.5)\n"
        "}\n"
    )
    res = run_check(source, tmp_path, "io_intrinsic_values.vl")

    assert res.returncode == 0, (
        "velo check rejected a valid intrinsic call:\n"
        f"stdout: {res.stdout}\nstderr: {res.stderr}"
    )


# ---------------------------------------------------------------------------
# Task 52.3: result spells (void vs bool vs handles).
# ---------------------------------------------------------------------------


def test_io_result_spells_are_precise(tmp_path):
    source = (
        "use std.io\n\n"
        "act main() {\n"
        "    let ok_out: bool = io.io_flush_stdout()\n"
        "    let ok_err: bool = io.io_flush_stderr()\n"
        "    let ok_all: bool = io.io_flush_all()\n"
        "    let w_out: @BufferedWriter = io.io_get_stdout_writer()\n"
        "    let w_err: @BufferedWriter = io.io_get_stderr_writer()\n"
        "    let fmt_buf: @u8 = io.io_get_fmt_buf()\n"
        "    io.io_ensure_atexit()\n"
        "    io.io_print_cleanup()\n"
        "}\n"
    )
    res = run_check(source, tmp_path, "io_result_types.vl")

    assert res.returncode == 0, (
        "velo check rejected a correct result-spell annotation:\n"
        f"stdout: {res.stdout}\nstderr: {res.stderr}"
    )


RESULT_REJECTS = [
    "let bad: i32 = io.io_flush_stdout()",
    "let bad: bool = io.io_get_stdout_writer()",
    "let bad: i32 = io.io_get_fmt_buf()",
    'let bad: bool = io.println_str("x")',
    "let bad: i32 = io.io_print_cleanup()",
]


@pytest.mark.parametrize("decl", RESULT_REJECTS)
def test_io_wrong_result_spell_rejected(decl, tmp_path):
    source = f"use std.io\n\nact main() {{\n    {decl}\n}}\n"
    res = run_check(source, tmp_path, "io_result_mismatch.vl")

    assert res.returncode != 0, (
        f"velo check accepted a wrong result annotation: {decl}\n"
        f"stdout: {res.stdout}\nstderr: {res.stderr}"
    )
    assert "Type mismatch in variable declaration" in (res.stdout + res.stderr), (
        f"diagnostic does not report the declaration mismatch:\n{res.stdout}{res.stderr}"
    )


def test_io_conformance_program_checks_clean():
    """Every call in the Phase 52.1 matrix must pass the semantic walls."""
    res = subprocess.run(
        [str(VELO_EXE), "check", str(CONFORMANCE_VL)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
    )
    assert res.returncode == 0, (
        "velo check rejected the io.* conformance program:\n"
        f"stdout: {res.stdout}\nstderr: {res.stderr}"
    )
