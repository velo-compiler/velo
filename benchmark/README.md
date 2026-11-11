# ⚡ Velo 2.0 vs. Node.js (v24) HTTP Server Benchmark

This directory contains an apples-to-apples, reproducible performance benchmark comparing the **Velo Asynchronous HTTP Server (`std.async` + `std.http`)** against **Node.js (`node:http`)**.

---

## 📁 Directory Structure

| File | Description |
| :--- | :--- |
| [`server_velo.vl`](file:///c:/projects/easylang/benchmark/server_velo.vl) | High-performance Velo async HTTP server running on `127.0.0.1:8080` |
| [`server_velo.exe`](file:///c:/projects/easylang/benchmark/server_velo.exe) | Compiled standalone native executable |
| [`server_node.js`](file:///c:/projects/easylang/benchmark/server_node.js) | Equivalent native Node.js HTTP server running on `127.0.0.1:8081` |
| [`run_benchmark.py`](file:///c:/projects/easylang/benchmark/run_benchmark.py) | Automated test harness measuring Throughput (RPS), Latencies, and Working Set RAM |
| [`BENCHMARK_RESULTS.md`](file:///c:/projects/easylang/benchmark/BENCHMARK_RESULTS.md) | Auto-generated Markdown report from the latest run |

---

## 🚀 How to Run the Benchmark

### 1. Automated Suite (Python Standard Library)

No third-party packages required (uses Windows native `psapi.dll` for byte-accurate RAM measurement):

```powershell
python benchmark/run_benchmark.py
```

This will automatically:
1. Compile and launch `server_velo.exe` on port 8080.
2. Launch `server_node.js` on port 8081.
3. Warm up both servers with 100 requests.
4. Execute concurrent load tests across `/plaintext` and `/json` endpoints.
5. Print the comparison table and save [`BENCHMARK_RESULTS.md`](file:///c:/projects/easylang/benchmark/BENCHMARK_RESULTS.md).
6. Cleanly terminate all background server processes.

---

### 2. Manual Testing with Autocannon (Industry Standard)

If you have `npx` installed, you can benchmark each server interactively:

```powershell
# In Terminal 1 (Start Velo):
.\benchmark\server_velo.exe

# In Terminal 2 (Start Node.js):
node .\benchmark\server_node.js

# In Terminal 3 (Run autocannon against Velo):
npx autocannon -c 20 -d 5 http://127.0.0.1:8080/plaintext

# In Terminal 3 (Run autocannon against Node.js):
npx autocannon -c 20 -d 5 http://127.0.0.1:8081/plaintext
```

---

## 📊 Summary of Benchmark Findings

| Characteristic | Velo 2.0 (`std.async`) | Node.js (v24) | Analysis |
| :--- | :---: | :---: | :--- |
| **Startup RAM** | **~4.3 MB** | ~36.5 MB | 🏆 **Velo uses 8.5x less memory** at startup |
| **Peak RAM (Load)** | **~5 – 9 MB** | ~50 – 68 MB | 🏆 **Velo stays under 10 MB** under heavy concurrency |
| **Deployment Size** | **~180 KB** binary | Node Runtime (~80 MB) | 🏆 Zero runtime dependencies or node_modules |
| **Throughput** | **1,100 – 2,750 req/s** | 4,200 – 5,500 req/s | Node.js benefits from 15+ years of C++ `libuv` and `llhttp` optimizations |
| **Cold Startup Time** | **< 10 ms** | ~150 – 300 ms | Instant native execution |

