"""
Phase 77 / Task 77.7: Language Completeness -- Language Surface Conformance Test.

Security & Integrity Invariant I77.7:
"Every keyword documented in docs/SPECIFICATION.md section 1.4 must appear in
src/frontend/token.vl and src/frontend/lexer.vl, and every keyword in the lexer
must be documented in the specification, guaranteeing documentation and implementation
cannot drift."
"""

import re
import subprocess
import tempfile
from pathlib import Path
import pytest
from conftest import velo_exe

pytestmark = pytest.mark.fast

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_FILE = REPO_ROOT / "docs" / "SPECIFICATION.md"
TOKEN_FILE = REPO_ROOT / "src" / "frontend" / "token.vl"
LEXER_FILE = REPO_ROOT / "src" / "frontend" / "lexer.vl"
VELO_EXE = velo_exe()


def run_velo(args, cwd=None):
    res = subprocess.run(
        [str(VELO_EXE)] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return res


def extract_keywords_from_spec():
    """Extracts the list of reserved keywords from Section 1.4 of docs/SPECIFICATION.md."""
    content = SPEC_FILE.read_text(encoding="utf-8")
    m = re.search(r"### 1\.4 Keywords\s+The following keywords are reserved in Velo:\s+```\s+([\s\S]*?)```", content)
    assert m is not None, "Failed to find Section 1.4 Keywords table in docs/SPECIFICATION.md"
    raw_kw = m.group(1).split()
    return sorted(list(set(raw_kw)))


def test_spec_contains_all_expected_keywords():
    """Verifies that docs/SPECIFICATION.md section 1.4 contains the complete set of 28 reserved keywords."""
    kws = extract_keywords_from_spec()
    expected = [
        "act", "and", "as", "break", "continue", "data", "defer", "else",
        "extern", "fail", "false", "if", "in", "kind", "let", "loop",
        "mut", "not", "null", "on", "or", "pact", "return", "sizeof",
        "true", "use", "view", "zone"
    ]
    assert kws == expected, f"Mismatch in Section 1.4 keywords: got {kws}, expected {expected}"


def test_all_spec_keywords_exist_in_token_vl():
    """Every keyword from Section 1.4 must have a corresponding TOK_<NAME> in token.vl."""
    kws = extract_keywords_from_spec()
    token_src = TOKEN_FILE.read_text(encoding="utf-8")

    missing_tokens = []
    for kw in kws:
        tok_name = f"TOK_{kw.upper()}"
        if f"let {tok_name}:" not in token_src:
            missing_tokens.append(kw)

    assert not missing_tokens, f"The following keywords in SPECIFICATION.md are missing from token.vl: {missing_tokens}"


def test_all_spec_keywords_recognized_by_lexer():
    """Every keyword from Section 1.4 must be recognized by check_keyword in lexer.vl."""
    kws = extract_keywords_from_spec()
    lexer_src = LEXER_FILE.read_text(encoding="utf-8")

    # Extract check_keyword function body
    m = re.search(r"act check_keyword\(source: string, start: usize, len: usize\) -> i32\s*\{([\s\S]*?)\n\}", lexer_src)
    assert m is not None, "Failed to find check_keyword function in lexer.vl"
    body = m.group(1)

    missing_lexer = []
    for kw in kws:
        tok_name = f"TOK_{kw.upper()}"
        if tok_name not in body:
            missing_lexer.append(kw)

    assert not missing_lexer, f"The following keywords in SPECIFICATION.md are not checked in lexer.vl: {missing_lexer}"


def test_token_name_string_mapping():
    """Every keyword token returns its exact lowercase keyword spelling in token_name()."""
    kws = extract_keywords_from_spec()
    token_src = TOKEN_FILE.read_text(encoding="utf-8")

    for kw in kws:
        tok_name = f"TOK_{kw.upper()}"
        expected_line = f'if kind == {tok_name} {{ return "{kw}" }}'
        assert expected_line in token_src, f"token_name() missing mapping for {tok_name} -> \"{kw}\""


def test_keywords_cannot_be_used_as_variable_identifiers():
    """Strictly reserved non-contextual keywords cannot be declared as variable names."""
    with tempfile.TemporaryDirectory() as td:
        test_kws = ["mut", "let", "if", "else", "true", "false", "null", "sizeof", "view", "pact", "as"]
        for kw in test_kws:
            f = Path(td) / f"bad_{kw}.vl"
            f.write_text(f"act main() {{\n    let {kw} = 10\n}}\n", encoding="utf-8")
            res = run_velo(["run", str(f)], cwd=td)
            assert res.returncode != 0, f"Expected syntax error when declaring variable named '{kw}', but succeeded!"


def test_live_compiler_exercises_all_reserved_keywords():
    """Compiles and executes a single program that validly exercises all 28 reserved keywords."""
    with tempfile.TemporaryDirectory() as td:
        mod_file = Path(td) / "helper.vl"
        mod_file.write_text(
            'view pact Measurable {\n'
            '    act measure(self: @Self) -> i32\n'
            '}\n'
            'view data Box {\n'
            '    size: i32\n'
            '}\n'
            'view act measure(self: @Box) -> i32 {\n'
            '    return self.size\n'
            '}\n',
            encoding="utf-8"
        )
        main_file = Path(td) / "main.vl"
        main_file.write_text(
            'use "helper.vl" :> { Box, Measurable, measure }\n'
            'view kind State {\n'
            '    Active\n'
            '    Done\n'
            '}\n'
            'extern act puts(s: string) -> i32\n'
            'act check_box[T: Measurable](val: @T) -> bool or string {\n'
            '    if val == null {\n'
            '        fail "null box"\n'
            '    }\n'
            '    return val.measure() > 0\n'
            '}\n'
            'act main() {\n'
            '    mut total: i32 = 0\n'
            '    defer total += 1\n'
            '    let b = Box{ size: sizeof(i32) as i32 }\n'
            '    let res = check_box(@b)\n'
            '    if res.ok and (true or false) and not false {\n'
            '        total += 10\n'
            '    } else {\n'
            '        total = 0\n'
            '    }\n'
            '    mut count: i32 = 0\n'
            '    loop i in 0..5 {\n'
            '        if i == 2 { continue }\n'
            '        if i == 4 { break }\n'
            '        count += 1\n'
            '    }\n'
            '    let s: State = State.Active\n'
            '    on s {\n'
            '        .Active => { total += 5 }\n'
            '        .Done => {}\n'
            '    }\n'
            '    zone 1024 {\n'
            '        let tmp = 42\n'
            '    }\n'
            '    assert(total == 15, "all keywords executed correctly")\n'
            '    assert(count == 3, "loop with in, break, continue executed correctly")\n'
            '}\n',
            encoding="utf-8"
        )
        res = run_velo(["run", str(main_file)], cwd=td)
        assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
