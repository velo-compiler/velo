"""
Phase 78 / Task 78.3: Standard Library Breadth -- DNS Resolution (std.net / std.net.dns).

Security & Integrity Invariants:
- A/AAAA DNS lookup via system getaddrinfo / getnameinfo on both Windows and POSIX
- Full support for IPv4 (lookup_ipv4), IPv6 (lookup_ipv6), auto-family (lookup), and multi-homed (lookup_all)
- tcp_connect and async_tcp_connect accept hostnames as well as IP literals
- Platform variants (dns_windows.vl, dns_linux.vl, dns_macos.vl) expose identical public APIs
"""

import os
import re
import subprocess
import tempfile
from pathlib import Path
import pytest
from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()


def get_env():
    env = os.environ.copy()
    if cc_dir() not in env.get("PATH", ""):
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return env


def test_std_net_dns_vl_suite():
    """Runs the pure-Velo DNS test suite in std/tests/net/dns_test.vl."""
    test_vl = REPO_ROOT / "std" / "tests" / "net" / "dns_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.net.dns all tests passed" in res.stdout


def test_net_lookup_ipv4_and_ipv6():
    """Verifies that lookup_ipv4 and lookup_ipv6 resolve localhost properly."""
    src = """
use std.net
use std.io

act main() -> i32 {
    let v4 = lookup_ipv4("localhost") or "ERR"
    if v4 != "127.0.0.1" { return 1 }

    let v6 = lookup_ipv6("localhost") or "ERR"
    if v6 != "::1" { return 2 }

    io.println("PASS: v4 and v6 resolution")
    return 0
}
"""
    with tempfile.TemporaryDirectory() as td:
        vl_file = Path(td) / "test_v4_v6.vl"
        vl_file.write_text(src, encoding="utf-8")

        res = subprocess.run(
            [str(VELO_EXE), "run", str(vl_file)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=get_env()
        )
        assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
        assert "PASS: v4 and v6 resolution" in res.stdout


def test_net_lookup_aliased_import():
    """Verifies that 'use std.net :> net' allows calling net.lookup* methods."""
    src = """
use std.net :> net
use std.io

act main() -> i32 {
    let v4 = net.lookup_ipv4("localhost") or "ERR"
    if v4 != "127.0.0.1" { return 1 }

    let any_ip = net.lookup("localhost") or "ERR"
    if any_ip != "127.0.0.1" and any_ip != "::1" { return 2 }

    io.println("PASS: net alias")
    return 0
}
"""
    with tempfile.TemporaryDirectory() as td:
        vl_file = Path(td) / "test_alias.vl"
        vl_file.write_text(src, encoding="utf-8")

        res = subprocess.run(
            [str(VELO_EXE), "run", str(vl_file)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=get_env()
        )
        assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
        assert "PASS: net alias" in res.stdout


def test_net_lookup_invalid_domain_fails():
    """Verifies that unresolvable domains trigger the 'or' fallback."""
    src = """
use std.net
use std.io

act main() -> i32 {
    let res = lookup("definitely-nonexistent-domain-404-xyz.invalid") or "HANDLED"
    if res != "HANDLED" { return 1 }
    io.println("PASS: invalid domain fallback")
    return 0
}
"""
    with tempfile.TemporaryDirectory() as td:
        vl_file = Path(td) / "test_invalid.vl"
        vl_file.write_text(src, encoding="utf-8")

        res = subprocess.run(
            [str(VELO_EXE), "run", str(vl_file)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=get_env()
        )
        assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
        assert "PASS: invalid domain fallback" in res.stdout


def test_tcp_connect_resolves_hostname_and_ip():
    """Verifies that tcp_connect resolves 'localhost' and numeric '127.0.0.1' identically."""
    src = """
use std.net
use std.io

act main() -> i32 {
    let port: u16 = 29543
    let listener = tcp_listen("127.0.0.1", port)
    if listener == null { return 1 }

    // Connect via hostname 'localhost'
    let c1 = tcp_connect("localhost", port)
    if c1 == null { return 2 }
    let s1 = tcp_accept(listener)
    if s1 == null { return 3 }
    socket_close(@s1.sock)
    socket_close(@c1.sock)

    // Connect via numeric IP '127.0.0.1'
    let c2 = tcp_connect("127.0.0.1", port)
    if c2 == null { return 4 }
    let s2 = tcp_accept(listener)
    if s2 == null { return 5 }
    socket_close(@s2.sock)
    socket_close(@c2.sock)

    socket_close(@listener.sock)
    io.println("PASS: tcp_connect resolved both")
    return 0
}
"""
    with tempfile.TemporaryDirectory() as td:
        vl_file = Path(td) / "test_tcp.vl"
        vl_file.write_text(src, encoding="utf-8")

        res = subprocess.run(
            [str(VELO_EXE), "run", str(vl_file)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=get_env()
        )
        assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
        assert "PASS: tcp_connect resolved both" in res.stdout


def test_dns_variants_expose_identical_public_api():
    """Verifies that dns_windows.vl, dns_linux.vl, and dns_macos.vl declare the exact same acts."""
    pattern = re.compile(r"^view act (\w+)\(", re.MULTILINE)

    def get_public_acts(variant):
        path = REPO_ROOT / "std" / "net" / f"dns_{variant}.vl"
        return set(pattern.findall(path.read_text(encoding="utf-8")))

    win = get_public_acts("windows")
    lin = get_public_acts("linux")
    mac = get_public_acts("macos")

    assert win == lin, f"DNS variants disagree: win={win}, lin={lin}"
    assert win == mac, f"DNS variants disagree: win={win}, mac={mac}"
    assert "net_lookup" in win
    assert "net_lookup_ipv4" in win
    assert "net_lookup_ipv6" in win
    assert "net_lookup_all" in win
