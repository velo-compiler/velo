"""Phase 73.2: Tests asserting fail-closed semantics for crypto_random_bytes, UUID v4/v7,
and crypto random integer/hex utilities under CSPRNG entropy exhaustion.

Security Invariant I73.1:
crypto_random_bytes fails closed (returning bool or string) and never silently degrades
to SplitMix64 or any predictable PRNG.
UUID generators either abort with a named fatal diagnostic or propagate the error via _try variants.
"""
import subprocess
from pathlib import Path
import pytest
from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()


def get_env(extra=None):
    import os
    env = os.environ.copy()
    if cc_dir() not in env.get("PATH", ""):
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    if extra:
        env.update(extra)
    return env


def _require_native():
    if not VELO_EXE.exists():
        pytest.skip("bin/velo not built")


def run_velo(args, extra_env=None):
    return subprocess.run(
        [str(VELO_EXE)] + args,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(extra_env),
        timeout=60,
    )


def test_crypto_random_bytes_normal(tmp_path):
    """Under normal conditions, crypto_random_bytes succeeds and populates buffer."""
    _require_native()
    src = tmp_path / "test_normal.vl"
    src.write_text("""use std.crypto
use std.io
use std.mem

act main() -> i32 {
    mut buf: @u8 = heap_alloc(16)
    let res = crypto_random_bytes(buf, 16)
    if !res.ok {
        io.println("FAIL: returned err")
        heap_free(buf)
        return 1
    }
    mut sum: u32 = 0
    mut i: usize = 0
    loop i < 16 {
        sum += buf[i] as u32
        i += 1
    }
    heap_free(buf)
    if sum == 0 {
        io.println("FAIL: all zeroes")
        return 2
    }
    io.println("PASS: normal crypto_random_bytes")
    return 0
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode == 0, f"Failed: {res.stderr}\n{res.stdout}"
    assert "PASS: normal crypto_random_bytes" in res.stdout


def test_crypto_random_bytes_failclosed_env(tmp_path):
    """Under VELO_FAIL_ENTROPY=1, crypto_random_bytes returns error and zeros the buffer."""
    _require_native()
    src = tmp_path / "test_failclosed.vl"
    src.write_text("""use std.crypto
use std.io
use std.mem

act main() -> i32 {
    mut buf: @u8 = heap_alloc(16)
    // Pre-fill buffer with non-zero canary values
    buf[0] = 0xAA as u8
    buf[1] = 0xBB as u8
    buf[15] = 0xCC as u8

    let res = crypto_random_bytes(buf, 16)
    if res.ok {
        io.println("FAIL: expected crypto_random_bytes to fail closed")
        heap_free(buf)
        return 1
    }

    io.println("ERR: " + res.err)

    // Verify buffer was scrubbed/zeroed and NOT filled with SplitMix64 fallback
    if buf[0] != (0 as u8) or buf[1] != (0 as u8) or buf[15] != (0 as u8) {
        io.println("FAIL: buffer not zeroed on failure")
        heap_free(buf)
        return 2
    }
    heap_free(buf)
    io.println("PASS: fail-closed zeroed")
    return 0
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)], extra_env={"VELO_FAIL_ENTROPY": "1"})
    assert res.returncode == 0, f"Failed: {res.stderr}\n{res.stdout}"
    assert "ERR: OS entropy source unavailable (CSPRNG failure)" in res.stdout
    assert "PASS: fail-closed zeroed" in res.stdout


def test_crypto_random_bytes_null_buffer(tmp_path):
    """Passing a null buffer fails closed with a clear diagnostic."""
    _require_native()
    src = tmp_path / "test_null_buf.vl"
    src.write_text("""use std.crypto
use std.io

act main() -> i32 {
    let res = crypto_random_bytes(null, 16)
    if res.ok {
        io.println("FAIL: expected null buffer to fail")
        return 1
    }
    io.println("ERR: " + res.err)
    return 0
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode == 0, f"Failed: {res.stderr}\n{res.stdout}"
    assert "ERR: null buffer passed to crypto_random_bytes" in res.stdout


def test_uuid_v4_fatal_abort_on_entropy_failure(tmp_path):
    """uuid_v4() aborts with named fatal error when entropy fails."""
    _require_native()
    src = tmp_path / "test_u4_fatal.vl"
    src.write_text("""use std.uuid

act main() -> i32 {
    let u = uuid_v4()
    return 0
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)], extra_env={"VELO_FAIL_ENTROPY": "1"})
    assert res.returncode != 0
    assert "Velo Fatal Error: uuid_v4: OS entropy source failed during UUID generation" in res.stderr


def test_uuid_v4_try_propagates_on_entropy_failure(tmp_path):
    """uuid_v4_try() propagates error without crashing when entropy fails."""
    _require_native()
    src = tmp_path / "test_u4_try.vl"
    src.write_text("""use std.uuid
use std.io

act main() -> i32 {
    let res = uuid_v4_try()
    if res.ok {
        io.println("FAIL: expected uuid_v4_try to fail")
        return 1
    }
    io.println("UUID_V4_TRY_ERR: " + res.err)
    return 0
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)], extra_env={"VELO_FAIL_ENTROPY": "1"})
    assert res.returncode == 0, f"Failed: {res.stderr}\n{res.stdout}"
    assert "UUID_V4_TRY_ERR: OS entropy source unavailable (CSPRNG failure)" in res.stdout


def test_uuid_v7_fatal_abort_on_entropy_failure(tmp_path):
    """uuid_v7() aborts with named fatal error when entropy fails."""
    _require_native()
    src = tmp_path / "test_u7_fatal.vl"
    src.write_text("""use std.uuid

act main() -> i32 {
    let u = uuid_v7()
    return 0
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)], extra_env={"VELO_FAIL_ENTROPY": "1"})
    assert res.returncode != 0
    assert "Velo Fatal Error: uuid_v7: OS entropy source failed during UUID generation" in res.stderr


def test_uuid_v7_at_fatal_abort_on_entropy_failure(tmp_path):
    """uuid_v7_at() aborts with named fatal error when entropy fails."""
    _require_native()
    src = tmp_path / "test_u7_at_fatal.vl"
    src.write_text("""use std.uuid

act main() -> i32 {
    let u = uuid_v7_at(1714567890123 as u64)
    return 0
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)], extra_env={"VELO_FAIL_ENTROPY": "1"})
    assert res.returncode != 0
    assert "Velo Fatal Error: uuid_v7_at: OS entropy source failed during UUID generation" in res.stderr


def test_uuid_v7_try_propagates_on_entropy_failure(tmp_path):
    """uuid_v7_try() and uuid_v7_at_try() propagate error when entropy fails."""
    _require_native()
    src = tmp_path / "test_u7_try.vl"
    src.write_text("""use std.uuid
use std.io

act main() -> i32 {
    let r1 = uuid_v7_try()
    if r1.ok {
        io.println("FAIL: expected uuid_v7_try to fail")
        return 1
    }
    io.println("UUID_V7_TRY_ERR: " + r1.err)

    let r2 = uuid_v7_at_try(1714567890123 as u64)
    if r2.ok {
        io.println("FAIL: expected uuid_v7_at_try to fail")
        return 2
    }
    io.println("UUID_V7_AT_TRY_ERR: " + r2.err)
    return 0
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)], extra_env={"VELO_FAIL_ENTROPY": "1"})
    assert res.returncode == 0, f"Failed: {res.stderr}\n{res.stdout}"
    assert "UUID_V7_TRY_ERR: OS entropy source unavailable (CSPRNG failure)" in res.stdout
    assert "UUID_V7_AT_TRY_ERR: OS entropy source unavailable (CSPRNG failure)" in res.stdout


def test_crypto_random_u32_fatal_on_entropy_failure(tmp_path):
    """crypto_random_u32() aborts fatally when entropy fails."""
    _require_native()
    src = tmp_path / "test_u32_fatal.vl"
    src.write_text("""use std.crypto

act main() -> i32 {
    let v = crypto_random_u32()
    return 0
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)], extra_env={"VELO_FAIL_ENTROPY": "1"})
    assert res.returncode != 0
    assert "Velo Fatal Error: crypto_random_u32: OS entropy source unavailable" in res.stderr


def test_crypto_random_u64_fatal_on_entropy_failure(tmp_path):
    """crypto_random_u64() aborts fatally when entropy fails."""
    _require_native()
    src = tmp_path / "test_u64_fatal.vl"
    src.write_text("""use std.crypto

act main() -> i32 {
    let v = crypto_random_u64()
    return 0
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)], extra_env={"VELO_FAIL_ENTROPY": "1"})
    assert res.returncode != 0
    assert "Velo Fatal Error: crypto_random_u64: OS entropy source unavailable" in res.stderr


def test_crypto_random_hex_fatal_on_entropy_failure(tmp_path):
    """crypto_random_hex() aborts fatally when entropy fails."""
    _require_native()
    src = tmp_path / "test_hex_fatal.vl"
    src.write_text("""use std.crypto

act main() -> i32 {
    let s = crypto_random_hex(16)
    return 0
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)], extra_env={"VELO_FAIL_ENTROPY": "1"})
    assert res.returncode != 0
    assert "Velo Fatal Error: crypto_random_hex: OS entropy source unavailable" in res.stderr


def test_crypto_random_try_utilities_propagate(tmp_path):
    """_try variants propagate error under entropy failure without aborting."""
    _require_native()
    src = tmp_path / "test_try_utils.vl"
    src.write_text("""use std.crypto
use std.io

act main() -> i32 {
    let r1 = crypto_random_u32_try()
    if r1.ok {
        io.println("FAIL: expected crypto_random_u32_try to fail")
        return 1
    }
    io.println("U32_ERR: " + r1.err)

    let r2 = crypto_random_u64_try()
    if r2.ok {
        io.println("FAIL: expected crypto_random_u64_try to fail")
        return 2
    }
    io.println("U64_ERR: " + r2.err)

    let r3 = crypto_random_hex_try(16)
    if r3.ok {
        io.println("FAIL: expected crypto_random_hex_try to fail")
        return 3
    }
    io.println("HEX_ERR: " + r3.err)

    return 0
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)], extra_env={"VELO_FAIL_ENTROPY": "1"})
    assert res.returncode == 0, f"Failed: {res.stderr}\n{res.stdout}"
    assert "U32_ERR: OS entropy source unavailable (CSPRNG failure)" in res.stdout
    assert "U64_ERR: OS entropy source unavailable (CSPRNG failure)" in res.stdout
    assert "HEX_ERR: OS entropy source unavailable (CSPRNG failure)" in res.stdout


def test_in_process_entropy_failure_injection(tmp_path):
    """crypto_inject_entropy_failure dynamically controls CSPRNG failure in-process."""
    _require_native()
    src = tmp_path / "test_inject.vl"
    src.write_text("""use std.crypto
use std.io
use std.mem

act main() -> i32 {
    // Normal initially
    let r1 = crypto_random_u32_try()
    if !r1.ok {
        io.println("FAIL: r1 not ok")
        return 1
    }

    // Inject failure
    crypto_inject_entropy_failure(true)
    let r2 = crypto_random_u32_try()
    if r2.ok {
        io.println("FAIL: r2 succeeded when failure injected")
        return 2
    }

    // Restore
    crypto_inject_entropy_failure(false)
    let r3 = crypto_random_u32_try()
    if !r3.ok {
        io.println("FAIL: r3 not ok after restore")
        return 3
    }

    io.println("PASS: dynamic injection toggle")
    return 0
}
""", encoding="utf-8")
    res = run_velo(["run", str(src)])
    assert res.returncode == 0, f"Failed: {res.stderr}\n{res.stdout}"
    assert "PASS: dynamic injection toggle" in res.stdout


def test_explicit_unsafe_fallback_bytes(tmp_path):
    """crypto_unsafe_fallback_bytes fills buffer deterministically without CSPRNG."""
    _require_native()
    src = tmp_path / "test_unsafe_fb.vl"
    src.write_text("""use std.crypto
use std.io
use std.mem

act main() -> i32 {
    mut buf: @u8 = heap_alloc(16)
    crypto_unsafe_fallback_bytes(buf, 16)
    mut sum: u32 = 0
    mut i: usize = 0
    loop i < 16 {
        sum += buf[i] as u32
        i += 1
    }
    heap_free(buf)
    if sum == 0 {
        io.println("FAIL: fallback bytes all zeroes")
        return 1
    }
    io.println("PASS: explicit fallback fill")
    return 0
}
""", encoding="utf-8")
    # Even under VELO_FAIL_ENTROPY=1, explicit fallback should work because it doesn't touch OS entropy
    res = run_velo(["run", str(src)], extra_env={"VELO_FAIL_ENTROPY": "1"})
    assert res.returncode == 0, f"Failed: {res.stderr}\n{res.stdout}"
    assert "PASS: explicit fallback fill" in res.stdout
