"""
Phase 71 / Task 71.3: the changelog is a real release document.

A changelog is not decoration in a pre-publication project: it is where a
consumer of `2.0.0-pre` learns what does not work. The rows below therefore
check not only that `CHANGELOG.md` is Keep-a-Changelog shaped, but that it
records the known P0 limitations and contains no fabricated links (there is no
public remote yet).
"""

import re

from release_meta import REPO_ROOT

CHANGELOG = REPO_ROOT / "CHANGELOG.md"


def _text():
    assert CHANGELOG.exists(), "CHANGELOG.md must exist"
    return CHANGELOG.read_text(encoding="utf-8")


def test_changelog_is_keep_a_changelog_shaped():
    text = _text()
    assert text.startswith("# Changelog")
    assert "Keep a Changelog" in text
    assert "Semantic Versioning" in text
    assert "## [Unreleased]" in text
    for section in ("### Added", "### Changed", "### Fixed", "### Security"):
        assert section in text, f"CHANGELOG must have a {section} section"


def test_changelog_names_the_current_version():
    """The released heading must match the VERSION file, not a stale literal."""
    from release_meta import read_version

    text = _text()
    assert f"## [{read_version()}]" in text, (
        f"CHANGELOG must have a section for {read_version()}"
    )


def test_changelog_defers_to_version_file_as_authority():
    text = _text()
    assert "VERSION" in text, "CHANGELOG must name the VERSION file as authoritative"


def test_changelog_records_known_limitations():
    """
    A preview release must state what does not work. This is the honesty gate:
    the unreleased section must list the P0 gaps rather than implying maturity.
    """
    text = _text()
    assert "Known limitations" in text
    for topic in ("Windows-only", "pkg install", "TLS", "overflow"):
        assert topic.lower() in text.lower(), (
            f"CHANGELOG known limitations must mention {topic!r}"
        )


def test_changelog_known_limitations_cite_the_gap_phases():
    """Each limitation should point at the phase that tracks its fix."""
    text = _text()
    section = text.split("### Known limitations", 1)
    assert len(section) == 2, "CHANGELOG must have a 'Known limitations' subsection"
    body = section[1]
    phases = re.findall(r"\(Phase (\d+)\)", body)
    assert len(phases) >= 4, (
        "each known limitation must cite its tracking phase, e.g. (Phase 70)"
    )


def test_changelog_has_no_fabricated_urls():
    """Links must be the two standard spec sites or relative; there is no remote."""
    text = _text()
    urls = re.findall(r"https?://[^\s)\]]+", text)
    allowed = ("keepachangelog.com", "semver.org")
    for url in urls:
        assert any(url.startswith(f"https://{host}") for host in allowed), (
            f"CHANGELOG.md has an unexpected URL: {url}"
        )


def test_changelog_entries_cite_commits():
    """Every backfilled entry must reference the commit that made the change."""
    text = _text()
    short_shas = re.findall(r"`([0-9a-f]{7})`", text)
    assert len(short_shas) >= 40, (
        "the backfilled changelog must cite commit shas so entries are verifiable"
    )
