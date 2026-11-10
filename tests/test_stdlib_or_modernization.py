import subprocess
import pytest
from pathlib import Path

def _run_stage1(cmd: list) -> subprocess.CompletedProcess:
    full_cmd = ["python", "velo.py"] + cmd
    return subprocess.run(full_cmd, capture_output=True, text=True)

def _run_stage2(cmd: list) -> subprocess.CompletedProcess:
    velo_exe = Path("bin/velo.exe").resolve()
    if not velo_exe.exists():
        pytest.skip("bin/velo.exe not built yet")
    full_cmd = [str(velo_exe)] + cmd
    return subprocess.run(full_cmd, capture_output=True, text=True)


def test_fmt_atoi_or_parsing(tmp_path):
    code = """
use std.io
use std.fmt

act test_parser() -> i64 or string {
    let a = parse_int("12345") or return
    let b = parse_int("-500") or return
    let c = parse_int("bad_number") or 99
    let h = parse_hex_uint("FF") or return
    let u = parse_uint("1000") or return
    let i32_val = parse_int32("42") or return

    io.println("a: {a}, b: {b}, c: {c}, h: {h}, u: {u}, i32: {i32_val}")
    return a + b + c
}

act main() {
    let r = test_parser()
    if r.ok {
        io.println("sum: {r.val}")
    } else {
        io.println("err: {r.err}")
    }

    let bad = parse_int("totally_invalid")
    if not bad.ok {
        io.println("bad err: {bad.err}")
    }
}
"""
    f = tmp_path / "test_fmt_or.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["run", str(f)])
    assert res1.returncode == 0, f"Stage 1 failed: {res1.stderr}"
    assert "a: 12345, b: -500, c: 99, h: 255, u: 1000, i32: 42" in res1.stdout
    assert "sum: 11944" in res1.stdout
    assert "bad err: invalid integer syntax" in res1.stdout

    res2 = _run_stage2(["run", str(f)])
    assert res2.returncode == 0, f"Stage 2 failed: {res2.stderr}"
    assert "a: 12345, b: -500, c: 99, h: 255, u: 1000, i32: 42" in res2.stdout
    assert "sum: 11944" in res2.stdout
    assert "bad err: invalid integer syntax" in res2.stdout


def test_fs_or_operations(tmp_path):
    code = """
use std.io
use std.fs

act file_flow() -> string or string {
    let path = ".velo_cache/fs_or_test.txt"
    fs_write_file(path, "Velo Modernized") or return
    fs_append_file(path, " with 'or'") or return
    let content = fs_read_file(path) or return
    return content
}

act main() {
    let res = file_flow()
    if res.ok {
        io.println("content: '{res.val}'")
    } else {
        io.println("err: {res.err}")
    }

    let missing = fs_read_file(".velo_cache/definitely_missing_file_12345.txt") or "default_fallback"
    io.println("missing: {missing}")
}
"""
    f = tmp_path / "test_fs_or.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["run", str(f)])
    assert res1.returncode == 0, f"Stage 1 failed: {res1.stderr}"
    assert "content: 'Velo Modernized with 'or''" in res1.stdout
    assert "missing: default_fallback" in res1.stdout

    res2 = _run_stage2(["run", str(f)])
    assert res2.returncode == 0, f"Stage 2 failed: {res2.stderr}"
    assert "content: 'Velo Modernized with 'or''" in res2.stdout
    assert "missing: default_fallback" in res2.stdout


def test_json_or_parsing(tmp_path):
    code = """
use std.io
use std.json

act parse_json_flow(raw: string) -> i64 or string {
    mut doc = json_from_str(raw) or return
    defer json_doc_free(@doc)
    let n = json_obj_get_str(doc.root, "count")
    if n != null {
        return n.int_val
    }
    return 0
}

act main() {
    let ok_res = parse_json_flow("{\\"count\\": 42}")
    if ok_res.ok {
        io.println("count: {ok_res.val}")
    }

    let bad_res = parse_json_flow("{broken_json...")
    if not bad_res.ok {
        io.println("json err: {bad_res.err}")
    }
}
"""
    f = tmp_path / "test_json_or.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["run", str(f)])
    assert res1.returncode == 0, f"Stage 1 failed: {res1.stderr}"
    assert "count: 42" in res1.stdout
    assert "json err: invalid json syntax" in res1.stdout

    res2 = _run_stage2(["run", str(f)])
    assert res2.returncode == 0, f"Stage 2 failed: {res2.stderr}"
    assert "count: 42" in res2.stdout
    assert "json err: invalid json syntax" in res2.stdout


def test_uuid_and_url_or_parsing(tmp_path):
    code = """
use std.io
use std.uuid
use std.url

act parse_entities() -> string or string {
    let u = uuid_from_str("550e8400-e29b-41d4-a716-446655440000") or return
    let addr = url_from_str("https://api.velo.org:9000/v1/query?sort=asc#top") or return

    io.println("uuid parsed ok, port: {addr.port}, host: {addr.hostname}")
    return addr.scheme
}

act main() {
    let res = parse_entities()
    if res.ok {
        io.println("scheme: {res.val}")
    }

    let bad_uuid = uuid_from_str("not-a-real-uuid")
    if not bad_uuid.ok {
        io.println("bad uuid: {bad_uuid.err}")
    }

    let bad_url = url_from_str("http://[invalid-ipv6:8080")
    if not bad_url.ok {
        io.println("bad url: {bad_url.err}")
    }
}
"""
    f = tmp_path / "test_uuid_url_or.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["run", str(f)])
    assert res1.returncode == 0, f"Stage 1 failed: {res1.stderr}"
    assert "uuid parsed ok, port: 9000, host: api.velo.org" in res1.stdout
    assert "scheme: https" in res1.stdout
    assert "bad uuid: invalid uuid format" in res1.stdout

    res2 = _run_stage2(["run", str(f)])
    assert res2.returncode == 0, f"Stage 2 failed: {res2.stderr}"
    assert "uuid parsed ok, port: 9000, host: api.velo.org" in res2.stdout
    assert "scheme: https" in res2.stdout
    assert "bad uuid: invalid uuid format" in res2.stdout


def test_encoding_and_str_or(tmp_path):
    code = """
use std.io
use std.encoding
use std.str

act decode_flow() -> string or string {
    let hex_val = hex_to_str("48656c6c6f2056656c6f") or return
    let b64_val = base64_to_str("VmVsbw==") or return
    let pos = str_find(hex_val, "Velo") or return

    io.println("hex: '{hex_val}', b64: '{b64_val}', pos: {pos}")
    return hex_val
}

act main() {
    let r = decode_flow()
    if r.ok {
        io.println("res ok")
    }

    let bad_hex = hex_to_str("abc") or "fallback_hex"
    let bad_b64 = base64_to_str("!!!") or "fallback_b64"
    let not_found = str_find("hello", "xyz") or 9999

    io.println("bad_hex: {bad_hex}, bad_b64: {bad_b64}, not_found: {not_found}")
}
"""
    f = tmp_path / "test_encoding_or.vl"
    f.write_text(code, encoding="utf-8")

    res1 = _run_stage1(["run", str(f)])
    assert res1.returncode == 0, f"Stage 1 failed: {res1.stderr}"
    assert "hex: 'Hello Velo', b64: 'Velo', pos: 6" in res1.stdout
    assert "res ok" in res1.stdout
    assert "bad_hex: fallback_hex, bad_b64: fallback_b64, not_found: 9999" in res1.stdout

    res2 = _run_stage2(["run", str(f)])
    assert res2.returncode == 0, f"Stage 2 failed: {res2.stderr}"
    assert "hex: 'Hello Velo', b64: 'Velo', pos: 6" in res2.stdout
    assert "res ok" in res2.stdout
    assert "bad_hex: fallback_hex, bad_b64: fallback_b64, not_found: 9999" in res2.stdout

