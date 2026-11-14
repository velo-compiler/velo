import os
import re
import subprocess
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = REPO_ROOT / "bin" / "velo.exe"

CONFORMANCE_VL = REPO_ROOT / "std" / "tests" / "io" / "print_api_conformance_test.vl"

CONFORMANCE_STDOUT = (
    "print_str|println_str\n"
    "AB\n"
    "-42-43\n"
    "1844674407370955161518446744073709551615\n"
    "3.142.718\n"
    "truefalse\n"
    "\n"
    "%s %n {not_interpolated}\n"
)

CONFORMANCE_STDERR = (
    "eprint_str|eprintln_str\n"
    "CD\n"
    "-44-45\n"
    "1844674407370955161518446744073709551615\n"
    "1.251.5\n"
    "falsetrue\n"
    "\n"
    "%s %n {not_interpolated}\n"
)

def get_env():
    env = os.environ.copy()
    if r"C:\msys64\ucrt64\bin" not in env.get("PATH", ""):
        env["PATH"] = r"C:\msys64\ucrt64\bin;" + env.get("PATH", "")
    return env

def test_std_io_handle():
    test_vl = REPO_ROOT / "std" / "tests" / "io" / "handle_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.io.handle all assertions succeeded" in res.stdout

def test_std_io_buffered_writer():
    test_vl = REPO_ROOT / "std" / "tests" / "io" / "buffered_writer_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.io.buffered_writer all assertions succeeded" in res.stdout

def test_std_io_print():
    test_vl = REPO_ROOT / "std" / "tests" / "io" / "print_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.io.print all assertions succeeded" in res.stdout

def test_std_io_print_integration():
    test_vl = REPO_ROOT / "std" / "tests" / "io" / "print_integration_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "STD_IO_PRINT_OK" in res.stdout
    assert "123456" in res.stdout
    assert "3.14" in res.stdout
    assert "true" in res.stdout
    assert "STD_IO_EPRINT_OK" in res.stderr

def test_std_io_buffered_reader():
    test_vl = REPO_ROOT / "std" / "tests" / "io" / "buffered_reader_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.io.buffered_reader all assertions succeeded" in res.stdout

def test_std_io_print_exit_flush():
    test_vl = REPO_ROOT / "std" / "tests" / "io" / "print_exit_flush_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "UNFLUSHED_STDOUT_DATA" in res.stdout
    assert "UNFLUSHED_STDERR_DATA" in res.stderr


# ---------------------------------------------------------------------------
# Phase 52, Task 52.1: io.* printing API conformance matrix (red baseline).
#
# These tests encode the behavior the io.* prefix must expose. They fail on
# the current wildcard dispatch: only print/println reach the intrinsic, every
# other member falls through to generic value printing (no newline, no stderr
# routing, signed u64, ignored f64 precision).
# ---------------------------------------------------------------------------


def run_velo(args, cwd=REPO_ROOT):
    return subprocess.run(
        [str(VELO_EXE), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env()
    )


def bare_conformance_source():
    """Return the conformance program with the io. prefix stripped."""
    source = CONFORMANCE_VL.read_text(encoding="utf-8")
    return re.sub(r"(?m)^([ \t]*)io\.", r"\1", source)


def test_std_io_bare_print_api_conformance_control(tmp_path):
    """Control: the unqualified stdlib API already meets the matrix."""
    bare = tmp_path / "bare_print_api_conformance.vl"
    bare.write_text(bare_conformance_source(), encoding="utf-8", newline="\n")

    res = run_velo(["run", str(bare)])
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert res.stdout == CONFORMANCE_STDOUT, f"stdout mismatch:\n{res.stdout!r}"
    assert res.stderr == CONFORMANCE_STDERR, f"stderr mismatch:\n{res.stderr!r}"


def test_std_io_prefix_print_api_conformance():
    """io.X must behave like the stdlib X for every printing member."""
    res = run_velo(["run", str(CONFORMANCE_VL)])
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert res.stdout == CONFORMANCE_STDOUT, f"stdout mismatch:\n{res.stdout!r}"
    assert res.stderr == CONFORMANCE_STDERR, f"stderr mismatch:\n{res.stderr!r}"


def test_std_io_prefix_matches_bare_parity(tmp_path):
    """Byte-for-byte parity between io.X and unqualified X."""
    bare = tmp_path / "bare_print_api_parity.vl"
    bare.write_text(bare_conformance_source(), encoding="utf-8", newline="\n")

    prefix = run_velo(["run", str(CONFORMANCE_VL)])
    plain = run_velo(["run", str(bare)])
    assert prefix.returncode == 0, f"io.* run failed:\n{prefix.stderr}\n{prefix.stdout}"
    assert plain.returncode == 0, f"bare run failed:\n{plain.stderr}\n{plain.stdout}"
    assert prefix.stdout == plain.stdout, f"stdout parity mismatch:\nio:   {prefix.stdout!r}\nbare: {plain.stdout!r}"
    assert prefix.stderr == plain.stderr, f"stderr parity mismatch:\nio:   {prefix.stderr!r}\nbare: {plain.stderr!r}"


@pytest.mark.parametrize("call", [
    "io.does_not_exist(123)",
    "io.also_missing()",
])
def test_std_io_prefix_rejects_unknown_member(call, tmp_path):
    source = f"use std.io\n\nact main() {{\n    {call}\n}}\n"
    probe = tmp_path / "unknown_member.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")

    res = run_velo(["check", str(probe)])
    assert res.returncode != 0, (
        f"velo check accepted an unknown io member: {call}\n"
        f"stdout: {res.stdout}\nstderr: {res.stderr}"
    )
    combined = (res.stdout + res.stderr).lower()
    member = call.split("(", 1)[0].split(".", 1)[1]
    assert member in combined, f"diagnostic does not name '{member}':\n{res.stdout}{res.stderr}"


@pytest.mark.parametrize("call", [
    'io.println("a", "b")',
    "io.println_str()",
    'io.println_str("a", "b")',
])
def test_std_io_prefix_rejects_arity_mismatch(call, tmp_path):
    source = f"use std.io\n\nact main() {{\n    {call}\n}}\n"
    probe = tmp_path / "arity_mismatch.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")

    res = run_velo(["check", str(probe)])
    assert res.returncode != 0, (
        f"velo check accepted an arity mismatch: {call}\n"
        f"stdout: {res.stdout}\nstderr: {res.stderr}"
    )
    combined = (res.stdout + res.stderr).lower()
    assert "argument" in combined or "arity" in combined, (
        f"diagnostic does not mention the argument mismatch:\n{res.stdout}{res.stderr}"
    )


def test_std_io_prefix_printf_metacharacters_are_data(tmp_path):
    """User text must never become a printf format string."""
    source = (
        "use std.io\n\n"
        "act main() {\n"
        '    io.println("%s %n")\n'
        '    io.println_str("%s %n {not_interpolated}")\n'
        "}\n"
    )
    probe = tmp_path / "printf_metacharacters.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")

    res = run_velo(["run", str(probe)])
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert res.stdout == "%s %n\n%s %n {not_interpolated}\n", f"stdout mismatch:\n{res.stdout!r}"
    assert res.stderr == "", f"stderr mismatch:\n{res.stderr!r}"


# ---------------------------------------------------------------------------
# Phase 52, Task 52.4: codegen dispatch boundary.
#
# Only the exact intrinsics print/println may lower through emit_io_call.
# Every other member is a normal stdlib act and must appear in the emitted C
# as a call to its real symbol, never as a printf hijack and never with the
# namespace identifier passed as a receiver.
# ---------------------------------------------------------------------------


def emit_c(tmp_path, source, stem):
    probe = tmp_path / f"{stem}.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")
    out_c = tmp_path / f"{stem}.c"
    res = run_velo(["emit-c", str(probe), "-o", str(out_c)])
    return res, out_c


def main_body(c_source):
    match = re.search(r"int main\([^)]*\) \{(.*?)\n\}", c_source, re.S)
    assert match, f"generated C has no main body:\n{c_source[:2000]}"
    return match.group(1)


def test_std_io_non_intrinsics_emit_real_stdlib_calls(tmp_path):
    source = (
        "use std.io\n\n"
        "act main() {\n"
        '    io.println_str("hello")\n'
        '    io.eprintln_str("oops")\n'
        "    io.println_u64(18446744073709551615u64)\n"
        "    io.print_f64(3.5, 2)\n"
        "}\n"
    )
    res, out_c = emit_c(tmp_path, source, "io_dispatch")
    assert res.returncode == 0, f"emit-c failed:\n{res.stderr}\n{res.stdout}"

    body = main_body(out_c.read_text(encoding="utf-8"))
    assert 'println_str("hello")' in body, f"println_str was not emitted:\n{body}"
    assert 'eprintln_str("oops")' in body, f"eprintln_str was not emitted:\n{body}"
    assert "println_u64(" in body, f"println_u64 was not emitted:\n{body}"
    assert "print_f64(" in body, f"print_f64 was not emitted:\n{body}"
    assert "printf" not in body, f"non-intrinsic io member was hijacked by printf:\n{body}"
    assert "println_str(io" not in body, f"namespace identifier passed as a receiver:\n{body}"
    assert "eprintln_str(io" not in body, f"namespace identifier passed as a receiver:\n{body}"


def test_std_io_intrinsics_still_lower_through_emit_io_call(tmp_path):
    source = (
        "use std.io\n\n"
        "act main() {\n"
        '    io.print("raw")\n'
        '    io.println("line")\n'
        "}\n"
    )
    res, out_c = emit_c(tmp_path, source, "io_intrinsic_dispatch")
    assert res.returncode == 0, f"emit-c failed:\n{res.stderr}\n{res.stdout}"

    body = main_body(out_c.read_text(encoding="utf-8"))
    assert "printf" in body, f"intrinsic io.print/io.println lost the printf path:\n{body}"
    assert "println_str(" not in body, f"intrinsic println resolved to the stdlib act:\n{body}"


def test_std_io_unknown_member_never_reaches_codegen(tmp_path):
    source = "use std.io\n\nact main() {\n    io.does_not_exist(123)\n}\n"
    res, out_c = emit_c(tmp_path, source, "io_unknown_dispatch")
    assert res.returncode != 0, "emit-c accepted an unknown io member"
    assert not out_c.exists() or out_c.read_text(encoding="utf-8").strip() == "", (
        f"unknown io member produced C output:\n{out_c.read_text(encoding='utf-8')}"
    )


def test_std_io_stdlib_member_without_import_fails_loudly(tmp_path):
    """Defense-in-depth: if semantic analysis accepts a call whose symbol is missing, codegen fails."""
    source = 'act main() {\n    io.println_str("hello")\n}\n'
    res, out_c = emit_c(tmp_path, source, "io_no_import")
    assert res.returncode != 0, "emit-c accepted io.println_str without use std.io"
    combined = (res.stdout + res.stderr).lower()
    assert "unknown io member" in combined or "reached codegen" in combined, (
        f"did not report missing symbol at codegen:\n{res.stdout}\n{res.stderr}"
    )


# ---------------------------------------------------------------------------
# Phase 52, Task 52.5: Harden the print/println intrinsic.
#
# - Exact arity enforcement (zero or one argument; reject extra arguments).
# - Format injection defense: format strings are always compiler-owned constants;
#   user text and format directives (%s, %n) are emitted as data, never format.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("call", [
    'io.println("a", "b")',
    'io.print("a", "b")',
    'io.println("a", "b", "c")',
])
def test_std_io_intrinsic_arity_rejected(call, tmp_path):
    source = f"use std.io\n\nact main() {{\n    {call}\n}}\n"
    probe = tmp_path / "intrinsic_arity.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")

    res = run_velo(["check", str(probe)])
    assert res.returncode != 0, f"check accepted extra intrinsic arguments: {call}"
    combined = (res.stdout + res.stderr).lower()
    assert "argument" in combined, f"diagnostic did not mention argument count: {combined}"

    res_emit = run_velo(["emit-c", str(probe)])
    assert res_emit.returncode != 0, f"emit-c accepted extra intrinsic arguments: {call}"


def test_std_io_intrinsic_literal_percent_directives_printed_as_data(tmp_path):
    source = (
        "use std.io\n\n"
        "act main() {\n"
        '    io.println("%n")\n'
        '    io.print("%n")\n'
        '    io.println("%s %n")\n'
        "}\n"
    )
    probe = tmp_path / "literal_percent.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")

    res = run_velo(["run", str(probe)])
    assert res.returncode == 0, f"run failed:\n{res.stderr}\n{res.stdout}"
    assert res.stdout == "%n\n%n%s %n\n", f"stdout mismatch:\n{res.stdout!r}"


def test_std_io_intrinsic_interpolated_format_directives_printed_as_data(tmp_path):
    source = (
        "use std.io\n\n"
        "act main() {\n"
        "    let x = 42\n"
        '    io.println("data: %n {x}")\n'
        '    io.println("%n {x} %s")\n'
        "}\n"
    )
    probe = tmp_path / "interp_percent.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")

    res = run_velo(["run", str(probe)])
    assert res.returncode == 0, f"run failed:\n{res.stderr}\n{res.stdout}"
    assert res.stdout == "data: %n 42\n%n 42 %s\n", f"stdout mismatch:\n{res.stdout!r}"


def test_std_io_intrinsic_unresolved_interp_percent_n_does_not_inject(tmp_path):
    source = (
        "use std.io\n\n"
        "act main() {\n"
        "    let x = 42\n"
        '    io.println("unresolved: {%n} {x}")\n'
        "}\n"
    )
    probe = tmp_path / "unresolved_percent.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")

    res = run_velo(["run", str(probe)])
    assert res.returncode == 0, f"run failed:\n{res.stderr}\n{res.stdout}"
    assert res.stdout == "unresolved: {%n} 42\n", f"stdout mismatch:\n{res.stdout!r}"


def test_std_io_intrinsic_variable_format_directives_printed_as_data(tmp_path):
    source = (
        "use std.io\n\n"
        "act main() {\n"
        '    let s = "%n%s%x"\n'
        "    io.println(s)\n"
        '    io.println("User: {s}")\n'
        "}\n"
    )
    probe = tmp_path / "var_percent.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")

    res = run_velo(["run", str(probe)])
    assert res.returncode == 0, f"run failed:\n{res.stderr}\n{res.stdout}"
    assert res.stdout == "%n%s%x\nUser: %n%s%x\n", f"stdout mismatch:\n{res.stdout!r}"


def test_std_io_intrinsic_zero_arg(tmp_path):
    source = (
        "use std.io\n\n"
        "act main() {\n"
        "    io.print()\n"
        "    io.println()\n"
        "}\n"
    )
    probe = tmp_path / "zero_arg.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")

    res = run_velo(["run", str(probe)])
    assert res.returncode == 0, f"run failed:\n{res.stderr}\n{res.stdout}"
    assert res.stdout == "\n", f"stdout mismatch:\n{res.stdout!r}"




