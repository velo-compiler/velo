"""Codegen-lane errors must fail the build, not just print a diagnostic.

Interpolation and intrinsic lowering re-enter the type checker during emission,
so a defect confined to that lane used to print `[Velo Error]`, still write the
C, still report `Successfully built binary!`, and still exit 0 - the baked-in
fallback then rendered the raw `{...}` text at runtime. Only `velo check` saw it.

The gate lives in `compile_source_to_c_test_opts` (src/backend/driver.vl): after
`emit_translation_unit`, a non-zero `st.error_count` returns null, which every
CLI verb already treats as failure. Stage 1 is a frozen reference tool and is
asserted here only for the divergences it shares (see gaps.md).
"""
import os
import subprocess
import sys

import pytest

# `{s.len()}` - `s` is a string, so member access is resolved in the emit lane.
INTERP_MEMBER_ERROR = """use std.io

act main() -> i32 {
    let s = "x"
    io.println("value is {s.len()}")
    return 0
}
"""

# `{"a" + "b"}` inside interpolation takes the same re-entry path. The inner
# quotes must reach the .vl file escaped, so each backslash is written twice.
INTERP_CONCAT_ERROR = """use std.io

act main() -> i32 {
    io.println("joined {\\"a\\" + \\"b\\"}")
    return 0
}
"""

VALID_PROGRAM = """use std.io

act main() -> i32 {
    let n: i64 = 21
    io.println("ok {n * 2}")
    return 0
}
"""


def _write(tmp_path, name, content):
    p = tmp_path / name
    with open(p, "w", newline="\n", encoding="utf-8") as fh:
        fh.write(content)
    return str(p)


@pytest.fixture(scope="module", autouse=True)
def _require_native():
    if not os.path.exists("bin/velo.exe"):
        pytest.skip("bin/velo.exe not built; skipping native tests")


def _native(args):
    return subprocess.run(["bin/velo.exe"] + args, capture_output=True, text=True)


@pytest.mark.parametrize("source", [INTERP_MEMBER_ERROR, INTERP_CONCAT_ERROR],
                         ids=["member-access", "string-concat"])
def test_build_fails_and_does_not_claim_success(tmp_path, source):
    path = _write(tmp_path, "bad.vl", source)
    out = str(tmp_path / "bad.exe")
    result = _native(["build", path, "-o", out])
    blob = result.stdout + result.stderr
    assert result.returncode != 0, blob
    assert "Code generation failed" in blob
    assert "Successfully built" not in blob
    assert not os.path.exists(out), "binary must not be produced"


@pytest.mark.parametrize("source", [INTERP_MEMBER_ERROR, INTERP_CONCAT_ERROR],
                         ids=["member-access", "string-concat"])
def test_run_fails_and_never_executes_the_program(tmp_path, source):
    path = _write(tmp_path, "bad_run.vl", source)
    result = _native(["run", path])
    blob = result.stdout + result.stderr
    # Pre-fix this built the broken binary, reported success and executed it.
    assert result.returncode != 0, blob
    assert "Code generation failed" in blob
    assert "Successfully built" not in blob


def test_emit_c_fails_and_writes_no_translation_unit(tmp_path):
    path = _write(tmp_path, "bad_emit.vl", INTERP_MEMBER_ERROR)
    out = str(tmp_path / "bad_emit.c")
    result = _native(["emit-c", path, "-o", out])
    assert result.returncode != 0, result.stdout + result.stderr
    assert not os.path.exists(out), "no C may be written for a failed codegen"


def test_diagnostic_wording_is_preserved(tmp_path):
    """The gate must not swallow the original message - it is the user's only clue."""
    path = _write(tmp_path, "bad_wording.vl", INTERP_MEMBER_ERROR)
    result = _native(["build", path, "-o", str(tmp_path / "bad_wording.exe")])
    blob = result.stdout + result.stderr
    assert "[Velo Error]" in blob
    assert "Member access on non-struct type" in blob


def test_check_still_flags_the_same_defect(tmp_path):
    path = _write(tmp_path, "bad_check.vl", INTERP_MEMBER_ERROR)
    result = _native(["check", path])
    assert result.returncode != 0


def test_valid_interpolation_still_builds_and_runs(tmp_path):
    """Over-blocking guard: the gate must not reject a clean program."""
    path = _write(tmp_path, "good.vl", VALID_PROGRAM)
    out = str(tmp_path / "good.exe")
    built = _native(["build", path, "-o", out])
    assert built.returncode == 0, built.stdout + built.stderr
    assert "Successfully built" in built.stdout + built.stderr
    ran = _native(["run", path])
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert "ok 42" in ran.stdout
