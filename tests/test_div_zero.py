import os
import subprocess
import sys
from pathlib import Path
import pytest
from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()


def get_env():
    env = os.environ.copy()
    if sys.platform == "win32":
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    env["VELO_STD"] = str(REPO_ROOT / "std")
    return env


def run_code(code: str, tmp_path: Path, mode: str = "--debug") -> subprocess.CompletedProcess:
    src_file = tmp_path / "div_test.vl"
    src_file.write_text(code, encoding="utf-8")
    cmd = [str(VELO_EXE), "run", str(src_file), mode]
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=get_env(),
    )


def check_code(code: str, tmp_path: Path) -> subprocess.CompletedProcess:
    src_file = tmp_path / "div_check.vl"
    src_file.write_text(code, encoding="utf-8")
    cmd = [str(VELO_EXE), "check", str(src_file)]
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=get_env(),
    )


def emit_c_code(code: str, tmp_path: Path) -> subprocess.CompletedProcess:
    src_file = tmp_path / "div_emit.vl"
    src_file.write_text(code, encoding="utf-8")
    cmd = [str(VELO_EXE), "emit-c", str(src_file)]
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=get_env(),
    )


# -----------------------------------------------------------------------------
# Runtime Division by Zero Tests (Task 74.2 / Invariant I74.3)
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_runtime_div_by_zero_fatal(tmp_path, mode):
    """Asserts that runtime division by zero produces a clean Velo diagnostic and exit code 1."""
    code = """
act main() -> i32 {
    let y = 0
    let x = 10 / y
    return x
}
"""
    p = run_code(code, tmp_path, mode)
    assert p.returncode == 1, f"Expected returncode 1 (not 0xC0000094), got {p.returncode}"
    assert "Velo Fatal Error: division by zero" in p.stderr
    assert ":4!" in p.stderr  # Line 4 of div_test.vl


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_runtime_mod_by_zero_fatal(tmp_path, mode):
    """Asserts that runtime modulo by zero produces a clean Velo diagnostic and exit code 1."""
    code = """
act main() -> i32 {
    let y = 0
    let x = 10 % y
    return x
}
"""
    p = run_code(code, tmp_path, mode)
    assert p.returncode == 1, f"Expected returncode 1 (not 0xC0000094), got {p.returncode}"
    assert "Velo Fatal Error: division by zero" in p.stderr
    assert ":4!" in p.stderr


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_runtime_compound_div_assign_by_zero_fatal(tmp_path, mode):
    """Asserts that runtime compound assignment /= zero produces a clean Velo diagnostic and exit code 1."""
    code = """
act main() -> i32 {
    mut x = 10
    let y = 0
    x /= y
    return x
}
"""
    p = run_code(code, tmp_path, mode)
    assert p.returncode == 1, f"Expected returncode 1 (not 0xC0000094), got {p.returncode}"
    assert "Velo Fatal Error: division by zero" in p.stderr
    assert ":5!" in p.stderr


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_runtime_u64_div_by_zero_fatal(tmp_path, mode):
    """Asserts that runtime unsigned 64-bit division by zero produces clean fatal."""
    code = """
act main() -> i32 {
    let y: u64 = 0u64
    let x: u64 = 100u64 / y
    if x > 0u64 { return 0 }
    return 1
}
"""
    p = run_code(code, tmp_path, mode)
    assert p.returncode == 1
    assert "Velo Fatal Error: division by zero" in p.stderr
    assert ":4!" in p.stderr


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_runtime_u32_div_by_zero_fatal(tmp_path, mode):
    """Asserts that runtime unsigned 32-bit division by zero produces clean fatal."""
    code = """
act main() -> i32 {
    let y: u32 = 0u32
    let x: u32 = 100u32 / y
    if x > 0u32 { return 0 }
    return 1
}
"""
    p = run_code(code, tmp_path, mode)
    assert p.returncode == 1
    assert "Velo Fatal Error: division by zero" in p.stderr
    assert ":4!" in p.stderr


# -----------------------------------------------------------------------------
# Compile-Time Constant Division by Zero Tests
# -----------------------------------------------------------------------------


def test_compile_time_div_by_zero_literal(tmp_path):
    """Asserts that compile-time constant division by 0 is rejected with a semantic error."""
    code = """
act main() -> i32 {
    let x = 10 / 0
    return x
}
"""
    p = check_code(code, tmp_path)
    assert p.returncode != 0
    assert "Division by zero" in (p.stdout + p.stderr)


def test_compile_time_div_by_zero_annotated(tmp_path):
    """Asserts that compile-time division by 0 with type annotation is rejected."""
    code = """
act main() -> i32 {
    let x: i32 = 10 / 0
    return x
}
"""
    p = check_code(code, tmp_path)
    assert p.returncode != 0
    assert "Division by zero" in (p.stdout + p.stderr)


def test_compile_time_mod_by_zero_literal(tmp_path):
    """Asserts that compile-time constant modulo by 0 is rejected."""
    code = """
act main() -> i32 {
    let x = 10 % 0
    return x
}
"""
    p = check_code(code, tmp_path)
    assert p.returncode != 0
    assert "Modulo by zero" in (p.stdout + p.stderr)


def test_compile_time_compound_div_assign_zero(tmp_path):
    """Asserts that compile-time compound assignment /= 0 is rejected."""
    code = """
act main() -> i32 {
    mut x = 10
    x /= 0
    return x
}
"""
    p = check_code(code, tmp_path)
    assert p.returncode != 0
    assert "Division by zero" in (p.stdout + p.stderr)


def test_compile_time_const_expr_eval_zero(tmp_path):
    """Asserts that constant expression evaluating to 0 (5 - 5) in divisor is rejected."""
    code = """
act main() -> i32 {
    let x = 10 / (5 - 5)
    return x
}
"""
    p = check_code(code, tmp_path)
    assert p.returncode != 0
    assert "Division by zero" in (p.stdout + p.stderr)


# -----------------------------------------------------------------------------
# Proven Non-Zero Constant & Optimization Tests
# -----------------------------------------------------------------------------


def test_proven_nonzero_constant_elides_guard(tmp_path):
    """Asserts that division/modulo by proven non-zero constants does NOT emit velo_div_guard."""
    code = """
act main() -> i32 {
    let a = 100 / 2
    let b = 100 % 3
    mut c = 50
    c /= 5
    let y = 4
    let d = 100 / y
    let e = 100 % y
    c /= y
    return a + b + c + d + e
}
"""
    p = emit_c_code(code, tmp_path)
    assert p.returncode == 0
    lines = p.stdout.splitlines()

    # Proven non-zero constants: must NOT have velo_div_guard
    div_const = [l for l in lines if "100 / 2" in l or "(100 / 2)" in l]
    mod_const = [l for l in lines if "100 % 3" in l or "(100 % 3)" in l]
    assign_const = [l for l in lines if "c /= 5;" in l]
    assert len(div_const) > 0, "Expected constant division in emitted C"
    assert len(mod_const) > 0, "Expected constant modulo in emitted C"
    assert len(assign_const) > 0, "Expected constant /= in emitted C"
    for l in div_const + mod_const + assign_const:
        assert "velo_div_guard" not in l, f"Unexpected velo_div_guard in constant math: {l}"

    # Non-constant divisors: MUST have velo_div_guard
    dyn_div = [l for l in lines if "velo_div_guard(y)" in l]
    assert len(dyn_div) >= 3, f"Expected velo_div_guard for dynamic divisions, got: {dyn_div}"


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_short_circuit_preserved(tmp_path, mode):
    """Asserts that short-circuit evaluation of `and` prevents guard from firing when LHS is false."""
    code = """
act main() -> i32 {
    let y = 0
    if y != 0 and 100 / y > 0 {
        return 1
    }
    return 0
}
"""
    p = run_code(code, tmp_path, mode)
    assert p.returncode == 0


@pytest.mark.parametrize("mode", ["--debug", "--release"])
def test_valid_integer_division_results(tmp_path, mode):
    """Asserts that division and modulo produce correct arithmetic results for all integer types."""
    code = """
act main() -> i32 {
    let s32_a: i32 = -100
    let s32_b: i32 = 7
    if s32_a / s32_b != -14 { return 1 }
    if s32_a % s32_b != -2 { return 2 }

    let u32_a: u32 = 100u32
    let u32_b: u32 = 7u32
    if u32_a / u32_b != 14u32 { return 3 }
    if u32_a % u32_b != 2u32 { return 4 }

    let u64_a: u64 = 1000000000000u64
    let u64_b: u64 = 3u64
    if u64_a / u64_b != 333333333333u64 { return 5 }
    if u64_a % u64_b != 1u64 { return 6 }

    return 0
}
"""
    p = run_code(code, tmp_path, mode)
    assert p.returncode == 0
