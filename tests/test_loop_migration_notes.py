"""
Task 68.6: the migration notes in SPEC 7.2 item 9.1 are executable.

The notes claim three things, and each is asserted here rather than trusted:

* every `velo` example in the section compiles and runs;
* a bound cast to `i32` really does select an `int32_t` induction, which is
  the pattern the notes recommend when a narrow induction is wanted;
* a wide bound really does iterate wide, and a truncated cast really does
  reproduce the old (now-unsupported) wrapped values, so the notes are not
  describing behaviour the compiler does not have.

A migration note that does not compile is worse than no note: it is the only
document a user reads after their loop starts producing different numbers.
"""
import re
import sys
from pathlib import Path

import pytest

from conftest import velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()

sys.path.insert(0, str(REPO_ROOT / "tests"))
from test_loop_induction_width import (  # noqa: E402
    build_and_run,
    emit_c,
    loop_header,
)

SPEC = REPO_ROOT / "docs" / "SPECIFICATION.md"
SECTION_HEADING = "##### 9.1 Migration from pre-Phase-68 loop semantics"


def migration_section() -> str:
    text = SPEC.read_text(encoding="utf-8")
    assert "#### 9. Induction Width & Overflow-Free Termination" in text
    assert SECTION_HEADING in text, "SPEC 7.2 item 9.1 migration notes are missing"
    return text.split(SECTION_HEADING, 1)[1].split("### 7.3 Pattern Matching", 1)[0]


def velo_examples() -> list:
    if not VELO_EXE.exists():
        pytest.skip(f"{VELO_EXE} is not built")
    return re.findall(r"```velo\n(.*?)\n```", migration_section(), re.DOTALL)


def test_migration_section_has_examples():
    examples = velo_examples() if VELO_EXE.exists() else re.findall(
        r"```velo\n(.*?)\n```", migration_section(), re.DOTALL
    )
    assert len(examples) >= 3, (
        f"expected at least 3 runnable examples in 7.2 item 9.1, got {len(examples)}"
    )


def test_migration_examples_compile_and_run(tmp_path):
    """Every `velo` block in the migration notes must compile and run."""
    for i, code in enumerate(velo_examples()):
        probe = tmp_path / f"migration_example_{i}.vl"
        probe.write_text(code, encoding="utf-8", newline="\n")
        res = build_and_run(code, timeout=20.0)
        assert res.returncode == 0, (
            f"migration example {i} failed to run:\n{code}\n{res.stdout}{res.stderr}"
        )


def test_notes_claim_cast_bound_narrows_is_true():
    """The notes say a cast bound selects an i32 induction. Verify it does.

    A dynamic bound hoists `__start`/`__end`/`__rev` temporaries, so the width
    shows up on those rather than on a bare `int32_t i` declaration; the row
    asserts the width of the hoisted temporaries, which is what the induction
    is initialised from.
    """
    header = loop_header(emit_c(
        "act main() -> i32 {\n"
        "    let lim: i64 = 3\n"
        "    loop i in 0..(lim as i32) { }\n"
        "    return 0\n"
        "}\n"
    ), "i")
    assert "int32_t" in header, (
        f"a cast bound did not select an int32_t induction:\n{header}"
    )
    assert "int64_t" not in header, (
        f"a cast bound still emitted a 64-bit induction:\n{header}"
    )


def test_notes_claim_wide_bound_stays_wide_is_true():
    """The notes say the uncast programme iterates in the wider type."""
    header = loop_header(emit_c(
        "act main() -> i32 {\n"
        "    let lim: i64 = 3\n"
        "    loop i in 0..lim { }\n"
        "    return 0\n"
        "}\n"
    ), "i")
    assert "int32_t i" not in header, (
        f"a wide bound was still narrowed without a cast:\n{header}"
    )
    assert "int64_t" in header, f"i64 bound did not produce a 64-bit induction:\n{header}"


def test_notes_claim_truncating_cast_reproduces_old_values_is_true():
    """The notes call truncating casts unsupported -- but they still reproduce
    the old defect, and saying so is only honest if it is observable.

    `3000000000 as i32` is negative, so `0..(lim as i32)` does not iterate a
    forward range at all: it is a *descending* range from 0. The row asserts
    that shape (0, -1, -2...) rather than a single value, because the single
    first value is a plausible 0 and would hide the defect.
    """
    res = build_and_run(
        "use std.io\n"
        "act main() -> i32 {\n"
        "    let lim: isize = 3000000000\n"
        "    mut n: i32 = 0\n"
        "    loop i in 0..(lim as i32) {\n"
        "        io.println_i64(i as i64)\n"
        "        n += 1\n"
        "        if n >= 3 { break }\n"
        "    }\n"
        "    return 0\n"
        "}\n"
    )
    assert res.returncode == 0, f"run failed:\n{res.stdout}{res.stderr}"
    assert res.stdout.split() == ["0", "-1", "-2"], (
        "a truncating cast no longer reproduces the wrong values the notes warn about: "
        f"{res.stdout.split()}"
    )


def test_notes_claim_inclusive_max_runs_three_times_is_true():
    """The notes say the inclusive-max loop always ran 3 times; it must now."""
    res = build_and_run(
        "use std.io\n"
        "act main() -> i32 {\n"
        "    mut n: i64 = 0\n"
        "    loop i in 2147483645..=2147483647 {\n"
        "        n += 1\n"
        "        if n > 10 { return 99 }\n"
        "    }\n"
        "    io.println_i64(n)\n"
        "    return 0\n"
        "}\n"
    )
    assert res.returncode == 0, f"run failed:\n{res.stdout}{res.stderr}"
    assert res.stdout.strip() == "3", (
        f"inclusive max loop did not run exactly 3 times: {res.stdout.strip()}"
    )
