"""Tests for `unsafe { ... }` block syntax and `--strict-safety` verification (Task 48.1 / PLR-VELO-004).

Covers:
- `unsafe { ... }` block statement syntax parsing and lowering to C
- Rejection of raw pointer dereference (`ptr.@`, `ptr[i]`, `ptr.field`) outside `unsafe` when `--strict-safety` is passed
- Acceptance of raw pointer dereference inside `unsafe { ... }` blocks with `--strict-safety`
- 100% backward compatibility when `--strict-safety` is omitted
- Rejection of pointer arithmetic (`ptr + n`, `ptr - n`, `n + ptr`, `ptr1 - ptr2`) outside `unsafe` with `--strict-safety`
- Acceptance of pointer arithmetic inside `unsafe { ... }` blocks with `--strict-safety`
- Rejection of foreign `extern act` calls outside `unsafe` with `--strict-safety`
- Acceptance of foreign `extern act` calls inside `unsafe { ... }` blocks with `--strict-safety`
- End-to-end execution of `unsafe { ... }` code compiled with `--strict-safety`
- Formatter handling of `unsafe` keyword and blocks
"""
import os
import tempfile
import subprocess
from pathlib import Path
import pytest
from conftest import velo_exe

ROOT_DIR = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()


def run_velo_check(source_code: str, strict_safety: bool = True) -> subprocess.CompletedProcess:
    """Helper to run `velo check` on a snippet."""
    with tempfile.NamedTemporaryFile("w", suffix=".vl", delete=False) as f:
        f.write(source_code)
        f_name = f.name
    try:
        cmd = [str(VELO_EXE), "check", f_name]
        if strict_safety:
            cmd.append("--strict-safety")
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res
    finally:
        Path(f_name).unlink(missing_ok=True)


def run_velo_program(source_code: str, strict_safety: bool = True) -> subprocess.CompletedProcess:
    """Helper to run `velo run` on a snippet."""
    with tempfile.NamedTemporaryFile("w", suffix=".vl", delete=False) as f:
        f.write(source_code)
        f_name = f.name
    try:
        cmd = [str(VELO_EXE), "run", f_name]
        if strict_safety:
            cmd.append("--strict-safety")
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res
    finally:
        Path(f_name).unlink(missing_ok=True)


class TestStrictSafety:
    @classmethod
    def setup_class(cls):
        if not VELO_EXE.exists():
            pytest.skip("bin/velo.exe not built")

    def test_raw_ptr_deref_rejected_under_strict_safety(self):
        code = """
        act main() -> i32 {
            let p: @i32 = mem.alloc(@i32, 1)
            let v = p.@
            return 0
        }
        """
        res = run_velo_check(code, strict_safety=True)
        assert res.returncode != 0
        out = res.stdout + res.stderr
        assert "Raw pointer dereference requires an 'unsafe { ... }' block when compiling with --strict-safety." in out

    def test_raw_ptr_deref_allowed_inside_unsafe(self):
        code = """
        act main() -> i32 {
            let p: @i32 = mem.alloc(@i32, 1)
            mut v: i32 = 0
            unsafe {
                v = p.@
            }
            return 0
        }
        """
        res = run_velo_check(code, strict_safety=True)
        assert res.returncode == 0

    def test_raw_ptr_deref_allowed_without_strict_safety(self):
        code = """
        act main() -> i32 {
            let p: @i32 = mem.alloc(@i32, 1)
            let v = p.@
            return 0
        }
        """
        res = run_velo_check(code, strict_safety=False)
        assert res.returncode == 0

    def test_raw_ptr_index_rejected_under_strict_safety(self):
        code = """
        act main() -> i32 {
            let p: @i32 = mem.alloc(@i32, 4)
            let v = p[1]
            return 0
        }
        """
        res = run_velo_check(code, strict_safety=True)
        assert res.returncode != 0
        out = res.stdout + res.stderr
        assert "Raw pointer dereference requires an 'unsafe { ... }' block when compiling with --strict-safety." in out

    def test_raw_ptr_index_allowed_inside_unsafe(self):
        code = """
        act main() -> i32 {
            let p: @i32 = mem.alloc(@i32, 4)
            mut v: i32 = 0
            unsafe {
                v = p[1]
            }
            return 0
        }
        """
        res = run_velo_check(code, strict_safety=True)
        assert res.returncode == 0

    def test_raw_ptr_member_rejected_under_strict_safety(self):
        code = """
        data Point {
            x: i32
            y: i32
        }

        act main() -> i32 {
            let pt: @Point = mem.alloc(@Point, 1)
            let x_val = pt.x
            return 0
        }
        """
        res = run_velo_check(code, strict_safety=True)
        assert res.returncode != 0
        out = res.stdout + res.stderr
        assert "Raw pointer dereference requires an 'unsafe { ... }' block when compiling with --strict-safety." in out

    def test_raw_ptr_member_allowed_inside_unsafe(self):
        code = """
        data Point {
            x: i32
            y: i32
        }

        act main() -> i32 {
            let pt: @Point = mem.alloc(@Point, 1)
            mut x_val: i32 = 0
            unsafe {
                x_val = pt.x
            }
            return 0
        }
        """
        res = run_velo_check(code, strict_safety=True)
        assert res.returncode == 0

    def test_pointer_arithmetic_plus_rejected_under_strict_safety(self):
        code = """
        act main() -> i32 {
            let p: @i32 = mem.alloc(@i32, 4)
            let p2 = p + 1
            return 0
        }
        """
        res = run_velo_check(code, strict_safety=True)
        assert res.returncode != 0
        out = res.stdout + res.stderr
        assert "Pointer arithmetic requires an 'unsafe { ... }' block when compiling with --strict-safety." in out

    def test_pointer_arithmetic_minus_rejected_under_strict_safety(self):
        code = """
        act main() -> i32 {
            let p: @i32 = mem.alloc(@i32, 4)
            let p2 = p - 1
            return 0
        }
        """
        res = run_velo_check(code, strict_safety=True)
        assert res.returncode != 0
        out = res.stdout + res.stderr
        assert "Pointer arithmetic requires an 'unsafe { ... }' block when compiling with --strict-safety." in out

    def test_pointer_arithmetic_allowed_inside_unsafe(self):
        code = """
        act main() -> i32 {
            let p: @i32 = mem.alloc(@i32, 4)
            mut p2: @i32 = null
            unsafe {
                p2 = p + 2
                let p3 = p2 - 1
            }
            return 0
        }
        """
        res = run_velo_check(code, strict_safety=True)
        assert res.returncode == 0

    def test_pointer_arithmetic_allowed_without_strict_safety(self):
        code = """
        act main() -> i32 {
            let p: @i32 = mem.alloc(@i32, 4)
            let p2 = p + 2
            return 0
        }
        """
        res = run_velo_check(code, strict_safety=False)
        assert res.returncode == 0

    def test_extern_call_rejected_under_strict_safety(self):
        code = """
        extern act puts(s: string) -> i32

        act main() -> i32 {
            puts("hello from extern")
            return 0
        }
        """
        res = run_velo_check(code, strict_safety=True)
        assert res.returncode != 0
        out = res.stdout + res.stderr
        assert "Call to foreign 'extern act' requires an 'unsafe { ... }' block when compiling with --strict-safety." in out

    def test_extern_call_allowed_inside_unsafe(self):
        code = """
        extern act puts(s: string) -> i32

        act main() -> i32 {
            unsafe {
                puts("hello from extern")
            }
            return 0
        }
        """
        res = run_velo_check(code, strict_safety=True)
        assert res.returncode == 0

    def test_extern_call_allowed_without_strict_safety(self):
        code = """
        extern act puts(s: string) -> i32

        act main() -> i32 {
            puts("hello from extern")
            return 0
        }
        """
        res = run_velo_check(code, strict_safety=False)
        assert res.returncode == 0

    def test_assign_to_ptr_deref_under_strict_safety(self):
        code_err = """
        act main() -> i32 {
            let p: @i32 = mem.alloc(@i32, 1)
            p.@ = 99
            return 0
        }
        """
        res = run_velo_check(code_err, strict_safety=True)
        assert res.returncode != 0
        assert "Raw pointer dereference requires an 'unsafe { ... }' block when compiling with --strict-safety." in res.stdout + res.stderr

        code_ok = """
        act main() -> i32 {
            let p: @i32 = mem.alloc(@i32, 1)
            unsafe {
                p.@ = 99
            }
            return 0
        }
        """
        res_ok = run_velo_check(code_ok, strict_safety=True)
        assert res_ok.returncode == 0

    def test_run_unsafe_program_with_strict_safety(self):
        code = """
        use std.io

        data Counter {
            val: i32
        }

        act main() -> i32 {
            let c: @Counter = mem.alloc(@Counter, 1)
            mut read_val: i32 = 0
            unsafe {
                c.val = 42
                read_val = c.val
            }
            println_str("Counter val: {read_val}")
            return 0
        }
        """
        res = run_velo_program(code, strict_safety=True)
        assert res.returncode == 0
        assert "Counter val: 42" in res.stdout

    def test_code_formatter_unsafe_block(self):
        snippet = "act f(){unsafe{let p:@i32=mem.alloc(@i32,1);let v=p.@;}}\n"
        with tempfile.NamedTemporaryFile("w", suffix=".vl", delete=False) as f:
            f.write(snippet)
            f_name = f.name
        try:
            res = subprocess.run([str(VELO_EXE), "fmt", f_name], capture_output=True, text=True)
            assert res.returncode == 0
            content = Path(f_name).read_text()
            assert "unsafe {" in content
        finally:
            Path(f_name).unlink(missing_ok=True)

