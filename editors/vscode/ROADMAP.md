# Velo VS Code Extension — Upgrade Roadmap (v0.1.0 → v1.0)

> **Status (2026-10-21): Phases 0–4 applied — Phase 4 quality tooling (dev-only, runtime unchanged, v0.4.0). Publication decided: vsix-only. CI activation by tracking the tree remains open.**
> Phases 0–1 (v0.2.0): grammar parity (`aka`, `#align`/`#packed`, `op`, `fs.remove_file`),
> 39 snippets, `onEnterRules`, offline `pack_vsix.py`, `uninstall.ps1`, installer
> version-generic, icon placeholder (owner artwork decision open).
> Phase 2 (committed `26bcaaf`, both compilers): `velo check [--json]` — parse → semantic →
> monomorphize Pass 0, no codegen/execution; JSON schema
> `{file, ok, diagnostics: [{file, line, col, severity, message}]}`; 15 CLI tests both
> sides; SPEC §9 documented; gaps §6.7 records residuals, incl. the discovered-and-
> worked-around Stage 2 codegen defect (`f(x) != null` re-evaluates the call — bind to a
> local; commit `6deb061`).
> Phase 3 Tier A (v0.3.0): `js/extension.js` activation, zero npm deps — debounced
> (250 ms/doc) on-save/on-open `velo check --json` → DiagnosticCollection → Problems panel.
> Settings: `velo.mode` (`off` default / `check`; `lsp` arrives with Tier B), 
> `velo.compilerPath`, `velo.compilerArgs`. Runs are judged by parseable JSON, not exit
> code (exit 1 + valid JSON is the normal diagnostics path); missing binary, hang (15 s
> timeout), or unparsable output degrades to *no diagnostics* + a line in the `Velo`
> output channel — never noise. Per-doc run-token guard discards superseded runs;
> restart-safe first paint re-derives on-disk state for already-open files; mode `off`
> is exactly the v0.2 behavior.
> Verified: 7/7 vscode-stub simulations (position/severity mapping incl. 1-based →
> 0-based and line-0 clamping, clean-file clear, ENOENT + junk-output degrade, off-mode
> no-op, restart hygiene); real-compiler probes — Stage 1 (`python velo.py`) and Stage 2
> (`bin/velo.exe`) map the same broken fixture to the identical 0-based (2,0) with the
> compiler's message; packaged vsix (7 payload files incl. `extension/js/extension.js`,
> `.js` content-type) installs via the real `code` CLI and reports
> `velo.velo-lang@0.3.0`; stale `velo-lang-0.2.0.vsix` removed. The in-GUI red-squiggle
> visual check is pending owner (same precedent as Phases 0/1).
> Phase 3 Tier B (v0.4.0): embedded Python LSP — `_server/velo_lsp.py` (stdlib-only
> JSON-RPC/stdio loop) + `_server/velo_analysis.py` (analysis layer over the real Stage 1
> frontend: lexer/parser/driver with a buffer-content overlay during single synchronous
> calls — no temp files written). Server keeps the driver's import-resolution mirrored
> WITH per-file provenance (tokens + AST per file) for outline/hover/def; diagnostics
> always go through `CompilerDriver.check` (the compiler's verdict is authoritative).
> Features in roadmap order: live diagnostics from unsaved buffers → outline (data
> fields, kind variants, aka, acts) → hover (signatures + origin, locals/params) →
> go-to-definition (token-index cursor fallback covers type positions the AST stores as
> bare `type_name` strings) → completions (keywords, types, imported decls, builtin
> member lists after `io.`/`mem.`/`fs.`/`sys.`). Extension side: `js/lsp_client.js`
> hand-rolled framing/transport (no npm deps), `velo.mode: off|check|lsp` with live
> relaunch on config change, 300 ms debounced full-buffer sync, `velo.pythonPath`,
> `velo.repoPath` (missing repoPath degrades to off + log). Discoveries recorded:
> statement-level semantic divergence added to gaps §6.7 (9) — Stage 1 accepts certain
> parse-valid statements (e.g. assignment to an undeclared identifier inside an act
> body) that Stage 2 rejects; hence `lsp` diagnostics always come from Stage 1, while
> `check` reflects whatever `velo.compilerPath` names. Honest limits: struct-field
> member completion (needs type inference) and astral columns (UTF-16 ≠ python-char
> for emoji) are recorded residuals.
> Verified end to end: 11/11 server probes over real stdio framing against the real
> python child (init caps, broken publish, clean clear, outline w/ children, hover on
> act + local, goto-def to the 0-based decl line, `io.` member completions, didClose
> clear, shutdown/exit); 10/10 extension-client sims driving the REAL server through
> the extension's own code (incl. mode switches off→lsp and teardown hygiene);
> Tier A regression suite still 7/7 + real-compiler probes pass. GUI visual checks
> pending owner (outline tree + squiggles) per precedent.

Owner material: this file and everything in `editors/` is deliberately untracked; it plans
the editor workstream and plugs into `gaps.md` §6.3 (diagnostics) / §6.4 (LSP).

## Current state (baseline audit of v0.1.0, before Phases 0–3A)

Declarative-only extension v0.1.0: TextMate grammar (353 lines), 33 snippets, language
configuration, folder-copy installer + one packaged `.vsix`. **Zero executable code — the
editor cannot report any error.** Grammar staleness verified against the real compiler:

| Fact | Status |
|---|---|
| `aka` contextual keyword (Milestone 3.6) | missing from grammar; renders as plain variable |
| `#align(N)` / `#packed` attributes | zero `#` rules in grammar |
| `op` keyword (`act op +(a, b)`) | missing from grammar (in compiler keyword table + example 25) |
| `fs.remove_file` | implemented by compiler, unknown to grammar builtins |
| escape set (`\n\t\r\0\"\'\\{} \xHH \uHHHH`) | grammar matches lexer exactly ✓ |
| numbers (bases, suffixes, separators) | matches ✓ |
| `.Variant` dot shorthand, `it`, `null`, word ops | matches ✓ |
| nested `/* /* */ */` comments | lexer nests; TextMate can't — known cosmetic limit |
| `mainargs` snippet (argc/argv shape) | unverified: no example uses CLI args — verify or demote |
| installer | hardcodes `0.1.0` folder; bypasses VS Code extension management; README claims personal-install state |

## Phase 0 — Language-state parity (→ v0.2.0, extension-only, ~2 h)

1. **Grammar `aka`**: rule scoped to declaration shape (line start + `aka Name = Target`),
   scope `keyword.declaration.alias.velo`; bare `aka` elsewhere must stay a plain identifier
   (it is contextual in the language — grammar must not lie about it).
2. **Grammar attributes**: `#align` / `#packed` → `punctuation.definition.attribute.velo`
   + `entity.other.attribute-name.velo`; `(...)` numbers flow via existing numbers rule.
3. **Grammar `op`**: keyword scope for `op`; operator symbol after it picks up existing
   operator rules. `fs` builtins: add `remove_file`.
4. **Snippets** (+~6): `aka` alias template; struct-with-field-defaults; `#align`/`#packed`
   struct templates; kind-variant `on` dispatch (`.Quit =>`, `.KeyDown(k) =>`, `else =>`);
   `op` overload template. Fix/verify `mainargs` against the CLI-arg truth.
5. **language-configuration**: `onEnterRules` — `//` continuation, `/** */` block
   continuation + ` */` closer.
6. **README**: distribution-neutral rewrite (remove "already installed" claim), add the new
   surface incl. `aka`/attributes/`op`.
Acceptance: all `examples/*.vl` spot-check with no visibly wrong coloring; snippets validate
as JSON; grammar loads clean.

## Phase 1 — Install & packaging hygiene (→ v0.2.x, extension-only, ~2 h)

1. `install.ps1` reads version from `package.json` (`ConvertFrom-Json`); prefers
   `code --install-extension` when the CLI is on PATH, falls back to a version-named copy;
   cleans superseded version folders. `uninstall.ps1`.
2. `.vscodeignore` (source-side artifacts excluded); extension icon placeholder — real
   artwork is an owner decision.
3. Single advertised install path documented; `.vsix` either regenerated with the tree or
   removed from the tree (generate on demand).
Acceptance: version bump + re-install requires zero script edits; no zombie folders.

## Phase 2 — `velo check` machine-readable diagnostics (→ v0.3.0, BOTH compilers + tests, ~4-6 h)

Keystone: today's CLI (`run | build | emit-c | doc`) has no diagnostics-only mode, and
`doc` exists on the Python side only. Every editor/CI integration needs:

1. `velo check <file> [--json]`, both compilers: parse → semantic → monomorphize Pass 0,
   **no** codegen/execution. Exit 0/1; pretty mode reuses existing message strings;
   `--json` schema:
   `{ "file", "ok", "diagnostics": [{ "file", "line", "col", "severity", "message" }] }`.
2. Reuse driver pipeline; emit paths untouched (determinism unaffected — verify).
3. Tests both sides: success / parse error / semantic error / 3.6 missing-field negative;
   JSON schema stability.
4. Docs: SPECIFICATION CLI table + `gaps.md` (§6.3 note: pretty snippet rendering can layer
   on top; see known residual below).
**Known residual (already recorded in gaps.md)**: wording of some messages differs between
the two compilers (e.g. missing-field error). JSON consumers must normalize; unify wording
in a later unit.
Acceptance: both compilers produce exit-0 on `examples/26_advanced_structs.vl --json` and
exit-1 with correct line/col on a broken file.

## Phase 3 — Diagnostics in the editor (→ v0.3.x–v0.5, extension, ~3 h Tier A / ~1-2 d Tier B)<!-- TIER A APPLIED in v0.3.0; TIER B APPLIED in v0.4.0 -->

- **Tier A (on-save diagnostics, no npm deps)**: activation script (`js/extension.js`),
  setting `velo.compilerPath`; debounce-save → `velo check --json` → `DiagnosticCollection`
  + Problems panel. Failure of the tool degrades to "no diagnostics", never noise.
- **Tier B (embedded LSP server, Python)**: `velo/` is importable as a library — server
  reuses lexer/parser/AST directly (bundled under `_server/`, PYTHONPATH pointed at a
  Velo checkout or a bundled copy). Settings `velo.mode`: `off | check | lsp`.
  Feature order: diagnostics → document symbols (outline of act/data/kind/aka) → hover
  (types) → go-to-definition (same tree) → completions (keywords, module functions, then
  struct fields/kind variants; string-library completions mature with `gaps.md` §5.1).
Acceptance: known-broken fixture shows the red squiggle with the compiler's message;
restart-safe; both modes off = exactly today's behavior.

## Phase 4 — Quality system (→ v1.0, when Node available)<!-- APPLIED 2026-10-21: dependency-free suite + CI blueprint; npm tier blueprinted; publication pending owner -->

GitHub Actions: `vsce package` + `vscode-tmgrammar-test` grammar snapshots on every push;
marketplace publication (owner publisher account) vs. continued vsix-only distribution —
owner decision.

Applied (dev-only, outside the vsix — runtime unchanged, v0.4.0 stands): `tests/` quality
suite driven by `run_tests.py` (`--quick` / default / `--real`), **6/6 suites**:
`parity_compiler.py` 16/16 pins grammar↔compiler truths (keywords vs `velo.tokens.KEYWORDS`
plus contextual `aka`/`it`; builtin member registries io/mem/fs/str across `codegen_c.py`'s
dispatch, grammar, analyzer; the use-root truth `sys.(io|mem|fs)` after discovering Stage 2
rejects `use sys.str` as a missing file — gaps §6.7 (10), analyzer completion roots
corrected in the same change; 71 scope-name lint; snippet baseline 39; language config);
`match_spotcheck.js` 14/14 replays real sample lines through the real TM patterns (aka shape
guard, `sys.str` root exclusion, PascalCase dot-variants, suffixed/hex numbers, char
escapes); the Phase 2–3 behavioral sims are ported to portable paths (`sim_extension`
7/7, `sim_lsp` 11/11, `sim_lsp_ext` 10/10, `sim_real` 3/3 over both real compilers).
`.vscodeignore` keeps `tests/`+`ci/` out of the package; snippet baseline documented.
`ci/github-workflow.yml` blueprints the workflow (python+node job = this suite, npm tier =
`vscode-tmgrammar-test` snapshots + `vsce package`, optional msys2 job = `--real` probes);
it activates when the owner tracks the extension tree.

**Publication decision (owner, 2026-10-21): stay vsix-only** — distribution continues
from the locally packed `velo-lang-0.4.0.vsix`; no marketplace step for now. The
`vscode-tmgrammar-test` + `vsce` npm tier therefore remains a blueprint that activates
only if/when the tree is tracked (CI value: snapshot regression proofs, not distribution).

## Explicit non-goals (for now)

Debugger adapter (DAP wrapping gdb), formatter-on-save, multi-file refactoring,
workspace-wide symbol indexing, any change to compiler semantics.

## Order of execution & value

| Phase | Cost | Impact |
|---|---|---|
| 0 grammar/snippets ✅ applied | ~2 h | language truth visible |
| 1 packaging ✅ applied | ~2 h | painless install |
| 2 `velo check` ✅ applied (`26bcaaf`) | ~4-6 h | enables ALL editor+CI tooling |
| 3 Tier A ✅ applied (v0.3.0) | ~3 h | red squiggles from the real compiler |
| 3 Tier B ✅ applied (v0.4.0) | 1-2 d | hover/outline/goto-def/completions |
| 4 CI/tests | ~half d | regression-proof, publishable |

Phases 0, 1, 3 Tier A can land independently of each other; Phase 2 unblocks Tier A's full
value and everything in Tier B.
