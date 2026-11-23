# 🛠️ Velo Editor Tooling & Integrations

This directory contains editor integrations, syntax grammars, and language server clients for the **Velo** programming language.

---

## 📁 Directory Structure

```
editors/
└── vscode/                      # Visual Studio Code extension
    ├── syntaxes/                # TextMate syntax definitions
    │   ├── velo.tmLanguage.json     # Syntax highlighting for .vl files
    │   └── velo.pkg.tmLanguage.json # Syntax highlighting for velo.pkg manifests
    ├── snippets/                # Snippet libraries (39 templates)
    │   ├── velo.json            # Velo language templates (main, data, kind, loop, etc.)
    │   └── velo.pkg.json        # Package manifest templates
    ├── js/                      # Extension host implementation
    │   ├── extension.js         # Extension lifecycle, commands, and mode dispatch
    │   └── lsp_client.js        # Dependency-free stdio LSP client implementation
    ├── _server/                 # Bundled Python language server (Tier B fallback)
    │   ├── velo_lsp.py          # JSON-RPC / LSP stdio transport
    │   └── velo_analysis.py     # Compiler AST analysis, hover, outline, and completions
    ├── ci/                      # Extension automation and continuous integration
    ├── tests/                   # Extension quality test suite
    │   ├── parity_compiler.py   # Compiler-vs-grammar parity verification
    │   ├── match_spotcheck.js   # Regex rule execution on real code patterns
    │   ├── sim_extension.js     # VS Code API simulation
    │   ├── sim_lsp.js           # LSP server protocol probes
    │   ├── sim_lsp_ext.js       # End-to-end client-server simulations
    │   └── run_tests.py         # Multi-tier test harness
    ├── package.json             # Extension manifest and configuration schema
    ├── language-configuration.json      # Brackets, auto-closing pairs, comments
    ├── pkg-language-configuration.json  # Package manifest configuration
    ├── install.ps1              # One-click Windows PowerShell installer
    ├── uninstall.ps1            # Extension uninstaller
    ├── pack_vsix.py             # Dependency-free .vsix package generator
    └── README.md                # Detailed VS Code extension documentation
```

---

## 🚀 Installation Instructions

### Method 1: Automatic Installer (PowerShell)

From `editors/vscode`:

```powershell
cd editors/vscode
.\install.ps1
```

The script automatically:
1. Detects `code` on `PATH`.
2. Packages the extension into `.vsix` on the fly via `python pack_vsix.py` (if not already present).
3. Installs via `code --install-extension <vsix> --force`.
4. Falls back to a versioned copy into `$HOME\.vscode\extensions` if `code` is not in `PATH`.

Then reload VS Code: press **`Ctrl+Shift+P`** → **`Developer: Reload Window`**.

### Method 2: Manual Packaging & Install

```powershell
cd editors/vscode
python pack_vsix.py
code --install-extension velo-lang-0.6.0.vsix --force
```

### Method 3: Uninstall

```powershell
cd editors/vscode
.\uninstall.ps1
```

---

## ⚙️ Configuration & Diagnostics Modes

Configure the extension in VS Code Settings under `velo.*`:

| Setting | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `velo.mode` | `string` | `"off"` | `"off"` (highlighting/snippets only), `"check"` (on-save diagnostics), or `"lsp"` (full language server) |
| `velo.compilerPath` | `string` | `"velo"` | Path to the native `velo` compiler binary (e.g. `C:/projects/easylang/bin/velo.exe`) |
| `velo.repoPath` | `string` | `""` | Root path of the Velo repository (required for bundled Python LSP mode) |
| `velo.lspServer` | `string` | `"python"` | Language server implementation: `"python"` (bundled Stage 1 analyzer) or `"native"` (`velo lsp`) |

---

## 🧪 Testing & Conformance

Editor integrations are verified continuously against compiler ground truths:

1. **Grammar Conformance Suite** (`tests/test_grammar_conformance.py`):
   Tokenizes real Velo fixtures with both the TextMate grammar and the compiler lexer, asserting 100% token coverage, category agreement, and zero keyword drift.
   ```powershell
   python -m pytest tests/test_grammar_conformance.py -v
   ```

2. **Parity Drift Detection** (`editors/vscode/tests/parity_compiler.py`):
   Validates keywords, builtin module surfaces, `use` roots, primitive types, and snippet counts against compiler definitions.
   ```powershell
   python editors/vscode/tests/parity_compiler.py
   ```

3. **Extension Test Suite** (`editors/vscode/tests/run_tests.py`):
   Runs grammar spot-checks, extension simulations, and LSP client/server probes without external npm dependencies.
   ```powershell
   python editors/vscode/tests/run_tests.py
   ```
