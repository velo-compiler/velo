import json
import os
import subprocess
import sys
import pytest

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

NEGATIVE_FLOAT_STRING = """use sys.io
data Point {
    x: f32 = "invalid"
}
act main() -> i32 {
    return 0
}
"""

NEGATIVE_INT_FLOAT = """use sys.io
data Config {
    count: i32 = 1.5
}
act main() -> i32 {
    return 0
}
"""

NEGATIVE_BOOL_INT = """use sys.io
data FlagSet {
    active: bool = 1
}
act main() -> i32 {
    return 0
}
"""

NEGATIVE_STRING_INT = """use sys.io
data User {
    name: string = 42
}
act main() -> i32 {
    return 0
}
"""

POSITIVE_VALID_DEFAULTS = """use sys.io

aka EntityId = u64

data Config {
    x: f32 = 0.0
    y: f32 = -2.5
    count: i32 = 10
    offset: i32 = -3
    name: string = "default"
    enabled: bool = true
    id: EntityId = 1
}

act main() -> i32 {
    let c = Config{}
    io.println("x={c.x}, y={c.y}, count={c.count}, offset={c.offset}, name={c.name}, enabled={c.enabled}, id={c.id}")
    return 0
}
"""

@pytest.mark.parametrize("source,expected_snippet", [
    (NEGATIVE_FLOAT_STRING, "Default value type mismatch for field 'x': expected f32, got string"),
    (NEGATIVE_INT_FLOAT, "Default value type mismatch for field 'count': expected i32, got f32"),
    (NEGATIVE_BOOL_INT, "Default value type mismatch for field 'active': expected bool, got i32"),
    (NEGATIVE_STRING_INT, "Default value type mismatch for field 'name': expected string, got i32"),
])
def test_stage1_negative_default_value_type_mismatch(tmp_path, source, expected_snippet):
    src = _write(tmp_path, "neg_test.vl", source)
    res = _run_stage1(["run", src])
    assert res.returncode != 0, f"Expected non-zero returncode for invalid default, got {res.returncode}"
    combined = res.stdout + res.stderr
    assert expected_snippet in combined, f"Expected '{expected_snippet}' in error output:\n{combined}"

@pytest.mark.parametrize("source,expected_snippet", [
    (NEGATIVE_FLOAT_STRING, "Default value type mismatch for field 'x': expected f32, got string"),
    (NEGATIVE_INT_FLOAT, "Default value type mismatch for field 'count': expected i32, got f32"),
    (NEGATIVE_BOOL_INT, "Default value type mismatch for field 'active': expected bool, got i32"),
    (NEGATIVE_STRING_INT, "Default value type mismatch for field 'name': expected string, got i32"),
])
def test_stage2_negative_default_value_type_mismatch(tmp_path, source, expected_snippet):
    src = _write(tmp_path, "neg_test.vl", source)
    res = _run_stage2(["run", src])
    assert res.returncode != 0, f"Expected non-zero returncode for invalid default, got {res.returncode}"
    combined = res.stdout + res.stderr
    assert expected_snippet in combined, f"Expected '{expected_snippet}' in error output:\n{combined}"

def test_stage1_check_cli_reports_diagnostic(tmp_path):
    src = _write(tmp_path, "check_test.vl", NEGATIVE_FLOAT_STRING)
    res = _run_stage1(["check", "--json", src])
    assert res.returncode != 0
    data = json.loads(res.stdout)
    assert not data["ok"]
    assert any("Default value type mismatch for field 'x': expected f32, got string" in d["message"] for d in data["diagnostics"])

def test_stage2_check_cli_reports_diagnostic(tmp_path):
    src = _write(tmp_path, "check_test.vl", NEGATIVE_FLOAT_STRING)
    res = _run_stage2(["check", "--json", src])
    assert res.returncode != 0
    data = json.loads(res.stdout)
    assert not data["ok"]
    assert any("Default value type mismatch for field 'x': expected f32, got string" in d["message"] for d in data["diagnostics"])

def test_stage1_positive_valid_defaults_execution(tmp_path):
    src = _write(tmp_path, "pos_test.vl", POSITIVE_VALID_DEFAULTS)
    res = _run_stage1(["run", src])
    assert res.returncode == 0, f"Stage 1 failed:\n{res.stderr}"
    assert "x=0.00, y=-2.50, count=10, offset=-3, name=default, enabled=true, id=1" in res.stdout

def test_stage2_positive_valid_defaults_execution(tmp_path):
    src = _write(tmp_path, "pos_test.vl", POSITIVE_VALID_DEFAULTS)
    res = _run_stage2(["run", src])
    assert res.returncode == 0, f"Stage 2 failed:\n{res.stderr}"
    assert "x=0.00, y=-2.50, count=10, offset=-3, name=default, enabled=true, id=1" in res.stdout
