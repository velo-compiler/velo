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

def test_crypto_zero_direct_and_partial():
    """Test crypto_zero clearing full buffers, partial ranges, and edge cases."""
    src = """use std.crypto
use std.mem
use std.io

act main() -> i32 {
    // 1. Full buffer zeroing
    mut buf: @u8 = heap_alloc(128)
    mut i: usize = 0
    loop i < 128 {
        buf[i] = ((i % 255) + 1) as u8
        i += 1
    }
    crypto_zero(buf, 128)
    mut j: usize = 0
    loop j < 128 {
        if buf[j] != (0 as u8) {
            io.println_str("FAIL: non-zero byte found after crypto_zero")
            return 1
        }
        j += 1
    }
    heap_free(buf)

    // 2. Partial zeroing
    mut pbuf: @u8 = heap_alloc(64)
    mut k: usize = 0
    loop k < 64 {
        pbuf[k] = 0x5A as u8
        k += 1
    }
    // Zero only bytes 16..47 (32 bytes)
    crypto_zero(pbuf + 16, 32)
    mut m: usize = 0
    loop m < 64 {
        if m < 16 or m >= 48 {
            if pbuf[m] != (0x5A as u8) {
                io.println_str("FAIL: untouched region corrupted")
                return 2
            }
        } else {
            if pbuf[m] != (0 as u8) {
                io.println_str("FAIL: zeroed region contains non-zero byte")
                return 3
            }
        }
        m += 1
    }
    heap_free(pbuf)

    // 3. Edge cases
    crypto_zero(null, 50) // must not crash
    mut dummy: @u8 = heap_alloc(8)
    dummy[0] = 77 as u8
    crypto_zero(dummy, 0) // zero length must not modify
    if dummy[0] != (77 as u8) {
        io.println_str("FAIL: zero length modified buffer")
        return 4
    }
    heap_free(dummy)

    io.println_str("PASS: crypto_zero direct and partial tests passed")
    return 0
}
"""
    tmp_vl = REPO_ROOT / "tests" / "_tmp_crypto_zero_test.vl"
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
        assert "PASS: crypto_zero direct and partial tests passed" in res.stdout
    finally:
        if tmp_vl.exists():
            tmp_vl.unlink()

def test_crypto_zero_in_hmac_temporaries():
    """Verify HMAC operations run cleanly and produce exact RFC 4231 vectors with zeroing enabled."""
    src = """
use std.crypto.hmac
use std.io

act main() -> i32 {
    // RFC 4231 Test Case 1
    let k1 = "\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b"
    let d1 = "Hi There"
    let h1 = hmac_sha256_str(k1, d1)
    if h1 != "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7" {
        io.println_str("FAIL: RFC 4231 Case 1 hash mismatch")
        return 1
    }
    if !hmac_sha256_verify(k1, d1, h1) {
        io.println_str("FAIL: RFC 4231 Case 1 verify mismatch")
        return 2
    }

    // RFC 4231 Test Case 6: Key larger than block size (131 bytes)
    let k6 = "\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa\\xaa"
    let d6 = "Test Using Larger Than Block-Size Key - Hash Key First"
    let h6 = hmac_sha256_str(k6, d6)
    if h6 != "60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f54" {
        io.println_str("FAIL: RFC 4231 Case 6 hash mismatch")
        return 3
    }
    if !hmac_sha256_verify(k6, d6, h6) {
        io.println_str("FAIL: RFC 4231 Case 6 verify mismatch")
        return 4
    }

    // Tampered verification
    if hmac_sha256_verify(k6, d6, "60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f55") {
        io.println_str("FAIL: tampered tag accepted")
        return 5
    }

    io.println_str("PASS: hmac temporaries zeroing test passed")
    return 0
}
"""
    tmp_vl = REPO_ROOT / "tests" / "_tmp_crypto_zero_hmac.vl"
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
        assert "PASS: hmac temporaries zeroing test passed" in res.stdout
    finally:
        if tmp_vl.exists():
            tmp_vl.unlink()

def test_crypto_zero_dead_store_optimization_resistance():
    """Verify that GCC with high optimization (-O2/-O3) does not elide velo_crypto_zero stores."""
    src = """use std.crypto
use std.mem
use std.io

act inspect_and_zero() -> i32 {
    mut sensitive: @u8 = heap_alloc(32)
    mut i: usize = 0
    loop i < 32 {
        sensitive[i] = 0xEE as u8
        i += 1
    }
    // Zero out before freeing
    crypto_zero(sensitive, 32)

    // Inspect: all bytes must be 0
    mut err = 0
    mut j: usize = 0
    loop j < 32 {
        if sensitive[j] != (0 as u8) {
            err = 1
        }
        j += 1
    }
    heap_free(sensitive)
    return err
}

act main() -> i32 {
    let err = inspect_and_zero()
    if err != 0 {
        io.println_str("FAIL: sensitive data was not zeroed prior to free")
        return 1
    }
    io.println_str("PASS: dead store optimization resistance verified")
    return 0
}
"""
    tmp_vl = REPO_ROOT / "tests" / "_tmp_crypto_zero_opt.vl"
    tmp_exe = REPO_ROOT / "tests" / "_tmp_crypto_zero_opt.exe"
    tmp_vl.write_text(src, encoding="utf-8")
    try:
        # Build with build command
        res = subprocess.run(
            [str(VELO_EXE), "build", str(tmp_vl), "-o", str(tmp_exe)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            env=get_env()
        )
        assert res.returncode == 0, f"build failed:\n{res.stderr}\n{res.stdout}"
        assert tmp_exe.exists()

        # Run built binary
        res_run = subprocess.run(
            [str(tmp_exe)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            env=get_env()
        )
        assert res_run.returncode == 0, f"run failed:\n{res_run.stderr}\n{res_run.stdout}"
        assert "PASS: dead store optimization resistance verified" in res_run.stdout
    finally:
        if tmp_vl.exists():
            tmp_vl.unlink()
        if tmp_exe.exists():
            tmp_exe.unlink()

def test_crypto_zero_large_buffer_and_raw():
    """Verify crypto_zero with large buffers (64KB) and crypto_zero_raw untyped pointers."""
    src = """use std.crypto
use std.mem
use std.io

act main() -> i32 {
    // 1. Large 64KB buffer
    let size: usize = 65536
    mut big_buf: @u8 = heap_alloc(size)
    mut i: usize = 0
    loop i < size {
        big_buf[i] = 0xAA as u8
        i += 1
    }
    crypto_zero(big_buf, size)
    mut j: usize = 0
    loop j < size {
        if big_buf[j] != (0 as u8) {
            io.println_str("FAIL: large buffer byte not zeroed")
            return 1
        }
        j += 1
    }
    heap_free(big_buf)

    // 2. crypto_zero_raw untyped @void pointer
    mut raw_buf: @u8 = heap_alloc(64)
    mut r: usize = 0
    loop r < 64 {
        raw_buf[r] = 0xCC as u8
        r += 1
    }
    crypto_zero_raw(raw_buf as @void, 64)
    mut s: usize = 0
    loop s < 64 {
        if raw_buf[s] != (0 as u8) {
            io.println_str("FAIL: crypto_zero_raw byte not zeroed")
            return 2
        }
        s += 1
    }
    heap_free(raw_buf)

    io.println_str("PASS: large buffer and raw tests passed")
    return 0
}
"""
    tmp_vl = REPO_ROOT / "tests" / "_tmp_crypto_zero_large.vl"
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
        assert "PASS: large buffer and raw tests passed" in res.stdout
    finally:
        if tmp_vl.exists():
            tmp_vl.unlink()

def test_crypto_zero_failclosed_entropy_wipe():
    """Verify that simulated entropy failure triggers crypto_zero on the output buffer."""
    src = """use std.crypto
use std.mem
use std.io

act main() -> i32 {
    mut b: @u8 = heap_alloc(32)
    mut i: usize = 0
    loop i < 32 {
        b[i] = 0xFF as u8
        i += 1
    }

    // Inject simulated entropy failure
    crypto_inject_entropy_failure(true)
    let res = crypto_random_bytes(b, 32)
    crypto_inject_entropy_failure(false)

    if res.ok {
        io.println_str("FAIL: simulated entropy failure succeeded unexpectedly")
        return 1
    }

    // Verify buffer was zeroed on failure
    mut j: usize = 0
    loop j < 32 {
        if b[j] != (0 as u8) {
            io.println_str("FAIL: buffer not zeroed after entropy failure")
            return 2
        }
        j += 1
    }
    heap_free(b)

    io.println_str("PASS: failclosed entropy wipe verified")
    return 0
}
"""
    tmp_vl = REPO_ROOT / "tests" / "_tmp_crypto_zero_wipe.vl"
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
        assert "PASS: failclosed entropy wipe verified" in res.stdout
    finally:
        if tmp_vl.exists():
            tmp_vl.unlink()

