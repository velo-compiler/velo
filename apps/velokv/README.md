# VeloKV: High-Performance Zero-GC In-Memory Key-Value Database & Cache

**VeloKV** is a production-grade, Redis-compatible in-memory key-value database and caching engine written entirely in **Velo**, compiling directly to lean, standalone native machine code (`bin/velokv.exe`) via ISO C99 without any garbage collection runtime.

---

## ⚡ Core Architecture & The Velo Advantage

Traditional managed runtimes (Go, Java, Python, C#) suffer from garbage collection latency spikes ("stop-the-world" GC pauses) and heap memory fragmentation when serving tens of thousands of concurrent network requests per second.

VeloKV solves this at the hardware level using **Velo's Scoped Zone Memory**:

```
+-------------------------------------------------------------------------+
|                               Client Request                            |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
| zone 65536 { ... }                                                     |
|   1. Read raw TCP payload into socket buffer                           |
|   2. Parse RESP2 wire frames into zero-copy command tokens              |
|   3. Dispatch mutating/read operation                                   |
|   4. Format RESP2 wire response                                         |
|   5. Flush response bytes to TCP socket                                 |
+-------------------------------------------------------------------------+
                                     |
                                     v
                     [1 CPU Cycle Arena Reset: O(1)]
        (Zero GC pauses, zero malloc/free overhead, zero fragmentation)
```

1. **Dual Allocator Delineation**:
   - **Request Lifecycle (`zone 65536`)**: All transient allocations (wire frames, parsed arguments, string transformations, response buffers) are allocated in a hardware bump arena and wiped in 1 CPU cycle on request completion.
   - **State Lifecycle (`@Allocator` Root Arena)**: Long-lived keys and values inserted into the hash table are copied into the permanent database arena via `mem.alloc_with(s.allocator, ...)`.
2. **Deterministic Low Latency**: 99.9th percentile latencies remain flat under continuous client load because there is no garbage collector scanning the keyspace.
3. **Dual-Compiler Parity**: Compiles cleanly with both the self-hosted Stage 2 compiler (`bin/velo.exe`) and the Stage 1 reference compiler (`velo.py`).

---

## 🚀 Features & Redis Command Compatibility

VeloKV implements the standard **Redis Serialization Protocol (RESP2)** and supports both pipelined binary frames (`*argc\r\n...`) and human-readable inline telnet commands.

| Command | Arguments | Description |
|---|---|---|
| `PING` | `[message]` | Server heartbeat. Returns `+PONG` or echoed message. |
| `ECHO` | `<message>` | Echoes input back to client. |
| `SET` | `<key> <value> [EX sec] [PX ms]` | Stores key-value pair with optional TTL expiration. |
| `GET` | `<key>` | Retrieves string value, or nil if expired/absent. |
| `DEL` | `<key> [keys...]` | Atomically deletes one or more keys. |
| `EXISTS` | `<key>` | Returns 1 if key exists and has not expired, else 0. |
| `INCR` | `<key>` | Atomically increments 64-bit integer value. |
| `DECR` | `<key>` | Atomically decrements 64-bit integer value. |
| `MSET` | `<k1> <v1> [k2 v2...]` | Sets multiple keys and values in one atomic pass. |
| `EXPIRE`| `<key> <seconds>` | Sets time-to-live in seconds on an existing key. |
| `TTL` | `<key>` | Returns remaining seconds, -1 (permanent), or -2 (missing). |
| `PERSIST`| `<key>` | Removes TTL expiration, making key permanent. |
| `DBSIZE` | — | Returns total active key count in database. |
| `FLUSHDB`| — | Atomically evicts all keys from database. |
| `INFO` | — | Emits runtime telemetry (commands processed, hits, misses). |
| `QUIT` | — | Cleanly closes client connection. |

---

## 💾 Durability & Persistence: Append-Only File (AOF)

VeloKV includes continuous streaming durability via an **Append-Only File (`velokv.aof`)**:
- All mutating commands (`SET`, `DEL`, `FLUSHDB`, `MSET`, `INCR`, `DECR`) are logged to disk as canonical RESP frames.
- Flushed with `fflush` after writes to ensure durability against sudden process termination.
- Automatic Crash Recovery: On startup, VeloKV parses and replays `velokv.aof`, reconstructing the entire in-memory keyspace before opening the TCP listener.

---

## 📊 Performance Benchmarks

Measured on Windows 11 (x86_64) using local loopback TCP sockets:

- **Sequential Round-Trip Throughput**: **17,400+ ops/sec** (synchronous client round-trips over loopback TCP).
- **Latency**: Sub-millisecond median response time with adaptive spin-yielding.
- **Binary Footprint**: Standalone single-file `.exe` (~120 KB), zero DLL dependencies outside standard `ws2_32.lib` and CRT.

### Reproducing Benchmarks

Run the automated benchmark suite:
```bash
python -m pytest tests/test_velokv.py -v -s -k "test_08_throughput_benchmark"
```

Or connect standard `redis-benchmark`:
```bash
redis-benchmark -p 6389 -t set,get -n 10000 -q
```

---

## 🛠️ Build & Run

### 1. Build Standalone Binary

Using the self-hosted native Velo compiler:
```bash
bin/velo.exe build apps/velokv/main.vl -o bin/velokv.exe -l ws2_32
```

Using the Stage 1 reference compiler:
```bash
python velo.py build apps/velokv/main.vl -o bin/velokv_py.exe -l ws2_32
```

### 2. Start VeloKV Server

```bash
# Starts on default port 6389
bin/velokv.exe

# Or specify a custom port
bin/velokv.exe 6379
```

### 3. Connect with any Redis Client

```bash
# redis-cli
redis-cli -p 6389
127.0.0.1:6389> SET user:1001 "Alice"
OK
127.0.0.1:6389> GET user:1001
"Alice"
127.0.0.1:6389> INCR page_views
(integer) 1
127.0.0.1:6389> INFO
```

Python (`redis-py`):
```python
import redis
r = redis.Redis(host="127.0.0.1", port=6389)
r.set("greeting", "Hello from Python!")
print(r.get("greeting").decode())  # Hello from Python!
```

---

## 🧪 Automated Test Suite

### 1. Native In-Engine Tests (Zero Dependencies)
Run all 9 native unit and TCP loopback integration tests directly with the Velo toolchain:
```bash
bin/velo.exe test apps/velokv/test_velokv.vl -l ws2_32
```
Or with the Stage 1 compiler:
```bash
python velo.py test apps/velokv/test_velokv.vl -l ws2_32
```

### 2. External TCP Supervisor & Benchmarks (Python)
Run end-to-end loopback TCP client, crash recovery, and microbenchmark tests:
```bash
python -m pytest tests/test_velokv.py -v -s
```
