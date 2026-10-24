"""5.3 Math Library (sys.math) — slice 1 battery: constants + sqrt/pow/cbrt.

Slice 1 ships the module scaffold, the four constants (PI / TAU / RAD2DEG /
DEG2RAD as bare member properties, f64, full-precision decimal literals
identical on both compilers), and the first call family sqrt/pow/cbrt with
the widening contract: every int spell and f32/f64 rides an emitted
(double)(...) cast; bool/string/collections reject. The math namespace is
CLOSED for calls — unknown members reject with the shelf-precedent wording.

Every accept row runs on BOTH compiler stages and requires byte-identical
stdout. Every reject row asserts the same wording on both stages (stage 2
prefixes "semantic:line:col - " and appends its error-count summary; the
comparison strips those house wrappers, exactly like the collections
batteries).
"""
import re
import sys
import unittest
from pathlib import Path

from test_allocators import run_stage, ROOT, VELO_PY, VELO_EXE


def _strip_stageWrappers(text: str) -> str:
    """Stage 1 prints bare [Velo Error] lines; stage 2 prefixes each with
    'semantic:line:col - ' and may append its 'Semantic analysis failed'
    summary. Normalize both to the bare words."""
    if "[Velo] Check passed" in text or "[Velo] Check passed" in text:
        return "PASS"
    lines = [
        ln for ln in text.splitlines()
        if ln.strip().startswith("[Velo Error]")  # parse/semantic/runtime errors only
    ]
    cleaned = [
        re.sub(r"^\[Velo Error\] (?:semantic:[0-9]+:[0-9]+ - )?", "", ln.strip())
        for ln in lines
    ]
    # stage 2's end-of-check summary line is house noise (wordings compare
    # without it)
    cleaned = [ln for ln in cleaned if not ln.startswith("Semantic analysis failed")]
    return "\n".join(cleaned)


def check_program(src_name: str, content: str):
    """Runs `check` on both stages for a reject program; returns the
    normalized stderr wording once per stage."""
    tmp = Path(VELO_PY).parent / ".velo_cache"
    tmp.mkdir(exist_ok=True)
    src = tmp / src_name
    src.write_text(content, encoding="utf-8")
    outs = []
    for cmd in ([sys.executable, str(VELO_PY), "check", str(src)],
                [str(VELO_EXE), "check", str(src)]):
        import subprocess
        res = subprocess.run(cmd, capture_output=True, timeout=180, cwd=ROOT)
        err = res.stderr.decode("utf-8", errors="replace") + res.stdout.decode("utf-8", errors="replace")
        outs.append(_strip_stageWrappers(err))
    return outs


class TestMathSlice1(unittest.TestCase):
    """gaps.md 5.3 slice 1 — module scaffold, constants, sqrt/pow/cbrt."""

    def test_accepts_constants_and_first_family(self):
        src = (
            "use sys.io\n"
            "use sys.math\n"
            "\n"
            "act main() -> i32 {\n"
            "    io.println(math.sqrt(2.0))\n"
            "    io.println(math.sqrt(2))\n"
            "    io.println(math.pow(2.0, 10.0))\n"
            "    io.println(math.pow(3, 5))\n"
            "    io.println(math.cbrt(27.0))\n"
            "    io.println(math.cbrt(90))\n"
            "    let pi = math.PI\n"
            "    io.println(\"{pi}\")\n"
            "    let half_of_tau = math.TAU / math.PI\n"
            "    io.println(\"{half_of_tau}\")\n"
            "    let rad = math.RAD2DEG\n"
            "    io.println(\"{rad}\")\n"
            "    let right_angle = math.DEG2RAD * 90\n"
            "    io.println(\"{right_angle}\")\n"
            "    mut mix: shelf[f64] = shelf[math.sqrt(2.0), 1]\n"
            "    let m0: f64 = mix[0]\n"
            "    let m1: f64 = mix[1]\n"
            "    io.println(\"{m0} {m1}\")\n"
            "    let f32arg: f32 = 1.5\n"
            "    io.println(math.sqrt(f32arg))\n"
            "    let wide: i64 = 64\n"
            "    let ok_sqrt: f64 = math.sqrt(wide)\n"
            "    io.println(\"{ok_sqrt}\")\n"
            "    let raw_len: usize = 1024\n"
            "    io.println(math.sqrt(raw_len))\n"
            "    let unum: u64 = 81\n"
            "    io.println(math.sqrt(unum))\n"
            "    return 0\n"
            "}\n"
        )
        s1 = run_stage("stage1", src, "example_math_s1")
        s2 = run_stage("stage2", src, "example_math_s1")
        self.assertEqual(s1.returncode, 0, s1.stderr[-3000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-3000:])
        self.assertEqual(s1.stdout, s2.stdout, "math slice-1 outputs diverged")

    def test_accepts_trig_family(self):
        """5.3 S2: sin/cos/tan/atan2/acos/asin — same widening contract; arc
        legs pin exact IEEE values (acos(1)=0, acos(0)=asin(1)=π/2); atan2 is
        2-ary with C argument order (y, x)."""
        src = (
            "use sys.io\n"
            "use sys.math\n"
            "\n"
            "act main() -> i32 {\n"
            "    io.println(math.sin(0.0))\n"
            "    io.println(math.cos(0.0))\n"
            "    io.println(math.tan(0.0))\n"
            "    let pi4 = math.atan2(1.0, 1.0)\n"
            "    io.println(\"{pi4}\")\n"
            "    io.println(math.atan2(0.0, 1.0))\n"
            "    io.println(math.acos(1.0))\n"
            "    io.println(math.acos(0.0))\n"
            "    io.println(math.asin(0.0))\n"
            "    io.println(math.asin(1.0))\n"
            "    let zero: i32 = 0\n"
            "    io.println(math.sin(zero))\n"
            "    let one: f32 = 1.0\n"
            "    io.println(math.cos(one))\n"
            "    let w: i64 = 1\n"
            "    io.println(math.atan2(w, w))\n"
            "    io.println(math.sin(1.0) + math.sin(0.0))\n"
            "    return 0\n"
            "}\n"
        )
        expected = (
            "0.000000\n1.000000\n0.000000\n0.79\n0.000000\n0.000000\n"
            "1.570796\n0.000000\n1.570796\n0.000000\n0.540302\n0.785398\n0.841471\n"
        )
        s1 = run_stage("stage1", src, "example_math_s2")
        s2 = run_stage("stage2", src, "example_math_s2")
        self.assertEqual(s1.returncode, 0, s1.stderr[-3000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-3000:])
        self.assertEqual(s1.stdout, expected, "trig pins moved (libc event)")
        self.assertEqual(s1.stdout, s2.stdout, "math slice-2 outputs diverged")

    def test_accepts_explog_family(self):
        """5.3 S3: exp/log/log2 — exact IEEE anchors (exp(0)=1, log(1)=0,
        log2(8)=3), the exp/log round-trip at %.2f, int/f32 widening, and a
        math element in the shelf[f64] ladder. log10 stays unshipped (not on
        the gaps list — it rides the closed-set wording)."""
        src = (
            "use sys.io\n"
            "use sys.math\n"
            "\n"
            "act main() -> i32 {\n"
            "    io.println(math.exp(0.0))\n"
            "    io.println(math.exp(1.0))\n"
            "    io.println(math.log(1.0))\n"
            "    io.println(math.log2(8.0))\n"
            "    let back = math.exp(math.log(5.0))\n"
            "    io.println(\"{back}\")\n"
            "    let wide: i64 = 1024\n"
            "    io.println(math.log2(wide))\n"
            "    io.println(math.exp(0))\n"
            "    let f32v: f32 = 1.0\n"
            "    io.println(math.log(f32v))\n"
            "    io.println(math.log2(1024))\n"
            "    let mix: shelf[f64] = shelf[math.log2(8.0), 1]\n"
            "    let m0: f64 = mix[0]\n"
            "    io.println(\"{m0}\")\n"
            "    return 0\n"
            "}\n"
        )
        expected = (
            "1.000000\n2.718282\n0.000000\n3.000000\n5.00\n10.000000\n"
            "1.000000\n0.000000\n10.000000\n3.00\n"
        )
        s1 = run_stage("stage1", src, "example_math_s3")
        s2 = run_stage("stage2", src, "example_math_s3")
        self.assertEqual(s1.returncode, 0, s1.stderr[-3000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-3000:])
        self.assertEqual(s1.stdout, expected, "exp/log pins moved (libc event)")
        self.assertEqual(s1.stdout, s2.stdout, "math slice-3 outputs diverged")

    def test_rejects_bool_and_string_args(self):
        outs = check_program(
            "rej_math_bool.vl",
            "use sys.io\nuse sys.math\nact main() -> i32 {\n"
            "    io.println(math.sqrt(true))\n    return 0\n}\n")
        self.assertEqual(outs[0], "math.sqrt expects f64 (or int) arguments (got bool)")
        self.assertEqual(outs[0], outs[1])

        outs = check_program(
            "rej_math_str.vl",
            "use sys.io\nuse sys.math\nact main() -> i32 {\n"
            "    io.println(math.sqrt(\"x\"))\n    return 0\n}\n")
        self.assertEqual(outs[0], "math.sqrt expects f64 (or int) arguments (got string)")
        self.assertEqual(outs[0], outs[1])

    def test_rejects_arity(self):
        outs = check_program(
            "rej_math_arity1.vl",
            "use sys.io\nuse sys.math\nact main() -> i32 {\n"
            "    io.println(math.pow(1.0))\n    return 0\n}\n")
        self.assertEqual(outs[0], "math.pow expects exactly 2 arguments: (f64 base, f64 exp)")
        self.assertEqual(outs[0], outs[1])

        outs = check_program(
            "rej_math_arity2.vl",
            "use sys.io\nuse sys.math\nact main() -> i32 {\n"
            "    io.println(math.sqrt())\n    return 0\n}\n")
        self.assertEqual(outs[0], "math.sqrt expects exactly 1 argument: (f64 x)")
        self.assertEqual(outs[0], outs[1])

        outs = check_program(
            "rej_math_arity3.vl",
            "use sys.io\nuse sys.math\nact main() -> i32 {\n"
            "    io.println(math.atan2(1.0))\n    return 0\n}\n")
        self.assertEqual(outs[0], "math.atan2 expects exactly 2 arguments: (f64 y, f64 x)")
        self.assertEqual(outs[0], outs[1])

    def test_rejects_unknown_member_and_constant(self):
        # S4 note: the closed-set row uses log10 — deliberately unshipped
        # through 5.3's close (not on the gaps list); the wording grows per
        # slice (S4 adds the utility family to the functions list).
        outs = check_program(
            "rej_math_member.vl",
            "use sys.io\nuse sys.math\nact main() -> i32 {\n"
            "    io.println(math.log10(100.0))\n    return 0\n}\n")
        self.assertEqual(outs[0], "unknown math member 'log10' (functions: sqrt, pow, cbrt, sin, cos, tan, atan2, acos, asin, exp, log, log2, abs, min, max, floor, ceil, round, clamp, lerp; constants: PI, TAU, RAD2DEG, DEG2RAD are available)")
        self.assertEqual(outs[0], outs[1])

        outs = check_program(
            "rej_math_const.vl",
            "use sys.io\nuse sys.math\nact main() -> i32 {\n"
            "    let s = math.sqrt\n    return 0\n}\n")
        self.assertEqual(outs[0], "unknown math constant 'sqrt' (constants: PI, TAU, RAD2DEG, DEG2RAD) (functions need parens: math.sqrt(...))")
        self.assertEqual(outs[0], outs[1])
        # an unknown constant name mirrors the wording without the hint
        outs = check_program(
            "rej_math_const2.vl",
            "use sys.io\nuse sys.math\nact main() -> i32 {\n"
            "    let s = math.PIE\n    return 0\n}\n")
        self.assertEqual(outs[0], "unknown math constant 'PIE' (constants: PI, TAU, RAD2DEG, DEG2RAD)")
        self.assertEqual(outs[0], outs[1])


class TestMathSlice4(unittest.TestCase):
    """gaps.md 5.3 slice 4 — utility family: floor/ceil/round (f64 libm),
    abs (type-dispatched: fabs for floats, identity for unsigned, llabs at
    the arg's spell for signed ints), min/max (fmin/fmax lane for any float
    arg, C ternary for same-spell ints, i64 lifted ternary for mixed int
    widths), clamp (canonical fmin(fmax(v,lo),hi)) and lerp
    ((a + (b - a) * t) all-widened)."""

    def test_accepts_utility_family(self):
        src = (
            "use sys.io\n"
            "use sys.math\n"
            "\n"
            "act main() -> i32 {\n"
            "    io.println(math.floor(2.7))\n"
            "    io.println(math.floor(-2.5))\n"
            "    io.println(math.ceil(2.1))\n"
            "    io.println(math.ceil(-2.5))\n"
            "    io.println(math.round(2.5))\n"
            "    io.println(math.round(2.4))\n"
            "    io.println(math.round(-2.5))\n"
            "    io.println(math.abs(-5.5))\n"
            "    let neg: i32 = -7\n"
            "    let abs32: i32 = math.abs(neg)\n"
            "    io.println(\"{abs32}\")\n"
            "    let neg64: i64 = -9000000000000\n"
            "    let abs64: i64 = math.abs(neg64)\n"
            "    io.println(\"{abs64}\")\n"
            "    let unum: u64 = 81\n"
            "    let abs_unum: u64 = math.abs(unum)\n"
            "    io.println(\"{abs_unum}\")\n"
            "    let usz: usize = 400\n"
            "    let abs_usz: usize = math.abs(usz)\n"
            "    io.println(\"{abs_usz}\")\n"
            "    let small: i32 = math.min(3, 9)\n"
            "    let big: i32 = math.max(3, 9)\n"
            "    io.println(\"{small} {big}\")\n"
            "    let n32: i32 = 5\n"
            "    let n64: i64 = 9\n"
            "    let mix_min: i64 = math.min(n32, n64)\n"
            "    let mix_max: i64 = math.max(n32, n64)\n"
            "    io.println(\"{mix_min} {mix_max}\")\n"
            "    io.println(math.min(2.5, 1.5))\n"
            "    io.println(math.max(2.5, 1.5))\n"
            "    io.println(math.min(2, 1.5))\n"
            "    io.println(math.clamp(5.0, 0.0, 3.0))\n"
            "    io.println(math.clamp(-1.0, 0.0, 3.0))\n"
            "    io.println(math.clamp(1.5, 0.0, 3.0))\n"
            "    let lerped: f64 = math.lerp(0, 10, 0.5)\n"
            "    io.println(\"{lerped}\")\n"
            "    io.println(math.max(math.min(1.0, 2.0), 1.5))\n"
            "    return 0\n"
            "}\n"
        )
        expected = (
            "2.000000\n-3.000000\n3.000000\n-2.000000\n3.000000\n2.000000\n"
            "-3.000000\n5.500000\n7\n9000000000000\n81\n400\n3 9\n5 9\n"
            "1.500000\n2.500000\n1.500000\n3.000000\n0.000000\n1.500000\n"
            "5.00\n1.500000\n"
        )
        s1 = run_stage("stage1", src, "example_math_s4")
        s2 = run_stage("stage2", src, "example_math_s4")
        self.assertEqual(s1.returncode, 0, s1.stderr[-3000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-3000:])
        # round(-2.5) = -3 pins C99 round() half-away-from-zero
        self.assertEqual(s1.stdout, expected, "utility pins moved (libc event)")
        self.assertEqual(s1.stdout, s2.stdout, "math slice-4 outputs diverged")

    def test_rejects_utility_family(self):
        # abs rides the same got-wall wording as the widening family
        outs = check_program(
            "rej_math_abs_bool.vl",
            "use sys.io\nuse sys.math\nact main() -> i32 {\n"
            "    io.println(math.abs(true))\n    return 0\n}\n")
        self.assertEqual(outs[0], "math.abs expects f64 (or int) arguments (got bool)")
        self.assertEqual(outs[0], outs[1])

        # min/max reject non-number args the same way
        outs = check_program(
            "rej_math_min_bool.vl",
            "use sys.io\nuse sys.math\nact main() -> i32 {\n"
            "    io.println(math.min(true, false))\n    return 0\n}\n")
        self.assertEqual(outs[0], "math.min expects f64 (or int) arguments (got bool)")
        self.assertEqual(outs[0], outs[1])

        # arity walls for the 3-ary members (new sig texts)
        outs = check_program(
            "rej_math_clamp_arity.vl",
            "use sys.io\nuse sys.math\nact main() -> i32 {\n"
            "    io.println(math.clamp(1.0, 2.0))\n    return 0\n}\n")
        self.assertEqual(outs[0], "math.clamp expects exactly 3 arguments: (f64 v, f64 lo, f64 hi)")
        self.assertEqual(outs[0], outs[1])

        outs = check_program(
            "rej_math_lerp_arity.vl",
            "use sys.io\nuse sys.math\nact main() -> i32 {\n"
            "    io.println(math.lerp(1.0, 2.0, 3.0, 4.0))\n    return 0\n}\n")
        self.assertEqual(outs[0], "math.lerp expects exactly 3 arguments: (f64 a, f64 b, f64 t)")
        self.assertEqual(outs[0], outs[1])


EXAMPLE33 = ROOT / "examples" / "33_math_library.vl"

EXAMPLE33_LINES = [
    "pi 3.14 tau 6.28",
    "rad2deg 57.30 deg2rad 0.02 semi 3.14",
    "right 1.57",
    "sqrt 1.41 1.73",
    "pow 1024.00 243.00",
    "cbrt 3.00 4.48",
    "trig 0.00 1.00 0.00",
    "arcs 1.57 0.00 0.79",
    "exp 1.00 log 0.00 log2 3.00",
    "exp(log(5.0)) 5.00",
    "round 2.00 3.00 3.00 -3.00",
    "abs 5.50 7 81",
    "minmax 3 9",
    "floats 1.50 2.50",
    "wide 5",
    "clamp 3.00 0.00 1.50",
    "lerp 5.00 3.00 shelf 3.00",
]


class TestMathExample33(unittest.TestCase):
    """gaps.md 5.3 → close: the chapter example is the byte-identical
    parity row (example-30 house style: header comment, deterministic
    program, every interpolation binds locals first)."""

    def test_example33_parity_and_output(self):
        src = EXAMPLE33.read_text(encoding="utf-8")
        s1 = run_stage("stage1", src, "example33")
        s2 = run_stage("stage2", src, "example33")
        self.assertEqual(s1.returncode, 0, s1.stderr[-3000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-3000:])
        self.assertEqual(s1.stdout, s2.stdout, "example 33 outputs diverged")
        self.assertEqual(s1.stdout.strip().splitlines(), EXAMPLE33_LINES)


if __name__ == "__main__":
    unittest.main()
