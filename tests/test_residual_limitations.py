"""tests/test_residual_limitations.py — Regression tests for Phase 85 residual audit.

Validates Phase 85 and Section 6 ("Definition of Public Release"):
- Residual limitation registry integrity in gaps.md
- Definition of Public Release gates (8 verified, 2 pending external remote)
- Honest unrun state in docs/CI_STATUS.md
- PID-isolated check capture path (76.4)
- Path-independent reproducible emit-c directives (79.2)
"""

import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GAPS_MD = REPO_ROOT / "gaps.md"
CI_STATUS_MD = REPO_ROOT / "docs" / "CI_STATUS.md"
ROADMAP_MD = REPO_ROOT / "docs" / "ROADMAP.md"

pytestmark = pytest.mark.fast


def test_phase_85_residual_table_integrity():
    """Verify that gaps.md Phase 85 contains all 15 audited residual items."""
    content = GAPS_MD.read_text(encoding="utf-8")
    m = re.search(r"# Phase 85:.*?\n\n(.*?)(?=\n---\Z|\n## 6|\Z)", content, re.DOTALL)
    assert m is not None, "Phase 85 section missing from gaps.md"

    table_lines = [l.strip() for l in m.group(1).splitlines() if l.strip().startswith("|")]
    assert len(table_lines) >= 17, "Phase 85 table must have header, divider, and at least 15 items"

    # Assert critical completed residual items are explicitly recorded
    table_text = "\n".join(table_lines)
    assert "`velo_check_capture.tmp` fixed CWD filename" in table_text
    assert "Overlapping `mem.copy`/`mem.set` remain C UB" in table_text
    assert "No `Set`/`Deque`/priority queue" in table_text
    assert "`defer` takes a block, not an expression" in table_text
    assert "400-line ceiling forces sliver modules" in table_text
    assert "Frozen Stage-1 Python compiler still in the build story" in table_text
    assert "`std/async` is `poll(2)` on Linux" in table_text


def test_definition_of_public_release_gates():
    """Verify that Section 6 tracks all 10 release gates with verified states."""
    content = GAPS_MD.read_text(encoding="utf-8")
    m = re.search(r"## 6\. Definition of Public Release\s*\n\n(.*?)(?=\n## 7|\Z)", content, re.DOTALL)
    assert m is not None, "Section 6 missing from gaps.md"

    section_text = m.group(1)
    gates = re.findall(r"\d+\.\s+\*\*([^:]+):\*\*[\s\S]*?(\[[ x]\])", section_text)
    assert len(gates) == 10, f"Expected 10 release gates, found {len(gates)}"

    gate_dict = {name.strip(): mark.strip() for name, mark in gates}

    # Verified gates must be marked [x]
    assert gate_dict["Legal"] == "[x]"
    assert gate_dict["No lying stubs"] == "[x]"
    assert gate_dict["Memory safety story"] == "[x]"
    assert gate_dict["Network reality"] == "[x]"
    assert gate_dict["Packages"] == "[x]"
    assert gate_dict["Robustness"] == "[x]"
    assert gate_dict["Docs"] == "[x]"
    assert gate_dict["Maintainability"] == "[x]"

    # Gated on remote CI execution (Phase 76.1) must remain [ ] until remote push
    assert gate_dict["Platforms"] == "[ ]"
    assert gate_dict["CI evidence"] == "[ ]"


def test_ci_status_document_maintains_honesty():
    """Verify that docs/CI_STATUS.md documents the unrun state rather than claiming false green."""
    assert CI_STATUS_MD.exists(), "docs/CI_STATUS.md must exist"
    content = CI_STATUS_MD.read_text(encoding="utf-8")

    assert "not yet" in content, "docs/CI_STATUS.md must state 'not yet' for jobs awaiting remote runs"
    assert "git remote" in content or "remote" in content


def test_check_capture_path_is_pid_isolated():
    """Verify that src/backend/check.vl isolates capture files using process PID."""
    check_vl = REPO_ROOT / "src" / "backend" / "check.vl"
    content = check_vl.read_text(encoding="utf-8")
    assert "check_capture_path" in content
    assert "velo_check_capture_" in content
    assert "velo_host_getpid" in content


def test_reproducible_no_line_directives_support():
    """Verify that compiler driver supports reproducible --no-line-directives emission."""
    driver_vl = REPO_ROOT / "src" / "backend" / "driver.vl"
    content = driver_vl.read_text(encoding="utf-8")
    assert "no_line_directives" in content
