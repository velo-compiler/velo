import os
import subprocess
from pathlib import Path
import shutil
import pytest
from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()
MSYS2_BIN = cc_dir()


def get_env():
    env = os.environ.copy()
    if MSYS2_BIN not in env.get("PATH", ""):
        env["PATH"] = MSYS2_BIN + ";" + env.get("PATH", "")
    return env


@pytest.fixture(scope="module", autouse=True)
def ensure_velo_exe():
    """Ensure bin/velo.exe exists before running lexer capacity tests."""
    if not VELO_EXE.exists():
        res = subprocess.run(
            ["python", "velo.py", "build", "src/main.vl", "-o", str(VELO_EXE)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=get_env(),
        )
        assert res.returncode == 0, f"Failed to bootstrap bin/velo.exe:\n{res.stderr}"
    assert VELO_EXE.exists(), "bin/velo.exe must exist"


@pytest.fixture(scope="module")
def big_program(tmp_path_factory):
    """Generate a valid Velo program with far more than 8192 tokens (~12k).

    Regression target: the self-hosted lexer used a fixed 8192-token buffer
    and silently discarded overflow tokens, which corrupted the token stream
    and crashed the compiler with a misleading 'Zone Arena Out of Memory'.
    The driver now sizes capacity from the source length.
    """
    out_dir = tmp_path_factory.mktemp("lexer_capacity")
    num_stmts = 3000
    lines = ["use sys.io", "", "act main() {", "    mut a = 1"]
    for i in range(2, num_stmts + 1):
        lines.append(f"    a += {i}")
    lines.append('    io.println("Total: {a}")')
    lines.append("}")
    src = out_dir / "hello_big.vl"
    src.write_text("\n".join(lines), encoding="utf-8")

    exe = out_dir / "hello_big.exe"
    res = subprocess.run(
        [str(VELO_EXE), "build", str(src), "-o", str(exe)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env(),
    )
    assert res.returncode == 0, f"Big program failed to build:\n{res.stdout}\n{res.stderr}"
    assert exe.exists(), "Big program must produce an executable"
    return exe, num_stmts


def test_large_file_compiles(big_program):
    """A file whose token count exceeds the old hardcoded 8192 cap must compile."""
    exe, _ = big_program
    assert "Total: 4501500" in subprocess.run(
        [str(exe)], capture_output=True, text=True, env=get_env()
    ).stdout


def test_lexer_overflow_reports_diagnostic(monkeypatch, tmp_path_factory):
    """If saturation ever occurs, the compiler must report a real error
    with the file path and truncated count instead of silently dropping tokens.

    Simulated by building a temporary tiny-cap variant of the compiler.
    """
    out_dir = tmp_path_factory.mktemp("lexer_overflow")
    src_dir = out_dir / "src"
    shutil.copytree(REPO_ROOT / "src", src_dir)

    driver_vl = src_dir / "backend" / "driver.vl"
    text = driver_vl.read_text(encoding="utf-8")
    text = text.replace("create_lexer(source, slen, slen + 2)", "create_lexer(source, slen, 100)")
    driver_vl.write_text(text, encoding="utf-8")

    tiny_exe = out_dir / "velo_tinycap.exe"
    builder = [str(VELO_EXE), "build", str(src_dir / "main.vl"), "-o", str(tiny_exe)] if VELO_EXE.exists() else [
        "python", "velo.py", "build", str(src_dir / "main.vl"), "-o", str(tiny_exe)
    ]
    res = subprocess.run(
        builder,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env(),
    )
    assert res.returncode == 0, f"Tiny-cap compiler failed to build:\n{res.stdout}\n{res.stderr}"

    # The session-built big program exceeds a 100-token cap by construction.
    big_src = out_dir / "big.vl"
    lines = ["use sys.io", "", "act main() {", "    mut a = 1"]
    for i in range(2, 1001):
        lines.append(f"    a += {i}")
    lines.append("}")
    big_src.write_text("\n".join(lines), encoding="utf-8")

    res = subprocess.run(
        [str(tiny_exe), "build", str(big_src), "-o", str(out_dir / "never.exe")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env(),
    )
    assert res.returncode != 0, "Saturated lexer must fail the build"
    assert "lexer token buffer too small" in res.stdout
    assert "tokens were truncated" in res.stdout
    assert str(big_src).replace("\\", "/") in res.stdout
