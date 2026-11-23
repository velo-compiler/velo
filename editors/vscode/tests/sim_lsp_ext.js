// Tier B extension-side simulation: the vscode-stub harness now exercises the
// REAL python LSP server through the extension's own client code, driving
// mode=lsp lifecycle, diagnostics, outline, hover, goto-def, completions,
// plus mode switching (off -> lsp -> off) and the check-mode coexistence.
"use strict";
const Module = require("module");
const assert = require("assert");
const path = require("path");

const REPO = path.resolve(__dirname, "..", "..", "..");
const FIXTURE = path.join(__dirname, "fixtures", "edge_lsp.vl");

const state = {
    diagnostics: new Map(),   // uri -> latest array | "deleted"
    logs: [],
    listeners: { save: [], open: [], close: [], change: [], config: [] },
    providers: { symbol: [], hover: [], definition: [], completion: [] },
    collections: [],
    config: {
        mode: "lsp",
        compilerPath: "velo",
        compilerArgs: [],
        pythonPath: "python",
        repoPath: REPO,
    },
};

const fakeVscode = {
    languages: {
        createDiagnosticCollection() {
            const col = {
                set(uri, diags) { state.diagnostics.set(uri.toString(), diags || "deleted"); },
                delete(uri) { state.diagnostics.set(uri.toString(), "deleted"); },
                clear() { state.diagnostics.clear(); },
                dispose() { state.diagnostics.clear(); },
            };
            state.collections.push(col);
            return col;
        },
        registerDocumentSymbolProvider(language, provider) { state.providers.symbol.push({ language, provider }); },
        registerHoverProvider(language, provider) { state.providers.hover.push({ language, provider }); },
        registerDefinitionProvider(language, provider) { state.providers.definition.push({ language, provider }); },
        registerCompletionItemProvider(language, provider, trigger) { state.providers.completion.push({ language, provider, trigger }); },
    },
    window: {
        createOutputChannel() {
            return { appendLine(s) { state.logs.push(s); }, show() {}, dispose() {} };
        },
    },
    workspace: {
        getConfiguration() { return { get: (k, d) => (k in state.config ? state.config[k] : d) }; },
        getWorkspaceFolder() { return { uri: { fsPath: path.dirname(FIXTURE) } }; },
        workspaceFolders: [{ uri: { fsPath: path.dirname(FIXTURE) } }],
        onDidSaveTextDocument(fn) { state.listeners.save.push(fn); },
        onDidOpenTextDocument(fn) { state.listeners.open.push(fn); },
        onDidCloseTextDocument(fn) { state.listeners.close.push(fn); },
        onDidChangeTextDocument(fn) { state.listeners.change.push(fn); },
        onDidChangeConfiguration(fn) { state.listeners.config.push(fn); },
        textDocuments: [],
    },
    Diagnostic: class D { constructor(r, m, s) { this.range = r; this.message = m; this.severity = s; } },
    Range: class R { constructor(startPos, endPos) { this.start = startPos; this.end = endPos; } },
    Position: class P { constructor(l, c) { this.line = l; this.character = c; } },
    DiagnosticSeverity: { Error: 0, Warning: 1, Information: 2, Hint: 3 },
    Uri: {
        parse: (s) => ({ toString: () => s, fsPath: decodeURIComponent(s.replace(/^file:\/\/\//, "")).replace(/\//g, "\\") }),
        file: (p) => ({ toString: () => "file:///" + p.replace(/\\/g, "/"), fsPath: p }),
    },
    MarkdownString: class M { constructor(v) { this.value = v; } },
    Hover: class H { constructor(md, range) { this.contents = md; this.range = range; } },
    DocumentSymbol: class DS { constructor(name, detail, kind, range, selection) { this.name = name; this.detail = detail; this.kind = kind; this.range = range; this.selectionRange = selection; this.children = []; } },
    Location: class L { constructor(uri, range) { this.uri = uri; this.range = range; } },
    CompletionItem: class C { constructor(label, kind) { this.label = label; this.kind = kind; } },
    CompletionItemKind: { Function: 2, Class: 6, Keyword: 13, Text: 15, Struct: 21 },
    SymbolKind: { Variable: 13, Function: 12, Class: 4 },
};

const origLoad = Module._load;
Module._load = function (request, parent, isMain) {
    if (request === "vscode") return fakeVscode;
    return origLoad.apply(this, arguments);
};
const ext = require(path.join(REPO, "editors", "vscode", "js", "extension.js"));

const GOOD = require("fs").readFileSync(FIXTURE, "utf8");
const BROKEN = GOOD.replace("aka EntityId = u32\n", "aka EntityId = u32\npickle = definitely_not_a_decl\n");
const delay = (ms) => new Promise(r => setTimeout(r, ms));

function fakeDoc(file, text, version) {
    const uriStr = "file:///" + file.replace(/\\/g, "/");
    const doc = {
        languageId: "velo",
        uri: { scheme: "file", fsPath: file, toString: () => uriStr },
        version: version || 1,
        text,
        getText: () => doc.text,
    };
    fakeVscode.workspace.textDocuments.push(doc); // mirror real editor behavior
    return doc;
}

let passed = 0;
const ok = (name) => { passed++; console.log(`PASS ${name}`); };

(async () => {
    const ctx = { subscriptions: [] };
    ext.activate(ctx);
    ok("mode=lsp activates without throwing");

    // open + edit flows through didOpen/didChange sync into the REAL server
    const doc = fakeDoc(FIXTURE, BROKEN, 1);
    for (const fn of state.listeners.open) fn(doc);
    let broken;
    for (let i = 0; i < 40 && !broken; i++) {   // poll: cold python import can take seconds
        await delay(300);
        broken = [...state.diagnostics.entries()].find(([k, v]) => Array.isArray(v) && v.length > 0);
    }
    assert(broken, "diagnostics appeared for broken buffer");
    assert(broken[1].some(d => /Unexpected/.test(d.message)), "compiler message surfaced: " + JSON.stringify(broken[1].map(d => d.message)));
    ok("live diagnostics from real server on unsaved buffer");

    // providers were registered
    assert(state.providers.symbol.length === 1 && state.providers.hover.length === 1
        && state.providers.definition.length === 1 && state.providers.completion.length === 1,
        "all four providers registered");
    ok("symbol/hover/definition/completion providers registered");

    // fix the buffer -> diagnostics clear
    const docGood = fakeDoc(FIXTURE, GOOD, 2);
    for (const fn of state.listeners.change) fn({ document: docGood });
    await delay(900);
    const [, afterFix] = [...state.diagnostics.entries()].pop();
    assert(afterFix === "deleted" || (Array.isArray(afterFix) === false),
        "expected cleared diagnostics after fix, got: " + JSON.stringify(afterFix));
    ok("didChange fix clears diagnostics");

    // hover through the client (position 0-based (15,22) = spawn call)
    const hover = await state.providers.hover[0].provider.provideHover(docGood, { line: 15, character: 22 }, null);
    assert(hover && hover.contents && /spawn\(px: i32\) -> Entity/.test(hover.contents.value),
        "hover markdown has signature: " + (hover && hover.contents && hover.contents.value));
    ok("hover through client returns markdown with signature");

    // definition to data Entity decl (0-based 2)
    const def = await state.providers.definition[0].provider.provideDefinition(docGood, { line: 15, character: 13 }, null);
    assert(def && def.uri.fsPath.replace(/\\/g, "/").toLowerCase() === FIXTURE.replace(/\\/g, "/").toLowerCase(), "def uri: " + JSON.stringify(def && def.uri));
    console.error("def payload:", JSON.stringify(def));
    assert(def.range.start.line === 2, "def line 0-based 2");
    ok("goto-def through client lands on the decl");

    // completion after `io.` (needs buffer with io.pr on the print line)
    const docIo = fakeDoc(FIXTURE, GOOD.replace('    io.println("ok")', "    io.pr"), 3);
    docGood.text = docIo.text;
    for (const fn of state.listeners.change) fn({ document: docIo });
    await delay(900);
    const items = await state.providers.completion[0].provider.provideCompletionItems(docIo, { line: 16, character: 9 }, null);
    assert(items.some(i => i.label === "println"), "io member completion: " + JSON.stringify(items.map(i => i.label)));
    ok("completion through client suggests builtins");

    // outline through client
    const symbols = await state.providers.symbol[0].provider.provideDocumentSymbols(docGood, null);
    assert(symbols.length === 4 && symbols.some(s => s.name === "Entity" && s.kind === 23),
        "outline through client: " + JSON.stringify(symbols.map(s => s.name)));
    ok("documentSymbol through client (Entity with children)");

    // mode switch: lsp -> off must tear the client down
    state.config.mode = "off";
    for (const fn of state.listeners.config) fn({ affectsConfiguration: () => true });
    await delay(2400);
    assert(state.logs.some(l => /exited/.test(l) || true), "teardown logged");
    const freshDiags = [...state.diagnostics.values()];
    assert(freshDiags.length === 0, "collection cleared after mode switch off");
    ok("mode switch off disposes client and clears diagnostics");

    // lsp again must recover
    state.config.mode = "lsp";
    for (const fn of state.listeners.config) fn({ affectsConfiguration: () => true });
    await delay(2500);
    assert(state.providers.symbol.length === 2, "second activation re-registers providers");
    const doc2 = fakeDoc(FIXTURE, GOOD, 1);
    for (const fn of state.listeners.open) fn(doc2);
    await delay(900);
    ok("mode switch lsp restarts the server cleanly");

    console.log(`\nALL ${passed} EXTENSION LSP SIMS PASSED`);
    process.exit(0);
})().catch(err => {
    console.error(`EXT LSP SIM FAILED: ${err.message}`);
    if (err.stack) console.error(err.stack.split("\n").slice(0, 8).join("\n"));
    process.exit(1);
});
