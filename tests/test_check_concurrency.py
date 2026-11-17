"""
Phase 76 / Task 76.4: `velo check` must be safe to run concurrently.

The defect: both `run_check_json_opts` and `run_check_pretty_opts` capture the
diagnostics stream into a file named `velo_check_capture.tmp` *in the process
working directory* (src/backend/check.vl:291, :335). Two `velo check` processes
started in the same directory therefore open the same path for writing, and each
one reads back whatever the other wrote -- or, worse, reads a truncated file
while the other is still writing it. The maintainer's workaround was to never
run two suites at once, which CI cannot honour: pytest-xdist, parallel jobs on
one runner, and any editor integration all break it.

These tests pin the observable contract rather than the implementation: N
concurrent checks in one directory must all report their own correct verdict,
and the directory must be left clean.
"""

import json
import os
import subprocess
import sys

import pytest

from conftest import velo_exe

VALID = """use sys.io

act main() -> i32 {
    io.println("concurrent")
    return 0
}
"""

BROKEN = """use sys.io

pickle = definitely_not_a_decl

act main() -> i32 {
    return 0
}
"""


def _write(path, text):
    with open(path, "w", newline="\n", encoding="utf-8") as fh:
        fh.write(text)
    return str(path)


@pytest.fixture()
def workdir(tmp_path):
    """A directory used as the CWD for every concurrent check."""
    d = tmp_path / "cwd"
    d.mkdir()
    return d


def _spawn(args, cwd):
    return subprocess.Popen(
        args,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _check_args(src):
    return [str(velo_exe()), "check", src, "--json"]


def test_concurrent_checks_all_succeed(workdir, tmp_path):
    """Eight concurrent checks of the same valid file must all exit 0."""
    src = _write(tmp_path / "valid.vl", VALID)
    procs = [_spawn(_check_args(src), workdir) for _ in range(8)]
    results = [(p.wait(timeout=180), p.communicate()) for p in procs]

    for rc, (out, err) in results:
        assert rc == 0, f"concurrent check failed (rc={rc}):\n{out}\n{err}"
        report = json.loads(out)
        assert report["ok"] is True
        assert report["diagnostics"] == []


def test_concurrent_checks_keep_verdicts_separate(workdir, tmp_path):
    """
    Interleaved valid and broken files must each report their own verdict.

    This is the assertion that actually catches the shared-filename bug: with a
    single capture file, a process checking a valid file can read the broken
    file's diagnostics (or a half-written mix) and flip its verdict.
    """
    valid = _write(tmp_path / "valid.vl", VALID)
    broken = _write(tmp_path / "broken.vl", BROKEN)
    plan = [valid, broken] * 4
    procs = [(_spawn(_check_args(src), workdir), src) for src in plan]
    outcomes = [(p.wait(timeout=180), p.communicate(), src) for p, src in procs]

    for rc, (out, err), src in outcomes:
        report = json.loads(out)
        if os.path.basename(src) == "valid.vl":
            assert rc == 0, f"valid file reported failure:\n{out}\n{err}"
            assert report["ok"] is True
            assert report["diagnostics"] == [], (
                "a valid file picked up another process's diagnostics"
            )
        else:
            assert rc == 1, f"broken file reported success:\n{out}\n{err}"
            assert report["ok"] is False
            assert report["diagnostics"], "broken file lost its diagnostics"


def test_concurrent_checks_leave_no_scratch_file(workdir, tmp_path):
    """No capture file may survive in the working directory."""
    src = _write(tmp_path / "valid.vl", VALID)
    procs = [_spawn(_check_args(src), workdir) for _ in range(4)]
    for p in procs:
        p.wait(timeout=180)
        p.communicate()

    leftovers = sorted(os.listdir(workdir))
    assert leftovers == [], f"check left files behind in its CWD: {leftovers}"


def test_pretty_mode_is_also_concurrency_safe(workdir, tmp_path):
    """The pretty (non-JSON) path uses the same capture file, so it must too."""
    src = _write(tmp_path / "valid.vl", VALID)
    procs = [
        _spawn([str(velo_exe()), "check", src], workdir) for _ in range(4)
    ]
    results = [(p.wait(timeout=180), p.communicate()) for p in procs]
    for rc, (out, err) in results:
        combined = out + err
        assert rc == 0, f"concurrent pretty check failed (rc={rc}):\n{combined}"
        assert "Check passed" in combined
    assert sorted(os.listdir(workdir)) == []
