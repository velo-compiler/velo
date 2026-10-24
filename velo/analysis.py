"""Velo language analysis layer for the Language Server Protocol (LSP).

Reuses the Python compiler's real frontend — `velo.lexer`, `velo.parser`,
`velo.driver`, and AST nodes — for every analysis feature:
- Diagnostics with in-memory buffer overlay (no temp files on disk)
- Document symbols (outline for struct fields, kind variants, aka aliases, acts)
- Hover (type signatures, parameters, returns, locals, and docs)
- Go-to-definition (cursor token to declaration in file or imports)
- Completions (keywords, types, builtin module methods, declared identifiers)
"""

import os
import sys
from contextlib import contextmanager
from dataclasses import fields as dc_fields, is_dataclass
from pathlib import Path
from typing import Optional

from velo.tokens import KEYWORDS as COMPILER_KEYWORDS

# ---------------------------------------------------------------------------
# Builtin module tables
# ---------------------------------------------------------------------------

BUILTIN_MODULES = {
    "sys.io": ["print", "print_char", "println"],
    "sys.mem": [
        "alloc", "alloc_with", "copy", "current", "free", "heap_alloc",
        "heap_used", "move", "realloc", "set", "used"
    ],
    "sys.fs": [
        "copy", "create_dir", "create_dir_all", "exists", "fclose", "fopen",
        "fread", "fseek", "fwrite", "is_dir", "is_file", "read_dir",
        "read_file", "remove", "remove_file", "rename", "size", "write_file"
    ],
    "sys.str": [
        "concat", "contains", "ends_with", "index_of", "len", "replace",
        "split", "starts_with", "to_lower", "to_upper", "trim"
    ],
    "sys.math": [
        "abs", "acos", "asin", "atan2", "cbrt", "ceil", "clamp", "cos",
        "exp", "floor", "lerp", "log", "log2", "max", "min", "pow",
        "round", "sin", "sqrt", "tan"
    ],
    "sys.time": ["delta", "now", "sleep_ms"],
    "sys.os": ["args", "exit", "get_env", "set_env"],
    "sys.thread": ["acquire", "free", "join", "mutex", "release", "spawn"],
}

_BUILTIN_ALIASES = {
    "io": BUILTIN_MODULES["sys.io"],
    "mem": BUILTIN_MODULES["sys.mem"],
    "fs": BUILTIN_MODULES["sys.fs"],
    "str": BUILTIN_MODULES["sys.str"],
    "math": BUILTIN_MODULES["sys.math"],
    "time": BUILTIN_MODULES["sys.time"],
    "os": BUILTIN_MODULES["sys.os"],
    "thread": BUILTIN_MODULES["sys.thread"],
}

KEYWORDS = sorted(set(COMPILER_KEYWORDS) | {"aka", "it"})

PRIMITIVE_TYPES = [
    "i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64",
    "f32", "f64", "bool", "string", "void", "usize", "dyn",
]


def to_position(line: int, col: int) -> dict:
    """Compiler 1-based (0/0 = unpositioned) -> LSP 0-based position."""
    return {"line": max(0, (line or 1) - 1), "character": max(0, (col or 1) - 1)}


def to_range(line: int, col: int) -> dict:
    """A one-width LSP range starting at the compiler position."""
    start = to_position(line, col)
    return {"start": start, "end": {"line": start["line"], "character": start["character"] + 1}}


def _span(start: dict, width: int) -> dict:
    return {"start": start, "end": {"line": start["line"], "character": start["character"] + width}}


def _path_to_uri(path: str) -> str:
    return "file:///" + Path(path).resolve().as_posix().lstrip("/")


def _uri_to_path(uri: str) -> str:
    from urllib.parse import urlparse, unquote
    parsed = urlparse(uri)
    if parsed.scheme not in ("file", ""):
        raise ValueError(f"unsupported uri scheme: {parsed.scheme}")
    p = unquote(parsed.path)
    if p.startswith("/") and len(p) > 2 and p[2] == ":":  # /C:/... windows form
        p = p[1:]
    return str(Path(p).resolve())


# ---------------------------------------------------------------------------
# Overlay machinery
# ---------------------------------------------------------------------------

@contextmanager
def overlay_read_text(overlays: dict):
    """Temporarily route Path.read_text through an overlay map (path str -> text)."""
    original = Path.read_text

    def patched(path_obj, encoding=None, errors=None):
        key = str(Path(path_obj).resolve())
        if key in overlays:
            return overlays[key]
        for ok, val in overlays.items():
            if str(Path(ok).resolve()) == key:
                return val
        return original(path_obj, encoding=encoding, errors=errors)

    Path.read_text = patched
    try:
        yield
    finally:
        Path.read_text = original


# ---------------------------------------------------------------------------
# AST traversal and reflection helpers
# ---------------------------------------------------------------------------

class FileRecord:
    __slots__ = ("path", "text", "tokens", "program")

    def __init__(self, path: str, text: str, tokens, program):
        self.path = path
        self.text = text
        self.tokens = tokens
        self.program = program


_NAME_ATTRS = ("name", "member", "struct_name", "variant_name", "kind_name", "iterator")


def collect_name_spans(node, out: list) -> None:
    """Collect {attr, value, line, col, len} for every name-bearing node."""
    if node is None or isinstance(node, (str, int, float, bool)):
        return
    if isinstance(node, (list, tuple)):
        for item in node:
            collect_name_spans(item, out)
        return
    if not is_dataclass(node):
        return
    has_pos = hasattr(node, "line") and hasattr(node, "col")
    if has_pos:
        for attr in _NAME_ATTRS:
            value = getattr(node, attr, None)
            if isinstance(value, str) and value:
                out.append({
                    "attr": attr, "value": value,
                    "line": node.line, "col": node.col, "len": len(value)
                })
    for f in dc_fields(node):
        collect_name_spans(getattr(node, f.name, None), out)


def _last_word(s: str) -> str:
    import re
    match = re.search(r"[A-Za-z_][A-Za-z0-9_.]*$", s)
    return match.group(0) if match else ""


def _from_velo_ast():
    from velo import ast_nodes as A
    return A


def _locals_of(act_decl) -> list:
    """(line, col, name, type_name, is_param) locals inside one act."""
    out = []
    for p in (act_decl.params or []):
        out.append({
            "line": p.line, "col": p.col, "name": p.name,
            "type": p.type_name, "is_param": True
        })
    A = _from_velo_ast()

    def walk(node):
        if node is None or isinstance(node, (str, int, float, bool)):
            return
        if isinstance(node, (list, tuple)):
            for item in node:
                walk(item)
            return
        if isinstance(node, A.VarDeclStmt):
            if node.name:
                out.append({
                    "line": node.line, "col": node.col, "name": node.name,
                    "type": node.type_name or "inferred", "is_param": False
                })
        if is_dataclass(node):
            for f in dc_fields(node):
                walk(getattr(node, f.name, None))

    walk(act_decl.body)
    return out


# ---------------------------------------------------------------------------
# VeloAnalysis Facade
# ---------------------------------------------------------------------------

class VeloAnalysis:
    """Per-server analysis facade over the real compiler."""

    def __init__(self, repo_root: Optional[str] = None):
        if repo_root is None:
            repo_root = str(Path(__file__).resolve().parent.parent)
        self.repo_root = repo_root
        self.import_error: Optional[str] = None
        try:
            if repo_root and Path(repo_root).is_dir():
                sys.path.insert(0, str(Path(repo_root).resolve()))
            from velo.driver import CompilerDriver
            self._driver_cls = CompilerDriver
        except Exception as exc:
            self.import_error = f"Velo compiler import failed: {exc}"
            self._driver_cls = None
        self.documents = {}  # uri -> {"path","text","version","record"}

    def open(self, uri: str, path: str, text: str, version: int) -> None:
        self.documents[uri] = {"path": path, "text": text, "version": version, "record": None}

    def change(self, uri: str, text: str, version: int) -> None:
        doc = self.documents.get(uri)
        if doc:
            doc["text"] = text
            doc["version"] = version
            doc["record"] = None

    def close(self, uri: str) -> None:
        self.documents.pop(uri, None)

    def _record_for(self, path: str, text: str) -> FileRecord:
        from velo.lexer import Lexer
        from velo.parser import Parser

        key = str(Path(path).resolve())
        with overlay_read_text({key: text}):
            lexer = Lexer(text, filename=key)
            tokens = lexer.tokenize()
            program = Parser(tokens).parse()
        return FileRecord(key, text, tokens, program)

    def resolve_with_provenance(self, root_path: str) -> dict:
        """Mirror of driver.resolve_program keeping per-file records."""
        root = Path(root_path).resolve()
        if not root.exists():
            raise FileNotFoundError(f"Source file not found: {root_path}")

        from velo.lexer import Lexer
        from velo.parser import Parser

        visited = set()
        records: dict = {}
        open_texts = {str(Path(d["path"]).resolve()): d["text"] for d in self.documents.values()}

        def load(file_path: Path):
            resolved = file_path.resolve()
            key = str(resolved)
            if key in visited:
                return
            visited.add(key)
            if not resolved.exists():
                raise FileNotFoundError(f"Source file not found: {resolved}")

            text = open_texts.get(key)
            if text is None:
                text = resolved.read_text(encoding="utf-8")

            lexer = Lexer(text, filename=key)
            tokens = lexer.tokenize()
            ast = Parser(tokens).parse()

            for decl in ast.declarations:
                mod = getattr(decl, "module_path", None)
                if mod and not mod.startswith("sys."):
                    target = (resolved.parent / mod).resolve()
                    if not target.exists() and not mod.endswith(".vl"):
                        target = (resolved.parent / f"{mod}.vl").resolve()
                    if not target.exists():
                        alt_target = (root.parent / mod).resolve()
                        if not alt_target.exists() and not mod.endswith(".vl"):
                            alt_target = (root.parent / f"{mod}.vl").resolve()
                        if alt_target.exists():
                            target = alt_target
                        else:
                            raise FileNotFoundError(f"Module not found: '{mod}' referenced in {resolved}")
                    load(target)

            records[key] = FileRecord(key, text, tokens, ast)

        load(root)
        for uri, doc in self.documents.items():
            doc_key = str(Path(doc["path"]).resolve())
            if doc_key in records and doc["record"] is None:
                doc["record"] = records[doc_key]
        return records

    def _index(self, root_path: str) -> dict:
        """Name -> [{rec, decl}] across the open doc and its imports."""
        records = self.resolve_with_provenance(root_path)
        index: dict = {}
        for rec in records.values():
            for decl in rec.program.declarations:
                name = getattr(decl, "name", None)
                if isinstance(name, str) and name:
                    index.setdefault(name, []).append({"rec": rec, "decl": decl})
                for variant in (getattr(decl, "variants", None) or []):
                    if variant.name:
                        index.setdefault(variant.name, []).append({"rec": rec, "decl": variant})
        return index

    def _ensure_record(self, uri: str):
        doc = self.documents[uri]
        if doc["record"] is None:
            doc["record"] = self._record_for(doc["path"], doc["text"])
        return doc["record"]

    # -- diagnostics ---------------------------------------------------------

    def diagnostics(self, uri: str) -> dict:
        """Authoritative diagnostics: CompilerDriver.check on the buffer text."""
        doc = self.documents.get(uri)
        if not doc:
            return {"uri": uri, "version": 0, "diagnostics": []}
        if self.import_error:
            return {
                "uri": uri, "version": doc["version"],
                "diagnostics": [{
                    "range": to_range(1, 1), "severity": 1, "source": "velo-lsp",
                    "message": self.import_error
                }]
            }
        overlay = {str(Path(doc["path"]).resolve()): doc["text"]}
        with overlay_read_text(overlay):
            report = self._driver_cls().check(doc["path"])
        diagnostics = [{
            "range": to_range(d.get("line", 0), d.get("col", 0)),
            "severity": 1 if d.get("severity", "error") == "error" else 2,
            "source": "velo",
            "message": d.get("message", ""),
        } for d in report.get("diagnostics", [])]
        return {"uri": uri, "version": doc["version"], "diagnostics": diagnostics}

    # -- document symbols ------------------------------------------------------

    def document_symbols(self, uri: str) -> list:
        try:
            rec = self._ensure_record(uri)
        except Exception:
            return []
        decls = list(rec.program.declarations)
        starts = sorted([(d.line, d.col) for d in decls if getattr(d, "line", 0)])

        def end_of(decl) -> dict:
            for line, col in starts:
                if (line, col) > (decl.line, decl.col):
                    prev = to_position(line, col)
                    return {"start": prev, "end": {"line": max(0, prev["line"] - 1), "character": 0}}
            return self._doc_end(rec.text)

        symbols = []
        for decl in decls:
            name = getattr(decl, "name", None)
            module_path = getattr(decl, "module_path", None)
            if not name or module_path:
                continue
            head = to_position(decl.line, decl.col)
            full = {"start": head, "end": end_of(decl)["end"]}
            if hasattr(decl, "variants"):
                children = [{
                    "name": v.name, "kind": 22, "detail": "variant",
                    "range": _span(to_position(v.line, v.col), len(v.name)),
                    "selectionRange": _span(to_position(v.line, v.col), len(v.name))
                } for v in decl.variants]
                symbols.append({
                    "name": name, "kind": 10, "detail": "kind", "range": full,
                    "selectionRange": self._name_range(rec, name, decl.line, decl.col),
                    "children": children
                })
            elif hasattr(decl, "fields"):
                children = [{
                    "name": f"{fld.name}: {getattr(fld, 'type_name', '')}", "kind": 8,
                    "detail": "field", "range": to_range(fld.line, fld.col),
                    "selectionRange": _span(to_position(fld.line, fld.col), len(fld.name))
                } for f in (decl.fields or []) for fld in [f]]
                symbols.append({
                    "name": name, "kind": 23, "detail": "data", "range": full,
                    "selectionRange": self._name_range(rec, name, decl.line, decl.col),
                    "children": children
                })
            elif hasattr(decl, "target_type"):
                symbols.append({
                    "name": f"aka {name} = {decl.target_type}", "kind": 26,
                    "detail": "aka", "range": full,
                    "selectionRange": self._name_range(rec, name, decl.line, decl.col)
                })
            elif hasattr(decl, "body"):
                params = ", ".join(f"{p.name}: {p.type_name}" for p in (decl.params or []))
                ret = getattr(decl, "return_type", None) or "void"
                symbols.append({
                    "name": f"{name}({params}) -> {ret}", "kind": 12, "detail": "act",
                    "range": full,
                    "selectionRange": self._name_range(rec, name, decl.line, decl.col)
                })
            elif hasattr(decl, "params"):
                symbols.append({
                    "name": name, "kind": 12, "detail": "extern", "range": full,
                    "selectionRange": self._name_range(rec, name, decl.line, decl.col)
                })
        return symbols

    @staticmethod
    def _doc_end(text: str) -> dict:
        lines = text.split("\n")
        point = {"line": len(lines), "character": 0}
        return {"start": point, "end": point}

    def _name_range(self, rec: FileRecord, name: str, line: int, col: int) -> dict:
        """Exact name-token span when the token stream can locate it."""
        best = None
        for tok in rec.tokens:
            if getattr(tok, "value", None) != name or tok.line != line or tok.col < col:
                continue
            if best is None or tok.col < best.col:
                best = tok
        if best:
            return _span(to_position(best.line, best.col), len(name))
        return to_range(line, col)

    # -- cursor mapping --------------------------------------------------------

    def _span_at(self, uri: str, line0: int, char0: int):
        """The name span covering the 0-based cursor, or None."""
        doc = self.documents.get(uri)
        if not doc:
            return None
        try:
            rec = self._ensure_record(uri)
        except Exception:
            return None

        from velo.tokens import TokenType
        for tok in rec.tokens:
            if tok.value and tok.line == line0 + 1 and getattr(tok, "type", None) == TokenType.IDENTIFIER:
                start = tok.col - 1
                if start <= char0 < start + len(tok.value):
                    return {
                        "attr": "name", "value": tok.value,
                        "line": tok.line, "col": tok.col, "len": len(tok.value)
                    }

        nearby = None
        spans = []
        collect_name_spans(rec.program, spans)
        for span in spans:
            if span["line"] != line0 + 1:
                continue
            start = (span["col"] or 1) - 1
            end = start + span["len"]
            if start <= char0 < end:
                return span
            if start - 1 <= char0 <= end + 1:
                if nearby is None or start < nearby["col"]:
                    nearby = span
        return nearby

    def _enclosing_act(self, uri: str, line0: int):
        rec = self._ensure_record(uri)
        acts = []
        for decl in rec.program.declarations:
            if hasattr(decl, "body") and hasattr(decl, "params"):
                acts.append(decl)
        acts.sort(key=lambda d: (d.line, d.col))
        chosen = None
        for act in acts:
            if (act.line - 1) <= line0:
                chosen = act
            else:
                break
        return chosen

    def _local_lookup(self, uri: str, name: str, line0: int):
        act = self._enclosing_act(uri, line0)
        if act is None:
            return None
        cands = [loc for loc in _locals_of(act) if loc["name"] == name]
        if not cands:
            return None
        above = [loc for loc in cands if loc["line"] - 1 <= line0]
        loc = (above[-1] if above else cands[0])
        return {
            "range": _span(to_position(loc["line"], loc["col"]), len(name)),
            "type": loc["type"], "is_param": loc["is_param"], "file": None
        }

    # -- hover / definition / completion -----------------------------------------

    def hover(self, uri: str, line0: int, char0: int):
        span = self._span_at(uri, line0, char0)
        if not span:
            return None
        name = span["value"]
        doc = self.documents[uri]
        try:
            index = self._index(doc["path"])
        except Exception:
            index = {}
        entries = index.get(name)
        if entries:
            decl = entries[0]["decl"]
            rec_path = entries[0]["rec"].path
            md = self._decl_markdown(decl) + "\n\n*declared in " + Path(rec_path).name + ":" + str(decl.line) + "*"
            return {"contents": {"kind": "markdown", "value": md}, "range": self._span_range(span)}
        local = self._local_lookup(uri, name, line0)
        if local:
            kind = "param" if local["is_param"] else "local"
            md = f"`{kind} **{name}**: {local['type']}`"
            return {"contents": {"kind": "markdown", "value": md}, "range": self._span_range(span)}
        return None

    @staticmethod
    def _span_range(span) -> dict:
        return _span(to_position(span["line"], span["col"]), span["len"])

    @staticmethod
    def _decl_markdown(decl) -> str:
        if hasattr(decl, "variants"):
            variants = ", ".join(v.name for v in decl.variants)
            return f"**kind** `{decl.name}`  \nvariants: {variants}"
        if hasattr(decl, "target_type"):
            return f"**aka** `{decl.name} = {decl.target_type}`"
        if hasattr(decl, "fields"):
            lines = [f"**data** `{decl.name}`"]
            lines += [f"- `{f.name}: {getattr(f, 'type_name', '')}`" for f in (decl.fields or [])[:8]]
            return "  \n".join(lines)
        params = ", ".join(f"{p.name}: {p.type_name}" for p in (getattr(decl, "params", None) or []))
        ret = getattr(decl, "return_type", None) or "void"
        return f"**act** `{decl.name}({params}) -> {ret}`"

    def definition(self, uri: str, line0: int, char0: int):
        span = self._span_at(uri, line0, char0)
        if not span:
            return None
        name = span["value"]
        doc = self.documents[uri]
        try:
            index = self._index(doc["path"])
        except Exception:
            index = {}
        entries = index.get(name)
        if entries:
            first = entries[0]
            return {
                "uri": _path_to_uri(first["rec"].path),
                "range": self._decl_name_range(first["rec"], first["decl"])
            }
        local = self._local_lookup(uri, name, line0)
        if local and local["range"]:
            return {"uri": uri, "range": local["range"]}
        return None

    def _decl_name_range(self, rec: FileRecord, decl) -> dict:
        return self._name_range(rec, getattr(decl, "name", ""), getattr(decl, "line", 0), getattr(decl, "col", 0))

    def completions(self, uri: str, line0: int, char0: int) -> list:
        doc = self.documents.get(uri)
        if not doc:
            return []
        lines = doc["text"].split("\n")
        prefix = lines[line0][:char0] if 0 <= line0 < len(lines) else ""
        stripped = prefix.rstrip()
        token = _last_word(stripped)
        items = []

        if "." in stripped:
            head, after = stripped.rsplit(".", 1)
            mod_key = _last_word(head)
            if mod_key == "sys":
                for mod in ("sys.io", "sys.mem", "sys.fs", "sys.math", "sys.time", "sys.os", "sys.thread"):
                    tail = mod[len("sys."):]
                    if not after or tail.startswith(after):
                        items.append({"label": mod, "kind": 9, "detail": "module"})
                return items
            table = BUILTIN_MODULES.get(mod_key) or _BUILTIN_ALIASES.get(mod_key, [])
            if table:
                for fn in table:
                    if not after or fn.startswith(after):
                        items.append({"label": fn, "kind": 3, "detail": mod_key})
            return items

        seen = set()
        for kw in KEYWORDS:
            if token and not kw.startswith(token):
                continue
            seen.add(kw)
            items.append({"label": kw, "kind": 14})
        try:
            index = self._index(doc["path"])
        except Exception:
            index = {}
        for name, entries in index.items():
            if token and not name.startswith(token):
                continue
            if name in seen:
                continue
            seen.add(name)
            decl = entries[0]["decl"]
            kind = (
                12 if hasattr(decl, "body")
                else (9 if hasattr(decl, "variants")
                      else (23 if hasattr(decl, "fields") else 7))
            )
            items.append({"label": name, "kind": kind, "detail": getattr(decl, "target_type", "") or ""})
        for t in PRIMITIVE_TYPES:
            if token and not t.startswith(token) or t in seen:
                continue
            seen.add(t)
            items.append({"label": t, "kind": 7})
        for mod in ("sys.io", "sys.mem", "sys.fs", "sys.str", "sys.math", "sys.time", "sys.os", "sys.thread"):
            if token and not mod.startswith(token) or mod in seen:
                continue
            items.append({"label": mod, "kind": 9, "detail": "module"})
        return items
