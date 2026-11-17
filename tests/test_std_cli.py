import os
import subprocess
import pytest
from pathlib import Path
from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()

def get_env():
    env = os.environ.copy()
    if cc_dir() not in env.get("PATH", ""):
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return env

def test_std_cli_help():
    test_vl = REPO_ROOT / "std" / "tests" / "cli" / "help_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "OK: std.cli help tests passed\n" in res.stdout
    # Task 52.6: stderr routing and stream separation
    assert "unknown flag '--bogus'\n" in res.stderr
    assert "  while processing token '--bogus'\n" in res.stderr
    assert "Run 'app --help' for usage.\n" in res.stderr
    assert "unknown flag" not in res.stdout
    assert "--bogus" not in res.stdout


def test_std_cli_error_path_captures_stderr_with_newline_and_clean_stdout(tmp_path):
    """Task 52.6: CLI error path captures stdout and stderr separately.

    Security gate: errors must not leak to stdout where a caller may parse it
    as machine-readable data, and each error line must end with a newline.
    """
    source = (
        "use std.cli\n"
        "use std.mem\n"
        "use std.os\n"
        "use std.io\n\n"
        "act main() -> i32 {\n"
        "    mut arena = arena_init(4096)\n"
        "    defer arena_reset(@arena)\n"
        '    let args_val = os_tokenize_cmdline(@arena, "mytool --invalid-opt")\n'
        "    let d: @Args = null\n"
        "    let args_ptr = arena_alloc_zeroed(@arena, (d + 1) as usize, 8) as @Args\n"
        "    args_ptr.count = args_val.count\n"
        "    args_ptr.items = args_val.items\n"
        "    args_ptr.raw = args_val.raw\n"
        "    mut p = cli_parser_init(@arena, args_ptr)\n"
        '    cli_parser_program(@p, "mytool", "demonstration utility")\n'
        "    let ok = cli_parse(@p)\n"
        "    if !ok {\n"
        "        cli_print_error(@p)\n"
        "        return 1\n"
        "    }\n"
        '    io.println_str("UNREACHABLE_DATA")\n'
        "    return 0\n"
        "}\n"
    )
    probe = tmp_path / "cli_error_isolation.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")

    res = subprocess.run(
        [str(VELO_EXE), "run", str(probe)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 1, f"expected returncode 1, got {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert res.stdout == "", f"stdout leaked error text or data:\n{res.stdout!r}"
    assert res.stderr.endswith("\n"), f"stderr does not end with a newline:\n{res.stderr!r}"
    assert (
        res.stderr == (
            "unknown flag '--invalid-opt'\n"
            "  while processing token '--invalid-opt'\n"
            "Run 'mytool --help' for usage.\n"
        )
    ), f"stderr mismatch:\n{res.stderr!r}"


def test_std_cli_parse():
    test_vl = REPO_ROOT / "std" / "tests" / "cli" / "parse_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "OK: std.cli parse tests passed" in res.stdout

def test_std_cli_module_import():
    test_vl = REPO_ROOT / "std" / "tests" / "cli_module_import_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.cli umbrella import all tests passed" in res.stdout

