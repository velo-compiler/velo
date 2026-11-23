// Tier B end-to-end probe: drive the REAL python LSP server (spawn + JSON-RPC
// frames) through lifecycle, diagnostics, outline, hover, goto-def, completions.
"use strict";
const cp = require("child_process");
const path = require("path");

const REPO = path.resolve(__dirname, "..", "..", "..");
const SERVER = path.join(REPO, "editors", "vscode", "_server", "velo_lsp.py");

// fixture content (tests/fixtures/edge_lsp.vl, passed as a BUFFER overlay)
const LINES = [
    "use sys.io",
    "",
    "data Entity {",
    "    x: i32",
    "    y: i32 = 0",
    "}",
    "",
    "aka EntityId = u32",
    "",
    "act spawn(px: i32) -> Entity {",
    "    let e: Entity = Entity { x: px, y: 0 }",
    "    return e",
    "}",
    "",
    "act main() -> i32 {",
    "    let e: Entity = spawn(1)",
    "    io.println(\"ok\")",
    "    return 0",
    "}",
    "",
];
const GOOD = LINES.join("\n");
const BROKEN = GOOD.replace("aka EntityId = u32\n", "aka EntityId = u32\npickle = definitely_not_a_decl\n"); // TOP-LEVEL junk: parse error on BOTH compilers. (Note: indented junk inside an act body is parse-valid and the stages DIVERGE — Stage 1 ok:true, Stage 2 "Undeclared identifier"; gaps.md 6.7 (9))

const child = cp.spawn("python", [SERVER, REPO], {
    env: Object.assign({}, process.env, { PYTHONPATH: REPO }),
    stdio: ["pipe", "pipe", "pipe"],
});
let stderrBuf = "";
child.stderr.on("data", d => { stderrBuf += d.toString(); });

// -- framing -----------------------------------------------------------------
let rxBuffer = Buffer.alloc(0);
const waiters = [];         // {resolve, reject, timer, filter}
const published = [];       // publishDiagnostics notifications
const pendingRequests = new Map();
let nextId = 1;

child.stdout.on("data", chunk => {
    rxBuffer = Buffer.concat([rxBuffer, chunk]);
    while (true) {
        const headerEnd = rxBuffer.indexOf("\r\n\r\n");
        if (headerEnd < 0) break;
        const header = rxBuffer.slice(0, headerEnd).toString("ascii");
        const match = /Content-Length: (\d+)/i.exec(header);
        if (!match) { console.error("BAD HEADER", header); process.exit(1); }
        const length = parseInt(match[1], 10);
        if (rxBuffer.length < headerEnd + 4 + length) break;
        const body = rxBuffer.slice(headerEnd + 4, headerEnd + 4 + length);
        rxBuffer = rxBuffer.slice(headerEnd + 4 + length);
        const message = JSON.parse(body.toString("utf8"));
        if (process.env.LSP_DEBUG) console.error("[rx]", JSON.stringify(message).slice(0, 900));
        if (message.method === "textDocument/publishDiagnostics") {
            published.push(message.params);
            continue;
        }
        if (message.method) { console.error("unexpected server request:", message.method); continue; }
        const waiter = pendingRequests.get(message.id);
        if (waiter) {
            pendingRequests.delete(message.id);
            clearTimeout(waiter.timer);
            waiter.resolve(message);
        }
    }
});

function send(payload) {
    const body = Buffer.from(JSON.stringify(payload), "utf8");
    const frame = Buffer.concat([Buffer.from(`Content-Length: ${body.length}\r\n\r\n`, "ascii"), body]);
    child.stdin.write(frame);
}

function request(method, params) {
    const id = nextId++;
    return new Promise((resolve, reject) => {
        const timer = setTimeout(() => { pendingRequests.delete(id); reject(new Error(`timeout on ${method}`)); }, 20000);
        pendingRequests.set(id, { resolve, reject, timer });
        send({ jsonrpc: "2.0", id, method, params });
    });
}
const notify = (method, params) => send({ jsonrpc: "2.0", method, params });
const delay = ms => new Promise(r => setTimeout(r, ms));
const FIXTURE = path.join(__dirname, "fixtures", "edge_lsp.vl"); // must exist on disk: check() guards exists(); the overlay only swaps CONTENT
const URI = "file:///" + FIXTURE.replace(/\\/g, "/");

let passed = 0;
const ok = (name) => { passed++; console.log(`PASS ${name}`); };

(async () => {
    // 1. lifecycle
    const init = await request("initialize", { processId: null, capabilities: {} });
    if (!init.result.capabilities.hoverProvider) throw new Error("missing hover capability");
    ok("initialize reports capabilities");
    notify("initialized", {});
    notify("textDocument/didOpen", { textDocument: { uri: URI, languageId: "velo", version: 1, text: BROKEN } });
    await delay(500);
    const brokenPub = published.find(p => p.uri === URI && p.diagnostics.length > 0);
    if (!brokenPub) throw new Error(`no broken diagnostics; stderr=${stderrBuf}`);
    const d0 = brokenPub.diagnostics[0];
    if (!d0.message) throw new Error("empty message");
    ok(`didOpen(broken) publishes {line:${d0.range.start.line}} "${d0.message.slice(0, 40)}"`);

    // 2. didChange fix -> empty diagnostics
    notify("textDocument/didChange", {
        textDocument: { uri: URI, version: 2 },
        contentChanges: [{ text: GOOD }],
    });
    await delay(500);
    const goodPub = published.filter(p => p.uri === URI).slice(-1)[0];
    if (!goodPub || goodPub.diagnostics.length !== 0) throw new Error("fixed buffer still has diagnostics");
    ok("didChange(clean) clears diagnostics");

    // 3. outline
    const symbols = await request("textDocument/documentSymbol", { textDocument: { uri: URI } });
    if (symbols.result.length !== 4) throw new Error(`expected 4 top symbols, got ${symbols.result.length}`);
    const entity = symbols.result.find(s => s.name === "Entity");
    if (!entity || entity.kind !== 23) throw new Error("Entity struct symbol wrong");
    if (entity.children.length !== 2 || entity.children[0].name !== "x: i32") throw new Error("Entity children wrong");
    const mainAct = symbols.result.find(s => s.name.startsWith("main("));
    if (!mainAct || mainAct.kind !== 12) throw new Error("main act symbol wrong");
    const aka = symbols.result.find(s => s.name.startsWith("aka EntityId"));
    if (!aka) throw new Error("aka symbol missing");
    ok("documentSymbol outline (struct+fields, kind, aka, acts)");

    // 4. hover over `spawn` usage (L15 "    let e: Entity = spawn(1)", 'spawn' at char 20..26)
    const hoverReq = await request("textDocument/hover", { textDocument: { uri: URI }, position: { line: 15, character: 22 } });
    if (!hoverReq.result) throw new Error(`no hover at spawn; `);
    const hoverText = JSON.stringify(hoverReq.result.contents);
    if (!hoverText.includes("spawn(px: i32) -> Entity") || !hoverText.includes("edge_lsp.vl:10")) {
        throw new Error(`hover content wrong: ${hoverText}`);
    }
    ok("hover on act usage shows signature + origin");

    // 5. hover over local `e` (char 8..9 of same line)
    const hoverLocal = await request("textDocument/hover", { textDocument: { uri: URI }, position: { line: 15, character: 5 } });
    if (!hoverLocal.result) throw new Error("no hover on local");
    if (!JSON.stringify(hoverLocal.result.contents).includes("local **e**: Entity")) {
        throw new Error(`local hover wrong: ${JSON.stringify(hoverLocal.result.contents)}`);
    }
    ok("hover on local let shows type");

    // 6. goto-def on `Entity` in `let e: Entity` (L15 char 11..17 -> line 14/char 13)
    const defReq = await request("textDocument/definition", { textDocument: { uri: URI }, position: { line: 15, character: 13 } });
    if (!defReq.result || defReq.result.uri !== URI) throw new Error(`definition uri wrong`);
    if (defReq.result.range.start.line !== 2) throw new Error(`definition line wrong (want 0-based 2): ${JSON.stringify(defReq.result.range)}`);
    ok("definition from usage lands on data Entity decl (0-based line 2)");

    // 7. completion: member after `io.` on L16 (write "    io.pr" then complete after "pr")
    notify("textDocument/didChange", { textDocument: { uri: URI, version: 3 }, contentChanges: [{ text: GOOD.replace("    io.println(\"ok\")", "    io.pr") }] });
    await delay(300);
    published.splice(0, published.length); // ignore that diagnostic batch
    const compl = await request("textDocument/completion", { textDocument: { uri: URI }, position: { line: 16, character: 9 } });
    const labels = compl.result.map(i => i.label);
    if (!labels.includes("println")) throw new Error(`io. completions missing println: ${labels}`);
    ok("completion inside io.<caret> suggests builtin members");

    // 8. completion: word prefix on empty line inserts decl names
    notify("textDocument/didChange", { textDocument: { uri: URI, version: 4 }, contentChanges: [{ text: GOOD }] });
    await delay(300);
    published.splice(0, published.length);
    const compl2 = await request("textDocument/completion", { textDocument: { uri: URI }, position: { line: 13, character: 0 } });
    const labels2 = compl2.result.map(i => i.label);
    if (!labels2.includes("spawn")) throw new Error(`decl completions missing spawn: ${labels2.slice(0, 10)}...`);
    ok("completion word-completes declarations from the parse tree");

    // 9. lifecycle close
    notify("textDocument/didClose", { textDocument: { uri: URI } });
    await delay(300);
    const lastPub = published.slice(-1)[0];
    if (!lastPub || lastPub.diagnostics.length !== 0) throw new Error("didClose did not clear diagnostics");
    ok("didClose publishes empty diagnostics");
    await request("shutdown", {});
    notify("exit", {});
    const code = await new Promise((resolve, reject) => {
        const t = setTimeout(() => reject(new Error("server did not exit")), 10000);
        child.on("exit", c => { clearTimeout(t); resolve(c); });
    });
    if (code !== 0) throw new Error(`server exit code ${code}`);
    ok("shutdown/exit round-trips cleanly");

    console.log(`\nALL ${passed} SERVER PROBES PASSED`);
    child.kill();
    process.exit(0);
})().catch(err => {
    console.error(`LSP PROBE FAILED: ${err.message}`);
    console.error("server stderr:", stderrBuf);
    child.kill();
    process.exit(1);
});
