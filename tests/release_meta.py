"""
Release metadata helpers shared by the test suite (Phase 71, Task 71.2).

The Velo toolchain has exactly one machine-readable version source: the
repository-root `VERSION` file. `src/common/version.vl` mirrors it as Velo
string constants so the compiler can print the banner, and
`docs/SPECIFICATION.md` / `SECURITY.md` refer to it by major version.

This module is the only place tests read those values, so a version bump is a
single-file edit plus a `VERSION` edit, and any drift fails loudly here instead
of silently passing a stale literal.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
VERSION_FILE = REPO_ROOT / "VERSION"
VERSION_VL = REPO_ROOT / "src" / "common" / "version.vl"

_SEMVER = r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$"


def read_version() -> str:
    """Return the version string from the repository-root VERSION file."""
    assert VERSION_FILE.exists(), "VERSION must exist at repository root"
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    assert re.match(_SEMVER, version), (
        f"VERSION must be MAJOR.MINOR.PATCH[-PRERELEASE], got {version!r}"
    )
    return version


def read_version_vl() -> str:
    """Return VELO_VERSION as declared in src/common/version.vl."""
    assert VERSION_VL.exists(), "src/common/version.vl must exist"
    text = VERSION_VL.read_text(encoding="utf-8")
    match = re.search(r'let\s+VELO_VERSION\s*:\s*string\s*=\s*"([^"]*)"', text)
    assert match, "src/common/version.vl must declare VELO_VERSION: string"
    return match.group(1)


def expected_banner_line() -> str:
    """Return the exact first line `velo version` must print."""
    return f"Velo v{read_version()} (Self-Hosted Native Compiler)"


def major_minor(version: str) -> str:
    """Return 'MAJOR.MINOR' for a version string (used by policy docs)."""
    parts = version.split(".")
    return ".".join(parts[:2])
