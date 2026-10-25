"""Task 1.2 — Native String Interpolation Function Calls.

Verifies that function calls, method calls (UFCS), and arbitrary expressions
inside `{...}` string interpolation evaluate correctly and identically across
Stage 1 (velo/codegen_c.py) and Stage 2 (src/backend/codegen_io.vl).
"""
import unittest

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
