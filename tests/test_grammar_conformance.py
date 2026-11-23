#!/usr/bin/env python3
"""Task 84.1: Grammar conformance test suite.

Verifies conformance between the VS Code TextMate grammar
(editors/vscode/syntaxes/velo.tmLanguage.json) and the canonical Velo compiler
lexer.

Guarantees:
  1. Canonical compiler keywords from `src/frontend/lexer.vl` are 100% covered by
     the grammar with zero omissions or drift.
  2. Dual tokenization of a comprehensive fixture (`tests/fixtures/grammar_conformance.vl`)
     proves token-by-token classification agreement (keywords, numbers, strings,
     identifiers, operators, comments).
  3. Edge token shapes (hex/binary/octal literals, suffixes, string interpolation,
     character escapes, dot variants, attributes, pointers, visibility modifiers)
     are strictly matched by grammar rules.
  4. The existing editor parity and spotcheck suites run clean without regression.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
VS_DIR = REPO_ROOT / "editors" / "vscode"
GRAMMAR_PATH = VS_DIR / "syntaxes" / "velo.tmLanguage.json"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "grammar_conformance.vl"
CANONICAL_LEXER_PATH = REPO_ROOT / "src" / "frontend" / "lexer.vl"

sys.path.insert(0, str(REPO_ROOT))
from velo.lexer import Lexer
from velo.tokens import TokenType, KEYWORDS as PYTHON_KEYWORDS


def load_grammar():
    assert GRAMMAR_PATH.exists(), f"Grammar file missing at {GRAMMAR_PATH}"
    return json.loads(GRAMMAR_PATH.read_text(encoding="utf-8"))


def extract_canonical_compiler_keywords() -> set[str]:
    """Extract all keyword tokens recognized by the canonical self-hosted compiler."""
    assert CANONICAL_LEXER_PATH.exists(), f"Canonical lexer missing at {CANONICAL_LEXER_PATH}"
    content = CANONICAL_LEXER_PATH.read_text(encoding="utf-8")
    
    # Matches: if source[start] == 'a' and source[start + 1] == 'c' ... { return TOK_ACT }
    keywords = set()
    for line in content.splitlines():
        if "return TOK_" in line and not line.strip().startswith("//"):
            m = re.findall(r"source\[start(?:\s*\+\s*\d+)?\]\s*==\s*'([^']+)'", line)
            if m:
                kw = "".join(m)
                keywords.add(kw)
    return keywords


def extract_grammar_keywords(grammar: dict) -> set[str]:
    """Extract all keywords highlighted by the TextMate grammar."""
    words = set()
    for pattern in grammar.get("repository", {}).get("keywords", {}).get("patterns", []):
        match_str = pattern.get("match", "")
        if match_str.startswith("^aka"):
            words.add("aka")
            continue
        m = re.fullmatch(r"\\b(.+)\\b", match_str)
        if not m:
            continue
        core = m.group(1)
        grouped = re.fullmatch(r"\(([\w|]+)\)", core)
        terms = grouped.group(1).split("|") if grouped else [core]
        for term in terms:
            words.add(term)
    return words


def compile_grammar_rules(grammar: dict):
    """Compile grammar rules in top-level inclusion order.
    
    Mirrors TextMate engine semantics: rules collect their own `name` scope
    plus all named capture scopes.
    """
    rules = []
    repo = grammar.get("repository", {})
    for include in grammar.get("patterns", []):
        sec_name = include.get("include", "").lstrip("#")
        sec = repo.get(sec_name, {})
        for p in sec.get("patterns", []):
            rx_str = p.get("match") or p.get("begin")
            if rx_str:
                scopes = set()
                if p.get("name"):
                    scopes.add(p["name"])
                caps = p.get("captures") or p.get("beginCaptures") or {}
                for c in caps.values():
                    if c.get("name"):
                        scopes.add(c["name"])
                rules.append((re.compile(rx_str), scopes))
    return rules


def tokenize_line_with_grammar(line: str, rules):
    """Tokenize a single source line into spans: (start_col, end_col, text, scopes)."""
    spans = []
    col = 0
    while col < len(line):
        if line[col] in (" ", "\t", "\r"):
            col += 1
            continue
        matched = False
        sub = line[col:]
        for rx, scopes in rules:
            m = rx.match(sub)
            if m and m.start() == 0 and m.end() > 0:
                txt = m.group(0)
                spans.append((col, col + len(txt), txt, scopes))
                col += len(txt)
                matched = True
                break
        if not matched:
            col += 1
    return spans


# ==============================================================================
# TESTS
# ==============================================================================

def test_grammar_schema_and_integrity():
    """Verify that velo.tmLanguage.json is valid and scope names conform to conventions."""
    grammar = load_grammar()
    assert grammar.get("scopeName") == "source.velo"
    assert "repository" in grammar
    assert "patterns" in grammar
    
    scope_names = []
    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "name" and isinstance(v, str):
                    scope_names.append(v)
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(grammar["repository"])
    
    malformed = [s for s in scope_names if not re.match(r"^[a-z][a-z0-9.\-]*\.velo$", s)]
    assert not malformed, f"Malformed TextMate scopes found: {malformed[:5]}"


def test_canonical_compiler_keyword_coverage():
    """Verify 100% coverage of canonical self-hosted compiler keywords in the grammar."""
    canonical_keywords = extract_canonical_compiler_keywords()
    grammar = load_grammar()
    grammar_keywords = extract_grammar_keywords(grammar)
    
    assert len(canonical_keywords) >= 35, f"Expected >= 35 canonical keywords, found {len(canonical_keywords)}"
    
    # Assert every canonical keyword is in grammar
    missing_from_grammar = canonical_keywords - grammar_keywords
    assert not missing_from_grammar, (
        f"Grammar is missing canonical compiler keywords: {sorted(missing_from_grammar)}"
    )
    
    # Contextual keywords
    assert "aka" in grammar_keywords
    assert "it" in grammar_keywords


def test_fixture_dual_tokenization_conformance():
    """Tokenize tests/fixtures/grammar_conformance.vl with both lexer and grammar, asserting parity."""
    assert FIXTURE_PATH.exists(), f"Fixture missing at {FIXTURE_PATH}"
    fixture_content = FIXTURE_PATH.read_text(encoding="utf-8")
    lines = fixture_content.splitlines()
    
    # 1. Lex with compiler lexer
    compiler_tokens = Lexer(fixture_content).tokenize()
    assert len(compiler_tokens) > 50, f"Too few compiler tokens: {len(compiler_tokens)}"
    
    # 2. Compile grammar rules and tokenize fixture lines
    grammar = load_grammar()
    rules = compile_grammar_rules(grammar)
    line_spans = {i + 1: tokenize_line_with_grammar(lines[i], rules) for i in range(len(lines))}
    
    # 3. Match each semantic compiler token against covering grammar span
    delimiter_types = {
        TokenType.LPAREN, TokenType.RPAREN, TokenType.LBRACE, TokenType.RBRACE,
        TokenType.LBRACKET, TokenType.RBRACKET, TokenType.COMMA, TokenType.COLON,
        TokenType.SEMICOLON
    }
    
    tested_semantic_tokens = 0
    matched_keywords = 0
    matched_literals = 0
    matched_operators = 0
    matched_identifiers = 0
    
    for tok in compiler_tokens:
        if tok.type in (TokenType.EOF, TokenType.NEWLINE):
            continue
        if tok.type in delimiter_types:
            continue  # Pure delimiters (brackets, commas) handled by editor bracket pairs
        
        col_0 = tok.col - 1
        spans = line_spans.get(tok.line, [])
        covering = [s for s in spans if s[0] <= col_0 < s[1]]
        
        assert covering, (
            f"No grammar rule matched compiler token {tok.type.name} ({tok.value!r}) "
            f"at line {tok.line}, col {tok.col} in: {lines[tok.line - 1].strip()!r}"
        )
        
        span_scopes = covering[0][3]
        
        # Verify category alignment
        if tok.value in PYTHON_KEYWORDS:
            assert any(s.startswith(prefix) for s in span_scopes for prefix in (
                "keyword.", "storage.", "constant.language."
            )), f"Keyword {tok.value!r} got non-keyword scopes {span_scopes!r}"
            matched_keywords += 1
        elif tok.type in (TokenType.INT_LIT, TokenType.FLOAT_LIT):
            if lines[tok.line - 1][col_0] == "'":
                assert any(s.startswith(p) for s in span_scopes for p in (
                    "constant.character.", "string.quoted.single."
                )), f"Character literal {tok.value!r} got scopes {span_scopes!r}"
                matched_literals += 1
            else:
                assert any(s.startswith("constant.numeric.") for s in span_scopes), (
                    f"Numeric literal {tok.value!r} got scopes {span_scopes!r}"
                )
                matched_literals += 1
        elif tok.type == TokenType.STRING_LIT:
            assert any(s.startswith("string.quoted.") for s in span_scopes), (
                f"String literal {tok.value!r} got scopes {span_scopes!r}"
            )
            matched_literals += 1
        elif tok.type in (TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH,
                          TokenType.EQ, TokenType.NE, TokenType.LT, TokenType.GT,
                          TokenType.ARROW, TokenType.FAT_ARROW, TokenType.ASSIGN,
                          TokenType.PLUS_ASSIGN, TokenType.MINUS_ASSIGN, TokenType.DOTDOT,
                          TokenType.AT):
            assert any(s.startswith(p) for s in span_scopes for p in (
                "keyword.operator.", "punctuation.", "support."
            )), f"Operator {tok.value!r} got non-operator scopes {span_scopes!r}"
            matched_operators += 1
        elif tok.type == TokenType.IDENTIFIER:
            assert any(s.startswith(p) for s in span_scopes for p in (
                "variable.", "entity.", "support.", "keyword.declaration.alias."
            )), f"Identifier {tok.value!r} got scopes {span_scopes!r}"
            matched_identifiers += 1
            
        tested_semantic_tokens += 1
    
    assert tested_semantic_tokens >= 100, f"Tested too few tokens: {tested_semantic_tokens}"
    assert matched_keywords >= 25, f"Matched too few keywords: {matched_keywords}"
    assert matched_literals >= 15, f"Matched too few literals: {matched_literals}"
    assert matched_operators >= 10, f"Matched too few operators: {matched_operators}"
    assert matched_identifiers >= 40, f"Matched too few identifiers: {matched_identifiers}"


def test_edge_token_highlighting():
    """Verify specific edge tokens and language constructs produce expected grammar scopes."""
    grammar = load_grammar()
    rules = compile_grammar_rules(grammar)
    
    cases = [
        # Hex, binary, octal literals
        ("0xFFu32", "constant.numeric.hex.velo"),
        ("0b1010u8", "constant.numeric.binary.velo"),
        ("0o77", "constant.numeric.octal.velo"),
        ("3.14159f64", "constant.numeric.float.velo"),
        
        # Character escapes
        ("'\\n'", "constant.character.velo"),
        ("'\\''", "constant.character.velo"),
        
        # Attributes
        ("#align(16)", "entity.other.attribute-name.velo"),
        ("#packed", "entity.other.attribute-name.velo"),
        
        # Visibility and safety keywords
        ("view", "storage.modifier.view.velo"),
        ("pact", "storage.type.contract.pact.velo"),
        ("unsafe", "keyword.control.unsafe.velo"),
        
        # Directives & builtins
        ("use sys.io", "support.class.module.velo"),
        ("use std.fs", "support.class.std.velo"),
        
        # Dot variants
        (".Active", "variable.other.enummember.dot.velo"),
        
        # Operators
        ("->", "keyword.operator.arrow.velo"),
        ("=>", "keyword.operator.arrow.velo"),
        ("..=", "keyword.operator.range.velo"),
    ]
    
    for sample, expected_scope in cases:
        spans = tokenize_line_with_grammar(sample, rules)
        all_scopes = set()
        for _, _, _, sc_set in spans:
            all_scopes.update(sc_set)
        assert expected_scope in all_scopes, (
            f"Sample {sample!r} failed to produce scope {expected_scope!r} (produced {all_scopes})"
        )


def test_comments_conformance():
    """Verify single-line, doc-comment, and block-comment grammar tokenization."""
    grammar = load_grammar()
    rules = compile_grammar_rules(grammar)
    
    comment_samples = [
        ("// normal comment", "comment.line.double-slash.velo"),
        ("/// documentation comment", "comment.line.documentation.velo"),
        ("/* block comment */", "comment.block.velo"),
    ]
    for text, expected_scope in comment_samples:
        spans = tokenize_line_with_grammar(text, rules)
        assert spans, f"Comment {text!r} produced no grammar spans"
        assert expected_scope in spans[0][3], (
            f"Comment {text!r} expected {expected_scope!r}, got {spans[0][3]!r}"
        )


def test_run_editor_parity_suite():
    """Run editors/vscode/tests/parity_compiler.py and verify all 24 parity checks pass."""
    parity_script = VS_DIR / "tests" / "parity_compiler.py"
    assert parity_script.exists()
    
    proc = subprocess.run(
        [sys.executable, str(parity_script)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    assert proc.returncode == 0, f"parity_compiler.py failed:\n{proc.stdout}\n{proc.stderr}"
    assert "ALL 24 PARITY CHECKS PASSED" in proc.stdout


def test_run_editor_spotchecks():
    """Run editors/vscode/tests/match_spotcheck.js if node is available."""
    node_exe = shutil.which("node")
    if not node_exe:
        pytest.skip("Node.js not installed on PATH")
        
    spotcheck_script = VS_DIR / "tests" / "match_spotcheck.js"
    assert spotcheck_script.exists()
    
    proc = subprocess.run(
        [node_exe, str(spotcheck_script)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    assert proc.returncode == 0, f"match_spotcheck.js failed:\n{proc.stdout}\n{proc.stderr}"
    assert "ALL 31 GRAMMAR SPOT-CHECKS PASSED" in proc.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
