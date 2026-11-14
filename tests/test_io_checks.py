"""Phase 52, Task 52.2: closed-set checks for the io.* namespace.

The checker must accept exactly the members declared by std/io/print.vl and
reject every other io.* member with a diagnostic that lists the valid set.
This test drives the checker with one call per declared member, using
signature-correct arguments so the same table survives Task 52.3's arity and
type walls.
"""
import os
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = REPO_ROOT / "bin" / "velo.exe"


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
    "eprint": '"x"',
    "eprintln": '"x"',
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
