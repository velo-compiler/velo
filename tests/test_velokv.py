"""
Automated Test Suite and Verification Harness for VeloKV
Tests end-to-end RESP2 wire protocol, all supported Redis commands,
passive TTL expiration, inline telnet commands, and throughput benchmarks.
"""

import os
import socket
import subprocess
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VELOKV_EXE = ROOT / "bin" / "velokv.exe"

def recv_line(sock: socket.socket) -> bytes:
    line = b""
    while not line.endswith(b"\r\n"):
        c = sock.recv(1)
        if not c:
            break
        line += c
    return line

def send_recv_raw(sock: socket.socket, data: bytes) -> bytes:
    sock.sendall(data)
    sock.settimeout(2.0)
    header = recv_line(sock)
    if not header:
        return b""
    prefix = header[:1]
    if prefix in (b"+", b"-", b":"):
        return header
    elif prefix == b"$":
        length = int(header[1:-2])
        if length == -1:
            return header
        payload = b""
        needed = length + 2
        while len(payload) < needed:
            chunk = sock.recv(needed - len(payload))
            if not chunk:
                break
            payload += chunk
        return header + payload
    elif prefix == b"*":
        count = int(header[1:-2])
        if count == -1:
            return header
        res = [header]
        for _ in range(count):
            line = recv_line(sock)
            if line.startswith(b"$"):
                blen = int(line[1:-2])
                if blen == -1:
                    res.append(line)
                else:
                    pay = sock.recv(blen + 2)
                    res.append(line + pay)
            else:
                res.append(line)
        return b"".join(res)
    return header

def resp_encode(*args: str) -> bytes:
    out = [f"*{len(args)}\r\n".encode("utf-8")]
    for a in args:
        b = a.encode("utf-8")
        out.append(f"${len(b)}\r\n".encode("utf-8"))
        out.append(b + b"\r\n")
    return b"".join(out)

class TestVeloKV(unittest.TestCase):
    server_proc = None
    port = 6389

    @classmethod
    def setUpClass(cls):
        # Clean any stale velokv.aof in working directory
        aof_file = ROOT / "velokv.aof"
        if aof_file.exists():
            try:
                aof_file.unlink()
            except Exception:
                pass

        # Build fresh velokv.exe if missing
        if not VELOKV_EXE.exists():
            subprocess.run(
                [str(ROOT / "bin" / "velo.exe"), "build", "apps/velokv/main.vl", "-o", str(VELOKV_EXE), "-l", "ws2_32"],
                check=True,
                cwd=str(ROOT)
            )

        # Launch server process explicitly on port 6389
        cls.server_proc = subprocess.Popen(
            [str(VELOKV_EXE), "6389"],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Wait for server to bind port 6389
        for _ in range(40):
            time.sleep(0.1)
            try:
                s = socket.create_connection(("127.0.0.1", 6389), timeout=0.2)
                cls.port = 6389
                s.close()
                return
            except (ConnectionRefusedError, socket.timeout, OSError):
                pass

        cls.tearDownClass()
        raise RuntimeError("VeloKV server failed to start on port 6389 within 4 seconds")

    @classmethod
    def tearDownClass(cls):
        if cls.server_proc:
            try:
                cls.server_proc.terminate()
                cls.server_proc.wait(timeout=1.0)
            except Exception:
                cls.server_proc.kill()

    def test_01_ping_and_echo(self):
        with socket.create_connection(("127.0.0.1", self.port), timeout=2.0) as s:
            # PING
            res = send_recv_raw(s, resp_encode("PING"))
            self.assertEqual(res, b"+PONG\r\n")

            # PING with custom message
            res = send_recv_raw(s, resp_encode("PING", "Hello Velo!"))
            self.assertEqual(res, b"$11\r\nHello Velo!\r\n")

            # ECHO
            res = send_recv_raw(s, resp_encode("ECHO", "Native Zero-GC Engine"))
            self.assertEqual(res, b"$21\r\nNative Zero-GC Engine\r\n")

    def test_02_get_set_del_exists(self):
        with socket.create_connection(("127.0.0.1", self.port), timeout=2.0) as s:
            # GET on missing key -> nil ($-1\r\n)
            res = send_recv_raw(s, resp_encode("GET", "my_nonexistent_key"))
            self.assertEqual(res, b"$-1\r\n")

            # SET key val
            res = send_recv_raw(s, resp_encode("SET", "cluster_name", "alpha_node_01"))
            self.assertEqual(res, b"+OK\r\n")

            # GET key
            res = send_recv_raw(s, resp_encode("GET", "cluster_name"))
            self.assertEqual(res, b"$13\r\nalpha_node_01\r\n")

            # EXISTS key
            res = send_recv_raw(s, resp_encode("EXISTS", "cluster_name"))
            self.assertEqual(res, b":1\r\n")

            # DEL key
            res = send_recv_raw(s, resp_encode("DEL", "cluster_name"))
            self.assertEqual(res, b":1\r\n")

            # EXISTS after DEL -> 0
            res = send_recv_raw(s, resp_encode("EXISTS", "cluster_name"))
            self.assertEqual(res, b":0\r\n")

    def test_03_incr_decr(self):
        with socket.create_connection(("127.0.0.1", self.port), timeout=2.0) as s:
            send_recv_raw(s, resp_encode("DEL", "session_counter"))
            res1 = send_recv_raw(s, resp_encode("INCR", "session_counter"))
            self.assertEqual(res1, b":1\r\n")
            res2 = send_recv_raw(s, resp_encode("INCR", "session_counter"))
            self.assertEqual(res2, b":2\r\n")
            res3 = send_recv_raw(s, resp_encode("INCR", "session_counter"))
            self.assertEqual(res3, b":3\r\n")
            res4 = send_recv_raw(s, resp_encode("DECR", "session_counter"))
            self.assertEqual(res4, b":2\r\n")

    def test_04_mset_and_dbsize(self):
        with socket.create_connection(("127.0.0.1", self.port), timeout=2.0) as s:
            send_recv_raw(s, resp_encode("FLUSHDB"))
            res = send_recv_raw(s, resp_encode("MSET", "usr:1", "Alice", "usr:2", "Bob", "usr:3", "Charlie"))
            self.assertEqual(res, b"+OK\r\n")

            # Verify values
            self.assertEqual(send_recv_raw(s, resp_encode("GET", "usr:1")), b"$5\r\nAlice\r\n")
            self.assertEqual(send_recv_raw(s, resp_encode("GET", "usr:2")), b"$3\r\nBob\r\n")
            self.assertEqual(send_recv_raw(s, resp_encode("GET", "usr:3")), b"$7\r\nCharlie\r\n")

            # DBSIZE
            res_size = send_recv_raw(s, resp_encode("DBSIZE"))
            self.assertEqual(res_size, b":3\r\n")

    def test_05_ttl_and_expiration(self):
        with socket.create_connection(("127.0.0.1", self.port), timeout=3.0) as s:
            # Set key with EX 1 (1 second TTL)
            send_recv_raw(s, resp_encode("SET", "temp_token", "secret123", "EX", "1"))
            ttl_res = send_recv_raw(s, resp_encode("TTL", "temp_token"))
            self.assertTrue(ttl_res.startswith(b":1\r\n") or ttl_res.startswith(b":2\r\n"))

            # Key exists initially
            self.assertEqual(send_recv_raw(s, resp_encode("GET", "temp_token")), b"$9\r\nsecret123\r\n")

            # Wait 1.2 seconds for expiration
            time.sleep(1.2)

            # Key should now be expired and return nil
            self.assertEqual(send_recv_raw(s, resp_encode("GET", "temp_token")), b"$-1\r\n")
            self.assertEqual(send_recv_raw(s, resp_encode("TTL", "temp_token")), b":-2\r\n")

    def test_06_inline_telnet_protocol(self):
        with socket.create_connection(("127.0.0.1", self.port), timeout=2.0) as s:
            # Send plain ASCII line without RESP array framing
            res = send_recv_raw(s, b"PING\r\n")
            self.assertEqual(res, b"+PONG\r\n")

            res = send_recv_raw(s, b"SET inline_key fast_val\r\n")
            self.assertEqual(res, b"+OK\r\n")

            res = send_recv_raw(s, b"GET inline_key\r\n")
            self.assertEqual(res, b"$8\r\nfast_val\r\n")

    def test_07_info_telemetry(self):
        with socket.create_connection(("127.0.0.1", self.port), timeout=2.0) as s:
            res = send_recv_raw(s, resp_encode("INFO"))
            self.assertTrue(res.startswith(b"$"))
            info_text = res.decode("utf-8")
            self.assertIn("velokv_version:1.0.0", info_text)
            self.assertIn("total_commands_processed=", info_text)
            self.assertIn("keyspace_hits=", info_text)

    def test_08_throughput_benchmark(self):
        """Microbenchmark: 1,000 round-trip commands through socket"""
        with socket.create_connection(("127.0.0.1", self.port), timeout=10.0) as s:
            t0 = time.perf_counter()
            count = 1000
            for i in range(count):
                cmd = resp_encode("SET", f"bench_key_{i}", f"bench_val_{i}")
                res = send_recv_raw(s, cmd)
                if res != b"+OK\r\n":
                    self.fail(f"Benchmark SET failed at iteration {i}: {res}")
            t1 = time.perf_counter()
            elapsed = t1 - t0
            ops_per_sec = count / elapsed
            print(f"\n[VeloKV Benchmark] 1,000 round-trip SET ops in {elapsed:.3f}s: {ops_per_sec:,.0f} ops/sec")
            self.assertGreater(ops_per_sec, 200)

    def test_09_aof_persistence_recovery(self):
        """Verifies Append-Only File replay reconstructs state across server restart"""
        # 1. Write persistence test keys
        with socket.create_connection(("127.0.0.1", self.port), timeout=2.0) as s:
            send_recv_raw(s, resp_encode("SET", "persist_node", "cluster_omega"))
            send_recv_raw(s, resp_encode("SET", "persist_secret", "velo_token_999"))

        # 2. Terminate server
        self.server_proc.terminate()
        self.server_proc.wait(timeout=2.0)

        # 3. Verify AOF file exists and has content
        aof_path = ROOT / "velokv.aof"
        self.assertTrue(aof_path.exists())
        self.assertGreater(aof_path.stat().st_size, 0)

        # 4. Restart server on port 6389
        self.server_proc = subprocess.Popen(
            [str(VELOKV_EXE), "6389"],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(0.4)

        # 5. Connect and verify replayed keys are present
        with socket.create_connection(("127.0.0.1", self.port), timeout=2.0) as s:
            res1 = send_recv_raw(s, resp_encode("GET", "persist_node"))
            self.assertEqual(res1, b"$13\r\ncluster_omega\r\n")

            res2 = send_recv_raw(s, resp_encode("GET", "persist_secret"))
            self.assertEqual(res2, b"$14\r\nvelo_token_999\r\n")

if __name__ == "__main__":
    unittest.main()

