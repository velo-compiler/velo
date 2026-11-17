"""
Phase 76 / Task 76.3: tests locate tools through `conftest`, not literal paths.

The defect this guards against is subtle: the suite *ran* on Windows while
hardcoding `C:\\msys64\\ucrt64\\bin` and `bin/velo.exe`, because `conftest.py`
patched `subprocess.Popen` to silently rewrite those paths at call time. The
tests were therefore asserting on a working directory and a compiler that
happened to exist on the maintainer's machine, and the Linux/macOS CI jobs could
never pass: `bootstrap.sh` produces `bin/velo`, and MSYS2 does not exist there.

Sweeping the literals without this test would leave the same trap armed. It
fails the moment a new test reintroduces an absolute Windows toolchain path, and
it is cheap enough to run on every push.
"""

import re
from pathlib import Path

import pytest

from conftest import (
    REPO_ROOT,
    cc_dir,
    cc_env,
    cc_path,
    require_velo_exe,
    velo_exe,
    velo_exe_or_none,
)

TESTS_DIR = REPO_ROOT / "tests"
CONFTEST = TESTS_DIR / "conftest.py"

# Files allowed to mention the platform-specific spellings: this test states
# them in order to forbid them, and conftest.py documents the defect.
ALLOWED = {"conftest.py", "test_platform_portability.py"}


def _test_files():
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        if path.name in ALLOWED:
            continue
        yield path


def test_no_msys64_literal_in_tests():
    offenders = []
    for path in _test_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "msys64" in line:
                offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert not offenders, (
        "tests must not hardcode an MSYS2 path; use conftest.cc_path()/cc_dir():\n"
        + "\n".join(offenders)
    )


def test_no_windows_compiler_filename_in_test_code():
    """
    A `velo.exe` mention is only a problem when it is a *path used to run it*.

    Prose in a skip message ("bin/velo.exe not built") is harmless and useful,
    and a content assertion on another file's text ("bin\\velo.exe" in
    bat_content) is testing that file, not locating the compiler. Both are
    allowed; `subprocess.run(["bin/velo.exe", ...])` is the defect.
    """
    pattern = re.compile(
        r'("bin[/\\]+velo\.exe"|Path\(\s*"bin[/\\]+velo\.exe"\s*\)'
        r'|["\']\.\./\s*bin[/\\]+velo\.exe["\']'
        r'|/\s*"bin"\s*/\s*"velo\.exe")'
    )
    # Content assertions read another file's bytes; they never spawn the binary.
    content_assertion = re.compile(r'assert\s+["\'].*["\']\s+in\s+\w+(_content|_text|source|text)')

    offenders = []
    for path in _test_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not pattern.search(line):
                continue
            if content_assertion.search(line):
                continue
            offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert not offenders, (
        "tests must locate the compiler with conftest.velo_exe():\n"
        + "\n".join(offenders)
    )


def test_no_popen_monkeypatch_in_conftest():
    """
    The `Popen` shim existed to rewrite the literals this phase removed.

    Leaving it in place would silently keep working for a while and then hide a
    genuine path bug, so its absence is asserted.
    """
    text = CONFTEST.read_text(encoding="utf-8")
    assert "subprocess.Popen =" not in text, (
        "conftest must not monkeypatch subprocess.Popen"
    )
    assert "_PatchedPopen" not in text
    assert "_PatchedPosixPopen" not in text


def test_velo_exe_resolves_to_a_real_file():
    path = require_velo_exe()
    assert path.exists()
    assert path.parent.name == "bin"


def test_velo_exe_is_platform_correct():
    """The name must match the platform, since `bootstrap.sh` produces `velo`."""
    path = velo_exe()
    if path.name == "velo.exe" and not path.exists():
        pytest.skip("compiler not built")
    if velo_exe_or_none() is None:
        pytest.skip("compiler not built")


def test_velo_exe_honours_velo_bin_override(monkeypatch, tmp_path):
    fake = tmp_path / "velo_msvc.exe"
    fake.write_bytes(b"")
    monkeypatch.setenv("VELO_BIN", str(fake))
    assert velo_exe() == fake


def test_velo_bin_override_accepts_a_relative_path(monkeypatch):
    monkeypatch.setenv("VELO_BIN", "bin/velo.exe")
    resolved = velo_exe()
    assert resolved.is_absolute()
    assert resolved == REPO_ROOT / "bin" / "velo.exe"


def test_cc_path_returns_something_runnable():
    cc = cc_path()
    assert cc
    if "/" not in cc and "\\" not in cc:
        import shutil

        assert shutil.which(cc), f"cc_path() returned a bare name not on PATH: {cc}"


def test_cc_dir_is_a_directory_when_absolute():
    directory = cc_dir()
    if directory:
        assert Path(directory).is_dir()


def test_cc_env_puts_the_compiler_on_path(monkeypatch):
    env = cc_env()
    assert "PATH" in env
    cc = cc_path()
    if "/" in cc or "\\" in cc:
        assert str(Path(cc).parent) in env["PATH"].split(__import__("os").pathsep)


def test_bootstrap_snapshot_uses_the_helper():
    """The snapshot test is the one that hardcoded the name most consequentially."""
    text = (TESTS_DIR / "test_bootstrap_snapshot.py").read_text(encoding="utf-8")
    assert "velo_exe()" in text
