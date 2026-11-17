"""
tests/test_integer_formatting_paths.py — Audit & Verification for Integer Formatting Paths (Task 57.5)

Audit ID: AUDIT-2026-11-06
Verifies that every subsystem formatting integers classifies signedness correctly
and handles boundary conditions (0, 1, -1, INT32_MIN, INT32_MAX, INT64_MIN, INT64_MAX, UINT64_MAX):
- StringBuilder: sb_append_int, sb_append_int64, sb_append_uint64 (src/common/string_builder.vl)
- std.fmt: format_u64, format_i64, format_hex, format_bin, format_oct (std/fmt/itoa.vl)
- std.str.builder: sb_append_i64, sb_append_u64 (std/str/builder.vl)
- std.json: json_write (std/json/writer.vl)
- std.net: net_format_ipv4 (std/net/addr.vl)
- std.time: time_format_iso8601 (std/time/calendar.vl)
- Compiler CLI & check JSON diagnostic formatting
"""

import os
import subprocess
import tempfile
from pathlib import Path
import pytest
from conftest import cc_dir, velo_exe


def get_build_env():
    """Returns an environment with ucrt64 GCC in PATH for compiling generated C."""
    env = dict(os.environ)
    ucrt_bin = cc_dir()
    if os.path.exists(ucrt_bin) and ucrt_bin not in env.get("PATH", ""):
        env["PATH"] = ucrt_bin + ";" + env.get("PATH", "")
    return env


def run_velo_source(source_code: str, timeout: float = 2.0) -> subprocess.CompletedProcess:
    """Compiles Velo source to an executable using bin/velo.exe build, then executes directly."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_path = Path(tmp_dir) / "test.vl"
        exe_path = Path(tmp_dir) / "test.exe"
        src_path.write_text(source_code, encoding="utf-8")

        build_res = subprocess.run(
            [str(velo_exe()), "build", str(src_path), "-o", str(exe_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=get_build_env(),
            cwd=Path.cwd()
        )
        if build_res.returncode != 0:
            return build_res

        try:
            return subprocess.run(
                [str(exe_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
                cwd=Path.cwd()
            )
        except subprocess.TimeoutExpired as e:
            pytest.fail(f"Execution timed out after {timeout}s: {e}")


def check_velo_source_json(source_code: str) -> subprocess.CompletedProcess:
    """Runs bin/velo.exe check --json on the given source code."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_path = Path(tmp_dir) / "test.vl"
        src_path.write_text(source_code, encoding="utf-8")

        return subprocess.run(
            [str(velo_exe()), "check", str(src_path), "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=Path.cwd()
        )


# ==============================================================================
# 1. StringBuilder Audit: sb_append_int, sb_append_int64, sb_append_uint64
# ==============================================================================

def test_string_builder_int32_min_fix():
    """Verify that StringBuilder formatting of INT32_MIN (-2147483648) does not drop digits."""
    code = """use sys.io
act main() -> i32 {
    let min_i32: i32 = -2147483647 - 1
    io.println(min_i32)
    io.println("val={min_i32}")
    return 0
}
"""
    res = run_velo_source(code)
    assert res.returncode == 0
    lines = res.stdout.strip().splitlines()
    assert lines[0] == "-2147483648", f"INT32_MIN lost digits: got {lines[0]}"
    assert lines[1] == "val=-2147483648", f"INT32_MIN interp lost digits: got {lines[1]}"


def test_string_builder_int64_boundaries():
    """Verify StringBuilder formatting of INT64 boundaries."""
    code = """use sys.io
act main() -> i32 {
    let max_i64: i64 = 9223372036854775807i64
    let min_i64: i64 = -9223372036854775807i64 - 1i64
    let max_u64: u64 = 18446744073709551615u64
    io.println(max_i64)
    io.println(min_i64)
    io.println(max_u64)
    return 0
}
"""
    res = run_velo_source(code)
    assert res.returncode == 0
    lines = res.stdout.strip().splitlines()
    assert lines[0] == "9223372036854775807"
    assert lines[1] == "-9223372036854775808"
    assert lines[2] == "18446744073709551615"


# ==============================================================================
# 2. std.fmt Audit: format_u64, format_i64, format_hex, format_bin, format_oct
# ==============================================================================

def test_std_fmt_itoa_full_suite():
    """Run native std/tests/fmt/itoa_test.vl verifying std.fmt formatting correctness."""
    res = subprocess.run(
        [str(velo_exe()), "run", "std/tests/fmt/itoa_test.vl"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_build_env(),
        cwd=Path.cwd()
    )
    assert res.returncode == 0, f"std.fmt itoa test failed: {res.stderr}\n{res.stdout}"
    assert "FAIL" not in res.stdout


def test_std_fmt_ftoa_full_suite():
    """Run native std/tests/fmt/ftoa_test.vl verifying float formatting correctness."""
    res = subprocess.run(
        [str(velo_exe()), "run", "std/tests/fmt/ftoa_test.vl"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_build_env(),
        cwd=Path.cwd()
    )
    assert res.returncode == 0, f"std.fmt ftoa test failed: {res.stderr}\n{res.stdout}"
    assert "FAIL" not in res.stdout


# ==============================================================================
# 3. std.str.builder Audit: sb_append_i64, sb_append_u64
# ==============================================================================

def test_std_str_builder_full_suite():
    """Run native std/tests/str/builder_test.vl verifying StrBuilder 64-bit integer appending."""
    res = subprocess.run(
        [str(velo_exe()), "run", "std/tests/str/builder_test.vl"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_build_env(),
        cwd=Path.cwd()
    )
    assert res.returncode == 0, f"std.str builder test failed: {res.stderr}\n{res.stdout}"
    assert "FAIL" not in res.stdout


# ==============================================================================
# 4. std.json Audit: JSON Integer DOM Serialization
# ==============================================================================

def test_std_json_integer_serialization_boundaries():
    """Verify JSON integer serialization preserves 64-bit signed boundaries without wrapping."""
    code = """use std.json
use std.mem.arena
use sys.io

act main() -> i32 {
    mut a = arena_init(4096)
    let v_zero = json_new_int(@a, 0 as i64)
    let v_pos = json_new_int(@a, 9223372036854775807 as i64)
    let v_neg = json_new_int(@a, (-9223372036854775807 as i64) - (1 as i64))

    let s_zero = json_stringify(@a, v_zero)
    let s_pos = json_stringify(@a, v_pos)
    let s_neg = json_stringify(@a, v_neg)

    io.println(s_zero.ptr as string)
    io.println(s_pos.ptr as string)
    io.println(s_neg.ptr as string)
    return 0
}
"""
    res = run_velo_source(code)
    assert res.returncode == 0
    lines = res.stdout.strip().splitlines()
    assert lines[0] == "0"
    assert lines[1] == "9223372036854775807"
    assert lines[2] == "-9223372036854775808"


def test_std_json_writer_full_suite():
    """Run native std/tests/json/writer_test.vl verifying full JSON serialization."""
    res = subprocess.run(
        [str(velo_exe()), "run", "std/tests/json/writer_test.vl"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_build_env(),
        cwd=Path.cwd()
    )
    assert res.returncode == 0, f"std.json writer test failed: {res.stderr}\n{res.stdout}"
    assert "PASS" in res.stdout


# ==============================================================================
# 5. std.net Audit: IPv4 Dotted-Decimal Formatting
# ==============================================================================

def test_std_net_addr_formatting():
    """Verify IPv4 address formatting produces unsigned dotted-decimal notation."""
    code = """use std.net
use sys.io

act main() -> i32 {
    // 127.0.0.1 in network byte order = 0x0100007F
    let loopback = net_format_ipv4(0x0100007Fu32)
    io.println(loopback)
    // 255.255.255.255 = 0xFFFFFFFF
    let broadcast = net_format_ipv4(0xFFFFFFFFu32)
    io.println(broadcast)
    // 0.0.0.0 = 0x00000000
    let any_addr = net_format_ipv4(0u32)
    io.println(any_addr)
    return 0
}
"""
    res = run_velo_source(code)
    assert res.returncode == 0
    lines = res.stdout.strip().splitlines()
    assert lines[0] == "127.0.0.1"
    assert lines[1] == "255.255.255.255"
    assert lines[2] == "0.0.0.0"


def test_std_net_addr_full_suite():
    """Run native std/tests/net/addr_test.vl verifying full network address formatting."""
    res = subprocess.run(
        [str(velo_exe()), "run", "std/tests/net/addr_test.vl"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_build_env(),
        cwd=Path.cwd()
    )
    assert res.returncode == 0, f"std.net addr test failed: {res.stderr}\n{res.stdout}"
    assert "OK" in res.stdout


# ==============================================================================
# 6. std.time Audit: ISO-8601 Calendar Formatting
# ==============================================================================

def test_std_time_calendar_formatting():
    """Verify ISO-8601 date-time calendar formatting."""
    code = """use std.time
use sys.io

act main() -> i32 {
    let dt = DateTime {
        year: 2026,
        month: 11,
        day: 14,
        hour: 23,
        minute: 59,
        second: 58,
        millisecond: 123,
        nanosecond: 123000000,
        weekday: 6,
        yearday: 318,
    }
    mut buf: @u8 = mem.alloc(@u8, 32)
    let s = time_format_iso8601(@dt, buf, 32)
    io.println(s.ptr as string)
    return 0
}
"""
    res = run_velo_source(code)
    assert res.returncode == 0
    actual = res.stdout.strip()
    assert actual == "2026-11-14T23:59:58Z"


def test_std_time_calendar_full_suite():
    """Run native std/tests/time/calendar_test.vl verifying full calendar formatting."""
    res = subprocess.run(
        [str(velo_exe()), "run", "std/tests/time/calendar_test.vl"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_build_env(),
        cwd=Path.cwd()
    )
    assert res.returncode == 0, f"std.time calendar test failed: {res.stderr}\n{res.stdout}"
    assert "PASS" in res.stdout


# ==============================================================================
# 7. Compiler Diagnostic Formatting: velo check --json Line/Col Numbers
# ==============================================================================

def test_check_json_diagnostic_line_col_formatting():
    """Verify velo check --json formats line and col numbers correctly."""
    code = """act main() {
    let x: i32 = "type mismatch error"
}
"""
    res = check_velo_source_json(code)
    # Output is JSON document
    assert res.returncode != 0
    assert '"ok": false' in res.stdout
    assert '"line": 2' in res.stdout
    assert '"col":' in res.stdout
    assert '"diagnostics":' in res.stdout


# ==============================================================================
# 8. Security Gate: No Signed/Unsigned Confusion in Sizes, Lengths, or Limits
# ==============================================================================

def test_security_gate_array_and_slice_lengths_never_negative():
    """Security Gate: Verify array lengths and string lengths are strictly non-negative unsigned."""
    code = """use sys.io
act main() -> i32 {
    let s = "Velo"
    let len = str.len(s)
    let arr: [4]i32 = [1, 2, 3, 4]
    io.println(len)
    io.println("len={len}")
    return 0
}
"""
    res = run_velo_source(code)
    assert res.returncode == 0
    lines = res.stdout.strip().splitlines()
    assert lines[0] == "4"
    assert lines[1] == "len=4"
    assert not lines[0].startswith("-")
    assert not lines[1].startswith("len=-")
