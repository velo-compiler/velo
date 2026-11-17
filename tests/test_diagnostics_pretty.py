"""6.3 S1: source-snippet blocks under positioned diagnostics on both stages.

The one-liner wire rows keep their exact bytes (the blocks are purely
additive). Each block is:
    {file}:{line}:{col}: {severity}: {message}
    {line} | {line_text}
    " "*(w+1) + "| " + " "*(col-1) + "^"      (w = decimal digits of line)
with line_text = the row's source line, each tab flattened to one space, a
trailing \\r stripped; past-EOF lines render an empty snippet.

The --json lanes stay block-free: Stage 2's capture noise rule (check.vl,
6.3 S1) skips snippet lines; Stage 1's json branch never prints rows.
Stream asymmetry (pre-existing per-lane shapes): Stage 1 check rows print
to stderr, Stage 2 check/run rows+blocks print to stdout — native tests
therefore assert on stdout + stderr combined.
Full-byte BLOCK-HEADER parity across stages is limited by the pre-existing
6.7 wording divergence (Stage 1 embellishes rows with "(got ...)"), so
cross-stage parity pins position + gutter + caret shape; wording pins stay
per-stage (same policy as test_check_cli.py).
"""
import json
import os
import subprocess
import sys

import pytest
from conftest import velo_exe


PARSE_BROKEN = """use sys.io

pickle = definitely_not_a_decl

act main() -> i32 {
    return 0
}
"""

EOF_BRACE = """use sys.io

act main() -> i32 {
    let x = 5
"""

TABBED = """use sys.io

\t\ttabbed_junk

act main() -> i32 {
    return 0
}
"""

DUP_ALIAS = """use sys.io

aka A = u64
aka A = u32

act main() -> i32 {
    return 0
}
"""

SEMANTIC_UNDECLARED = """use sys.io

act main() -> i32 {
    let x = foo + 10
    return 0
}
"""

SEMANTIC_MULTI_ERROR = """use sys.io

act main() -> i32 {
    let x = foo + 10
    return "mismatch"
}
"""

MULTI_FILE_MAIN = """use sys.io
use "sub.vl"

act main() -> i32 {
    let x = foo + 10
    return helper()
}
"""

MULTI_FILE_SUB = """act helper() -> i32 {
    return 42
}
"""


def _write(tmp_path, name, content):
    p = tmp_path / name
    with open(p, "w", newline="\n", encoding="utf-8") as fh:
        fh.write(content)
    return str(p).replace("\\", "/")


def _run_stage1(args):
    return subprocess.run(
        [sys.executable, "velo.py"] + args,
        capture_output=True,
        text=True
    )


def _run_native(args):
    if not os.path.exists(str(velo_exe())):
        pytest.skip("bin/velo.exe not built; skipping native test")
    return subprocess.run(
        [str(velo_exe())] + args,
        capture_output=True,
        text=True
    )


# ---------------- Stage 1 (python) ----------------

def test_row_plus_block_stage1(tmp_path):
    path = _write(tmp_path, "broken.vl", PARSE_BROKEN)
    result = _run_stage1(["check", path])
    assert result.returncode == 1
    err = result.stderr
    # The wire row keeps its exact bytes.
    assert f"[Velo Error] {path}:3:1 - Unexpected top-level token 'pickle'" in err
    # The additive block: header, gutter, caret — in that order.
    header_pos = err.index(f"{path}:3:1: error: Unexpected top-level token 'pickle'")
    gutter_pos = err.index("3 | pickle = definitely_not_a_decl")
    caret_pos = err.index("  | ^^^^^^")
    row_pos = err.index("[Velo Error]")
    assert row_pos < header_pos < gutter_pos < caret_pos


def test_json_lane_block_free_stage1(tmp_path):
    path = _write(tmp_path, "broken.vl", PARSE_BROKEN)
    result = _run_stage1(["check", path, "--json"])
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["ok"] is False
    assert len(report["diagnostics"]) == 1
    assert (report["diagnostics"][0]["line"], report["diagnostics"][0]["col"]) == (3, 1)
    # The JSON lane never grows a snippet payload or extra diagnostics.
    assert "^" not in result.stdout
    assert "pickle = definitely_not_a_decl" not in result.stdout


def test_eof_row_empty_snippet_stage1(tmp_path):
    path = _write(tmp_path, "eof.vl", EOF_BRACE)
    result = _run_stage1(["check", path])
    assert result.returncode == 1
    err = result.stderr
    assert "[Velo Error]" in err
    assert "Expected '}' at end of block (got EOF '')" in err
    # Row 5 is the empty trailing line: empty snippet, caret at col 1.
    assert "5 | " in err
    assert "  | ^" in err


def test_tab_flatten_stage1(tmp_path):
    path = _write(tmp_path, "tab.vl", TABBED)
    result = _run_stage1(["check", path])
    assert result.returncode == 1
    err = result.stderr
    # Tabs never reach the block gutter: flattened to one space each.
    assert "\t" not in err
    assert "  tabbed_junk" in err
    # The caret line still exists for the tabbed row (col from token scan).
    carets = [ln for ln in err.splitlines() if ln.startswith("  | ") and "^" in ln]
    assert len(carets) >= 1


def test_run_lane_block_stage1(tmp_path):
    path = _write(tmp_path, "broken.vl", PARSE_BROKEN)
    result = _run_stage1(["run", path])
    assert result.returncode == 1
    err = result.stderr
    assert "Parser Error at line 3, col 1: Unexpected top-level token 'pickle'" in err
    assert f"{path}:3:1: error: Unexpected top-level token 'pickle'" in err
    assert "3 | pickle = definitely_not_a_decl" in err


# ---------------- Stage 2 (native) ----------------

def test_row_plus_block_native(tmp_path):
    path = _write(tmp_path, "broken.vl", PARSE_BROKEN)
    result = _run_native(["check", path])
    assert result.returncode == 1
    err = result.stdout + result.stderr
    # Recovered parse errors each keep their row; blocks ride every row.
    assert err.count(":3:1: error: Unexpected top-level token") == 1
    assert ":3:8: error: Unexpected top-level token" in err
    assert ":3:10: error: Unexpected top-level token" in err
    gutters = [ln for ln in err.splitlines() if ln == "3 | pickle = definitely_not_a_decl"]
    assert len(gutters) == 3
    assert "  | ^^^^^^" in err  # col 1: pickle (len 6)
    assert "  |        ^" in err  # col 8: = (len 1)
    assert "  |          ^^^^^^^^^^^^^^^^^^^^^" in err  # col 10: definitely_not_a_decl (len 21)


def test_json_lane_block_free_native(tmp_path):
    path = _write(tmp_path, "broken.vl", PARSE_BROKEN)
    result = _run_native(["check", path, "--json"])
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["ok"] is False
    # Each recovered row is a real diagnostic; snippet lines never become
    # sham unpositioned entries (the 6.3 S1 noise rule in check.vl).
    seen = {(d["line"], d["col"]) for d in report["diagnostics"]}
    assert seen == {(3, 1), (3, 8), (3, 10)}
    assert all(d["line"] > 0 for d in report["diagnostics"])
    # No snippet bytes leak into the JSON lane.
    assert "pickle = definitely" not in result.stdout
    assert "error: Unexpected" not in result.stdout


def test_eof_row_empty_snippet_native(tmp_path):
    path = _write(tmp_path, "eof.vl", EOF_BRACE)
    result = _run_native(["check", path])
    assert result.returncode == 1
    err = result.stdout + result.stderr
    assert "Expected '}' at end of block" in err
    assert "5 | " in err
    assert "  | ^" in err


def test_tab_flatten_native(tmp_path):
    path = _write(tmp_path, "tab.vl", TABBED)
    result = _run_native(["check", path])
    assert result.returncode == 1
    err = result.stdout + result.stderr
    assert "\t" not in err
    assert "  tabbed_junk" in err
    carets = [ln for ln in err.splitlines() if ln.startswith("  | ") and "^" in ln]
    assert len(carets) >= 1


def test_run_lane_block_native(tmp_path):
    path = _write(tmp_path, "broken.vl", PARSE_BROKEN)
    result = _run_native(["run", path])
    err = result.stdout + result.stderr
    assert ":3:1: error: Unexpected top-level token" in err
    assert "3 | pickle = definitely_not_a_decl" in err


def test_warning_rows_get_no_block_native(tmp_path):
    """Warnings are row-only in S1: no snippet header, rc stays 0."""
    path = _write(tmp_path, "dup.vl", DUP_ALIAS)
    result = _run_native(["check", path])
    assert result.returncode == 0
    err = result.stderr + result.stdout
    assert "Duplicate type alias" in err
    assert "[Velo Warning]" in err
    # No block ever rides a warning row.
    assert "error: Duplicate type alias" not in err
    assert "warning: Duplicate type alias" not in err


# ---------------- 6.3 S2: Semantic-row blocks (Stage 2) ----------------

def test_semantic_row_plus_block_native(tmp_path):
    path = _write(tmp_path, "sem_undec.vl", SEMANTIC_UNDECLARED)
    result = _run_native(["check", path])
    assert result.returncode == 1
    err = result.stdout + result.stderr
    assert f"[Velo Error] semantic:4:13 - Undeclared identifier" in err
    header_pos = err.index(f"{path}:4:13: error: Undeclared identifier")
    gutter_pos = err.index("4 |     let x = foo + 10")
    caret_pos = err.index("  |             ^")
    row_pos = err.index("[Velo Error] semantic:4:13 - Undeclared identifier")
    assert row_pos < header_pos < gutter_pos < caret_pos
    assert "[Velo Error] Semantic analysis failed with 1 errors." in err
    assert "error: Semantic analysis failed" not in err


def test_semantic_multi_row_blocks_native(tmp_path):
    path = _write(tmp_path, "sem_multi.vl", SEMANTIC_MULTI_ERROR)
    result = _run_native(["check", path])
    assert result.returncode == 1
    err = result.stdout + result.stderr
    assert "[Velo Error] semantic:4:13 - Undeclared identifier" in err
    assert f"{path}:4:13: error: Undeclared identifier" in err
    assert "4 |     let x = foo + 10" in err
    assert "  |             ^" in err
    assert "[Velo Error] semantic:5:5 - Return type mismatch" in err
    assert f"{path}:5:5: error: Return type mismatch" in err
    assert "5 |     return \"mismatch\"" in err
    assert "  |     ^" in err
    assert "[Velo Error] Semantic analysis failed with 2 errors." in err


def test_semantic_multi_file_block_less_native(tmp_path):
    _write(tmp_path, "sub.vl", MULTI_FILE_SUB)
    path = _write(tmp_path, "main.vl", MULTI_FILE_MAIN)
    result = _run_native(["check", path])
    assert result.returncode == 1
    err = result.stdout + result.stderr
    assert "[Velo Error] semantic:5:13 - Undeclared identifier" in err
    assert f"{path}:5:13: error: Undeclared identifier" not in err
    assert "5 |     let x = foo + 10" not in err
    assert "[Velo Error] Semantic analysis failed with 1 errors." in err


def test_semantic_json_lane_block_free_native(tmp_path):
    path = _write(tmp_path, "sem_multi.vl", SEMANTIC_MULTI_ERROR)
    result = _run_native(["check", path, "--json"])
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["ok"] is False
    assert len(report["diagnostics"]) == 2
    assert report["diagnostics"][0]["file"] == path
    assert (report["diagnostics"][0]["line"], report["diagnostics"][0]["col"]) == (4, 13)
    assert (report["diagnostics"][1]["line"], report["diagnostics"][1]["col"]) == (5, 5)
    assert "^" not in result.stdout
    assert "let x = foo" not in result.stdout


SEM_STAGE1 = """use sys.io

data Vec4 {
    x: f32 = 0.0
    z: f32
}

act main() -> i32 {
    let v = Vec4{ x: 1.0 }
    return 0
}
"""


def test_semantic_row_stage1_block_free(tmp_path):
    path = _write(tmp_path, "sem_st1.vl", SEM_STAGE1)
    result = _run_stage1(["check", path])
    assert result.returncode == 1
    err = result.stderr
    assert "[Velo Error] Struct literal 'Vec4' is missing field 'z'" in err
    # Unpositioned semantic rows in Stage 1 stay block-less.
    assert "^" not in err
    assert "8 | " not in err


# ---------------- Cross-stage parity (shape, not wording) ----------------

def test_block_shape_parity_gutter_and_caret(tmp_path):
    """6.7 divergence means row WORDINGS differ; the block under the FIRST
    row pins the same gutter line and the same col-1 caret bytes."""
    if not os.path.exists(str(velo_exe())):
        pytest.skip("bin/velo.exe not built; skipping native test")
    path = _write(tmp_path, "broken.vl", PARSE_BROKEN)
    s1 = _run_stage1(["check", path])
    s2 = _run_native(["check", path])
    g1 = [ln for ln in s1.stderr.splitlines() if ln == "3 | pickle = definitely_not_a_decl"]
    g2 = [ln for ln in (s2.stdout + s2.stderr).splitlines() if ln == "3 | pickle = definitely_not_a_decl"]
    assert g1 and g2
    assert "  | ^^^^^^" in s1.stderr and "  | ^^^^^^" in (s2.stdout + s2.stderr)


def test_block_position_parity_first_row(tmp_path):
    if not os.path.exists(str(velo_exe())):
        pytest.skip("bin/velo.exe not built; skipping native test")
    path = _write(tmp_path, "eof.vl", EOF_BRACE)
    py_report = json.loads(_run_stage1(["check", path, "--json"]).stdout)
    native_report = json.loads(_run_native(["check", path, "--json"]).stdout)
    py_first = py_report["diagnostics"][0]
    native_first = native_report["diagnostics"][0]
    assert (py_first["line"], py_first["col"]) == (native_first["line"], native_first["col"]) == (5, 1)


# ---------------- 6.3 S3: Span carets and lexer warnings ----------------

def test_lexer_warning_blocks_native(tmp_path):
    if not os.path.exists(str(velo_exe())):
        pytest.skip("bin/velo.exe not built; skipping native test")
    # Unclosed block comment: warning row + warning block with span carets (^^)
    p1 = _write(tmp_path, "warn_comment.vl", "/* unclosed comment\nact main() -> i32 { return 0; }\n")
    res1 = _run_native(["check", p1])
    err1 = res1.stdout + res1.stderr
    assert "[Velo Warning] lexer:1:1 - Unclosed block comment" in err1
    assert f"{p1}:1:1: warning: Unclosed block comment" in err1
    assert "1 | /* unclosed comment" in err1
    assert "  | ^^" in err1

    # Unknown character: warning row + warning block with point caret (^)
    p2 = _write(tmp_path, "warn_char.vl", "act main() -> i32 { let $ = 0; return 0; }\n")
    res2 = _run_native(["check", p2])
    err2 = res2.stdout + res2.stderr
    assert "[Velo Warning] lexer:1:25 - Unknown character encountered" in err2
    assert f"{p2}:1:25: warning: Unknown character encountered" in err2
    assert "1 | act main() -> i32 { let $ = 0; return 0; }" in err2
    assert "  |                         ^" in err2


def test_run_lane_span_caret_stage1(tmp_path):
    path = _write(tmp_path, "broken.vl", PARSE_BROKEN)
    res = _run_stage1(["run", path])
    assert res.returncode == 1
    assert "  | ^^^^^^" in res.stderr


# ---------------- 6.3 S4: Colors & --color auto|always|never ----------------

def test_color_modes_stage1(tmp_path):
    path = _write(tmp_path, "broken.vl", PARSE_BROKEN)

    # auto (default) resolves to never on Stage 1
    res_default = _run_stage1(["check", path])
    assert "\x1b[" not in res_default.stderr
    assert "\x1b[" not in res_default.stdout

    # explicit never matches default
    res_never = _run_stage1(["check", path, "--color=never"])
    assert res_never.stderr == res_default.stderr

    # explicit always renders colors
    res_always = _run_stage1(["check", path, "--color=always"])
    err = res_always.stderr
    assert "\x1b[31merror\x1b[0m" in err
    assert "\x1b[1m^^^^^^\x1b[0m" in err
    # Sacred wire row is never colored
    assert "[Velo Error] " in err
    assert "\x1b[31m[Velo Error]" not in err

    # --json with --color=always stays strictly color-free
    res_json = _run_stage1(["check", path, "--json", "--color=always"])
    assert "\x1b[" not in res_json.stdout
    assert "\x1b[" not in res_json.stderr
    data = json.loads(res_json.stdout)
    assert data["ok"] is False


def test_color_modes_native(tmp_path):
    if not os.path.exists(str(velo_exe())):
        pytest.skip("bin/velo.exe not built; skipping native test")
    path = _write(tmp_path, "broken.vl", PARSE_BROKEN)

    # auto (default) resolves to never on Stage 2
    res_default = _run_native(["check", path])
    out_default = res_default.stdout + res_default.stderr
    assert "\x1b[" not in out_default

    # explicit never matches default
    res_never = _run_native(["check", path, "--color=never"])
    out_never = res_never.stdout + res_never.stderr
    assert out_never == out_default

    # explicit always renders colors: error (red 31) and carets (bold 1)
    res_always = _run_native(["check", path, "--color=always"])
    out_always = res_always.stdout + res_always.stderr
    assert "\x1b[31merror\x1b[0m" in out_always
    assert "\x1b[1m^^^^^^\x1b[0m" in out_always
    # Sacred wire row is never colored
    assert "[Velo Error] " in out_always
    assert "\x1b[31m[Velo Error]" not in out_always

    # Warning severity (yellow 33) and carets (bold 1)
    p_warn = _write(tmp_path, "warn.vl", "/* unclosed\nact main() -> i32 { return 0; }\n")
    res_warn = _run_native(["check", p_warn, "--color=always"])
    out_warn = res_warn.stdout + res_warn.stderr
    assert "\x1b[33mwarning\x1b[0m" in out_warn
    assert "\x1b[1m^^\x1b[0m" in out_warn
    assert "[Velo Warning] " in out_warn
    assert "\x1b[33m[Velo Warning]" not in out_warn

    # Semantic error summary line in bold 1
    p_sem = _write(tmp_path, "sem.vl", SEMANTIC_MULTI_ERROR)
    res_sem = _run_native(["check", p_sem, "--color=always"])
    out_sem = res_sem.stdout + res_sem.stderr
    assert "\x1b[1m[Velo Error] Semantic analysis failed with 2 errors.\x1b[0m" in out_sem

    # --json with --color=always stays strictly color-free
    res_json = _run_native(["check", path, "--json", "--color=always"])
    out_json = res_json.stdout + res_json.stderr
    assert "\x1b[" not in out_json
    data = json.loads(res_json.stdout)
    assert data["ok"] is False


