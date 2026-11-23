#!/usr/bin/env python3
"""Task 84.2: Test suite for GitHub issue and PR templates.

Verifies:
  1. `.github/ISSUE_TEMPLATE/bug.md` exists, contains valid YAML front matter,
     a `velo version` field, a minimal `.vl` reproduction section, and clear
     diagnostic reporting prompts.
  2. `.github/ISSUE_TEMPLATE/feature.md` exists, contains valid YAML front matter,
     motivation, syntax design with code examples, runtime/memory model prompts,
     and 400-line limit checks.
  3. `.github/PULL_REQUEST_TEMPLATE.md` exists and explicitly references the
     Phase 45-69 Task Execution Contract (unit of work, gaps.md 4-part audit,
     tests, triple-bootstrap determinism, UTF-8 without BOM, 400-line ceiling).
"""

import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GITHUB_DIR = REPO_ROOT / ".github"
ISSUE_DIR = GITHUB_DIR / "ISSUE_TEMPLATE"
BUG_MD = ISSUE_DIR / "bug.md"
FEATURE_MD = ISSUE_DIR / "feature.md"
PR_TEMPLATE_MD = GITHUB_DIR / "PULL_REQUEST_TEMPLATE.md"


def parse_yaml_front_matter(content: str) -> dict:
    """Extracts simple key-value YAML front matter from a Markdown file."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    assert m, "Markdown file is missing YAML front matter (--- ... ---)"
    front_matter_raw = m.group(1)
    result = {}
    for line in front_matter_raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            result[key.strip()] = val.strip().strip("'\"")
    return result


def test_bug_template_structure_and_fields():
    """Verify bug.md exists, has front matter, minimal repro, and velo version field."""
    assert BUG_MD.exists(), f"Bug report template missing at {BUG_MD}"
    content = BUG_MD.read_text(encoding="utf-8")
    
    # 1. Front matter
    fm = parse_yaml_front_matter(content)
    assert "name" in fm, "bug.md missing 'name' in front matter"
    assert "about" in fm, "bug.md missing 'about' in front matter"
    assert "labels" in fm, "bug.md missing 'labels' in front matter"
    assert "bug" in fm["labels"], "bug.md labels should include 'bug'"
    
    # 2. Velo version field
    assert re.search(r"##\s+Velo Version", content, re.IGNORECASE), (
        "bug.md must contain a '## Velo Version' section"
    )
    assert "velo version" in content, "bug.md must instruct user to run `velo version`"
    
    # 3. Minimal .vl repro section
    assert re.search(r"##\s+Minimal `\.vl` Repro", content, re.IGNORECASE), (
        "bug.md must contain a '## Minimal `.vl` Repro' section"
    )
    assert "```velo" in content, "bug.md should provide a ```velo code block template"
    
    # 4. Diagnostics and behavior
    assert re.search(r"##\s+Expected Behavior", content, re.IGNORECASE)
    assert re.search(r"##\s+Actual Behavior", content, re.IGNORECASE)
    assert re.search(r"##\s+Steps to Reproduce", content, re.IGNORECASE)


def test_feature_template_structure_and_fields():
    """Verify feature.md exists, has front matter, proposal/syntax, and runtime model."""
    assert FEATURE_MD.exists(), f"Feature template missing at {FEATURE_MD}"
    content = FEATURE_MD.read_text(encoding="utf-8")
    
    # 1. Front matter
    fm = parse_yaml_front_matter(content)
    assert "name" in fm, "feature.md missing 'name' in front matter"
    assert "about" in fm, "feature.md missing 'about' in front matter"
    assert "labels" in fm, "feature.md missing 'labels' in front matter"
    
    # 2. Problem and syntax design
    assert re.search(r"##\s+Problem & Motivation", content, re.IGNORECASE)
    assert re.search(r"##\s+Proposed Solution / Syntax Design", content, re.IGNORECASE)
    assert "```velo" in content, "feature.md should provide a ```velo code block template"
    
    # 3. Semantics and invariants
    assert re.search(r"##\s+Semantics & Runtime Model", content, re.IGNORECASE)
    assert "Zero-GC" in content, "feature.md should prompt for zero-GC invariant compliance"
    assert re.search(r"##\s+Alternatives Considered & Tradeoffs", content, re.IGNORECASE)
    assert "400-line" in content or "count_lines.py" in content, (
        "feature.md should remind author of 400-line modular design ceiling"
    )


def test_pull_request_template_contract_compliance():
    """Verify PULL_REQUEST_TEMPLATE.md explicitly references Phase 45-69 task contract."""
    assert PR_TEMPLATE_MD.exists(), f"PR template missing at {PR_TEMPLATE_MD}"
    content = PR_TEMPLATE_MD.read_text(encoding="utf-8")
    
    # 1. References Phase 45-69 contract
    assert "Phase 45-69" in content or "Task Execution Contract" in content, (
        "PULL_REQUEST_TEMPLATE.md must reference Phase 45-69 task contract"
    )
    
    # 2. gaps.md 4-part audit trail
    assert "gaps.md" in content, "PR template must reference gaps.md"
    for term in ("Former Defect", "Fix Applied", "Residual Limitation", "Verification"):
        assert term in content, f"PR template must include '{term}' in gaps.md audit checklist"
        
    # 3. Determinism and bootstrap snapshot
    assert "determinism" in content.lower() or "bootstrap.c" in content, (
        "PR template must include compiler determinism / bootstrap check"
    )
    assert "test_bootstrap_snapshot.py" in content or "verify-determinism" in content
    
    # 4. UTF-8 without BOM and 400-line ceiling
    assert "without BOM" in content or "BOM" in content, (
        "PR template must include UTF-8 without BOM check"
    )
    assert "400" in content, "PR template must include 400-line limit check"
    assert "count_lines.py" in content, "PR template must cite count_lines.py"
    
    # 5. Conventional commit format
    assert "conventional commit" in content.lower() or "feat|fix|docs|test" in content, (
        "PR template must reference conventional commit format"
    )


def test_issue_template_config():
    """Verify .github/ISSUE_TEMPLATE/config.yml provides helpful links and disables blank issues."""
    config_yml = ISSUE_DIR / "config.yml"
    assert config_yml.exists(), f"config.yml missing at {config_yml}"
    content = config_yml.read_text(encoding="utf-8")
    assert "blank_issues_enabled: false" in content
    assert "contact_links" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
