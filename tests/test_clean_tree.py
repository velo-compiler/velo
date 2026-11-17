"""Tests for the clean-tree gate (Phase 67, Task 67.4).

The gate exists to keep the Phase 67.1-67.3 defect from returning: eight Velo
tests wrote into a relative `scratch/` without creating it, passed only because
an earlier run had left the directory behind, and went unnoticed for exactly as
long as the developer tree carried it. Each of those tests is now self-contained,
but a test that is merely *fixed* can regress silently. This module pins the
enforcement instead.

Two things are tested, and they are different claims:

* the gate is **sound** -- it fails for every way a run can dirty the tree
  (new file, new empty directory, modified tracked file) and passes for build
  products;
* the gate is **load-bearing** -- running it against Velo suites that are known
  to leave artifacts must fail, and against the fixed suites must pass. A gate
  that never fires is not a gate, and a passing summary line would look
  identical either way.

Everything runs against a throwaway git repository in `tmp_path`, so the real
worktree is never touched.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
GATE = REPO_ROOT / "scripts" / "check_clean_tree.py"
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"
VELO_EXE = velo_exe()


def run_gate(root, *command, timeout=120):
    return subprocess.run(
        [sys.executable, str(GATE), "--root", str(root), "--", *command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def make_repo(path: Path) -> Path:
    """A git repository with one tracked file, so `git status` is meaningful."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=str(path), check=True)
    (path / "tracked.txt").write_text("hi\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=str(path), check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@example.com", "-c", "user.name=t",
         "commit", "-qm", "init"],
        cwd=str(path),
        check=True,
    )
    return path


def py(code: str):
    return [sys.executable, "-c", code]


# ---------------------------------------------------------------------------
# Soundness: the gate must fire for every kind of workspace leak.
# ---------------------------------------------------------------------------


def test_gate_fails_on_new_file(tmp_path):
    repo = make_repo(tmp_path / "repo")
    res = run_gate(repo, *py("open('stray.txt','w').write('x')"))
    assert res.returncode == 1, f"gate missed a new file:\n{res.stdout}{res.stderr}"
    assert "stray.txt" in res.stdout


def test_gate_fails_on_new_empty_directory(tmp_path):
    """The case `git status` cannot see, and the exact Phase 67 state.

    Git does not track empty directories, so an ambient `scratch/` left behind
    by a suite that cleaned its files is invisible to git while still being the
    state every later suite then depends on. A git-only gate would have passed
    on the very tree Task 67.3 was fixing.
    """
    repo = make_repo(tmp_path / "repo")
    res = run_gate(repo, *py("import os;os.makedirs('scratch')"))
    assert res.returncode == 1, f"gate missed an empty directory:\n{res.stdout}{res.stderr}"
    assert "scratch/" in res.stdout


def test_gate_fails_on_modified_tracked_file(tmp_path):
    repo = make_repo(tmp_path / "repo")
    res = run_gate(repo, *py("open('tracked.txt','a').write('x')"))
    assert res.returncode == 1, f"gate missed a tracked modification:\n{res.stdout}{res.stderr}"
    assert "tracked.txt" in res.stdout


def test_gate_fails_on_nested_leak(tmp_path):
    repo = make_repo(tmp_path / "repo")
    res = run_gate(repo, *py(
        "import os;os.makedirs('scratch/deep/er',exist_ok=True);"
        "open('scratch/deep/er/f.txt','w').write('x')"
    ))
    assert res.returncode == 1, f"gate missed a nested leak:\n{res.stdout}{res.stderr}"
    assert "scratch/" in res.stdout


# ---------------------------------------------------------------------------
# Precision: build products must not be reported, or the gate would be
# disabled as noise and stop enforcing anything.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("code,path", [
    ("import os;os.makedirs('bin')", "bin/"),
    ("import os;os.makedirs('.velo_cache')", ".velo_cache/"),
    ("import os;os.makedirs('__pycache__')", "__pycache__/"),
    ("open('x.pyc','wb').write(b'')", "x.pyc"),
    ("open('prog.exe','wb').write(b'')", "prog.exe"),
    ("open('obj.o','wb').write(b'')", "obj.o"),
])
def test_gate_allows_build_artifacts(tmp_path, code, path):
    repo = make_repo(tmp_path / "repo")
    res = run_gate(repo, *py(code))
    assert res.returncode == 0, (
        f"gate rejected build artefact {path}:\n{res.stdout}{res.stderr}"
    )
    assert path not in res.stdout


def test_gate_passes_on_clean_run(tmp_path):
    repo = make_repo(tmp_path / "repo")
    res = run_gate(repo, *py("print('ok')"))
    assert res.returncode == 0, f"gate failed on a clean run:\n{res.stdout}{res.stderr}"
    assert "CLEAN-TREE GATE: no leaked paths" in res.stdout


# ---------------------------------------------------------------------------
# Failure propagation: a failing command must never read as a passing gate.
# ---------------------------------------------------------------------------


def test_gate_propagates_command_failure(tmp_path):
    repo = make_repo(tmp_path / "repo")
    res = run_gate(repo, *py("import sys;sys.exit(7)"))
    assert res.returncode == 7, (
        f"gate swallowed the command's exit status:\n{res.stdout}{res.stderr}"
    )


def test_gate_reports_leak_before_failure_code(tmp_path):
    """A dirty tree plus a failed run must exit 1, not the command's code.

    Both are problems, but the leak is the one that makes the workspace
    unreliable, and reporting the command's own code would suggest the tree was
    clean.
    """
    repo = make_repo(tmp_path / "repo")
    res = run_gate(repo, *py(
        "import os,sys;os.makedirs('scratch');sys.exit(3)"
    ))
    assert res.returncode == 1, f"leak did not take precedence:\n{res.stdout}{res.stderr}"
    assert "scratch/" in res.stdout


def test_gate_requires_a_command(tmp_path):
    res = subprocess.run(
        [sys.executable, str(GATE)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert res.returncode != 0, "gate accepted an invocation with no command"
    assert "no command given" in (res.stdout + res.stderr)


# ---------------------------------------------------------------------------
# Load-bearing: run the gate against the real Velo suites it is meant to guard.
# ---------------------------------------------------------------------------


pytestmark_velo = pytest.mark.skipif(
    not VELO_EXE.exists(), reason="bin/velo.exe not built"
)


@pytestmark_velo
def test_gate_passes_for_self_contained_vs_suites(tmp_path):
    """The suites fixed in 67.2/67.3 must leave a temp cwd untouched.

    This is the property the gate asserts in CI, checked here against the real
    compiler: the workspace the suites run in is a git repository, so any
    relative write would be reported.

    Only suites that depend on nothing but their own `scratch/` are listed.
    `std/tests/fs/dir_test.vl`, `stat_test.vl` and
    `path_fs_module_import_test.vl` also read tracked repository paths
    (`README.md`, `src`, `std`), so they need `cwd=REPO_ROOT` and are covered by
    the CI job in the real checkout rather than by this temp-repo row. That
    dependency is documented in `gaps.md` Task 67.3.
    """
    repo = make_repo(tmp_path / "repo")
    for suite in (
        "fs/ops_test.vl",
        "io/handle_test.vl",
        "io/print_test.vl",
        "io/buffered_reader_test.vl",
        "io/buffered_writer_test.vl",
    ):
        res = run_gate(
            repo, str(VELO_EXE), "run", str(REPO_ROOT / "std" / "tests" / suite),
            timeout=300,
        )
        assert res.returncode == 0, (
            f"{suite} dirtied the working tree:\n{res.stdout}{res.stderr}"
        )

        assert res.returncode == 0, (
            f"{suite} dirtied the working tree:\n{res.stdout}{res.stderr}"
        )


@pytestmark_velo
def test_gate_fires_on_a_vs_suite_that_leaks(tmp_path):
    """A Velo program that creates `scratch/` must make the gate fail.

    Without this row the gate could be broken in the direction that matters
    most -- reporting clean for a program that leaks -- while the row above
    still passed, because "nothing leaked" and "the gate cannot see leaks" are
    indistinguishable from a green run.
    """
    repo = make_repo(tmp_path / "repo")
    probe = repo / "leaky.vl"
    probe.write_text(
        "use std.fs\n\n"
        "act main() -> i32 {\n"
        '    if !fs_create_dir_str("scratch") { return 1 }\n'
        '    if !fs_write_str("scratch/f.txt", "x") { return 2 }\n'
        "    return 0\n"
        "}\n",
        encoding="utf-8",
        newline="\n",
    )
    res = run_gate(repo, str(VELO_EXE), "run", str(probe), timeout=300)
    assert res.returncode == 1, (
        f"gate did not fire on a leaky Velo program:\n{res.stdout}{res.stderr}"
    )
    assert "scratch/" in res.stdout


# ---------------------------------------------------------------------------
# CI wiring: the gate only protects the tree if a job runs it.
# ---------------------------------------------------------------------------


def ci_job(name):
    """Return the parsed job dict from .github/workflows/ci.yml."""
    yaml = pytest.importorskip("yaml")
    workflow = yaml.safe_load((CI_YML).read_text(encoding="utf-8"))
    jobs = workflow.get("jobs", {})
    assert name in jobs, f"ci.yml has no '{name}' job; jobs: {sorted(jobs)}"
    return jobs[name]


def test_ci_has_a_clean_checkout_job():
    """Task 67.4: a job must run the suite with no untracked state.

    The existing matrix jobs all start from a fresh checkout too, so they
    would also catch these defects -- but only after the failure, and only as
    a test failure attributed to whichever suite happened to run first. A
    dedicated job states the invariant explicitly and names the leaked path.
    """
    job = ci_job("clean-checkout")
    steps = job["steps"]
    scripts = "\n".join(str(step.get("run", "")) for step in steps)

    assert "bootstrap.sh" in scripts, "clean-checkout must build the compiler"
    assert "scripts/check_clean_tree.py" in scripts, (
        "clean-checkout must run the suite under the clean-tree gate"
    )
    assert "pytest tests" in scripts, "clean-checkout must run the full suite"


def test_ci_clean_checkout_job_asserts_scratch_is_absent():
    """The job must fail loudly if a clean checkout contains `scratch/`.

    checkout gives a clean tree, so this is a cheap tripwire: if a future
    change commits a `scratch/` directory (or a test fixture starts creating
    one before the step), the suite would pass for the wrong reason and the
    gate would compare against an already-dirty baseline.
    """
    job = ci_job("clean-checkout")
    scripts = "\n".join(str(step.get("run", "")) for step in job["steps"])
    assert "if [ -e scratch ]" in scripts, (
        "clean-checkout must fail when a scratch/ directory exists"
    )


def test_ci_clean_checkout_gate_precedes_the_suite_in_the_same_step():
    """The gate must wrap the suite, not run as a sibling step.

    A separate `check_clean_tree.py` invocation with no command after it would
    exit on "no command given"; the gate is only meaningful when it is the
    process that launches pytest, so that its before-snapshot is taken before
    any test can create a file.
    """
    job = ci_job("clean-checkout")
    gate_steps = [
        step for step in job["steps"]
        if "check_clean_tree.py" in str(step.get("run", ""))
    ]
    assert len(gate_steps) == 1, (
        f"expected exactly one gate step, found {len(gate_steps)}"
    )
    run = str(gate_steps[0]["run"])
    assert "-- python3 -m pytest tests" in run, (
        f"the gate step must launch pytest itself:\n{run}"
    )
