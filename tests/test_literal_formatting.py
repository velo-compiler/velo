import os
import sys
import subprocess
import unittest
from pathlib import Path

class TestLiteralFormatting(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.velo_py = self.root_dir / "velo.py"
        self.velo_exe = self.root_dir / "bin" / "velo.exe"
        self.example = self.root_dir / "examples" / "16_literal_formatting.vl"
        self.env = os.environ.copy()
        if r"C:\msys64\ucrt64\bin" not in self.env.get("PATH", ""):
            self.env["PATH"] = r"C:\msys64\ucrt64\bin;" + self.env.get("PATH", "")

    def test_stage1_run_literal_formatting(self):
        cmd = [sys.executable, str(self.velo_py), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, env=self.env)
        self.assertEqual(res.returncode, 0, f"Stage 1 run failed: {res.stderr}")
        self.assertIn("Hex 0xFF: 255", res.stdout)
        self.assertIn("Binary 0b1010: 10", res.stdout)
        self.assertIn("Binary 0b1100_0011: 195", res.stdout)
        self.assertIn("Octal 0o755: 493", res.stdout)
        self.assertIn("One million 1_000_000: 1000000", res.stdout)
        self.assertIn("Scientific 2.5e3: 2500.00", res.stdout)
        self.assertIn("Explicit suffix 255u8: 255", res.stdout)
        self.assertIn("Explicit suffix 500i64: 500", res.stdout)
        self.assertIn("Explicit suffix 1000usize: 1000", res.stdout)
        self.assertIn("Explicit suffix 3.14f32: 3.14", res.stdout)
        self.assertIn("Explicit suffix 10.5f64: 10.50", res.stdout)
        self.assertIn("All literal formatting tests passed successfully!", res.stdout)

    def test_self_hosted_run_literal_formatting(self):
        self.assertTrue(self.velo_exe.exists(), "velo.exe must exist")
        cmd = [str(self.velo_exe), "run", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, env=self.env)
        self.assertEqual(res.returncode, 0, f"Self-hosted run failed: {res.stderr}")
        self.assertIn("Hex 0xFF: 255", res.stdout)
        self.assertIn("Binary 0b1010: 10", res.stdout)
        self.assertIn("Binary 0b1100_0011: 195", res.stdout)
        self.assertIn("Octal 0o755: 493", res.stdout)
        self.assertIn("One million 1_000_000: 1000000", res.stdout)
        self.assertIn("Scientific 2.5e3: 2500.00", res.stdout)
        self.assertIn("Explicit suffix 255u8: 255", res.stdout)
        self.assertIn("Explicit suffix 500i64: 500", res.stdout)
        self.assertIn("Explicit suffix 1000usize: 1000", res.stdout)
        self.assertIn("Explicit suffix 3.14f32: 3.14", res.stdout)
        self.assertIn("Explicit suffix 10.5f64: 10.50", res.stdout)
        self.assertIn("All literal formatting tests passed successfully!", res.stdout)

    def test_emit_c_literal_formatting(self):
        cmd = [str(self.velo_exe), "emit-c", str(self.example)]
        res = subprocess.run(cmd, capture_output=True, text=True, env=self.env)
        self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
        self.assertIn("0xFF", res.stdout)
        self.assertIn("0xAABBCCDD", res.stdout)
        self.assertIn("1000000", res.stdout)
        self.assertIn("1e-4f", res.stdout)
        self.assertIn("2.5e3f", res.stdout)
        self.assertIn("255U", res.stdout)
        self.assertIn("500LL", res.stdout)
        self.assertIn("1000ULL", res.stdout)
        self.assertIn("10.5", res.stdout)

    def test_range_loop_not_broken_by_float_scan(self):
        # Verify 0..5 range loop continues to compile and execute properly
        code = "use sys.io\nact main() {\n    mut sum = 0\n    loop i in 0..5 {\n        sum += i\n    }\n    io.println(\"Sum: {sum}\")\n}\n"
        src_path = self.root_dir / ".velo_cache" / "test_range.vl"
        src_path.write_text(code, encoding="utf-8")
        cmd = [str(self.velo_exe), "run", str(src_path)]
        res = subprocess.run(cmd, capture_output=True, text=True, env=self.env)
        self.assertEqual(res.returncode, 0, f"Range loop execution failed: {res.stderr}")
        self.assertIn("Sum: 10", res.stdout)
        src_path.unlink()

    def test_decimal_leading_zeros_execution(self):
        code = """use sys.io
act main() {
    let a = 099
    let b = 017
    let c = 007
    let d = 00
    let e = 0_0
    let f = 0_17
    let g = 017_u64
    let h = 0x00FF
    let i = 0.5
    io.println("a: {a}")
    io.println("b: {b}")
    io.println("c: {c}")
    io.println("d: {d}")
    io.println("e: {e}")
    io.println("f: {f}")
    io.println("g: {g}")
    io.println("h: {h}")
    io.println("i: {i}")
}
"""
        src_path = self.root_dir / ".velo_cache" / "test_leading_zeros.vl"
        src_path.write_text(code, encoding="utf-8")
        try:
            cmd = [str(self.velo_exe), "run", str(src_path)]
            res = subprocess.run(cmd, capture_output=True, text=True, env=self.env)
            self.assertEqual(res.returncode, 0, f"Run failed: {res.stderr}")
            self.assertIn("a: 99", res.stdout)
            self.assertIn("b: 17", res.stdout)
            self.assertIn("c: 7", res.stdout)
            self.assertIn("d: 0", res.stdout)
            self.assertIn("e: 0", res.stdout)
            self.assertIn("f: 17", res.stdout)
            self.assertIn("g: 17", res.stdout)
            self.assertIn("h: 255", res.stdout)

            # Also verify emit-c output format
            cmd_emit = [str(self.velo_exe), "emit-c", str(src_path)]
            res_emit = subprocess.run(cmd_emit, capture_output=True, text=True, env=self.env)
            self.assertEqual(res_emit.returncode, 0, f"emit-c failed: {res_emit.stderr}")
            # Ensure C source does not have leading zero decimal literals (e.g. 017 or 099)
            self.assertIn("int32_t a = 99;", res_emit.stdout)
            self.assertIn("int32_t b = 17;", res_emit.stdout)
            self.assertIn("int32_t c = 7;", res_emit.stdout)
            self.assertIn("int32_t d = 0;", res_emit.stdout)
            self.assertIn("int32_t e = 0;", res_emit.stdout)
            self.assertIn("int32_t f = 17;", res_emit.stdout)
            self.assertIn("uint64_t g = 17ULL;", res_emit.stdout)
            self.assertIn("0x00FF", res_emit.stdout)
        finally:
            if src_path.exists():
                src_path.unlink()

    def test_boundary_integer_literal_types_in_c(self):
        code = """act main() {
    let a = 2147483648
    let b = 0xFFFFFFFF
    let c = 9223372036854775807
    let d = 18446744073709551615
}
"""
        src_path = self.root_dir / ".velo_cache" / "test_boundary_emit.vl"
        src_path.write_text(code, encoding="utf-8")
        try:
            cmd = [str(self.velo_exe), "emit-c", str(src_path)]
            res = subprocess.run(cmd, capture_output=True, text=True, env=self.env)
            self.assertEqual(res.returncode, 0, f"emit-c failed: {res.stderr}")
            # The type ladder (Task 53.6/53.7) requires wide types in emitted C:
            # a (2147483648) fits i64 -> int64_t, not int32_t
            # b (0xFFFFFFFF) fits i64 -> int64_t, not int32_t
            # c (9223372036854775807) fits i64 -> int64_t, not int32_t
            # d (18446744073709551615) fits u64 -> uint64_t, not int32_t
            self.assertIn("int64_t a", res.stdout)
            self.assertIn("int64_t b", res.stdout)
            self.assertIn("int64_t c", res.stdout)
            self.assertIn("uint64_t d", res.stdout)
        finally:
            if src_path.exists():
                src_path.unlink()

    def test_unsigned_integer_formatting_red_baseline(self):
        """Defect (AUDIT-2026-11-06 / Phase 57): io.println(u64_max) formats as -1 via %lld."""
        code = """use sys.io
act main() {
    let u64_max: u64 = 18446744073709551615u64
    let usize_max: usize = 18446744073709551615usize
    io.println(u64_max)
    io.println(usize_max)
    io.print(u64_max)
    io.println("")
}
"""
        src_path = self.root_dir / ".velo_cache" / "test_unsigned_fmt.vl"
        src_path.write_text(code, encoding="utf-8")
        try:
            # 1. Verify emitted C does not use %lld or (long long) for u64/usize
            cmd_emit = [str(self.velo_exe), "emit-c", str(src_path)]
            res_emit = subprocess.run(cmd_emit, capture_output=True, text=True, env=self.env)
            self.assertEqual(res_emit.returncode, 0, f"emit-c failed: {res_emit.stderr}")
            self.assertNotIn("%lld", res_emit.stdout, "Unsigned values must not be formatted with signed %lld")
            self.assertIn("%llu", res_emit.stdout, "Unsigned u64/usize must be formatted with %llu (or %zu)")

            # 2. Verify runtime output does not wrap to negative -1
            cmd_run = [str(self.velo_exe), "run", str(src_path)]
            res_run = subprocess.run(cmd_run, capture_output=True, text=True, env=self.env)
            self.assertEqual(res_run.returncode, 0, f"run failed: {res_run.stderr}")
            self.assertIn("18446744073709551615", res_run.stdout)
            self.assertNotIn("-1", res_run.stdout)
        finally:
            if src_path.exists():
                src_path.unlink()

    def test_integer_formatting_full_boundary_matrix(self):
        """Task 57.6: Comprehensive boundary matrix for 0, max, max-1, and signed negatives."""
        code = """use sys.io

act main() {
    // Unsigned boundaries: 0, 1, max-1, max
    let u8_0: u8 = 0u8
    let u8_1: u8 = 1u8
    let u8_prev: u8 = 254u8
    let u8_max: u8 = 255u8

    let u16_0: u16 = 0u16
    let u16_1: u16 = 1u16
    let u16_prev: u16 = 65534u16
    let u16_max: u16 = 65535u16

    let u32_0: u32 = 0u32
    let u32_1: u32 = 1u32
    let u32_prev: u32 = 4294967294u32
    let u32_max: u32 = 4294967295u32

    let u64_0: u64 = 0u64
    let u64_1: u64 = 1u64
    let u64_prev: u64 = 18446744073709551614u64
    let u64_max: u64 = 18446744073709551615u64

    let usize_0: usize = 0usize
    let usize_1: usize = 1usize
    let usize_prev: usize = 18446744073709551614usize
    let usize_max: usize = 18446744073709551615usize

    // Signed boundaries
    let i8_min: i8 = -127i8 - 1i8
    let i8_neg1: i8 = -1i8
    let i8_max: i8 = 127i8

    let i16_min: i16 = -32767i16 - 1i16
    let i16_neg1: i16 = -1i16
    let i16_max: i16 = 32767i16

    let i32_min: i32 = -2147483647 - 1
    let i32_neg1: i32 = -1
    let i32_max: i32 = 2147483647

    let i64_min: i64 = -9223372036854775807i64 - 1i64
    let i64_neg1: i64 = -1i64
    let i64_max: i64 = 9223372036854775807i64

    let isize_neg: isize = -42isize
    let isize_pos: isize = 42isize

    // Direct printing
    io.println(u8_0)
    io.println(u8_1)
    io.println(u8_prev)
    io.println(u8_max)

    io.println(u16_0)
    io.println(u16_1)
    io.println(u16_prev)
    io.println(u16_max)

    io.println(u32_0)
    io.println(u32_1)
    io.println(u32_prev)
    io.println(u32_max)

    io.println(u64_0)
    io.println(u64_1)
    io.println(u64_prev)
    io.println(u64_max)

    io.println(usize_0)
    io.println(usize_1)
    io.println(usize_prev)
    io.println(usize_max)

    io.println(i8_min)
    io.println(i8_neg1)
    io.println(i8_max)

    io.println(i16_min)
    io.println(i16_neg1)
    io.println(i16_max)

    io.println(i32_min)
    io.println(i32_neg1)
    io.println(i32_max)

    io.println(i64_min)
    io.println(i64_neg1)
    io.println(i64_max)

    io.println(isize_neg)
    io.println(isize_pos)

    // Interpolation checking
    io.println("interp u64: {u64_max}, i64: {i64_min}, usize: {usize_max}, isize: {isize_neg}")
}
"""
        src_path = self.root_dir / ".velo_cache" / "test_boundary_matrix.vl"
        src_path.write_text(code, encoding="utf-8")
        try:
            # 1. Check emit-c for specifier correctness
            cmd_emit = [str(self.velo_exe), "emit-c", str(src_path)]
            res_emit = subprocess.run(cmd_emit, capture_output=True, text=True, env=self.env)
            self.assertEqual(res_emit.returncode, 0, f"emit-c failed: {res_emit.stderr}")
            # Ensure unsigned types use %llu and (unsigned long long)
            self.assertIn("%llu", res_emit.stdout)
            self.assertIn("(unsigned long long)", res_emit.stdout)
            # Ensure signed types use %lld and (long long)
            self.assertIn("%lld", res_emit.stdout)
            self.assertIn("(long long)", res_emit.stdout)

            # 2. Run and check exact outputs
            cmd_run = [str(self.velo_exe), "run", str(src_path)]
            res_run = subprocess.run(cmd_run, capture_output=True, text=True, env=self.env)
            self.assertEqual(res_run.returncode, 0, f"run failed: {res_run.stderr}")
            lines = [l.strip() for l in res_run.stdout.strip().splitlines() if l.strip()]

            expected = [
                # u8
                "0", "1", "254", "255",
                # u16
                "0", "1", "65534", "65535",
                # u32
                "0", "1", "4294967294", "4294967295",
                # u64
                "0", "1", "18446744073709551614", "18446744073709551615",
                # usize
                "0", "1", "18446744073709551614", "18446744073709551615",
                # i8
                "-128", "-1", "127",
                # i16
                "-32768", "-1", "32767",
                # i32
                "-2147483648", "-1", "2147483647",
                # i64
                "-9223372036854775808", "-1", "9223372036854775807",
                # isize
                "-42", "42",
                # interpolation
                "interp u64: 18446744073709551615, i64: -9223372036854775808, usize: 18446744073709551615, isize: -42",
            ]
            self.assertEqual(lines, expected)
        finally:
            if src_path.exists():
                src_path.unlink()

    def test_format_injection_security_hardening(self):
        """Task 57.6: Format-injection strings (%s, %n, {%n}) must be treated as pure data."""
        code = """use sys.io

act main() {
    // Literal format metacharacters
    io.println("%s%s%s%s%s")
    io.println("%n%n%n%n")
    io.println("%d %i %u %o %x %X %f %e %g %a %c %s %p %n %%")
    io.println("data: %s, count: %n, ptr: %p")

    // In variables
    let attack: string = "%n%n%n%n%s%s%s"
    io.println(attack)

    // Unresolved interpolation tokens
    io.println("{%n}")
    io.println("{%s}")
    io.println("{%p}")

    // Mixed interpolation with variables and format directives
    let u: u64 = 18446744073709551615u64
    let payload: string = "%x_%n_%s"
    io.println("val={u}, payload={payload}, raw=%n%s")
}
"""
        src_path = self.root_dir / ".velo_cache" / "test_format_injection.vl"
        src_path.write_text(code, encoding="utf-8")
        try:
            # 1. emit-c check: user strings must never become the format string itself
            cmd_emit = [str(self.velo_exe), "emit-c", str(src_path)]
            res_emit = subprocess.run(cmd_emit, capture_output=True, text=True, env=self.env)
            self.assertEqual(res_emit.returncode, 0, f"emit-c failed: {res_emit.stderr}")
            # Ensure printf format string argument is always a static literal format
            self.assertNotIn('printf(attack', res_emit.stdout)
            self.assertNotIn('printf(payload', res_emit.stdout)
            self.assertNotIn('printf("%n', res_emit.stdout)

            # 2. Execution check: must run cleanly with code 0 and not crash
            cmd_run = [str(self.velo_exe), "run", str(src_path)]
            res_run = subprocess.run(cmd_run, capture_output=True, text=True, env=self.env)
            self.assertEqual(res_run.returncode, 0, f"run failed: {res_run.stderr}")
            self.assertIn("%s%s%s%s%s", res_run.stdout)
            self.assertIn("%n%n%n%n", res_run.stdout)
            self.assertIn("data: %s, count: %n, ptr: %p", res_run.stdout)
            self.assertIn("%n%n%n%n%s%s%s", res_run.stdout)
            self.assertIn("{%n}", res_run.stdout)
            self.assertIn("{%s}", res_run.stdout)
            self.assertIn("{%p}", res_run.stdout)
            self.assertIn("val=18446744073709551615, payload=%x_%n_%s, raw=%n%s", res_run.stdout)
        finally:
            if src_path.exists():
                src_path.unlink()

    def test_formatting_locale_independence_and_determinism(self):
        """Task 57.6: Integer and float formatting must be deterministic and locale-independent."""
        code = """use sys.io

act main() {
    let big_int: u64 = 18446744073709551615u64
    let one_million: i32 = 1000000
    let neg_val: i32 = -2147483647 - 1
    let flt: f32 = 1234.56f32

    io.println(big_int)
    io.println(one_million)
    io.println(neg_val)
    io.println(flt)
    io.println("formatted: {big_int} / {one_million} / {neg_val} / {flt}")
}
"""
        src_path = self.root_dir / ".velo_cache" / "test_locale_independence.vl"
        src_path.write_text(code, encoding="utf-8")
        try:
            cmd_run = [str(self.velo_exe), "run", str(src_path)]
            res_run = subprocess.run(cmd_run, capture_output=True, text=True, env=self.env)
            self.assertEqual(res_run.returncode, 0, f"run failed: {res_run.stderr}")

            # Verify no locale-dependent thousands separators (comma, apostrophe, space)
            # Output must strictly use ASCII digits
            self.assertIn("18446744073709551615", res_run.stdout)
            self.assertNotIn("18,446,744,073,709,551,615", res_run.stdout)
            self.assertNotIn("18.446.744.073.709.551.615", res_run.stdout)
            self.assertNotIn("18'446'744'073'709'551'615", res_run.stdout)

            self.assertIn("1000000", res_run.stdout)
            self.assertNotIn("1,000,000", res_run.stdout)
            self.assertNotIn("1.000.000", res_run.stdout)

            self.assertIn("-2147483648", res_run.stdout)
            self.assertNotIn("-2,147,483,648", res_run.stdout)

            # Decimal separator must be dot, never comma
            self.assertIn("1234.56", res_run.stdout)
            self.assertNotIn("1234,56", res_run.stdout)

            self.assertIn("formatted: 18446744073709551615 / 1000000 / -2147483648 / 1234.56", res_run.stdout)
        finally:
            if src_path.exists():
                src_path.unlink()

if __name__ == "__main__":
    unittest.main()
