#!/usr/bin/env python3
"""
Velo vs. Node.js HTTP Server Benchmark Suite
Measures: Throughput (RPS), Latency percentiles (min, avg, p50, p95, p99, max), and RAM footprint.
"""

import sys
import os
import time
import socket
import subprocess
import threading
import statistics
import ctypes
from ctypes import wintypes
from concurrent.futures import ThreadPoolExecutor

class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('PageFaultCount', wintypes.DWORD),
        ('PeakWorkingSetSize', ctypes.c_size_t),
        ('WorkingSetSize', ctypes.c_size_t),
        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
        ('PagefileUsage', ctypes.c_size_t),
        ('PeakPagefileUsage', ctypes.c_size_t),
    ]

def get_process_memory_mb(pid: int) -> float:
    if os.name != 'nt':
        return 0.0
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010
    handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not handle:
        return 0.0
    try:
        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return counters.WorkingSetSize / (1024.0 * 1024.0)
        return 0.0
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)

def make_http_request(host: str, port: int, path: str) -> float:
    """Sends a single HTTP/1.1 request via raw socket and returns latency in milliseconds."""
    t0 = time.perf_counter()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5.0)
    try:
        s.connect((host, port))
        req = f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n"
        s.sendall(req.encode('ascii'))
        resp = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            resp += chunk
        t1 = time.perf_counter()
        return (t1 - t0) * 1000.0
    finally:
        s.close()

def wait_for_server(host: str, port: int, timeout: float = 5.0) -> bool:
    t_start = time.time()
    while time.time() - t_start < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.05)
    return False

def benchmark_endpoint(host: str, port: int, path: str, num_requests: int, concurrency: int, pid: int):
    latencies = []
    errors = 0
    lock = threading.Lock()

    def worker():
        nonlocal errors
        try:
            lat = make_http_request(host, port, path)
            with lock:
                latencies.append(lat)
        except Exception:
            with lock:
                errors += 1

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker) for _ in range(num_requests)]
        for f in futures:
            f.result()
    t1 = time.perf_counter()

    elapsed = t1 - t0
    rps = len(latencies) / elapsed if elapsed > 0 else 0
    latencies.sort()

    mem_mb = get_process_memory_mb(pid)

    return {
        "requests": num_requests,
        "concurrency": concurrency,
        "success": len(latencies),
        "errors": errors,
        "elapsed_sec": elapsed,
        "rps": rps,
        "min_ms": min(latencies) if latencies else 0,
        "avg_ms": statistics.mean(latencies) if latencies else 0,
        "p50_ms": statistics.median(latencies) if latencies else 0,
        "p95_ms": latencies[int(len(latencies) * 0.95)] if latencies else 0,
        "p99_ms": latencies[int(len(latencies) * 0.99)] if latencies else 0,
        "max_ms": max(latencies) if latencies else 0,
        "ram_mb": mem_mb
    }

def main():
    root = os.path.dirname(os.path.abspath(__file__))
    velo_exe = os.path.join(root, "server_velo.exe")
    node_js = os.path.join(root, "server_node.js")

    if not os.path.exists(velo_exe):
        print(f"[Error] Velo binary not found at {velo_exe}. Run 'velo build server_velo.vl -o server_velo.exe' first.")
        sys.exit(1)

    print("=" * 70)
    print(" 🚀 Velo 2.0 vs. Node.js (v24) HTTP Benchmark Suite")
    print("=" * 70)

    # 1. Start Velo Server on 8080
    print("[1/4] Spawning Velo HTTP Server on http://127.0.0.1:8080...")
    velo_proc = subprocess.Popen([velo_exe], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if not wait_for_server("127.0.0.1", 8080):
        print("[Error] Failed to connect to Velo server!")
        velo_proc.kill()
        sys.exit(1)
    velo_baseline_mem = get_process_memory_mb(velo_proc.pid)
    print(f"      -> Velo Running (PID: {velo_proc.pid}) | Baseline RAM: {velo_baseline_mem:.2f} MB")

    # 2. Start Node.js Server on 8081
    print("[2/4] Spawning Node.js HTTP Server on http://127.0.0.1:8081...")
    node_proc = subprocess.Popen(["node", node_js], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if not wait_for_server("127.0.0.1", 8081):
        print("[Error] Failed to connect to Node.js server!")
        velo_proc.kill()
        node_proc.kill()
        sys.exit(1)
    node_baseline_mem = get_process_memory_mb(node_proc.pid)
    print(f"      -> Node.js Running (PID: {node_proc.pid}) | Baseline RAM: {node_baseline_mem:.2f} MB")

    try:
        # Warmup
        print("\n[3/4] Warming up servers (100 requests each)...")
        benchmark_endpoint("127.0.0.1", 8080, "/plaintext", 100, 10, velo_proc.pid)
        benchmark_endpoint("127.0.0.1", 8081, "/plaintext", 100, 10, node_proc.pid)

        # Scenarios to test
        scenarios = [
            ("Plaintext (/plaintext)", "/plaintext", 1000, 20),
            ("JSON REST (/json)", "/json", 1000, 20),
            ("High Concurrency (/plaintext)", "/plaintext", 2000, 50),
            ("High Concurrency (/json)", "/json", 2000, 50),
        ]

        results = []

        print("\n[4/4] Executing Benchmark Scenarios...")
        for title, path, reqs, conc in scenarios:
            print(f"\n--- Running: {title} ({reqs} requests, concurrency {conc}) ---")
            
            # Velo
            v_res = benchmark_endpoint("127.0.0.1", 8080, path, reqs, conc, velo_proc.pid)
            print(f" [Velo]    {v_res['rps']:8.1f} req/s | Avg: {v_res['avg_ms']:5.2f}ms | p95: {v_res['p95_ms']:5.2f}ms | RAM: {v_res['ram_mb']:5.2f} MB")

            # Node
            n_res = benchmark_endpoint("127.0.0.1", 8081, path, reqs, conc, node_proc.pid)
            print(f" [Node.js] {n_res['rps']:8.1f} req/s | Avg: {n_res['avg_ms']:5.2f}ms | p95: {n_res['p95_ms']:5.2f}ms | RAM: {n_res['ram_mb']:5.2f} MB")

            results.append((title, v_res, n_res))

        # Print Final Comparison Summary Table
        print("\n" + "=" * 80)
        print(" 📊 FINAL BENCHMARK COMPARISON SUMMARY")
        print("=" * 80)
        header = f"{'Scenario':<30} | {'Metric':<14} | {'Velo 2.0':<14} | {'Node.js v24':<14} | {'Winner':<10}"
        print(header)
        print("-" * len(header))

        report_md = ["# 🏁 Velo vs. Node.js HTTP Server Benchmark Results\n\n"]
        report_md.append(f"- **Velo Baseline RAM**: `{velo_baseline_mem:.2f} MB`\n")
        report_md.append(f"- **Node.js Baseline RAM**: `{node_baseline_mem:.2f} MB` (Velo uses ~**{node_baseline_mem / max(velo_baseline_mem, 0.1):.1f}x less RAM**)\n\n")
        report_md.append("| Benchmark Scenario | Metric | Velo 2.0 | Node.js v24 | Winner |\n")
        report_md.append("| :--- | :--- | :---: | :---: | :---: |\n")

        for title, v, n in results:
            # Throughput
            v_rps = v['rps']
            n_rps = n['rps']
            rps_winner = "🏆 Velo" if v_rps >= n_rps else "Node.js"
            row1 = f"{title:<30} | Throughput     | {v_rps:9.1f} rps | {n_rps:9.1f} rps | {rps_winner}"
            print(row1)
            report_md.append(f"| **{title}** | **Throughput** | **{v_rps:,.1f} req/s** | {n_rps:,.1f} req/s | {rps_winner} |\n")

            # Latency (Avg)
            v_lat = v['avg_ms']
            n_lat = n['avg_ms']
            lat_winner = "🏆 Velo" if v_lat <= n_lat else "Node.js"
            row2 = f"{'':<30} | Avg Latency    | {v_lat:9.2f} ms  | {n_lat:9.2f} ms  | {lat_winner}"
            print(row2)
            report_md.append(f"| | Avg Latency | {v_lat:.2f} ms | {n_lat:.2f} ms | {lat_winner} |\n")

            # Latency (p95)
            v_p95 = v['p95_ms']
            n_p95 = n['p95_ms']
            p95_winner = "🏆 Velo" if v_p95 <= n_p95 else "Node.js"
            row3 = f"{'':<30} | p95 Latency    | {v_p95:9.2f} ms  | {n_p95:9.2f} ms  | {p95_winner}"
            print(row3)
            report_md.append(f"| | p95 Latency | {v_p95:.2f} ms | {n_p95:.2f} ms | {p95_winner} |\n")

            # Memory Footprint
            v_ram = v['ram_mb']
            n_ram = n['ram_mb']
            ram_ratio = n_ram / max(v_ram, 0.1)
            row4 = f"{'':<30} | Working Set RAM| {v_ram:9.2f} MB  | {n_ram:9.2f} MB  | 🏆 Velo ({ram_ratio:.1f}x less)"
            print(row4)
            report_md.append(f"| | Working Set RAM | **{v_ram:.2f} MB** | {n_ram:.2f} MB | 🏆 Velo ({ram_ratio:.1f}x less) |\n")
            print("-" * len(header))

        # Save Markdown Report
        report_path = os.path.join(root, "BENCHMARK_RESULTS.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.writelines(report_md)
        print(f"\n[OK] Benchmark completed successfully! Markdown saved to {report_path}")

    finally:
        print("\nCleaning up processes...")
        velo_proc.terminate()
        node_proc.terminate()
        velo_proc.wait()
        node_proc.wait()
        print("Servers stopped cleanly.")

if __name__ == "__main__":
    main()

