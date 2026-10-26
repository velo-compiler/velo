import os
import sys
import subprocess
import pytest
from velo.manifest import parse_manifest, load_manifest, ManifestError

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

def _run_stage2(args):
    if not os.path.exists("bin/velo.exe"):
        pytest.skip("bin/velo.exe not built; skipping native stage 2 test")
    return subprocess.run(
        ["bin/velo.exe"] + args,
        capture_output=True,
        text=True
    )

FULL_MANIFEST_SRC = """# Velo Package Manifest
pkg "my_game" {
    version: "0.1.0"
    entry: "src/main.vl"
    authors: ["Devad", "Alice"]
    description: "A fast 2D game in Velo"
    license: "MIT"
}

// Dependencies section
deps {
    raylib: git "https://github.com/velo-lang/raylib-velo" @ "v1.0"
    physics: local "../physics_engine"
    math: "1.2.0"
}

// Linker configuration
link {
    libs: ["raylib", "gdi32", "winmm"]
    flags: ["-O3", "-Wall"]
}
"""

MINIMAL_MANIFEST_SRC = """pkg "minimal_app" {
    version: "1.0.0"
    entry: "main.vl"
}
"""

def test_manifest_python_api_full(tmp_path):
    m_path = _write(tmp_path, "velo.pkg", FULL_MANIFEST_SRC)
    m = load_manifest(m_path)
    assert m.pkg.name == "my_game"
    assert m.pkg.version == "0.1.0"
    assert m.pkg.entry == "src/main.vl"
    assert m.pkg.authors == ["Devad", "Alice"]
    assert m.pkg.description == "A fast 2D game in Velo"
    assert m.pkg.license == "MIT"

    assert "raylib" in m.deps
    assert m.deps["raylib"].kind == "git"
    assert m.deps["raylib"].source == "https://github.com/velo-lang/raylib-velo"
    assert m.deps["raylib"].tag == "v1.0"

    assert "physics" in m.deps
    assert m.deps["physics"].kind == "local"
    assert m.deps["physics"].source == "../physics_engine"

    assert "math" in m.deps
    assert m.deps["math"].kind == "registry"
    assert m.deps["math"].source == "1.2.0"

    assert m.link.libs == ["raylib", "gdi32", "winmm"]
    assert m.link.flags == ["-O3", "-Wall"]

def test_manifest_python_api_minimal(tmp_path):
    m = parse_manifest(MINIMAL_MANIFEST_SRC, "velo.pkg")
    assert m.pkg.name == "minimal_app"
    assert m.pkg.version == "1.0.0"
    assert m.pkg.entry == "main.vl"
    assert len(m.deps) == 0
    assert len(m.link.libs) == 0

def test_manifest_cli_check_positive(tmp_path):
    m_path = _write(tmp_path, "velo.pkg", FULL_MANIFEST_SRC)

    p1 = _run_stage1(["pkg", "check", m_path])
    assert p1.returncode == 0, f"Stage 1 failed:\n{p1.stderr}\n{p1.stdout}"
    assert "[Velo] Valid package manifest: my_game v0.1.0 (src/main.vl)" in p1.stdout

    p2 = _run_stage2(["pkg", "check", m_path])
    assert p2.returncode == 0, f"Stage 2 failed:\n{p2.stderr}\n{p2.stdout}"
    assert "[Velo] Valid package manifest: my_game v0.1.0 (src/main.vl)" in p2.stdout

def test_manifest_cli_check_minimal(tmp_path):
    m_path = _write(tmp_path, "velo.pkg", MINIMAL_MANIFEST_SRC)

    p1 = _run_stage1(["pkg", "check", m_path])
    assert p1.returncode == 0
    assert "[Velo] Valid package manifest: minimal_app v1.0.0 (main.vl)" in p1.stdout

    p2 = _run_stage2(["pkg", "check", m_path])
    assert p2.returncode == 0
    assert "[Velo] Valid package manifest: minimal_app v1.0.0 (main.vl)" in p2.stdout

MANIFEST_NEGATIVE_CASES = [
    (
        "missing_pkg",
        "deps {}",
        "missing required 'pkg' block in manifest"
    ),
    (
        "missing_name",
        "pkg { version: \"1.0\" entry: \"main.vl\" }",
        "missing required field 'name' in pkg block"
    ),
    (
        "missing_version",
        "pkg \"app\" { entry: \"main.vl\" }",
        "missing required field 'version' in pkg block"
    ),
    (
        "missing_entry",
        "pkg \"app\" { version: \"1.0\" }",
        "missing required field 'entry' in pkg block"
    ),
    (
        "unknown_toplevel",
        "foo {}",
        "unexpected top-level item 'foo' (expected 'pkg', 'deps', or 'link')"
    ),
    (
        "unknown_pkg_field",
        "pkg \"app\" { version: \"1.0\" entry: \"main.vl\" invalid_key: \"x\" }",
        "unknown field 'invalid_key' in 'pkg' block"
    ),
    (
        "unknown_link_field",
        "pkg \"app\" { version: \"1.0\" entry: \"main.vl\" } link { bad_field: [\"x\"] }",
        "unknown field 'bad_field' in 'link' block (expected 'libs' or 'flags')"
    ),
    (
        "unterminated_string",
        "pkg \"app",
        "unterminated string literal"
    ),
]

@pytest.mark.parametrize("name,code,expected_error", MANIFEST_NEGATIVE_CASES)
def test_manifest_negative_diagnostics_parity(tmp_path, name, code, expected_error):
    m_path = _write(tmp_path, f"{name}.pkg", code)

    p1 = _run_stage1(["pkg", "check", m_path])
    assert p1.returncode != 0, f"Stage 1 unexpectedly passed for {name}"
    s1_out = p1.stdout + p1.stderr
    assert expected_error in s1_out, f"Stage 1 missing '{expected_error}' in:\n{s1_out}"

    p2 = _run_stage2(["pkg", "check", m_path])
    assert p2.returncode != 0, f"Stage 2 unexpectedly passed for {name}"
    s2_out = p2.stdout + p2.stderr
    assert expected_error in s2_out, f"Stage 2 missing '{expected_error}' in:\n{s2_out}"

def test_manifest_file_not_found():
    p1 = _run_stage1(["pkg", "check", "nonexistent_manifest_12345.pkg"])
    assert p1.returncode != 0
    assert "manifest file not found" in (p1.stdout + p1.stderr)

    p2 = _run_stage2(["pkg", "check", "nonexistent_manifest_12345.pkg"])
    assert p2.returncode != 0
    assert "manifest file not found" in (p2.stdout + p2.stderr)
