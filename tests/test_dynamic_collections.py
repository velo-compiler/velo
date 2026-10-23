"""5.2 Dynamic Collections — the dynamic shelf end-to-end: typed literals,
`.len`, put/take (the LIFO stack core — take pops FROM THE END), index
reads/writes, `loop v of xs` snapshot iteration, homogeneous elements,
exact element types across call boundaries, annotation pinning of empty
literals, and the mut doctrine. Slice 2 adds the element inference ladder
(int+float → f64 widening, mixed → shelf[dyn] tagged boxes), `as`-cast
unboxing, the raw-dyn gates, and their two-stage parity (gaps.md 5.2).
Every case runs identically on the Stage 1 Python compiler and the
self-hosted Stage 2 native compiler."""
import subprocess
import sys
import unittest
from pathlib import Path

from test_allocators import run_stage, ROOT, VELO_PY, VELO_EXE

EXAMPLE31 = ROOT / "examples" / "31_shelf_basics.vl"
EXAMPLE31_LINES = [
    "len: 4",
    "third: 15",
    "mutated: 99",
    "grown: 4 top: 40",
    "after take: 3",
    "walked: 3 grown-during: 6",
    "sum: 43",
    "names: 3 / grace / eal",
    "g01: 2",
    "g10: 7",
    "q: 6 len: 1",
]


def check_result(stage: str, src: Path) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(VELO_PY), "check", str(src)]
    if stage == "stage2":
        cmd = [str(VELO_EXE), "check", str(src)]
    # explicit UTF-8 decode: both stages emit diagnostics as UTF-8 bytes
    # (velo.py reconfigures its streams; the C compiler writes UTF-8 natively)
    res = subprocess.run(cmd, capture_output=True, cwd=ROOT, timeout=120)
    res.stdout = res.stdout.decode("utf-8", errors="replace")
    res.stderr = res.stderr.decode("utf-8", errors="replace")
    res.returncode = res.returncode
    return res


class TestShelfBasics(unittest.TestCase):
    """gaps.md 5.2 Dynamic Collections — shelf core surface parity."""

    def test_example31_parity_and_output(self):
        src = EXAMPLE31.read_text(encoding="utf-8")
        s1 = run_stage("stage1", src, "example31")
        s2 = run_stage("stage2", src, "example31")
        self.assertEqual(s1.returncode, 0, s1.stderr)
        self.assertEqual(s2.returncode, 0, s2.stderr)
        self.assertEqual(s1.stdout, s2.stdout, "example 31 outputs diverged")
        self.assertEqual(s1.stdout.strip().splitlines(), EXAMPLE31_LINES)

    # ------------------------------------------------------------------
    # 5.2 slice 2 — shelf[dyn] acceptance: the JS-array surface.
    # ------------------------------------------------------------------
    def test_dyn_mixed_bag_basics(self):
        # shelf[15, true, "sx"] lowers to tagged boxes; reads unbox via `as`.
        program = (
            "use sys.io\n"
            "data Pair { a: i32; b: i32 }\n"
            "act main() -> i32 {\n"
            "    let xs = shelf[15, true, \"sx\"]\n"
            "    let n = xs.len\n"
            "    io.println(\"n {n}\")\n"
            "    let a = xs[0] as i32\n"
            "    let b = xs[1] as bool\n"
            "    let c = xs[2] as string\n"
            "    io.println(\"a {a} b {b} c {c}\")\n"
            "    let pr = Pair{ a: 12, b: 56 }\n"
            "    mut grow = xs\n"
            "    grow.put(64)\n"
            "    grow.put(@pr)\n"
            "    let n2 = grow.len\n"
            "    let p = grow[4] as @Pair\n"
            "    let pa = p.a\n"
            "    let pb = p.b\n"
            "    let lastp = grow.take() as @Pair\n"
            "    let lb = lastp.b\n"
            "    io.println(\"n2 {n2} key {pa} val {pb} top {lb}\")\n"
            "    return 0\n"
            "}\n"
        )
        expected = ["n 3", "a 15 b true c sx", "n2 5 key 12 val 56 top 56"]
        s1 = run_stage("stage1", program, "dyn_basics")
        s2 = run_stage("stage2", program, "dyn_basics")
        self.assertEqual(s1.returncode, 0, s1.stderr)
        self.assertEqual(s2.returncode, 0, s2.stderr)
        self.assertEqual(s1.stdout, s2.stdout, "dyn bag outputs diverged")
        self.assertEqual(s1.stdout.strip().splitlines(), expected)

    def test_dyn_widen_ladder_f64(self):
        # int+float mixes widen to f64 (either order), leaving no box.
        program = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    let ws = shelf[1, 2.5]\n"
            "    let t = ws[0] + ws[1]\n"
            "    let ws2 = shelf[2.5, 1]\n"
            "    let u = ws2[0] + ws2[1]\n"
            "    io.println(\"t {t} u {u}\")\n"
            "    return 0\n"
            "}\n"
        )
        expected = ["t 3.50 u 3.50"]
        s1 = run_stage("stage1", program, "dyn_widen")
        s2 = run_stage("stage2", program, "dyn_widen")
        self.assertEqual(s1.returncode, 0, s1.stderr)
        self.assertEqual(s2.returncode, 0, s2.stderr)
        self.assertEqual(s1.stdout, s2.stdout, "f64 widen diverged")
        self.assertEqual(s1.stdout.strip().splitlines(), expected)

    def test_dyn_nested_child_shelf(self):
        # A child shelf inside a mixed literal boxes as tag CHILD and comes
        # back as a value copy via `as shelf[...]`.
        program = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    let ys = shelf[shelf[1, 2], \"c\"]\n"
            "    let row = ys[0] as shelf[i32]\n"
            "    let f0 = row[0]\n"
            "    let w = ys[1] as string\n"
            "    io.println(\"f0 {f0} w {w}\")\n"
            "    return 0\n"
            "}\n"
        )
        expected = ["f0 1 w c"]
        s1 = run_stage("stage1", program, "dyn_child")
        s2 = run_stage("stage2", program, "dyn_child")
        self.assertEqual(s1.returncode, 0, s1.stderr)
        self.assertEqual(s2.returncode, 0, s2.stderr)
        self.assertEqual(s1.stdout, s2.stdout, "dyn child-shelf diverged")
        self.assertEqual(s1.stdout.strip().splitlines(), expected)

    def test_dyn_generic_over_dyn(self):
        # A generic act over `shelf[T]` called with a mixed shelf: the mono
        # ladder must deduce T = dyn (it has to scan ALL literal args).
        program = (
            "use sys.io\n"
            "act len_once[T](xs: shelf[T]) -> i32 {\n"
            "    let n = xs.len\n"
            "    return n as i32\n"
            "}\n"
            "act main() -> i32 {\n"
            "    let bag = shelf[15, true, \"sx\"]\n"
            "    let k = len_once(bag)\n"
            "    io.println(\"k {k}\")\n"
            "    return 0\n"
            "}\n"
        )
        expected = ["k 3"]
        s1 = run_stage("stage1", program, "dyn_generic")
        s2 = run_stage("stage2", program, "dyn_generic")
        self.assertEqual(s1.returncode, 0, s1.stderr)
        self.assertEqual(s2.returncode, 0, s2.stderr)
        self.assertEqual(s1.stdout, s2.stdout, "dyn generic diverged")
        self.assertEqual(s1.stdout.strip().splitlines(), expected)

    def test_dyn_empty_annotation_and_put(self):
        # An empty shelf[dyn] borrows the dyn elem from the annotation; puts
        # box by the source type and a dyn pass-through keeps the tag.
        program = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    mut e: shelf[dyn] = shelf[]\n"
            "    e.put(7)\n"
            "    e.put(\"grade\")\n"
            "    e.put(e[0])\n"
            "    let n = e.len\n"
            "    let one = e[0] as i32\n"
            "    let two = e[1] as string\n"
            "    let three = e[2] as i64\n"
            "    io.println(\"n {n} one {one} two {two} three {three}\")\n"
            "    return 0\n"
            "}\n"
        )
        expected = ["n 3 one 7 two grade three 7"]
        s1 = run_stage("stage1", program, "dyn_empty_put")
        s2 = run_stage("stage2", program, "dyn_empty_put")
        self.assertEqual(s1.returncode, 0, s1.stderr)
        self.assertEqual(s2.returncode, 0, s2.stderr)
        self.assertEqual(s1.stdout, s2.stdout, "dyn empty-put diverged")
        self.assertEqual(s1.stdout.strip().splitlines(), expected)


    def test_put_take_get_set_stack_core(self):
        # put appends at the end; take() pops FROM THE END (LIFO core).
        # Every interpolated value is bound to a plain local first.
        program = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    mut xs = shelf[10, 20, 30]\n"
            "    let n0 = xs.len\n"
            "    io.println(\"len {n0}\")\n"
            "    xs.put(40)\n"
            "    let last = xs[n0]\n"
            "    xs[0] = 11\n"
            "    let a = xs.take()\n"
            "    let b = xs.take()\n"
            "    let mid = xs[0]\n"
            "    let n1 = xs.len\n"
            "    io.println(\"last {last} takes {a} {b} mid {mid} left {n1}\")\n"
            "    return 0\n"
            "}\n"
        )
        expected = ["len 3", "last 40 takes 40 30 mid 11 left 2"]
        s1 = run_stage("stage1", program, "stack_core")
        s2 = run_stage("stage2", program, "stack_core")
        self.assertEqual(s1.returncode, 0, s1.stderr)
        self.assertEqual(s2.returncode, 0, s2.stderr)
        self.assertEqual(s1.stdout, s2.stdout, "stack core diverged")
        self.assertEqual(s1.stdout.strip().splitlines(), expected)

    def test_loop_of_snapshot_semantics(self):
        # take() inside the body pops from the mutation view; the walk keeps
        # the snapshot length and visits the pre-loop elements per index.
        program = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    mut xs: shelf[i32] = shelf[7, 8, 9]\n"
            "    let before: usize = xs.len\n"
            "    loop v of xs {\n"
            "        xs.take()\n"
            "        io.println(\"visit {v}\")\n"
            "    }\n"
            "    let after: usize = xs.len\n"
            "    io.println(\"before {before} after {after}\")\n"
            "    return 0\n"
            "}\n"
        )
        expected = ["visit 7", "visit 8", "visit 9", "before 3 after 0"]
        s1 = run_stage("stage1", program, "of_snapshot")
        s2 = run_stage("stage2", program, "of_snapshot")
        self.assertEqual(s1.returncode, 0, s1.stderr)
        self.assertEqual(s2.returncode, 0, s2.stderr)
        self.assertEqual(s1.stdout, s2.stdout, "snapshot semantics diverged")
        self.assertEqual(s1.stdout.strip().splitlines(), expected)

    def test_empty_literal_annotation_pinning(self):
        # An EMPTY literal borrows the annotation's element type; puts then
        # work with those elements. This also covers the annotation-pin side
        # of the checker on both stages.
        program = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    mut empty: shelf[i32] = shelf[]\n"
            "    empty.put(5)\n"
            "    let top: i32 = empty.take()\n"
            "    io.println(\"pinned top {top}\")\n"
            "    return 0\n"
            "}\n"
        )
        s1 = run_stage("stage1", program, "empty_pin")
        s2 = run_stage("stage2", program, "empty_pin")
        self.assertEqual(s1.returncode, 0, s1.stderr)
        self.assertEqual(s2.returncode, 0, s2.stderr)
        self.assertEqual(s1.stdout, s2.stdout)
        self.assertIn("pinned top 5", s1.stdout)


def find_gcc() -> str:
    import shutil
    found = shutil.which("gcc")
    if found:
        return found
    for candidate in (r"C:\msys64\ucrt64\bin\gcc.exe", r"C:\msys64\mingw64\bin\gcc.exe"):
        if Path(candidate).exists():
            return candidate
    raise RuntimeError("gcc not found \u2014 needed for the runtime fatal harnesses")


# Compile-time rejections — identical wording on both stages (the position
# prefixes differ by the historical per-compiler taxonomy, gaps 6.7).
REJECTIONS = [
    # 5.2 slice 2: the int+float ladder widened ([1, "two"] alone is now a
    # LEGAL dyn mix) — mixed integer WIDTHS stay a strict differ error.
    ("use sys.io\nact main() -> i32 {\n    let wid: i64 = 9\n    let bad = shelf[1, wid]\n    return 0\n}",
     "shelf literal element types differ: i32 vs i64",
     "rej_int_widths"),
    ("use sys.io\ndata Point { a: i32; b: i32 }\nact main() -> i32 {\n    let bad = shelf[Point{ a: 1 }, \"s\"]\n    return 0\n}",
     "shelf[dyn] element type Point cannot be boxed — use a @Point pointer element",
     "rej_dyn_boxed"),
    ("use sys.io\nact main() -> i32 {\n    let bad: shelf[i32] = shelf[15, true]\n    return 0\n}",
     "shelf literal element type shelf[dyn] does not match annotation shelf[i32]",
     "rej_dyn_ann"),
    ("use sys.io\nact main() -> i32 {\n    let bad: shelf[dyn] = shelf[1, 2]\n    return 0\n}",
     "shelf literal element type shelf[i32] does not match annotation shelf[dyn]",
     "rej_dyn_ann_homo"),
    ("use sys.io\nact main() -> i32 {\n    let bad = shelf[5, \"s\"]\n    let n = bad[0] + 1\n    return 0\n}",
     "shelf[dyn] unbox: raw dyn values must be cast (as) to a concrete type first",
     "rej_dyn_gate_add"),
    ("use sys.io\nact main() -> i32 {\n    let bad = shelf[5, \"s\"]\n    let same = bad[0] == bad[1]\n    return 0\n}",
     "shelf[dyn] unbox: raw dyn values must be cast (as) to a concrete type first",
     "rej_dyn_gate_cmp"),
    ("use sys.io\nact main() -> i32 {\n    let bad = shelf[5, \"s\"]\n    io.println(bad[0])\n    return 0\n}",
     "shelf[dyn] unbox: raw dyn values must be cast (as) to a concrete type first",
     "rej_dyn_gate_print"),
    ("use sys.io\nact main() -> i32 {\n    let bad = shelf[5, \"s\"]\n    let v = bad[0]\n    io.println(\"v {v}\")\n    return 0\n}",
     "shelf[dyn] unbox: raw dyn values must be cast (as) to a concrete type first",
     "rej_dyn_gate_interp"),
    ("use sys.io\nact main() -> i32 {\n    let bad = shelf[5, \"s\"]\n    let f = bad[1].b\n    return 0\n}",
     "shelf[dyn] unbox: raw dyn values must be cast (as) to a concrete type first",
     "rej_dyn_member"),
    ("use sys.io\nact main() -> i32 {\n    let bad = shelf[5, \"s\"]\n    let p = bad[0] as Point\n    return 0\n}",
     "cannot unbox a shelf[dyn] value into Point — targets: int family, f32/f64, bool, string, @T, shelf[T]",
     "rej_dyn_unbox_struct"),
    ("use sys.io\nact main() -> i32 {\n    let bad = shelf[5, \"s\"]\n    let r = bad[0] as @shelf[i32]\n    return 0\n}",
     "cannot unbox a shelf[dyn] child as @shelf — the header copy would dangle; use as shelf[...] instead",
     "rej_dyn_unbox_shelfptr"),
    ("use sys.io\nact hit() {\n    return\n}\nact main() -> i32 {\n    let bad = shelf[5, \"s\"]\n    mut m = bad\n    m.put(hit())\n    return 0\n}",
     "shelf[dyn] put: cannot box a void value",
     "rej_dyn_put_void"),
    ("use sys.io\ndata Point { a: i32; b: i32 }\nact main() -> i32 {\n    let bad = shelf[5, \"s\"]\n    mut m = bad\n    m.put(Point{ a: 1, b: 2 })\n    return 0\n}",
     "shelf[dyn] element type Point cannot be boxed — use a @Point pointer element",
     "rej_dyn_put_struct"),
    ("use sys.io\nact main() -> i32 {\n    let xs = shelf[1]\n    xs.put(4)\n    return 0\n}",
     "cannot put into a shelf held by a let (declare with mut)",
     "rej_put_let"),
    ("use sys.io\nact main() -> i32 {\n    let xs = shelf[1]\n    xs.take()\n    return 0\n}",
     "cannot take from a shelf held by a let (declare with mut)",
     "rej_take_let"),
    ("use sys.io\nact main() -> i32 {\n    let xs = shelf[1]\n    xs[0] = 5\n    return 0\n}",
     "cannot write into a shelf held by a let (declare with mut)",
     "rej_write_let"),
    ("use sys.io\nact main() -> i32 {\n    mut xs = shelf[1]\n    let what = xs[\"no\"]\n    return 0\n}",
     "shelf index must be an integer (got string)",
     "rej_str_index"),
    ("use sys.io\nact main() -> i32 {\n    mut grid = shelf[shelf[0, 0]]\n    grid[0][1] = 5\n    return 0\n}",
     "cannot write through a shelf row copy (snapshot rows) \u2014 use @shelf[int] rows for in-place mutation",
     "rej_row_copy"),
    ("use sys.io\nact main() -> i32 {\n    let e = shelf[]\n    return 0\n}",
     "cannot infer element type of empty shelf literal",
     "rej_empty_raw"),
    ("use sys.io\nact main() -> i32 {\n    let bad: shelf[i64] = shelf[1, 2]\n    return 0\n}",
     "shelf literal element type shelf[i32] does not match annotation shelf[i64]",
     "rej_annotation"),
    ("use sys.io\nact main() -> i32 {\n    mut xs = shelf[1]\n    let n = xs.push(3)\n    return 0\n}",
     "unknown shelf member 'push' (put, take, len are available)",
     "rej_push"),
    ("use sys.io\nact main() -> i32 {\n    mut xs = shelf[1]\n    xs.put(1, 2)\n    return 0\n}",
     "shelf.put expects exactly 1 argument: (shelf s, element value)",
     "rej_put_arity"),
    ("use sys.io\nact main() -> i32 {\n    mut xs = shelf[1]\n    let t = xs.take(3)\n    return 0\n}",
     "shelf.take takes no arguments",
     "rej_take_arity"),
    ("use sys.io\nact main() -> i32 {\n    mut xs = shelf[1]\n    xs.put(\"a\")\n    return 0\n}",
     "shelf.put element mismatch: expected i32 (got string)",
     "rej_put_type"),
    ("use sys.io\nact main() -> i32 {\n    let x: shelf = shelf[1]\n    return 0\n}",
     "a bare 'shelf' needs an element type: use shelf[T]",
     "rej_bare_shelf"),
    ("use sys.io\nact main() -> i32 {\n    mut xs = shelf[1]\n    xs[0] += 5\n    return 0\n}",
     "compound assignments on shelves are not supported yet",
     "rej_compound"),
    ("use sys.io\nact hold(s: shelf[i64]) -> i32 {\n    let n = s.len\n    return n as i32\n}\n"
     "act main() -> i32 {\n    let ok = hold(shelf[1])\n    return 0\n}",
     "shelf argument element types must match exactly: got shelf[i32], expected shelf[i64]",
     "rej_cross_call"),
]

RUNTIME_FATALS = [
    ("use sys.io\nact main() -> i32 {\n    mut xs: shelf[i32] = shelf[1, 2]\n"
     "    let boom = xs[5]\n    io.println(\"never\")\n    return 0\n}",
     "Velo Fatal Error: shelf index out of bounds: 5 (len 2)!",
     "oob"),
    ("use sys.io\nact main() -> i32 {\n    mut xs: shelf[i32] = shelf[]\n"
     "    let boom = xs.take()\n    io.println(\"never\")\n    return 0\n}",
     "Velo Fatal Error: shelf take from an empty shelf!",
     "take_empty"),
    # 5.2 slice 2: a wrong-family unbox is a loud fatal (words live in the
    # shared runtime header — both stages cannot diverge).
    ("use sys.io\nact main() -> i32 {\n"
     "    let bad = shelf[15, \"sx\"]\n"
     "    let boom = bad[1] as i64\n"
     "    io.println(\"never\")\n"
     "    return 0\n}",
     "Velo Fatal Error: shelf[dyn] unbox: expected int, found string!",
     "wrong_unbox"),
    ("use sys.io\nact main() -> i32 {\n"
     "    let bad = shelf[15, \"sx\"]\n"
     "    let boom = bad[0] as f64\n"
     "    io.println(\"never\")\n"
     "    return 0\n}",
     "Velo Fatal Error: shelf[dyn] unbox: expected float, found int!",
     "wrong_unbox_float"),
]


class TestShelfRejections(unittest.TestCase):
    """Both stages must reject the same programs with the same words."""

    def test_compile_rejections(self):
        tmp = ROOT / ".velo_cache" / "shelf52_reject"
        tmp.mkdir(parents=True, exist_ok=True)
        for program, want, name in REJECTIONS:
            src = tmp / f"{name}.vl"
            src.write_text(program, encoding="utf-8")
            for stage, res in (("stage1", check_result("stage1", src)),
                               ("stage2", check_result("stage2", src))):
                text = res.stdout + res.stderr
                self.assertNotEqual(res.returncode, 0, f"{stage} accepted {name}:\n{text[-2000:]}")
                self.assertIn(want, text, f"{stage} wording mismatch for {name}:\n{text[-2000:]}")

    def test_runtime_fatals(self):
        for program, want, name in RUNTIME_FATALS:
            for stage in ("stage1", "stage2"):
                res = run_stage(stage, program, f"shelf52_{name}")
                self.assertNotEqual(res.returncode, 0, f"{stage} survived {name}!")
                text = res.stdout + res.stderr
                self.assertIn(want, text, f"{stage} fatal wording mismatch:\n{text[-2000:]}")


if __name__ == "__main__":
    unittest.main()
