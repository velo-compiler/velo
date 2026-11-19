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

def test_std_async_poller():
    test_vl = REPO_ROOT / "std" / "tests" / "async" / "poller_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "OK: std.async.poller tests passed" in res.stdout

def test_std_async_loop():
    test_vl = REPO_ROOT / "std" / "tests" / "async" / "loop_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "OK: std.async.loop tests passed" in res.stdout

def test_std_async_iocp():
    test_vl = REPO_ROOT / "std" / "tests" / "async" / "iocp_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "OK: std.async.iocp tests passed" in res.stdout

def test_std_async_tcp():
    test_vl = REPO_ROOT / "std" / "tests" / "async" / "tcp_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "OK: std.async.tcp echo test passed" in res.stdout

def test_std_async_module_import():
    test_vl = REPO_ROOT / "std" / "tests" / "async_module_import_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "OK: std.async module import test passed" in res.stdout


def test_poller_variants_expose_the_same_public_api():
    """All poller variants (windows, linux, macos, posix fallback) must expose identical lifecycle acts."""
    import re
    pattern = re.compile(r"^act (poller_\w+)\(", re.MULTILINE)

    def poller_acts(name):
        path = REPO_ROOT / "std" / "async" / f"poller_{name}.vl"
        return set(pattern.findall(path.read_text(encoding="utf-8")))

    expected_acts = {
        "poller_init",
        "poller_free",
        "poller_ensure_cap",
        "poller_add",
        "poller_modify",
        "poller_remove",
        "poller_poll",
    }
    for variant in ("windows", "linux", "macos", "posix"):
        acts = poller_acts(variant)
        assert expected_acts.issubset(acts), f"poller_{variant}.vl missing acts: {expected_acts - acts}"


def test_linux_poller_uses_epoll():
    """Phase 70 / Task 70.4: poller_linux.vl must be powered by epoll(7), not poll(2)."""
    text = (REPO_ROOT / "std" / "async" / "poller_linux.vl").read_text(encoding="utf-8")
    assert "epoll_create" in text, "poller_linux.vl must call epoll_create/epoll_create1"
    assert "epoll_ctl" in text, "poller_linux.vl must call epoll_ctl"
    assert "epoll_wait" in text, "poller_linux.vl must call epoll_wait"
    assert "extern act poll(" not in text, "poller_linux.vl must not declare poll(2)"


def test_posix_fallback_poller_uses_poll():
    """Phase 70 / Task 70.4: poller_posix.vl preserves generic poll(2) fallback for unknown POSIX targets."""
    text = (REPO_ROOT / "std" / "async" / "poller_posix.vl").read_text(encoding="utf-8")
    assert "extern act poll(" in text, "poller_posix.vl must use poll(2)"


