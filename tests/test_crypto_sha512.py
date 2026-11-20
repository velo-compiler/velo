import os
import subprocess
import pytest
from pathlib import Path
from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()

def get_env():
    env = os.environ.copy()
    if cc_dir() not in env.get("PATH", ""):
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return env

def test_sha512_nist_vectors():
    """Verify SHA-512 against NIST FIPS 180-4 standard test vectors."""
    src = """use std.crypto
use std.io

act main() -> i32 {
    // 1. Empty string
    let h0 = sha512_hash_str("")
    if h0 != "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e" {
        io.println_str("FAIL: empty string mismatch")
        return 1
    }

    // 2. "abc"
    let h1 = sha512_hash_str("abc")
    if h1 != "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f" {
        io.println_str("FAIL: 'abc' mismatch")
        return 2
    }

    // 3. "The quick brown fox jumps over the lazy dog"
    let h2 = sha512_hash_str("The quick brown fox jumps over the lazy dog")
    if h2 != "07e547d9586f6a73f73fbac0435ed76951218fb7d0c8d788a309d785436bbb642e93a252a954f23912547d1e8a3b5ed6e1bfd7097821233fa0538f3db854fee6" {
        io.println_str("FAIL: fox mismatch")
        return 3
    }

    io.println_str("PASS: nist sha512 vectors passed")
    return 0
}
"""
    tmp_vl = REPO_ROOT / "tests" / "_tmp_sha512_nist.vl"
    tmp_vl.write_text(src, encoding="utf-8")
    try:
        res = subprocess.run(
            [str(VELO_EXE), "run", str(tmp_vl)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            env=get_env()
        )
        assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
        assert "PASS: nist sha512 vectors passed" in res.stdout
    finally:
        if tmp_vl.exists():
            tmp_vl.unlink()

def test_sha512_streaming_and_raw_bytes():
    """Verify incremental streaming hash state and raw bytes hashing."""
    src = """use std.crypto
use std.mem
use std.io

act main() -> i32 {
    mut s: Sha512State
    s.buf = null
    sha512_init(@s)
    sha512_update_str(@s, "message ")
    sha512_update_str(@s, "digest ")
    sha512_update_str(@s, "computation")
    let h_stream = sha512_final_hex(@s)

    let h_direct = sha512_hash_str("message digest computation")
    if h_stream != h_direct {
        io.println_str("FAIL: streaming does not match direct hash")
        return 1
    }

    // Verify raw 64-byte digest output
    mut raw_out: @u8 = heap_alloc(64)
    sha512_bytes("message digest computation" as @u8, 26, raw_out)
    let hex_from_raw = bytes_to_hex(raw_out, 64)
    if hex_from_raw != h_direct {
        io.println_str("FAIL: raw bytes digest mismatch")
        heap_free(raw_out)
        return 2
    }
    heap_free(raw_out)

    io.println_str("PASS: streaming and raw bytes passed")
    return 0
}
"""
    tmp_vl = REPO_ROOT / "tests" / "_tmp_sha512_stream.vl"
    tmp_vl.write_text(src, encoding="utf-8")
    try:
        res = subprocess.run(
            [str(VELO_EXE), "run", str(tmp_vl)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            env=get_env()
        )
        assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
        assert "PASS: streaming and raw bytes passed" in res.stdout
    finally:
        if tmp_vl.exists():
            tmp_vl.unlink()

def test_hmac_sha512_rfc4231_vectors():
    """Verify HMAC-SHA512 against all applicable RFC 4231 test vectors."""
    src = """use std.crypto
use std.mem
use std.io

act main() -> i32 {
    // Case 1: 20 bytes 0x0b, "Hi There"
    mut k1: @u8 = heap_alloc(20)
    mut i1: usize = 0
    loop i1 < 20 { k1[i1] = 0x0b as u8; i1 += 1 }
    let mac1 = hmac_sha512_hash(k1, 20, "Hi There" as @u8, 8)
    if mac1 != "87aa7cdea5ef619d4ff0b4241a1d6cb02379f4e2ce4ec2787ad0b30545e17cdedaa833b7d6b8a702038b274eaea3f4e4be9d914eeb61f1702e696c203a126854" {
        io.println_str("FAIL: RFC 4231 Case 1")
        heap_free(k1)
        return 1
    }
    heap_free(k1)

    // Case 2: key "Jefe", "what do ya want for nothing?"
    let mac2 = hmac_sha512_str("Jefe", "what do ya want for nothing?")
    if mac2 != "164b7a7bfcf819e2e395fbe73b56e0a387bd64222e831fd610270cd7ea2505549758bf75c05a994a6d034f65f8f0e6fdcaeab1a34d4a6b4b636e070a38bce737" {
        io.println_str("FAIL: RFC 4231 Case 2")
        return 2
    }

    // Case 3: key 20 bytes 0xaa, data 50 bytes 0xdd
    mut k3: @u8 = heap_alloc(20)
    mut i3: usize = 0
    loop i3 < 20 { k3[i3] = 0xaa as u8; i3 += 1 }
    mut d3: @u8 = heap_alloc(50)
    mut j3: usize = 0
    loop j3 < 50 { d3[j3] = 0xdd as u8; j3 += 1 }
    let mac3 = hmac_sha512_hash(k3, 20, d3, 50)
    if mac3 != "fa73b0089d56a284efb0f0756c890be9b1b5dbdd8ee81a3655f83e33b2279d39bf3e848279a722c806b485a47e67c807b946a337bee8942674278859e13292fb" {
        io.println_str("FAIL: RFC 4231 Case 3")
        heap_free(k3)
        heap_free(d3)
        return 3
    }
    heap_free(k3)
    heap_free(d3)

    // Case 4: key 25 bytes 0x01..0x19, data 50 bytes 0xcd
    mut k4: @u8 = heap_alloc(25)
    mut i4: usize = 0
    loop i4 < 25 { k4[i4] = (i4 + 1) as u8; i4 += 1 }
    mut d4: @u8 = heap_alloc(50)
    mut j4: usize = 0
    loop j4 < 50 { d4[j4] = 0xcd as u8; j4 += 1 }
    let mac4 = hmac_sha512_hash(k4, 25, d4, 50)
    if mac4 != "b0ba465637458c6990e5a8c5f61d4af7e576d97ff94b872de76f8050361ee3dba91ca5c11aa25eb4d679275cc5788063a5f19741120c4f2de2adebeb10a298dd" {
        io.println_str("FAIL: RFC 4231 Case 4")
        heap_free(k4)
        heap_free(d4)
        return 4
    }
    heap_free(k4)
    heap_free(d4)

    // Case 6: key 131 bytes 0xaa (larger than block size 128)
    mut k6: @u8 = heap_alloc(131)
    mut i6: usize = 0
    loop i6 < 131 { k6[i6] = 0xaa as u8; i6 += 1 }
    let d6 = "Test Using Larger Than Block-Size Key - Hash Key First"
    let mac6 = hmac_sha512_hash(k6, 131, d6 as @u8, str.len(d6))
    if mac6 != "80b24263c7c1a3ebb71493c1dd7be8b49b46d1f41b4aeec1121b013783f8f3526b56d037e05f2598bd0fd2215d6a1e5295e64f73f63f0aec8b915a985d786598" {
        io.println_str("FAIL: RFC 4231 Case 6")
        heap_free(k6)
        return 5
    }
    heap_free(k6)

    // Case 7: key 131 bytes 0xaa, data 152 bytes (larger than block size)
    mut k7: @u8 = heap_alloc(131)
    mut i7: usize = 0
    loop i7 < 131 { k7[i7] = 0xaa as u8; i7 += 1 }
    let d7 = "This is a test using a larger than block-size key and a larger than block-size data. The key needs to be hashed before being used by the HMAC algorithm."
    let mac7 = hmac_sha512_hash(k7, 131, d7 as @u8, str.len(d7))
    if mac7 != "e37b6a775dc87dbaa4dfa9f96e5e3ffddebd71f8867289865df5a32d20cdc944b6022cac3c4982b10d5eeb55c3e4de15134676fb6de0446065c97440fa8c6a58" {
        io.println_str("FAIL: RFC 4231 Case 7")
        heap_free(k7)
        return 6
    }
    heap_free(k7)

    io.println_str("PASS: hmac sha512 rfc4231 vectors passed")
    return 0
}
"""
    tmp_vl = REPO_ROOT / "tests" / "_tmp_hmac512_rfc.vl"
    tmp_vl.write_text(src, encoding="utf-8")
    try:
        res = subprocess.run(
            [str(VELO_EXE), "run", str(tmp_vl)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            env=get_env()
        )
        assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
        assert "PASS: hmac sha512 rfc4231 vectors passed" in res.stdout
    finally:
        if tmp_vl.exists():
            tmp_vl.unlink()

def test_hmac_sha512_verification_and_tampering():
    """Verify constant-time HMAC-SHA512 verification and rejection of corruptions."""
    src = """use std.crypto
use std.mem
use std.io

act main() -> i32 {
    let k = "super-secret-key"
    let d = "important authenticated message payload"
    let valid_tag = hmac_sha512_str(k, d)

    // 1. Valid hex string tag
    if !hmac_sha512_verify(k, d, valid_tag) {
        io.println_str("FAIL: valid hex tag rejected")
        return 1
    }

    // 2. Tampered message
    if hmac_sha512_verify(k, "important authenticated message payloae", valid_tag) {
        io.println_str("FAIL: tampered message accepted")
        return 2
    }

    // 3. Tampered key
    if hmac_sha512_verify("super-secret-kex", d, valid_tag) {
        io.println_str("FAIL: tampered key accepted")
        return 3
    }

    // 4. Corrupted first byte of tag
    mut bad_first: @u8 = heap_alloc(129)
    mut i: usize = 0
    loop i < 128 {
        bad_first[i] = valid_tag[i]
        i += 1
    }
    bad_first[128] = 0 as u8
    if bad_first[0] == ('a' as u8) { bad_first[0] = 'b' as u8 } else { bad_first[0] = 'a' as u8 }
    if hmac_sha512_verify(k, d, bad_first as string) {
        io.println_str("FAIL: corrupted first byte accepted")
        heap_free(bad_first)
        return 4
    }
    heap_free(bad_first)

    // 5. Corrupted last byte of tag
    mut bad_last: @u8 = heap_alloc(129)
    mut j: usize = 0
    loop j < 128 {
        bad_last[j] = valid_tag[j]
        j += 1
    }
    bad_last[128] = 0 as u8
    if bad_last[127] == ('0' as u8) { bad_last[127] = '1' as u8 } else { bad_last[127] = '0' as u8 }
    if hmac_sha512_verify(k, d, bad_last as string) {
        io.println_str("FAIL: corrupted last byte accepted")
        heap_free(bad_last)
        return 5
    }
    heap_free(bad_last)

    // 6. Truncated tag (length mismatch)
    if hmac_sha512_verify(k, d, "1234567890abcdef") {
        io.println_str("FAIL: truncated tag accepted")
        return 6
    }

    // 7. Null tag
    if hmac_sha512_verify(k, d, null) {
        io.println_str("FAIL: null tag accepted")
        return 7
    }

    // 8. Raw binary tag verification via hmac_sha512_verify_bytes
    mut raw_tag: @u8 = heap_alloc(64)
    hmac_sha512(k as @u8, str.len(k), d as @u8, str.len(d), raw_tag)
    if !hmac_sha512_verify_bytes(k as @u8, str.len(k), d as @u8, str.len(d), raw_tag, 64) {
        io.println_str("FAIL: raw binary tag rejected")
        heap_free(raw_tag)
        return 8
    }
    // Corrupt one byte in raw tag
    raw_tag[31] = raw_tag[31] ^ (0xFF as u8)
    if hmac_sha512_verify_bytes(k as @u8, str.len(k), d as @u8, str.len(d), raw_tag, 64) {
        io.println_str("FAIL: corrupted raw tag accepted")
        heap_free(raw_tag)
        return 9
    }
    heap_free(raw_tag)

    io.println_str("PASS: hmac sha512 verification tests passed")
    return 0
}
"""
    tmp_vl = REPO_ROOT / "tests" / "_tmp_hmac512_verify.vl"
    tmp_vl.write_text(src, encoding="utf-8")
    try:
        res = subprocess.run(
            [str(VELO_EXE), "run", str(tmp_vl)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            env=get_env()
        )
        assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
        assert "PASS: hmac sha512 verification tests passed" in res.stdout
    finally:
        if tmp_vl.exists():
            tmp_vl.unlink()
