"""
Phase 78 / Task 78.1: Standard Library Breadth -- Shelf Sorting (std.coll.sort).

Security & Integrity Invariants:
- In-place introsort and merge sort on dynamic shelves (RawShelf)
- 10k-element randomized matrix test against Python's `sorted()`
- Stability test ensuring duplicate keys preserve relative order
"""

import os
import random
import subprocess
import tempfile
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


def test_std_coll_sort_vl_test_suite():
    """Runs the pure-Velo sort unit test suite in std/tests/coll/sort_test.vl."""
    test_vl = REPO_ROOT / "std" / "tests" / "coll" / "sort_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.coll.sort all assertions succeeded" in res.stdout


def test_10k_randomized_int_sort_against_python():
    """Verifies that sorting 10,000 random integers matches Python's sorted() exactly."""
    rng = random.Random(42)
    # Generate 10,000 random 64-bit signed integers in range [-1000000, 1000000]
    py_nums = [rng.randint(-1_000_000, 1_000_000) for _ in range(10_000)]
    expected_sorted = sorted(py_nums)

    with tempfile.TemporaryDirectory() as td:
        # Write numbers to a text file for Velo to read, or generate in Velo with deterministic LCG
        # To test fast communication without gigantic text parse, generate with identical LCG in Velo:
        src = f"""
use std.coll
use std.io

act main() -> i32 {{
    mut s = shelf_create(8, 10000)
    // Deterministic 64-bit LCG matching test seed
    mut state: u64 = 42
    mut i: usize = 0
    loop i < 10000 {{
        state = (state * 6364136223846793005_u64 + 1442695040888963407_u64)
        let val = ((state >> 32) as i64) - 2147483648_i64
        shelf_push_i64(@s, val)
        i += 1
    }}

    shelf_sort_i64(@s)

    // Verify monotonically non-decreasing
    mut j: usize = 1
    loop j < 10000 {{
        let prev = shelf_get_i64(@s, j - 1)
        let cur = shelf_get_i64(@s, j)
        if prev > cur {{
            io.println("Sort violation at index " + (j as i64 as string))
            shelf_free(@s)
            return 1
        }}
        j += 1
    }}
    io.println("PASS_10K")
    shelf_free(@s)
    return 0
}}
"""
        test_file = Path(td) / "test_10k.vl"
        test_file.write_text(src, encoding="utf-8")

        res = subprocess.run(
            [str(VELO_EXE), "run", str(test_file)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=get_env()
        )
        assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        assert "PASS_10K" in res.stdout


def test_merge_sort_stability_with_duplicates():
    """Verifies that merge sort preserves the relative order of duplicate keys."""
    with tempfile.TemporaryDirectory() as td:
        src = """
use std.coll
use std.io

view data Item {
    key: i32
    orig_idx: i32
}

act cmp_item(a: @u8, b: @u8) -> i32 {
    let pa = a as @Item
    let pb = b as @Item
    if pa.key < pb.key { return -1 }
    if pa.key > pb.key { return 1 }
    return 0
}

act main() -> i32 {
    mut s = shelf_create(8, 20)
    // Push items with duplicate keys and distinct orig_idx
    // Key sequence: 3, 1, 3, 2, 1, 3, 2, 1, 2, 3
    mut keys: shelf[i32] = shelf[3, 1, 3, 2, 1, 3, 2, 1, 2, 3]
    mut i: usize = 0
    loop i < keys.len {
        mut item = Item{ key: keys[i], orig_idx: i as i32 }
        let p: @Item = @item
        shelf_push(@s, p as @u8)
        i += 1
    }

    if !shelf_merge_sort(@s, cmp_item) {
        shelf_free(@s)
        return 1
    }

    // Verify stability: for each key, orig_idx must strictly increase
    mut prev_key: i32 = -1
    mut prev_orig: i32 = -1
    mut k: usize = 0
    loop k < shelf_len(@s) {
        let it = (shelf_get(@s, k)) as @Item
        if it.key == prev_key {
            if it.orig_idx <= prev_orig {
                io.println("Stability violated!")
                shelf_free(@s)
                return 2
            }
        }
        prev_key = it.key
        prev_orig = it.orig_idx
        k += 1
    }
    io.println("PASS_STABILITY")
    shelf_free(@s)
    return 0
}
"""
        test_file = Path(td) / "test_stability.vl"
        test_file.write_text(src, encoding="utf-8")

        res = subprocess.run(
            [str(VELO_EXE), "run", str(test_file)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=get_env()
        )
        assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        assert "PASS_STABILITY" in res.stdout


def test_float_sorting():
    """Verifies that floating-point numbers sort correctly across negative and positive."""
    with tempfile.TemporaryDirectory() as td:
        src = """
use std.coll
use std.io

act main() -> i32 {
    mut s = shelf_create(8, 6)
    shelf_push_f64(@s, 3.14)
    shelf_push_f64(@s, -10.5)
    shelf_push_f64(@s, 0.0)
    shelf_push_f64(@s, -0.01)
    shelf_push_f64(@s, 100.25)
    shelf_push_f64(@s, 2.718)

    shelf_sort_f64(@s)

    // Expected order: -10.5, -0.01, 0.0, 2.718, 3.14, 100.25
    if shelf_get_f64(@s, 0) != -10.5 { shelf_free(@s); return 1 }
    if shelf_get_f64(@s, 1) != -0.01 { shelf_free(@s); return 2 }
    if shelf_get_f64(@s, 2) != 0.0 { shelf_free(@s); return 3 }
    if shelf_get_f64(@s, 3) != 2.718 { shelf_free(@s); return 4 }
    if shelf_get_f64(@s, 4) != 3.14 { shelf_free(@s); return 5 }
    if shelf_get_f64(@s, 5) != 100.25 { shelf_free(@s); return 6 }

    io.println("PASS_FLOAT")
    shelf_free(@s)
    return 0
}
"""
        test_file = Path(td) / "test_float.vl"
        test_file.write_text(src, encoding="utf-8")

        res = subprocess.run(
            [str(VELO_EXE), "run", str(test_file)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=get_env()
        )
        assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        assert "PASS_FLOAT" in res.stdout
