import subprocess
import socket
import ssl
import sys
import tempfile
import threading
import time
import datetime
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ed25519

REPO_ROOT = Path(__file__).parent.parent
from conftest import velo_exe
VELO_EXE = velo_exe()

def generate_ed25519_cert(common_name="localhost", san_dns=None):
    priv = ed25519.Ed25519PrivateKey.generate()
    builder = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)]))
        .public_key(priv.public_key())
        .serial_number(123456789)
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1))
    )
    if san_dns:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.DNSName(name) for name in san_dns]),
            critical=False,
        )
    cert = builder.sign(priv, None)
    der = cert.public_bytes(serialization.Encoding.DER)
    pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    fp = hashes.Hash(hashes.SHA256())
    fp.update(der)
    fp_hex = fp.finalize().hex()
    return priv, cert, der, pem, key_pem, fp_hex

def test_tls_positive_handshake_and_echo():
    """Verify standard TLS 1.3 client handshake against a pinned Ed25519 server."""
    priv, cert, der, pem, key_pem, fp_hex = generate_ed25519_cert("localhost", ["localhost"])
    
    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as cf, tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as kf:
        cf.write(pem); cf.flush()
        kf.write(key_pem); kf.flush()
        cert_path = cf.name
        key_path = kf.name

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.maximum_version = ssl.TLSVersion.TLSv1_3
    ctx.load_cert_chain(cert_path, key_path)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    port = srv.getsockname()[1]
    srv.listen(1)

    server_received = []

    def server_worker():
        try:
            conn, _ = srv.accept()
            tls_conn = ctx.wrap_socket(conn, server_side=True)
            msg = tls_conn.read(1024)
            server_received.append(msg.decode("utf-8", errors="replace"))
            tls_conn.write(b"PONG_TLS13")
            time.sleep(0.05)
            tls_conn.close()
        except Exception as e:
            server_received.append(f"ERROR: {e}")
        finally:
            srv.close()

    t = threading.Thread(target=server_worker)
    t.start()

    client_code = f"""
    use std.tls
    use std.io

    act main() -> i32 {{
        let cfg = tls_config_new()
        cfg.verify_peer = true
        cfg.server_name = "localhost"
        cfg.pinned_cert_fp_hex = "{fp_hex}"

        let c_res = tls_connect("127.0.0.1", {port} as u16, cfg)
        if !c_res.ok {{
            println_str(str.concat("CONNECT_FAIL: ", c_res.err))
            return 1
        }}
        let sock = c_res.val

        let w_res = tls_write_str(sock, "PING_TLS13")
        if !w_res.ok {{
            println_str(str.concat("WRITE_FAIL: ", w_res.err))
            tls_close(sock)
            return 2
        }}

        let r_res = tls_read_str(sock, 1024)
        if !r_res.ok {{
            println_str(str.concat("READ_FAIL: ", r_res.err))
            tls_close(sock)
            return 3
        }}

        println_str(str.concat("REPLY: ", r_res.val))
        tls_close(sock)
        return 0
    }}
    """
    client_vl = REPO_ROOT / "tests" / "_tmp_tls_positive.vl"
    client_vl.write_text(client_code, encoding="utf-8")

    try:
        res = subprocess.run([str(VELO_EXE), "run", str(client_vl)], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO_ROOT), timeout=15)
        t.join(timeout=5)
        assert res.returncode == 0, f"Client exited with {res.returncode}:\n{res.stdout}\n{res.stderr}"
        assert "REPLY: PONG_TLS13" in res.stdout, f"Unexpected output:\n{res.stdout}"
        assert server_received == ["PING_TLS13"], f"Server received: {server_received}"
    finally:
        if client_vl.exists():
            client_vl.unlink()

def test_tls_negative_untrusted_peer():
    """Verify that a certificate with mismatching fingerprint fails closed with TlsUntrustedPeer."""
    priv, cert, der, pem, key_pem, fp_hex = generate_ed25519_cert("localhost", ["localhost"])
    
    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as cf, tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as kf:
        cf.write(pem); cf.flush()
        kf.write(key_pem); kf.flush()
        cert_path = cf.name
        key_path = kf.name

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.load_cert_chain(cert_path, key_path)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    port = srv.getsockname()[1]
    srv.listen(1)

    def server_worker():
        try:
            conn, _ = srv.accept()
            ctx.wrap_socket(conn, server_side=True)
        except Exception:
            pass
        finally:
            srv.close()

    t = threading.Thread(target=server_worker)
    t.start()

    # Wrong pinned fingerprint
    wrong_fp = "00" * 32
    client_code = f"""
    use std.tls
    use std.io

    act main() -> i32 {{
        let cfg = tls_config_new()
        cfg.verify_peer = true
        cfg.server_name = "localhost"
        cfg.pinned_cert_fp_hex = "{wrong_fp}"

        let c_res = tls_connect("127.0.0.1", {port} as u16, cfg)
        if !c_res.ok {{
            println_str(str.concat("EXPECTED_ERR: ", c_res.err))
            return 0
        }}
        println_str("UNEXPECTED_SUCCESS")
        tls_close(c_res.val)
        return 1
    }}
    """
    client_vl = REPO_ROOT / "tests" / "_tmp_tls_neg_untrusted.vl"
    client_vl.write_text(client_code, encoding="utf-8")

    try:
        res = subprocess.run([str(VELO_EXE), "run", str(client_vl)], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO_ROOT), timeout=15)
        t.join(timeout=5)
        assert res.returncode == 0, f"Client exited with {res.returncode}:\n{res.stdout}\n{res.stderr}"
        assert "EXPECTED_ERR: TlsUntrustedPeer" in res.stdout, f"Unexpected output:\n{res.stdout}"
    finally:
        if client_vl.exists():
            client_vl.unlink()

def test_tls_negative_hostname_mismatch():
    """Verify that a certificate for another hostname fails closed with TlsHostnameMismatch."""
    priv, cert, der, pem, key_pem, fp_hex = generate_ed25519_cert("attacker.internal", ["attacker.internal"])
    
    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as cf, tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as kf:
        cf.write(pem); cf.flush()
        kf.write(key_pem); kf.flush()
        cert_path = cf.name
        key_path = kf.name

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.load_cert_chain(cert_path, key_path)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    port = srv.getsockname()[1]
    srv.listen(1)

    def server_worker():
        try:
            conn, _ = srv.accept()
            ctx.wrap_socket(conn, server_side=True)
        except Exception:
            pass
        finally:
            srv.close()

    t = threading.Thread(target=server_worker)
    t.start()

    # Pinned matches cert, but server_name does not match cert's CN/SAN
    client_code = f"""
    use std.tls
    use std.io

    act main() -> i32 {{
        let cfg = tls_config_new()
        cfg.verify_peer = true
        cfg.server_name = "legit.example.com"
        cfg.pinned_cert_fp_hex = "{fp_hex}"

        let c_res = tls_connect("127.0.0.1", {port} as u16, cfg)
        if !c_res.ok {{
            println_str(str.concat("EXPECTED_ERR: ", c_res.err))
            return 0
        }}
        println_str("UNEXPECTED_SUCCESS")
        tls_close(c_res.val)
        return 1
    }}
    """
    client_vl = REPO_ROOT / "tests" / "_tmp_tls_neg_host.vl"
    client_vl.write_text(client_code, encoding="utf-8")

    try:
        res = subprocess.run([str(VELO_EXE), "run", str(client_vl)], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO_ROOT), timeout=15)
        t.join(timeout=5)
        assert res.returncode == 0, f"Client exited with {res.returncode}:\n{res.stdout}\n{res.stderr}"
        assert "EXPECTED_ERR: TlsHostnameMismatch" in res.stdout, f"Unexpected output:\n{res.stdout}"
    finally:
        if client_vl.exists():
            client_vl.unlink()

def test_tls_negative_tampered_record():
    """Verify that an altered ciphertext or tag in a TLS record fails closed with TlsTamperedRecord."""
    priv, cert, der, pem, key_pem, fp_hex = generate_ed25519_cert("localhost", ["localhost"])
    
    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as cf, tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as kf:
        cf.write(pem); cf.flush()
        kf.write(key_pem); kf.flush()
        cert_path = cf.name
        key_path = kf.name

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.load_cert_chain(cert_path, key_path)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv_port = srv.getsockname()[1]
    srv.listen(1)

    proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy.bind(("127.0.0.1", 0))
    proxy_port = proxy.getsockname()[1]
    proxy.listen(1)

    def server_worker():
        try:
            conn, _ = srv.accept()
            tls_conn = ctx.wrap_socket(conn, server_side=True)
            tls_conn.read(1024)
        except Exception:
            pass
        finally:
            srv.close()

    def proxy_worker():
        try:
            client_sock, _ = proxy.accept()
            srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv_sock.connect(("127.0.0.1", srv_port))

            # Forward ClientHello from client to server
            ch = client_sock.recv(4096)
            srv_sock.sendall(ch)

            # Read ServerHello and server flight from server
            data = srv_sock.recv(4096)
            # Find the first application_data record (0x17) and tamper with 1 byte of ciphertext
            idx = data.find(b"\x17\x03\x03")
            if idx != -1 and len(data) > idx + 10:
                data_tampered = bytearray(data)
                data_tampered[idx + 10] ^= 0x55  # Corrupt 1 byte of encrypted record
                client_sock.sendall(data_tampered)
            else:
                client_sock.sendall(data)
            
            time.sleep(0.1)
            client_sock.close()
            srv_sock.close()
        except Exception:
            pass
        finally:
            proxy.close()

    t_srv = threading.Thread(target=server_worker)
    t_proxy = threading.Thread(target=proxy_worker)
    t_srv.start()
    t_proxy.start()

    client_code = f"""
    use std.tls
    use std.io

    act main() -> i32 {{
        let cfg = tls_config_new()
        cfg.verify_peer = true
        cfg.server_name = "localhost"
        cfg.pinned_cert_fp_hex = "{fp_hex}"

        let c_res = tls_connect("127.0.0.1", {proxy_port} as u16, cfg)
        if !c_res.ok {{
            println_str(str.concat("EXPECTED_ERR: ", c_res.err))
            return 0
        }}
        println_str("UNEXPECTED_SUCCESS")
        tls_close(c_res.val)
        return 1
    }}
    """
    client_vl = REPO_ROOT / "tests" / "_tmp_tls_neg_tamper.vl"
    client_vl.write_text(client_code, encoding="utf-8")

    try:
        res = subprocess.run([str(VELO_EXE), "run", str(client_vl)], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO_ROOT), timeout=15)
        t_srv.join(timeout=5)
        t_proxy.join(timeout=5)
        assert res.returncode == 0, f"Client exited with {res.returncode}:\n{res.stdout}\n{res.stderr}"
        assert "EXPECTED_ERR: TlsTamperedRecord" in res.stdout, f"Unexpected output:\n{res.stdout}"
    finally:
        if client_vl.exists():
            client_vl.unlink()

