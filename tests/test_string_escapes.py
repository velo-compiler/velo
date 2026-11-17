import subprocess
import sys
from pathlib import Path
from conftest import velo_exe

def test_raw_strings_python(tmp_path):
    source = tmp_path / "raw.vl"
    source.write_text("""
use sys.io
act main() -> i32 {
    let raw = `SELECT *
FROM "items"
WHERE path = 'C:\\files';`
    io.println(raw)
    return 0
}
""", encoding="utf-8")

    res = subprocess.run([sys.executable, "velo.py", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res.returncode == 0
    assert "SELECT *" in res.stdout
    assert 'FROM "items"' in res.stdout
    assert "WHERE path = 'C:\\files';" in res.stdout

def test_raw_strings_self_hosted(tmp_path):
    source = tmp_path / "raw_sh.vl"
    source.write_text("""
use sys.io
act main() -> i32 {
    let raw = `multi
line
raw \\n text`
    io.println(raw)
    return 0
}
""", encoding="utf-8")

    res = subprocess.run([str(velo_exe()), "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res.returncode == 0
    assert "multi\nline\nraw \\n text" in res.stdout or ("multi" in res.stdout and "raw \\n text" in res.stdout)

def test_unicode_and_hex_escapes(tmp_path):
    source = tmp_path / "unicode.vl"
    source.write_text("""
use sys.io
act main() -> i32 {
    let c1 = '\\u0041'
    let c2 = '\\x41'
    let c3 = '\\u00A9'
    let c4 = '\\u2764'
    let c5 = '\\n'
    let c6 = '\\0'
    if c1 == 65 and c2 == 65 and c3 == 169 and c4 == 10084 and c5 == 10 and c6 == 0 {
        io.println("All char escapes match!")
    }
    let s = "Symbol: \\u00A9 and \\u2764 and hex \\x41"
    io.println(s)
    return 0
}
""", encoding="utf-8")

    # Run with Python compiler
    res_py = subprocess.run([sys.executable, "velo.py", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    assert "All char escapes match!" in res_py.stdout
    assert "Symbol: © and ❤ and hex A" in res_py.stdout

    # Run with self-hosted compiler
    res_sh = subprocess.run([str(velo_exe()), "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "All char escapes match!" in res_sh.stdout
    assert "Symbol: © and ❤ and hex A" in res_sh.stdout

def test_example_17_e2e():
    example_path = "examples/17_string_escapes.vl"

    # Test with Python Stage 1
    res_py = subprocess.run([sys.executable, "velo.py", "run", example_path], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    assert "[SUCCESS] Milestone 1.4: String & Character Escapes Verified!" in res_py.stdout

    # Test with Self-Hosted Stage 2
    res_sh = subprocess.run([str(velo_exe()), "run", example_path], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "[SUCCESS] Milestone 1.4: String & Character Escapes Verified!" in res_sh.stdout

def test_multibyte_utf8_char_literals(tmp_path):
    source = tmp_path / "utf8_chars.vl"
    source.write_text("""
use sys.io
act main() -> i32 {
    let c_ascii = 'A'
    let c_e = 'é'
    let c_copy = '©'
    let c_euro = '€'
    let c_heart = '❤'
    let c_fire = '🔥'

    if c_ascii == 65 and c_e == 233 and c_e == '\\u00e9' and c_copy == 169 and c_copy == '\\u00A9' and c_euro == 8364 and c_heart == 10084 and c_fire == 128293 {
        io.println("All multibyte UTF-8 char literals match!")
    }
    return 0
}
""", encoding="utf-8")

    # Run with Python compiler (Stage 1)
    res_py = subprocess.run([sys.executable, "velo.py", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    assert "All multibyte UTF-8 char literals match!" in res_py.stdout

    # Run with self-hosted compiler (Stage 2)
    res_sh = subprocess.run([str(velo_exe()), "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "All multibyte UTF-8 char literals match!" in res_sh.stdout

