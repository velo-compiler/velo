"""5.5 High-Resolution Clock & Timing (sys.time) — slice 1 battery: scaffold
+ now/delta/sleep_ms + the closed namespace.

Slice 1 ships the module scaffold and the three runtime helpers
(velo_time_now_us / velo_time_delta_us / velo_time_sleep — the platform
#if lives once in velo_runtime.h): now/delta are zero-arg i64 microsecond
monotonic clocks (QPC on Windows, clock_gettime(CLOCK_MONOTONIC) on POSIX),
and sleep_ms takes exactly one INT duration (floats/bool/string reject).
The first delta() call anchors and returns 0 — the one element of this
otherwise nondeterministic surface that pins EXACTLY.

The window problem: elapsed times cannot be pinned across stages (or even
across runs on one stage). Every accept row therefore prints DETERMINISTIC
verdict strings decided by IN-PROGRAM margin checks — the byte-equal
cross-stage comparison holds because the printed strings are the verdicts,
not raw tick prints. Margins (sleep 50 ms ⇒ elapsed in [45_000, 2_000_000]
µs) are asserted by the program itself; a hiccup prints the bad string
identically on both stages and the pin fails loudly.

Every accept row runs on BOTH compiler stages and requires byte-identical
stdout. Every reject row asserts the same wording on both stages (stage 2
prefixes "semantic:line:col - " and appends its error-count summary; the
comparison strips those house wrappers, exactly like the math batteries).
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

from test_allocators import run_stage, ROOT, VELO_PY, VELO_EXE


def _strip_stageWrappers(text: str) -> str:
    """Stage 1 prints bare [Velo Error] lines; stage 2 prefixes each with
    'semantic:line:col - ' and may append its 'Semantic analysis failed'
    summary. Normalize both to the bare words (math-battery precedent)."""
    lines = [
        ln for ln in text.splitlines()
        if ln.strip().startswith("[Velo Error]")  # parse/semantic/runtime errors only
    ]
    cleaned = [
        re.sub(r"^\[Velo Error\] (?:semantic:[0-9]+:[0-9]+ - )?", "", ln.strip())
        for ln in lines
    ]
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
        res = subprocess.run(cmd, capture_output=True, timeout=180, cwd=ROOT)
        err = res.stderr.decode("utf-8", errors="replace") + res.stdout.decode("utf-8", errors="replace")
        outs.append(_strip_stageWrappers(err))
    return outs


def run_program(content: str, name: str):
    """Runs a full program on both stages (run_stage compiles + executes);
    returns the two CompletedResults."""
    s1 = run_stage("stage1", content, name)
    s2 = run_stage("stage2", content, name)
    return s1, s2


def time_header():
    return "use sys.io\nuse sys.time\nact main() -> i32 {\n"


CLOCK_MAIN = """use sys.io
use sys.time

act main() -> i32 {
    let first = time.delta()
    io.println("{first}")
    let t0 = time.now()
    time.sleep_ms(50)
    let t1 = time.now()
    let span = t1 - t0
    if span >= 45000 and span <= 2000000 {
        io.println("clock ok")
    } else {
        io.println("clock bad")
    }
    let second = time.delta()
    if second >= 45000 and second <= 2000000 {
        io.println("delta ok")
    } else {
        io.println("delta bad")
    }
    time.sleep_ms(20)
    let third = time.delta()
    if third >= 15000 and third <= 2000000 {
        io.println("statement ok")
    } else {
        io.println("statement bad")
    }
    io.println("done ok")
    return 0
}
"""

CLOCK_LINES = ["0", "clock ok", "delta ok", "statement ok", "done ok"]

LADDER_MAIN = """use sys.io
use sys.time

act main() -> i32 {
    let a: i8 = 1
    let b: i16 = 1
    let c: i32 = 1
    let d: i64 = 1
    let e: u8 = 1
    let f: u16 = 1
    let g: u32 = 1
    let h: u64 = 1
    let s: usize = 1
    let z: isize = 1
    time.sleep_ms(a)
    time.sleep_ms(b)
    time.sleep_ms(c)
    time.sleep_ms(d)
    time.sleep_ms(e)
    time.sleep_ms(f)
    time.sleep_ms(g)
    time.sleep_ms(h)
    time.sleep_ms(s)
    time.sleep_ms(z)
    mut log: shelf[i64] = shelf[time.now(), time.now()]
    let p: i64 = log[0]
    let q: i64 = log[1]
    if q >= p and q <= p + 10000000 {
        io.println("ladder ok")
    } else {
        io.println("ladder bad")
    }
    return 0
}
"""

LADDER_LINES = ["ladder ok"]


class TestTimeSlice1(unittest.TestCase):
    """gaps.md 5.5 slice 1 — module scaffold, now/delta/sleep_ms, closed
    namespace, i64 microsecond contract."""

    def test_accepts_clock_delta_sleep(self):
        s1, s2 = run_program(CLOCK_MAIN, "time_clock_main")
        self.assertEqual(s1.returncode, 0, s1.stderr[-3000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-3000:])
        out1 = s1.stdout.replace("\r\n", "\n")
        out2 = s2.stdout.replace("\r\n", "\n")
        self.assertEqual(out1, out2, "sys.time outputs diverged between stages")
        self.assertEqual(out1.strip().splitlines(), CLOCK_LINES)

    def test_accepts_int_widen_and_shelf(self):
        s1, s2 = run_program(LADDER_MAIN, "time_ladder_main")
        self.assertEqual(s1.returncode, 0, s1.stderr[-3000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-3000:])
        out1 = s1.stdout.replace("\r\n", "\n")
        out2 = s2.stdout.replace("\r\n", "\n")
        self.assertEqual(out1, out2, "sys.time ladder outputs diverged")
        self.assertEqual(out1.strip().splitlines(), LADDER_LINES)

    def test_rejects_closed_namespace_calls(self):
        rows = [
            ("rej_time_unknown_member.vl",
             "    let n = time.nanos()\n",
             "unknown time member 'nanos' (functions: now, delta, sleep_ms)"),
            ("rej_time_now_one.vl",
             "    let n = time.now(1)\n",
             "time.now expects exactly 0 arguments"),
            ("rej_time_delta_one.vl",
             "    let n = time.delta(1)\n",
             "time.delta expects exactly 0 arguments"),
            ("rej_time_sleep_zero.vl",
             "    time.sleep_ms()\n",
             "time.sleep_ms expects exactly 1 argument: (i64 ms)"),
            ("rej_time_sleep_two.vl",
             "    time.sleep_ms(1, 2)\n",
             "time.sleep_ms expects exactly 1 argument: (i64 ms)"),
            ("rej_time_sleep_float.vl",
             "    time.sleep_ms(1.5)\n",
             "time.sleep_ms expects int arguments (got f32)"),
            ("rej_time_sleep_f64.vl",
             "    let q: f64 = 1.5\n    time.sleep_ms(q)\n",
             "time.sleep_ms expects int arguments (got f64)"),
            ("rej_time_sleep_bool.vl",
             "    time.sleep_ms(true)\n",
             "time.sleep_ms expects int arguments (got bool)"),
            ("rej_time_sleep_string.vl",
             "    time.sleep_ms(\"x\")\n",
             "time.sleep_ms expects int arguments (got string)"),
        ]
        for name, body, wording in rows:
            with self.subTest(row=name):
                src = time_header() + body + "    return 0\n}\n"
                outs = check_program(name, src)
                self.assertEqual(outs[0], wording, f"stage 1 wording for {name}: {outs[0]!r}")
                self.assertEqual(outs[0], outs[1], f"stages disagree for {name}")

    def test_rejects_property_lane(self):
        src_fn = time_header() + "    let x = time.now\n" + "    return 0\n}\n"
        outs = check_program("rej_time_bare_fn.vl", src_fn)
        self.assertEqual(
            outs[0],
            "unknown time constant 'now' (time functions are: now, delta, sleep_ms)"
            " (functions need parens: time.now())")
        self.assertEqual(outs[0], outs[1])
        src_c = time_header() + "    let x = time.PI\n" + "    return 0\n}\n"
        outs = check_program("rej_time_unknown_const.vl", src_c)
        self.assertEqual(
            outs[0],
            "unknown time constant 'PI' (time functions are: now, delta, sleep_ms)")
        self.assertEqual(outs[0], outs[1])


EXAMPLE34 = ROOT / "examples" / "34_time_basics.vl"

EXAMPLE34_LINES = [
    "anchor 0",
    "clock ok",
    "dt ok",
    "arith ok",
    "lane ok",
    "ticks ok",
]


class TestTimeExample34(unittest.TestCase):
    """gaps.md 5.5 → close: the chapter example is the byte-identical
    parity row (example-30 house style: header comment, deterministic
    program, every interpolation binds locals first; margins validated
    IN the program so only fixed verdict strings reach stdout)."""

    def test_example34_parity_and_output(self):
        src = EXAMPLE34.read_text(encoding="utf-8")
        s1 = run_stage("stage1", src, "time_example34")
        s2 = run_stage("stage2", src, "time_example34")
        self.assertEqual(s1.returncode, 0, s1.stderr[-3000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-3000:])
        out1 = s1.stdout.replace("\r\n", "\n")
        out2 = s2.stdout.replace("\r\n", "\n")
        self.assertEqual(out1, out2, "example 34 outputs diverged")
        self.assertEqual(out1.strip().splitlines(), EXAMPLE34_LINES)
