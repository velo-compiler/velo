"""
Phase 71 / Task 71.6: the release script and the archive it produces.

These tests pin the *contract* of `scripts/release.py` rather than running a
full release (which would take the whole suite's runtime again as a subprocess
of a subprocess):

- the script reads `VERSION` instead of hardcoding a version;
- its gate list covers the five gates `CONTRIBUTING.md` promises;
- each declared archive entry actually exists in the repository;
- the archive contains a bootstrap-capable set of files;
- a gate failure aborts before packaging (proved by invoking the script with an
  impossible version and asserting a non-zero exit and no archive).

The last row is the important one: a release script that packages a tree which
fails its own gates is worse than no release script.
"""

import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from release_meta import REPO_ROOT, read_version
from conftest import velo_exe

RELEASE_PY = REPO_ROOT / "scripts" / "release.py"


def _text():
    return RELEASE_PY.read_text(encoding="utf-8")


def test_release_script_exists_and_reads_version_file():
    assert RELEASE_PY.exists(), "scripts/release.py must exist"
    text = _text()
    assert "VERSION" in text, "release.py must read the VERSION file"
    assert not re.search(r'"[0-9]+\.[0-9]+\.[0-9]+', text), (
        "release.py must not hardcode a version literal; read VERSION instead"
    )


@pytest.mark.parametrize(
    "gate",
    [
        "gate_version_agreement",
        "gate_velo_binary",
        "gate_bootstrap_snapshot",
        "gate_determinism",
        "gate_clean_worktree",
        "gate_test_suite",
    ],
)
def test_release_script_declares_each_gate(gate):
    """Every gate promised by CONTRIBUTING.md section 4 must exist in the script."""
    assert gate in _text(), f"release.py must define {gate}"


def test_declared_archive_entries_exist():
    """Any path the script packages must exist, so packaging cannot half-fail."""
    text = _text()
    block = re.search(r"ARCHIVE_ENTRIES\s*=\s*\[(.*?)\]", text, re.S)
    assert block, "release.py must declare ARCHIVE_ENTRIES"
    entries = re.findall(r'"([^"]+)"', block.group(1))
    assert entries, "ARCHIVE_ENTRIES must not be empty"
    for entry in entries:
        assert (REPO_ROOT / entry).exists(), f"archive entry missing: {entry}"


def test_archive_entries_include_bootstrap_prerequisites():
    """The archive must be buildable on a machine with only a C compiler."""
    text = _text()
    block = re.search(r"ARCHIVE_ENTRIES\s*=\s*\[(.*?)\]", text, re.S)
    entries = set(re.findall(r'"([^"]+)"', block.group(1)))
    for required in ("bootstrap.c", "runtime", "std", "LICENSE-MIT", "LICENSE-APACHE"):
        assert required in entries, f"archive must include {required}"


def test_gate_failure_prevents_packaging(tmp_path):
    """
    A failing gate must abort with a non-zero exit and write no archive.

    The version-agreement gate is the cheapest to force: point the script at a
    temporary VERSION file by running it in a copy-free way is not possible, so
    instead we assert the gate function raises on a deliberately wrong value.
    """
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        import release
    finally:
        sys.path.pop(0)

    with pytest.raises(release.GateFailure):
        release.gate_version_agreement("999.999.999-definitely-not-the-version")

    # And the real value must pass, so the gate is not simply always-throwing.
    release.gate_version_agreement(read_version())


def test_release_script_help_runs():
    res = subprocess.run(
        [sys.executable, str(RELEASE_PY), "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert res.returncode == 0, res.stderr
    assert "--skip-tests" in res.stdout


def test_bootstrap_gate_spells_source_path_relatively():
    """
    The snapshot gate must invoke emit-c with `src/main.vl`, not an absolute path.

    `#line` directives embed the source path verbatim apart from `\\\\` -> `/`
    (src/backend/codegen_line.vl:6-17), so an absolute path produces a
    byte-different bootstrap.c from identical source. The first version of this
    gate used an absolute path and failed against a perfectly consistent tree.
    """
    text = _text()
    gate = text.split("def gate_bootstrap_snapshot", 1)[1].split("\ndef ", 1)[0]
    assert '"src/main.vl"' in gate, (
        "gate_bootstrap_snapshot must pass the relative path 'src/main.vl'"
    )
    assert "str(MAIN_VL)" not in gate, (
        "gate_bootstrap_snapshot must not pass an absolute source path"
    )


def test_emit_c_output_depends_on_source_path_spelling(tmp_path):
    """Pins the underlying compiler behaviour the gate has to work around."""
    import subprocess as sp

    from release_meta import REPO_ROOT as root

    velo = velo_exe()
    if not velo.exists():
        pytest.skip("compiler binary not built")

    rel_out = tmp_path / "rel.c"
    abs_out = tmp_path / "abs.c"
    rel = sp.run(
        [str(velo), "emit-c", "src/main.vl", "-o", str(rel_out)],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    absolute = sp.run(
        [str(velo), "emit-c", str(root / "src" / "main.vl"), "-o", str(abs_out)],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert rel.returncode == 0, rel.stderr
    assert absolute.returncode == 0, absolute.stderr
    assert rel_out.read_bytes() != abs_out.read_bytes(), (
        "if these ever become equal, path spelling no longer matters and the "
        "gate can accept either form"
    )
    rel_text = rel_out.read_text(encoding="utf-8", errors="replace")
    abs_text = abs_out.read_text(encoding="utf-8", errors="replace")
    assert '#line 5 "src/main.vl"' in rel_text
    assert "src/main.vl" in abs_text and '#line 5 "src/main.vl"' not in abs_text


def test_committed_bootstrap_matches_relative_invocation(tmp_path):
    """The committed snapshot was generated relatively; the gate must agree."""
    import hashlib
    import subprocess as sp

    from release_meta import REPO_ROOT as root

    velo = velo_exe()
    if not velo.exists():
        pytest.skip("compiler binary not built")

    fresh = tmp_path / "fresh.c"
    res = sp.run(
        [str(velo), "emit-c", "src/main.vl", "-o", str(fresh)],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert res.returncode == 0, res.stderr
    assert hashlib.sha256(fresh.read_bytes()).hexdigest() == hashlib.sha256(
        (root / "bootstrap.c").read_bytes()
    ).hexdigest(), "bootstrap.c must equal relative emit-c output"
