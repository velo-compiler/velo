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

def test_pkg_build_and_run_minimal(tmp_path):
    proj_dir = tmp_path / "mini_proj"
    proj_dir.mkdir()
    m_path = _write(proj_dir, "velo.pkg", """pkg "mini_calc" {
    version: "0.1.0"
    entry: "main.vl"
}
""")
    _write(proj_dir, "main.vl", """use sys.io
act main() {
    io.println("CALC_READY: 42")
}
""")

    # Stage 1: pkg build
    p1_build = _run_stage1(["pkg", "build", m_path])
    assert p1_build.returncode == 0, f"Stage 1 pkg build failed:\n{p1_build.stderr}"
    assert "[Velo] Successfully built binary!" in p1_build.stdout
    exe1 = proj_dir / "mini_calc.exe"
    assert exe1.exists()
    run1 = subprocess.run([str(exe1)], capture_output=True, text=True)
    assert run1.returncode == 0
    assert "CALC_READY: 42" in run1.stdout

    # Stage 1: pkg run
    p1_run = _run_stage1(["pkg", "run", m_path])
    assert p1_run.returncode == 0
    assert "CALC_READY: 42" in p1_run.stdout

    # Stage 2: pkg build
    exe1.unlink()
    p2_build = _run_stage2(["pkg", "build", m_path])
    assert p2_build.returncode == 0, f"Stage 2 pkg build failed:\n{p2_build.stderr}"
    assert "[Velo] Successfully built binary!" in p2_build.stdout
    assert exe1.exists()
    run2 = subprocess.run([str(exe1)], capture_output=True, text=True)
    assert run2.returncode == 0
    assert "CALC_READY: 42" in run2.stdout

    # Stage 2: pkg run
    p2_run = _run_stage2(["pkg", "run", m_path])
    assert p2_run.returncode == 0
    assert "CALC_READY: 42" in p2_run.stdout

def test_pkg_build_nested_dir_and_custom_output(tmp_path):
    proj_dir = tmp_path / "nested_proj"
    src_dir = proj_dir / "src"
    src_dir.mkdir(parents=True)
    m_path = _write(proj_dir, "velo.pkg", """pkg "nested_app" {
    version: "1.0.0"
    entry: "src/entry.vl"
}
""")
    _write(src_dir, "entry.vl", """use sys.io
act main() {
    io.println("NESTED_OK")
}
""")
    custom_out = str(tmp_path / "custom_nested.exe")

    # Stage 1 build with -o
    p1 = _run_stage1(["pkg", "build", m_path, "-o", custom_out])
    assert p1.returncode == 0, f"Stage 1 custom output failed: {p1.stderr}"
    assert os.path.exists(custom_out)
    r1 = subprocess.run([custom_out], capture_output=True, text=True)
    assert r1.returncode == 0
    assert "NESTED_OK" in r1.stdout
    os.remove(custom_out)

    # Stage 2 build with -o
    p2 = _run_stage2(["pkg", "build", m_path, "-o", custom_out])
    assert p2.returncode == 0, f"Stage 2 custom output failed: {p2.stderr}"
    assert os.path.exists(custom_out)
    r2 = subprocess.run([custom_out], capture_output=True, text=True)
    assert r2.returncode == 0
    assert "NESTED_OK" in r2.stdout

def test_pkg_build_bin_dir_detection(tmp_path):
    proj_dir = tmp_path / "bin_proj"
    bin_dir = proj_dir / "bin"
    bin_dir.mkdir(parents=True)
    m_path = _write(proj_dir, "velo.pkg", """pkg "auto_bin_app" {
    version: "0.5.0"
    entry: "main.vl"
}
""")
    _write(proj_dir, "main.vl", """use sys.io
act main() {
    io.println("AUTO_BIN_DETECTED")
}
""")

    expected_exe = bin_dir / "auto_bin_app.exe"

    # Stage 1: should place into bin/ directory automatically
    p1 = _run_stage1(["pkg", "build", m_path])
    assert p1.returncode == 0
    assert expected_exe.exists()
    expected_exe.unlink()

    # Stage 2: should place into bin/ directory automatically
    p2 = _run_stage2(["pkg", "build", m_path])
    assert p2.returncode == 0
    assert expected_exe.exists()
    r2 = subprocess.run([str(expected_exe)], capture_output=True, text=True)
    assert r2.returncode == 0
    assert "AUTO_BIN_DETECTED" in r2.stdout

def test_pkg_build_with_link_flags(tmp_path):
    proj_dir = tmp_path / "link_proj"
    proj_dir.mkdir()
    m_path = _write(proj_dir, "velo.pkg", """pkg "optimized_app" {
    version: "2.0.0"
    entry: "main.vl"
}
link {
    flags: ["-O2"]
}
""")
    _write(proj_dir, "main.vl", """use sys.io
act main() {
    io.println("LINK_FLAGS_OK")
}
""")

    p1 = _run_stage1(["pkg", "build", m_path])
    assert p1.returncode == 0
    p2 = _run_stage2(["pkg", "build", m_path])
    assert p2.returncode == 0

    run_res = _run_stage2(["pkg", "run", m_path])
    assert run_res.returncode == 0
    assert "LINK_FLAGS_OK" in run_res.stdout

def test_pkg_build_entry_not_found(tmp_path):
    proj_dir = tmp_path / "missing_entry_proj"
    proj_dir.mkdir()
    m_path = _write(proj_dir, "velo.pkg", """pkg "broken_app" {
    version: "0.1.0"
    entry: "missing_file.vl"
}
""")
    p1 = _run_stage1(["pkg", "build", m_path])
    assert p1.returncode != 0
    assert "Entry source file not found" in (p1.stdout + p1.stderr)

    p2 = _run_stage2(["pkg", "build", m_path])
    assert p2.returncode != 0
    assert "Entry source file not found" in (p2.stdout + p2.stderr)

def test_pkg_help_parity():
    p1 = _run_stage1(["pkg", "--help"])
    assert p1.returncode == 0
    assert "check" in p1.stdout
    assert "build" in p1.stdout
    assert "run" in p1.stdout

    p2 = _run_stage2(["pkg", "help"])
    assert p2.returncode == 0
    assert "check" in p2.stdout
    assert "build" in p2.stdout
    assert "run" in p2.stdout
