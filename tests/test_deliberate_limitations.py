"""
Phase 77 / Task 77.1: Language Completeness -- Deliberate Limitations Specification.

Security Invariant I77.1:
"A missing language feature is documented in docs/SPECIFICATION.md under 'Deliberate limitations'
with the workaround and the cost. Silence is not allowed."

This test suite audits docs/SPECIFICATION.md to verify that Section 11 ('Deliberate Limitations & Workarounds')
is present, covers all four core absences (closures, traits/interfaces, module privacy, conditional compilation)
as well as import aliasing and expression defer, detailing the architectural rationale, the cost, and the
official, idiomatic workaround with code examples.
"""

from pathlib import Path
import pytest

pytestmark = pytest.mark.fast

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_FILE = REPO_ROOT / "docs" / "SPECIFICATION.md"


def test_specification_file_exists():
    assert SPEC_FILE.exists(), f"Missing specification file at {SPEC_FILE}"


def test_deliberate_limitations_section_exists():
    content = SPEC_FILE.read_text(encoding="utf-8")
    assert "## 11. Deliberate Limitations & Workarounds" in content or "## 11. Deliberate Limitations" in content, (
        "docs/SPECIFICATION.md must contain a dedicated 'Deliberate Limitations' section (Invariant I77.1)"
    )


def test_closures_absence_documented():
    content = SPEC_FILE.read_text(encoding="utf-8")
    assert "11.1 Closures and Environment Capture" in content
    # Invariant I77.1 checks: Absence, Rationale, Cost, Workaround
    assert "* **Absence:**" in content
    assert "* **Architectural Rationale:**" in content
    assert "* **The Cost:**" in content
    assert "* **Official Workaround:**" in content
    assert "user_data" in content or "TimerContext" in content


def test_interfaces_absence_documented():
    content = SPEC_FILE.read_text(encoding="utf-8")
    assert "11.2 Dynamic Interfaces, Traits, and Vtables" in content
    assert "vtables" in content.lower()
    assert "monomorphized" in content.lower()
    assert "WriterVTable" in content or "vtable" in content


def test_module_privacy_absence_documented():
    content = SPEC_FILE.read_text(encoding="utf-8")
    assert "11.3 Module Privacy and Export Control" in content
    assert "pub" in content
    assert "underscore" in content.lower() or "_helper" in content


def test_conditional_compilation_absence_documented():
    content = SPEC_FILE.read_text(encoding="utf-8")
    assert "11.4 Preprocessor Directives and Conditional Compilation" in content
    assert "#if" in content
    assert "_windows.vl" in content
    assert "os_is_windows()" in content


def test_import_aliasing_and_defer_documented():
    content = SPEC_FILE.read_text(encoding="utf-8")
    assert "11.5 Import Aliasing and Selective Imports" in content
    assert "11.6 Expression Defer" in content
    assert "defer" in content
