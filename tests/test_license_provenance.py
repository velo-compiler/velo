"""
Phase 71 / Task 71.1: license and provenance files exist and are coherent.

Invariant I71.1 from `gaps.md`: "Every tracked source file is covered by a
declared license." Without a license the legal default is all rights reserved,
which makes the project unusable regardless of code quality, so this suite is a
release gate rather than a documentation nicety.
"""

import re
import subprocess
from pathlib import Path

import pytest

from release_meta import REPO_ROOT

pytestmark = pytest.mark.fast

MIT = REPO_ROOT / "LICENSE-MIT"
APACHE = REPO_ROOT / "LICENSE-APACHE"
README = REPO_ROOT / "README.md"
SECURITY = REPO_ROOT / "SECURITY.md"


def test_both_license_files_exist():
    assert MIT.exists(), "LICENSE-MIT must exist"
    assert APACHE.exists(), "LICENSE-APACHE must exist"


def test_mit_license_text_is_intact():
    text = MIT.read_text(encoding="utf-8")
    assert "MIT License" in text
    assert "Permission is hereby granted, free of charge" in text
    assert 'THE SOFTWARE IS PROVIDED "AS IS"' in text
    # The copyright holder must be identified, not left as a placeholder.
    assert re.search(r"Copyright \(c\) \d{4} .+\S", text), "copyright line required"
    assert "[yyyy]" not in text and "TODO" not in text


def test_apache_license_text_is_intact():
    text = APACHE.read_text(encoding="utf-8")
    assert "Apache License" in text
    assert "Version 2.0, January 2004" in text
    assert "TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION" in text
    assert "END OF TERMS AND CONDITIONS" in text
    # Verbatim requirement: the clause count must survive editing accidents.
    for clause in ("1. Definitions.", "9. Accepting Warranty or Additional Liability."):
        assert clause in text, f"Apache-2.0 text is missing {clause!r}"


def test_readme_declares_dual_license():
    text = README.read_text(encoding="utf-8")
    assert "MIT OR Apache-2.0" in text, "README must declare the SPDX expression"
    assert "LICENSE-MIT" in text and "LICENSE-APACHE" in text
    assert "## License" in text


def test_readme_documents_generated_artifact_licensing():
    """bootstrap.c is generated; its license status must be stated, not implied."""
    text = README.read_text(encoding="utf-8")
    assert "bootstrap.c" in text
    section = text.split("### Generated artifacts", 1)
    assert len(section) == 2, "README must have a 'Generated artifacts' subsection"
    body = section[1]
    assert "MIT OR Apache-2.0" in body, "generated artifacts must inherit the license"
    assert "yours" in body.lower(), (
        "README must state that user programs are not covered by this license"
    )


def test_security_md_carries_spdx_identifier():
    text = SECURITY.read_text(encoding="utf-8")
    assert "SPDX-License-Identifier: MIT OR Apache-2.0" in text


def test_license_files_have_no_bom():
    for path in (MIT, APACHE):
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{path.name} must not have a BOM"


def test_license_files_are_tracked_by_git():
    """An untracked license is not distributed, so it does not license anything."""
    res = subprocess.run(
        ["git", "ls-files", "LICENSE-MIT", "LICENSE-APACHE"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    tracked = set(res.stdout.split())
    assert "LICENSE-MIT" in tracked, "LICENSE-MIT must be committed"
    assert "LICENSE-APACHE" in tracked, "LICENSE-APACHE must be committed"
