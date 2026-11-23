// Velo Language Support — editor diagnostics + LSP features (ROADMAP Phase 3).
//
// Tier A (`velo.mode: "check"`): wires the real compilers ("velo check --json",
// docs/SPECIFICATION.md §9) into the Problems panel: debounced on save/open,
// one DiagnosticCollection, zero npm dependencies. Tool failure degrades to
// "no diagnostics" — never noise. Runs are judged by parseable JSON, not exit
// code (exit 1 + valid JSON is the normal diagnostics path).
//
// Tier B (`velo.mode: "lsp"`): spawns the bundled Python LSP server
// (_server/velo_lsp.py), which reuses the Stage 1 compiler frontend directly
// (lexer/parser/driver). Adds outline, hover, go-to-definition, completions
// and live diagnostics. The server speaks standard LSP over stdio; the client
// transport in js/lsp_client.js is hand-rolled (still no npm dependencies).
//
// `velo.mode: "off"` (default) is exactly the v0.2 behavior: highlighting and
// snippets only.
//
// Compiler targeting: `check` mode runs whatever `velo.compilerPath` points
// at (Stage 2 binary or Stage 1 via `python` + `velo.compilerArgs`). `lsp`
// mode always analyzes with the Python compiler reachable via
// `velo.repoPath` (a checkout containing velo/).

const vscode = require("vscode");
const child_process = require("child_process");
const path = require("path");
const { LspClient } = require("./lsp_client.js");

const DEBOUNCE_MS = 250;
const SYNC_DEBOUNCE_MS = 300;
const CHECK_TIMEOUT_MS = 15000;
const SERVER_DIR = path.join(__dirname, "..", "_server");
const SERVER_SCRIPT = path.join(SERVER_DIR, "velo_lsp.py");

function activate(context) {
    const collection = vscode.languages.createDiagnosticCollection("velo");
    context.subscriptions.push(collection);
    const channel = vscode.window.createOutputChannel("Velo");
    context.subscriptions.push(channel);

    const setting = (name, fallback) =>
        vscode.workspace.getConfiguration("velo").get(name, fallback);

    const isEligible = (doc) =>
        doc && doc.languageId === "velo" && doc.uri && doc.uri.scheme === "file";

    let modeSwitch = null; // {dispose()} teardown of the active mode's machinery

    function relaunch() {
        if (modeSwitch) {
            try { modeSwitch.dispose(); } catch (_) { /* already gone */ }
            modeSwitch = null;
        }
        const mode = setting("mode", "off");
        if (mode === "lsp") {
            modeSwitch = startLspMode();
        } else if (mode === "check") {
            modeSwitch = startCheckMode();
        }
    }

    // -------------------------------------------------------------------
    // Tier A: on-save diagnostics via `velo check --json`
    // -------------------------------------------------------------------

    function startCheckMode() {
        const timers = new Map(); // doc key -> debounce timer
        const runs = new Map();   // doc key -> in-flight run token

        const cwdFor = (uri) => {
            const folder = vscode.workspace.getWorkspaceFolder(uri);
            return folder ? folder.uri.fsPath : path.dirname(uri.fsPath);
        };

        // Compiler positions are 1-based; VS Code ranges are 0-based. Unpositioned
        // diagnostics (line 0) land as a one-character range on the first line.
        const rangeFor = (line, col) => {
            const l = Math.max(0, (line | 0) - 1);
            const c = Math.max(0, (col | 0) - 1);
            return new vscode.Range(l, c, l, c + 1);
        };

        const clearDoc = (doc) => {
            const key = doc.uri.toString();
            if (timers.has(key)) {
                clearTimeout(timers.get(key));
                timers.delete(key);
            }
            collection.delete(doc.uri);
        };

        const runCheckNow = (doc) => {
            const key = doc.uri.toString();
            const myRun = (runs.get(key) || 0) + 1;
            runs.set(key, myRun);

            const args = setting("compilerArgs", []).slice();
            // CLI contract: `velo check <file> [--json]` — file first, flag last
            // (docs/SPECIFICATION.md §9). The compiler binds argv[2] to the file.
            args.push("check", doc.uri.fsPath, "--json");

            child_process.execFile(
                setting("compilerPath", "velo"),
                args,
                { cwd: cwdFor(doc.uri), timeout: CHECK_TIMEOUT_MS },
                (err, stdout) => {
                    if (runs.get(key) !== myRun) {
                        return; // a newer run supersedes this one
                    }
                    runs.delete(key);

                    let report = null;
                    try {
                        report = JSON.parse(stdout);
                    } catch (_) {
                        report = null;
                    }
                    if (!report || typeof report.ok !== "boolean" || !Array.isArray(report.diagnostics)) {
                        const reason = err ? (err.code || err.message) : "unparseable output";
                        channel.appendLine(
                            `check unavailable (${reason}) for ${path.basename(doc.uri.fsPath)}; no diagnostics shown`
                        );
                        collection.delete(doc.uri);
                        return;
                    }

                    const diags = [];
                    for (const d of report.diagnostics) {
                        if (!d || typeof d.message !== "string" || !d.message) {
                            continue;
                        }
                        const diag = new vscode.Diagnostic(
                            rangeFor(d.line, d.col),
                            d.message,
                            d.severity === "warning" ? vscode.DiagnosticSeverity.Warning : vscode.DiagnosticSeverity.Error
                        );
                        diag.source = "velo";
                        diags.push(diag);
                    }
                    if (diags.length > 0) {
                        collection.set(doc.uri, diags);
                    } else {
                        collection.delete(doc.uri);
                    }
                }
            );
        };

        const scheduleCheck = (doc) => {
            if (!isEligible(doc)) {
                return;
            }
            const key = doc.uri.toString();
            if (timers.has(key)) {
                clearTimeout(timers.get(key));
            }
            timers.set(key, setTimeout(() => {
                timers.delete(key);
                runCheckNow(doc);
            }, DEBOUNCE_MS));
        };

        const disposables = [
            vscode.workspace.onDidSaveTextDocument(scheduleCheck),
            vscode.workspace.onDidOpenTextDocument(scheduleCheck),
            vscode.workspace.onDidCloseTextDocument(clearDoc),
            collection,
        ];

        // Restart-safe first paint: surface the on-disk state of already-open files.
        for (const doc of vscode.workspace.textDocuments) {
            if (isEligible(doc)) {
                scheduleCheck(doc);
            }
        }

        return {
            dispose() {
                for (const t of timers.values()) clearTimeout(t);
                timers.clear();
                for (const d of disposables) { try { d.dispose(); } catch (_) { /* noop */ } }
                collection.clear();
            },
        };
    }

    // -------------------------------------------------------------------
    // Tier B: embedded Python LSP
    // -------------------------------------------------------------------

    function findNativeCompiler(compilerSetting, repoPath) {
        const fs = require("fs");
        if (compilerSetting && compilerSetting !== "velo" && fs.existsSync(compilerSetting)) {
            return compilerSetting;
        }
        if (repoPath) {
            const p = path.join(repoPath, "bin", process.platform === "win32" ? "velo.exe" : "velo");
            if (fs.existsSync(p)) return p;
        }
        if (vscode.workspace && vscode.workspace.workspaceFolders) {
            for (const wf of vscode.workspace.workspaceFolders) {
                const p = path.join(wf.uri.fsPath, "bin", process.platform === "win32" ? "velo.exe" : "velo");
                if (fs.existsSync(p)) return p;
            }
        }
        const devBin = path.join(__dirname, "..", "..", "bin", process.platform === "win32" ? "velo.exe" : "velo");
        if (fs.existsSync(devBin)) return devBin;

        const known = path.join("C:", "projects", "easylang", "bin", process.platform === "win32" ? "velo.exe" : "velo");
        if (fs.existsSync(known)) return known;

        return compilerSetting || "velo";
    }

    function startLspMode() {
        const fs = require("fs");
        const repoPath = setting("repoPath", "");
        const lspServer = setting("lspServer", "auto");
        const nativeBin = findNativeCompiler(setting("compilerPath", "velo"), repoPath);
        const hasNative = fs.existsSync(nativeBin);

        // In test harnesses or when explicitly configured, prefer python if requested or in repo simulation
        const useNative = (lspServer === "native") || (lspServer === "auto" && hasNative && !repoPath) || (hasNative && !fs.existsSync(SERVER_SCRIPT));

        if (!useNative && !repoPath && lspServer === "python") {
            channel.appendLine("velo.mode=lsp with Python server requires velo.repoPath; staying off");
            return { dispose() { } };
        }

        const subscriptions = [];
        const timers = new Map(); // doc key -> sync debounce timer

        let client = null;
        let closed = false;
        const pendingSends = [];

        const uriToFsPath = (uri) => uri.fsPath;

        function startClient() {
            const cwd = (vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0])
                ? vscode.workspace.workspaceFolders[0].uri.fsPath : undefined;
            let startOpts;
            if (useNative) {
                channel.appendLine(`Starting Native Velo LSP server: ${nativeBin} lsp`);
                startOpts = {
                    command: nativeBin,
                    args: ["lsp"],
                    repoPath: repoPath || cwd || "",
                    cwd: cwd || repoPath || undefined,
                    log: (line) => channel.appendLine(line),
                    onExit: () => collection.clear(),
                };
            } else {
                channel.appendLine(`Starting Python LSP server: ${setting("pythonPath", "python")} ${SERVER_SCRIPT}`);
                startOpts = {
                    pythonPath: setting("pythonPath", "python"),
                    serverPath: SERVER_SCRIPT,
                    repoPath,
                    cwd: cwd || repoPath,
                    log: (line) => channel.appendLine(line),
                    onExit: () => collection.clear(),
                };
            }
            LspClient.start(startOpts).then((ready) => {
                if (closed) { ready.dispose(); return; }
                client = ready;
                client.onPublish = (payload) => {
                    const uri = vscode.Uri.parse(payload.uri);
                    if (!payload.diagnostics || payload.diagnostics.length === 0) {
                        collection.delete(uri);
                        return;
                    }
                    const mapped = [];
                    for (const d of payload.diagnostics) {
                        if (!d || typeof d.message !== "string" || !d.message || !d.range) {
                            continue;
                        }
                        const diag = new vscode.Diagnostic(
                            toVscodeRange(d.range), d.message,
                            d.severity === 2 ? vscode.DiagnosticSeverity.Warning : vscode.DiagnosticSeverity.Error
                        );
                        diag.source = "velo";
                        mapped.push(diag);
                    }
                    if (mapped.length > 0) {
                        collection.set(uri, mapped);
                    } else {
                        collection.delete(uri);
                    }
                };
                registerProviders();
                // already-open files join the session
                for (const doc of vscode.workspace.textDocuments) {
                    if (isEligible(doc)) syncDoc("textDocument/didOpen", doc);
                }
                // events that fired while the server was initializing
                const buffered = pendingSends.splice(0);
                for (const send of buffered) send();
            }).catch((err) => {
                channel.appendLine(`LSP server unavailable: ${err && err.message}`);
            });
        }

        function toVscodePosition(p) {
            return new vscode.Position(p.line, p.character);
        }
        function toVscodeRange(r) {
            return new vscode.Range(toVscodePosition(r.start), toVscodePosition(r.end));
        }

        function registerProviders() {
            const td = (doc) => ({ textDocument: { uri: doc.uri.toString() } });

            subscriptions.push(vscode.languages.registerDocumentSymbolProvider("velo", {
                provideDocumentSymbols(doc, _token) {
                    return client && client.request("textDocument/documentSymbol", td(doc))
                        .then((symbols) => (symbols || []).map(toVscodeSymbol))
                        .catch(() => []);
                },
            }));
            subscriptions.push(vscode.languages.registerHoverProvider("velo", {
                provideHover(doc, position, _token) {
                    return client && client.request("textDocument/hover", Object.assign(td(doc), {
                        position: { line: position.line, character: position.character },
                    })).then((hover) => {
                        if (!hover || !hover.contents) return undefined;
                        const md = new vscode.MarkdownString(hover.contents.value || "");
                        const hoverLike = new vscode.Hover(md, hover.range ? toVscodeRange(hover.range) : undefined);
                        return hoverLike;
                    }).catch(() => undefined);
                },
            }));
            subscriptions.push(vscode.languages.registerDefinitionProvider("velo", {
                provideDefinition(doc, position, _token) {
                    return client && client.request("textDocument/definition", Object.assign(td(doc), {
                        position: { line: position.line, character: position.character },
                    })).then((def) => {
                        if (!def || !def.uri || !def.range) return undefined;
                        return new vscode.Location(vscode.Uri.parse(def.uri), toVscodeRange(def.range));
                    }).catch(() => undefined);
                },
            }));
            subscriptions.push(vscode.languages.registerCompletionItemProvider("velo", {
                provideCompletionItems(doc, position, _token) {
                    return client && client.request("textDocument/completion", Object.assign(td(doc), {
                        position: { line: position.line, character: position.character },
                    })).then((items) => (items || []).map((it) => {
                        const item = new vscode.CompletionItem(it.label, symbolKindToCompletionKind(it.kind));
                        if (it.detail) item.detail = it.detail;
                        return item;
                    })).catch(() => []);
                },
            }, "."));
        }

        function toVscodeSymbol(s) {
            const symbol = new vscode.DocumentSymbol(
                s.name, s.detail || "",
                typeof s.kind === "number" ? s.kind : vscode.SymbolKind.Variable,
                toVscodeRange(s.range), toVscodeRange(s.selectionRange)
            );
            for (const child of s.children || []) {
                symbol.children.push(toVscodeSymbol(child));
            }
            return symbol;
        }

        function symbolKindToCompletionKind(kind) {
            switch (kind) {
                case 12: return vscode.CompletionItemKind.Function;
                case 23: case 9: case 7: return vscode.CompletionItemKind.Class;
                case 14: return vscode.CompletionItemKind.Keyword;
                case 3: return vscode.CompletionItemKind.Function;
                default: return vscode.CompletionItemKind.Text;
            }
        }

        function syncDoc(method, doc, version) {
            const send = () => {
                if (!client || !isEligible(doc)) return;
                client.notify(method, {
                    textDocument: Object.assign({ uri: doc.uri.toString() }, method === "textDocument/didOpen" ? {
                        languageId: doc.languageId, version: doc.version || version || 0,
                        text: doc.getText(),
                    } : { version: doc.version || version || 0 }),
                    ...(method === "textDocument/didChange" ? {
                        contentChanges: [{ text: doc.getText() }],
                    } : {}),
                });
            };
            if (method === "textDocument/didChange") {
                const key = doc.uri.toString();
                if (timers.has(key)) clearTimeout(timers.get(key));
                timers.set(key, setTimeout(() => {
                    timers.delete(key);
                    send();
                }, SYNC_DEBOUNCE_MS));
                return;
            }
            if (!client) {
                pendingSends.push(send); // server still initializing: flush on ready
                return;
            }
            send();
        }

        const openSub = vscode.workspace.onDidOpenTextDocument((doc) => syncDoc("textDocument/didOpen", doc));
        const saveSub = vscode.workspace.onDidSaveTextDocument((doc) => syncDoc("textDocument/didChange", doc));
        const changeSub = vscode.workspace.onDidChangeTextDocument((event) => {
            if (event.document && isEligible(event.document)) {
                syncDoc("textDocument/didChange", event.document);
            }
        });
        const closeSub = vscode.workspace.onDidCloseTextDocument((doc) => {
            const key = doc.uri.toString();
            if (timers.has(key)) {
                clearTimeout(timers.get(key));
                timers.delete(key);
            }
            if (client) client.notify("textDocument/didClose", { textDocument: { uri: doc.uri.toString() } });
            collection.delete(doc.uri);
        });

        subscriptions.push(openSub, saveSub, changeSub, closeSub);
        startClient();

        return {
            dispose() {
                closed = true;
                for (const d of subscriptions) { try { d.dispose(); } catch (_) { /* noop */ } }
                for (const t of timers.values()) clearTimeout(t);
                timers.clear();
                if (client) {
                    try { client.dispose(); } catch (_) { /* already gone */ }
                    client = null;
                }
                collection.clear();
            },
        };
    }

    // -------------------------------------------------------------------

    context.subscriptions.push(
        vscode.workspace.onDidChangeConfiguration((event) => {
            if (event.affectsConfiguration("velo")) {
                relaunch();
            }
        })
    );

    // -------------------------------------------------------------------
    // Command Palette integration
    // -------------------------------------------------------------------
    if (vscode.commands && typeof vscode.commands.registerCommand === "function") {
        const getCompiler = () => {
            const compilerPath = setting("compilerPath", "velo");
            const compilerArgs = setting("compilerArgs", []) || [];
            return { compilerPath, compilerArgs };
        };

        const runTerminal = (cmdStr, cwd) => {
            let term = (vscode.window.terminals && vscode.window.terminals.find) ?
                vscode.window.terminals.find(t => t.name === "Velo") : null;
            if (!term && vscode.window.createTerminal) {
                term = vscode.window.createTerminal({ name: "Velo", cwd });
            }
            if (term) {
                if (term.show) term.show(true);
                if (term.sendText) term.sendText(cmdStr);
            }
        };

        const activeFilePath = () => {
            const editor = vscode.window.activeTextEditor;
            return (editor && editor.document && editor.document.fileName) ? editor.document.fileName : null;
        };

        const getCwd = () => {
            const editor = vscode.window.activeTextEditor;
            if (editor && editor.document && editor.document.uri && vscode.workspace.getWorkspaceFolder) {
                const folder = vscode.workspace.getWorkspaceFolder(editor.document.uri);
                if (folder) return folder.uri.fsPath;
                return path.dirname(editor.document.fileName);
            }
            if (vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders.length > 0) {
                return vscode.workspace.workspaceFolders[0].uri.fsPath;
            }
            return process.cwd();
        };

        context.subscriptions.push(
            vscode.commands.registerCommand("velo.run", () => {
                const file = activeFilePath();
                if (!file) {
                    if (vscode.window.showWarningMessage) vscode.window.showWarningMessage("No active Velo file to run.");
                    return;
                }
                const { compilerPath, compilerArgs } = getCompiler();
                const cmdParts = [compilerPath, ...compilerArgs, "run", `"${file}"`];
                runTerminal(cmdParts.join(" "), getCwd());
            })
        );

        context.subscriptions.push(
            vscode.commands.registerCommand("velo.build", () => {
                const file = activeFilePath();
                if (!file) {
                    if (vscode.window.showWarningMessage) vscode.window.showWarningMessage("No active Velo file to build.");
                    return;
                }
                const { compilerPath, compilerArgs } = getCompiler();
                const cmdParts = [compilerPath, ...compilerArgs, "build", `"${file}"`];
                runTerminal(cmdParts.join(" "), getCwd());
            })
        );

        context.subscriptions.push(
            vscode.commands.registerCommand("velo.test", () => {
                const file = activeFilePath();
                if (!file) {
                    if (vscode.window.showWarningMessage) vscode.window.showWarningMessage("No active Velo file to test.");
                    return;
                }
                const { compilerPath, compilerArgs } = getCompiler();
                const cmdParts = [compilerPath, ...compilerArgs, "test", `"${file}"`];
                runTerminal(cmdParts.join(" "), getCwd());
            })
        );

        context.subscriptions.push(
            vscode.commands.registerCommand("velo.pkg.run", () => {
                const { compilerPath, compilerArgs } = getCompiler();
                const cmdParts = [compilerPath, ...compilerArgs, "pkg", "run"];
                runTerminal(cmdParts.join(" "), getCwd());
            })
        );

        context.subscriptions.push(
            vscode.commands.registerCommand("velo.pkg.build", () => {
                const { compilerPath, compilerArgs } = getCompiler();
                const cmdParts = [compilerPath, ...compilerArgs, "pkg", "build"];
                runTerminal(cmdParts.join(" "), getCwd());
            })
        );

        context.subscriptions.push(
            vscode.commands.registerCommand("velo.pkg.check", () => {
                const { compilerPath, compilerArgs } = getCompiler();
                const cmdParts = [compilerPath, ...compilerArgs, "pkg", "check"];
                runTerminal(cmdParts.join(" "), getCwd());
            })
        );
    }

    relaunch();
}

function deactivate() {
    // Mode machinery disposes through its own teardown on session end.
}

module.exports = { activate, deactivate };
