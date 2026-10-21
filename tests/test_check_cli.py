"""Machine-readable diagnostics CLI ('velo check [--json]') on both compilers.

Each compiler keeps its own pipeline truths (Stage 1 fails fast at the first
lex/parse error and reports unpositioned semantic ValueErrors; the self-hosted
compiler collects many parse errors and warns instead of failing on duplicate
aliases). Tests therefore assert the shared JSON schema, exit codes, and
first-parse-error position parity - and per-compiler expectations where the
compilers legitimately differ (see gaps.md 6.7).
"""
import json
import os
import subprocess
import sys
import pytest

DIAG_KEYS = {"file", "line", "col", "severity", "message"}

VALID_PROGRAM = """use sys.io

act main() -> i32 {
    io.println("check me")
    return 0
}
"""

# Retired-keyword-style junk at top level: both parsers report the first
# diagnostic at the offending token's position (line 3, col 1).
PARSE_BROKEN_PROGRAM = """use sys.io

pickle = definitely_not_a_decl

act main() -> i32 {
    return 0
}
"""

MISSING_FIELD_PROGRAM = """use sys.io

data Vec4 {
    x: f32 = 0.0
    z: f32
}

act main() -> i32 {
    let v = Vec4{ x: 1.0 }
    io.println("v.z={v.z}")
    return 0
}
"""

# Stage 2 emits a warning and keeps compiling; Stage 1 raises ValueError.
DUP_ALIAS_PROGRAM = """use sys.io

aka A = u64
aka A = u32

act main() -> i32 {
    return 0
}
"""


def _write(tmp_path, name, content):
    p = tmp_path / name
    with open(p, "w", newline="\n", encoding="utf-8") as fh:
        fh.write(content)
    return str(p)


def _run_stage1(args):
    return subprocess.run(
        [sys.executable, "velo.py"] + args,
        capture_output=True,
        text=True
    )


def _run_native(args):
    if not os.path.exists("bin/velo.exe"):
        pytest.skip("bin/velo.exe not built; skipping native test")
    return subprocess.run(
        ["bin/velo.exe"] + args,
        capture_output=True,
        text=True
    )


def _assert_schema(report, path, strict_file):
    assert set(report.keys()) == {"file", "ok", "diagnostics"}
    assert report["file"] == path
    assert isinstance(report["ok"], bool)
    assert isinstance(report["diagnostics"], list)
    for diag in report["diagnostics"]:
        assert set(diag.keys()) == DIAG_KEYS
        assert isinstance(diag["line"], int) and diag["line"] >= 0
        assert isinstance(diag["col"], int) and diag["col"] >= 0
        assert diag["severity"] in ("error", "warning")
        assert isinstance(diag["message"], str) and diag["message"]
        assert diag["file"]
        if strict_file:
            assert diag["file"] == path


def test_check_json_valid_stage1(tmp_path):
    path = _write(tmp_path, "valid.vl", VALID_PROGRAM)
    result = _run_stage1(["check", path, "--json"])
    assert result.returncode == 0
    report = json.loads(result.stdout)
    _assert_schema(report, path, strict_file=True)
    assert report["ok"] is True
    assert report["diagnostics"] == []


def test_check_json_parse_error_stage1(tmp_path):
    path = _write(tmp_path, "broken.vl", PARSE_BROKEN_PROGRAM)
    result = _run_stage1(["check", path, "--json"])
    assert result.returncode == 1
    report = json.loads(result.stdout)
    _assert_schema(report, path, strict_file=True)
    assert report["ok"] is False
    assert len(report["diagnostics"]) >= 1
    first = report["diagnostics"][0]
    assert (first["line"], first["col"]) == (3, 1)
    assert first["severity"] == "error"


def test_check_json_semantic_error_stage1(tmp_path):
    path = _write(tmp_path, "missing.vl", MISSING_FIELD_PROGRAM)
    result = _run_stage1(["check", path, "--json"])
    assert result.returncode == 1
    report = json.loads(result.stdout)
    _assert_schema(report, path, strict_file=True)
    assert report["ok"] is False
    assert len(report["diagnostics"]) >= 1
    assert "missing field" in report["diagnostics"][0]["message"]


def test_check_json_missing_file_stage1(tmp_path):
    path = str(tmp_path / "does_not_exist.vl")
    result = _run_stage1(["check", path, "--json"])
    assert result.returncode == 1
    report = json.loads(result.stdout)
    _assert_schema(report, path, strict_file=True)
    assert report["ok"] is False
    assert len(report["diagnostics"]) == 1
    assert report["diagnostics"][0]["line"] == 0


def test_check_pretty_valid_stage1(tmp_path):
    path = _write(tmp_path, "valid.vl", VALID_PROGRAM)
    result = _run_stage1(["check", path])
    assert result.returncode == 0
    assert "Check passed" in result.stdout + result.stderr


def test_check_pretty_parse_error_stage1(tmp_path):
    path = _write(tmp_path, "broken.vl", PARSE_BROKEN_PROGRAM)
    result = _run_stage1(["check", path])
    assert result.returncode == 1
    assert "[Velo Error]" in result.stdout + result.stderr


def test_check_json_valid_native(tmp_path):
    path = _write(tmp_path, "valid.vl", VALID_PROGRAM)
    result = _run_native(["check", path, "--json"])
    assert result.returncode == 0
    report = json.loads(result.stdout)
    _assert_schema(report, path, strict_file=False)
    assert report["ok"] is True
    assert report["diagnostics"] == []


def test_check_json_parse_error_native(tmp_path):
    path = _write(tmp_path, "broken.vl", PARSE_BROKEN_PROGRAM)
    result = _run_native(["check", path, "--json"])
    assert result.returncode == 1
    report = json.loads(result.stdout)
    _assert_schema(report, path, strict_file=False)
    assert report["ok"] is False
    assert len(report["diagnostics"]) >= 1
    assert report["diagnostics"][0]["severity"] == "error"
    # Guard against the Stage 2 codegen double-evaluation class
    # (`f(x) != null` re-running the pipeline; gaps.md 6.7 item 8).
    seen = {(d["line"], d["col"], d["message"]) for d in report["diagnostics"]}
    assert len(seen) == len(report["diagnostics"]), "duplicate diagnostics detected"


def test_check_json_semantic_error_native(tmp_path):
    path = _write(tmp_path, "missing.vl", MISSING_FIELD_PROGRAM)
    result = _run_native(["check", path, "--json"])
    assert result.returncode == 1
    report = json.loads(result.stdout)
    _assert_schema(report, path, strict_file=False)
    assert report["ok"] is False
    assert len(report["diagnostics"]) >= 1
    assert "missing field" in report["diagnostics"][0]["message"]


def test_check_json_missing_file_native(tmp_path):
    path = str(tmp_path / "does_not_exist.vl")
    result = _run_native(["check", path, "--json"])
    assert result.returncode == 1
    report = json.loads(result.stdout)
    _assert_schema(report, path, strict_file=False)
    assert report["ok"] is False
    assert len(report["diagnostics"]) >= 1
    assert report["diagnostics"][0]["line"] == 0


def test_check_pretty_native(tmp_path):
    path = _write(tmp_path, "valid.vl", VALID_PROGRAM)
    result = _run_native(["check", path])
    assert result.returncode == 0
    assert "Check passed" in result.stdout + result.stderr


def test_check_pretty_parse_error_native(tmp_path):
    path = _write(tmp_path, "broken.vl", PARSE_BROKEN_PROGRAM)
    result = _run_native(["check", path])
    assert result.returncode == 1
    assert "[Velo Error]" in result.stdout + result.stderr


def test_check_parse_error_position_parity(tmp_path):
    """First parse diagnostic must land on the same line/col in both compilers."""
    if not os.path.exists("bin/velo.exe"):
        pytest.skip("bin/velo.exe not built; skipping native test")
    path = _write(tmp_path, "broken.vl", PARSE_BROKEN_PROGRAM)
    py_report = json.loads(_run_stage1(["check", path, "--json"]).stdout)
    native_report = json.loads(_run_native(["check", path, "--json"]).stdout)
    py_first = py_report["diagnostics"][0]
    native_first = native_report["diagnostics"][0]
    assert (py_first["line"], py_first["col"]) == (native_first["line"], native_first["col"])
    assert native_report["ok"] is False and py_report["ok"] is False


def test_check_native_warning_keeps_ok(tmp_path):
    """Stage 2 report warnings and keep compiling (ok stays true, exit 0)."""
    path = _write(tmp_path, "dup_alias.vl", DUP_ALIAS_PROGRAM)
    result = _run_native(["check", path, "--json"])
    assert result.returncode == 0
    report = json.loads(result.stdout)
    _assert_schema(report, path, strict_file=False)
    assert report["ok"] is True
    warnings = [d for d in report["diagnostics"] if d["severity"] == "warning"]
    assert len(warnings) >= 1
    assert "Duplicate type alias" in warnings[0]["message"]


def test_check_stage1_dup_alias_is_error(tmp_path):
    """Documented divergence: Stage 1 treats duplicate aliases as errors."""
    path = _write(tmp_path, "dup_alias.vl", DUP_ALIAS_PROGRAM)
    result = _run_stage1(["check", path, "--json"])
    assert result.returncode == 1
    report = json.loads(result.stdout)
    _assert_schema(report, path, strict_file=True)
    assert report["ok"] is False
    assert "Duplicate type alias" in report["diagnostics"][0]["message"]
