import json
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

def test_std_json_codec_unit_suite():
    """Executes the pure Velo unit test suite for std.json.codec."""
    test_vl = REPO_ROOT / "std" / "tests" / "json" / "codec_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.json.codec all unit tests passed" in res.stdout

def test_python_velo_json_interop(tmp_path):
    """Verifies bidirectional JSON codec interop between Python and Velo."""
    velo_code = """
use std.io
use std.json

view data Item {
    sku: string
    price: f64
    qty: i32
    available: bool
    notes: ?string
}

view data Order {
    order_id: i64
    customer: string
    item: Item
    role: Role
}

act main() -> i32 {
    let opt_notes: ?string = "fragile handling"
    mut o = Order{
        order_id: 99887766,
        customer: "Ada Lovelace",
        item: Item{
            sku: "VELO-KEY-01",
            price: 149.99,
            qty: 2,
            available: true,
            notes: opt_notes
        },
        role: Role.Admin
    }

    let encoded = json_encode(@o)
    io.println(encoded)
    return 0
}
"""
    src_file = tmp_path / "interop.vl"
    src_file.write_text(velo_code, encoding="utf-8")

    res = subprocess.run(
        [str(VELO_EXE), "run", str(src_file)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"Velo run failed: {res.stderr}\n{res.stdout}"
    
    # Parse Velo's output with Python's standard json library
    out_json = res.stdout.strip()
    data = json.loads(out_json)

    assert data["order_id"] == 99887766
    assert data["customer"] == "Ada Lovelace"
    assert data["role"] == "Admin"
    assert data["item"]["sku"] == "VELO-KEY-01"
    assert abs(data["item"]["price"] - 149.99) < 0.001
    assert data["item"]["qty"] == 2
    assert data["item"]["available"] is True
    assert data["item"]["notes"] == "fragile handling"

def test_python_to_velo_decode(tmp_path):
    """Verifies that JSON produced by Python's json.dumps is accurately decoded by Velo."""
    payload = {
        "title": "Quantum Computing Basics",
        "author": "Dr. Smith",
        "edition": 3,
        "is_published": True,
        "co_author": None
    }
    json_str = json.dumps(payload)

    velo_code = f"""
use std.io
use std.json

view data Book {{
    title: string
    author: string
    edition: i32
    is_published: bool
    co_author: ?string
}}

act main() -> i32 {{
    let json_text = {json.dumps(json_str)}
    mut b: Book
    let ok = json_decode(@b, json_text)
    if !ok.ok {{
        io.println("FAIL: decode error")
        return 1
    }}

    io.println(b.title)
    io.println(b.author)
    io.println(b.edition)
    if b.is_published {{ io.println("true") }} else {{ io.println("false") }}
    let co = b.co_author
    if co == null {{ io.println("null") }} else {{ io.println(co) }}
    return 0
}}
"""
    src_file = tmp_path / "decode_interop.vl"
    src_file.write_text(velo_code, encoding="utf-8")

    res = subprocess.run(
        [str(VELO_EXE), "run", str(src_file)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"Velo run failed: {res.stderr}\n{res.stdout}"
    lines = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
    assert lines == [
        "Quantum Computing Basics",
        "Dr. Smith",
        "3",
        "true",
        "null"
    ]
