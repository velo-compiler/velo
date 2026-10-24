# diagnostics.md — 6.3 Diagnostic Formatting & Error Visuals: complete build sheet

> Companion to `gaps.md` §6.3. Everything the chapter needs, with the target
> contract for each remaining slice. Every slice lands as one golden-rule
> unit: pin the slice in `gaps.md` 6.3 ✅ (＋ tests + this sheet), both
> compiler stages in the same commit → parity suite → bootstrap chain
> rebuild + Gen2 ≡ Gen3 emit-c SHA-256 fixed point → `scripts/count_lines.py`
> clean → one conventional commit.

## Goal

Modern-compiler diagnostics (Clang/Rust/Zig shape): every **positioned**
`[Velo Error]` / `[Velo Warning]` row gains a source-snippet block below it —

```text
examples/02_math_and_logic.vl:29:14: error: undeclared identifier 'foo'
29 |     let x = foo + 10;
   |             ^
```

— without touching one byte of the pinned one-liner wire format. The one-liner
row IS the wire (215 tests, the sweeps, and the `velo check --json` capture
parser all consume its exact bytes); the block is additive output that every
existing filter ignores. Colors come as an opt-in mode in S4; S1–S3 are plain.

## The plumbing map (scouted 2026-10-24, bytes from live probes)

**Stage 1 (Python).** `velo.py` CLI → `velo/driver.py` `check()`:
check collects `{file, line, col, severity, message}` diagnostics —
`LexerError`/`ParserError` are positioned (exception carries `line`/`col` /
`token`), and every other exception (including ALL ~153 semantic
`raise ValueError` sites in `velo/codegen_c.py` + 1 in `velo/monomorphize.py`)
rides `line=0/col=0` — the fail-fast-vs-collect-many divergence 6.7 pinned.
`velo.py` prints the JSON report's rows to **stderr** as
`[Velo {Error|Warning}] {file}:{line}:{col} - {message}` (the `[Velo Error] {message}`
shape when line ≤ 0), `[Velo] Check passed: …` on ok, and in `run`/`build`
mode a catch-all prints `\n[Velo Error] {str(exc)}` (unstripped exception
text). JSON mode prints only the report — no rows.

**Stage 2 (self-hosted).** `src/common/diagnostics.vl` (22 lines) emits the
one-liners with io.println → **stdout**. Labels: analysis sites pass the
pseudo-filename `"semantic"`, parser sites pass `p.filename` (the REAL
canonical path) except `parser_decl.vl` (4 sites: `"parse"`) and
`parser_stmt.vl:200` (`"parser"`) which pass pseudo-names, and
`lexer.vl` (2 sites: `report_warning("lexer", …)`) which is warning-only.
The whole class list: ~140 analysis sites across 13 `analysis/*.vl` files,
14 parse sites (6+4+2+2), 2 lexer warning sites, 2 `codegen_io.vl` sites,
misc. The `Parser` struct carries BOTH `filename` and `source` (parser.vl:18-19),
so every parse site has everything a renderer needs at hand.

**The capture channel (check.vl, load-bearing).** BOTH stage-2 check lanes
redirect fd 1 during the compile (`velo_capture_begin/end` externs → temp
file `velo_check_capture.tmp`): `run_check_pretty` echoes the captured
stream verbatim; `run_check_json` re-parses the capture line-by-line —
`check_diag_to_json` peels `[Velo Error|Warning] file:line:col - msg` shapes
(and re-attributes the `semantic`/`parser`/`parse` pseudo-names to
`src_path`, check.vl:141), while `check_is_noise` skips `[Velo] …`
confirmations, `…Semantic analysis failed with…` summaries, and blank lines.
**Anything else falls through to the UNPOSITIONED JSON branch (check.vl:160)
and becomes a sham diagnostic with the whole line as the message** — so every
non-`[Velo …]` line the sites print (i.e. any snippet block) MUST be taught
to `check_is_noise` as a skip, or `velo check --json` bytes break. Stage 1's
json lane needs nothing (it never prints rows).

**No module-level mutable state exists** (126 top-level `let` hits are all
immutable constants) — and none is needed now that the capture carries the
rows: the S2 engine re-derives everything the driver already has.

## Contract (byte rules)

* **The one-liner wire is sacred**: `[Velo {Error|Warning}] {label}:{line}:{col} - {message}`
  keeps its exact bytes — including the pseudo-name labels
  (`semantic`/`parse`/`parser`/`lexer`). exit codes, the `Semantic analysis
  failed with N errors.` summary row, the `[Velo] Check passed:` row, and
  `velo check --json` output all stay byte-stable.
* **The block is additive**, printed immediately after its one-liner on the
  SAME stream (stage 2: stdout; stage 1: stderr). House normalize filters
  (`[Velo Error]`-prefixed-line strips) ignore it → all 215 tests stay green.
* **Block shape (locked)**, for a positioned row
  `(file, line, col, message, severity)`:
  * header: `{file}:{line}:{col}: {error|warning}: {message}` — file/label
    spelling stays whatever the row already carries (stage 1: the invoked
    spelling; stage 2 parse rows: the canonical spelling; identical for
    fixtures invoked without `./`, `..`, or backslashes — battery rule).
  * `w = digits(line)` (no min-width padding — an intentional simplification
    of Rust's column padding; the illustrative gaps-6.3 example is not
    byte-binding). content line: `{line:>w} | {line_text}`.
    alignment line: `{" "*(w+1)} |`… precisely `" "*(w+1) + "| "` + caret
    padding; the caret line: that alignment + `" "*(col-1) + "^"`, so the
    `^` sits under content column `col` (ASCII).
  * `line_text` = the row's source line with each tab flattened to one
    space, `\r` stripped, no truncation. A row past EOF yields an empty
    `line_text` (trailing space after `| `) with the caret at the formula
    position — deterministic, documented.
  * point caret (`^`, one per row) in S1; span carets (`^^^`) arrive in S3
    where a token span is known.
* **Only positioned rows block** (line > 0). Stage-1 semantic rows
  (ValueErrors, line = 0) keep the one-liner-only shape — the 6.7 divergence
  continues; stage-2 analysis rows join in S2 via the driver.
* **Col semantics** are a documented residue: cols count BYTES on stage 2
  and code points on stage 1 — identical for ASCII; the battery uses ASCII
  fixtures only (existing divergence, not a 6.3 defect).
* `--json` lane: JSON bytes remain exact on both stages. The stage-2 noise
  rule must learn to skip block lines in S1 (see S1 step 4).

## House rules (shared with 5.3/5.4/5.5)

* Both stages, one commit; docs + gaps + tests same commit; chain rebuild +
  fixed point whenever `src/**/*.vl` changes; no UTF-8 BOM in `.vl` files.
* Line budget snapshot at chapter open (2026-10-24): `lexer.vl` 399 (hard,
  needs a shave for any addition), `symbol_table.vl` 399, `parser_expr.vl`
  395, `parser.vl` 396, `parser_decl.vl` 375, `parser_stmt.vl` 358,
  `parser_binary.vl` 123, `check.vl` 341, `driver.vl` 296,
  `diagnostics.vl` 22, `velo.py` 101. 6.3 grows ONLY in new files or wide
  files: stage 2's renderer lives in `diagnostics.vl` (→ ~60), the parse
  wrapper lives in `parser_binary.vl` (→ ~140), S2's pretty engine lives in
  a NEW `src/backend/pretty_recon.vl`, stage 1's renderer lives in a NEW
  `velo/pretty_diag.py`; `velo.py` absorbs ≤ +10.
* Anti-collision: Velo/C names dodge libc + the main-wrapper stash (`argc`,
  `argv`, `log`, `short`, …); house suffixes (`vlist`, `fminv`).

## Slice plan

* **S1 — parse-row blocks, point caret, both stages.**
  1. Stage 2 renderer: `src/common/diagnostics.vl` gains
     `act pretty_render_block(file, line, col, message, sev, source)`
     (+ `use "utils.vl"` for `copy_slice_to_string`) — byte spec above.
  2. Stage 2 wrapper: `src/frontend/parser_binary.vl` gains
     `act report_parse(p: @Parser, label: string, line: i32, col: i32, msg: string)`
     = `report_error(label, line, col, msg)` + the block from
     `p.filename`/`p.source` (`sev` = "error"). The `label` param keeps the
     5 pseudo-name sites byte-identical.
  3. Site swaps (net-zero line moves, all 14): `parser.vl` 6,
     `parser_decl.vl` 4 (label `"parse"`), `parser_expr.vl` 2,
     `parser_stmt.vl` 2 (label `"parser"`). `lexer.vl`'s 2 warning sites are
     UNTOUCHED in S1 (they are warnings with no path in the Lexer struct —
     S3 adds the field + a small shave). `codegen_io.vl`'s 2 sites ride S2.
  4. JSON lane: `src/backend/check.vl` `check_is_noise` gains
     `if not check_starts_with(line_text, "[Velo ") { return true }` —
     block lines skip; `check_count_errors` (counts `[Velo Error]` rows
     only) and `check_diag_to_json` stay untouched.
  5. Stage 1: NEW `velo/pretty_diag.py` (render_block(file, line, col,
     message, severity, sev_stream) — re-reads and slices the file itself,
     so the JSON report dict gains NO fields) + `velo.py`: the check row
     loop prints the block after each positioned row (stderr), and the
     `run`/`build` catch-all prints a block when the exception carries
     `line`/`col` (`LexerError` → `.line/.col`; `ParserError` →
     `.token.line/.col`), with the exception-text prefix
     (`Lexer Error at line L, col C: ` / `Parser Error …` ) stripped for
     the block header. JSON branch and 0/0 rows untouched.
  6. Battery: NEW `tests/test_diagnostics_pretty.py` cloning
     `test_check_cli.py`'s `_run_stage1`/`_run_native` harness — a parse
     fixture both stages agree on (same wording/position class) pinned
     byte-equal WITH its block; the `--json` byte pins (unchanged shapes);
     run-mode catch-all fixtures; a stage-2-only lexer-warning row pin
     (unchanged bytes).
  7. Sweep `sweep_63_s1.py` (clone sweep_54_final.py mechanics):
     parse fixtures both stages × (check/run), rc-map for the run rows,
     several cumulative 5.x wording rows re-swept for no-regression, and
     the `--json` byte rows on both stages.
  8. Chain rebuild Gen1→Gen2→Gen3 + `bin/velo.exe`; fixed point moved (both
     stages change) → record the new SHA; count_lines; gaps pin + sheet
     snapshot; one conventional commit `feat(diag): 6.3 S1 — parse-row
     snippet blocks on both stages`.
* **S2 — semantic-row blocks on stage 2, via the capture (NO site edits).**
  `run_check_pretty` (check.vl) stops echoing verbatim: a NEW
  `src/backend/pretty_recon.vl` reconstructs the stream — each captured
  `[Velo Error|Warning]` line reprinted verbatim, then a block rendered
  under positioned rows whose peeled label matches the single-visited-file
  case against the re-read `src_path` source (the pseudo-name re-attribution
  mirrors check.vl:141's logic). Multi-file programs (visited list ≥ 2):
  rows keep one-liner-only (block-less) with a documented residual —
  per-node file provenance is a future chapter (the AST does not carry it).
  The JSON lane is already covered by S1's noise rule. Stage-1 semantic rows
  stay block-less (the 6.7 divergence documented; ~153 Python raise sites
  gaining positions is its own future chapter, NOT this one). The
  `run`/`build` lanes keep row-only output for semantic rows (a capture
  wrapper around `compile_source_to_c` there is a documented optional
  follow-up, not owed). Chain rebuild + fixed point; battery: semantic-row
  block pins on stage 2 + rerun of S1 rows; sweep cumulative.
* **S3 — span carets (`^^^`) where the token span is known.** Stage-2
  `Token` already carries `start: usize` + `length: usize` (token.vl:97-98)
  — raw source byte spans. The parse wrapper's signature grows the span
  (the sites hold the offending token); the renderer prints
  `^` × max(1, length) with the same alignment for ASCII. Stage 1: verify
  `velo/tokens.py` `Token` carries the raw span (add `start`/`length` in
  `lexer.py` if absent — mirrored on stage 2 which already has them), and
  `LexerError`/`ParserError` carry the span to the catch-all. Lexer
  warnings join here: `lexer.vl` gains a `file_path` field
  (`create_lexer` + 1 param; 2 driver/docgen call sites; needs ~3-4 shaved
  comment lines in `lexer.vl`, at 399 hard) and warnings render blocks with
  `warning:` headers. Semantic rows keep point carets (no lexeme evidence)
  — residual.
* **S4 — colors, `--color auto|always|never` (default auto).** The renderer
  takes a mode; `always` wraps header severity word/row and caret in fixed
  ANSI codes (locked in the sheet at ship time: error = red 31, warning =
  yellow 33, summary/caret bold 1); `never` = today's bytes; `auto`
  resolves to **never on both stages** until they share a true TTY
  detector (a native `velo_std_istty` extern + a Python `sys.isatty` twin —
  a runtime addition that can land in a later chapter; documented as the
  auto=never residual). Byte-pinned under `--color=always` on both stages;
  `velo check --json` stays color-free ALWAYS. Flag plumbing on stage 2:
  `main.vl` parses `--color` next to `--json`; stage 1: `velo.py` argparse.
* **S5 — finale sweep + chapter close.** Cumulative sweep (the S1–S4 rows
  re-swept), battery refresh, the gaps.md 6.3 header flip to
  `— COMPLETE (slices 1–5) ✅`, the sheet's "THE CHAPTER SHIPS IN FULL"
  trailer.

## Reference snapshots (live bytes, 2026-10-24 probe)

Fixture: `use sys.io` + `act main() -> i32 { let q = ` + backquote
(lex_bad), and a bare-shelf / undeclared-identifier probe. Stage 1
`check` on lex_bad (stderr, rc 1):

```text
[Velo Error] C:/projects/easylang/.velo_cache/v63probe/lex_bad.vl:3:13 - Unterminated raw string literal
```

Stage 2 `check` on the same file (stdout, rc 1) — the two stages classify
the SAME source differently (6.7 divergence, made visible as block shape
differences in S1+):

```text
[Velo Error] C:/projects/easylang/.velo_cache/v63probe/lex_bad.vl:7:1 - Expected '}' at end of block
```

Stage 1 `run` on lex_bad (stderr, rc 1) — the catch-all's unstripped
exception text:

```text
[Velo Error] Lexer Error at line 3, col 13: Unterminated raw string literal
```

Stage 2 `check` on the undeclared-identifier fixture — multi-row collected
analysis rows + the summary (the S2 engine's material):

```text
[Velo Error] semantic:3:12 - Undeclared identifier
[Velo Error] semantic:3:5 - Return type mismatch
[Velo Error] Semantic analysis failed with 2 errors.
```

Stage 2 `check --json` re-attributes the pseudo-names to `src_path`
(and stays byte-stable through S1–S5):

```text
{"file": ".velo_cache/v63probe/sem_bad.vl", "ok": false, "diagnostics": [{"file": ".velo_cache/v63probe/sem_bad.vl", "line": 3, "col": 12, "severity": "error", "message": "Undeclared identifier"}, {"file": ".velo_cache/v63probe/sem_bad.vl", "line": 3, "col": 5, "severity": "error", "message": "Return type mismatch"}]}
```

**S1 target block shapes** (hand-composed from the byte spec, to be pinned
byte-exact by the battery): the stage-2 lex_bad check row gains —

```text
C:/projects/easylang/.velo_cache/v63probe/lex_bad.vl:7:1: error: Expected '}' at end of block
7 | 
  | ^
```

(row 7 is past EOF → empty `line_text`, caret at the formula position);
and an interior example with `w = digits(29) = 2` (the 14th column caret —
the caret under `foo`):

```text
examples/02_math_and_logic.vl:29:14: error: undeclared identifier 'foo'
29 |     let x = foo + 10;
   |             ^
```

## Discoveries ledger (probe findings recorded for FUTURE chapters, not 6.3)

* Stage 1 `velo check` **passes** `let s = shelf` AND `return foo`
  (undeclared identifiers ride through the stage-1 checker unheard and die
  at GCC as `'shelf' undeclared` / `'foo' undeclared` with `velo run`
  printing a GCC-shaped error + the generated C) — the stage-1 semantic
  checker misses free-identifier resolution that stage 2 catches
  (`semantic:3:13 - Undeclared identifier`). A candidate new gaps entry.
* The stage-2 lexer has NO hard errors — unknown characters and unclosed
  block comments are `report_warning("lexer", …)` rows and the lexer keeps
  going (stage 1 raises `LexerError` and fails fast at the same inputs).
  Candidate language gap: severity/continuation policy for lex inputs.
* `load_file_and_deps` frees each file's source at act exit (defer), so any
  post-parse consumer must re-read or copy — driver.vl:98 ruled out the
  "keep the source in the driver" shortcut for S2, favoring re-read.

## Verification snapshots

(Filled per slice at ship time, fs.md pattern: [x] rows with counts,
sweep rc, chain SHA, suite totals, ceilings.)

### S1 — parse-row snippet blocks on both stages (shipped 2026-10-24)

* [x] Renderer acts `pretty_render_block` / `pretty_line_text` /
  `pretty_digit_count` (+ helper `pretty_pad_spaces`) in
  `src/common/diagnostics.vl` (22 → 122 lines; wide headroom for S2/S3);
  wrapper `report_parse(p, label, line, col, msg)` in
  `src/frontend/parser_binary.vl` (123 → 134) — calls the pinned
  `report_error` verbatim, then rides the additive block.
* [x] 14 site swaps, wording NET ZERO: `parser.vl` 6 (label `p.filename`),
  `parser_decl.vl` 4 (pseudo `"parse"`), `parser_expr.vl` 2
  (`p.filename`), `parser_stmt.vl` 2 (L86 `p.filename`, L200 pseudo
  `"parser"`). Lexer warning rows and codegen_io rows untouched (S1 scope).
* [x] JSON-lane guard: `check_is_noise` (src/backend/check.vl) now returns
  true for any line NOT starting `[Velo` — snippet headers/gutters/carets
  cannot become sham unpositioned diagnostics; `check --json` byte-stable
  on both stages.
* [x] Stage-1 twin: new `velo/pretty_diag.py` (`render_block`, `print_block`
  — re-reads the file with the loader shape `utf-8`, silent no-print on
  unreadable paths) + `velo.py` integration: check loop prints the block
  under each positioned row on stderr; the run/build/emit-c catch-all
  prints blocks for `LexerError` (`.line/.col`) and `ParserError`
  (`.token.line/.col`) with the row-prefix strip mirrored from
  `driver.check`.
* [x] Battery `tests/test_diagnostics_pretty.py`: 13 tests (row+block order,
  `--json` block-free, tab flatten, EOF empty snippet, run lanes, warning
  rows block-less, cross-stage gutter/caret/position parity). Full suite
  **228/228** (215 prior + 13).
* [x] Sweep `sweep_63_s1.py` (temp, uncommitted like the 5.x sweeps):
  **57/57 clean** — 8 cumulative accepts (incl. the example-35 parity row),
  all 43 reject wording rows re-pinned through the block-blind normalize,
  3 full-byte check-lane rows pinned per stage (broken / eofbrace / paren),
  plus tab-flatten, dup-alias divergence, and 2 `--json` rows.
* [x] Chain rebuilt Gen1→Gen2→Gen3, `bin/velo.exe` updated; new fixed point
  SHA-256 `DD0988C3A97516445660DEF7F6B59FAC60083CAF3B4B177FB331C3383B3D3520`
  (new SHA is expected — both stages changed this slice).
* [x] Ceilings: every source ≤ 399 (`parser.vl` 396, `parser_expr.vl` 395,
  `parser_decl.vl` 375, `parser_stmt.vl` 358, `check.vl` 347,
  `parser_binary.vl` 134, `diagnostics.vl` 122).
* [x] Cross-stage parity state: first-diagnostic positions, gutter lines and
  caret bytes agree; ROW/BLOCK-HEADER wordings stay per-stage — the
  pre-existing 6.7 divergence (stage 1 embellishes `(got …)`) means NO parse
  fixture yields full-byte cross-stage equality (probed: broken, eofbrace,
  paren, bare-shelf — the last is stage-2-clean). Documented in the battery.
* Recorded residuals (pre-existing, untouched): stage-2 pretty check echo
  doubles `\r\n` → `\r\r\n` under the capture roundtrip (pytest/`text=True`
  and the wording sweeps collapse it; `--json` lane clean); stage-2 `run` on
  parse-broken input exits 0 (best-effort execute path — `check` is the
  rc-gated lane).

### S2 — semantic-row blocks on stage 2 (shipped 2026-10-24)

* [x] Stream reconstructor in new `src/backend/pretty_recon.vl` (272 lines);
  wired into `src/backend/check.vl` `run_check_pretty` (347 → 348 lines):
  reconstructs the captured stdout stream so that positioned semantic error
  rows gain source-snippet blocks identical to parse-row blocks, without
  modifying any of the ~140 semantic report sites in `src/analysis/*.vl`.
* [x] Pseudo-name re-attribution: `semantic`, `backend`, `parser`, `parse`
  peeled labels are re-attributed to `src_path` (matching check.vl:141 logic)
  and render snippet blocks from the re-read source file.
* [x] Single-file vs multi-file distinction: `recon_is_single_file` scans
  the source for non-sys `use` statements. Multi-file programs (visited
  list ≥ 2) keep one-liner-only output (block-less) with a documented
  residual (AST lacks per-node file provenance).
* [x] Zero duplication on S1 parse blocks: lookahead check ensures that
  positioned rows whose subsequent line is already a snippet block line
  (i.e. not starting `[Velo`) pass through verbatim without re-rendering.
* [x] Stage-1 semantic rows stay block-less (documented 6.7 divergence).
* [x] JSON lane stability: `velo check --json` remains block-free on both
  stages (covered by S1's `check_is_noise` rule).
* [x] Battery `tests/test_diagnostics_pretty.py`: +5 tests (single semantic
  error row+block, multi-row semantic errors with summary, multi-file
  block-less pin, JSON lane stability, Stage 1 block-less parity). Full suite
  **233/233** (228 prior + 5).
* [x] Chain rebuilt Gen1→Gen2→Gen3, `bin/velo.exe` updated; fixed point
  SHA-256 `4EFBFD05966A777AE656C04FDEF8C108DFDBD6725F8A204C901B78987D653CE4`
  (Gen2 ≡ Gen3 emit-c).
* [x] Ceilings: every source ≤ 399 (`pretty_recon.vl` 272, `check.vl` 348,
  `diagnostics.vl` 122).

### S3 — span carets (^^^) and lexer warning blocks (shipped 2026-10-24)

* [x] Stage 2 renderer: `pretty_render_block` (`src/common/diagnostics.vl`, 130 lines)
  gains `length: usize` and renders `span_len = max(1, length)` carets via loop.
* [x] Stage 2 parse wrapper: `report_parse` (`src/frontend/parser_binary.vl`, 134 lines)
  gains `length: usize` and passes it to `pretty_render_block`. All 14 parse report
  sites across `parser.vl` (6), `parser_decl.vl` (4), `parser_expr.vl` (2),
  and `parser_stmt.vl` (2) pass the offending token's `.length`.
* [x] Semantic rows: `src/backend/pretty_recon.vl` passes `length = 1` (point caret residual).
* [x] Lexer warnings: `src/frontend/lexer.vl` `Lexer` struct gains `file_path: string`;
  `create_lexer` retains backward-compatible signature initializing `file_path: "<input>"`,
  and `driver.vl` sets `lex.file_path = file_path` / `lex.file_path = source_path`;
  the 2 warning sites in `lexer.vl` (unclosed comment length 2, unknown character length 1)
  render `warning:` snippet blocks with exact span carets. Comments shaved so `lexer.vl`
  stays at 397 lines (<= 399 ceiling).
* [x] Stage 1 twin: `velo/tokens.py` `Token` gains `start: int = 0, length: int = 0`;
  `velo/lexer.py` records `start` and `length` on each `Token`, `LexerError` accepts `length`;
  `velo/pretty_diag.py` adds `_infer_token_len` when `length` is omitted (preserving the
  `--json` schema without adding fields to `driver.check` report dict); `velo.py` catch-all
  passes `tok.length` for `ParserError` and `e.length` for `LexerError`.
* [x] Battery `tests/test_diagnostics_pretty.py`: +2 tests (20 passed; suite **235/235**
  from 233 prior).
* [x] Chain rebuilt Gen1→Gen2→Gen3, `bin/velo.exe` updated; fixed point SHA-256
  `375B55A400CBFCBBD1E47E359C217F6F207F3E1A25AF80F74CB4227CE6B7E902`.
* [x] Ceilings: every source <= 399 (`driver.vl` 298, `lexer.vl` 397, `parser.vl` 396,
  `diagnostics.vl` 130).

### S4 — colors, `--color auto|always|never` (shipped 2026-10-24)

* [x] Mode resolution: `--color auto|always|never` (default `auto`). `auto` resolves to
  `never` on both stages (documented residual until true TTY detector is implemented).
  `never` outputs verbatim uncolored bytes (today's exact bytes).
* [x] Stage 2 renderer & plumbing:
  - `src/common/diagnostics.vl` (157 lines): `g_pretty_color: bool`, `pretty_set_color(enabled: bool)`,
    `pretty_get_color() -> bool`; `pretty_render_block` renders ANSI colored severity word
    (`\x1b[31merror\x1b[0m` in red 31, `\x1b[33mwarning\x1b[0m` in yellow 33) and wraps carets in
    bold 1 (`\x1b[1m{carets}\x1b[0m`).
  - `src/main.vl` (182 lines): parses `--color auto|always|never` and `--color=...` next to `--json`.
    Sets `pretty_set_color(color_always)` on pretty check and `pretty_set_color(false)` on JSON check.
  - `src/backend/pretty_recon.vl` (276 lines): wraps semantic analysis summary rows in bold 1
    (`\x1b[1m{summary_line}\x1b[0m`) when `pretty_get_color()` is active.
* [x] Stage 1 twin:
  - `velo/pretty_diag.py`: `render_block` and `print_block` gain `color: bool = False`; wraps error
    in red 31, warning in yellow 33, and carets in bold 1.
  - `velo.py`: `check_parser` adds `--color` argument with choices `["auto", "always", "never"]`
    and default `"auto"`; passes `color=color_enabled` in check diagnostics loop and catch-all.
* [x] Sacred wire format preservation:
  - `[Velo Error]` / `[Velo Warning]` wire rows are NEVER colored (remain 100% byte-identical).
  - `--json` check output remains strictly color-free on both stages even with `--color=always`.
* [x] Battery `tests/test_diagnostics_pretty.py`: +2 tests (22 passed; suite **237/237** from 235 prior).
* [x] Chain rebuilt Gen1→Gen2→Gen3, `bin/velo.exe` updated; fixed point SHA-256
  `87257A5E45A53C1062ED897BA1CFF57233DD0F1EB2E4594ADD5D1CFB7E59F871`.
* [x] Ceilings: every source <= 399 (`pretty_recon.vl` 276, `main.vl` 182, `diagnostics.vl` 157).


