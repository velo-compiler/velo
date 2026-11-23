// Tier A acceptance probe: the extension plumbing driven by the REAL compilers.
// mode=check + a known-broken .vl fixture must yield editor diagnostics carrying
// the compiler's message and the right 0-based range, for both Stage 1
// (python velo.py) and Stage 2 (bin/velo.exe). No GUI: same vscode stub.
"use strict";
const Module = require("module");
const assert = require("assert");
const path = require("path");

const state = {
    diagnostics: new Map(),
    logs: [],
    listeners: { save: [], open: [], close: [], config: [] },
    collections: [],
    config: { mode: "check", compilerPath: "velo", compilerArgs: [] },
};

const fakeVscode = {
    languages: {
        createDiagnosticCollection() {
            const col = {
                set(uri, diags) { state.diagnostics.set(uri.toString(), diags || "deleted"); },
                delete(uri) { state.diagnostics.set(uri.toString(), "deleted"); },
                clear() { state.diagnostics.clear(); },
                dispose() {},
            };
            state.collections.push(col);
            return col;
        },
    },
    window: { createOutputChannel() { return { appendLine(s) { state.logs.push(s); }, show() {}, dispose() {} }; } },
    workspace: {
        getConfiguration() { return { get: (k, d) => (k in state.config ? state.config[k] : d) }; },
        getWorkspaceFolder() { return null; }, // cwd falls back to the file's directory
        onDidSaveTextDocument(fn) { state.listeners.save.push(fn); },
        onDidOpenTextDocument(fn) { state.listeners.open.push(fn); },
        onDidCloseTextDocument(fn) { state.listeners.close.push(fn); },
        onDidChangeConfiguration(fn) { state.listeners.config.push(fn); },
        textDocuments: [],
    },
    Diagnostic: class D { constructor(r, m, s) { this.range = r; this.message = m; this.severity = s; } },
    Range: class R { constructor(a, b, c, d) { this.start = { line: a, character: b }; this.end = { line: c, character: d }; } },
    DiagnosticSeverity: { Error: 0, Warning: 1, Information: 2, Hint: 3 },
};

const origLoad = Module._load;
Module._load = function (request, parent, isMain) {
    if (request === "vscode") return fakeVscode;
    return origLoad.apply(this, arguments);
};

// Instrument the real child_process so probe failures expose raw compiler IO.
const cpReal = require("child_process");
const origExecFile = cpReal.execFile;
cpReal.execFile = function (cmd, args, opts, cb) {
    return origExecFile.call(cpReal, cmd, args, opts, (err, stdout, stderr) => {
        console.error(`[exec] cmd=${cmd} args=${JSON.stringify(args)} errCode=${err && err.code} stdoutLen=${stdout.length} stderrLen=${stderr.length}`);
        if (stdout.length < 200) console.error(`[exec] stdout=${JSON.stringify(stdout)}`);
        cb.call(this, err, stdout, stderr);
    });
};
const ext = require(path.join(path.resolve(__dirname, ".."), "js", "extension.js"));

const pause = (ms) => new Promise(r => setTimeout(r, ms));
const fakeDoc = (file) => {
    const uri = { scheme: "file", fsPath: file, toString: () => "file:///" + file.replace(/\\/g, "/") };
    return { languageId: "velo", uri };
};

(async () => {
    const broken = path.join(__dirname, "fixtures", "edge_parse_broken.vl");
    const ctx = { subscriptions: [] };
    ext.activate(ctx);
    const save = (doc) => { for (const fn of state.listeners.save) fn(doc); };

    // Stage 2 first: canonical native binary.
    state.config.compilerPath = path.resolve(__dirname, "..", "..", "..", "bin", "velo.exe");
    state.config.compilerArgs = [];
    const doc2 = fakeDoc(broken);
    save(doc2);
    await pause(1500);
    let diags = state.diagnostics.get(doc2.uri.toString());
    assert(Array.isArray(diags) && diags.length >= 1, "native compiler produced diagnostics");
    assert(diags[0].range.start.line === 2 && diags[0].range.start.character === 0, "native first diag at 0-based (2,0)");
    assert(diags[0].message.includes("Unexpected top-level token"), "native message surfaced");
    assert(diags[0].source === "velo", "attributed to velo");
    console.log("PASS Stage 2 (bin/velo.exe) broken file -> diagnostics at (2,0)");

    // Stage 1 next: python velo.py from an arbitrary cwd.
    state.config.compilerPath = "python";
    state.config.compilerArgs = [path.resolve(__dirname, "..", "..", "..", "velo.py")];
    const doc1 = fakeDoc(broken);
    save(doc1);
    await pause(1500);
    diags = state.diagnostics.get(doc1.uri.toString());
    assert(Array.isArray(diags) && diags.length === 1, "stage1 compiler produced 1 diagnostic (fail-fast)");
    assert(diags[0].range.start.line === 2, "stage1 first diag line 2 (0-based)");
    assert(diags[0].message.includes("Unexpected top-level token"), "stage1 message surfaced");
    console.log("PASS Stage 1 (python velo.py) broken file -> diagnostics at (2,0)");

    // Clean file through the real pipeline must clear (not noise).
    const clean = path.join(__dirname, "fixtures", "edge_valid.vl");
    const docC = fakeDoc(clean);
    state.config.compilerArgs = [];
    save(docC);
    await pause(1500);
    const got = state.diagnostics.get(docC.uri.toString());
    assert(got === "deleted", "clean file stays clean");
    console.log("PASS clean file -> cleared, no noise");

    console.log("\nALL REAL-COMPILER PROBES PASSED");
    process.exit(0);
})().catch(e => { console.error(`REAL PROBE FAILED: ${e.message}`); console.error(state.logs.join("\n")); process.exit(1); });
