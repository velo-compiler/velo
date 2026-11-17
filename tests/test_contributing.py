"""
Phase 71 / Task 71.5: CONTRIBUTING.md documents the gates a change must pass.

The build model is unusual (self-hosted, C snapshot, determinism fixed point),
so a contributor who does not know the five gates will produce work that a
reviewer has to reject. These rows assert the document names each gate command
verbatim, because a paraphrased command is a command that does not run.
"""

from release_meta import REPO_ROOT

import pytest

pytestmark = pytest.mark.fast

CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"


def _text():
    assert CONTRIBUTING.exists(), "CONTRIBUTING.md must exist"
    return CONTRIBUTING.read_text(encoding="utf-8")


def test_contributing_documents_every_gate_command():
    text = _text()
    for command in (
        "pytest tests -q",
        "scripts/check_determinism.py",
        "scripts/count_lines.py",
        "scripts/check_clean_tree.py",
        "test_bootstrap_snapshot.py",
    ):
        assert command in text, f"CONTRIBUTING.md must document {command}"


def test_contributing_warns_about_bom():
    text = _text()
    assert "BOM" in text, "CONTRIBUTING.md must warn about UTF-8 BOMs"
    assert "ufeff" in text or "FEFF" in text, (
        "CONTRIBUTING.md must show the actual BOM error so it is searchable"
    )


def test_contributing_states_the_license_stance():
    text = _text()
    assert "MIT OR Apache-2.0" in text, (
        "CONTRIBUTING.md must state the inbound licensing of contributions"
    )


def test_contributing_documents_the_gaps_md_contract():
    """gaps.md is the living audit; a contributor must know to update it."""
    text = _text()
    assert "gaps.md" in text
    assert "COMPLETED" in text
    assert "residual limitation" in text.lower()


def test_contributing_documents_commit_style():
    text = _text()
    for prefix in ("feat(", "fix(", "test(", "docs("):
        assert prefix in text, f"CONTRIBUTING.md must show the {prefix} prefix"


def test_contributing_documents_the_bootstrap_procedure():
    text = _text()
    assert "bootstrap.bat --full" in text or "bootstrap.sh --full" in text
    assert "velo_gen2" in text and "velo_gen3" in text, (
        "the manual Gen2 -> Gen3 chain must be spelled out"
    )


def test_contributing_explains_the_snapshot_stdout_trap():
    """
    `emit-c` to stdout is a different code path from `emit-c -o`; a contributor
    who compares the wrong one gets a confusing mismatch.
    """
    text = _text()
    assert "file output" in text.lower() or "not stdout" in text.lower()


def test_contributing_forbids_committing_build_products():
    text = _text()
    assert ".velo_cache" in text
    assert "BOM" in text
