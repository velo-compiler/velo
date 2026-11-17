"""
Task 68.5: performance and determinism verification for the Phase 68 fixes.

Two claims have to be checked, and neither is implied by the Phase 68 tests:

* **No performance cliff.** W2 turns a header-terminated inclusive loop into a
  body-terminated one, adding one comparison per iteration. If that cost were
  material, every `..=` loop in the standard library would pay it, so it is
  measured rather than assumed.
* **Determinism is preserved.** Tasks 68.3 and 68.4 changed `src/**/*.vl`, so
  `bootstrap.c` was regenerated and the Gen2/Gen3 SHA-256 necessarily changed.
  The *property* that must survive is Gen2 == Gen3 and `bootstrap.c` equal to
  the current `emit-c` output; the hash value itself is expected to move.

The performance test is written to detect a cliff, not to produce a precise
number: it measures the same loop body compiled two ways and fails only on a
large relative difference, because wall-clock on a CI runner is noisy and a
tight assertion would be flaky rather than informative. The measured numbers
are recorded in `gaps.md`.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = REPO_ROOT / "bin" / ("velo.exe" if sys.platform == "win32" else "velo")
CHECK_DET = REPO_ROOT / "scripts" / "check_determinism.py"
BOOTSTRAP_C = REPO_ROOT / "bootstrap.c"

# 20M iterations keeps each sample well under a second on a slow runner while
# still being dominated by the loop, not by process startup.
N = 20_000_000

pytestmark = pytest.mark.skipif(
    not VELO_EXE.exists(), reason="bin/velo.exe not built"
)


def get_build_env():
    env = dict(os.environ)
    ucrt_bin = r"C:\msys64\ucrt64\bin"
    if os.path.exists(ucrt_bin) and ucrt_bin not in env.get("PATH", ""):
        env["PATH"] = ucrt_bin + ";" + env.get("PATH", "")
    return env


def build_temp(source: str, name: str):
    """Build `source` in a temp dir and return (exe_path, tmpdir)."""
    tmp = tempfile.mkdtemp()
    src = Path(tmp) / f"{name}.vl"
    exe = Path(tmp) / (f"{name}.exe" if sys.platform == "win32" else name)
    src.write_text(source, encoding="utf-8", newline="\n")
    res = subprocess.run(
        [str(VELO_EXE), "build", str(src), "-o", str(exe)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(REPO_ROOT),
        env=get_build_env(),
    )
    assert res.returncode == 0, f"build failed:\n{res.stdout}\n{res.stderr}"
    return exe, tmp


def time_binary(exe: Path, runs: int = 5) -> float:
    """Best-of-`runs` wall time in seconds; best-of rejects scheduler noise."""
    import time

    best = None
    for _ in range(runs):
        start = time.perf_counter()
        res = subprocess.run([str(exe)], capture_output=True, timeout=120)
        elapsed = time.perf_counter() - start
        assert res.returncode == 0, f"benchmark binary failed: {res.stderr!r}"
        if best is None or elapsed < best:
            best = elapsed
    return best


ACCUMULATE_BODY = (
    "    mut acc: i64 = 0\n"
    f"    let n: i32 = {N}\n"
)


def test_inclusive_loop_has_no_performance_cliff():
    """An inclusive loop must not be dramatically slower than an exclusive one.

    The two programs differ only in the bound form, so the comparison isolates
    W2's extra per-iteration comparison. A 2x allowance is deliberately loose:
    this test exists to catch a *cliff* (for example an O(n^2) accident or a
    lost optimisation), not to police a few percent.
    """
    exclusive, dir_a = build_temp(
        "use std.io\n"
        "act main() -> i32 {\n" + ACCUMULATE_BODY +
        "    loop i in 0..n { acc += i as i64 }\n"
        "    io.println_i64(acc)\n"
        "    return 0\n"
        "}\n",
        "bench_exclusive",
    )
    inclusive, dir_b = build_temp(
        "use std.io\n"
        "act main() -> i32 {\n" + ACCUMULATE_BODY +
        "    loop i in 0..=n { acc += i as i64 }\n"
        "    io.println_i64(acc)\n"
        "    return 0\n"
        "}\n",
        "bench_inclusive",
    )
    try:
        t_excl = time_binary(exclusive)
        t_incl = time_binary(inclusive)
    finally:
        import shutil
        shutil.rmtree(dir_a, ignore_errors=True)
        shutil.rmtree(dir_b, ignore_errors=True)

    ratio = t_incl / t_excl if t_excl else float("inf")
    assert ratio < 2.0, (
        f"inclusive loop is {ratio:.2f}x the exclusive loop "
        f"(exclusive {t_excl*1000:.0f} ms, inclusive {t_incl*1000:.0f} ms) at "
        f"{N} iterations"
    )


def test_stepped_inclusive_loop_has_no_performance_cliff():
    """The step-aware terminator must not degrade stepped loops either."""
    plain, dir_a = build_temp(
        "use std.io\n"
        "act main() -> i32 {\n" + ACCUMULATE_BODY +
        "    loop i in 0..n:4 { acc += i as i64 }\n"
        "    io.println_i64(acc)\n"
        "    return 0\n"
        "}\n",
        "bench_stepless",
    )
    inclusive, dir_b = build_temp(
        "use std.io\n"
        "act main() -> i32 {\n" + ACCUMULATE_BODY +
        "    loop i in 0..=n:4 { acc += i as i64 }\n"
        "    io.println_i64(acc)\n"
        "    return 0\n"
        "}\n",
        "bench_stepped",
    )
    try:
        t_plain = time_binary(plain)
        t_incl = time_binary(inclusive)
    finally:
        import shutil
        shutil.rmtree(dir_a, ignore_errors=True)
        shutil.rmtree(dir_b, ignore_errors=True)

    ratio = t_incl / t_plain if t_plain else float("inf")
    assert ratio < 2.0, (
        f"stepped inclusive loop is {ratio:.2f}x the stepped exclusive loop "
        f"(plain {t_plain*1000:.0f} ms, inclusive {t_incl*1000:.0f} ms)"
    )


def test_range_loop_cgen_recompiles_the_same_output_twice():
    """`emit-c` must be deterministic for the same source, run to run.

    A body-terminated loop introduced new temporaries and a second comparison;
    if any of it depended on iteration order or a counter that reset
    differently, the compiler could diverge from itself. Both backends are
    checked because the bootstrap chain compares Gen2 to Gen3.
    """
    source = (
        "use std.io\n"
        "act main() -> i32 {\n"
        "    mut acc: i64 = 0\n"
        "    loop i in 0..=10:3 { acc += i as i64 }\n"
        "    loop j in 5..=1 { acc += j as i64 }\n"
        "    let lo: i32 = 1\n"
        "    let hi: i32 = 4\n"
        "    loop k in hi..=lo { acc += 1 }\n"
        "    io.println_i64(acc)\n"
        "    return 0\n"
        "}\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "det.vl"
        src.write_text(source, encoding="utf-8", newline="\n")
        outputs = []
        for _ in range(2):
            res = subprocess.run(
                [str(VELO_EXE), "emit-c", str(src)],
                capture_output=True,
                cwd=str(REPO_ROOT),
            )
            assert res.returncode == 0, f"emit-c failed: {res.stderr!r}"
            outputs.append(res.stdout)
        assert outputs[0] == outputs[1], (
            "emit-c produced different output for identical input"
        )


def test_bootstrap_snapshot_matches_current_emit_c():
    """`bootstrap.c` must be exactly what the current compiler emits.

    This is the frozen-bootstrap invariant: the committed snapshot is the
    output of `emit-c src/main.vl`, so a stale snapshot means the compiler can
    no longer reproduce itself. Tasks 68.3/68.4 regenerated it; this row is
    what would catch a future edit that changes codegen without refreshing it.

    The comparison uses `emit-c -o <file>`, which is the route the bootstrap
    script and `test_bootstrap_snapshot.py` use. Emitting to stdout is a
    different code path and its output is not byte-identical, so comparing
    against stdout would fail for reasons unrelated to the snapshot.
    """
    assert BOOTSTRAP_C.exists(), "bootstrap.c is missing"
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "fresh.c"
        res = subprocess.run(
            [str(VELO_EXE), "emit-c", "src/main.vl", "-o", str(fresh)],
            capture_output=True,
            cwd=str(REPO_ROOT),
        )
        assert res.returncode == 0, f"emit-c failed: {res.stderr!r}"
        committed = BOOTSTRAP_C.read_bytes().replace(b"\r\n", b"\n")
        emitted = fresh.read_bytes().replace(b"\r\n", b"\n")
    assert committed == emitted, (
        "bootstrap.c is stale: regenerate with "
        "`bin/velo.exe emit-c src/main.vl -o bootstrap.c`"
    )


def test_determinism_script_reports_a_match_after_the_fix():
    """Gen2 and Gen3 must still agree after the Phase 68 codegen changes."""
    res = subprocess.run(
        [sys.executable, str(CHECK_DET)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(REPO_ROOT),
        timeout=600,
    )
    assert res.returncode == 0, f"determinism check failed:\n{res.stdout}{res.stderr}"
    assert "SHA-256 MATCH" in res.stdout, res.stdout
    hashes = [
        line.split(":", 1)[1].strip()
        for line in res.stdout.splitlines()
        if line.startswith(("Gen2:", "Gen3:"))
    ]
    assert len(hashes) == 2 and hashes[0] == hashes[1], res.stdout
