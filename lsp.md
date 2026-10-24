# lsp.md — 6.4 Developer Tooling: Language Server Protocol (LSP)

> Companion build sheet to `gaps.md` §6.4.
> Standard JSON-RPC 2.0 Language Server Protocol (LSP 3.17) implementation
> powering rich IDE and editor experiences (diagnostics, outline, hover,
> go-to-definition, autocompletion) for Velo.

---

## 1. Overview & Architecture

Velo's Language Server (`velo.lsp`) is a dependency-free, stdio-driven JSON-RPC 2.0
server that interfaces directly with the compiler frontend (`velo.analysis`,
`velo.lexer`, `velo.parser`, `velo.driver`, `velo.tokens`):

```text
+-----------------------------+
| Editor (VS Code / Neovim)   |
+-----------------------------+
               | stdio JSON-RPC 2.0 (Content-Length)
               v
+-----------------------------+
| velo lsp (velo.lsp.Protocol)|
+-----------------------------+
               |
               v
+-----------------------------+
| Dispatcher (Request Router) |
+-----------------------------+
               |
               v
+-----------------------------+
| velo.analysis.VeloAnalysis  | <---> CompilerDriver.check()
| (Overlay, Provenance AST,   |       (In-memory buffer overlay,
|  Symbols, Hover, Def, Comp) |        no temporary files on disk)
+-----------------------------+
```

---

## 2. Server Capabilities

The server announces standard LSP 3.17 capabilities on `initialize`:

| Capability | LSP Method | Description |
| :--- | :--- | :--- |
| **Buffer Sync** | `textDocument/didOpen`<br>`textDocument/didChange`<br>`textDocument/didClose` | Full-text in-memory buffer synchronization. Buffer edits are analyzed in memory using an active `Path.read_text` overlay with zero temp files written to disk. |
| **Diagnostics** | `textDocument/publishDiagnostics` | Live error and warning diagnostics emitted on every open or buffer change via `CompilerDriver.check()`. Cleared immediately on close. |
| **Document Outline** | `textDocument/documentSymbol` | Hierarchical symbol tree: `data` structs (with child fields), `kind` enums (with child variants), `aka` type aliases, and `act` functions. |
| **Hover Tooltips** | `textDocument/hover` | Markdown tooltips displaying function signatures, parameter names and types, return types, local variable types, and struct definitions. |
| **Go-to-Definition** | `textDocument/definition` | Navigates from usage to declaration for types, functions, local variables, and imported modules (`use "<file>"`). |
| **Autocompletion** | `textDocument/completion` | Context-aware completions triggered globally or on `.`: keywords (including Chapter 5.2 collections `shelf`, `map`, `ring`, `bitset`, `heap`, `of`), primitive types (`dyn`, `usize`, etc.), and builtin module functions (`io.`, `mem.`, `fs.`, `str.`, `math.`, `time.`, `os.`, `thread.`). |

---

## 3. CLI Command Surface

The LSP server is exposed as a first-class compiler subcommand:

```bash
# Launch language server on stdio (auto-detects repo root)
velo lsp

# Explicit repo root
velo lsp /path/to/project

# Python direct invocations
python velo.py lsp
python -m velo.lsp
```

---

## 4. Editor Integrations

### VS Code (via `editors/vscode`)
Configure in `settings.json`:
```json
{
  "velo.mode": "lsp",
  "velo.pythonPath": "python",
  "velo.repoPath": "C:/projects/easylang"
}
```

### Neovim (`nvim-lspconfig`)
```lua
local lspconfig = require('lspconfig')
local configs = require('lspconfig.configs')

if not configs.velo then
  configs.velo = {
    default_config = {
      cmd = { 'velo', 'lsp' },
      filetypes = { 'velo' },
      root_dir = lspconfig.util.root_pattern('velo.py', 'bin/velo.exe', '.git'),
      settings = {},
    },
  }
end
lspconfig.velo.setup{}
```

### Helix (`languages.toml`)
```toml
[[language]]
name = "velo"
scope = "source.velo"
injection-regex = "velo"
file-types = ["vl"]
roots = ["velo.py", "bin/velo.exe", ".git"]
language-servers = ["velo-lsp"]

[language-server.velo-lsp]
command = "velo"
args = ["lsp"]
```

---

## 5. Verification Snapshot [SHIPPED ✅ 2026-10-25]

* **Unit Tests** (`tests/test_lsp.py`): **8/8 passing**
  - Protocol message framing (`Content-Length` encode/decode).
  - Lifecycle (`initialize` capabilities, `shutdown`, `exit`).
  - Live diagnostics on unsaved buffers (clean, syntax-error, fix, clear).
  - Document outline extraction (`data`, `kind`, `aka`, `act`).
  - Hover tooltips (functions, parameters, locals).
  - Go-to-definition (functions, struct types).
  - Completions (keywords, primitive types, builtin module methods `io.`, `mem.`, `fs.`, `math.`).
  - End-to-end `python velo.py lsp` subprocess interaction over piped stdio.
* **VS Code Extension Test Runner** (`editors/vscode/tests/run_tests.py --real`): **6/6 suites passed**
  - `parity_compiler.py`: 20/20 checks passing (keywords, builtins, types, grammar).
  - `match_spotcheck.js`: 14/14 spot-checks passing.
  - `sim_extension.js`: 7/7 extension simulation checks passing.
  - `sim_lsp.js`: 11/11 server probes passing.
  - `sim_lsp_ext.js`: 10/10 extension client simulations passing.
  - `sim_real.js`: 3/3 real compiler probes passing.
* **Packaging**: Re-packed `velo-lang-0.4.0.vsix` with updated grammar and server.
* **Bootstrap Chain & Fixed-Point Determinism**:
  - Rebuilt: Gen1 → Gen2 → Gen3 → `bin/velo.exe`.
  - Bit-for-bit determinism verified: Gen2 ≡ Gen3 `emit-c src/main.vl`.
* **Line Count Ceilings**: All files ≤ 399 lines (`src/main.vl` 304).
