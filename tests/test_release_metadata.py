"""
Phase 71 / Task 71.2: release version metadata has exactly one source.

Invariant I71.2 from `gaps.md`: "`velo version` derives its version from one
machine-readable source, so the CLI, the manifest parser, and the release
artifact cannot disagree."

The single source is the repository-root `VERSION` file. Three things must
follow it, and this module proves each one:

1. `src/common/version.vl` declares the same string (the compiler's copy).
2. The `velo version` banner is produced from those constants, not a literal.
3. `docs/SPECIFICATION.md` and `SECURITY.md` do not hardcode a full
   `MAJOR.MINOR.PATCH` version that would go stale on the next bump.

These are white-box assertions about source text plus one black-box assertion
about the shipped binary. The black-box row is what actually matters: it runs
`velo version` and compares against `VERSION`.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

from release_meta import (
    REPO_ROOT,
    VERSION_FILE,
    VERSION_VL,
    expected_banner_line,
    read_version,
    read_version_vl,
)

from conftest import velo_exe

VELO_EXE = velo_exe()

SPEC = REPO_ROOT / "docs" / "SPECIFICATION.md"
SECURITY = REPO_ROOT / "SECURITY.md"


def _run_version():
    return subprocess.run(
        [str(VELO_EXE), "version"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_version_file_is_semver():
    """VERSION exists and holds a MAJOR.MINOR.PATCH[-PRE] string."""
    assert VERSION_FILE.exists(), "VERSION must exist at the repository root"
    raw = VERSION_FILE.read_text(encoding="utf-8")
    assert raw == raw.strip() + "\n", "VERSION should be a single newline-terminated line"
    assert re.match(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$", raw.strip())


def test_version_vl_matches_version_file():
    """src/common/version.vl must declare exactly the VERSION file's value."""
    assert read_version_vl() == read_version(), (
        f"src/common/version.vl declares {read_version_vl()!r} but VERSION says "
        f"{read_version()!r}; update both in the same commit"
    )


def test_main_vl_has_no_literal_version():
    """src/main.vl must format VELO_VERSION, never a hardcoded version string."""
    text = (REPO_ROOT / "src" / "main.vl").read_text(encoding="utf-8")
    assert "VELO_VERSION" in text, "src/main.vl must use VELO_VERSION"
    # No bare "Velo v<digit>..." literal may survive in the banner path.
    assert not re.search(r'"Velo v\d', text), (
        "src/main.vl still contains a literal version banner; "
        "the banner must be built from src/common/version.vl"
    )


def test_cli_banner_matches_version_file():
    """Black-box: `velo version` prints exactly the banner derived from VERSION."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo not built")
    res = _run_version()
    assert res.returncode == 0, res.stderr
    first_line = res.stdout.splitlines()[0]
    assert first_line == expected_banner_line(), (
        f"banner {first_line!r} != {expected_banner_line()!r}"
    )


def test_docs_do_not_pin_a_full_patch_version():
    """
    SPECIFICATION.md and SECURITY.md must refer to the major line, not a full
    literal like `2.0.0`, so a version bump is a one-file change.
    """
    version = read_version()
    full = version.split("-")[0]
    for path in (SPEC, SECURITY):
        text = path.read_text(encoding="utf-8")
        assert full not in text, (
            f"{path.name} hardcodes the full version {full!r}; refer to VERSION instead"
        )


def test_version_file_is_staged_by_release_script():
    """scripts/release.py must read VERSION rather than hardcode a version."""
    script = REPO_ROOT / "scripts" / "release.py"
    if not script.exists():
        pytest.skip("scripts/release.py not present yet")
    text = script.read_text(encoding="utf-8")
    assert "VERSION" in text, "release.py must read the VERSION file"
