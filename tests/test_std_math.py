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

def test_std_math_bits():
    test_vl = REPO_ROOT / "std" / "tests" / "math" / "bits_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.math.bits tests succeeded" in res.stdout


def test_std_math_int():
    test_vl = REPO_ROOT / "std" / "tests" / "math" / "int_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.math.int tests succeeded" in res.stdout


def test_std_math_float():
    test_vl = REPO_ROOT / "std" / "tests" / "math" / "float_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.math.float tests succeeded" in res.stdout


def test_std_math_trig():
    test_vl = REPO_ROOT / "std" / "tests" / "math" / "trig_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.math.trig tests succeeded" in res.stdout


def test_std_math_module_import():
    test_vl = REPO_ROOT / "std" / "tests" / "math_module_import_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: use std.math umbrella module verified" in res.stdout


def test_std_math_decimal():
    test_vl = REPO_ROOT / "std" / "tests" / "math" / "decimal_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.math.decimal tests succeeded" in res.stdout


def test_std_math_decimal_property_test(tmp_path):
    import random
    from decimal import Decimal as PyDecimal, ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_DOWN, ROUND_UP, ROUND_FLOOR, ROUND_CEILING

    mode_map = [
        (ROUND_HALF_EVEN, "ROUND_HALF_EVEN"),
        (ROUND_HALF_UP, "ROUND_HALF_UP"),
        (ROUND_DOWN, "ROUND_DOWN"),
        (ROUND_UP, "ROUND_UP"),
        (ROUND_FLOOR, "ROUND_FLOOR"),
        (ROUND_CEILING, "ROUND_CEIL"),
    ]

    rng = random.Random(789)
    lines = [
        'use std.io',
        'use std.math',
        '',
        'act main() -> i32 {',
    ]

    for i in range(150):
        u1 = rng.randint(-100000, 100000)
        s1 = rng.randint(1, 4)
        u2 = rng.randint(-100000, 100000)
        s2 = rng.randint(1, 4)

        d1_str = f"{PyDecimal(u1) / (10 ** s1):.{s1}f}"
        d2_str = f"{PyDecimal(u2) / (10 ** s2):.{s2}f}"
        p1 = PyDecimal(d1_str)
        p2 = PyDecimal(d2_str)

        op = rng.choice(["add", "sub", "mul", "rescale"])
        if op == "add":
            expected = p1 + p2
            lines.append(f'    let a{i} = dec_from_str("{d1_str}")')
            lines.append(f'    let b{i} = dec_from_str("{d2_str}")')
            lines.append(f'    let exp{i} = dec_from_str("{expected}")')
            lines.append(f'    if !dec_eq(dec_add(a{i}, b{i}), exp{i}) {{ return {1000 + i}; }}')
        elif op == "sub":
            expected = p1 - p2
            lines.append(f'    let a{i} = dec_from_str("{d1_str}")')
            lines.append(f'    let b{i} = dec_from_str("{d2_str}")')
            lines.append(f'    let exp{i} = dec_from_str("{expected}")')
            lines.append(f'    if !dec_eq(dec_sub(a{i}, b{i}), exp{i}) {{ return {2000 + i}; }}')
        elif op == "mul":
            m1 = rng.randint(-1000, 1000)
            m2 = rng.randint(-1000, 1000)
            sm1_str = f"{PyDecimal(m1) / 100:.2f}"
            sm2_str = f"{PyDecimal(m2) / 100:.2f}"
            expected = PyDecimal(sm1_str) * PyDecimal(sm2_str)
            lines.append(f'    let a{i} = dec_from_str("{sm1_str}")')
            lines.append(f'    let b{i} = dec_from_str("{sm2_str}")')
            lines.append(f'    let exp{i} = dec_from_str("{expected}")')
            lines.append(f'    if !dec_eq(dec_mul(a{i}, b{i}), exp{i}) {{ return {3000 + i}; }}')
        elif op == "rescale":
            py_mode, velo_mode = rng.choice(mode_map)
            target_scale = rng.randint(0, 2)
            exp_quantum = PyDecimal(10) ** (-target_scale) if target_scale > 0 else PyDecimal(1)
            expected = p1.quantize(exp_quantum, rounding=py_mode)
            lines.append(f'    let a{i} = dec_from_str("{d1_str}")')
            lines.append(f'    let res{i} = dec_rescale(a{i}, {target_scale} as u32, {velo_mode})')
            lines.append(f'    let exp{i} = dec_from_str("{expected}")')
            lines.append(f'    if !dec_eq(res{i}, exp{i}) {{ return {4000 + i}; }}')

    lines.append('    println_str("PASS: decimal property test succeeded")')
    lines.append('    return 0;')
    lines.append('}')

    test_file = tmp_path / "prop_decimal.vl"
    test_file.write_text("\n".join(lines), encoding="utf-8")
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_file)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"Decimal property test failed: code {res.returncode}\n{res.stderr}\n{res.stdout}"
    assert "PASS: decimal property test succeeded" in res.stdout
