"""Phase 73.3: Tests asserting constant-time cryptographic memory comparison
and constant-time HMAC-SHA256 verification.

Security Invariant I73.2:
Every MAC/password verification path compares in constant time.
crypto_secure_eq executes in constant time with respect to input byte values
without early-exit shortcuts or length-dependent branches.

SMOKE TEST NOTICE:
The statistical timing assertion in test_crypto_secure_eq_statistical_timing asserts
execution time ratio < 1.5x across 1,000,000 iterations to catch compiler optimization
regressions (e.g. replacing constant-time loop with early-exiting memcmp).
It is a regression smoke test, not a formal hardware-isolated cryptographic proof.
"""
import subprocess
from pathlib import Path
import pytest
from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()


def get_env():
    import os
    env = os.environ.copy()
    if cc_dir() not in env.get("PATH", ""):
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return env


def _require_native():
    if not VELO_EXE.exists():
        pytest.skip("bin/velo not built")


def run_velo(args):
    return subprocess.run(
        [str(VELO_EXE)] + args,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
        timeout=60,
    )


def test_crypto_secure_eq_correctness(tmp_path):
    """crypto_secure_eq correctly identifies matching and non-matching buffers."""
    _require_native()
    src = tmp_path / "test_secure_eq.vl"
    src.write_text("""use std.crypto
use std.io
use std.mem

act main() -> i32 {
    // 1. Zero-length buffers match
    if !crypto_secure_eq(null, null, 0) {
        io.println("FAIL: zero len null")
        return 1
    }

    mut b1: @u8 = heap_alloc(32)
    mut b2: @u8 = heap_alloc(32)
    mut i: usize = 0
    loop i < 32 {
        b1[i] = (i + 1) as u8
        b2[i] = (i + 1) as u8
        i += 1
    }

    // 2. Identical 32-byte buffers match
    if !crypto_secure_eq(b1, b2, 32) {
        io.println("FAIL: identical buffers")
        return 2
    }

    // 3. Difference at each single byte index must return false
    mut pos: usize = 0
    loop pos < 32 {
        let orig = b2[pos]
        b2[pos] = orig ^ (0xFF as u8)
        if crypto_secure_eq(b1, b2, 32) {
            io.println("FAIL: undetected difference at pos")
            return 3
        }
        b2[pos] = orig
        pos += 1
    }

    // 4. Null buffers with len > 0 return false
    if crypto_secure_eq(null, b2, 32) {
        io.println("FAIL: null a accepted")
        return 4
    }
    if crypto_secure_eq(b1, null, 32) {
        io.println("FAIL: null b accepted")
        return 5
    }

    heap_free(b1)
    heap_free(b2)
    io.println("PASS: crypto_secure_eq correctness")
    return 0
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode == 0, f"Failed: {res.stderr}\n{res.stdout}"
    assert "PASS: crypto_secure_eq correctness" in res.stdout


def test_crypto_secure_eq_str_correctness(tmp_path):
    """crypto_secure_eq_str compares strings in constant time."""
    _require_native()
    src = tmp_path / "test_secure_eq_str.vl"
    src.write_text("""use std.crypto
use std.io

act main() -> i32 {
    if !crypto_secure_eq_str("hello", "hello") {
        io.println("FAIL: identical str")
        return 1
    }
    if crypto_secure_eq_str("hello", "world") {
        io.println("FAIL: different str")
        return 2
    }
    if crypto_secure_eq_str("hello", "hell") {
        io.println("FAIL: prefix str")
        return 3
    }
    if crypto_secure_eq_str("hell", "hello") {
        io.println("FAIL: shorter str")
        return 4
    }
    if !crypto_secure_eq_str(null, null) {
        io.println("FAIL: both null")
        return 5
    }
    if crypto_secure_eq_str("a", null) or crypto_secure_eq_str(null, "a") {
        io.println("FAIL: one null")
        return 6
    }
    io.println("PASS: crypto_secure_eq_str")
    return 0
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode == 0, f"Failed: {res.stderr}\n{res.stdout}"
    assert "PASS: crypto_secure_eq_str" in res.stdout


def test_hmac_sha256_verify_rfc_vectors(tmp_path):
    """hmac_sha256_verify validates authentic tags and rejects forgeries."""
    _require_native()
    src = tmp_path / "test_hmac_verify.vl"
    src.write_text("""use std.crypto
use std.io

act main() -> i32 {
    // RFC 4231 Test Case 2:
    // Key: "Jefe"
    // Data: "what do ya want for nothing?"
    // Tag: 5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843
    let key = "Jefe"
    let msg = "what do ya want for nothing?"
    let valid_tag = "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"

    // 1. Authentic tag passes
    if !hmac_sha256_verify(key, msg, valid_tag) {
        io.println("FAIL: valid tag rejected")
        return 1
    }

    // 2. Tampered key fails
    if hmac_sha256_verify("jefe", msg, valid_tag) {
        io.println("FAIL: tampered key accepted")
        return 2
    }

    // 3. Tampered message fails
    if hmac_sha256_verify(key, "what do ya want for nothing!", valid_tag) {
        io.println("FAIL: tampered message accepted")
        return 3
    }

    // 4. Tampered first character in tag fails
    let bad_tag_first = "0bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"
    if hmac_sha256_verify(key, msg, bad_tag_first) {
        io.println("FAIL: bad first char tag accepted")
        return 4
    }

    // 5. Tampered last character in tag fails
    let bad_tag_last = "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3840"
    if hmac_sha256_verify(key, msg, bad_tag_last) {
        io.println("FAIL: bad last char tag accepted")
        return 5
    }

    // 6. Truncated tag fails
    let short_tag = "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec384"
    if hmac_sha256_verify(key, msg, short_tag) {
        io.println("FAIL: short tag accepted")
        return 6
    }

    // 7. Extended tag fails
    let long_tag = "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec384300"
    if hmac_sha256_verify(key, msg, long_tag) {
        io.println("FAIL: long tag accepted")
        return 7
    }

    // 8. Null tag fails
    if hmac_sha256_verify(key, msg, null) {
        io.println("FAIL: null tag accepted")
        return 8
    }

    io.println("PASS: hmac_sha256_verify")
    return 0
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode == 0, f"Failed: {res.stderr}\n{res.stdout}"
    assert "PASS: hmac_sha256_verify" in res.stdout


def test_hmac_sha256_verify_bytes(tmp_path):
    """hmac_sha256_verify_bytes verifies binary MACs in constant time."""
    _require_native()
    src = tmp_path / "test_verify_bytes.vl"
    src.write_text("""use std.crypto
use std.io
use std.mem

act main() -> i32 {
    let key = "my-secret-key"
    let msg = "binary payload data"

    mut digest: @u8 = heap_alloc(32)
    hmac_sha256(key as @u8, str.len(key), msg as @u8, str.len(msg), digest)

    // 1. Matches own computed digest
    if !hmac_sha256_verify_bytes(key as @u8, str.len(key), msg as @u8, str.len(msg), digest, 32) {
        io.println("FAIL: verify_bytes failed")
        heap_free(digest)
        return 1
    }

    // 2. Corrupt one byte
    digest[15] = digest[15] ^ (0x01 as u8)
    if hmac_sha256_verify_bytes(key as @u8, str.len(key), msg as @u8, str.len(msg), digest, 32) {
        io.println("FAIL: corrupted byte accepted")
        heap_free(digest)
        return 2
    }

    // 3. Invalid tag length
    if hmac_sha256_verify_bytes(key as @u8, str.len(key), msg as @u8, str.len(msg), digest, 16) {
        io.println("FAIL: invalid tag length accepted")
        heap_free(digest)
        return 3
    }

    heap_free(digest)
    io.println("PASS: hmac_sha256_verify_bytes")
    return 0
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode == 0, f"Failed: {res.stderr}\n{res.stdout}"
    assert "PASS: hmac_sha256_verify_bytes" in res.stdout


def test_crypto_secure_eq_statistical_timing_smoke_test(tmp_path):
    """Statistical timing assertion: compares 1,000,000 iterations of crypto_secure_eq on

    equal-prefix buffers (differing at last byte) vs differing-first-byte buffers (differing at byte 0).
    Asserts ratio < 1.5x.

    SMOKE TEST NOTICE:
    This test is a regression smoke test to detect compiler early-exit optimizations (e.g. memcmp);
    it is not a formal cryptographic proof of constant-time execution on physical hardware.
    """
    _require_native()
    src = tmp_path / "test_timing.vl"
    src.write_text("""use std.crypto
use std.time
use std.io
use std.mem

act main() -> i32 {
    mut a: @u8 = heap_alloc(64)
    mut b_first: @u8 = heap_alloc(64)
    mut b_last: @u8 = heap_alloc(64)

    mut i: usize = 0
    loop i < 64 {
        a[i] = 0xAA as u8
        b_first[i] = 0xAA as u8
        b_last[i] = 0xAA as u8
        i += 1
    }
    // Differ on byte 0
    b_first[0] = 0x55 as u8
    // Differ on byte 63 (all first 63 bytes identical)
    b_last[63] = 0x55 as u8

    // Warm up instruction cache and branch predictor
    mut w: usize = 0
    loop w < 50000 {
        crypto_secure_eq(a, b_first, 64)
        crypto_secure_eq(a, b_last, 64)
        w += 1
    }

    // Measure 5 alternating blocks of 200,000 iterations (1,000,000 iterations total each)
    // Alternating cancels monotonic clock drift and CPU frequency scaling effects
    let iters_per_block: usize = 200000
    mut total_ns_first: u64 = 0 as u64
    mut total_ns_last: u64 = 0 as u64

    mut round: usize = 0
    loop round < 5 {
        // Measure first-byte difference
        let t0 = time_monotonic_ns()
        mut c1: usize = 0
        loop c1 < iters_per_block {
            crypto_secure_eq(a, b_first, 64)
            c1 += 1
        }
        let t1 = time_monotonic_ns()
        total_ns_first += (t1 - t0)

        // Measure last-byte difference (equal prefix)
        let t2 = time_monotonic_ns()
        mut c2: usize = 0
        loop c2 < iters_per_block {
            crypto_secure_eq(a, b_last, 64)
            c2 += 1
        }
        let t3 = time_monotonic_ns()
        total_ns_last += (t3 - t2)

        round += 1
    }

    heap_free(a)
    heap_free(b_first)
    heap_free(b_last)

    io.println("TIMING: first_ns={total_ns_first}, last_ns={total_ns_last}")
    return 0
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode == 0, f"Failed: {res.stderr}\n{res.stdout}"
    assert "TIMING:" in res.stdout

    # Parse timing output
    for line in res.stdout.splitlines():
        if "TIMING:" in line:
            parts = line.split("TIMING:")[1].strip().split(",")
            first_ns = int(parts[0].split("=")[1])
            last_ns = int(parts[1].split("=")[1])
            ratio = max(first_ns, last_ns) / min(first_ns, last_ns)
            print(f"Timing smoke test: first={first_ns}ns, last={last_ns}ns, ratio={ratio:.3f}")
            assert ratio < 1.5, (
                f"Statistical timing assertion failed: ratio {ratio:.3f} >= 1.5x "
                f"(differing-first={first_ns}ns, equal-prefix-differing-last={last_ns}ns). "
                f"Potential compiler early-exit optimization detected."
            )
            break
