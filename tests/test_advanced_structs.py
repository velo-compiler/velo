import subprocess
import sys
import os
import pytest

NEG_TEMPLATE_MISSING_FIELD = """use sys.io

type EntityId = u64

data Vec4 #align(16) {
    x: f32 = 0.0
    z: f32
}

act main() -> i32 {
    let v = Vec4{ x: 1.0 }
    io.println("v.z={v.z}")
    return 0
}
"""

NEG_TEMPLATE_BAD_ALIAS = """
data Point {
    x: f32
}

type Vec = Point
"""

def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)

def _run_stage1(args):
    return subprocess.run(
        [sys.executable, "velo.py"] + args,
        capture_output=True,
        text=True
    )

def test_advanced_structs_execution():
    result = _run_stage1(["run", "examples/26_advanced_structs.vl"])
    assert result.returncode == 0, f"Error: {result.stderr}"
    output = result.stdout
    assert "=== Testing Advanced Struct Features (Milestone 3.6) ===" in output
    assert "entity=42, next_entity=43" in output
    assert "tex is null: true" in output
    assert "p is null: true" in output
    assert "v: x=2.50, y=0.00, z=0.00, w=1.00" in output
    assert "full: x=1.00, y=2.00, z=3.00, w=4.00" in output
    assert "header: magic=7, version=1, size=8" in output
    assert "particle: id=1, hp=100, pos.x=2.50, pos.w=1.00" in output
    assert "=== Advanced Struct Verification Complete ===" in output

def test_advanced_structs_emit_c():
    result = _run_stage1(["emit-c", "examples/26_advanced_structs.vl"])
    assert result.returncode == 0, f"Error: {result.stderr}"
    output = result.stdout
    # Type aliases emitted as C typedefs
    assert "typedef u64 EntityId;" in output
    assert "typedef u8* TexBuf;" in output
    # Extra pointer levels over aliases compose correctly: @EntityId -> u64*
    assert "u64* ep = NULL" in output
    # Struct layout attributes on definitions only
    assert "struct __attribute__((aligned(16))) Vec4 {" in output
    assert "struct __attribute__((packed)) Header {" in output
    # Omitted fields filled from defaults in declaration order
    assert ".y = 0.0f, .z = 0.0f, .w = 1.0f" in output
    # Defaults appended after provided initializers
    assert ".pos = (Vec4){ .x = 2.5f, .y = 0.0f, .z = 0.0f, .w = 1.0f }, .id = 1, .hp = 100 }" in output
    assert ".magic = 7, .version = 1, .size = 8" in output

def test_advanced_structs_native_execution():
    if not os.path.exists("bin/velo.exe"):
        pytest.skip("bin/velo.exe not built; skipping native test")
    result = subprocess.run(
        ["bin/velo.exe", "run", "examples/26_advanced_structs.vl"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Error: {result.stderr}"
    output = result.stdout
    assert "entity=42, next_entity=43" in output
    assert "p is null: true" in output
    assert "v: x=2.50, y=0.00, z=0.00, w=1.00" in output
    assert "header: magic=7, version=1, size=8" in output
    assert "particle: id=1, hp=100, pos.x=2.50, pos.w=1.00" in output

def test_native_emit_c_attributes():
    if not os.path.exists("bin/velo.exe"):
        pytest.skip("bin/velo.exe not built; skipping native test")
    result = subprocess.run(
        ["bin/velo.exe", "emit-c", "examples/26_advanced_structs.vl"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Error: {result.stderr}"
    output = result.stdout
    assert "typedef uint64_t EntityId;" in output
    assert "uint64_t* ep = NULL" in output
    assert "struct __attribute__((aligned(16))) Vec4 {" in output
    assert "struct __attribute__((packed)) Header {" in output
    assert ".id = 1, .hp = 100" in output

def test_native_missing_field_without_default_is_error(tmp_path):
    if not os.path.exists("bin/velo.exe"):
        pytest.skip("bin/velo.exe not built; skipping native test")
    src = _write(tmp_path, "neg_missing_native.vl", NEG_TEMPLATE_MISSING_FIELD)
    result = subprocess.run(
        ["bin/velo.exe", "run", src],
        capture_output=True,
        text=True
    )
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "missing field" in combined

def test_missing_field_without_default_is_error(tmp_path):
    src = _write(tmp_path, "neg_missing.vl", NEG_TEMPLATE_MISSING_FIELD)
    result = _run_stage1(["run", src])
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "missing field" in combined

def test_alias_target_must_be_primitive(tmp_path):
    src = _write(tmp_path, "neg_alias.vl", NEG_TEMPLATE_BAD_ALIAS)
    result = _run_stage1(["run", src])
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "primitive" in combined
