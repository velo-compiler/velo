import os
import subprocess
from pathlib import Path
import pytest

pytest.importorskip("cryptography")
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()


def get_env():
    env = os.environ.copy()
    if cc_dir() not in env.get("PATH", ""):
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return env


def test_rfc8439_standard_test_suite():
    """Runs the full native Velo test suite in std/tests/crypto/chacha20poly1305_test.vl."""
    test_path = REPO_ROOT / "std" / "tests" / "crypto" / "chacha20poly1305_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_path)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=get_env(),
    )
    assert res.returncode == 0, f"STDOUT: {res.stdout}\nSTDERR: {res.stderr}"
    assert "OK: std.crypto.chacha20poly1305 tests passed" in res.stdout


def test_rfc8439_appendix_a5_decryption():
    """Verifies RFC 8439 Appendix A.5 AEAD decryption test vector (265-byte ciphertext & AAD)."""
    key_hex = "1c9240a5eb55d38af333888604f6b5f0473917c1402b80099dca5cbc207075c0"
    nonce_hex = "000000000102030405060708"
    aad_hex = "f33388860000000000004e91"
    ct_hex = (
        "64a0861575861af460f062c79be643bd"
        "5e805cfd345cf389f108670ac76c8cb2"
        "4c6cfc18755d43eea09ee94e382d26b0"
        "bdb7b73c321b0100d4f03b7f355894cf"
        "332f830e710b97ce98c8a84abd0b9481"
        "14ad176e008d33bd60f982b1ff37c855"
        "9797a06ef4f0ef61c186324e2b350638"
        "3606907b6a7c02b0f9f6157b53c867e4"
        "b9166c767b804d46a59b5216cde7a4e9"
        "9040c5a40433225ee282a1b0a06c523e"
        "af4534d7f83fa1155b0047718cbc546a"
        "0d072b04b3564eea1b422273f548271a"
        "0bb2316053fa76991955ebd63159434e"
        "cebb4e466dae5a1073a6727627097a10"
        "49e617d91d361094fa68f0ff77987130"
        "305beaba2eda04df997b714d6c6f2c29"
        "a6ad5cb4022b02709b"
    )
    tag_hex = "eead9d67890cbb22392336fea1851f38"

    src = f'''use std.crypto
use std.io

act main() -> i32 {{
    let k: @u8 = heap_alloc(32) as @u8
    hex_to_bytes("{key_hex}", k, 32)
    let n: @u8 = heap_alloc(12) as @u8
    hex_to_bytes("{nonce_hex}", n, 12)
    let aad: @u8 = heap_alloc(12) as @u8
    hex_to_bytes("{aad_hex}", aad, 12)

    let ct: @u8 = heap_alloc(265) as @u8
    hex_to_bytes("{ct_hex}", ct, 265)
    let tag: @u8 = heap_alloc(16) as @u8
    hex_to_bytes("{tag_hex}", tag, 16)

    let pt: @u8 = heap_alloc(265) as @u8
    let ok = chacha20poly1305_decrypt(k, n, aad, 12, ct, 265, tag, pt)
    if !ok {{
        io.println_str("FAIL: A.5 decryption failed")
        return 1
    }}

    // Check first 15 bytes are "Internet-Drafts"
    if !crypto_secure_eq(pt, "Internet-Drafts" as @u8, 15) {{
        io.println_str("FAIL: A.5 decrypted plaintext prefix mismatch")
        return 2
    }}

    io.println_str("PASS: A.5 decryption verified")
    heap_free(k as @void); heap_free(n as @void); heap_free(aad as @void)
    heap_free(ct as @void); heap_free(tag as @void); heap_free(pt as @void)
    return 0
}}
'''
    tmp_vl = REPO_ROOT / "tests" / "_tmp_chacha_a5.vl"
    tmp_vl.write_text(src, encoding="utf-8")
    try:
        res = subprocess.run(
            [str(VELO_EXE), "run", str(tmp_vl)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=get_env(),
        )
        assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
        assert "PASS: A.5 decryption verified" in res.stdout
    finally:
        if tmp_vl.exists():
            tmp_vl.unlink()


def test_nonce_reuse_refusal_handle():
    """Verifies that ChaCha20Poly1305Handle strictly refuses nonce reuse via returning null ?@u8."""
    src = '''use std.crypto
use std.io

act main() -> i32 {
    let key: @u8 = heap_alloc(32) as @u8
    mut i: usize = 0
    loop i < 32 { key[i] = (i + 1) as u8; i += 1 }

    // Case 1: Handle with explicit nonce
    let nonce: @u8 = heap_alloc(12) as @u8
    i = 0
    loop i < 12 { nonce[i] = (i + 10) as u8; i += 1 }

    let h = chacha20poly1305_handle_new(key, 32, nonce, 12)
    if h == null {
        io.println_str("FAIL: handle_new failed")
        return 1
    }
    if chacha20poly1305_handle_is_used(h) {
        io.println_str("FAIL: handle initialized as used")
        return 2
    }

    let tag1: @u8 = heap_alloc(16) as @u8
    let msg1 = "Secret message payload #1"
    let ct1 = chacha20poly1305_handle_seal(h, msg1 as @u8, str.len(msg1), null, 0, tag1)
    if ct1 == null {
        io.println_str("FAIL: first seal failed")
        return 3
    }
    if !chacha20poly1305_handle_is_used(h) {
        io.println_str("FAIL: handle not marked as used")
        return 4
    }

    // Attempt second seal with same handle -> MUST RETURN NULL (REFUSED)
    let tag2: @u8 = heap_alloc(16) as @u8
    let msg2 = "Second payload attempting catastrophic nonce reuse"
    let ct2 = chacha20poly1305_handle_seal(h, msg2 as @u8, str.len(msg2), null, 0, tag2)
    if ct2 != null {
        io.println_str("FAIL: handle permitted nonce reuse!")
        return 5
    }

    // Third attempt also refused
    let ct3 = chacha20poly1305_handle_seal(h, msg2 as @u8, str.len(msg2), null, 0, tag2)
    if ct3 != null {
        io.println_str("FAIL: handle permitted nonce reuse on 3rd attempt!")
        return 6
    }

    chacha20poly1305_handle_free(h)
    heap_free(ct1 as @void); heap_free(tag1 as @void); heap_free(tag2 as @void)
    heap_free(nonce as @void)

    // Case 2: Handle with null nonce (auto-seeded by CSPRNG)
    let h_auto = chacha20poly1305_handle_new(key, 32, null, 0)
    if h_auto == null {
        io.println_str("FAIL: handle_new with auto nonce failed")
        return 7
    }
    let auto_nonce = chacha20poly1305_handle_nonce(h_auto)
    if auto_nonce == null {
        io.println_str("FAIL: auto nonce is null")
        return 8
    }

    let tag_auto: @u8 = heap_alloc(16) as @u8
    let ct_auto = chacha20poly1305_handle_seal(h_auto, "data" as @u8, 4, null, 0, tag_auto)
    if ct_auto == null {
        io.println_str("FAIL: auto nonce handle seal failed")
        return 9
    }

    // Nonce reuse refused on auto handle too
    let ct_auto_reused = chacha20poly1305_handle_seal(h_auto, "data" as @u8, 4, null, 0, tag_auto)
    if ct_auto_reused != null {
        io.println_str("FAIL: auto nonce handle permitted reuse")
        return 10
    }

    chacha20poly1305_handle_free(h_auto)
    heap_free(ct_auto as @void); heap_free(tag_auto as @void)
    heap_free(key as @void)

    io.println_str("PASS: nonce reuse refusal verified")
    return 0
}
'''
    tmp_vl = REPO_ROOT / "tests" / "_tmp_chacha_reuse.vl"
    tmp_vl.write_text(src, encoding="utf-8")
    try:
        res = subprocess.run(
            [str(VELO_EXE), "run", str(tmp_vl)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=get_env(),
        )
        assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
        assert "PASS: nonce reuse refusal verified" in res.stdout
    finally:
        if tmp_vl.exists():
            tmp_vl.unlink()


def test_cross_cryptography_bidirectional():
    """Generates random data in Python, encrypts with cryptography library, decrypts in Velo, and vice versa."""
    import secrets

    key = secrets.token_bytes(32)
    nonce = secrets.token_bytes(12)
    aad = b"header-metadata-aad-42"
    plaintext = b"Cross-validation between pure Velo RFC 8439 and OpenSSL cryptography hazmat!"

    chacha = ChaCha20Poly1305(key)
    res = chacha.encrypt(nonce, plaintext, aad)
    ct = res[:-16]
    tag = res[-16:]

    src = f'''use std.crypto
use std.io

act main() -> i32 {{
    let k: @u8 = heap_alloc(32) as @u8
    hex_to_bytes("{key.hex()}", k, 32)
    let n: @u8 = heap_alloc(12) as @u8
    hex_to_bytes("{nonce.hex()}", n, 12)
    let aad: @u8 = heap_alloc({len(aad)}) as @u8
    hex_to_bytes("{aad.hex()}", aad, {len(aad)})

    let ct: @u8 = heap_alloc({len(ct)}) as @u8
    hex_to_bytes("{ct.hex()}", ct, {len(ct)})
    let tag: @u8 = heap_alloc(16) as @u8
    hex_to_bytes("{tag.hex()}", tag, 16)

    let pt: @u8 = heap_alloc({len(plaintext)}) as @u8
    let ok = chacha20poly1305_decrypt(k, n, aad, {len(aad)}, ct, {len(ct)}, tag, pt)
    if !ok {{
        io.println_str("FAIL: cross decrypt failed")
        return 1
    }}

    let expected = "{plaintext.decode('utf-8')}"
    if !crypto_secure_eq(pt, expected as @u8, {len(plaintext)}) {{
        io.println_str("FAIL: cross decrypted plaintext mismatch")
        return 2
    }}

    // Now re-encrypt in Velo and verify byte output matches OpenSSL cryptography
    let out_ct: @u8 = heap_alloc({len(plaintext)}) as @u8
    let out_tag: @u8 = heap_alloc(16) as @u8
    chacha20poly1305_encrypt(k, n, aad, {len(aad)}, pt, {len(plaintext)}, out_ct, out_tag)

    let out_ct_hex = bytes_to_hex(out_ct, {len(plaintext)})
    let out_tag_hex = bytes_to_hex(out_tag, 16)

    if out_ct_hex != "{ct.hex()}" {{
        io.println_str("FAIL: re-encrypt ct mismatch")
        return 3
    }}
    if out_tag_hex != "{tag.hex()}" {{
        io.println_str("FAIL: re-encrypt tag mismatch")
        return 4
    }}

    io.println_str("PASS: bidirectional cross-validation passed")
    heap_free(k as @void); heap_free(n as @void); heap_free(aad as @void)
    heap_free(ct as @void); heap_free(tag as @void); heap_free(pt as @void)
    heap_free(out_ct as @void); heap_free(out_tag as @void)
    return 0
}}
'''
    tmp_vl = REPO_ROOT / "tests" / "_tmp_chacha_cross.vl"
    tmp_vl.write_text(src, encoding="utf-8")
    try:
        res = subprocess.run(
            [str(VELO_EXE), "run", str(tmp_vl)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=get_env(),
        )
        assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
        assert "PASS: bidirectional cross-validation passed" in res.stdout
    finally:
        if tmp_vl.exists():
            tmp_vl.unlink()
