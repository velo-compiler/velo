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


