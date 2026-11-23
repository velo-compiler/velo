# 🚀 Velo 2.0 Multi-Language Benchmark Suite

This directory contains an automated, reproducible benchmark suite comparing **Velo 2.0** against peer systems languages and runtimes:
- **C** (GCC 16.1 `-O3`)
- **Rust** (`rustc -O`)
- **Go** (`go build`)
- **Node.js** (`node` v24)

All peer implementations execute the exact same workloads with verified identical output.

---

## 📊 Workloads

1. **HTTP Server (`/plaintext` and `/json`)**:
   - Evaluates async / event loop socket handling, concurrency under load, request throughput (req/s), latency percentiles (min, avg, p50, p95, p99, max), and memory footprint (baseline and peak RSS).
   - Endpoints:
     - `/plaintext`: returns `200 OK` with `Hello, World!`
     - `/json`: returns `200 OK` with `{"message":"Hello, World!","status":"ok"}`

2. **JSON Parsing & Aggregation**:
   - Parses a 10-record structured JSON array repeatedly (default: 5,000 iterations).
   - Filters records where `active == true`, accumulates age and array score fields.
   - Output parity verification across all implementations: `Done 5000 iterations: active=35000, age=1170000, score=3110000`.

3. **Large File Scanning & Word Count**:
   - Reads and scans `bootstrap.c` (~3.25 MB, 76,000+ lines).
   - Counts lines (`\n`), whitespace-separated words, and total bytes.
   - Output parity verification across all implementations: `Scanned: lines=76931, words=285222, bytes=3259543`.

---

## 📁 Source Files

| Workload | Velo | C | Rust | Go | Node.js |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **HTTP Server** | [`server_velo.vl`](file:///c:/projects/easylang/benchmark/server_velo.vl) | [`server_c.c`](file:///c:/projects/easylang/benchmark/server_c.c) | [`server_rust.rs`](file:///c:/projects/easylang/benchmark/server_rust.rs) | [`server_go.go`](file:///c:/projects/easylang/benchmark/server_go.go) | [`server_node.js`](file:///c:/projects/easylang/benchmark/server_node.js) |
| **JSON Parse** | [`json_velo.vl`](file:///c:/projects/easylang/benchmark/json_velo.vl) | [`json_c.c`](file:///c:/projects/easylang/benchmark/json_c.c) | [`json_rust.rs`](file:///c:/projects/easylang/benchmark/json_rust.rs) | [`json_go.go`](file:///c:/projects/easylang/benchmark/json_go.go) | [`json_node.js`](file:///c:/projects/easylang/benchmark/json_node.js) |
| **File Scan** | [`filescan_velo.vl`](file:///c:/projects/easylang/benchmark/filescan_velo.vl) | [`filescan_c.c`](file:///c:/projects/easylang/benchmark/filescan_c.c) | [`filescan_rust.rs`](file:///c:/projects/easylang/benchmark/filescan_rust.rs) | [`filescan_go.go`](file:///c:/projects/easylang/benchmark/filescan_go.go) | [`filescan_node.js`](file:///c:/projects/easylang/benchmark/filescan_node.js) |

---

## 🏃 Running the Benchmarks

The benchmark runner is fully automated and uses Python's standard library:

```powershell
# Full benchmark run across all workloads and languages:
python benchmark/run_benchmark.py

# Quick mode (reduced iterations for rapid verification / CI):
python benchmark/run_benchmark.py --quick

# Skip build step if binaries are already compiled:
python benchmark/run_benchmark.py --skip-build

# Compute-only benchmarks (skip HTTP servers):
python benchmark/run_benchmark.py --skip-http
```

### 📄 Output

The runner compiles all targets, executes the suite, prints real-time metrics to stdout, and auto-generates:
- [`benchmark/RESULTS.md`](file:///c:/projects/easylang/benchmark/RESULTS.md)

The generated report includes complete host machine specifications (OS, CPU model and core count, total RAM) and exact toolchain versions for Velo, GCC, rustc, go, and node.
