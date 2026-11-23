#!/usr/bin/env python3
"""Phase 4 parity checks: grammar vs compiler drift detection.

The extension mirrors three real compiler truths; this test pins them together
so a change on any side fails loudly instead of silently drifting:

  1. keywords         — velo.tokens.KEYWORDS (the real lexer table) vs the
                        grammar's #keywords rules vs the LSP analyzer's mirror.
                        Documented extras: `aka` and `it` are contextual (not
                        lexer tokens) and are deliberately highlighted/analyzed.
  2. builtin members  — velo/codegen_c.py member dispatch (the real registry)
                        vs the grammar's #builtins member rules vs the
                        analyzer's module tables.
  3. use roots        — the grammar's `sys.(io|mem|fs)` rule must name EXACTLY
                        the modules both stage loaders accept after `use sys.`:
                        Stage 2's loader rejects `use sys.str` as a missing
                        file (gaps §6.7 (10)) even though str.* calls are
                        ambient, so `sys.str` stays a member surface and must
                        never be offered as a `use` root.
                        The grammar's `std.(io|fs|mem|path|os|str|time|math|json|fmt|coll)`
                        rule covers all 11 standard library modules.
  4. structure        — every tmLanguage scope name is well-formed and
                        language-suffixed; snippet baseline count; language
                        configuration healthy.

Run:  python tests/parity_compiler.py

Exits 1 on any mismatch, printing the offending sets.
"""

import importlib.util
import json
import re
import sys
from pathlib import Path

VS_DIR = Path(__file__).resolve().parent.parent
REPO = VS_DIR.parent.parent
sys.path.insert(0, str(REPO))

CONTEXTUAL_KEYWORDS = {"aka", "it"}


def load_analyzer():
    spec = importlib.util.spec_from_file_location(
        "velo_analysis", VS_DIR / "_server" / "velo_analysis.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["velo_analysis"] = module
    spec.loader.exec_module(module)
    return module


def grammar_builtin_members(grammar) -> dict:
    """Call-site member rules: module alias -> {member, ...}.

    Pattern strings are JSON-decoded, so the oniguruma `\\b` anchors appear as
    literal backslash+b character pairs and must be matched as such.
    """
    table = {}
    for pattern in grammar["repository"]["builtins"]["patterns"]:
        match = re.fullmatch(r"\\b\((\w+)\)\\\.\(([\w|]+)\)\\b", pattern["match"])
        if not match:
            raise AssertionError(f"unexpected builtin rule shape: {pattern['match']!r}")
        module, members = match.group(1), match.group(2).split("|")
        if module in ("sys", "std"):
            continue  # the use-statement root rules, checked separately
        table[module] = set(members)
    return table


def grammar_use_roots(grammar) -> set:
    for pattern in grammar["repository"]["builtins"]["patterns"]:
        match = re.fullmatch(r"\\b\(sys\)\\\.\(([\w|]+)\)\\b", pattern["match"])
        if match:
            return set(match.group(1).split("|"))
    raise AssertionError("grammar has no sys. use-root rule")


def grammar_std_use_roots(grammar) -> set:
    for pattern in grammar["repository"]["builtins"]["patterns"]:
        match = re.fullmatch(r"\\b\(std\)\\\.\(([\w|]+)\)\\b", pattern["match"])
        if match:
            return set(match.group(1).split("|"))
    raise AssertionError("grammar has no std. use-root rule")


def grammar_keywords(grammar) -> set:
    words = set()
    for pattern in grammar["repository"]["keywords"]["patterns"]:
        source = pattern["match"]
        if source.startswith("^aka"):  # alias declaration shape guard
            words.add("aka")
            continue
        inner = re.fullmatch(r"\\b(.+)\\b", source)
        if not inner:
            raise AssertionError(f"unexpected keyword rule shape: {source!r}")
        core = inner.group(1)
        grouped = re.fullmatch(r"\(([\w|]+)\)", core)
        terms = grouped.group(1).split("|") if grouped else [core]
        for term in terms:
            if not re.fullmatch(r"\w+", term):
                raise AssertionError(f"unexpected keyword term: {term!r} in {source!r}")
        words.update(terms)
    return words


def grammar_type_words(grammar) -> set:
    words = set()
    for pattern in grammar["repository"]["types"]["patterns"]:
        for group in re.findall(r"\(([\w|]+)\)", pattern.get("match", "")):
            words.update(part for part in group.split("|") if part and part.islower())
    return words


def codegen_builtin_registry() -> dict:
    """Extract the builtin module member sets from velo/codegen_c.py itself."""
    source = (REPO / "velo" / "codegen_c.py").read_text(encoding="utf-8")
    chain = re.search(
        r'if isinstance\(expr\.callee, MemberAccess\):\s*'
        r'if isinstance\(expr\.callee\.target, Identifier\):(.*?)'
        r'target_type = self\._resolve_expr_type',
        source, re.DOTALL)
    if not chain:
        raise AssertionError("codegen builtin dispatch (io/mem/fs/str chain) not found — _emit_expression shape changed")
    body = chain.group(1)
    registry = {}
    for module in re.findall(r'callee\.target\.name == "(\w+)"', body):
        end = body.index(f'callee.target.name == "{module}"')
        following = body[end:]
        stop = re.search(
            r'callee\.target\.name == "(?!' + re.escape(module) + r'"\s*:)',
            following[30:] if len(following) > 30 else following)
        block = following[:30 + (stop.start() if stop else len(following) - 30)]
        members = set(re.findall(r'callee\.member == "(\w+)"', block))
        for group in re.findall(r'callee\.member in \(([^)]*)\)', block):
            members.update(re.findall(r'"(\w+)"', group))
        registry[module] = members

    import velo.codegen_c as cg
    if hasattr(cg, "FS_CALLS"):
        registry["fs"] = set(cg.FS_CALLS.keys())
    if hasattr(cg, "MATH_CALLS"):
        registry["math"] = set(cg.MATH_CALLS.keys())
    if hasattr(cg, "TIME_CALLS"):
        registry["time"] = set(cg.TIME_CALLS.keys())
    if hasattr(cg, "OS_CALLS"):
        registry["os"] = set(cg.OS_CALLS.keys())
    if hasattr(cg, "STR_RUNTIME_MEMBERS"):
        registry["str"] = set(cg.STR_RUNTIME_MEMBERS.keys()) | registry.get("str", set())
    return {k: v for k, v in registry.items() if v}


def main() -> int:
    results = []
    failures = []

    def check(name, condition, detail=""):
        results.append(f"PASS {name}" if condition else f"FAIL {name}  {detail}")
        if not condition:
            failures.append(name)

    grammar = json.loads((VS_DIR / "syntaxes" / "velo.tmLanguage.json").read_text(encoding="utf-8"))
    snippets = json.loads((VS_DIR / "snippets" / "velo.json").read_text(encoding="utf-8"))
    langconfig = json.loads((VS_DIR / "language-configuration.json").read_text(encoding="utf-8"))
    analyzer = load_analyzer()

    # -- 1. keywords --------------------------------------------------------
    from velo.tokens import KEYWORDS as REAL_KEYWORDS
    real_words = set(REAL_KEYWORDS)
    grammar_words = grammar_keywords(grammar)
    analyzer_words = set(analyzer.KEYWORDS)
    check("keywords: lexer table == grammar minus contextual",
          real_words == grammar_words - CONTEXTUAL_KEYWORDS,
          f"lexer-only: {sorted(real_words - grammar_words)}; grammar-only: {sorted(grammar_words - real_words)}")
    check("keywords: analyzer mirror == lexer + contextual",
          analyzer_words == real_words | CONTEXTUAL_KEYWORDS,
          f"diff: {sorted(analyzer_words ^ (real_words | CONTEXTUAL_KEYWORDS))}")

    # -- 2. builtin members --------------------------------------------------
    registry = codegen_builtin_registry()
    grammar_members = grammar_builtin_members(grammar)
    aliases = {m: set(v) for m, v in analyzer._BUILTIN_ALIASES.items()}
    check("builtins: codegen registry == grammar member rules",
          registry == grammar_members,
          f"diff: { {m: sorted(registry.get(m, set()) ^ grammar_members.get(m, set())) for m in set(registry) | set(grammar_members)} }")
    check("builtins: codegen registry == analyzer call-site aliases",
          registry == aliases,
          f"diff: { {m: sorted(registry.get(m, set()) ^ aliases.get(m, set())) for m in set(registry) | set(aliases)} }")
    for module, functions in analyzer.BUILTIN_MODULES.items():
        short = module.split(".", 1)[1]
        check(f"builtins: analyzer long table {module} == call-site alias",
              set(functions) == aliases[short],
              f"long: {sorted(set(functions) ^ aliases[short])}")

    # -- 3. use-statement module roots ---------------------------------------
    roots = grammar_use_roots(grammar)
    expected_roots = {"io", "mem", "fs"}
    check("use-roots: grammar sys rule == {io, mem, fs} (Stage 2 loader truth)",
          roots == expected_roots,
          f"grammar roots: {sorted(roots)} — sys.str must stay a member surface (gaps 6.7 (10))")
    std_roots = grammar_std_use_roots(grammar)
    expected_std_roots = {"io", "fs", "mem", "path", "os", "str", "time", "math", "json", "fmt", "coll"}
    check("use-roots: grammar std rule covers 11 modules",
          std_roots == expected_std_roots,
          f"grammar std roots: {sorted(std_roots)}")
    source = (VS_DIR / "_server" / "velo_analysis.py").read_text(encoding="utf-8")
    roots_line = re.search(r"for mod in \(([^)]*)\):", source)
    offered_roots = {part.strip().strip('"') for part in roots_line.group(1).split(",")} if roots_line else set()
    check("use-roots: completion never suggests an invalid use root",
          offered_roots == {"sys.io", "sys.mem", "sys.fs"},
          f"analyzer offers: {sorted(offered_roots)}")

    # -- 4. structural health --------------------------------------------------
    type_words = grammar_type_words(grammar)
    analyzer_types = {"void"} | set(analyzer.PRIMITIVE_TYPES)
    missing_types = [t for t in analyzer_types if t not in type_words]
    check("types: grammar type rule covers every primitive the analyzer offers",
          not missing_types, f"missing from grammar: {missing_types}")

    scope_names = []

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "name" and isinstance(value, str):
                    scope_names.append(value)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(grammar["repository"])
    malformed = [n for n in scope_names if not re.match(r"^[a-z][a-z0-9.\-]*\.velo$", n)]
    check("grammar: scope names well-formed and language-suffixed",
          not malformed, f"offenders: {malformed[:5]}")

    baseline_path = Path(__file__).parent / "baselines" / "suite_counts.json"
    if baseline_path.exists():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        check("snippets: count matches deliberate baseline",
              len(snippets) == baseline.get("snippets", -1),
              f"now {len(snippets)}, baseline {baseline.get('snippets')} — update tests/baselines deliberately")
    else:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps({"snippets": len(snippets)}, indent=1) + "\n", encoding="utf-8")
        results.append(f"NOTE snippets baseline written ({len(snippets)})")
    check("snippets: templates declare prefix and non-empty body",
          all(s.get("prefix") and s.get("body") for s in snippets.values()))

    brackets = langconfig.get("brackets", [])
    check("language-configuration: brackets are two-char pairs",
          all(isinstance(pair, list) and len(pair) == 2
              and all(isinstance(ch, str) and ch for ch in pair) for pair in brackets))
    comments = langconfig.get("comments", {})
    block = comments.get("blockComment")
    block_ok = (isinstance(block, list) and len(block) == 2
                and all(isinstance(c, str) and c for c in block)) or \
               (isinstance(block, dict) and block.get("open") and block.get("close"))
    check("language-configuration: comment tokens non-empty",
          isinstance(comments.get("lineComment"), str) and comments["lineComment"] and block_ok)

    # -- 5. package manifest (velo.pkg) ----------------------------------------
    pkg_grammar = json.loads((VS_DIR / "syntaxes" / "velo.pkg.tmLanguage.json").read_text(encoding="utf-8"))
    pkg_snippets = json.loads((VS_DIR / "snippets" / "velo.pkg.json").read_text(encoding="utf-8"))
    pkg_langconfig = json.loads((VS_DIR / "pkg-language-configuration.json").read_text(encoding="utf-8"))

    pkg_scopes = []
    walk_pkg = lambda n: [pkg_scopes.append(v) if k == "name" and isinstance(v, str) else walk_pkg(v) for k, v in n.items()] if isinstance(n, dict) else [walk_pkg(i) for i in n] if isinstance(n, list) else None
    walk_pkg(pkg_grammar["repository"])
    pkg_malformed = [n for n in pkg_scopes if not re.match(r"^[a-z][a-z0-9.\-]*\.velo$", n)]
    check("velo.pkg: grammar scope names well-formed and language-suffixed",
          not pkg_malformed, f"offenders: {pkg_malformed[:5]}")
    check("velo.pkg: snippets declare prefix and non-empty body",
          all(s.get("prefix") and s.get("body") for s in pkg_snippets.values()))
    check("velo.pkg: language-configuration brackets valid",
          all(isinstance(p, list) and len(p) == 2 for p in pkg_langconfig.get("brackets", [])))

    for line in results:
        print(line)
    if failures:
        print(f"\nPARITY FAILED ({len(failures)}): {failures}")
        return 1
    print(f"\nALL {len([r for r in results if r.startswith('PASS')])} PARITY CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
