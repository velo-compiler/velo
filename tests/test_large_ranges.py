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
    ("inc_asc_3000000000", "act main() { loop i in 0..=3000000000 { } }", "<="),
    ("inc_desc_3000000000", "act main() { loop i in 3000000000..=0 { } }", ">="),
    ("desc_int32_max", "act main() { loop i in 2147483647..0 { } }", ">"),
    ("asc_int32_max_plus_1", "act main() { loop i in 0..2147483648 { } }", "<"),
    ("asc_uint32_max", "act main() { loop i in 0..4294967295u64 { } }", "<"),
    ("desc_uint32_max", "act main() { loop i in 4294967295u64..0 { } }", ">"),
    ("asc_int64_max_plus_1", "act main() { loop i in 1..9223372036854775808u64 { } }", "<"),
    ("desc_int64_max_plus_1", "act main() { loop i in 9223372036854775808u64..0 { } }", ">"),
    ("asc_uint64_max", "act main() { loop i in 1..18446744073709551615u64 { } }", "<"),
    ("desc_uint64_max", "act main() { loop i in 18446744073709551615u64..0 { } }", ">"),
    ("inc_asc_uint64_max", "act main() { loop i in 1..=18446744073709551615u64 { } }", "<="),
    ("inc_desc_uint64_max", "act main() { loop i in 18446744073709551615u64..=0 { } }", ">="),
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
    
    # Check if expected operator is present in the condition
    if expected_op == "<=":
        assert "<=" in cond_part, f"Expected '<=' in condition, got: {header}"
    elif expected_op == ">=":
        assert ">=" in cond_part, f"Expected '>=' in condition, got: {header}"
    elif expected_op == "<":
        assert "<" in cond_part and "<=" not in cond_part, f"Expected '<' in condition, got: {header}"
    elif expected_op == ">":
        assert ">" in cond_part and ">=" not in cond_part, f"Expected '>' in condition, got: {header}"
