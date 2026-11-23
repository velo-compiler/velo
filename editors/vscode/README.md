# ⚡ Velo Language Support for VS Code (v0.4.0)

Syntax highlighting, snippets, language configuration, **on-save compiler
diagnostics**, and an **embedded language server** (outline, hover,
go-to-definition, completions) for the **Velo** systems programming language
(`.vl`) — the game-biased, zero-GC language that compiles itself.

The extension is dependency-free: highlighting, snippets, diagnostics from the
real compilers' `velo check --json` contract (Phase 3 Tier A), and a bundled
Python LSP server reusing the Stage 1 compiler frontend (Phase 3 Tier B) —
no npm or pip packages anywhere.

---

## ✨ Features

### 1. Snippets (39 templates)
Type a prefix and press **Tab**/ **Enter** to expand. Highlights of the current set:

| Prefix | Expands To |
| :--- | :--- |
| `main` / `mainargs` | Entry point with or without `argc: i32, argv: @string` (verified against both compilers) |
| `act` / `actv` / `actg` | Function declarations (plain / void / generic) |
| `data` / `datag` / `datad` | Structs — plain / generic / **with field-default initializers** |
| `dataalign` / `datapacked` | Structs annotated `#align(N)` / `#packed` |
| `aka` | Named primitive alias: `aka Name = u64` (contextual keyword, top level) |
| `kind` / `kindu` | Pure enum / payload-bearing tagged union |
| `onk` | Dispatch over kind variants **with payload binding** — `.KeyDown(key) =>` (no type annotations in arms, per SPEC §7.3) |
| `opover` | Operator overload: `act op +(a: Vector2, b: Vector2)` |
| `loop` / `loopr` / `loops` / `loopi` / `loopc` / `loopw` / `loopinf` | The full `loop` family |
| `zone` / `memalloc` / `heapalloc` / `defer` | Arena allocation + LIFO cleanup |
| `println` / `pl` / `fsread` / `fswrite` / `strlen` | I/O and file helpers |
| `mut` / `let` / `useio` / `usemem` / `usefs` / `extern` | Declarations and imports |

### 2. Syntax highlighting (current-language parity)
* **Keywords**: `act`, `data`, `kind`, `op`, `zone`, `loop`, `in`, `mut`, `let`, `if`, `else`, `on`, `defer`, `return`, `break`, `continue`, `use`, `extern`, `as`, `sizeof`, `and`, `or`, `not`, `it` plus literals `true` / `false` / `null`.
* **`aka` alias declarations** — highlighted only in the true declaration shape (`aka Name = Target` at column 0 with a primitive target); `aka` used as a variable/field name elsewhere stays a normal identifier, exactly like the language's contextual keyword rule.
* **Attributes**: `#align(N)`, `#packed` render as named attributes.
* **Pointers**: `@` (pointer / address-of) and `.@` (dereference).
* **Types**: all fixed-width integers, `f32`/`f64`, `bool`, `string`, `void`, plus PascalCase user types and alias names.
* **Strings**: double-quoted strings with interpolation `{expr}` and escapes (`\uHHHH`, `\xHH`, `\n \t \r \0 \\ \' \" \{ \}`), raw backtick strings, character literals.
* **Numbers**: hex / binary / octal, `_` separators, suffixes (`255u8`, `3.14f32`), float exponents.
* **Variants**: dot-shorthand `.North`, `.KeyDown(65)`.
* **Built-in modules**: `sys.io`, `sys.mem`, `sys.fs`, `sys.str` with their current function surface (`io.println|print|print_char`, `mem.alloc|heap_alloc|free|used|heap_used`, `fs.read_file|write_file|remove_file|exists|size|remove`, `str.len`).
* **Comments**: `//`, `///` doc lines, nestable `/* ... */` (nested tails are a TextMate limitation — see ROADMAP).

### 3. Language configuration
* Comment toggling (`Ctrl+/`), bracket matching, auto-closing pairs (incl. raw-string backticks).
* **Smart Enter behavior**: `//` lines and `/** */` doc blocks auto-continue on Enter.
* Indentation and `// #region` folding.

### 4. On-save compiler diagnostics (v0.3, opt-in)
Saved and newly opened `.vl` files are validated by running the **real compilers**'
`velo check --json` command and rendering the report in the Problems panel.

* **Enable it**: put `velo.mode`: `"check"` in settings, then point at a compiler:
  * Stage 2 native binary: `"velo.compilerPath": "C:/projects/easylang/bin/velo.exe"`.
  * Stage 1 Python compiler: `"velo.compilerPath": "python"` and
    `"velo.compilerArgs": ["C:/projects/easylang/velo.py"]`.
* Errors, warnings, and unpositioned load diagnostics all surface with the compiler's
  exact message text; positions are 1-based in the compiler and mapped to the editor.
* **Never noise**: a missing compiler, a hang (15 s timeout), or unparsable output
  degrades to *no diagnostics* for that file — failures are visible only in the
  `Velo` output channel. `velo.mode: "off"` (the default) returns to pure
  highlighting/snippets behavior.
* Restart-safe: a fresh session re-derives diagnostics from the on-disk state of
  already-open files.

### 5. Embedded language server (v0.4, opt-in)

`velo.mode: "lsp"` spawns a bundled Python server (`_server/velo_lsp.py`, speaks
standard LSP over stdio; the client transport is hand-rolled — still zero npm
dependencies) that reuses the **Stage 1 compiler frontend directly** (lexer,
parser, driver). It adds:

* **Live diagnostics** — recomputed from the *unsaved buffer* as you type
  (300 ms debounce), not just on save; cleared automatically on close.
* **Outline** — `data` (with fields), `kind` (with variants), `aka`, `act`
  signatures, `extern` import surface in the Symbols view.
* **Hover** — act signatures, data field tables, kind variants, aka targets,
  local variable/param types, each with the declaring file and line.
* **Go-to-definition** — from any identifier or type position (tokens cover
  type uses the AST stores as plain strings), across `use`-imported files.
* **Completions** — keywords, primitive types, every declaration reachable
  through your imports, and builtin member lists after `io.` / `mem.` /
  `fs.` / `sys.` (mirroring the real builtin surfaces).

Settings (all in the `velo.*` group):

| Setting | Meaning |
| :--- | :--- |
| `velo.mode` | `off` (default) / `check` / `lsp` |
| `velo.pythonPath` | Interpreter for the LSP server, default `python` |
| `velo.repoPath` | Checkout root containing `velo/` (e.g. `C:/projects/easylang`) — **required** for `lsp`; missing it degrades to `off` with a log line |

**Which compiler judges what** (honest scoping): `check` mode runs whatever
`velo.compilerPath` points at — your Stage 2 binary or Stage 1. `lsp` mode
always analyzes with the Python compiler under `velo.repoPath`, so a program
in a known stage-divergence class (recorded in the project `gaps.md` §6.7, e.g.
statement-level semantic checks) may be clean in `lsp` but flagged in `check`
with a Stage 2 binary, or vice versa. Server errors (a missing or stripped
`velo` import) surface as a single actionable diagnostic on the file, never as
noise. GUI visual checks (squiggles, outline tree) follow the same
owner-verifies precedent as Phases 0–2; the data flow itself is
sim-verified end to end against the real server.

---

## 🚀 Install

Run from this folder:

```powershell
.\install.ps1
```

The script reads the version from `package.json` (no edits needed on bumps) and prefers
`code --install-extension` with the packaged `velo-lang-<version>.vsix` (official path),
falling back to a versioned folder copy; superseded versions are cleaned automatically.

Then press **`Ctrl+Shift+P`** → **`Developer: Reload Window`**, open any `.vl` file, and
try `main`, `data`, `onk`, or `aka`. To see diagnostics, set `velo.mode: "check"` and a
`velo.compilerPath` (or `velo.mode: "lsp"` plus `velo.repoPath` for live diagnostics,
outline, hover, go-to-definition, and completions), and check the Problems panel.

## Uninstall

```powershell
.\uninstall.ps1
```

## Rebuild the .vsix

After changing extension sources (grammar, snippets, README), regenerate the package:

```powershell
python .\pack_vsix.py
```

The packer is offline and dependency-free; it reads identity fields from `package.json`
and honors `.vscodeignore`, producing `velo-lang-<version>.vsix`.

## Tests (development)

`tests/` is the Phase 4 quality suite — every check is dependency-free
(python stdlib + node, no npm/pip installs) and self-contained:

```powershell
python .\tests\run_tests.py          # stub + server tiers (6 suites)
python .\tests\run_tests.py --quick  # compiler-parity + grammar spot-checks only
python .\tests\run_tests.py --real   # everything, incl. the real toolchain tier
```

| Tier | Suites | Covers |
| :--- | :--- | :--- |
| stub | `parity_compiler.py`, `match_spotcheck.js`, `sim_extension.js` | grammar↔compiler drift (keywords, builtin members, use roots, types, scope names, snippet baseline), pattern behavior on real sample lines, on-save plumbing with fake compilers |
| server | `sim_lsp.js`, `sim_lsp_ext.js` | the real python LSP server probes + extension-client end-to-end |
| real | `sim_real.js` | both real compilers (Stage 1 `python velo.py`, Stage 2 `bin/velo.exe`) driving editor diagnostics |

The suite pins three compiler truths so drift fails loudly:
`velo.tokens.KEYWORDS` (keywords), the codegen builtin member dispatch
(`io/mem/fs/str` registries), and both stage loaders' `use sys.*` acceptance
(`sys.str` is a member surface, never a suggested `use` root — `gaps.md` §6.7 (10)).

A GitHub Actions blueprint for this suite (plus the npm tier:
`vscode-tmgrammar-test` grammar snapshots and `vsce package`) lives in
[`ci/github-workflow.yml`](ci/github-workflow.yml); it activates when the
extension tree is committed to a tracked branch (owner decision — see the
roadmap). Snippet counts are snapshotted in `tests/baselines/suite_counts.json`
and are updated deliberately when snippets change.

## 🗺 Upgrading

Remaining tooling gaps (struct-field member completion, cross-session symbol
caching, astral-column edge cases) and their language-side mirrors live in
[`ROADMAP.md`](ROADMAP.md) and the project `gaps.md` §6.3–6.4/§6.7.
