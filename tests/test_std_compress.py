import os
import zlib
import gzip
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

def test_std_compress_native_suite():
    test_vl = REPO_ROOT / "std" / "tests" / "compress" / "compress_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.compress all tests passed" in res.stdout

def test_python_zlib_to_velo_inflate(tmp_path):
    # Python compresses raw deflate with dynamic huffman
    orig_text = "The quick brown fox jumps over the lazy dog. Repetition for LZ77: 1234567890 1234567890 1234567890"
    raw_deflate = zlib.compress(orig_text.encode("utf-8"), wbits=-15)
    hex_str = raw_deflate.hex()

    test_file = tmp_path / "test_cross_inflate.vl"
    test_file.write_text(f'''
use std.compress
use std.encoding.hex
use std.io

view act main() -> i32 {{
    let hex_input = "{hex_str}"
    mut bin_len: usize = 0
    let bin_data = hex_decode(hex_input, @bin_len)
    if bin_data == null or bin_len == 0 {{ return 1 }}

    let res = inflate_str(bin_data, bin_len)
    if !res.ok {{ return 2 }}
    print_str(res.val)
    return 0
}}
''', encoding="utf-8")

    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_file)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert res.stdout == orig_text

def test_velo_deflate_to_python_zlib(tmp_path):
    orig_text = "Velo to Python raw deflate test case. Testing back-references and fixed Huffman block emission!"
    
    test_file = tmp_path / "test_cross_deflate.vl"
    test_file.write_text(f'''
use std.compress
use std.encoding.hex
use std.io

view act main() -> i32 {{
    let input_msg = "{orig_text}"
    let comp_res = deflate_str(input_msg)
    if !comp_res.ok {{ return 1 }}
    let hex = hex_encode(comp_res.val.data, comp_res.val.len, false)
    print_str(hex)
    return 0
}}
''', encoding="utf-8")

    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_file)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    comp_bytes = bytes.fromhex(res.stdout.strip())
    decomp = zlib.decompress(comp_bytes, wbits=-15).decode("utf-8")
    assert decomp == orig_text

def test_python_gzip_to_velo_gzip_decode(tmp_path):
    orig_text = "Hello cross-platform Gzip from standard Python gzip module to pure Velo decoder!"
    gz_bytes = gzip.compress(orig_text.encode("utf-8"))
    hex_str = gz_bytes.hex()

    test_file = tmp_path / "test_cross_gzip_dec.vl"
    test_file.write_text(f'''
use std.compress
use std.encoding.hex
use std.io

view act main() -> i32 {{
    let hex_input = "{hex_str}"
    mut bin_len: usize = 0
    let bin_data = hex_decode(hex_input, @bin_len)
    if bin_data == null or bin_len == 0 {{ return 1 }}

    let res = gzip_decode_str(bin_data, bin_len)
    if !res.ok {{ return 2 }}
    print_str(res.val)
    return 0
}}
''', encoding="utf-8")

    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_file)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert res.stdout == orig_text

def test_velo_gzip_encode_to_python_gzip(tmp_path):
    orig_text = "Pure Velo Gzip encoder output cross-verified with Python gzip decompressor."
    
    test_file = tmp_path / "test_cross_gzip_enc.vl"
    test_file.write_text(f'''
use std.compress
use std.encoding.hex
use std.io

view act main() -> i32 {{
    let input_msg = "{orig_text}"
    let comp_res = gzip_encode_str(input_msg)
    if !comp_res.ok {{ return 1 }}
    let hex = hex_encode(comp_res.val.data, comp_res.val.len, false)
    print_str(hex)
    return 0
}}
''', encoding="utf-8")

    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_file)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    comp_bytes = bytes.fromhex(res.stdout.strip())
    decomp = gzip.decompress(comp_bytes).decode("utf-8")
    assert decomp == orig_text

def test_python_zlib_to_velo_zlib_decode(tmp_path):
    orig_text = "Testing Python zlib.compress -> Velo zlib_decode_str compatibility."
    zl_bytes = zlib.compress(orig_text.encode("utf-8"))
    hex_str = zl_bytes.hex()

    test_file = tmp_path / "test_cross_zlib_dec.vl"
    test_file.write_text(f'''
use std.compress
use std.encoding.hex
use std.io

view act main() -> i32 {{
    let hex_input = "{hex_str}"
    mut bin_len: usize = 0
    let bin_data = hex_decode(hex_input, @bin_len)
    if bin_data == null or bin_len == 0 {{ return 1 }}

    let res = zlib_decode_str(bin_data, bin_len)
    if !res.ok {{ return 2 }}
    print_str(res.val)
    return 0
}}
''', encoding="utf-8")

    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_file)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert res.stdout == orig_text

def test_velo_zlib_encode_to_python_zlib(tmp_path):
    orig_text = "Testing Velo zlib_encode_str -> Python zlib.decompress compatibility."
    
    test_file = tmp_path / "test_cross_zlib_enc.vl"
    test_file.write_text(f'''
use std.compress
use std.encoding.hex
use std.io

view act main() -> i32 {{
    let input_msg = "{orig_text}"
    let comp_res = zlib_encode_str(input_msg)
    if !comp_res.ok {{ return 1 }}
    let hex = hex_encode(comp_res.val.data, comp_res.val.len, false)
    print_str(hex)
    return 0
}}
''', encoding="utf-8")

    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_file)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    comp_bytes = bytes.fromhex(res.stdout.strip())
    decomp = zlib.decompress(comp_bytes).decode("utf-8")
    assert decomp == orig_text
