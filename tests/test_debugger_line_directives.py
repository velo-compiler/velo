import os
import sys
import shutil
import subprocess
from pathlib import Path
import pytest
from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).resolve().parent.parent
VELO_PY = REPO_ROOT / "velo.py"
VELO_EXE = velo_exe()


def get_env():
    env = os.environ.copy()
    env["PATH"] = f"{REPO_ROOT};{REPO_ROOT / 'bin'};" + env.get("PATH", "") + os.pathsep + cc_dir()
    return env


def test_emit_c_contains_line_directives_stage1(tmp_path):
    source_file = tmp_path / "sample.vl"
    source_file.write_text(
        "use sys.io\n"
        "act calculate(a: i32, b: i32) -> i32 {\n"
        "    let x = a + 1\n"
        "    let y = b * 2\n"
        "    return x + y\n"
        "}\n"
        "act main() {\n"
        "    let res = calculate(10, 20)\n"
        "    io.println(\"res: {res}\")\n"
        "}\n",
        encoding="utf-8"
    )

    res = subprocess.run(
        [sys.executable, str(VELO_PY), "emit-c", str(source_file)],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(REPO_ROOT),
        env=get_env()
    )

    norm_path = str(source_file).replace("\\", "/")
    assert f'#line 2 "{norm_path}"' in res.stdout
    assert f'#line 3 "{norm_path}"' in res.stdout
    assert f'#line 4 "{norm_path}"' in res.stdout
    assert f'#line 5 "{norm_path}"' in res.stdout
    assert f'#line 7 "{norm_path}"' in res.stdout
    assert f'#line 8 "{norm_path}"' in res.stdout
    assert f'#line 9 "{norm_path}"' in res.stdout
    # Ensure forward slash normalization (no Windows backslash in #line path)
    assert "\\" not in [line for line in res.stdout.splitlines() if line.startswith("#line")][0]


def test_emit_c_contains_line_directives_stage2(tmp_path):
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    source_file = tmp_path / "sample_s2.vl"
    source_file.write_text(
        "use sys.io\n"
        "act calculate(a: i32, b: i32) -> i32 {\n"
        "    let x = a + 1\n"
        "    let y = b * 2\n"
        "    return x + y\n"
        "}\n"
        "act main() {\n"
        "    let res = calculate(10, 20)\n"
        "    io.println(\"res: {res}\")\n"
        "}\n",
        encoding="utf-8"
    )

    res = subprocess.run(
        [str(VELO_EXE), "emit-c", str(source_file)],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(REPO_ROOT),
        env=get_env()
    )

    norm_path = str(source_file).replace("\\", "/")
    assert f'#line 2 "{norm_path}"' in res.stdout
    assert f'#line 3 "{norm_path}"' in res.stdout
    assert f'#line 4 "{norm_path}"' in res.stdout
    assert f'#line 5 "{norm_path}"' in res.stdout
    assert f'#line 7 "{norm_path}"' in res.stdout
    assert f'#line 8 "{norm_path}"' in res.stdout
    assert f'#line 9 "{norm_path}"' in res.stdout
    assert "\\" not in [line for line in res.stdout.splitlines() if line.startswith("#line")][0]


def test_no_line_directives_flag_stage1(tmp_path):
    source_file = tmp_path / "clean_s1.vl"
    source_file.write_text(
        "act main() {\n"
        "    let x = 42\n"
        "}\n",
        encoding="utf-8"
    )

    res = subprocess.run(
        [sys.executable, str(VELO_PY), "emit-c", "--no-line-directives", str(source_file)],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(REPO_ROOT),
        env=get_env()
    )

    assert "#line" not in res.stdout
    assert "int main(int argc, char** argv) {" in res.stdout
    assert "x = 42;" in res.stdout


def test_no_line_directives_flag_stage2(tmp_path):
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    source_file = tmp_path / "clean_s2.vl"
    source_file.write_text(
        "act main() {\n"
        "    let x = 42\n"
        "}\n",
        encoding="utf-8"
    )

    res = subprocess.run(
        [str(VELO_EXE), "emit-c", "--no-line-directives", str(source_file)],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(REPO_ROOT),
        env=get_env()
    )

    assert "#line" not in res.stdout
    assert "int main(int argc, char** argv) {" in res.stdout
    assert "x = 42;" in res.stdout


def test_control_flow_statements_line_directives(tmp_path):
    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    source_file = tmp_path / "ctrl.vl"
    source_file.write_text(
        "act check_val(x: i32) -> i32 {\n"   # line 1
        "    if x > 10 {\n"                  # line 2
        "        return 1\n"                  # line 3
        "    } else if x > 5 {\n"            # line 4
        "        return 2\n"                  # line 5
        "    } else {\n"                     # line 6
        "        return 0\n"                  # line 7
        "    }\n"                            # line 8
        "}\n"                                # line 9
        "act main() {\n"                     # line 10
        "    mut i: i32 = 0\n"               # line 11
        "    loop i < 5 {\n"                 # line 12
        "        i += 1\n"                   # line 13
        "        if i == 3 { break }\n"      # line 14
        "    }\n"                            # line 15
        "}\n",                               # line 16
        encoding="utf-8"
    )

    res = subprocess.run(
        [str(VELO_EXE), "emit-c", str(source_file)],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(REPO_ROOT),
        env=get_env()
    )

    norm_path = str(source_file).replace("\\", "/")
    assert f'#line 1 "{norm_path}"' in res.stdout
    assert f'#line 2 "{norm_path}"' in res.stdout
    assert f'#line 3 "{norm_path}"' in res.stdout
    assert f'#line 4 "{norm_path}"' in res.stdout
    assert f'#line 5 "{norm_path}"' in res.stdout
    assert f'#line 7 "{norm_path}"' in res.stdout
    assert f'#line 10 "{norm_path}"' in res.stdout
    assert f'#line 11 "{norm_path}"' in res.stdout
    assert f'#line 12 "{norm_path}"' in res.stdout
    assert f'#line 13 "{norm_path}"' in res.stdout
    assert f'#line 14 "{norm_path}"' in res.stdout


def test_debugger_gdb_backtrace_reports_source_line(tmp_path):
    gdb_path = shutil.which("gdb") or "gdb"
    if not os.path.exists(gdb_path):
        pytest.skip("gdb not available for debugger backtrace test")

    if not VELO_EXE.exists():
        pytest.skip("bin/velo.exe not built")

    source_file = tmp_path / "crash_test.vl"
    source_file.write_text(
        "act crash() {\n"                    # line 1
        "    mut p: @i32 = null\n"           # line 2
        "    let val = p.@\n"                # line 3 - null pointer dereference!
        "}\n"                                # line 4
        "act main() {\n"                     # line 5
        "    crash()\n"                      # line 6
        "}\n",                               # line 7
        encoding="utf-8"
    )

    exe_file = tmp_path / "crash_test.exe"
    build_res = subprocess.run(
        [str(VELO_EXE), "build", "--debug", str(source_file), "-o", str(exe_file)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=get_env()
    )
    assert build_res.returncode == 0, f"Build failed: {build_res.stderr}\n{build_res.stdout}"
    assert exe_file.exists()

    gdb_res = subprocess.run(
        [gdb_path, "-batch", "-ex", "run", "-ex", "bt", str(exe_file)],
        capture_output=True,
        text=True,
        env=get_env()
    )

    output = gdb_res.stdout + "\n" + gdb_res.stderr
    # Verify GDB reported the crash occurring at crash_test.vl line 3!
    assert "crash_test.vl:3" in output or "crash_test.vl: 3" in output, (
        f"GDB backtrace failed to report crash_test.vl:3!\nOutput:\n{output}"
    )
