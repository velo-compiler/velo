// benchmark/json_node.js — JSON parsing and aggregation benchmark in Node.js
const process = require('node:process');

function runJsonBenchmark(payload, iterations) {
    let totalActive = 0;
    let totalAge = 0;
    let totalScore = 0;

    for (let it = 0; it < iterations; it++) {
        const doc = JSON.parse(payload);
        if (Array.isArray(doc)) {
            for (let i = 0; i < doc.length; i++) {
                const item = doc[i];
                if (item && item.active === true) {
                    totalActive++;
                    totalAge += (item.age || 0);
                    if (Array.isArray(item.scores) && item.scores.length > 0) {
                        totalScore += (item.scores[0] || 0);
                    }
                }
            }
        }
    }

    console.log(`Done ${iterations} iterations: active=${totalActive}, age=${totalAge}, score=${totalScore}`);
}

const payload = '[{"id":1,"name":"Alice","age":28,"active":true,"scores":[85,92,78]},{"id":2,"name":"Bob","age":34,"active":false,"scores":[70,75,80]},{"id":3,"name":"Charlie","age":22,"active":true,"scores":[95,98,91]},{"id":4,"name":"Diana","age":41,"active":true,"scores":[88,84,90]},{"id":5,"name":"Evan","age":29,"active":false,"scores":[65,72,68]},{"id":6,"name":"Fiona","age":31,"active":true,"scores":[92,89,94]},{"id":7,"name":"George","age":50,"active":true,"scores":[79,83,85]},{"id":8,"name":"Hannah","age":26,"active":false,"scores":[81,77,86]},{"id":9,"name":"Ian","age":38,"active":true,"scores":[87,91,89]},{"id":10,"name":"Julia","age":24,"active":true,"scores":[96,94,99]}]';

const iters = process.argv[2] ? parseInt(process.argv[2], 10) : 5000;
runJsonBenchmark(payload, iters);
