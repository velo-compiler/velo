// Node.js HTTP Benchmark Server (Equivalent to server_velo.vl)
const http = require('node:http');

const PORT = parseInt(process.env.PORT || process.argv[2] || '8080', 10);
const HOST = '127.0.0.1';

const server = http.createServer((req, res) => {
    // Parity with Velo: Connection close per request
    res.setHeader('Connection', 'close');

    if (req.url === '/plaintext') {
        res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
        res.end('Hello, World!');
    } else if (req.url === '/json') {
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end('{"message":"Hello, World!","status":"ok"}');
    } else {
        res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
        res.end('Not Found');
    }
});

server.listen(PORT, HOST, () => {
    console.log(`[Node.js] Server listening on http://${HOST}:${PORT}`);
});

