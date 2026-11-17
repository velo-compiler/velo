"""
Unit and integration tests for Task 49.1:
Multi-platform continuous integration matrix, POSIX bootstrap scripts,
and cross-platform determinism verification.
"""

import os
import sys
import subprocess
from pathlib import Path
import pytest
from conftest import velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"
BOOTSTRAP_SH = REPO_ROOT / "scripts" / "bootstrap.sh"
BOOTSTRAP_BAT = REPO_ROOT / "scripts" / "bootstrap.bat"
CHECK_DET = REPO_ROOT / "scripts" / "check_determinism.py"
VELO_EXE = velo_exe()

def test_ci_workflow_exists_and_configured():
    """
    Parse the workflow and assert its structure, not its substrings.

    The previous version asserted that strings like "ubuntu-22.04" and
    "pytest tests -q" appeared somewhere in the file. That passes for a workflow
    whose jobs are commented out, whose steps are under the wrong key, or that
    GitHub would reject outright. Parsing the YAML and walking the job/step tree
    is the difference between testing the workflow and testing the prose.

    Whether the workflow has ever *run* is a separate question, answered by
    tests/test_ci_evidence.py against docs/CI_STATUS.md.
    """
    yaml = pytest.importorskip("yaml")
    assert CI_YML.exists(), ".github/workflows/ci.yml must exist"
    doc = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))

    # Triggers: a real mapping, not the string "push:".
    # PyYAML parses the bare key `on:` as the boolean True, so accept both.
    triggers = doc.get("on", doc.get(True))
    assert triggers, "workflow must declare triggers"
    assert "push" in triggers, "workflow must trigger on push"
    assert "pull_request" in triggers, "workflow must trigger on pull_request"

    jobs = doc.get("jobs") or {}
    assert jobs, "workflow must declare jobs"

    required = {"linux", "macos", "windows-gcc", "windows-msvc", "sanitizer"}
    missing = required - set(jobs)
    assert not missing, f"workflow is missing required jobs: {sorted(missing)}"

    for name, job in jobs.items():
        assert "runs-on" in job, f"job {name} has no runs-on"
        steps = job.get("steps") or []
        assert steps, f"job {name} has no steps"
        for step in steps:
            assert ("uses" in step) or ("run" in step), (
                f"job {name} has a step with neither uses nor run"
            )


def test_linux_and_macos_jobs_use_a_matrix():
    yaml = pytest.importorskip("yaml")
    doc = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))
    jobs = doc["jobs"]

    for name in ("linux", "macos"):
        strategy = jobs[name].get("strategy") or {}
        matrix = strategy.get("matrix") or {}
        assert matrix, f"job {name} must define a matrix"
        # runs-on must reference the matrix, otherwise every leg runs on one OS.
        runs_on = str(jobs[name]["runs-on"])
        assert "matrix." in runs_on, (
            f"job {name} has a matrix but runs-on does not use it: {runs_on}"
        )


def test_linux_matrix_covers_both_compilers():
    yaml = pytest.importorskip("yaml")
    jobs = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))["jobs"]
    compilers = jobs["linux"]["strategy"]["matrix"].get("compiler") or []
    assert {"gcc", "clang"} <= set(compilers), (
        f"the linux job must test gcc and clang, got {compilers}"
    )


def test_every_job_runs_the_test_suite():
    """
    Each job must actually invoke pytest.

    A job that bootstraps the compiler and stops proves only that it compiles,
    which is how `windows-msvc` was silently reduced to two test files.
    """
    yaml = pytest.importorskip("yaml")
    jobs = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))["jobs"]
    for name, job in jobs.items():
        commands = [
            str(step.get("run", ""))
            for step in (job.get("steps") or [])
        ]
        joined = "\n".join(commands)
        assert "pytest" in joined, f"job {name} never runs pytest"


def test_fast_job_runs_only_the_fast_lane():
    """
    The push lane must select `-m fast` and must not bootstrap a compiler.

    Task 76.6 exists because a 16-minute red X on every push trains people to
    ignore CI. A `fast` job that quietly runs the whole suite, or that builds the
    compiler first, restores the problem while looking solved.
    """
    yaml = pytest.importorskip("yaml")
    jobs = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))["jobs"]
    assert "fast" in jobs, "the workflow must declare a `fast` job"

    job = jobs["fast"]
    commands = "\n".join(str(step.get("run", "")) for step in (job.get("steps") or []))

    assert "-m fast" in commands, (
        "the fast job must select the fast tier with `-m fast`, otherwise it runs "
        "the full suite"
    )
    assert "bootstrap" not in commands, (
        "the fast job must not bootstrap the compiler: the fast tier is defined "
        "as tests that never invoke a C compiler"
    )
    assert job.get("if") in (None, ""), (
        "the fast job must run on every push; a conditional defeats the lane"
    )


def test_heavy_jobs_do_not_run_on_push():
    """
    Only the fast lane runs on a push; the suite runs on pull requests.

    Without this, every push starts six jobs that each spend ~16 minutes
    compiling, which is exactly the cost Task 76.6 was written to remove.
    """
    yaml = pytest.importorskip("yaml")
    jobs = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))["jobs"]

    for name, job in jobs.items():
        if name == "fast":
            continue
        condition = str(job.get("if") or "")
        assert "github.event_name" in condition and "push" in condition, (
            f"job {name} has no condition excluding push, so it runs on every "
            f"push (condition was {condition!r})"
        )

def test_bootstrap_sh_structure():
    """Verify that scripts/bootstrap.sh has the correct structure, permissions, and POSIX commands."""
    assert BOOTSTRAP_SH.exists(), "scripts/bootstrap.sh must exist"
    content = BOOTSTRAP_SH.read_text(encoding="utf-8")

    # POSIX shebang and flags
    assert content.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in content

    # Compiler probe and compilation flags
    assert "gcc" in content
    assert "clang" in content
    assert "-std=c99" in content
    assert "-O2" in content
    assert "-I runtime" in content
    assert "-lm" in content
    assert "-lpthread" in content

    # Self-hosting bootstrap steps
    assert "bin/velo build src/main.vl -o bin/velo_gen2" in content
    assert "bin/velo_gen2 build src/main.vl -o bin/velo_gen3" in content
    assert "check_determinism.py" in content
    assert "--quick" in content or "-q" in content
    assert "--full" in content

def test_bootstrap_bat_structure():
    """Verify that scripts/bootstrap.bat supports --full for 3-stage self-hosting verification."""
    assert BOOTSTRAP_BAT.exists(), "scripts/bootstrap.bat must exist"
    content = BOOTSTRAP_BAT.read_text(encoding="utf-8")

    assert "bootstrap.c" in content
    assert "--full" in content
    assert "bin\\velo.exe build src/main.vl -o bin\\velo_gen2.exe" in content
    assert "bin\\velo_gen2.exe build src/main.vl -o bin\\velo_gen3.exe" in content
    assert "check_determinism.py" in content

def test_check_determinism_script_runs():
    """Verify that scripts/check_determinism.py executes and confirms SHA-256 fixed-point determinism."""
    assert CHECK_DET.exists(), "scripts/check_determinism.py must exist"
    res = subprocess.run([sys.executable, str(CHECK_DET)], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0, f"check_determinism.py failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "SHA-256 MATCH" in res.stdout


def _run_determinism_with_encoding(encoding):
    """Run the determinism script with the CHILD's stdout forced to `encoding`.

    PYTHONIOENCODING makes the encoding explicit on every platform, so the
    test never inspects or depends on the host console (a Windows CI runner
    and a Linux runner take the same path). This is the same mechanism a
    cp1252 console uses, without needing one.
    """
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = encoding
    # Make sure no ambient UTF-8 mode masks the encoding under test.
    env.pop("PYTHONUTF8", None)
    return subprocess.run(
        [sys.executable, str(CHECK_DET)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=600,
    )


def test_check_determinism_is_encoding_independent():
    """Task 66.2: the determinism check must succeed under any codec.

    This is the contract that replaced the Task 66.1 red row. The script was
    printing a check mark and an em dash, so a cp1252 console raised
    UnicodeEncodeError *after* the hashes had matched and the release gate
    exited 1 for no reason. Its output is now ASCII only.

    The codecs are exercised through the child's `PYTHONIOENCODING`, so the
    assertion never inspects the host console and behaves identically on a
    Windows runner and a Linux runner.
    """
    for encoding in ("cp1252", "utf-8", "ascii", "latin-1"):
        res = _run_determinism_with_encoding(encoding)
        blob = res.stdout + res.stderr
        assert res.returncode == 0, f"{encoding}: expected exit 0, got {res.returncode}:\n{blob}"
        assert "Gen2:" in res.stdout, f"{encoding}: no Gen2 hash:\n{blob}"
        assert "Gen3:" in res.stdout, f"{encoding}: no Gen3 hash:\n{blob}"
        assert "SHA-256 MATCH" in res.stdout, f"{encoding}: no match line:\n{blob}"
        assert "UnicodeEncodeError" not in blob, f"{encoding}: still raising:\n{blob}"

        # The match line is only meaningful if the two hashes it reports are
        # actually equal: a comparison that broke and printed the same label
        # twice would still satisfy the assertions above.
        hashes = [
            line.split(":", 1)[1].strip()
            for line in res.stdout.splitlines()
            if line.startswith(("Gen2:", "Gen3:"))
        ]
        assert len(hashes) == 2, f"{encoding}: expected two hash lines:\n{blob}"
        assert hashes[0] == hashes[1], f"{encoding}: reported hashes differ:\n{blob}"
        assert len(hashes[0]) == 64, f"{encoding}: not a SHA-256 digest: {hashes[0]!r}"
        assert all(c in "0123456789abcdef" for c in hashes[0]), (
            f"{encoding}: digest is not lowercase hex: {hashes[0]!r}"
        )


def test_check_determinism_output_is_ascii():
    """The script's own source must not smuggle non-ASCII into its output.

    Encoding-independence is a property of the bytes this script prints, so it
    is checked at the source: a future edit that adds a glyph would reintroduce
    the cp1252 crash even though the behavioural test above still passed on a
    UTF-8 host.
    """
    source = CHECK_DET.read_text(encoding="utf-8")
    non_ascii = [
        (lineno, line)
        for lineno, line in enumerate(source.splitlines(), 1)
        if any(ord(ch) > 127 for ch in line)
    ]
    assert not non_ascii, (
        "scripts/check_determinism.py must stay ASCII-only so its output "
        "cannot raise UnicodeEncodeError on a cp1252 console; found:\n  "
        + "\n  ".join(f"line {n}: {text!r}" for n, text in non_ascii)
    )

def test_velo_accepts_clang_compiler_flag():
    """Verify that Velo CLI accepts --cc clang without rejecting it as an unknown backend."""
    if not VELO_EXE.exists():
        pytest.skip("bin/velo not built")
    
    # Check help text
    res_help = subprocess.run([str(VELO_EXE), "help"], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res_help.returncode == 0
    assert "--cc gcc|clang|cl" in res_help.stdout

    # Test invalid vs accepted cc backend diagnostic
    res_unknown = subprocess.run([str(VELO_EXE), "check", "examples/01_hello.vl", "--cc", "bad_compiler"], cwd=str(REPO_ROOT), capture_output=True, text=True)
    # When --cc is passed to check/build, bad_compiler error should mention clang
    res_build_bad = subprocess.run([str(VELO_EXE), "build", "examples/01_hello.vl", "--cc", "bad_compiler"], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert "Expected 'gcc', 'clang', or 'cl'" in res_build_bad.stdout or "Expected 'gcc', 'clang', or 'cl'" in res_build_bad.stderr

