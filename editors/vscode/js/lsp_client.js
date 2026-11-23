// Minimal dependency-free LSP client transport for the Velo extension (Tier B).
//
// Spawns the bundled Python stdio server, speaks the standard
// `Content-Length`-framed JSON-RPC 2.0, correlates responses to requests, and
// streams notifications (publishDiagnostics) upward. Deliberately hand-rolled:
// the Tier A constraint of no npm dependencies stays true. All framing handles
// split/merged chunks as delivered by the child's stdout stream.

class LspClient {
    /**
     * @param {({
     *   pythonPath: string, serverPath: string, repoPath: string,
     *   cwd: string, log?: (line: string) => void, onExit?: () => void
     * })} options
     * @returns {Promise<LspClient>} initialized and ready client, or rejects.
     */
    static start(options) {
        const child_process = require("child_process");
        const cmd = options.command || options.pythonPath;
        const args = options.args || [options.serverPath, options.repoPath];
        const child = child_process.spawn(cmd, args, {
            stdio: ["pipe", "pipe", "pipe"],
            windowsHide: true,
            cwd: options.cwd || undefined,
            env: Object.assign({}, process.env, options.env || {
                PYTHONPATH: options.repoPath,
                VELO_LSP_REPO: options.repoPath,
            }),
        });

        const client = new LspClient(child, options);
        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => reject(new Error("LSP initialize timed out")), 20000);
            child.once("error", reject);
            child.once("exit", (code) => {
                clearTimeout(timer);
                reject(new Error(`LSP server exited during startup (code ${code})`));
            });
            client._readyWith = (initialResult) => {
                clearTimeout(timer);
                child.removeAllListeners("exit");
                child.on("exit", (code) => {
                    client.log(`server exited (code ${code})`);
                    if (client.onExit) client.onExit(code);
                });
                resolve(client);
            };
            client._initializeFor(options.cwd);
        });
    }

    constructor(child, options) {
        this.child = child;
        this.log = options.log || (() => {});
        this.onExit = options.onExit || null;
        this.onPublish = null;
        this.nextId = 1;
        this.pending = new Map(); // id -> {resolve, reject, timer}
        this.buffer = Buffer.alloc(0);
        this.disposed = false;

        child.stdout.on("data", (chunk) => this._feed(chunk));
        child.stderr.on("data", (chunk) => {
            const lines = chunk.toString().split(/\r?\n/);
            for (const line of lines) {
                if (line && line.includes("[velo-lsp]")) this.log(line);
            }
        });
    }

    _initializeFor(cwd) {
        this.request("initialize", {
            processId: process.pid,
            capabilities: {},
            rootUri: "file:///" + String(cwd).replace(/\\/g, "/"),
        }).then(result => {
            this.notify("initialized", {});
            if (this._readyWith) this._readyWith(result);
        }).catch(err => {
            this.log(`initialize failed: ${err && err.message}`);
            this.child.kill();
        });
    }

    _feed(chunk) {
        this.buffer = Buffer.concat([this.buffer, chunk]);
        while (true) {
            const headerEnd = this.buffer.indexOf("\r\n\r\n");
            if (headerEnd < 0) return;
            const header = this._head(headerEnd);
            const match = /Content-Length: (\d+)/i.exec(header);
            if (!match) {
                this.log("malformed LSP header from server; dropping");
                // resync: skip past the (mal)framed header
                const next = this.buffer.indexOf("\r\n\r\n", headerEnd + 4);
                if (next < 0) return;
                this.buffer = this.buffer.slice(next + 4);
                continue;
            }
            const length = parseInt(match[1], 10);
            if (this.buffer.length < headerEnd + 4 + length) return;
            const body = this.buffer.slice(headerEnd + 4, headerEnd + 4 + length).toString("utf8");
            this.buffer = this.buffer.slice(headerEnd + 4 + length);
            let message = null;
            try {
                message = JSON.parse(body);
            } catch (_) {
                this.log("unparseable LSP body from server; dropped");
                continue;
            }
            this._deliver(message);
        }
    }

    _head(headerEnd) {
        return this.buffer.slice(0, headerEnd).toString("ascii");
    }

    _deliver(message) {
        if (message.method === "textDocument/publishDiagnostics") {
            if (this.onPublish) this.onPublish(message.params);
            return;
        }
        if (message.id != null && message.method) {
            this.log(`server requested ${message.method}; unsupported (declined)`);
            this.notify(message.method + "Failed", { message: "unimplemented in velo extension client" });
            return;
        }
        const waiter = message.id != null ? this.pending.get(message.id) : null;
        if (!waiter) {
            return;
        }
        this.pending.delete(message.id);
        clearTimeout(waiter.timer);
        if (message.error) {
            waiter.reject(new Error(`LSP ${message.error.message} (code ${message.error.code})`));
        } else {
            waiter.resolve(message.result);
        }
    }

    request(method, params, timeoutMs = 15000) {
        if (this.disposed) return Promise.reject(new Error("LSP client disposed"));
        const id = this.nextId++;
        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                this.pending.delete(id);
                reject(new Error(`LSP ${method} timed out`));
            }, timeoutMs);
            this.pending.set(id, { resolve, reject, timer });
            this.send({ jsonrpc: "2.0", id, method, params });
        });
    }

    notify(method, params) {
        if (this.disposed) return;
        this.send({ jsonrpc: "2.0", method, params });
    }

    send(payload) {
        const body = Buffer.from(JSON.stringify(payload), "utf8");
        this.child.stdin.write(Buffer.concat([
            Buffer.from(`Content-Length: ${body.length}\r\n\r\n`, "ascii"),
            body,
        ]));
    }

    dispose() {
        if (this.disposed) return;
        this.disposed = true;
        try {
            this.notify("exit", {});
        } catch (_) { /* server may already be gone */ }
        const child = this.child;
        setTimeout(() => {
            try { child.kill(); } catch (_) { /* already gone */ }
        }, 1500);
        for (const { reject, timer } of this.pending.values()) {
            clearTimeout(timer);
            reject(new Error("LSP client disposed"));
        }
        this.pending.clear();
    }
}

module.exports = { LspClient };
