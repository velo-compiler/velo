# 🏁 Velo vs. Node.js HTTP Server Benchmark Results

- **Velo Baseline RAM**: `4.59 MB`
- **Node.js Baseline RAM**: `36.55 MB` (Velo uses ~**8.0x less RAM**)

| Benchmark Scenario | Metric | Velo 2.0 | Node.js v24 | Winner |
| :--- | :--- | :---: | :---: | :---: |
| **Plaintext (/plaintext)** | **Throughput** | **6,576.6 req/s** | 4,310.2 req/s | 🏆 Velo |
| | Avg Latency | 2.82 ms | 4.40 ms | 🏆 Velo |
| | p95 Latency | 5.15 ms | 7.19 ms | 🏆 Velo |
| | Working Set RAM | **5.23 MB** | 50.10 MB | 🏆 Velo (9.6x less) |
| **JSON REST (/json)** | **Throughput** | **7,865.9 req/s** | 5,787.2 req/s | 🏆 Velo |
| | Avg Latency | 2.15 ms | 3.19 ms | 🏆 Velo |
| | p95 Latency | 3.01 ms | 4.27 ms | 🏆 Velo |
| | Working Set RAM | **5.74 MB** | 53.87 MB | 🏆 Velo (9.4x less) |
| **High Concurrency (/plaintext)** | **Throughput** | **7,242.0 req/s** | 4,778.6 req/s | 🏆 Velo |
| | Avg Latency | 6.11 ms | 9.78 ms | 🏆 Velo |
| | p95 Latency | 9.21 ms | 15.10 ms | 🏆 Velo |
| | Working Set RAM | **6.87 MB** | 61.85 MB | 🏆 Velo (9.0x less) |
| **High Concurrency (/json)** | **Throughput** | **6,269.8 req/s** | 5,565.8 req/s | 🏆 Velo |
| | Avg Latency | 7.35 ms | 8.20 ms | 🏆 Velo |
| | p95 Latency | 15.23 ms | 11.82 ms | Node.js |
| | Working Set RAM | **7.88 MB** | 63.67 MB | 🏆 Velo (8.1x less) |
