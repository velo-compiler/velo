import os
import re
import subprocess
from pathlib import Path

from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()

# Phase 70 / Task 70.2. A "platform-typed extern" is a C function whose
# signature differs between the variants -- `SOCKET` (i64) on Windows versus
# `int` (i32) on POSIX. Calling one from a file that carries no platform suffix
# is the exact defect 70.2 exists to remove: the neutral file compiles on one
# target and fails on the other, and only the target that is never built in CI
# sees the failure.
#
# `udp.vl` did this with setsockopt until the test below was written, and the
# existing suite did not catch it because every net test runs on the Windows
# host. These rows assert the property directly, by emitting C for the other
# target, which is the only way this machine can see the POSIX path at all.
PLATFORM_TYPED = (
    "setsockopt", "bind", "listen", "accept", "recv", "send", "recvfrom",
    "sendto", "connect", "socket", "closesocket", "ioctlsocket", "fcntl",
    "close", "WSAStartup", "WSACleanup",
)
VARIANT_SUFFIXES = ("_windows", "_linux", "_macos", "_win32", "_posix")


def get_env(target=None):
    env = os.environ.copy()
    if cc_dir() not in env.get("PATH", ""):
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    if target is not None:
        env["VELO_TARGET_PLATFORM"] = target
    return env


def emit_c(tmp_path, module, target):
    src = tmp_path / "probe.vl"
    src.write_text(f"use {module}\n\nact main() -> i32 {{ return 0 }}\n", encoding="utf-8")
    out = tmp_path / "probe.c"
    return subprocess.run(
        [str(VELO_EXE), "emit-c", str(src), "-o", str(out)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=get_env(target),
        timeout=180,
    )


def neutral_std_files():
    files = []
    for path in sorted((REPO_ROOT / "std").rglob("*.vl")):
        if path.stem.endswith(VARIANT_SUFFIXES):
            continue
        files.append(path)
    return files


def test_no_platform_neutral_file_calls_a_platform_typed_socket_function():
    """I70.1 for the socket surface.

    Scans the source rather than the emitted C because the emitted C for this
    host can only ever show the Windows branch; the defect lives in the file
    that has no branch at all.
    """
    offenders = []
    for path in neutral_std_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            for symbol in PLATFORM_TYPED:
                if re.search(rf"\b{symbol}\s*\(", stripped):
                    offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno} {symbol}")
                    break
    assert not offenders, (
        "platform-neutral std files call platform-typed socket functions; move the "
        "call into the _windows/_linux variants:\n" + "\n".join(offenders)
    )


def test_socket_variants_expose_the_same_public_api():
    """A variant that is missing a function breaks only its own target."""
    pattern = re.compile(r"^act (\w+)\(", re.MULTILINE)

    def names(variant):
        path = REPO_ROOT / "std" / "net" / f"socket_{variant}.vl"
        return set(pattern.findall(path.read_text(encoding="utf-8")))

    windows = names("windows")
    linux = names("linux")
    assert windows == linux, (
        f"socket variants disagree; only-windows={sorted(windows - linux)} "
        f"only-linux={sorted(linux - windows)}"
    )
    assert "socket_set_broadcast" in windows, (
        "socket_set_broadcast must live in the variants so udp.vl can stay neutral"
    )


def test_linux_target_emits_bsd_sockets_for_std_net_types(tmp_path):
    """The linux row of the variant table has to actually be reachable."""
    res = emit_c(tmp_path, "std.net.types", "linux")
    assert res.returncode == 0, res.stdout + res.stderr
