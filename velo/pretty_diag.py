"""6.3 S1: Stage-1 source-snippet block renderer (the behavioral twin of
src/common/diagnostics.vl's pretty_render_block family).

A block is ADDITIVE output printed right after a positioned one-liner wire
row (whose bytes never change). Byte spec, shared with Stage 2:
    {file}:{line}:{col}: {severity}: {message}
    {line} | {line_text}
    " "*(w+1) + "| " + " "*(col-1) + "^"       (w = decimal digits of line)

line_text is the row's source line with each tab flattened to one space and a
trailing \\r stripped; a past-EOF line yields an empty text row with the
caret at the formula position.

Column-semantics residue: Stage 2 counts BYTES, Stage 1 counts code points
(Python str) — identical on all ASCII house fixtures. Line-end residue:
Stage 1 reads text mode (universal newlines, same as velo/driver.py's
loader), Stage 2 keeps raw bytes and strips exactly the trailing \\r —
identical for LF and CRLF fixtures.

This module never mutates the report or the --json lane; it only re-reads
the (already-loaded, unchanged) source file for the garnish rows.
"""

import sys


def _digit_count(n: int) -> int:
    """Mirror of pretty_digit_count (no min-width padding)."""
    if n <= 0:
        return 1
    c = 1
    while n > 9:
        n //= 10
        c += 1
    return c


def _line_text(source: str, want_line: int) -> str:
    """Mirror of pretty_line_text: tabs flattened to one space, trailing
    \\r stripped, interior bytes kept verbatim; empty for past-EOF lines."""
    n = len(source)
    start = 0
    line_no = 1
    while line_no < want_line and start < n:
        if source[start] == '\n':
            line_no += 1
        start += 1
    end = start
    while end < n:
        if source[end] == '\n':
            break
        end += 1
    if end > start and source[end - 1] == '\r':
        end -= 1
    return source[start:end].replace('\t', ' ')


def _infer_token_len(source: str, want_line: int, col: int) -> int:
    """Infers offending token span for check mode from source text."""
    n = len(source)
    start = 0
    line_no = 1
    while line_no < want_line and start < n:
        if source[start] == '\n':
            line_no += 1
        start += 1
    idx = start + max(0, col - 1)
    if idx >= n or idx < 0:
        return 1
    ch = source[idx]
    if ch.isalnum() or ch == '_':
        end = idx
        while end < n and (source[end].isalnum() or source[end] == '_'):
            end += 1
        return max(1, end - idx)
    if idx + 3 <= n and source[idx:idx + 3] in ("..=", "<<=", ">>="):
        return 3
    if idx + 2 <= n and source[idx:idx + 2] in ("->", "=>", "==", "!=", "<=", ">=", "..", "/*", "+=", "-=", "*=", "/=", "<<", ">>", "&&", "||"):
        return 2
    return 1


def render_block(file, line, col, message, severity, source, length=1, color=False):
    """The exact block bytes — useful for tests and for print_block."""
    w = _digit_count(line)
    caret_pad = max(0, col - 1)
    span_len = max(1, length if length is not None else 1)
    carets = "^" * span_len
    if color:
        if severity == "error":
            sev_str = "\x1b[31merror\x1b[0m"
        elif severity == "warning":
            sev_str = "\x1b[33mwarning\x1b[0m"
        else:
            sev_str = severity
        caret_str = f"\x1b[1m{carets}\x1b[0m"
    else:
        sev_str = severity
        caret_str = carets

    return "\n".join((
        f"{file}:{line}:{col}: {sev_str}: {message}",
        f"{line} | {_line_text(source, line)}",
        " " * (w + 1) + "| " + " " * caret_pad + caret_str,
    ))


def print_block(path, line, col, message, severity, stream=None, length=None, color=False):
    """Reads `path` from disk and prints the block to `stream` (stderr by
    default). Prints NOTHING when the file is unreadable or absent — the
    block is additive garnish, never worth a crash or a row-byte change.
    Re-reads with the driver's loader shape (utf-8) for byte parity with
    the rows the lexer/parser positions were computed from."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            source = fh.read()
    except OSError:
        return
    if length is None:
        length = _infer_token_len(source, line, col)
    print(render_block(path, line, col, message, severity, source, length=length, color=color),
          file=stream if stream is not None else sys.stderr)
