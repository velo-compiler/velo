"""
VeloKV Interactive CLI Client (Drop-in replacement for redis-cli on Windows)
Usage:
    python apps/velokv/cli.py [port]
"""

import sys
import socket

def send_cmd(s: socket.socket, cmd: str) -> str:
    s.sendall((cmd.strip() + "\r\n").encode("utf-8"))
    
    # Read response
    buf = b""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk
        if buf.startswith(b"$"):
            first_crlf = buf.find(b"\r\n")
            if first_crlf > 0:
                blen = int(buf[1:first_crlf])
                if blen == -1 or len(buf) >= first_crlf + 2 + blen + 2:
                    break
        elif buf.endswith(b"\r\n"):
            break
    return buf.decode("utf-8", errors="replace")

def format_resp(raw: str) -> str:
    if not raw:
        return "(nil)"
    if raw.startswith("+"):
        return raw[1:].strip()
    if raw.startswith("-"):
        return f"(error) {raw[1:].strip()}"
    if raw.startswith(":"):
        return f"(integer) {raw[1:].strip()}"
    if raw.startswith("$-1"):
        return "(nil)"
    if raw.startswith("$"):
        first_crlf = raw.find("\r\n")
        if first_crlf > 0:
            payload = raw[first_crlf + 2:]
            if payload.endswith("\r\n"):
                payload = payload[:-2]
            if "\n" in payload:
                return payload
            return f'"{payload}"'
    return raw.strip()

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 6389
    host = "127.0.0.1"

    try:
        s = socket.create_connection((host, port), timeout=5.0)
    except ConnectionRefusedError:
        print(f"Error: Could not connect to VeloKV at {host}:{port}.")
        print("Please ensure the server is running with: ./bin/velokv")
        sys.exit(1)

    print(f"Connected to VeloKV at {host}:{port}")
    print("Type Redis commands (e.g. PING, SET k v, GET k, INCR k, INFO, DBSIZE). Type 'exit' or 'quit' to close.\n")

    while True:
        try:
            line = input(f"velokv {host}:{port}> ").strip()
            if not line:
                continue
            if line.lower() in ("exit", "quit"):
                s.close()
                break

            resp = send_cmd(s, line)
            print(format_resp(resp))
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            s.close()
            break
        except Exception as e:
            print(f"(error) {e}")
            break

if __name__ == "__main__":
    main()
