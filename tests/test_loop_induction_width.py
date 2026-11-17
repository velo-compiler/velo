"""
Task 68.2 / 68.4 baseline: induction width and inclusive-boundary behaviour
for every loop codegen path.

Phase 68 is split by measurement, not by assumption. Task 68.1 found two
distinct defects and only one is about width:

* **W1 (width)** - a loop's induction type must not be *narrower* than its
  bounds. The live case is `isize`, which is missing from the range widening
  ladder in `src/analysis/range_checks.vl`, so `loop i in 0..isize_var`
  silently emits `int32_t` temporaries and iterates the wrong number of times.
* **W2 (termination)** - an inclusive range must not need to form a value
  outside the range to stop. `for (T i = start; i <= end; i++)` overflows when
  `end` is the maximum of `T`, at *every* width: signed is undefined behaviour
  (gcc deletes or shortens the loop under -O2), unsigned wraps to zero and the
  loop restarts from the bottom.

The two are verified separately here because a single "we made the induction
wider" claim would pass W1 and silently leave W2 broken. That is why this
module asserts per-path emitted types AND per-width boundary termination.

THIS FILE IS THE 68.2 AUDIT ARTEFACT
------------------------------------
Every loop codegen path in the backend is enumerated below with a test that
pins its induction representation, so a future path cannot be added (or an
existing one changed) without this table being updated:

    path                          induction  site
    range, literal bounds         from W1    range_gen.vl:19  (emit_range_loop_header)
    range, dynamic bounds         from W1    range_gen.vl:47
    count loop                    count type codegen_stmt.vl:270, W1 floor
    condition loop                i32        codegen_stmt.vl:279 (only `it`)
    infinite loop                 i32        codegen_stmt.vl:284 (only `it`)
    shelf `loop v of s`           usize      shelf_gen.vl:217
    ring  `loop v of r`           usize      ring_gen.vl:192
    map   `loop k of m`           usize      map_gen.vl:242

Tasks 68.3 and 68.4 make these rows pass. Until then the width and boundary
rows below are expected to fail on purpose: this is the red baseline for the
two fixes, exactly like Task 67.1 did for Phase 67.

Every generated C assertion reads the loop header that the compiler actually
emits, and every run assertion executes the compiled program, so neither half
can pass by inspecting a doc comment.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()


def get_build_env():
    env = dict(os.environ)
    ucrt_bin = cc_dir()
    if os.path.exists(ucrt_bin) and ucrt_bin not in env.get("PATH", ""):
        env["PATH"] = ucrt_bin + ";" + env.get("PATH", "")
    return env


def emit_c(source: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "probe.vl"
        out = Path(tmp) / "probe.c"
        src.write_text(source, encoding="utf-8", newline="\n")
        res = subprocess.run(
            [str(VELO_EXE), "emit-c", str(src), "-o", str(out)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(REPO_ROOT),
            env=get_build_env(),
        )
        assert res.returncode == 0, f"emit-c failed:\n{res.stdout}\n{res.stderr}"
        return out.read_text(encoding="utf-8")


def build_and_run(source: str, timeout: float = 10.0):
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "probe.vl"
        exe = Path(tmp) / ("probe.exe" if sys.platform == "win32" else "probe")
        src.write_text(source, encoding="utf-8", newline="\n")
        build = subprocess.run(
            [str(VELO_EXE), "build", str(src), "-o", str(exe)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(REPO_ROOT),
            env=get_build_env(),
        )
        assert build.returncode == 0, f"build failed:\n{build.stdout}\n{build.stderr}"
        try:
            return subprocess.run(
                [str(exe)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                cwd=str(REPO_ROOT),
            )
        except subprocess.TimeoutExpired:
            pytest.fail(f"execution timed out after {timeout}s (infinite loop)")


def loop_header(c_source: str, var: str) -> str:
    """The emitted `for (...)` header whose induction name starts with `var`.

    Collection loops name their index `_velo_lidx_<counter>`, so the match is
    a prefix on the declared name rather than an exact identifier.
    """
    hits = [
        line.strip()
        for line in c_source.splitlines()
        if line.strip().startswith("for (") and f"{var}" in line
    ]
    assert hits, f"no for-header declaring induction '{var}' was emitted"
    return hits[-1]


# ---------------------------------------------------------------------------
# Audit row 1-2: range loops must not narrow their bounds (W1).
# ---------------------------------------------------------------------------


def test_w1_range_isize_endpoint_is_not_narrowed():
    """`isize` is 64-bit; the induction must be 64-bit.

    Regression row for the actual live defect: `range_checks.vl` omitted
    `isize` from the widening ladder, so the emitted temporaries were
    `int32_t` and a bound above INT32_MAX truncated.

    The assertion is on *width*, not on a specific C spelling: `isize` maps to
    `ptrdiff_t` (the natural signed pointer-width type), not to `int64_t`, so
    demanding `int64_t` would reject the correct fix.
    """
    header = loop_header(emit_c(
        "act main() -> i32 {\n"
        "    let lim: isize = 3000000000\n"
        "    mut n: i32 = 0\n"
        "    loop i in 0..lim { n += 1 }\n"
        "    return n\n"
        "}\n"
    ), "i")
    assert "int32_t" not in header, f"isize range narrowed to int32_t:\n{header}"
    assert any(t in header for t in ("int64_t", "ptrdiff_t", "intptr_t", "long")), (
        f"isize range induction is not a 64-bit signed type:\n{header}"
    )


def test_w1_range_isize_endpoint_iterates_the_full_range():
    """The narrowing is observable: an isize bound above INT32_MAX truncates.

    A plain 3-iteration guard would pass even with the defect, because
    truncation changes *which* values are visited, not whether the loop
    starts. So both endpoints are above INT32_MAX and the visited values are
    asserted: narrowed to `int32_t`, `3000000000` becomes negative and the
    runtime direction flips, which the count and the observed values expose.
    """
    res = build_and_run(
        "use std.io\n"
        "act main() -> i32 {\n"
        "    let lo: isize = 3000000000\n"
        "    let hi: isize = 3000000003\n"
        "    mut n: i64 = 0\n"
        "    mut first: isize = 0\n"
        "    mut last: isize = 0\n"
        "    loop i in lo..hi {\n"
        "        if n == 0 { first = i }\n"
        "        last = i\n"
        "        n += 1\n"
        "        if n > 10 { io.println_i64(-1i64); return 99 }\n"
        "    }\n"
        "    io.println_i64(n)\n"
        "    io.println_i64(first as i64)\n"
        "    io.println_i64(last as i64)\n"
        "    return 0\n"
        "}\n"
    )
    assert res.returncode == 0, f"run failed:\n{res.stdout}{res.stderr}"
    lines = res.stdout.split()
    assert lines == ["3", "3000000000", "3000000002"], (
        f"isize range visited the wrong values (narrowed induction?): {lines}"
    )


def test_w1_range_i32_bounds_stay_i32():
    """No gratuitous widening: an i32 range keeps an int32_t induction."""
    header = loop_header(emit_c(
        "act main() -> i32 {\n"
        "    mut n: i32 = 0\n"
        "    loop i in 0..10 { n += 1 }\n"
        "    return n\n"
        "}\n"
    ), "i")
    assert "int32_t" in header, f"i32 range widened unnecessarily:\n{header}"
    assert "int64_t" not in header, f"i32 range widened:\n{header}"


@pytest.mark.parametrize("row", [
    ("i64", "0i64", "10i64", ("int64_t",)),
    ("u64", "0u64", "10u64", ("uint64_t",)),
    ("u32", "0u32", "10u32", ("uint32_t",)),
    ("usize", "0usize", "10usize", ("size_t",)),
    ("isize", "0isize", "10isize", ("ptrdiff_t", "int64_t")),
])
def test_w1_range_widens_to_the_endpoint_type(row):
    """Each endpoint type must drive the induction type (W1 ladder).

    `usize` and `isize` are both pointer-width; they map to `size_t` and
    `ptrdiff_t` respectively, so each row accepts its own C spelling and no
    other.
    """
    ty, start, end, expect = row
    header = loop_header(emit_c(
        "act main() -> i32 {\n"
        "    mut n: i32 = 0\n"
        f"    loop i in {start}..{end} {{ n += 1 }}\n"
        "    return n\n"
        "}\n"
    ), "i")
    assert any(t in header for t in expect), (
        f"{ty} range did not widen to {expect}:\n{header}"
    )


def test_w1_negative_signed_range_keeps_its_width():
    """A negative start must not collapse the induction to an unsigned type."""
    header = loop_header(emit_c(
        "act main() -> i32 {\n"
        "    mut n: i32 = 0\n"
        "    loop i in -5i64..5i64 { n += 1 }\n"
        "    return n\n"
        "}\n"
    ), "i")
    assert "int64_t" in header, f"negative i64 range lost its width:\n{header}"
    assert "uint" not in header, f"negative range became unsigned:\n{header}"


def test_w1_descending_wide_range_keeps_its_width():
    """Descending ranges go through the same header, so width must survive."""
    header = loop_header(emit_c(
        "act main() -> i32 {\n"
        "    mut n: i32 = 0\n"
        "    loop i in 10i64..0i64 { n += 1 }\n"
        "    return n\n"
        "}\n"
    ), "i")
    assert "int64_t" in header, f"descending i64 range narrowed:\n{header}"


# ---------------------------------------------------------------------------
# Audit row 2-4: count loops derive width from the count expression.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("decl,endpoint,expect", [
    ("c: u64 = 5u64", "c", "uint64_t"),
    ("c: i64 = 3000000000", "c", "int64_t"),
])
def test_w1_count_loop_uses_the_count_type(decl, endpoint, expect):
    header = loop_header(emit_c(
        "act main() -> i32 {\n"
        "    mut n: i32 = 0\n"
        f"    let {decl}\n"
        f"    loop {endpoint} {{ n += 1 }}\n"
        "    return n\n"
        "}\n"
    ), "it")
    assert expect in header, f"count loop did not use {expect}:\n{header}"


def test_w1_narrow_count_loop_has_an_i32_floor():
    """`loop 5` and `loop <u8>` iterate in int32_t, per the W1 floor."""
    header = loop_header(emit_c(
        "act main() -> i32 {\n"
        "    mut n: i32 = 0\n"
        "    loop 5 { n += it }\n"
        "    return n\n"
        "}\n"
    ), "it")
    assert "int32_t" in header, f"count loop lost its i32 floor:\n{header}"


# ---------------------------------------------------------------------------
# Audit row 5-6: condition and infinite loops keep an i32 `it` counter.
# ---------------------------------------------------------------------------


def test_condition_loop_counter_is_i32():
    header = loop_header(emit_c(
        "act main() -> i32 {\n"
        "    mut x: i32 = 3\n"
        "    loop x > 0 { x -= 1 }\n"
        "    return x\n"
        "}\n"
    ), "it")
    assert "int32_t" in header, f"condition loop counter changed width:\n{header}"


def test_infinite_loop_counter_is_i32():
    header = loop_header(emit_c(
        "act main() -> i32 {\n"
        "    mut n: i32 = 0\n"
        "    loop {\n"
        "        n += 1\n"
        "        if n > 2 { break }\n"
        "    }\n"
        "    return n\n"
        "}\n"
    ), "it")
    assert "int32_t" in header, f"infinite loop counter changed width:\n{header}"


# ---------------------------------------------------------------------------
# Audit row 7-9: collection loops iterate with a usize index.
# ---------------------------------------------------------------------------


def test_shelf_loop_index_is_usize():
    header = loop_header(emit_c(
        "act main() -> i32 {\n"
        "    let xs: shelf[i32] = shelf[1, 2]\n"
        "    mut t: i32 = 0\n"
        "    loop v of xs { t = t + v }\n"
        "    return t\n"
        "}\n"
    ), "_velo_lidx_")
    assert "usize" in header, f"shelf loop index is not usize:\n{header}"


def test_ring_loop_index_is_usize():
    header = loop_header(emit_c(
        "act main() -> i32 {\n"
        "    mut rq: ring[i32] = ring[]\n"
        "    rq.put(1)\n"
        "    mut t: i32 = 0\n"
        "    loop v of rq { t = t + v }\n"
        "    return t\n"
        "}\n"
    ), "_velo_lidx_")
    assert "usize" in header, f"ring loop index is not usize:\n{header}"


def test_map_loop_index_is_usize():
    header = loop_header(emit_c(
        "act main() -> i32 {\n"
        "    mut m: Map[string, i32] = map[\"a\": 1]\n"
        "    mut t: i32 = 0\n"
        "    loop k of m { t += 1 }\n"
        "    return t\n"
        "}\n"
    ), "_velo_lidx_")
    assert "usize" in header, f"map loop index is not usize:\n{header}"


# ---------------------------------------------------------------------------
# W2: inclusive ranges must terminate without forming an out-of-range value.
# These rows are width-independent by construction: each is run at the maximum
# of its own type, so widening the type cannot make them pass.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("row", [
    ("i32", "2147483645", "2147483647"),
    ("i64", "9223372036854775805", "9223372036854775807"),
])
def test_w2_inclusive_signed_max_terminates(row):
    """Three iterations over MAX-2..=MAX, at the maximum of the type.

    Before W2 this is undefined behaviour: the increment after the final
    iteration overflows, and gcc reports `iteration N invokes undefined
    behavior` and may drop the loop exit entirely.
    """
    ty, start, end = row
    res = build_and_run(
        "use std.io\n"
        "act main() -> i32 {\n"
        f"    mut n: i64 = 0\n"
        f"    loop i in {start}{ty}..={end}{ty} {{\n"
        "        n += 1\n"
        "        if n > 10 { io.println_i64(-1i64); return 99 }\n"
        "    }\n"
        "    io.println_i64(n)\n"
        "    return 0\n"
        "}\n"
    )
    assert res.returncode == 0, (
        f"{ty} inclusive-max loop did not terminate cleanly:\n{res.stdout}{res.stderr}"
    )
    assert res.stdout.strip() == "3", (
        f"{ty} inclusive-max loop ran {res.stdout.strip()!r} iterations, expected 3"
    )


@pytest.mark.parametrize("row", [
    ("u32", "4294967293u32", "4294967295u32"),
    ("u64", "18446744073709551613u64", "18446744073709551615u64"),
])
def test_w2_inclusive_unsigned_max_terminates(row):
    """Unsigned MAX wraps to 0 instead of UB, and restarts from the bottom."""
    ty, start, end = row
    res = build_and_run(
        "use std.io\n"
        "act main() -> i32 {\n"
        "    mut n: i64 = 0\n"
        f"    loop i in {start}..={end} {{\n"
        "        n += 1\n"
        "        if n > 10 { io.println_i64(-1i64); return 99 }\n"
        "    }\n"
        "    io.println_i64(n)\n"
        "    return 0\n"
        "}\n"
    )
    assert res.returncode == 0, (
        f"{ty} inclusive-max loop did not terminate cleanly:\n{res.stdout}{res.stderr}"
    )
    assert res.stdout.strip() == "3", (
        f"{ty} inclusive-max loop ran {res.stdout.strip()!r} iterations, expected 3"
    )


def test_w2_inclusive_descending_min_terminates():
    """The mirror case: descending to the type minimum must not wrap either.

    The full descending range is 4294967296 iterations, which is far too slow
    to run. Instead the loop starts three above the minimum and must stop
    after exactly three, which is the same boundary the ascending rows test
    from the other direction: the decrement after the final iteration would
    form MIN-1.
    """
    res = build_and_run(
        "use std.io\n"
        "act main() -> i32 {\n"
        "    mut n: i64 = 0\n"
        "    loop i in -2147483646i32..=-2147483648i32 {\n"
        "        n += 1\n"
        "        if n > 10 { io.println_i64(-1i64); return 99 }\n"
        "    }\n"
        "    io.println_i64(n)\n"
        "    return 0\n"
        "}\n"
    )
    assert res.returncode == 0, f"descending inclusive-min loop failed:\n{res.stderr}"
    assert res.stdout.strip() == "3", (
        f"descending inclusive-min loop ran {res.stdout.strip()!r} iterations, expected 3"
    )


def test_w2_inclusive_max_emits_an_equality_terminator():
    """The fix is structural: no `i <= end` test that can overflow.

    This asserts the emitted shape rather than only the runtime result, so a
    future change that reintroduces the `<=` form fails here even if the
    platform happens to tolerate the overflow.
    """
    header = loop_header(emit_c(
        "act main() -> i32 {\n"
        "    mut n: i32 = 0\n"
        "    loop i in 0..=5 { n += 1 }\n"
        "    return n\n"
        "}\n"
    ), "i")
    assert "i <= 5" not in header, (
        f"inclusive range still uses an overflowing `<=` test:\n{header}"
    )


# ---------------------------------------------------------------------------
# W2 semantics that equality alone would get wrong. These are the cases that
# forced the terminator to be a step-aware distance test; each was found by
# running the first (equality-based) implementation and watching it hang or
# under-count.
# ---------------------------------------------------------------------------


def test_w2_inclusive_step_visits_the_whole_ladder():
    """`0..=10:3` yields 0,3,6,9 — equality on `end` would never fire.

    An `if (i == end) break;` terminator loops forever here, because 9+3 skips
    past 10. The distance test stops as soon as fewer than `step` remain.
    """
    res = build_and_run(
        "use std.io\n"
        "act main() -> i32 {\n"
        "    mut n: i64 = 0\n"
        "    loop i in 0..=10:3 {\n"
        "        io.println_i64(i as i64)\n"
        "        n += 1\n"
        "        if n > 20 { return 99 }\n"
        "    }\n"
        "    return 0\n"
        "}\n"
    )
    assert res.returncode == 0, f"stepped inclusive loop did not finish:\n{res.stdout}"
    assert res.stdout.split() == ["0", "3", "6", "9"], (
        f"stepped inclusive ladder wrong: {res.stdout.split()}"
    )


def test_w2_inclusive_continue_still_advances():
    """`continue` must advance; a terminator placed below the label would hang.

    The exit test must sit AFTER `__loop_cont_N` so `goto __loop_cont_N`
    reaches both the test and the increment.
    """
    res = build_and_run(
        "use std.io\n"
        "act main() -> i32 {\n"
        "    mut n: i64 = 0\n"
        "    loop i in 0..=5 {\n"
        "        if i == 2 { continue }\n"
        "        n += 1\n"
        "        if n > 20 { return 99 }\n"
        "    }\n"
        "    io.println_i64(n)\n"
        "    return 0\n"
        "}\n"
    )
    assert res.returncode == 0, f"continue hung the inclusive loop:\n{res.stdout}"
    assert res.stdout.strip() == "5", (
        f"continue skipped the increment: {res.stdout.strip()}"
    )


def test_w2_dynamic_descending_inclusive_counts_every_value():
    """A runtime `start > end` must use the runtime direction, not a static guess.

    The first implementation tested `end - i` unconditionally, which for a
    descending dynamic range is negative and stops after one iteration. The
    direction is a runtime temporary (`__rev_<v>`), so the terminator has to
    branch on it.
    """
    res = build_and_run(
        "use std.io\n"
        "act main() -> i32 {\n"
        "    let lo: i32 = 1\n"
        "    let hi: i32 = 4\n"
        "    mut acc: i64 = 0\n"
        "    loop i in hi..=lo { acc += 1 }\n"
        "    io.println_i64(acc)\n"
        "    let a: i32 = 1\n"
        "    let b: i32 = 4\n"
        "    mut up: i64 = 0\n"
        "    loop i in a..=b {\n"
        "        up += i as i64\n"
        "    }\n"
        "    io.println_i64(up)\n"
        "    return 0\n"
        "}\n"
    )
    assert res.returncode == 0, f"dynamic inclusive loop failed:\n{res.stderr}"
    assert res.stdout.split() == ["4", "10"], (
        f"dynamic direction mishandled: {res.stdout.split()}"
    )


def test_w2_inclusive_equal_endpoints_run_exactly_once():
    """`n..=n` is one iteration, with and without a step."""
    res = build_and_run(
        "use std.io\n"
        "act main() -> i32 {\n"
        "    mut a: i64 = 0\n"
        "    loop i in 2..=2 { a += 1 }\n"
        "    mut b: i64 = 0\n"
        "    loop i in 2..=2:5 { b += 1 }\n"
        "    io.println_i64(a)\n"
        "    io.println_i64(b)\n"
        "    return 0\n"
        "}\n"
    )
    assert res.returncode == 0, f"equal-endpoint loop failed:\n{res.stderr}"
    assert res.stdout.split() == ["1", "1"], (
        f"equal endpoints wrong: {res.stdout.split()}"
    )


def test_w2_exclusive_range_shape_is_unchanged():
    """`..` keeps its plain `<` test: it cannot overflow, so W2 must not touch it."""
    header = loop_header(emit_c(
        "act main() -> i32 {\n"
        "    mut n: i32 = 0\n"
        "    loop i in 0..5 { n += 1 }\n"
        "    return n\n"
        "}\n"
    ), "i")
    assert "i < 5" in header, f"exclusive range lost its `<` test:\n{header}"
