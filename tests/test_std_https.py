import subprocess
import socket
import ssl
import sys
import tempfile
import threading
import time
import datetime
from pathlib import Path
import pytest
pytest.importorskip("cryptography")
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

def test_https_get_success_pinned_cert():
    """Verify that http_get_with_tls succeeds against a local HTTPS server with pinned certificate."""
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
            msg = tls_conn.read(2048)
            server_received.append(msg.decode("utf-8", errors="replace"))
            resp = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/plain\r\n"
                b"Content-Length: 12\r\n"
                b"Connection: close\r\n"
                b"\r\n"
                b"Hello HTTPS!"
            )
            tls_conn.write(resp)
            time.sleep(0.05)
            tls_conn.close()
        except Exception as e:
            server_received.append(f"ERROR: {e}")
        finally:
            srv.close()

    t = threading.Thread(target=server_worker)
    t.start()

    client_code = f"""
    use std.http
    use std.tls
    use std.io

    act main() -> i32 {{
        let cfg = tls_config_new()
        cfg.verify_peer = true
        cfg.server_name = "localhost"
        cfg.pinned_cert_fp_hex = "{fp_hex}"

        let resp = http_get_with_tls("https://localhost:{port}/hello", cfg)
        println_str(str.concat("STATUS_TEXT: ", resp.status_text))
        println_str(str.concat("BODY: ", resp.body))
        if resp.status_code == (200 as u16) and resp.body == "Hello HTTPS!" {{
            println_str("OK_GET_SUCCESS")
            return 0
        }}
        return 1
    }}
    """
    client_vl = REPO_ROOT / "tests" / "_tmp_https_get_pinned.vl"
    client_vl.write_text(client_code, encoding="utf-8")

    try:
        res = subprocess.run([str(VELO_EXE), "run", str(client_vl)], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO_ROOT), timeout=15)
        t.join(timeout=5)
        assert res.returncode == 0, f"Client exited with {res.returncode}:\n{res.stdout}\n{res.stderr}"
        assert "OK_GET_SUCCESS" in res.stdout
        assert "BODY: Hello HTTPS!" in res.stdout
        assert len(server_received) == 1
        assert "GET /hello HTTP/1.1" in server_received[0]
        assert "Host: localhost" in server_received[0]
    finally:
        if client_vl.exists():
            client_vl.unlink()

def test_https_get_fails_untrusted_peer():
    """Verify that http_get against an unpinned self-signed HTTPS certificate fails closed with TlsUntrustedPeer."""
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

    # http_get default uses verify_peer: true with no pin -> must fail closed with TlsUntrustedPeer
    client_code = f"""
    use std.http
    use std.io

    act main() -> i32 {{
        let resp = http_get("https://localhost:{port}/secret")
        println_str(str.concat("STATUS_TEXT: ", resp.status_text))
        println_str(str.concat("BODY: ", resp.body))
        if resp.status_code == (526 as u16) and resp.status_text == "TlsUntrustedPeer" {{
            println_str("OK_UNTRUSTED_FAIL_CLOSED")
            return 0
        }}
        return 1
    }}
    """
    client_vl = REPO_ROOT / "tests" / "_tmp_https_get_untrusted.vl"
    client_vl.write_text(client_code, encoding="utf-8")

    try:
        res = subprocess.run([str(VELO_EXE), "run", str(client_vl)], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO_ROOT), timeout=15)
        t.join(timeout=5)
        assert res.returncode == 0, f"Client exited with {res.returncode}:\n{res.stdout}\n{res.stderr}"
        assert "OK_UNTRUSTED_FAIL_CLOSED" in res.stdout
        assert "STATUS_TEXT: TlsUntrustedPeer" in res.stdout
        assert "TlsUntrustedPeer" in res.stdout
    finally:
        if client_vl.exists():
            client_vl.unlink()

def test_https_get_fails_hostname_mismatch():
    """Verify that an HTTPS certificate for a different hostname fails closed with TlsHostnameMismatch."""
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

    # Hostname in URL is localhost, but cert is for attacker.internal
    client_code = f"""
    use std.http
    use std.tls
    use std.io

    act main() -> i32 {{
        let cfg = tls_config_new()
        cfg.verify_peer = true
        cfg.server_name = "localhost"
        cfg.pinned_cert_fp_hex = "{fp_hex}"

        let resp = http_get_with_tls("https://localhost:{port}/info", cfg)
        println_str(str.concat("STATUS_TEXT: ", resp.status_text))
        if resp.status_code == (526 as u16) and resp.status_text == "TlsHostnameMismatch" {{
            println_str("OK_HOSTNAME_FAIL_CLOSED")
            return 0
        }}
        return 1
    }}
    """
    client_vl = REPO_ROOT / "tests" / "_tmp_https_get_host_mismatch.vl"
    client_vl.write_text(client_code, encoding="utf-8")

    try:
        res = subprocess.run([str(VELO_EXE), "run", str(client_vl)], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO_ROOT), timeout=15)
        t.join(timeout=5)
        assert res.returncode == 0, f"Client exited with {res.returncode}:\n{res.stdout}\n{res.stderr}"
        assert "OK_HOSTNAME_FAIL_CLOSED" in res.stdout
        assert "STATUS_TEXT: TlsHostnameMismatch" in res.stdout
    finally:
        if client_vl.exists():
            client_vl.unlink()

def test_https_post_success_pinned_cert():
    """Verify that http_post_with_tls transmits payload over TLS and receives the response."""
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

    server_received = []

    def server_worker():
        try:
            conn, _ = srv.accept()
            tls_conn = ctx.wrap_socket(conn, server_side=True)
            msg = tls_conn.read(2048)
            server_received.append(msg.decode("utf-8", errors="replace"))
            resp = (
                b"HTTP/1.1 201 Created\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: 20\r\n"
                b"Connection: close\r\n"
                b"\r\n"
                b"{\"status\":\"created\"}"
            )
            tls_conn.write(resp)
            time.sleep(0.05)
            tls_conn.close()
        except Exception as e:
            server_received.append(f"ERROR: {e}")
        finally:
            srv.close()

    t = threading.Thread(target=server_worker)
    t.start()

    client_code = f"""
    use std.http
    use std.tls
    use std.io

    act main() -> i32 {{
        let cfg = tls_config_new()
        cfg.verify_peer = true
        cfg.server_name = "localhost"
        cfg.pinned_cert_fp_hex = "{fp_hex}"

        let resp = http_post_with_tls("https://localhost:{port}/items", "application/json", "{{\\"item\\":\\"book\\"}}", cfg)
        println_str(str.concat("STATUS_TEXT: ", resp.status_text))
        println_str(str.concat("BODY: ", resp.body))
        if resp.status_code == (201 as u16) and resp.body == "{{\\"status\\":\\"created\\"}}" {{
            println_str("OK_POST_SUCCESS")
            return 0
        }}
        return 1
    }}
    """
    client_vl = REPO_ROOT / "tests" / "_tmp_https_post_pinned.vl"
    client_vl.write_text(client_code, encoding="utf-8")

    try:
        res = subprocess.run([str(VELO_EXE), "run", str(client_vl)], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO_ROOT), timeout=15)
        t.join(timeout=5)
        assert res.returncode == 0, f"Client exited with {res.returncode}:\n{res.stdout}\n{res.stderr}"
        assert "OK_POST_SUCCESS" in res.stdout
        assert 'BODY: {"status":"created"}' in res.stdout
        assert len(server_received) == 1
        assert "POST /items HTTP/1.1" in server_received[0]
        assert "Content-Type: application/json" in server_received[0]
        assert '{"item":"book"}' in server_received[0]
    finally:
        if client_vl.exists():
            client_vl.unlink()
