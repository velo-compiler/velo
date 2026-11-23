#!/usr/bin/env python3
"""Task 84.3: Test suite for Velo project governance and deprecation policy.

Verifies:
  1. `GOVERNANCE.md` exists at repository root and defines the decision-making model
     ("Who Decides"), breaking change approval pipeline, what "1.0" means, and
     the deprecation policy (minimum two minor versions).
  2. The breaking change process mandates invariant compliance, two-maintainer
     sign-off, and gaps.md audit trail.
  3. The 1.0 definition mandates specification freeze, backward compatibility,
     Tier 1 cross-platform stdlib, and zero unresolved P0/P1 gaps.
  4. The deprecation policy formally encodes the two minor versions minimum rule.
  5. `README.md` and `CONTRIBUTING.md` link to `GOVERNANCE.md`.
"""

import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GOVERNANCE_MD = REPO_ROOT / "GOVERNANCE.md"
README_MD = REPO_ROOT / "README.md"
CONTRIBUTING_MD = REPO_ROOT / "CONTRIBUTING.md"


def test_governance_file_exists():
    """Verify GOVERNANCE.md exists and is non-empty."""
    assert GOVERNANCE_MD.exists(), f"GOVERNANCE.md missing at {GOVERNANCE_MD}"
    content = GOVERNANCE_MD.read_text(encoding="utf-8")
    assert len(content.strip()) > 500, "GOVERNANCE.md is too short or empty"


def test_decision_making_model_who_decides():
    """Verify decision-making roles and authority are defined."""
    content = GOVERNANCE_MD.read_text(encoding="utf-8")
    
    assert re.search(r"Who Decides", content, re.IGNORECASE) or re.search(r"Decision-Making Model", content)
    assert "Core Maintainers" in content
    assert "Subsystem Stewards" in content or "Stewards" in content
    assert "Contributors" in content
    
    # Check core invariants reviewed during decision making
    for invariant in ("Zero-GC", "Deterministic C99", "400", "gaps.md"):
        assert invariant in content, f"Decision model should reference invariant: {invariant}"


def test_breaking_change_approval_process():
    """Verify breaking change definition and approval pipeline."""
    content = GOVERNANCE_MD.read_text(encoding="utf-8")
    
    assert re.search(r"Breaking Change Approval", content, re.IGNORECASE)
    assert "RFC" in content
    assert "Two-Maintainer Sign-Off" in content or "two Core Maintainers" in content
    assert "Deprecation" in content
    assert "CHANGELOG.md" in content


def test_what_1_0_means_definition():
    """Verify explicit criteria and stability promises for version 1.0."""
    content = GOVERNANCE_MD.read_text(encoding="utf-8")
    
    assert re.search(r'What "1\.0" Means', content, re.IGNORECASE) or re.search(r'1\.0 Stability', content)
    assert "Specification Freeze" in content or "frozen" in content.lower()
    assert "Backward Compatibility" in content
    assert "Tier 1" in content
    assert "Deterministic Self-Hosting" in content or "determinism" in content.lower()
    assert "gaps.md" in content


def test_deprecation_policy_minimum_two_minor_versions():
    """Verify deprecation policy enforces minimum two minor versions."""
    content = GOVERNANCE_MD.read_text(encoding="utf-8")
    
    assert re.search(r"Deprecation Policy", content, re.IGNORECASE)
    assert "two minor versions" in content.lower() or "two consecutive minor" in content.lower()
    
    # Check lifecycle phases
    assert re.search(r"vX\.Y\.0", content) or re.search(r"v1\.2\.0", content)
    assert "Warning" in content
    assert "Security Exception" in content or "SECURITY.md" in content


def test_cross_references_in_readme_and_contributing():
    """Verify README.md and CONTRIBUTING.md link to GOVERNANCE.md."""
    readme_content = README_MD.read_text(encoding="utf-8")
    contributing_content = CONTRIBUTING_MD.read_text(encoding="utf-8")
    
    assert "GOVERNANCE.md" in readme_content, "README.md should link to GOVERNANCE.md"
    assert "GOVERNANCE.md" in contributing_content, "CONTRIBUTING.md should link to GOVERNANCE.md"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
