"""
CI evidence gate (Phase 76 / Task 76.2, invariant I76.1).

The previous version of the CI test asserted that certain strings appeared in
`.github/workflows/ci.yml`. That passes for a workflow that has never executed,
which is exactly the state this repository was in: no remote, no run, no
evidence. A test that greps YAML is a test of the YAML, not of the CI.

This module separates the two questions:

  * `test_workflow_*.py`-style structural checks live in `test_ci_matrix.py`
    and now parse the YAML instead of matching substrings.
  * *Evidence* lives here. `docs/CI_STATUS.md` must record, for every job the
    workflow declares, the run URL and the commit it ran on. A job with no entry
    fails, and an entry whose SHA is not an ancestor of HEAD fails, because
    evidence for a commit nobody is looking at is not evidence about this tree.

`docs/CI_STATUS.md` is therefore deliberately allowed to be incomplete for
jobs that have never run -- but then the corresponding test fails, which is the
point. The file is the project's claim; this module makes the claim checkable.
"""

import re
import subprocess
from pathlib import Path

import pytest

from conftest import REPO_ROOT


CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"
CI_STATUS = REPO_ROOT / "docs" / "CI_STATUS.md"

# Job keys declared in the workflow. Parsed, never hardcoded, so adding a job
# without adding evidence fails automatically.
RUN_URL = re.compile(r"https://github\.com/[^\s)]+/actions/runs/\d+")
SHA_RE = re.compile(r"\b[0-9a-f]{7,40}\b")


def _workflow_jobs():
    """Return the job IDs declared in ci.yml, parsed with a minimal YAML read."""
    yaml = pytest.importorskip("yaml")
    doc = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))
    jobs = doc.get("jobs") or {}
    assert jobs, "ci.yml declares no jobs"
    return sorted(jobs)


def _status_text():
    assert CI_STATUS.exists(), (
        "docs/CI_STATUS.md must exist and record the latest green run per job"
    )
    return CI_STATUS.read_text(encoding="utf-8")


def _entries(text):
    """
    Parse `docs/CI_STATUS.md` into {job: (run_url, sha)}.

    Expected row shape, one per job:

        | `linux` | https://github.com/.../actions/runs/123 | `abc1234` | 2026-11-17 |
    """
    entries = {}
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        job = cells[0].strip("` ")
        url_match = RUN_URL.search(cells[1])
        sha_match = SHA_RE.search(cells[2])
        if job and url_match and sha_match:
            entries[job] = (url_match.group(0), sha_match.group(0))
    return entries


def _is_ancestor(sha):
    res = subprocess.run(
        ["git", "merge-base", "--is-ancestor", sha, "HEAD"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return res.returncode == 0


def test_ci_status_file_exists():
    assert CI_STATUS.exists(), (
        "docs/CI_STATUS.md must exist. It is the committed evidence that CI ran "
        "on a real commit; without it, green CI is a claim."
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Task 76.1 is blocked: the repository has no git remote, so Actions has "
        "never run and no job can cite a green run. This is expected to fail "
        "until a remote exists and the workflow executes; strict=True means the "
        "marker must be removed once it starts passing."
    ),
)
def test_every_declared_job_has_evidence():
    text = _status_text()
    entries = _entries(text)
    missing = [job for job in _workflow_jobs() if job not in entries]
    assert not missing, (
        "these CI jobs have no recorded green run in docs/CI_STATUS.md: "
        + ", ".join(missing)
    )


def test_evidence_links_are_actions_runs():
    for job, (url, _sha) in _entries(_status_text()).items():
        assert RUN_URL.fullmatch(url), f"{job}: not an Actions run URL: {url}"


def test_evidence_commits_are_ancestors_of_head():
    """
    Evidence must describe a commit this tree descends from.

    A run on an unrelated branch says nothing about `HEAD`, and a fabricated SHA
    fails here because git cannot resolve it.
    """
    offenders = []
    for job, (_url, sha) in _entries(_status_text()).items():
        if not _is_ancestor(sha):
            offenders.append(job)
    assert not offenders, (
        "these jobs cite a commit that is not an ancestor of HEAD: "
        + ", ".join(offenders)
    )


def test_ci_status_states_the_open_gap():
    """
    The file must not imply coverage it does not have.

    Until a remote exists and the jobs have run, the honest state is "never
    executed". Encoding that in the document keeps the claim and the code in
    agreement; deleting the sentence is the moment someone starts believing the
    badges.
    """
    text = _status_text()
    lowered = text.lower()
    assert ("never" in lowered and "run" in lowered) or "not yet" in lowered or (
        "no remote" in lowered
    ), (
        "docs/CI_STATUS.md must say plainly that CI has not executed yet, so a "
        "reader is not misled by an empty table"
    )
