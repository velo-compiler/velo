"""
Task 79.5: Debug Build Story & Line Mapping Tests.

Verifies:
1. Emitted C preprocessor `#line` directives match exact source line numbers for functions and statements.
2. Multi-module compilation correctly attributes `#line` directives to each respective `.vl` file
   (st.current_file vs st.source_file attribution fix).
3. `--no-line-directives` cleanly suppresses all `#line` directives.
4. `velo build --debug` produces binary with DWARF symbols that GDB can load and resolve
   breakpoints at exact Velo source file lines.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
import pytest
from conftest import cc_dir, velo_exe

pytestmark = pytest.mark.fast

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()


def get_env():
    env = os.environ.copy()
    if cc_dir() not in env.get("PATH", ""):
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return env


def find_gdb():
    cand = shutil.which("gdb", path=get_env().get("PATH", ""))
    if cand:
        return cand
    for default_path in [
        r"C:\msys64\ucrt64\bin\gdb.exe",
        r"C:\msys64\mingw64\bin\gdb.exe",
        "/usr/bin/gdb",
        "/usr/local/bin/gdb",
    ]:
        if Path(default_path).is_file():
            return default_path
    return None


def test_emit_c_line_directives_match_source_lines(tmp_path):
    """Asserts that #line numbers in emit-c output match exact source lines."""
    src_file = tmp_path / "sample.vl"
    src_file.write_text(
        '// Line 1: comment\n'
        '// Line 2: comment\n'
        'act compute_sum(a: i32, b: i32) -> i32 {\n'  # Line 3
        '    let sum = a + b\n'                     # Line 4
        '    return sum\n'                          # Line 5
        '}\n'                                       # Line 6
        '\n'                                        # Line 7
        'act main() -> i32 {\n'                     # Line 8
        '    let x = 10\n'                          # Line 9
        '    let res = compute_sum(x, 20)\n'        # Line 10
        '    return 0\n'                            # Line 11
        '}\n',                                      # Line 12
        encoding="utf-8",
    )

    res = subprocess.run(
        [str(VELO_EXE), "emit-c", str(src_file)],
        capture_output=True,
        text=True,
        env=get_env(),
        cwd=str(REPO_ROOT),
    )
    assert res.returncode == 0, f"emit-c failed: {res.stderr}\n{res.stdout}"
    c_code = res.stdout

    # Verify line directives for compute_sum and main
    norm_path = str(src_file).replace("\\", "/")
    assert f'#line 3 "{norm_path}"' in c_code, "Missing #line 3 for compute_sum function entry"
    assert f'#line 4 "{norm_path}"' in c_code, "Missing #line 4 for let sum = a + b"
    assert f'#line 5 "{norm_path}"' in c_code, "Missing #line 5 for return sum"
    assert f'#line 8 "{norm_path}"' in c_code, "Missing #line 8 for main function entry"
    assert f'#line 9 "{norm_path}"' in c_code, "Missing #line 9 for let x = 10"
    assert f'#line 10 "{norm_path}"' in c_code, "Missing #line 10 for let res = compute_sum(x, 20)"
    assert f'#line 11 "{norm_path}"' in c_code, "Missing #line 11 for return 0"


def test_no_line_directives_flag(tmp_path):
    """Asserts that --no-line-directives suppresses all #line directives."""
    src_file = tmp_path / "noline.vl"
    src_file.write_text(
        'act main() -> i32 {\n'
        '    let a = 1\n'
        '    return 0\n'
        '}\n',
        encoding="utf-8",
    )

    res = subprocess.run(
        [str(VELO_EXE), "emit-c", str(src_file), "--no-line-directives"],
        capture_output=True,
        text=True,
        env=get_env(),
        cwd=str(REPO_ROOT),
    )
    assert res.returncode == 0
    assert "#line " not in res.stdout, "--no-line-directives must suppress #line directives"


def test_multi_file_line_directives_attribute_correct_files(tmp_path):
    """
    Asserts that in a multi-file project, #line directives for imported modules
    carry the module's file path, not the root main file's path.
    """
    sub_file = tmp_path / "submodule.vl"
    sub_file.write_text(
        'view act sub_calc(val: i32) -> i32 {\n'  # Line 1
        '    let doubled = val * 2\n'             # Line 2
        '    return doubled\n'                    # Line 3
        '}\n',
        encoding="utf-8",
    )

    main_file = tmp_path / "main_app.vl"
    main_file.write_text(
        'use "submodule.vl"\n'                    # Line 1
        'act main() -> i32 {\n'                   # Line 2
        '    let res = sub_calc(5)\n'             # Line 3
        '    return 0\n'                          # Line 4
        '}\n',
        encoding="utf-8",
    )

    res = subprocess.run(
        [str(VELO_EXE), "emit-c", str(main_file)],
        capture_output=True,
        text=True,
        env=get_env(),
        cwd=str(REPO_ROOT),
    )
    assert res.returncode == 0
    c_code = res.stdout

    norm_sub = str(sub_file).replace("\\", "/")
    norm_main = str(main_file).replace("\\", "/")

    # Submodule declarations and statements must point to submodule.vl
    assert f'#line 1 "{norm_sub}"' in c_code, "sub_calc must be attributed to submodule.vl"
    assert f'#line 2 "{norm_sub}"' in c_code, "submodule statements must be attributed to submodule.vl"

    # Main declarations and statements must point to main_app.vl
    assert f'#line 2 "{norm_main}"' in c_code, "main must be attributed to main_app.vl"
    assert f'#line 3 "{norm_main}"' in c_code, "main statements must be attributed to main_app.vl"


def test_gdb_breakpoint_resolution_on_velo_source_lines(tmp_path):
    """
    Builds with --debug and verifies that GDB successfully sets and hits
    breakpoints at exact Velo source file and line numbers.
    """
    gdb = find_gdb()
    if not gdb:
        pytest.skip("GDB not found on system PATH or standard locations")

    src_file = tmp_path / "debug_target.vl"
    src_file.write_text(
        'use std.io\n'                            # Line 1
        'act compute_answer() -> i32 {\n'        # Line 2
        '    let factor1 = 6\n'                   # Line 3
        '    let factor2 = 7\n'                   # Line 4
        '    return factor1 * factor2\n'          # Line 5
        '}\n'                                     # Line 6
        'act main() -> i32 {\n'                   # Line 7
        '    let ans = compute_answer()\n'        # Line 8
        '    return 0\n'                          # Line 9
        '}\n',
        encoding="utf-8",
    )

    out_exe = tmp_path / "debug_target.exe"

    # 1. Build binary with --debug
    build_res = subprocess.run(
        [str(VELO_EXE), "build", str(src_file), "-o", str(out_exe), "--debug"],
        capture_output=True,
        text=True,
        env=get_env(),
        cwd=str(REPO_ROOT),
    )
    assert build_res.returncode == 0, f"Build --debug failed: {build_res.stderr}\n{build_res.stdout}"
    assert out_exe.is_file()

    # 2. Run GDB session setting breakpoint at Line 4: let factor2 = 7
    norm_src = str(src_file).replace("\\", "/")
    gdb_cmd = [
        str(gdb),
        "--batch",
        "-ex", f"break {norm_src}:4",
        "-ex", "run",
        "-ex", "info line",
        "-ex", "continue",
        str(out_exe),
    ]

    gdb_res = subprocess.run(
        gdb_cmd,
        capture_output=True,
        text=True,
        env=get_env(),
        cwd=str(REPO_ROOT),
    )
    assert gdb_res.returncode == 0, f"GDB run failed: {gdb_res.stderr}\n{gdb_res.stdout}"

    # Assert that GDB resolved and hit breakpoint at debug_target.vl line 4
    output = gdb_res.stdout
    assert "Breakpoint 1" in output
    assert "Line 4 of" in output or "line 4" in output
    assert "factor2 = 7" in output
