"""
tests/test_large_ranges.py — Test Matrix for Large Endpoint Range Loops (Phase 55)

Verifies range loop direction detection, iteration counts, and emitted C
around INT32_MAX (2147483647), UINT32_MAX (4294967295), INT64_MAX (9223372036854775807),
and UINT64_MAX (18446744073709551615).

Establishes the Red Baseline for Phase 55 (Task 55.1).
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest


def get_build_env():
    """Returns an environment with ucrt64 GCC in PATH for compiling generated C."""
    env = dict(os.environ)
    ucrt_bin = r"C:\msys64\ucrt64\bin"
    if os.path.exists(ucrt_bin) and ucrt_bin not in env.get("PATH", ""):
        env["PATH"] = ucrt_bin + ";" + env.get("PATH", "")
    return env


def run_velo_source(source_code: str, timeout: float = 2.0) -> subprocess.CompletedProcess:
    """Compiles Velo source to an executable using bin/velo.exe build, then executes directly."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_path = Path(tmp_dir) / "test.vl"
        exe_path = Path(tmp_dir) / "test.exe"
        src_path.write_text(source_code, encoding="utf-8")

        build_res = subprocess.run(
            ["bin/velo.exe", "build", str(src_path), "-o", str(exe_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=get_build_env(),
            cwd=Path.cwd()
        )
        if build_res.returncode != 0:
            return build_res

        try:
            return subprocess.run(
                [str(exe_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
                cwd=Path.cwd()
            )
        except subprocess.TimeoutExpired as e:
            pytest.fail(f"Execution timed out after {timeout}s (infinite loop detected): {e}")


def emit_c_velo_source(source_code: str) -> str:
    """Emits C source code using bin/velo.exe emit-c."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_path = Path(tmp_dir) / "test.vl"
        c_path = Path(tmp_dir) / "test.c"
        src_path.write_text(source_code, encoding="utf-8")

        res = subprocess.run(
            ["bin/velo.exe", "emit-c", str(src_path), "-o", str(c_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=Path.cwd()
        )
        assert res.returncode == 0, f"emit-c failed:\nstdout: {res.stdout}\nstderr: {res.stderr}"
        return c_path.read_text(encoding="utf-8")


# ==============================================================================
# 1. Ranges around INT32_MAX (2147483647)
# ==============================================================================

def check_velo_source(source_code: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_path = Path(tmp_dir) / "test.vl"
        src_path.write_text(source_code, encoding="utf-8")
        return subprocess.run(
            ["bin/velo.exe", "check", str(src_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=Path.cwd()
        )


def test_range_ascending_3000000000():
    """Verifies ascending range 0..3000000000 iterates in ascending order."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 0..3000000000 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_descending_3000000000():
    """Verifies descending range 3000000000..0 iterates in descending order."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 3000000000..0 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_inclusive_ascending_3000000000():
    """Verifies inclusive ascending range 0..=3000000000 iterates in ascending order."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 0..=3000000000 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_inclusive_descending_3000000000():
    """Verifies inclusive descending range 3000000000..=0 iterates in descending order."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 3000000000..=0 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_descending_int32_max_to_zero():
    """Verifies descending range 2147483647..0 (INT32_MAX to 0) executes descending."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 2147483647..0 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_ascending_zero_to_int32_max_plus_1():
    """Verifies ascending range 0..2147483648 (0 to INT32_MAX + 1) executes ascending."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 0..2147483648 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


# ==============================================================================
# 2. Ranges around UINT32_MAX (4294967295)
# ==============================================================================

def test_range_ascending_uint32_max():
    """Verifies ascending range 0..4294967295u64 executes ascending."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 0..4294967295u64 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_descending_uint32_max():
    """Verifies descending range 4294967295u64..0 executes descending."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 4294967295u64..0 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_ascending_uint32_max_plus_1():
    """Verifies ascending range 0..4294967296u64 executes ascending."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 0..4294967296u64 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_descending_uint32_max_plus_1():
    """Verifies descending range 4294967296u64..0 executes descending."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 4294967296u64..0 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


# ==============================================================================
# 3. Ranges around INT64_MAX (9223372036854775807) and UINT64_MAX (18446744073709551615)
# ==============================================================================

def test_range_ascending_int64_max():
    """Verifies ascending range 0..9223372036854775807i64 executes ascending."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 0..9223372036854775807i64 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_descending_int64_max():
    """Verifies descending range 9223372036854775807i64..0 executes descending."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 9223372036854775807i64..0 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_ascending_int64_max_plus_1():
    """Baseline defect: 1..9223372036854775808u64 derives direction from truncated field and reverses."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 1..9223372036854775808u64 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_descending_int64_max_plus_1():
    """Baseline defect: 9223372036854775808u64..0 derives direction from truncated field and reverses."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 9223372036854775808u64..0 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_inclusive_ascending_int64_max_plus_1():
    """Baseline defect: 1..=9223372036854775808u64 reverses direction on baseline."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 1..=9223372036854775808u64 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_inclusive_descending_int64_max_plus_1():
    """Baseline defect: 9223372036854775808u64..=0 reverses direction on baseline."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 9223372036854775808u64..=0 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_ascending_uint64_max():
    """Baseline defect: 1..18446744073709551615u64 reverses direction on baseline."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 1..18446744073709551615u64 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_descending_uint64_max():
    """Baseline defect: 18446744073709551615u64..0 reverses direction on baseline."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 18446744073709551615u64..0 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_inclusive_ascending_uint64_max():
    """Baseline defect: 1..=18446744073709551615u64 reverses direction on baseline."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 1..=18446744073709551615u64 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_inclusive_descending_uint64_max():
    """Baseline defect: 18446744073709551615u64..=0 reverses direction on baseline."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 18446744073709551615u64..=0 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_ascending_large_10_to_10e18():
    """Baseline defect: 10..10000000000000000000u64 reverses direction on baseline."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 10..10000000000000000000u64 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_descending_large_10e18_to_0():
    """Baseline defect: 10000000000000000000u64..0 reverses direction on baseline."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 10000000000000000000u64..0 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_hex_ascending_uint64_max():
    """Baseline defect: 1..0xFFFFFFFFFFFFFFFFu64 reverses direction on baseline."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 1..0xFFFFFFFFFFFFFFFFu64 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_range_hex_descending_uint64_max():
    """Baseline defect: 0xFFFFFFFFFFFFFFFFu64..0 reverses direction on baseline."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    loop i in 0xFFFFFFFFFFFFFFFFu64..0 {
        iters += 1
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


# ==============================================================================
# 4. Emitted C Loop Direction Operator Matrix
# ==============================================================================

@pytest.mark.parametrize("name,code,expected_op", [
    ("asc_3000000000", "act main() { loop i in 0..3000000000 { } }", "<"),
    ("desc_3000000000", "act main() { loop i in 3000000000..0 { } }", ">"),
    # Phase 68 / W2: inclusive ranges no longer carry a `<=` / `>=` condition,
    # because that test overflows at the type maximum. They emit an empty
    # condition plus a step-aware distance terminator after the body.
    ("inc_asc_3000000000", "act main() { loop i in 0..=3000000000 { } }", "inclusive"),
    ("inc_desc_3000000000", "act main() { loop i in 3000000000..=0 { } }", "inclusive"),
    ("desc_int32_max", "act main() { loop i in 2147483647..0 { } }", ">"),
    ("asc_int32_max_plus_1", "act main() { loop i in 0..2147483648 { } }", "<"),
    ("asc_uint32_max", "act main() { loop i in 0..4294967295u64 { } }", "<"),
    ("desc_uint32_max", "act main() { loop i in 4294967295u64..0 { } }", ">"),
    ("asc_int64_max_plus_1", "act main() { loop i in 1..9223372036854775808u64 { } }", "<"),
    ("desc_int64_max_plus_1", "act main() { loop i in 9223372036854775808u64..0 { } }", ">"),
    ("asc_uint64_max", "act main() { loop i in 1..18446744073709551615u64 { } }", "<"),
    ("desc_uint64_max", "act main() { loop i in 18446744073709551615u64..0 { } }", ">"),
    ("inc_asc_uint64_max", "act main() { loop i in 1..=18446744073709551615u64 { } }", "inclusive"),
    ("inc_desc_uint64_max", "act main() { loop i in 18446744073709551615u64..=0 { } }", "inclusive"),
])
def test_emitted_c_range_loop_direction_operator(name, code, expected_op):
    """Verifies that emitted C generates the correct comparison operator for range direction."""
    c_out = emit_c_velo_source(code)
    for_lines = [l.strip() for l in c_out.splitlines() if "for (" in l]
    assert len(for_lines) >= 1, f"No for loop generated:\n{c_out}"
    header = for_lines[0]
    # Check operator between the two semicolons in for (init; cond; step)
    parts = header.split(";")
    assert len(parts) >= 3, f"Unexpected for loop header format: {header}"
    cond_part = parts[1]

    if expected_op == "inclusive":
        # W2: the condition is empty and the exit test is a distance comparison
        # emitted after the loop body, so no `<=` / `>=` can overflow at MAX.
        assert cond_part.strip() == "", (
            f"inclusive range still carries a possibly-overflowing condition: {header}"
        )
        assert "<=" not in header and ">=" not in header, (
            f"inclusive range still uses a non-strict bound test: {header}"
        )
        assert " < " in c_out, f"no distance terminator emitted:\n{c_out}"
        return

    # Check if expected operator is present in the condition
    if expected_op == "<":
        assert "<" in cond_part and "<=" not in cond_part, f"Expected '<' in condition, got: {header}"
    elif expected_op == ">":
        assert ">" in cond_part and ">=" not in cond_part, f"Expected '>' in condition, got: {header}"


# ==============================================================================
# 5. Task 55.2 Diagnostic Probe: Pinned Truncated Field Root Cause
# ==============================================================================

def test_probe_prove_wrapped_value_root_cause():
    """Task 55.2: Diagnostic probe asserting that endpoint direction matches the mathematical value."""
    code = "act main() { loop i in 1..18446744073709551615u64 { } }"
    c_out = emit_c_velo_source(code)
    for_lines = [l.strip() for l in c_out.splitlines() if "for (" in l]
    assert len(for_lines) >= 1, "No for loop generated"
    header = for_lines[0]
    
    # Mathematical relation: 1 < 18446744073709551615 (ascending)
    # Baseline defect: is_reverse_loop_range derives direction from truncated int_val (0),
    # leading to s_val (1) > e_val (0) being TRUE, incorrectly emitting '>' instead of '<'.
    assert "<" in header and "<=" not in header, (
        f"Task 55.2 Root Cause Proved: Direction derived from truncated field (int_val = 0). "
        f"Expected '<' for ascending range 1..18446744073709551615u64, got header:\n  {header}"
    )


# ==============================================================================
# 6. Emitted C Condition and Literal Verification (Task 55.4)
# ==============================================================================

def test_emitted_c_exact_condition_3000000000():
    """Security Invariant: Emitted C for 0..3000000000 must contain '< 3000000000LL' and never '> 3000000000'."""
    asc_code = "act main() { loop i in 0..3000000000 { } }"
    asc_c = emit_c_velo_source(asc_code)
    assert "i < 3000000000LL" in asc_c
    assert "i > 3000000000" not in asc_c

    desc_code = "act main() { loop i in 3000000000..0 { } }"
    desc_c = emit_c_velo_source(desc_code)
    assert "i = 3000000000LL" in desc_c
    assert "i > 0" in desc_c
    assert "i < 0" not in desc_c


def test_emitted_c_no_negative_wrapped_constants():
    """Security Invariant: Emitted C must never contain negative wrapped integer constants."""
    for code in [
        "act main() { loop i in 0..3000000000 { } }",
        "act main() { loop i in 1..9223372036854775808u64 { } }",
        "act main() { loop i in 1..18446744073709551615u64 { } }",
        "act main() { loop i in 10..10000000000000000000u64 { } }",
    ]:
        c_out = emit_c_velo_source(code)
        for line in c_out.splitlines():
            if "for (" in line:
                assert "-1294967296" not in line
                assert "-9223372036854775808" not in line
                assert "i = -1" not in line
                assert "i < -1" not in line


def test_emitted_c_anonymous_large_ranges():
    """Verifies emitted C for anonymous large ranges loop <start>..<end>."""
    asc_code = "act main() { loop 0..3000000000 { } }"
    asc_c = emit_c_velo_source(asc_code)
    assert "for (int64_t it = 0; it < 3000000000LL; it++)" in asc_c

    desc_code = "act main() { loop 3000000000..0 { } }"
    desc_c = emit_c_velo_source(desc_code)
    assert "for (int64_t it = 3000000000LL; it > 0; it--)" in desc_c


def test_emitted_c_stepped_large_ranges():
    """Verifies emitted C for stepped large ranges loop i in <start>..<end>:<step>."""
    asc_code = "act main() { loop i in 0..3000000000:2 { } }"
    asc_c = emit_c_velo_source(asc_code)
    assert "for (int64_t i = 0; i < 3000000000LL; i += 2)" in asc_c

    desc_code = "act main() { loop i in 3000000000..0:2 { } }"
    desc_c = emit_c_velo_source(desc_code)
    assert "for (int64_t i = 3000000000LL; i > 0; i -= 2)" in desc_c


@pytest.mark.parametrize("name,code,expected_header", [
    ("asc_3000000000", "act main() { loop i in 0..3000000000 { } }", "for (int64_t i = 0; i < 3000000000LL; i++)"),
    ("desc_3000000000", "act main() { loop i in 3000000000..0 { } }", "for (int64_t i = 3000000000LL; i > 0; i--)"),
    # Phase 68 / W2: inclusive ranges emit an empty condition and terminate on
    # a distance comparison after the body, so the header carries no bound.
    ("inc_asc_3000000000", "act main() { loop i in 0..=3000000000 { } }", "for (int64_t i = 0;;)"),
    ("inc_desc_3000000000", "act main() { loop i in 3000000000..=0 { } }", "for (int64_t i = 3000000000LL;;)"),
    ("asc_u64_max", "act main() { loop i in 1..18446744073709551615u64 { } }", "for (uint64_t i = 1; i < 18446744073709551615ULL; i++)"),
    ("desc_u64_max", "act main() { loop i in 18446744073709551615u64..0 { } }", "for (uint64_t i = 18446744073709551615ULL; i > 0; i--)"),
    ("hex_asc_u64_max", "act main() { loop i in 1..0xFFFFFFFFFFFFFFFFu64 { } }", "for (uint64_t i = 1; i < 0xFFFFFFFFFFFFFFFFULL; i++)"),
    ("hex_desc_u64_max", "act main() { loop i in 0xFFFFFFFFFFFFFFFFu64..0 { } }", "for (uint64_t i = 0xFFFFFFFFFFFFFFFFULL; i > 0; i--)"),
])
def test_emitted_c_exact_loop_header(name, code, expected_header):
    """Verifies that emitted C generates exact standard C99 loop header with appropriate types and suffixes."""
    c_out = emit_c_velo_source(code)
    for_lines = [l.strip() for l in c_out.splitlines() if "for (" in l]
    assert len(for_lines) >= 1, f"No for loop generated:\n{c_out}"
    header = for_lines[0]
    assert expected_header in header, f"Expected header '{expected_header}', got:\n  {header}"


# ==============================================================================
# 7. Runtime Iteration-Count Verification (Task 55.5)
# ==============================================================================

def test_runtime_iteration_count_slice_around_3b_ascending():
    """Verifies 3000000000..3000000005 runs to completion with exact 5 iterations."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut last_val: i64 = 0
    loop i in 3000000000..3000000005 {
        iters += 1
        last_val = i
    }
    assert(iters == 5)
    assert(last_val == 3000000004)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_runtime_iteration_count_slice_around_3b_descending():
    """Verifies 3000000005..3000000000 runs to completion with exact 5 iterations."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut last_val: i64 = 0
    loop i in 3000000005..3000000000 {
        iters += 1
        last_val = i
    }
    assert(iters == 5)
    assert(last_val == 3000000001)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_runtime_iteration_count_slice_around_3b_inclusive_ascending():
    """Verifies 3000000000..=3000000005 runs to completion with exact 6 iterations."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut last_val: i64 = 0
    loop i in 3000000000..=3000000005 {
        iters += 1
        last_val = i
    }
    assert(iters == 6)
    assert(last_val == 3000000005)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_runtime_iteration_count_slice_around_3b_inclusive_descending():
    """Verifies 3000000005..=3000000000 runs to completion with exact 6 iterations."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut last_val: i64 = 0
    loop i in 3000000005..=3000000000 {
        iters += 1
        last_val = i
    }
    assert(iters == 6)
    assert(last_val == 3000000000)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_runtime_iteration_count_near_uint64_max_ascending():
    """Verifies 18446744073709551610u64..18446744073709551615u64 runs with exact 5 iterations."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut last_val: u64 = 0u64
    loop i in 18446744073709551610u64..18446744073709551615u64 {
        iters += 1
        last_val = i
    }
    assert(iters == 5)
    assert(last_val == 18446744073709551614u64)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_runtime_iteration_count_near_uint64_max_descending():
    """Verifies 18446744073709551615u64..18446744073709551610u64 runs with exact 5 iterations."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut last_val: u64 = 0u64
    loop i in 18446744073709551615u64..18446744073709551610u64 {
        iters += 1
        last_val = i
    }
    assert(iters == 5)
    assert(last_val == 18446744073709551611u64)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_runtime_iteration_count_near_uint64_max_inclusive_descending():
    """Verifies 18446744073709551614u64..=18446744073709551610u64 runs with exact 5 iterations."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut last_val: u64 = 0u64
    loop i in 18446744073709551614u64..=18446744073709551610u64 {
        iters += 1
        last_val = i
    }
    assert(iters == 5)
    assert(last_val == 18446744073709551610u64)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_runtime_iteration_stepped_ascending():
    """Verifies 3000000000..3000000010:2 executes exact 5 iterations."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut last_val: i64 = 0
    loop i in 3000000000..3000000010:2 {
        iters += 1
        last_val = i
    }
    assert(iters == 5)
    assert(last_val == 3000000008)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_runtime_iteration_stepped_descending():
    """Verifies 3000000010..3000000000:2 executes exact 5 iterations."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut last_val: i64 = 0
    loop i in 3000000010..3000000000:2 {
        iters += 1
        last_val = i
    }
    assert(iters == 5)
    assert(last_val == 3000000002)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_runtime_iteration_sentinel_break_ascending():
    """Verifies breaking at sentinel i == 5 from 0..3000000000 terminates with exact 6 iterations."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut last_i: i64 = 0
    loop i in 0..3000000000 {
        iters += 1
        last_i = i
        if i == 5 {
            break
        }
    }
    assert(iters == 6)
    assert(last_i == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_runtime_iteration_sentinel_break_descending():
    """Verifies breaking after 5 iterations descending from 3000000000..0."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut last_i: i64 = 0
    loop i in 3000000000..0 {
        iters += 1
        last_i = i
        if iters == 5 {
            break
        }
    }
    assert(iters == 5)
    assert(last_i == 2999999996)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_runtime_iteration_empty_ranges():
    """Verifies empty ranges execute 0 iterations."""
    code = """
act main() -> i32 {
    mut iters_3b: i32 = 0
    loop i in 3000000000..3000000000 {
        iters_3b += 1
    }
    assert(iters_3b == 0)

    mut iters_u64: i32 = 0
    loop i in 18446744073709551615u64..18446744073709551615u64 {
        iters_u64 += 1
    }
    assert(iters_u64 == 0)

    mut inc_3b: i32 = 0
    mut inc_3b_val: i64 = 0
    loop i in 3000000000..=3000000000 {
        inc_3b += 1
        inc_3b_val = i
    }
    assert(inc_3b == 1)
    assert(inc_3b_val == 3000000000)

    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_runtime_iteration_anonymous_ranges():
    """Verifies anonymous range loop loop <start>..<end> iterates exact count."""
    code = """
act main() -> i32 {
    mut asc_count: i32 = 0
    loop 3000000000..3000000004 {
        asc_count += 1
    }
    assert(asc_count == 4)

    mut desc_count: i32 = 0
    loop 3000000004..3000000000 {
        desc_count += 1
    }
    assert(desc_count == 4)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0





# ==============================================================================
# 8. Boundary and Overflow Tests (Task 55.6)
# ==============================================================================

def test_boundary_crossing_int32_max_ascending():
    """Verifies crossing INT32_MAX ascending seamlessly infers i64 and runs exact 5 iterations."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut last_i: i64 = 0
    loop i in 2147483645..2147483650 {
        iters += 1
        last_i = i
    }
    assert(iters == 5)
    assert(last_i == 2147483649)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_boundary_crossing_int32_max_descending():
    """Verifies crossing INT32_MAX descending seamlessly infers i64 and runs exact 5 iterations."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut last_i: i64 = 0
    loop i in 2147483650..2147483645 {
        iters += 1
        last_i = i
    }
    assert(iters == 5)
    assert(last_i == 2147483646)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_boundary_crossing_int32_max_inclusive():
    """Verifies inclusive boundary crossing INT32_MAX executes exact 6 iterations."""
    code = """
act main() -> i32 {
    mut asc_iters: i32 = 0
    loop i in 2147483645..=2147483650 {
        asc_iters += 1
    }
    assert(asc_iters == 6)

    mut desc_iters: i32 = 0
    loop i in 2147483650..=2147483645 {
        desc_iters += 1
    }
    assert(desc_iters == 6)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_boundary_crossing_uint32_max_ascending():
    """Verifies crossing UINT32_MAX ascending runs exact 5 iterations."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut last_i: u64 = 0u64
    loop i in 4294967293u64..4294967298u64 {
        iters += 1
        last_i = i
    }
    assert(iters == 5)
    assert(last_i == 4294967297u64)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_boundary_crossing_uint32_max_descending():
    """Verifies crossing UINT32_MAX descending runs exact 5 iterations."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut last_i: u64 = 0u64
    loop i in 4294967298u64..4294967293u64 {
        iters += 1
        last_i = i
    }
    assert(iters == 5)
    assert(last_i == 4294967294u64)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_boundary_crossing_int64_max_ascending():
    """Verifies crossing INT64_MAX into u64 range ascending runs exact 5 iterations."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut last_i: u64 = 0u64
    loop i in 9223372036854775805u64..9223372036854775810u64 {
        iters += 1
        last_i = i
    }
    assert(iters == 5)
    assert(last_i == 9223372036854775809u64)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_boundary_crossing_int64_max_descending():
    """Verifies crossing INT64_MAX descending into signed range runs exact 5 iterations."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut last_i: u64 = 0u64
    loop i in 9223372036854775810u64..9223372036854775805u64 {
        iters += 1
        last_i = i
    }
    assert(iters == 5)
    assert(last_i == 9223372036854775806u64)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_boundary_large_step_crossing_int32_max():
    """Verifies large step of 1 billion increments 0, 1000000000, 2000000000 (3 iterations)."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut last_i: i64 = 0
    loop i in 0..3000000000:1000000000 {
        iters += 1
        last_i = i
    }
    assert(iters == 3)
    assert(last_i == 2000000000)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_boundary_large_step_descending_crossing_int32_max():
    """Verifies large descending step of 1 billion decrements 3000000000, 2000000000, 1000000000 (3 iterations)."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut last_i: i64 = 0
    loop i in 3000000000..0:1000000000 {
        iters += 1
        last_i = i
    }
    assert(iters == 3)
    assert(last_i == 1000000000)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_boundary_sign_crossing_ascending():
    """Verifies ascending range crossing negative to positive -5..5 runs 10 iterations."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut sum: i32 = 0
    loop i in -5..5 {
        iters += 1
        sum += i
    }
    assert(iters == 10)
    // sum(-5..5) = -5 + -4 + -3 + -2 + -1 + 0 + 1 + 2 + 3 + 4 = -5
    assert(sum == -5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_boundary_sign_crossing_descending():
    """Verifies descending range crossing positive to negative 5..-5 runs 10 iterations."""
    code = """
act main() -> i32 {
    mut iters: i32 = 0
    mut sum: i32 = 0
    loop i in 5..-5 {
        iters += 1
        sum += i
    }
    assert(iters == 10)
    // sum(5..-5) = 5 + 4 + 3 + 2 + 1 + 0 + -1 + -2 + -3 + -4 = 5
    assert(sum == 5)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_boundary_sign_crossing_inclusive():
    """Verifies inclusive range crossing sign boundaries -3..=3 runs 7 iterations with sum 0."""
    code = """
act main() -> i32 {
    mut asc_sum: i32 = 0
    loop i in -3..=3 {
        asc_sum += i
    }
    assert(asc_sum == 0)

    mut desc_sum: i32 = 0
    loop i in 3..=-3 {
        desc_sum += i
    }
    assert(desc_sum == 0)
    return 0
}
"""
    res = run_velo_source(code, timeout=2.0)
    assert res.returncode == 0


def test_boundary_unrepresentable_decimal_rejected():
    """Security Invariant: Endpoints exceeding 64-bit unsigned maximum must be rejected at velo check."""
    code = "act main() { loop i in 0..18446744073709551616 { } }"
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for endpoint exceeding 64-bit unsigned max"
    assert "exceeds 64-bit" in (res.stdout + res.stderr).lower() or "error" in (res.stdout + res.stderr).lower()


def test_boundary_unrepresentable_hex_rejected():
    """Security Invariant: Hexadecimal endpoint exceeding 64-bit maximum must be rejected at velo check."""
    code = "act main() { loop i in 0..0x10000000000000000 { } }"
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for hex endpoint exceeding 64-bit unsigned max"
    assert "exceeds 64-bit" in (res.stdout + res.stderr).lower() or "error" in (res.stdout + res.stderr).lower()


# ==============================================================================
# 9. Security and Negative Gate (Task 55.7)
# ==============================================================================

def test_negative_string_literal_endpoints_rejected():
    """Security Invariant: String endpoints in range loop must fail closed at velo check."""
    code = 'act main() { loop i in "a".."z" { } }'
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for string range endpoints"
    assert "integer type" in (res.stdout + res.stderr).lower()


def test_negative_string_start_endpoint_rejected():
    """Security Invariant: String start endpoint must fail closed at velo check."""
    code = 'act main() { loop i in "start"..10 { } }'
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for string start endpoint"
    assert "integer type" in (res.stdout + res.stderr).lower()


def test_negative_string_end_endpoint_rejected():
    """Security Invariant: String end endpoint must fail closed at velo check."""
    code = 'act main() { loop i in 0.."end" { } }'
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for string end endpoint"
    assert "integer type" in (res.stdout + res.stderr).lower()


def test_negative_float_literal_endpoints_rejected():
    """Security Invariant: Float endpoints in range loop must fail closed at velo check."""
    code = 'act main() { loop i in 1.0..5.0 { } }'
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for float range endpoints"
    assert "integer type" in (res.stdout + res.stderr).lower()


def test_negative_float_start_endpoint_rejected():
    """Security Invariant: Float start endpoint must fail closed at velo check."""
    code = 'act main() { loop i in 0.5..10 { } }'
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for float start endpoint"
    assert "integer type" in (res.stdout + res.stderr).lower()


def test_negative_float_end_endpoint_rejected():
    """Security Invariant: Float end endpoint must fail closed at velo check."""
    code = 'act main() { loop i in 0..10.5 { } }'
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for float end endpoint"
    assert "integer type" in (res.stdout + res.stderr).lower()


def test_negative_struct_endpoints_rejected():
    """Security Invariant: Struct endpoints in range loop must fail closed at velo check."""
    code = """
data Point { x: i32, y: i32 }
act main() {
    let p1 = Point{ x: 0, y: 0 }
    let p2 = Point{ x: 10, y: 10 }
    loop i in p1..p2 { }
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for struct endpoints"
    assert "integer type" in (res.stdout + res.stderr).lower()


def test_negative_string_step_rejected():
    """Security Invariant: String step in range loop must fail closed at velo check."""
    code = 'act main() { loop i in 0..10:"two" { } }'
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for string step"
    assert "integer type" in (res.stdout + res.stderr).lower()


def test_negative_float_step_rejected():
    """Security Invariant: Float step in range loop must fail closed at velo check."""
    code = 'act main() { loop i in 0..10:2.5 { } }'
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for float step"
    assert "integer type" in (res.stdout + res.stderr).lower()


def test_negative_zero_step_rejected():
    """Security Invariant: Step of 0 cannot advance to end; must fail closed at velo check."""
    code = 'act main() { loop i in 0..10:0 { } }'
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for zero step"
    assert "greater than zero" in (res.stdout + res.stderr).lower()


def test_negative_zero_step_descending_rejected():
    """Security Invariant: Step of 0 in descending loop cannot advance; must fail closed at velo check."""
    code = 'act main() { loop i in 10..0:0 { } }'
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for zero descending step"
    assert "greater than zero" in (res.stdout + res.stderr).lower()


def test_negative_step_rejected():
    """Security Invariant: Negative step cannot reach endpoint; must fail closed at velo check."""
    code = 'act main() { loop i in 0..10:-1 { } }'
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for negative step"
    assert "greater than zero" in (res.stdout + res.stderr).lower()


def test_negative_step_descending_rejected():
    """Security Invariant: Negative descending step moves away from endpoint; must fail closed at velo check."""
    code = 'act main() { loop i in 10..0:-2 { } }'
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for negative descending step"
    assert "greater than zero" in (res.stdout + res.stderr).lower()


def test_negative_endpoint_with_unsigned_range_rejected():
    """Security Invariant: Negative endpoint with unsigned u64 cannot be represented; must fail closed."""
    code = 'act main() { loop i in -5..18446744073709551615u64 { } }'
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for negative endpoint with u64 range"
    assert "cannot be negative for unsigned type" in (res.stdout + res.stderr).lower()


def test_negative_descending_endpoint_with_unsigned_range_rejected():
    """Security Invariant: Negative descending endpoint with unsigned u64 cannot be represented; must fail closed."""
    code = 'act main() { loop i in 18446744073709551615u64..-5 { } }'
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error for negative descending endpoint with u64 range"
    assert "cannot be negative for unsigned type" in (res.stdout + res.stderr).lower()


def test_negative_u64max_assigned_to_i32_rejected():
    """Security Invariant: Wide loop variable (u64) cannot be assigned to i32 variable without cast."""
    code = """
act main() -> i32 {
    mut x: i32 = 0
    loop i in 0..18446744073709551615u64 {
        x = i
    }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error assigning u64 loop var to i32"
    assert "cannot implicitly convert" in (res.stdout + res.stderr).lower() or "narrower type" in (res.stdout + res.stderr).lower()


def test_negative_u64max_passed_to_i32_param_rejected():
    """Security Invariant: Wide loop variable (u64) cannot be passed to i32 function without cast."""
    code = """
act takes_i32(v: i32) { }
act main() -> i32 {
    loop i in 0..18446744073709551615u64 {
        takes_i32(i)
    }
    return 0
}
"""
    res = check_velo_source(code)
    assert res.returncode != 0, "Expected compile error passing u64 loop var to i32 param"
    assert "cannot implicitly convert" in (res.stdout + res.stderr).lower() or "narrower type" in (res.stdout + res.stderr).lower()
