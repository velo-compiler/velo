"""
Package Manifest Parser and Data Model for Velo (velo.pkg)

Implements the Velo-native declarative block manifest specification:
- pkg block: name, version, entry, authors, description, license
- deps block: git, local, and registry dependencies
- link block: native libraries (libs) and compiler/linker flags (flags)
"""

import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional


class ManifestError(Exception):
    """Raised when a manifest syntax or validation error occurs."""
    def __init__(self, filename: str, line: int, col: int, message: str):
        self.filename = filename
        self.line = line
        self.col = col
        self.message = message
        super().__init__(f"[Velo Error] {filename}:{line}:{col} - {message}")


@dataclass
class PackageMeta:
    name: str = ""
    version: str = ""
    entry: str = ""
    authors: List[str] = field(default_factory=list)
    description: str = ""
    license: str = ""


@dataclass
class DependencySpec:
    name: str
    kind: str  # "git", "local", "registry"
    source: str  # url, local directory, or version string
    tag: Optional[str] = None  # tag, branch, or commit hash for git dependencies


@dataclass
class LinkConfig:
    libs: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)


@dataclass
class PackageManifest:
    pkg: PackageMeta = field(default_factory=PackageMeta)
    deps: Dict[str, DependencySpec] = field(default_factory=dict)
    link: LinkConfig = field(default_factory=LinkConfig)


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

TOK_IDENT = "IDENT"
TOK_STRING = "STRING"
TOK_LBRACE = "{"
TOK_RBRACE = "}"
TOK_LBRACKET = "["
TOK_RBRACKET = "]"
TOK_COLON = ":"
TOK_COMMA = ","
TOK_AT = "@"
TOK_EOF = "EOF"


@dataclass
class Token:
    kind: str
    value: str
    line: int
    col: int


class ManifestTokenizer:
    def __init__(self, source: str, filename: str = "velo.pkg"):
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.col = 1
        self.length = len(source)

    def _peek(self) -> str:
        if self.pos < self.length:
            return self.source[self.pos]
        return ""

    def _advance(self) -> str:
        ch = self._peek()
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []

        while self.pos < self.length:
            ch = self._peek()

            # Skip whitespace
            if ch in (" ", "\t", "\r", "\n"):
                self._advance()
                continue

            # Line comments: '//' or '#'
            if ch == "#" or (ch == "/" and self.pos + 1 < self.length and self.source[self.pos + 1] == "/"):
                while self.pos < self.length and self._peek() != "\n":
                    self._advance()
                continue

            start_line = self.line
            start_col = self.col

            if ch == "{":
                self._advance()
                tokens.append(Token(TOK_LBRACE, "{", start_line, start_col))
            elif ch == "}":
                self._advance()
                tokens.append(Token(TOK_RBRACE, "}", start_line, start_col))
            elif ch == "[":
                self._advance()
                tokens.append(Token(TOK_LBRACKET, "[", start_line, start_col))
            elif ch == "]":
                self._advance()
                tokens.append(Token(TOK_RBRACKET, "]", start_line, start_col))
            elif ch == ":":
                self._advance()
                tokens.append(Token(TOK_COLON, ":", start_line, start_col))
            elif ch == ",":
                self._advance()
                tokens.append(Token(TOK_COMMA, ",", start_line, start_col))
            elif ch == "@":
                self._advance()
                tokens.append(Token(TOK_AT, "@", start_line, start_col))
            elif ch == '"':
                str_val = self._read_string(start_line, start_col)
                tokens.append(Token(TOK_STRING, str_val, start_line, start_col))
            elif ch.isalpha() or ch == "_":
                ident_val = self._read_ident()
                tokens.append(Token(TOK_IDENT, ident_val, start_line, start_col))
            else:
                raise ManifestError(self.filename, start_line, start_col, f"unexpected character: '{ch}'")

        tokens.append(Token(TOK_EOF, "", self.line, self.col))
        return tokens

    def _read_string(self, start_line: int, start_col: int) -> str:
        self._advance()  # consume opening quote
        buf = []
        while self.pos < self.length:
            ch = self._peek()
            if ch == '"':
                self._advance()  # consume closing quote
                return "".join(buf)
            if ch == "\n" or ch == "":
                raise ManifestError(self.filename, start_line, start_col, "unterminated string literal")
            if ch == "\\":
                self._advance()
                esc = self._advance()
                if esc == "n":
                    buf.append("\n")
                elif esc == "t":
                    buf.append("\t")
                elif esc == "r":
                    buf.append("\r")
                elif esc == '"':
                    buf.append('"')
                elif esc == "\\":
                    buf.append("\\")
                else:
                    buf.append(esc)
            else:
                buf.append(self._advance())
        raise ManifestError(self.filename, start_line, start_col, "unterminated string literal")

    def _read_ident(self) -> str:
        buf = []
        while self.pos < self.length:
            ch = self._peek()
            if ch.isalnum() or ch in ("_", "-"):
                buf.append(self._advance())
            else:
                break
        return "".join(buf)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class ManifestParser:
    def __init__(self, tokens: List[Token], filename: str = "velo.pkg"):
        self.tokens = tokens
        self.filename = filename
        self.pos = 0

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        tok = self._peek()
        if tok.kind != TOK_EOF:
            self.pos += 1
        return tok

    def _expect(self, kind: str, message: str) -> Token:
        tok = self._peek()
        if tok.kind != kind:
            raise ManifestError(self.filename, tok.line, tok.col, f"{message} (got '{tok.value or tok.kind}')")
        return self._advance()

    def parse(self) -> PackageManifest:
        manifest = PackageManifest()
        has_pkg_block = False

        while self._peek().kind != TOK_EOF:
            tok = self._peek()
            if tok.kind == TOK_IDENT and tok.value == "pkg":
                if has_pkg_block:
                    raise ManifestError(self.filename, tok.line, tok.col, "duplicate 'pkg' block")
                self._parse_pkg_block(manifest)
                has_pkg_block = True
            elif tok.kind == TOK_IDENT and tok.value == "deps":
                self._parse_deps_block(manifest)
            elif tok.kind == TOK_IDENT and tok.value == "link":
                self._parse_link_block(manifest)
            else:
                raise ManifestError(
                    self.filename, tok.line, tok.col,
                    f"unexpected top-level item '{tok.value}' (expected 'pkg', 'deps', or 'link')"
                )

        if not has_pkg_block:
            raise ManifestError(self.filename, 1, 1, "missing required 'pkg' block in manifest")

        self._validate(manifest)
        return manifest

    def _parse_pkg_block(self, manifest: PackageManifest):
        self._advance()  # consume 'pkg'
        if self._peek().kind == TOK_STRING:
            manifest.pkg.name = self._advance().value

        self._expect(TOK_LBRACE, "expected '{' after 'pkg'")

        while self._peek().kind != TOK_RBRACE and self._peek().kind != TOK_EOF:
            key_tok = self._expect(TOK_IDENT, "expected field name in 'pkg' block")
            self._expect(TOK_COLON, f"expected ':' after field '{key_tok.value}'")

            if key_tok.value == "name":
                manifest.pkg.name = self._expect(TOK_STRING, "expected string for 'name'").value
            elif key_tok.value == "version":
                manifest.pkg.version = self._expect(TOK_STRING, "expected string for 'version'").value
            elif key_tok.value == "entry":
                manifest.pkg.entry = self._expect(TOK_STRING, "expected string for 'entry'").value
            elif key_tok.value == "description":
                manifest.pkg.description = self._expect(TOK_STRING, "expected string for 'description'").value
            elif key_tok.value == "license":
                manifest.pkg.license = self._expect(TOK_STRING, "expected string for 'license'").value
            elif key_tok.value == "authors":
                manifest.pkg.authors = self._parse_string_list("authors")
            else:
                raise ManifestError(
                    self.filename, key_tok.line, key_tok.col,
                    f"unknown field '{key_tok.value}' in 'pkg' block"
                )

        self._expect(TOK_RBRACE, "expected '}' closing 'pkg' block")

    def _parse_deps_block(self, manifest: PackageManifest):
        self._advance()  # consume 'deps'
        self._expect(TOK_LBRACE, "expected '{' after 'deps'")

        while self._peek().kind != TOK_RBRACE and self._peek().kind != TOK_EOF:
            name_tok = self._expect(TOK_IDENT, "expected dependency name")
            dep_name = name_tok.value
            self._expect(TOK_COLON, f"expected ':' after dependency '{dep_name}'")

            val_tok = self._peek()
            if val_tok.kind == TOK_IDENT and val_tok.value == "git":
                self._advance()
                url = self._expect(TOK_STRING, "expected git repository URL string").value
                tag = None
                if self._peek().kind == TOK_AT:
                    self._advance()
                    tag = self._expect(TOK_STRING, "expected git tag, branch, or commit string after '@'").value
                manifest.deps[dep_name] = DependencySpec(name=dep_name, kind="git", source=url, tag=tag)
            elif val_tok.kind == TOK_IDENT and val_tok.value == "local":
                self._advance()
                path = self._expect(TOK_STRING, "expected local directory path string").value
                manifest.deps[dep_name] = DependencySpec(name=dep_name, kind="local", source=path)
            elif val_tok.kind == TOK_STRING:
                ver = self._advance().value
                manifest.deps[dep_name] = DependencySpec(name=dep_name, kind="registry", source=ver)
            else:
                raise ManifestError(
                    self.filename, val_tok.line, val_tok.col,
                    f"expected 'git', 'local', or version string for dependency '{dep_name}'"
                )

        self._expect(TOK_RBRACE, "expected '}' closing 'deps' block")

    def _parse_link_block(self, manifest: PackageManifest):
        self._advance()  # consume 'link'
        self._expect(TOK_LBRACE, "expected '{' after 'link'")

        while self._peek().kind != TOK_RBRACE and self._peek().kind != TOK_EOF:
            key_tok = self._expect(TOK_IDENT, "expected field name in 'link' block ('libs' or 'flags')")
            self._expect(TOK_COLON, f"expected ':' after field '{key_tok.value}'")

            if key_tok.value == "libs":
                manifest.link.libs.extend(self._parse_string_list("libs"))
            elif key_tok.value == "flags":
                manifest.link.flags.extend(self._parse_string_list("flags"))
            else:
                raise ManifestError(
                    self.filename, key_tok.line, key_tok.col,
                    f"unknown field '{key_tok.value}' in 'link' block (expected 'libs' or 'flags')"
                )

        self._expect(TOK_RBRACE, "expected '}' closing 'link' block")

    def _parse_string_list(self, field_name: str) -> List[str]:
        self._expect(TOK_LBRACKET, f"expected '[' for list '{field_name}'")
        items: List[str] = []

        while self._peek().kind != TOK_RBRACKET and self._peek().kind != TOK_EOF:
            item = self._expect(TOK_STRING, f"expected string item in '{field_name}' list").value
            items.append(item)
            if self._peek().kind == TOK_COMMA:
                self._advance()
            else:
                break

        self._expect(TOK_RBRACKET, f"expected ']' closing '{field_name}' list")
        return items

    def _validate(self, manifest: PackageManifest):
        if not manifest.pkg.name:
            raise ManifestError(self.filename, 1, 1, "missing required field 'name' in pkg block")
        if not manifest.pkg.version:
            raise ManifestError(self.filename, 1, 1, "missing required field 'version' in pkg block")
        if not manifest.pkg.entry:
            raise ManifestError(self.filename, 1, 1, "missing required field 'entry' in pkg block")


def parse_manifest(content: str, filename: str = "velo.pkg") -> PackageManifest:
    """Parses a velo.pkg manifest string into a PackageManifest."""
    tokenizer = ManifestTokenizer(content, filename)
    tokens = tokenizer.tokenize()
    parser = ManifestParser(tokens, filename)
    return parser.parse()


def load_manifest(path: str = "velo.pkg") -> PackageManifest:
    """Loads and parses a velo.pkg file from disk."""
    if not os.path.exists(path):
        raise ManifestError(path, 1, 1, "manifest file not found")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return parse_manifest(content, path)
