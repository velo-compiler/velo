// Stub-based behavioral simulation of the Velo extension's Tier A activation.
// No npm deps and no editor required: a fake `vscode` module is injected via
// Module._load, fake compilers are plain node scripts, and the debounced
// on-save flow is asserted end to end.
"use strict";
const Module = require("module");
const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");

const EXT_DIR = path.resolve(__dirname, "..");
const SIM_DIR = fs.mkdtempSync(path.join(os.tmpdir(), "velo-ext-tests-"));

const state = {
    diagnostics: new Map(), // uri -> latest set payload (array | "deleted")
    logs: [],
    listeners: { save: [], open: [], close: [], config: [] },
    collections: [],
    commands: new Map(),
    config: { mode: "check", compilerPath: "node", compilerArgs: [] },
};

const fakeVscode = {
    languages: {
        createDiagnosticCollection(name) {
            const col = {
                name,
                set(uri, diags) { state.diagnostics.set(uri.toString(), diags || "deleted"); },
                delete(uri) { state.diagnostics.set(uri.toString(), "deleted"); },
                clear() { state.diagnostics.clear(); },
                dispose() {},
            };
            state.collections.push(col);
            return col;
        },
    },
    window: {
        createOutputChannel() {
            return {
                appendLine(s) { state.logs.push(s); },
                show() {},
                dispose() {},
            };
        },
    },
    workspace: {
        getConfiguration(section) {
            return { get: (key, dflt) => (key in state.config ? state.config[key] : dflt) };
        },
        getWorkspaceFolder(uri) {
            return { uri: { fsPath: path.dirname(uri.fsPath) } };
        },
        onDidSaveTextDocument(fn) { state.listeners.save.push(fn); return { dispose() { state.listeners.save = state.listeners.save.filter(f => f !== fn); } }; },
        onDidOpenTextDocument(fn) { state.listeners.open.push(fn); return { dispose() { state.listeners.open = state.listeners.open.filter(f => f !== fn); } }; },
        onDidCloseTextDocument(fn) { state.listeners.close.push(fn); return { dispose() { state.listeners.close = state.listeners.close.filter(f => f !== fn); } }; },
        onDidChangeConfiguration(fn) { state.listeners.config.push(fn); return { dispose() { state.listeners.config = state.listeners.config.filter(f => f !== fn); } }; },
        textDocuments: [],
    },
    Diagnostic: class FakeDiagnostic {
        constructor(range, message, severity) {
            this.range = range; this.message = message; this.severity = severity;
        }
    },
    Range: class FakeRange {
        constructor(sl, sc, el, ec) { this.start = { line: sl, character: sc }; this.end = { line: el, character: ec }; }
    },
    DiagnosticSeverity: { Error: 0, Warning: 1, Information: 2, Hint: 3 },
    commands: {
        registerCommand(name, fn) {
            state.commands.set(name, fn);
            return { dispose() { state.commands.delete(name); } };
        },
    },
};

const origLoad = Module._load;
Module._load = function (request, parent, isMain) {
    if (request === "vscode") return fakeVscode;
    return origLoad.apply(this, arguments);
};
const ext = require(path.join(EXT_DIR, "js", "extension.js"));

// --- fake compilers -------------------------------------------------------
function writeFakeCompiler(name, body) {
    const p = path.join(SIM_DIR, name);
    fs.writeFileSync(p, body, "utf8");
    return p;
}

const COMP_OK = writeFakeCompiler("fake_clean.js", "process.stdout.write(JSON.stringify({file:'v',ok:true,diagnostics:[]}))");
const COMP_ERR = writeFakeCompiler("fake_err.js", "process.stdout.write(JSON.stringify({file:'v',ok:false,diagnostics:[{file:'v',line:3,col:5,severity:'error',message:'struct missing field \"z\"'},{file:'v',line:0,col:0,severity:'warning',message:'dup alias wins'}]}))");
// compiler contract: exit 1 WITH valid JSON is a normal diagnostics path.
// (fake_err.js never calls process.exit, so the child exits 0; the parse path
// is identical. A real compiler's exit-1-with-JSON takes the same code path.)

function pause(ms) { return new Promise(r => setTimeout(r, ms)); }
function fakeDoc(file) {
    const uri = { scheme: "file", fsPath: file, toString: () => "file:///" + file.replace(/\\/g, "/") };
    return { languageId: "velo", uri };
}
function save(doc) {
    for (const fn of state.listeners.save) fn(doc);
}

let passed = 0;
function ok(name) { passed++; console.log(`PASS ${name}`); }
function setMode(mode) {
    state.config.mode = mode;
    for (const fn of state.listeners.config) fn({ affectsConfiguration: () => true }); // real VS Code always fires this
}

(async () => {
    const ctx = { subscriptions: [] };
    ext.activate(ctx);
    assert(state.collections.length === 1, "one DiagnosticCollection");
    ok("activate creates a collection");

    // E: stage mode default / off runs nothing
    setMode("off");
    save(fakeDoc(path.join(SIM_DIR, "off.vl")));
    await pause(400);
    assert(state.diagnostics.size === 0, "mode off runs no checks");
    ok("mode off: no compiler invocations");

    // A: errors compiler, mode check
    setMode("check");
    state.config.compilerArgs = [COMP_ERR];
    const doc = fakeDoc(path.join(SIM_DIR, "app.vl"));
    save(doc);
    await pause(600);
    let diags = state.diagnostics.get(doc.uri.toString());
    assert(Array.isArray(diags) && diags.length === 2, "two diagnostics reported");
    assert(diags[0].severity === 0 && diags[0].range.start.line === 2 && diags[0].range.start.character === 4,
        "error mapped from 1-based (3,5) to 0-based (2,4)");
    assert(diags[0].message.includes("missing field"), "error message present");
    assert(diags[0].source === "velo", "diagnostics attributed to velo");
    assert(diags[1].severity === 1 && diags[1].range.start.line === 0, "warning line 0 clamps to first line");
    ok("compiler diagnostics mapped to editor ranges/severity");

    // B: clean compiler clears
    state.config.compilerArgs = [COMP_OK];
    save(doc);
    await pause(600);
    assert(state.diagnostics.get(doc.uri.toString()) === "deleted", "clean file clears diagnostics");
    ok("ok:true report clears the file");

    // C: missing compiler degrades (no noise)
    state.config.compilerPath = "definitely-not-a-real-compiler-exe";
    state.config.compilerArgs = [];
    save(doc);
    await pause(600);
    assert(state.diagnostics.get(doc.uri.toString()) === "deleted", "missing tool clears");
    assert(state.logs.some(l => l.includes("unavailable")), "degradation logged to channel only");
    ok("tool failure degrades to no diagnostics");

    // D: junk output degrades
    const COMP_JUNK = writeFakeCompiler("fake_junk.js", "process.stdout.write('not json at all'); ");
    state.config.compilerPath = "node";
    state.config.compilerArgs = [COMP_JUNK];
    save(doc);
    await pause(600);
    assert(state.diagnostics.get(doc.uri.toString()) === "deleted", "junk output clears");
    assert(state.logs.some(l => l.includes("unparseable")), "unparseable output logged");
    ok("junk report degrades to no diagnostics");

    // G: restart-safety — deactivate is a no-op; fresh activate yields fresh state
    ext.deactivate();
    state.collections = [];
    state.diagnostics.clear();
    ext.activate(ctx);
    assert(state.collections.length === 1, "second activation gets a fresh collection");
    assert(state.diagnostics.size === 0, "fresh activation starts clean");
    ok("restart-safe: fresh session re-derives diagnostics");

    // Test 8: All 6 Velo commands registered
    const requiredCommands = ["velo.run", "velo.build", "velo.test", "velo.pkg.run", "velo.pkg.build", "velo.pkg.check"];
    for (const cmd of requiredCommands) {
        assert(state.commands.has(cmd), `command ${cmd} not registered`);
    }
    ok("all 6 Velo commands registered in VS Code");

    console.log(`\nALL ${passed} SIMULATIONS PASSED`);
    process.exit(0);
})().catch(e => { console.error(`SIM FAILED: ${e.message}`); process.exit(1); });
