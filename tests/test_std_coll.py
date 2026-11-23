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

def test_std_coll_shelf():
    test_vl = REPO_ROOT / "std" / "tests" / "coll" / "shelf_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.coll.shelf all assertions succeeded" in res.stdout

def test_std_coll_shelf_ops():
    test_vl = REPO_ROOT / "std" / "tests" / "coll" / "shelf_ops_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.coll.shelf_ops all assertions succeeded" in res.stdout

def test_std_coll_ring():
    test_vl = REPO_ROOT / "std" / "tests" / "coll" / "ring_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.coll.ring all assertions succeeded" in res.stdout

def test_std_coll_hash():
    test_vl = REPO_ROOT / "std" / "tests" / "coll" / "hash_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.coll.hash all assertions succeeded" in res.stdout

def test_std_coll_map():
    test_vl = REPO_ROOT / "std" / "tests" / "coll" / "map_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.coll.map all assertions succeeded" in res.stdout

def test_std_coll_map_ops():
    test_vl = REPO_ROOT / "std" / "tests" / "coll" / "map_ops_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.coll.map_ops all assertions succeeded" in res.stdout

def test_std_coll_sort():
    test_vl = REPO_ROOT / "std" / "tests" / "coll" / "sort_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.coll.sort all assertions succeeded" in res.stdout

def test_std_coll_set():
    test_vl = REPO_ROOT / "std" / "tests" / "coll" / "set_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.coll.set all assertions succeeded" in res.stdout

def test_std_coll_deque():
    test_vl = REPO_ROOT / "std" / "tests" / "coll" / "deque_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.coll.deque all assertions succeeded" in res.stdout

def test_std_coll_heap():
    test_vl = REPO_ROOT / "std" / "tests" / "coll" / "heap_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.coll.heap all assertions succeeded" in res.stdout

def test_std_coll_set_property_test(tmp_path):
    import random
    rng = random.Random(42)
    py_set = set()
    lines = [
        'use std.io',
        'use std.coll',
        '',
        'act main() -> i32 {',
        '    mut s = set_create_i64(8)',
    ]
    for i in range(300):
        op = rng.choice(["add", "contains", "remove"])
        val = rng.randint(0, 50)
        if op == "add":
            py_set.add(val)
            lines.append(f'    if !set_add_i64(@s, {val}i64) {{ return {1000 + i}; }}')
        elif op == "contains":
            expected = "true" if val in py_set else "false"
            lines.append(f'    if set_contains_i64(@s, {val}i64) != {expected} {{ return {2000 + i}; }}')
        elif op == "remove":
            expected = "true" if val in py_set else "false"
            if val in py_set:
                py_set.remove(val)
            lines.append(f'    if set_remove_i64(@s, {val}i64) != {expected} {{ return {3000 + i}; }}')
    lines.append(f'    if set_len(@s) != {len(py_set)} {{ return 4000; }}')
    lines.append('    set_free(@s)')
    lines.append('    println_str("PASS: set property test succeeded")')
    lines.append('    return 0;')
    lines.append('}')

    test_file = tmp_path / "prop_set.vl"
    test_file.write_text("\n".join(lines), encoding="utf-8")
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_file)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"Set property test failed: code {res.returncode}\n{res.stderr}\n{res.stdout}"
    assert "PASS: set property test succeeded" in res.stdout

def test_std_coll_deque_property_test(tmp_path):
    import random
    from collections import deque
    rng = random.Random(1337)
    py_deq = deque()
    lines = [
        'use std.io',
        'use std.coll',
        '',
        'act main() -> i32 {',
        '    mut d = deque_create_i64(8)',
        '    mut out_val: i64 = 0',
    ]
    for i in range(300):
        choices = ["push_back", "push_front"]
        if len(py_deq) > 0:
            choices.extend(["pop_back", "pop_front", "rotate", "get"])
        op = rng.choice(choices)
        if op == "push_back":
            val = rng.randint(-1000, 1000)
            py_deq.append(val)
            lines.append(f'    if !deque_push_back_i64(@d, {val}i64) {{ return {1000 + i}; }}')
        elif op == "push_front":
            val = rng.randint(-1000, 1000)
            py_deq.appendleft(val)
            lines.append(f'    if !deque_push_front_i64(@d, {val}i64) {{ return {2000 + i}; }}')
        elif op == "pop_back":
            expected = py_deq.pop()
            lines.append(f'    if !deque_pop_back_i64(@d, @out_val) or out_val != {expected}i64 {{ return {3000 + i}; }}')
        elif op == "pop_front":
            expected = py_deq.popleft()
            lines.append(f'    if !deque_pop_front_i64(@d, @out_val) or out_val != {expected}i64 {{ return {4000 + i}; }}')
        elif op == "rotate":
            rot = rng.randint(-5, 5)
            py_deq.rotate(rot)
            lines.append(f'    if !deque_rotate(@d, {rot} as isize) {{ return {5000 + i}; }}')
        elif op == "get":
            idx = rng.randint(0, len(py_deq) - 1)
            expected = py_deq[idx]
            lines.append(f'    if !deque_get_i64(@d, {idx}, @out_val) or out_val != {expected}i64 {{ return {6000 + i}; }}')

    lines.append(f'    if deque_len(@d) != {len(py_deq)} {{ return 7000; }}')
    for idx, expected in enumerate(py_deq):
        lines.append(f'    if !deque_get_i64(@d, {idx}, @out_val) or out_val != {expected}i64 {{ return {8000 + idx}; }}')
    lines.append('    deque_free(@d)')
    lines.append('    println_str("PASS: deque property test succeeded")')
    lines.append('    return 0;')
    lines.append('}')

    test_file = tmp_path / "prop_deque.vl"
    test_file.write_text("\n".join(lines), encoding="utf-8")
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_file)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"Deque property test failed: code {res.returncode}\n{res.stderr}\n{res.stdout}"
    assert "PASS: deque property test succeeded" in res.stdout

def test_std_coll_heap_property_test(tmp_path):
    import random
    import heapq
    rng = random.Random(2026)
    py_heap = []
    lines = [
        'use std.io',
        'use std.coll',
        '',
        'act main() -> i32 {',
        '    mut h = bheap_create_min_i64(8)',
        '    mut out_val: i64 = 0',
    ]
    for i in range(300):
        choices = ["push"]
        if len(py_heap) > 0:
            choices.extend(["pop", "peek", "push_pop"])
        op = rng.choice(choices)
        if op == "push":
            val = rng.randint(-1000, 1000)
            heapq.heappush(py_heap, val)
            lines.append(f'    if !bheap_push_i64(@h, {val}i64) {{ return {1000 + i}; }}')
        elif op == "pop":
            expected = heapq.heappop(py_heap)
            lines.append(f'    if !bheap_pop_i64(@h, @out_val) or out_val != {expected}i64 {{ return {2000 + i}; }}')
        elif op == "peek":
            expected = py_heap[0]
            lines.append(f'    if !bheap_peek_i64(@h, @out_val) or out_val != {expected}i64 {{ return {3000 + i}; }}')
        elif op == "push_pop":
            val = rng.randint(-1000, 1000)
            expected = heapq.heappushpop(py_heap, val)
            lines.append(f'    mut in_v{i}: i64 = {val}i64')
            lines.append(f'    let pin{i}: @i64 = @in_v{i}')
            lines.append(f'    let pout{i}: @i64 = @out_val')
            lines.append(f'    if !bheap_push_pop(@h, pin{i} as @u8, pout{i} as @u8) or out_val != {expected}i64 {{ return {4000 + i}; }}')

    lines.append(f'    if bheap_len(@h) != {len(py_heap)} {{ return 5000; }}')
    while py_heap:
        expected = heapq.heappop(py_heap)
        lines.append(f'    if !bheap_pop_i64(@h, @out_val) or out_val != {expected}i64 {{ return 6000; }}')
    lines.append('    bheap_free(@h)')
    lines.append('    println_str("PASS: heap property test succeeded")')
    lines.append('    return 0;')
    lines.append('}')

    test_file = tmp_path / "prop_heap.vl"
    test_file.write_text("\n".join(lines), encoding="utf-8")
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_file)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"Heap property test failed: code {res.returncode}\n{res.stderr}\n{res.stdout}"
    assert "PASS: heap property test succeeded" in res.stdout

def test_std_module_imports():
    test_vl = REPO_ROOT / "std" / "tests" / "std_module_import_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: native use std.* imports succeeded" in res.stdout






