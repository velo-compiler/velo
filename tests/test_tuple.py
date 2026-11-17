"""Tests for first-class tuples and multiple return values (-> (A, B)).

Validates:
- Multiple return value signatures: act fn() -> (string, bool)
- Tuple literals: ("alice", true), (1, 2, 3)
- Tuple destructuring: let (a, b) = val, mut (x, y) = val
- Wildcard destructuring: let (val, _) = pair
- Tuple member access: t.0, t.1, t._0, t._1
- Outcome integration: (T0, T1) or Error, let (a, b) = fn() or return
- If-else expression integration: let (a, b) = if c { (1, 2) } else { (3, 4) }
- Semantic rejection for binding count mismatch, out of bounds index, non-tuple destructuring
"""

import subprocess
import os
import pytest

from conftest import velo_exe

VELO_BIN = str(velo_exe())


def run_velo_source(code: str, tmp_path) -> subprocess.CompletedProcess:
    source_file = tmp_path / "test_prog.vl"
    source_file.write_text(code, encoding="utf-8")
    return subprocess.run(
        [VELO_BIN, "run", str(source_file)],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace"
    )


def build_velo_source(code: str, tmp_path) -> subprocess.CompletedProcess:
    source_file = tmp_path / "test_prog.vl"
    source_file.write_text(code, encoding="utf-8")
    return subprocess.run(
        [VELO_BIN, "build", str(source_file), "-o", str(tmp_path / "out.exe")],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace"
    )


def test_tuple_multiple_return_and_destructuring(tmp_path):
    code = """
use std.io

act find_item(id: i32) -> (string, i32, bool) {
    if id == 1 {
        return ("sword", 100, true)
    }
    return ("nothing", 0, false)
}

act main() -> i32 {
    let (item, price, available) = find_item(1)
    if item == "sword" and price == 100 and available {
        let (none_item, none_price, none_avail) = find_item(2)
        if none_item == "nothing" and none_price == 0 and not none_avail {
            println_str("OK")
            return 0
        }
    }
    return 1
}
"""
    res = run_velo_source(code, tmp_path)
    assert res.returncode == 0
    assert "OK" in res.stdout


def test_tuple_mutability_and_wildcard(tmp_path):
    code = """
use std.io

act main() -> i32 {
    mut (x, y) = (10, 20)
    x += 5
    y *= 2
    if x != 15 or y != 40 { return 1 }

    let (only_first, _) = (999, "ignored")
    if only_first != 999 { return 2 }

    let (_, only_mid, _) = (1, 2, 3)
    if only_mid != 2 { return 3 }

    println_str("MUT_OK")
    return 0
}
"""
    res = run_velo_source(code, tmp_path)
    assert res.returncode == 0
    assert "MUT_OK" in res.stdout


def test_tuple_member_access(tmp_path):
    code = """
use std.io

act main() -> i32 {
    let t = ("velo", 42, 3.14)
    if t.0 != "velo" or t.1 != 42 { return 1 }
    if t._0 != "velo" or t._1 != 42 { return 2 }
    println_str("ACCESS_OK")
    return 0
}
"""
    res = run_velo_source(code, tmp_path)
    assert res.returncode == 0
    assert "ACCESS_OK" in res.stdout


def test_tuple_outcome_integration(tmp_path):
    code = """
use std.io

act divide_mod(a: i32, b: i32) -> (i32, i32) or string {
    if b == 0 { fail "div by zero" }
    return (a / b, a % b)
}

act run_calc() -> i32 or string {
    let (q, r) = divide_mod(23, 5) or return
    return q * 10 + r
}

act main() -> i32 {
    let res = run_calc()
    if res.ok and res.val == 43 {
        let err_res = divide_mod(5, 0)
        if not err_res.ok and err_res.err == "div by zero" {
            println_str("OUTCOME_OK")
            return 0
        }
    }
    return 1
}
"""
    res = run_velo_source(code, tmp_path)
    assert res.returncode == 0
    assert "OUTCOME_OK" in res.stdout


def test_tuple_if_expression(tmp_path):
    code = """
use std.io

act get_pair(flag: bool) -> (i32, string) {
    return if flag { (1, "yes") } else { (0, "no") }
}

act main() -> i32 {
    let (v1, s1) = get_pair(true)
    let (v2, s2) = get_pair(false)
    if v1 == 1 and s1 == "yes" and v2 == 0 and s2 == "no" {
        println_str("IF_OK")
        return 0
    }
    return 1
}
"""
    res = run_velo_source(code, tmp_path)
    assert res.returncode == 0
    assert "IF_OK" in res.stdout


def test_tuple_destructure_count_mismatch_rejected(tmp_path):
    code = """
act main() -> i32 {
    let (a, b, c) = (1, 2)
    return 0
}
"""
    res = build_velo_source(code, tmp_path)
    assert res.returncode != 0
    assert "Destructuring binding count mismatch" in res.stdout or "Destructuring binding count mismatch" in res.stderr


def test_tuple_destructure_non_tuple_rejected(tmp_path):
    code = """
act main() -> i32 {
    let (a, b) = 123
    return 0
}
"""
    res = build_velo_source(code, tmp_path)
    assert res.returncode != 0
    assert "Cannot destructure non-tuple" in res.stdout or "Cannot destructure non-tuple" in res.stderr


def test_tuple_index_out_of_bounds_rejected(tmp_path):
    code = """
act main() -> i32 {
    let t = (1, 2)
    let x = t.2
    return 0
}
"""
    res = build_velo_source(code, tmp_path)
    assert res.returncode != 0
    assert "Tuple index out of bounds" in res.stdout or "Tuple index out of bounds" in res.stderr


def test_tuple_binding_type_mismatch_rejected(tmp_path):
    code = """
act main() -> i32 {
    let (a: string, b: i32) = (10, 20)
    return 0
}
"""
    res = build_velo_source(code, tmp_path)
    assert res.returncode != 0
    assert "Type mismatch in destructuring binding" in res.stdout or "Type mismatch in destructuring binding" in res.stderr
