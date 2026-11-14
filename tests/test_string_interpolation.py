"""Task 1.2 — Native String Interpolation Function Calls.

Verifies that function calls, method calls (UFCS), and arbitrary expressions
inside `{...}` string interpolation evaluate correctly and identically across
Stage 1 (velo/codegen_c.py) and Stage 2 (src/backend/codegen_io.vl).
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_allocators import run_stage

INTERP_PROGRAM = """use sys.io

act add(a: i32, b: i32) -> i32 {
    return a + b
}

act get_pi() -> f64 {
    return 3.14159
}

act is_even(n: i32) -> bool {
    return (n % 2) == 0
}

act greet() -> string {
    return "hello"
}

data Person {
    name: string,
    age: i32
}

act get_name(p: @Person) -> string {
    return p.name
}

act next_age(p: @Person) -> i32 {
    return p.age + 1
}

act main() -> i32 {
    mut p: Person
    p.name = "Grace"
    p.age = 41

    io.println("Funcs: {add(15, 27)}, Pi: {get_pi()}, Even: {is_even(4)}, Greet: {greet()}")
    io.println("Methods: {p.get_name()}, NextAge: {p.next_age()}")
    io.println("Arith: {10 * 5 + 2}")
    io.println("Compound: {add(p.age, 1)} == {p.next_age()}")
    return 0
}
"""

EXPECTED_LINES = [
    "Funcs: 42, Pi: 3.14, Even: true, Greet: hello",
    "Methods: Grace, NextAge: 42",
    "Arith: 52",
    "Compound: 42 == 42",
]


class TestStringInterpolation(unittest.TestCase):
    """Parity tests for function/method calls inside string interpolation."""

    def test_interp_parity_and_output(self):
        s1 = run_stage("stage1", INTERP_PROGRAM, "interp_s1")
        s2 = run_stage("stage2", INTERP_PROGRAM, "interp_s2")
        for label, res in (("stage1", s1), ("stage2", s2)):
            self.assertEqual(res.returncode, 0, f"{label} run failed: {res.stderr[-2000:]}")
        self.assertEqual(s1.stdout, s2.stdout, "interpolation outputs diverged between stages")
        self.assertEqual(
            s1.stdout.strip().splitlines(),
            EXPECTED_LINES,
            "interpolation outputs do not match expected",
        )

    def test_unsigned_interpolation_stage2(self):
        """Phase 57 / Task 57.1: Verify interpolation of unsigned integers across all widths."""
        prog = """use sys.io
act main() -> i32 {
    let u8_val: u8 = 255u8
    let u16_val: u16 = 65535u16
    let u32_val: u32 = 4294967295u32
    let u64_val: u64 = 18446744073709551615u64
    let usize_val: usize = 18446744073709551615usize
    io.println("u8: {u8_val}, u16: {u16_val}, u32: {u32_val}, u64: {u64_val}, usize: {usize_val}")
    return 0
}
"""
        res = run_stage("stage2", prog, "u_interp")
        self.assertEqual(res.returncode, 0, f"stage2 run failed: {res.stderr[-2000:]}")
        expected = "u8: 255, u16: 65535, u32: 4294967295, u64: 18446744073709551615, usize: 18446744073709551615"
        self.assertIn(expected, res.stdout)
        self.assertNotIn("-1", res.stdout)

    def test_unsigned_interpolation_expression_stage2(self):
        """Phase 57 / Task 57.1: Verify interpolation of unsigned expressions."""
        prog = """use sys.io
act main() -> i32 {
    let u64_val: u64 = 18446744073709551615u64
    io.println("expr: {u64_val - 1u64}")
    return 0
}
"""
        res = run_stage("stage2", prog, "u_interp_expr")
        self.assertEqual(res.returncode, 0, f"stage2 run failed: {res.stderr[-2000:]}")
        self.assertIn("expr: 18446744073709551614", res.stdout)
        self.assertNotIn("-1", res.stdout)

    def test_unsigned_interpolation_struct_and_pointer_members_stage2(self):
        """Phase 57 / Task 57.3: Verify interpolation of struct members and pointer members."""
        prog = """use sys.io

data Stats {
    u8_val: u8,
    u16_val: u16,
    u32_val: u32,
    u64_val: u64,
    usize_val: usize
}

data Container {
    stats: Stats
}

act print_stats_ptr(p: @Stats) {
    io.println("ptr: u64={p.u64_val}, usize={p.usize_val}")
}

act main() -> i32 {
    mut s: Stats
    s.u8_val = 255u8
    s.u16_val = 65535u16
    s.u32_val = 4294967295u32
    s.u64_val = 18446744073709551615u64
    s.usize_val = 18446744073709551615usize

    io.println("members: u8={s.u8_val}, u16={s.u16_val}, u32={s.u32_val}, u64={s.u64_val}, usize={s.usize_val}")
    print_stats_ptr(@s)

    mut c: Container
    c.stats.u64_val = 18446744073709551615u64
    c.stats.u32_val = 4294967295u32
    io.println("nested: u64={c.stats.u64_val}, u32={c.stats.u32_val}")
    return 0
}
"""
        res = run_stage("stage2", prog, "u_interp_struct")
        self.assertEqual(res.returncode, 0, f"stage2 run failed: {res.stderr[-2000:]}")
        self.assertIn("members: u8=255, u16=65535, u32=4294967295, u64=18446744073709551615, usize=18446744073709551615", res.stdout)
        self.assertIn("ptr: u64=18446744073709551615, usize=18446744073709551615", res.stdout)
        self.assertIn("nested: u64=18446744073709551615, u32=4294967295", res.stdout)
        self.assertNotIn("-1", res.stdout)

    def test_unsigned_interpolation_functions_and_ufcs_stage2(self):
        """Phase 57 / Task 57.3: Verify interpolation of function calls and UFCS methods."""
        prog = """use sys.io

data Counter {
    val: u64
}

act get_u64() -> u64 { return 18446744073709551615u64 }
act get_u32() -> u32 { return 4294967295u32 }
act get_usize() -> usize { return 18446744073709551615usize }

act get_count(c: @Counter) -> u64 {
    return c.val
}

act main() -> i32 {
    mut c: Counter
    c.val = 18446744073709551615u64

    io.println("funcs: u64={get_u64()}, u32={get_u32()}, usize={get_usize()}")
    io.println("ufcs: count={c.get_count()}")
    return 0
}
"""
        res = run_stage("stage2", prog, "u_interp_fn")
        self.assertEqual(res.returncode, 0, f"stage2 run failed: {res.stderr[-2000:]}")
        self.assertIn("funcs: u64=18446744073709551615, u32=4294967295, usize=18446744073709551615", res.stdout)
        self.assertIn("ufcs: count=18446744073709551615", res.stdout)
        self.assertNotIn("-1", res.stdout)

    def test_unsigned_interpolation_compound_expressions_stage2(self):
        """Phase 57 / Task 57.3: Verify interpolation of compound expressions, arithmetic, bitwise ops, and casts."""
        prog = """use sys.io

act main() -> i32 {
    let u64_max: u64 = 18446744073709551615u64
    let u32_max: u32 = 4294967295u32
    io.println("sub: {u64_max - 5u64}")
    io.println("div: {u32_max / 2u32}")
    io.println("mod: {u64_max % 1000u64}")
    io.println("xor: {u64_max ^ 1u64}")
    io.println("cast: {42 as u64}")
    return 0
}
"""
        res = run_stage("stage2", prog, "u_interp_compound")
        self.assertEqual(res.returncode, 0, f"stage2 run failed: {res.stderr[-2000:]}")
        self.assertIn("sub: 18446744073709551610", res.stdout)
        self.assertIn("div: 2147483647", res.stdout)
        self.assertIn("mod: 615", res.stdout)
        self.assertIn("xor: 18446744073709551614", res.stdout)
        self.assertIn("cast: 42", res.stdout)
        self.assertNotIn("-1", res.stdout)

    def test_signed_interpolation_regression_stage2(self):
        """Phase 57 / Task 57.3: Signed regression: negative numbers preserved in interpolation."""
        prog = """use sys.io

data SignedBox {
    i64_val: i64,
    i32_val: i32
}

act get_neg_i64() -> i64 { return -9223372036854775807i64 }

act main() -> i32 {
    let i8_neg: i8 = -127i8
    let i16_neg: i16 = -32767i16
    let i32_neg: i32 = -2147483647i32
    let i64_neg: i64 = -9223372036854775807i64
    let isize_neg: isize = -100isize

    io.println("signed: i8={i8_neg}, i16={i16_neg}, i32={i32_neg}, i64={i64_neg}, isize={isize_neg}")
    io.println("signed_fn: {get_neg_i64()}")
    io.println("signed_expr: {i64_neg + 1i64}")

    mut sb: SignedBox
    sb.i64_val = -42i64
    sb.i32_val = -10i32
    io.println("signed_struct: i64={sb.i64_val}, i32={sb.i32_val}")
    return 0
}
"""
        res = run_stage("stage2", prog, "s_interp_regression")
        self.assertEqual(res.returncode, 0, f"stage2 run failed: {res.stderr[-2000:]}")
        self.assertIn("signed: i8=-127, i16=-32767, i32=-2147483647, i64=-9223372036854775807, isize=-100", res.stdout)
        self.assertIn("signed_fn: -9223372036854775807", res.stdout)
        self.assertIn("signed_expr: -9223372036854775806", res.stdout)
        self.assertIn("signed_struct: i64=-42, i32=-10", res.stdout)

    def test_interpolation_in_string_variable_stage2(self):
        """Phase 57 / Task 57.3: Verify interpolation into string variable (velo_str_format)."""
        prog = """use sys.io

act main() -> i32 {
    let u64_val: u64 = 18446744073709551615u64
    let i64_val: i64 = -42i64
    let msg: string = "formatted: u64={u64_val}, i64={i64_val}"
    io.println(msg)
    return 0
}
"""
        res = run_stage("stage2", prog, "u_interp_str_var")
        self.assertEqual(res.returncode, 0, f"stage2 run failed: {res.stderr[-2000:]}")
        self.assertIn("formatted: u64=18446744073709551615, i64=-42", res.stdout)

    def test_interpolation_emitted_c_security_split(self):
        """Phase 57 / Task 57.3: Security gate: format specifiers and argument casts must match 1:1.

        Unsigned expressions must use %llu and (unsigned long long) with NO %lld or (long long).
        Signed expressions must use %lld and (long long) with NO %llu or (unsigned long long).
        Mixed expressions must preserve exact 1:1 alignment.
        """
        def emit_c(code: str) -> str:
            with tempfile.TemporaryDirectory() as tmp_dir:
                src_path = Path(tmp_dir) / "test.vl"
                c_path = Path(tmp_dir) / "test.c"
                src_path.write_text(code, encoding="utf-8")
                res = subprocess.run(
                    ["bin/velo.exe", "emit-c", str(src_path), "-o", str(c_path)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    cwd=Path.cwd()
                )
                self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
                return c_path.read_text(encoding="utf-8")

        # 1. Pure unsigned interpolation
        unsigned_code = """use sys.io
act main() -> i32 {
    let u64_val: u64 = 18446744073709551615u64
    let u32_val: u32 = 4294967295u32
    io.println("u64={u64_val}, u32={u32_val}, expr={u64_val - 1u64}")
    return 0
}
"""
        c_out_u = emit_c(unsigned_code)
        self.assertIn("printf(\"u64=%llu, u32=%llu, expr=%llu\\n\"", c_out_u)
        self.assertIn("(unsigned long long)(u64_val)", c_out_u)
        self.assertIn("(unsigned long long)(u32_val)", c_out_u)
        self.assertIn("(unsigned long long)((u64_val - 1ULL))", c_out_u)
        self.assertNotIn("%lld", c_out_u, "Unsigned interpolation emitted signed %lld")
        self.assertNotIn("(long long)", c_out_u, "Unsigned interpolation emitted signed (long long) cast")

        # 2. Pure signed interpolation
        signed_code = """use sys.io
act main() -> i32 {
    let i64_val: i64 = -42i64
    let i32_val: i32 = -10i32
    io.println("i64={i64_val}, i32={i32_val}")
    return 0
}
"""
        c_out_s = emit_c(signed_code)
        self.assertIn("printf(\"i64=%lld, i32=%lld\\n\"", c_out_s)
        self.assertIn("(long long)(i64_val)", c_out_s)
        self.assertIn("(long long)(i32_val)", c_out_s)
        self.assertNotIn("%llu", c_out_s, "Signed interpolation emitted unsigned %llu")
        self.assertNotIn("(unsigned long long)", c_out_s, "Signed interpolation emitted unsigned (unsigned long long) cast")

        # 3. Mixed interpolation in 1:1 order
        mixed_code = """use sys.io
act main() -> i32 {
    let s: i64 = -42i64
    let u: u64 = 18446744073709551615u64
    io.println("signed={s}, unsigned={u}")
    return 0
}
"""
        c_out_m = emit_c(mixed_code)
        self.assertIn("printf(\"signed=%lld, unsigned=%llu\\n\", (long long)(s), (unsigned long long)(u))", c_out_m)
