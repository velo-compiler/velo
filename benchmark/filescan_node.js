// benchmark/filescan_node.js — File scanning & word count benchmark in Node.js
const fs = require('node:fs');
const process = require('node:process');

function scanFile(path) {
    const buffer = fs.readFileSync(path);
    const len = buffer.length;
    let lines = 0;
    let words = 0;
    let inWord = false;

    for (let i = 0; i < len; i++) {
        const b = buffer[i];
        if (b === 10) { // '\n'
            lines++;
        }
        if (b === 32 || b === 9 || b === 10 || b === 13) { // ' ', '\t', '\n', '\r'
            inWord = false;
        } else if (!inWord) {
            inWord = true;
            words++;
        }
    }

    console.log(`Scanned: lines=${lines}, words=${words}, bytes=${len}`);
}

const target = process.argv[2] && process.argv[2].length > 0 ? process.argv[2] : 'bootstrap.c';
try {
    scanFile(target);
} catch (err) {
    console.error(`[Node Error] ${err.message}`);
    process.exit(1);
}
