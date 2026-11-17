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

from test_allocators import run_stage, assert_parity, ROOT, VELO_PY, VELO_EXE
from conftest import cc_path

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

    # ------------------------------------------------------------------
    # 5.2 slice 3 — the vector surface: sorted() / insert / remove_at.
    # ------------------------------------------------------------------
    def test_shelf_sorted_families(self):
        # sorted() returns a NEW shelf (receiver untouched — legal on let);
        # per-width numeric compares for ints/floats, strcmp for strings.
        program = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    let xs = shelf[9, 1, 5, 3]\n"
            "    let by = xs.sorted()\n"
            "    let fl = shelf[2.5, 0.5, 1.5]\n"
            "    let fb = fl.sorted()\n"
            "    let words = shelf[\"pear\", \"apple\", \"mango\"]\n"
            "    let wb = words.sorted()\n"
            "    let a = by[0]\n"
            "    let b = by[3]\n"
            "    let c = fb[0]\n"
            "    let d = wb[0]\n"
            "    let keep = xs[0]\n"
            "    io.println(\"a {a} b {b} c {c} d {d} keep {keep}\")\n"
            "    return 0\n"
            "}\n"
        )
        s1 = run_stage("stage1", program, "shelf53_sorted")
        s2 = run_stage("stage2", program, "shelf53_sorted")
        self.assertEqual(s1.returncode, 0, s1.stderr)
        self.assertEqual(s2.returncode, 0, s2.stderr)
        self.assertEqual(s1.stdout, s2.stdout, "sorted outputs diverged")
        self.assertEqual(
            s1.stdout.strip().splitlines(),
            ["a 1 b 9 c 0.50 d apple keep 9"],
        )

    def test_shelf_insert_remove_at(self):
        # insert shifts the tail right (i == len appends); remove_at returns
        # the removed element BY VALUE and collapses the hole.
        program = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    mut ns: shelf[i32] = shelf[1, 2, 3]\n"
            "    ns.insert(1, 99)\n"
            "    let gone = ns.remove_at(2)\n"
            "    ns.insert(3, 7)\n"
            "    let n = ns.len\n"
            "    let last = ns[3]\n"
            "    io.println(\"gone {gone} n {n} last {last}\")\n"
            "    return 0\n"
            "}\n"
        )
        s1 = run_stage("stage1", program, "shelf53_insrem")
        s2 = run_stage("stage2", program, "shelf53_insrem")
        self.assertEqual(s1.returncode, 0, s1.stderr)
        self.assertEqual(s2.returncode, 0, s2.stderr)
        self.assertEqual(s1.stdout, s2.stdout, "insert/remove outputs diverged")
        self.assertEqual(s1.stdout.strip().splitlines(), ["gone 2 n 4 last 7"])

    def test_shelf_dyn_insert_remove(self):
        # The dyn battery: insert boxes (mixed bag passthrough keeps the tag),
        # remove_at yields the raw dyn box for as-casting downstream.
        program = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    mut bag: shelf[dyn] = shelf[]\n"
            "    bag.insert(0, \"sx\")\n"
            "    bag.insert(0, 15)\n"
            "    bag.insert(2, bag[0])\n"
            "    let dn = bag.len\n"
            "    let d2 = bag.remove_at(0)\n"
            "    let d2n = d2 as i32\n"
            "    let w = bag[0] as string\n"
            "    io.println(\"dn {dn} d2 {d2n} w {w}\")\n"
            "    return 0\n"
            "}\n"
        )
        s1 = run_stage("stage1", program, "shelf53_dynbag")
        s2 = run_stage("stage2", program, "shelf53_dynbag")
        self.assertEqual(s1.returncode, 0, s1.stderr)
        self.assertEqual(s2.returncode, 0, s2.stderr)
        self.assertEqual(s1.stdout, s2.stdout, "dyn bag outputs diverged")
        self.assertEqual(s1.stdout.strip().splitlines(), ["dn 3 d2 15 w sx"])

    # ------------------------------------------------------------------
    # 5.2 slice 4 — the loop index binding + the reversed() copy.
    # ------------------------------------------------------------------
    def test_loop_of_index_binding(self):
        # `loop v, i of xs` — first binding is the VALUE, second the step
        # index (usize). Exercised through a GENERIC body so mono has to
        # carry the usize index scope on both stages.
        program = (
            "use sys.io\n"
            "act walk[T](xs: shelf[T]) -> i32 {\n"
            "    loop v, i of xs {\n"
            "        io.println(\"i {i} v {v}\")\n"
            "    }\n"
            "    return 0\n"
            "}\n"
            "act main() -> i32 {\n"
            "    let xs = shelf[9, 1, 5, 3]\n"
            "    walk(xs)\n"
            "    return 0\n"
            "}\n"
        )
        expected = ["i 0 v 9", "i 1 v 1", "i 2 v 5", "i 3 v 3"]
        s1 = run_stage("stage1", program, "shelf54_loopidx")
        s2 = run_stage("stage2", program, "shelf54_loopidx")
        self.assertEqual(s1.returncode, 0, s1.stderr)
        self.assertEqual(s2.returncode, 0, s2.stderr)
        self.assertEqual(s1.stdout, s2.stdout, "loop-index outputs diverged")
        self.assertEqual(s1.stdout.strip().splitlines(), expected)

    def test_shelf_reversed_copy(self):
        # reversed() returns a NEW shelf (receiver untouched — legal on let,
        # no family restriction: dyn boxes keep their tags); empty reverses
        # to empty.
        program = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    let xs = shelf[9, 1, 5, 3]\n"
            "    let rv = xs.reversed()\n"
            "    let r0 = rv[0]\n"
            "    let r1 = rv[1]\n"
            "    let r3 = rv[3]\n"
            "    let keep = xs[0]\n"
            "    let words = shelf[\"pear\", \"apple\"]\n"
            "    let wb = words.reversed()\n"
            "    let w0 = wb[0]\n"
            "    let e: shelf[i32] = shelf[]\n"
            "    let er = e.reversed()\n"
            "    let n = er.len\n"
            "    io.println(\"rev {r0} mid {r1} last {r3} keep {keep}\")\n"
            "    io.println(\"w {w0} en {n}\")\n"
            "    mut bag: shelf[dyn] = shelf[]\n"
            "    bag.insert(0, \"sx\")\n"
            "    bag.insert(0, 15)\n"
            "    let rb = bag.reversed()\n"
            "    let b0 = rb[0] as string\n"
            "    let b1 = rb[1] as i32\n"
            "    io.println(\"b0 {b0} b1 {b1}\")\n"
            "    return 0\n"
            "}\n"
        )
        expected = ["rev 3 mid 5 last 9 keep 9", "w apple en 0", "b0 sx b1 15"]
        s1 = run_stage("stage1", program, "shelf54_rev")
        s2 = run_stage("stage2", program, "shelf54_rev")
        self.assertEqual(s1.returncode, 0, s1.stderr)
        self.assertEqual(s2.returncode, 0, s2.stderr)
        self.assertEqual(s1.stdout, s2.stdout, "reversed outputs diverged")
        self.assertEqual(s1.stdout.strip().splitlines(), expected)

    # ------------------------------------------------------------------
    # 5.2 slice 5 — join(sep) and the shared repr machinery. bool is
    # joinable (it is NOT sorted-joinable) — deliberate closure contrast.
    # ------------------------------------------------------------------
    def test_shelf_join_families(self):
        # Per-family stringify (interpolation ladder): ints %lld, floats
        # %.2f, bools true/false, strings verbatim, any separator (incl.
        # ""), empty shelf -> empty string. join is read-only, legal on
        # let and mut alike.
        program = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    let xs = shelf[9, -1, 5, 3]\n"
            "    let s = xs.join(\", \")\n"
            "    let big = shelf[-61 as i64, 8191 as i64]\n"
            "    let bsj = big.join(\"|\")\n"
            "    let tiny = shelf[7 as u8, 255 as u8]\n"
            "    let tsj = tiny.join(\",\")\n"
            "    let fl = shelf[2.5, 0.5, 1.0]\n"
            "    let fs = fl.join(\"|\")\n"
            "    let words = shelf[\"pear\", \"apple\", \"mango\"]\n"
            "    let ws = words.join(\"\")\n"
            "    let bs = shelf[true, false, true]\n"
            "    let bb = bs.join(\"/\")\n"
            "    let e: shelf[i32] = shelf[]\n"
            "    let es = e.join(\"-\")\n"
            "    let en = e.len\n"
            "    io.println(\"s {s} b {bsj} t {tsj}\")\n"
            "    io.println(\"f {fs} w {ws} b2 {bb}\")\n"
            "    io.println(\"e[{es}] n {en}\")\n"
            "    return 0\n"
            "}\n"
        )
        s1 = run_stage("stage1", program, "shelf55_join")
        s2 = run_stage("stage2", program, "shelf55_join")
        self.assertEqual(s1.returncode, 0, s1.stderr)
        self.assertEqual(s2.returncode, 0, s2.stderr)
        self.assertEqual(s1.stdout, s2.stdout, "join outputs diverged")
        self.assertEqual(
            s1.stdout.strip().splitlines(),
            ["s 9, -1, 5, 3 b -61|8191 t 7,255",
             "f 2.50|0.50|1.00 w pearapplemango b2 true/false/true",
             "e[] n 0"],
        )

    def test_shelf_join_interpolation_parity(self):
        # The pinned contract: join's per-family runtime writers render
        # EXACTLY like io-string interpolation (ints (long long)/%lld,
        # floats (double)/%.2f, bools true/false, strings verbatim).
        # Each pair below prints the JOIN line and the equivalent
        # interpolation line; the harness asserts the payload bytes match.
        program = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    let xs = shelf[9, -1, 5, 3]\n"
            "    let a = xs[0]\n"
            "    let b = xs[1]\n"
            "    let c = xs[2]\n"
            "    let d = xs[3]\n"
            "    let j = xs.join(\", \")\n"
            "    io.println(j)\n"
            "    io.println(\"q {a}, {b}, {c}, {d}\")\n"
            "    let fl = shelf[2.5, 0.5]\n"
            "    let f0 = fl[0]\n"
            "    let f1 = fl[1]\n"
            "    let fj = fl.join(\"|\")\n"
            "    io.println(fj)\n"
            "    io.println(\"q {f0}|{f1}\")\n"
            "    let bs = shelf[true, false]\n"
            "    let y = bs[0]\n"
            "    let n = bs[1]\n"
            "    let bj = bs.join(\":\")\n"
            "    io.println(bj)\n"
            "    io.println(\"q {y}:{n}\")\n"
            "    let words = shelf[\"pear\", \"apple\"]\n"
            "    let w0 = words[0]\n"
            "    let w1 = words[1]\n"
            "    let wj = words.join(\"~\")\n"
            "    io.println(wj)\n"
            "    io.println(\"q {w0}~{w1}\")\n"
            "    return 0\n"
            "}\n"
        )
        s1 = run_stage("stage1", program, "shelf55_joinpar")
        s2 = run_stage("stage2", program, "shelf55_joinpar")
        self.assertEqual(s1.returncode, 0, s1.stderr)
        self.assertEqual(s2.returncode, 0, s2.stderr)
        self.assertEqual(s1.stdout, s2.stdout, "join parity outputs diverged")
        lines = s1.stdout.strip().splitlines()
        self.assertEqual(lines, [
            "9, -1, 5, 3",
            "q 9, -1, 5, 3",
            "2.50|0.50",
            "q 2.50|0.50",
            "true:false",
            "q true:false",
            "pear~apple",
            "q pear~apple",
        ])
        # byte-parity of the two paths: join vs interpolation payload
        self.assertEqual(lines[0], lines[1][2:])
        self.assertEqual(lines[2], lines[3][2:])
        self.assertEqual(lines[4], lines[5][2:])
        self.assertEqual(lines[6], lines[7][2:])


def find_gcc() -> str:
    import shutil
    found = shutil.which("gcc")
    if found:
        return found
    for candidate in (cc_path(), cc_path()):
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
    # 5.2 slice 8 REPLACED the slice-2 blanket gate rows `rej_dyn_gate_add`
    # (`bad[0] + 1`) and `rej_dyn_gate_cmp` (`bad[0] == bad[1]`) — raw-dyn
    # arithmetic and same-family compares now auto-unbox (see
    # TestDynOperators); the gates that REMAIN are pinned below and in the
    # print/interp/member rows above.
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
    # 5.2 slice 10 RETIRED the `as @shelf` dangle reject (the PTR box holds a
    # real pointer the user owns — trust doctrine); the roundtrip is now an
    # ACCEPT in TestSharedRows.
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
     "unknown shelf member 'push' (put, take, len, sorted, insert, remove_at, reversed, join, free, destroy are available)",
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
    # 5.2 slice 3 — sorted / insert / remove_at surface.
    ("use sys.io\nact main() -> i32 {\n    let bad = shelf[5, \"s\"]\n    let s = bad.sorted()\n    return 0\n}",
     "shelf.sorted() supports numeric or string elements (got dyn)",
     "rej_sorted_dyn"),
    ("use sys.io\nact main() -> i32 {\n    let xs = shelf[true, false]\n    let s = xs.sorted()\n    return 0\n}",
     "shelf.sorted() supports numeric or string elements (got bool)",
     "rej_sorted_bool"),
    ("use sys.io\ndata Point { a: i32; b: i32 }\nact main() -> i32 {\n"
     "    let ps = shelf[Point{ a: 1, b: 2 }]\n    let s = ps.sorted()\n    return 0\n}",
     "shelf.sorted() supports numeric or string elements (got Point)",
     "rej_sorted_struct"),
    ("use sys.io\ndata Point { a: i32; b: i32 }\nact main() -> i32 {\n"
     "    let p = Point{ a: 1, b: 2 }\n    let ps = shelf[@p]\n    let s = ps.sorted()\n    return 0\n}",
     "shelf.sorted() supports numeric or string elements (got @Point)",
     "rej_sorted_ptrrow"),
    ("use sys.io\nact main() -> i32 {\n    let xs = shelf[1]\n    xs.insert(0, 5)\n    return 0\n}",
     "cannot insert into a shelf held by a let (declare with mut)",
     "rej_insert_let"),
    ("use sys.io\nact main() -> i32 {\n    let xs = shelf[1]\n    let g = xs.remove_at(0)\n    return 0\n}",
     "cannot remove from a shelf held by a let (declare with mut)",
     "rej_remove_let"),
    ("use sys.io\nact main() -> i32 {\n    mut xs = shelf[1]\n    xs.insert(0, \"s\")\n    return 0\n}",
     "shelf.insert element mismatch: expected i32 (got string)",
     "rej_insert_type"),
    ("use sys.io\nact main() -> i32 {\n    mut xs = shelf[1]\n    xs.insert(0.5, 2)\n    return 0\n}",
     "shelf index must be an integer (got f32)",
     "rej_insert_index"),
    ("use sys.io\nact main() -> i32 {\n    mut xs = shelf[1]\n    let g = xs.remove_at(\"x\")\n    return 0\n}",
     "shelf index must be an integer (got string)",
     "rej_remove_index"),
    ("use sys.io\nact main() -> i32 {\n    mut xs = shelf[1]\n    let s = xs.sorted(1)\n    return 0\n}",
     "shelf.sorted takes no arguments",
     "rej_sorted_args"),
    ("use sys.io\nact main() -> i32 {\n    mut xs = shelf[1]\n    xs.insert(0)\n    return 0\n}",
     "shelf.insert expects exactly 2 arguments: (shelf s, index, element value)",
     "rej_insert_arity"),
    ("use sys.io\nact main() -> i32 {\n    mut xs = shelf[1]\n    xs.remove_at()\n    return 0\n}",
     "shelf.remove_at expects exactly 1 argument: (shelf s, index)",
     "rej_remove_arity"),
    ("use sys.io\nact hit() {\n    return\n}\nact main() -> i32 {\n"
     "    mut m: shelf[dyn] = shelf[]\n    m.insert(0, hit())\n    return 0\n}",
     "shelf[dyn] insert: cannot box a void value",
     "rej_dyn_insert_void"),
    # 5.2 slice 4 — loop-index arity + reversed arity.
    ("use sys.io\nact main() -> i32 {\n    let xs = shelf[1]\n"
     "    loop v, i, w of xs {\n        io.println(\"x\")\n    }\n    return 0\n}",
     "loop of takes at most two bindings (value, then index)",
     "rej_loop_third_binding"),
    ("use sys.io\nact main() -> i32 {\n    let xs = shelf[1]\n    let s = xs.reversed(1)\n    return 0\n}",
     "shelf.reversed takes no arguments",
     "rej_reversed_args"),
    # 5.2 slice 5 — join(sep): arity, separator typing, family closures.
    ("use sys.io\nact main() -> i32 {\n    let xs = shelf[1]\n    let s = xs.join()\n    return 0\n}",
     "shelf.join expects exactly 1 argument: (shelf s, separator)",
     "rej_join_args"),
    ("use sys.io\nact main() -> i32 {\n    let xs = shelf[1]\n    let s = xs.join(3)\n    return 0\n}",
     "shelf.join separator must be a string (got i32)",
     "rej_join_sep"),
    ("use sys.io\nact main() -> i32 {\n    let bad = shelf[5, \"s\"]\n    let s = bad.join(\",\")\n    return 0\n}",
     "shelf[dyn] join is not supported — cast elements first",
     "rej_join_dyn"),
    ("use sys.io\ndata Point { a: i32; b: i32 }\nact main() -> i32 {\n"
     "    let p = Point{ a: 1, b: 2 }\n    let ps = shelf[@p]\n    let s = ps.join(\",\")\n    return 0\n}",
     "shelf.join is not supported on @Point elements",
     "rej_join_ptrrow"),
    ("use sys.io\nact main() -> i32 {\n    let rows = shelf[shelf[1, 2]]\n    let s = rows.join(\",\")\n    return 0\n}",
     "shelf.join is not supported on shelf[i32] elements",
     "rej_join_childrow"),
    # 5.2 slice 8 — raw-dyn operators: the pinned reject walls.
    ("use sys.io\nact main() -> i32 {\n    let bad = shelf[5, \"s\"]\n    let z = bad[0] + \"a\"\n    return 0\n}",
     "shelf[dyn] op: cannot apply '+' between dyn and string — unbox with as first",
     "rej_s8_dyn_plus_str"),
    ("use sys.io\nact main() -> i32 {\n    let bad = shelf[5, true]\n    let z = bad[0] % true\n    return 0\n}",
     "shelf[dyn] op: cannot apply '%' between dyn and bool — unbox with as first",
     "rej_s8_dyn_mod_bool"),
    # String concatenation with '+' is supported. Non-plus string arithmetic ('-', etc.) remains rejected:
    ("use sys.io\nact main() -> i32 {\n    let a = \"x\"\n    let b = a - \"y\"\n    io.println(b)\n    return 0\n}",
     "cannot apply '-' to string operands (concatenation is str.concat)",
     "rej_s8_str_sub"),
    ("use sys.io\nact main() -> i32 {\n    let xs = shelf[1]\n    let b = xs[0] < \"a\"\n    io.println(b)\n    return 0\n}",
     "mismatched compare operand families: i32 and string (no implicit conversion)",
     "rej_s8_mixed_cmp"),
    ("use sys.io\nact main() -> i32 {\n    let b = 1 < \"a\"\n    io.println(b)\n    return 0\n}",
     "mismatched compare operand families: i32 and string (no implicit conversion)",
     "rej_s8_mixed_cmp_lit"),
    ("use sys.io\nact main() -> i32 {\n    let b = true == \"a\"\n    io.println(b)\n    return 0\n}",
     "mismatched compare operand families: bool and string (no implicit conversion)",
     "rej_s8_bool_str_cmp"),
    ("use sys.io\nact main() -> i32 {\n    let bad = shelf[5, \"s\"]\n    let z = bad[0] and true\n    return 0\n}",
     "shelf[dyn] unbox: raw dyn values must be cast (as) to a concrete type first",
     "rej_s8_dyn_and"),
    ("use sys.io\nact main() -> i32 {\n    let bad = shelf[5, \"s\"]\n    let z = -bad[0]\n    return 0\n}",
     "shelf[dyn] unbox: raw dyn values must be cast (as) to a concrete type first",
     "rej_s8_dyn_unary"),
    ("use sys.io\nact main() -> i32 {\n    let bad = shelf[5, \"s\"]\n    if bad[0] == null {\n        io.println(\"n\")\n    }\n    return 0\n}",
     "shelf elements cannot be null (use a @T pointer element)",
     "rej_s8_dyn_null_cmp"),
    ("use sys.io\nact main() -> i32 {\n    let bad: shelf[dyn] = shelf[18446744073709551615]\n    return 0\n}",
     "shelf literal element type shelf[i32] does not match annotation shelf[dyn]",
     "rej_s8_u64_lone"),
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
    # 5.2 slice 3: insert/remove bounds tiering (the shared runtime header
    # words it — both stages cannot diverge).
    ("use sys.io\nact main() -> i32 {\n    mut xs: shelf[i32] = shelf[1, 2]\n"
     "    xs.insert(4, 9)\n    io.println(\"never\")\n    return 0\n}",
     "Velo Fatal Error: shelf insert index out of bounds: 4 (len 2)!",
     "insert_oob"),
    ("use sys.io\nact main() -> i32 {\n    mut xs: shelf[i32] = shelf[1, 2]\n"
     "    let boom = xs.remove_at(4)\n    io.println(\"never\")\n    return 0\n}",
     "Velo Fatal Error: shelf remove index out of bounds: 4 (len 2)!",
     "remove_oob"),
    ("use sys.io\nact main() -> i32 {\n    mut xs: shelf[i32] = shelf[]\n"
     "    let boom = xs.remove_at(0)\n    io.println(\"never\")\n    return 0\n}",
     "Velo Fatal Error: shelf remove index out of bounds: 0 (len 0)!",
     "remove_empty"),
    # 5.2 slice 8 — raw-dyn operator runtime fatals (words live in the
    # shared runtime header — the stages cannot diverge).
    ("use sys.io\nact main() -> i32 {\n"
     "    let bad = shelf[15, \"sx\"]\n"
     "    if bad[0] < \"zz\" {\n        io.println(\"never\")\n    }\n"
     "    return 0\n}",
     "Velo Fatal Error: shelf[dyn] unbox: expected string, found int!",
     "s8_cmp_family"),
    ("use sys.io\nact main() -> i32 {\n"
     "    let bad = shelf[15, \"sx\"]\n"
     "    let boom = bad[0] + bad[1]\n"
     "    io.println(\"never\")\n"
     "    return 0\n}",
     "Velo Fatal Error: shelf[dyn] arith: cannot apply '+' to int and string!",
     "s8_arith_family"),
    ("use sys.io\nact main() -> i32 {\n"
     "    let bad = shelf[18446744073709551615, \"sx\"]\n"
     "    let boom = bad[0] as f64\n"
     "    io.println(\"never\")\n"
     "    return 0\n}",
     "Velo Fatal Error: shelf[dyn] unbox: expected float, found int!",
     "s8_u64_f64"),
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
                if name == "rej_s8_u64_lone" and stage == "stage2":
                    self.assertIn("shelf literal element type shelf[u64] does not match annotation shelf[dyn]", text)
                else:
                    self.assertIn(want, text, f"{stage} wording mismatch for {name}:\n{text[-2000:]}")

    def test_runtime_fatals(self):
        for program, want, name in RUNTIME_FATALS:
            for stage in ("stage1", "stage2"):
                res = run_stage(stage, program, f"shelf52_{name}")
                self.assertNotEqual(res.returncode, 0, f"{stage} survived {name}!")
                text = res.stdout + res.stderr
                self.assertIn(want, text, f"{stage} fatal wording mismatch:\n{text[-2000:]}")


# ======================================================================
# 5.2 slice 6 — Map[K, V] core: parity surface (gaps.md map contract).
# Canonical comma-space spellings; open-addressing engine (VeloMap);
# string keys hash CONTENT (FNV-1a + strcmp); the value ladder rides the
# shelf machinery; fatal-on-miss reads speak the S5 repr writers.
# ======================================================================

# 5.2 slice 7 — key-iteration visit orders replay the engine's own
# placement (FNV-1a-64 over key bytes, |1; ≤6 entries keep cap 8; linear
# probe past collisions) so the battery pins the HASH-ordered rows exactly.
def _fnv1a_64(key: str) -> int:
    h = 14695981039346656037
    for b in key.encode():
        h = ((h ^ b) * 1099511628211) % (1 << 64)
    return h | 1


def _map_key_visit_order(keys, cap: int = 8):
    slots = {}
    for k in keys:
        s = _fnv1a_64(k) & (cap - 1)
        while s in slots:
            s = (s + 1) % cap
        slots[s] = k
    return [slots[s] for s in sorted(slots)]


def _map_loop_expect_lines(keys):
    """Expected stdout rows for the map_loop_keys program (values pinned in
    the program source below: alpha 1, gamma 2, beta 3)."""
    order = _map_key_visit_order(keys)
    values = {"alpha": 1, "gamma": 2, "beta": 3}
    rows = [f"k: {k} i: {i}" for i, k in enumerate(order)]
    rows += [f"lookup {k}: {values[k]}" for k in order]
    return rows


MAP_ACCEPTS = [
    ("""use sys.io
act main() -> i32 {
    mut m: Map[i32, string] = map[1: "one", 2: "two"]
    let n0: usize = m.len
    let got2 = m.get(2)
    m.put(3, "three")
    m.put(1, "uno")
    let uno = m.get(1)
    let three = m.get(3)
    m[2] = "dos"
    let dos: string = m[2]
    let h99 = m.has(99)
    let h1 = m.has(1)
    let h2 = m.has(2)
    io.println("len: {n0}")
    io.println("get 2: {got2}")
    io.println("after: {uno} {three}")
    io.println("bracket: {dos}")
    io.println("has 99: {h99} has 1: {h1} has 2: {h2}")
    return 0
}""",
     ["len: 2", "get 2: two", "after: uno three", "bracket: dos",
      "has 99: false has 1: true has 2: true"],
     "map_int_upsert"),
    ("""use sys.io
act main() -> i32 {
    mut m: Map[string, i32] = map[]
    m.put("alpha", 1)
    m.put("beta", 2)
    m.put("alpha", 11)
    m["gamma"] = 3
    let n: usize = m.len
    let a: i32 = m.get("alpha")
    let b: i32 = m.get("beta")
    let g: i32 = m["gamma"]
    io.println("len: {n} alpha: {a} beta: {b} gamma: {g}")
    return 0
}""",
     ["len: 3 alpha: 11 beta: 2 gamma: 3"],
     "map_string_keys"),
    ("""use sys.io
data Point { x: i32, y: i32 }
act main() -> i32 {
    mut names: Map[string, Point] = map["a": Point{ x: 1, y: 2 }, "b": Point{ x: 3, y: 4 }]
    names["c"] = Point{ x: 5, y: 6 }
    let p = names.get("b")
    let q = names["c"]
    let px: i32 = p.x
    let py: i32 = p.y
    let qx: i32 = q.x
    let qy: i32 = q.y
    io.println("child: {px}/{py}")
    io.println("child2: {qx}/{qy}")
    return 0
}""",
     ["child: 3/4", "child2: 5/6"],
     "map_child_values"),
    ("""use sys.io
act main() -> i32 {
    mut mixed: Map[i32, dyn] = map[1: 15, 2: "box", 3: 2.5]
    mixed[4] = true
    let d1 = (mixed.get(1) as i32)
    let d2 = (mixed.get(2) as string)
    let d3 = (mixed.get(3) as f64)
    let d4 = (mixed[4] as bool)
    io.println("dyn: {d1} {d2} {d3} {d4}")
    return 0
}""",
     ["dyn: 15 box 2.50 true"],
     "map_dyn_values"),
    ("""use sys.io
act main() -> i32 {
    let say: Map[bool, i32] = map[true: 10, false: 20]
    let bt = say.get(true)
    let bf = say[false]
    io.println("bool key: {bt}/{bf}")
    return 0
}""",
     ["bool key: 10/20"],
     "map_bool_keys"),
    # 5.2 slice 7 — get_or / take / key iteration / V edges
    ("""use sys.io
act main() -> i32 {
    mut m: Map[i32, string] = map[1: "one", 2: "two"]
    let hit = m.get_or(1, "?")
    let miss = m.get_or(9, "?")
    let n: usize = m.len
    let ro: Map[string, i32] = map["a": 1]
    let dv = ro.get_or("a", 99)
    let dm = ro.get_or("zz", 99)
    io.println("hit: {hit} miss: {miss} len: {n}")
    io.println("let: {dv} {dm}")
    return 0
}""",
     ["hit: one miss: ? len: 2", "let: 1 99"],
     "map_get_or_defaults"),
    ("""use sys.io
act main() -> i32 {
    mut m: Map[string, i32] = map["a": 7]
    let hit = m.get_or("a", m.take("zz"))
    io.println("hit: {hit}")
    let n: usize = m.len
    io.println("len: {n}")
    return 0
}""",
     ["hit: 7", "len: 1"],
     "map_get_or_lazy_default"),
    ("""use sys.io
act main() -> i32 {
    mut m: Map[i32, i32] = map[1: 10, 2: 20, 3: 30]
    let got = m.take(2)
    let n1: usize = m.len
    let h2 = m.has(2)
    m.put(2, 22)
    let back = m.get_or(2, 0)
    let n2: usize = m.len
    let got3 = m.take(3)
    let n3: usize = m.len
    io.println("got: {got} n1: {n1} has2: {h2} back: {back} n2: {n2} got3: {got3} n3: {n3}")
    return 0
}""",
     ["got: 20 n1: 2 has2: false back: 22 n2: 3 got3: 30 n3: 2"],
     "map_take_recycle"),
    ("""use sys.io
act main() -> i32 {
    mut d: Map[i32, dyn] = map[1: 15, 2: "box"]
    let hit = d.get_or(1, "none")
    let miss = d.get_or(9, "none")
    let u1 = (hit as i32)
    let u2 = (miss as string)
    let taken = d.take(1)
    let u3 = (taken as i32)
    let n: usize = d.len
    io.println("dyn: {u1} {u2} {u3} len: {n}")
    return 0
}""",
     ["dyn: 15 none 15 len: 1"],
     "map_dyn_get_or"),
    ("""use sys.io
act main() -> i32 {
    mut km: Map[string, shelf[i32]] = map["a": shelf[1, 2]]
    let got = km.get("a")
    let g: usize = got.len
    let orv = km.get_or("b", shelf[7])
    let o: usize = orv.len
    let taken = km.take("a")
    let t: usize = taken.len
    io.println("child: {g} {o} {t}")
    return 0
}""",
     ["child: 2 1 2"],
     "map_child_header"),
    ("""use sys.io
act main() -> i32 {
    mut mm: Map[string, Map[i32, i32]] = map["a": map[1: 11]]
    let child = mm.take("a")
    let c: usize = child.len
    let inner = child.get(1)
    io.println("child map: {c} {inner}")
    return 0
}""",
     ["child map: 1 11"],
     "map_child_map_header"),
    ("""use sys.io
act main() -> i32 {
    mut mm: Map[string, Map[i32, i32]] = map["a": map[1: 11]]
    mut child = mm.get("a")
    child.put(2, 22)
    let c: usize = child.len
    let n: usize = mm.len
    let r1 = child.get(2)
    io.println("child: {c} outer: {n} own: {r1}")
    return 0
}""",
     ["child: 2 outer: 1 own: 22"],
     "map_child_mut_copy"),
    ("""use sys.io
act main() -> i32 {
    mut km: Map[string, i32] = map["alpha": 1, "gamma": 2, "beta": 3]
    loop kx, i of km {
        io.println("k: {kx} i: {i}")
    }
    loop key of km {
        let v = km.get_or(key, 0)
        io.println("lookup {key}: {v}")
    }
    return 0
}""",
     _map_loop_expect_lines(["alpha", "gamma", "beta"]),
     "map_loop_keys"),
    ("""use sys.io
act main() -> i32 {
    let empty: Map[string, i32] = map[]
    mut ran = 0
    loop ek of empty {
        ran = ran + 1
    }
    io.println("ran: {ran}")
    return 0
}""",
     ["ran: 0"],
     "map_loop_empty"),
]

# 5.2 slice 6 — struct values ride the map as dyn elements, so the
# cross-call boundary pins exact-KV spellings on both stages.
MAP_CALL_PARITY = [
    ("""use sys.io
act grab(m: Map[i32, string]) -> string {
    return m.get(42)
}
act main() -> i32 {
    mut m: Map[i32, string] = map[42: "everything"]
    let v = grab(m)
    io.println(v)
    return 0
}""",
     ["everything"],
     "map_call_exact"),
    ("""use sys.io
act count(m: Map[string, i32]) -> usize {
    return m.len
}
act main() -> i32 {
    mut m: Map[string, i32] = map["a": 1]
    let v: usize = count(m)
    io.println("len: {v}")
    return 0
}""",
     ["len: 1"],
     "map_call_len"),
]

MAP_REJECTIONS = [
    ("act main() -> i32 { mut m: Map[Point, string] = map[] return 0 }",
     "map keys must be integer, bool, or string (got Point)", "key_struct"),
    ("act main() -> i32 { mut m: Map[f32, string] = map[] return 0 }",
     "map keys must be integer, bool, or string (got f32)", "key_float"),
    ("act main() -> i32 { mut m = map[1: \"a\", \"b\": \"c\"] return 0 }",
     "map literal key types differ: i32 vs string", "key_differ"),
    ("act main() -> i32 { mut m = map[1: 5, 2: (7 as i64)] return 0 }",
     "map literal value types differ: i32 vs i64", "val_differ"),
    ("act main() -> i32 { mut m: Map[i32, string] = map[0: \"a\"] m.put(1) return 0 }",
     "map.put expects exactly 2 arguments: (map m, key, value)", "put_arity"),
    ("act main() -> i32 { mut m: Map[i32, string] = map[0: \"a\"] m.get() return 0 }",
     "map.get expects exactly 1 argument: (map m, key)", "get_arity"),
    ("act main() -> i32 { mut m: Map[i32, string] = map[0: \"a\"] m.get(1, 2) return 0 }",
     "map.get expects exactly 1 argument: (map m, key)", "get_arity2"),
    ("act main() -> i32 { mut m: Map[i32, string] = map[0: \"a\"] m.has() return 0 }",
     "map.has expects exactly 1 argument: (map m, key)", "has_arity"),
    ("act main() -> i32 { mut m: Map[i32, string] = map[0: \"a\"] m.nope() return 0 }",
     "unknown map member 'nope' (put, get, has, len, get_or, take, free, destroy are available)", "unknown_member"),
    ("act main() -> i32 { mut m: Map[i32, string] = map[0: \"a\"] let w = m.nope return 0 }",
     "unknown map member 'nope' (put, get, has, len, get_or, take, free, destroy are available)", "unknown_prop"),
    ("act main() -> i32 { let n: Map[i32, string] = map[0: \"a\"] n.put(1, \"b\") return 0 }",
     "cannot put into a map held by a let (declare with mut)", "put_on_let"),
    ("act main() -> i32 { let n: Map[i32, string] = map[0: \"a\"] n[1] = \"b\" return 0 }",
     "cannot write into a map held by a let (declare with mut)", "write_on_let"),
    ("act main() -> i32 { mut m: Map[i32, string] = map[0: \"a\"] m.put(\"w\", \"v\") return 0 }",
     "map key mismatch: expected i32 (got string)", "put_key_mismatch"),
    ("act main() -> i32 { mut m: Map[i32, string] = map[0: \"a\"] m.get(\"w\") return 0 }",
     "map key mismatch: expected i32 (got string)", "get_key_mismatch"),
    ("act main() -> i32 { mut m: Map[i32, string] = map[0: \"a\"] m.put(1, 7) return 0 }",
     "map value mismatch: expected string (got i32)", "put_val_mismatch"),
    ("act main() -> i32 { let n: Map[i64, string] = map[1: \"a\"] return 0 }",
     "map literal type Map[i32, string] does not match annotation Map[i64, string]", "ann_mismatch"),
    ("act main() -> i32 { let e = map[] return 0 }",
     "cannot infer key and value types of empty map literal — annotate it (e.g. let m: Map[i32, string] = map[])", "empty_no_ann"),
    ("act main() -> i32 { mut m = map[1: null] return 0 }",
     "map values cannot be null (use a @T pointer value)", "null_value"),
    ("act main() -> i32 { mut m: Map[dyn, string] = map[] return 0 }",
     "map keys must be integer, bool, or string (got dyn)", "illegalDynKey"),
    ("act main() -> i32 { let n: Map = map[] return 0 }",
     "a bare 'Map' needs key and value types: use Map[K, V]", "bare_map"),
    # cross-call boundary: distinct spellings of the SAME two slots reject
    ("use sys.io\nact grab(m: Map[i32, string]) -> string { return m.get(1) }\n"
     "act main() -> i32 { mut other: Map[string, i32] = map[\"a\": 1] let v = grab(other) return 0 }",
     "map argument types must match exactly: got Map[string, i32], expected Map[i32, string]", "cross_map_mismatch"),
    ("act main() -> i32 { mut m: Map[i32, string] = map[0: \"a\"] m[0] += \"x\" return 0 }",
     "compound assignments on maps are not supported yet — use an explicit '=' write", "compound"),
    # 5.2 slice 7 — get_or / take / of-source rejects
    ("act main() -> i32 { mut m: Map[i32, string] = map[0: \"a\"] m.get_or(1) return 0 }",
     "map.get_or expects exactly 2 arguments: (map m, key, default)", "getor_arity1"),
    ("act main() -> i32 { mut m: Map[i32, string] = map[0: \"a\"] m.get_or(1, \"b\", \"c\") return 0 }",
     "map.get_or expects exactly 2 arguments: (map m, key, default)", "getor_arity3"),
    ("act main() -> i32 { mut m: Map[i32, string] = map[0: \"a\"] let x = m.get_or(\"w\", \"v\") return 0 }",
     "map key mismatch: expected i32 (got string)", "getor_key_mismatch"),
    ("act main() -> i32 { mut m: Map[i32, string] = map[0: \"a\"] let x = m.get_or(0, 7) return 0 }",
     "map value mismatch: expected string (got i32)", "getor_default_mismatch"),
    ("act main() -> i32 { mut m: Map[i32, string] = map[0: \"a\"] let x = m.get_or(2, null) return 0 }",
     "map value mismatch: expected string (got @void)", "getor_null_default"),
    ("act main() -> i32 { mut m: Map[i32, string] = map[0: \"a\"] m.take(1, 2) return 0 }",
     "map.take expects exactly 1 argument: (map m, key)", "take_arity"),
    ("act main() -> i32 { mut m: Map[i32, string] = map[0: \"a\"] m.take() return 0 }",
     "map.take expects exactly 1 argument: (map m, key)", "take_arity0"),
    ("act main() -> i32 { let n: Map[i32, string] = map[0: \"a\"] let x = n.take(0) return 0 }",
     "cannot take from a map held by a let (declare with mut)", "take_on_let"),
    ("act main() -> i32 { mut m: Map[i32, string] = map[0: \"a\"] m.take(\"w\") return 0 }",
     "map key mismatch: expected i32 (got string)", "take_key_mismatch"),
    ("act main() -> i32 { loop x of 3 { io.println(\"x\") } return 0 }",
     "the 'of' source of a loop must be a shelf, map, or ring (got i32)", "of_odd_source"),
]

MAP_FATALS = [
    ("use sys.io\nact main() -> i32 { mut m: Map[string, i32] = map[\"a\": 1] let n = m.get(\"zz\") io.println(n) return 0 }",
     "Velo Fatal Error: map key not found: zz!", "fatal_str"),
    ("use sys.io\nact main() -> i32 { mut m: Map[bool, i32] = map[true: 1] let n = m.get(false) io.println(n) return 0 }",
     "Velo Fatal Error: map key not found: false!", "fatal_bool"),
    ("use sys.io\nact main() -> i32 { mut m: Map[i32, string] = map[1: \"a\"] let n: string = m[9] io.println(n) return 0 }",
     "Velo Fatal Error: map key not found: 9!", "fatal_sub"),
    # 5.2 slice 7 — take's fatal family: miss and second take
    ("use sys.io\nact main() -> i32 { mut m: Map[string, i32] = map[\"a\": 1] let n = m.take(\"zz\") io.println(n) return 0 }",
     "Velo Fatal Error: map key not found: zz!", "fatal_take_miss"),
    ("use sys.io\nact main() -> i32 { mut m: Map[i32, i32] = map[5: 55] let a = m.take(5) let b = m.take(5) io.println(a) return 0 }",
     "Velo Fatal Error: map key not found: 5!", "fatal_take_second"),
]


class TestMapBasics(unittest.TestCase):
    """gaps.md 5.2 slice 6 — Map[K, V] core surface parity."""

    def test_map_accepts_parity(self):
        for program, expected, name in MAP_ACCEPTS:
            with self.subTest(name=name):
                assert_parity(program, f"map52_{name}", expected)

    def test_map_call_boundary_parity(self):
        for program, expected, name in MAP_CALL_PARITY:
            with self.subTest(name=name):
                assert_parity(program, f"map52_{name}", expected)


class TestMapRejections(unittest.TestCase):
    """Both stages must reject the same programs with the same words."""

    def test_compile_rejections(self):
        tmp = ROOT / ".velo_cache" / "map52_reject"
        tmp.mkdir(parents=True, exist_ok=True)
        for program, want, name in MAP_REJECTIONS:
            src = tmp / f"{name}.vl"
            src.write_text(program, encoding="utf-8")
            for stage, res in (("stage1", check_result("stage1", src)),
                               ("stage2", check_result("stage2", src))):
                text = res.stdout + res.stderr
                self.assertNotEqual(res.returncode, 0, f"{stage} accepted {name}:\n{text[-2000:]}")
                self.assertIn(want, text, f"{stage} wording mismatch for {name}:\n{text[-2000:]}")

    def test_runtime_fatals(self):
        for program, want, name in MAP_FATALS:
            for stage in ("stage1", "stage2"):
                res = run_stage(stage, program, f"map52_{name}")
                self.assertNotEqual(res.returncode, 0, f"{stage} survived {name}!")
                text = res.stdout + res.stderr
                self.assertIn(want, text, f"{stage} fatal wording mismatch:\n{text[-2000:]}")


# ======================================================================
# 5.2 slice 8 — raw-dyn operators + the U64 tag: auto-unbox arithmetic
# (result RE-BOXED as dyn), same-family compares (plain bool), warning-
# free u64 boxing, and the U64 roundtrip. Both stages lower identical C
# (temps + box + the runtime ladder helpers), so outputs must be
# byte-identical by construction — this class pins it anyway.
# ======================================================================

class TestDynOperators(unittest.TestCase):
    """gaps.md 5.2 slice 8 — the auto-unbox operator surface parity."""

    def test_dyn_arith_and_compare_accepts(self):
        # dyn+concrete (both sides), dyn+dyn, the float ladder, compares
        # per family (int/int, float/float, string strcmp, bool/bool).
        program = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    mut bag: shelf[dyn] = shelf[10, 3, \"z\"]\n"
            "    let a = bag[0] + 2\n"
            "    let b = 2 + bag[0]\n"
            "    let c = bag[0] + bag[1]\n"
            "    let av = a as i32\n"
            "    let bv = b as i32\n"
            "    let cv = c as i32\n"
            "    io.println(\"a {av} b {bv} c {cv}\")\n"
            "    let f = bag[0] + 0.5\n"
            "    let fv = f as f64\n"
            "    io.println(\"f {fv}\")\n"
            "    mut fb: shelf[dyn] = shelf[2, 0.5, \"z\"]\n"
            "    let g = fb[0] + fb[1]\n"
            "    let gv = g as f64\n"
            "    io.println(\"g {gv}\")\n"
            "    let c1 = bag[0] < 100\n"
            "    let c2 = bag[0] == bag[1]\n"
            "    let c3 = fb[1] > 0.25\n"
            "    io.println(\"c1 {c1} c2 {c2} c3 {c3}\")\n"
            "    mut sb: shelf[dyn] = shelf[1, \"abc\", \"z\"]\n"
            "    let s1 = sb[1] == \"abc\"\n"
            "    let s2 = sb[1] < \"abd\"\n"
            "    io.println(\"s1 {s1} s2 {s2}\")\n"
            "    mut bb: shelf[dyn] = shelf[1, true, \"z\"]\n"
            "    let b1 = bb[1] == true\n"
            "    io.println(\"b1 {b1}\")\n"
            "    return 0\n"
            "}"
        )
        s1 = run_stage("stage1", program, "shelf52_s8_arith")
        s2 = run_stage("stage2", program, "shelf52_s8_arith")
        self.assertEqual(s1.returncode, 0, s1.stderr[-2000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-2000:])
        self.assertEqual(s1.stdout, s2.stdout, "S8 arith/compare outputs diverged")
        self.assertEqual(
            s1.stdout.strip().splitlines(),
            ["a 12 b 12 c 13", "f 10.50", "g 2.50",
             "c1 true c2 false c3 true", "s1 true s2 true", "b1 true"],
        )

    def test_u64_box_roundtrip(self):
        # The slice-2 residual closed: a big literal in a mixed bag boxes the
        # U64 tag (warning-free) and `as u64` reads it exactly; u64-typed
        # sources box U64 too; `as i64` off the U64 box is the signed view.
        program = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    mut bag: shelf[dyn] = shelf[18446744073709551615, \"z\"]\n"
            "    let u = bag[0] as u64\n"
            "    if u == 18446744073709551615 {\n"
            "        io.println(\"exact\")\n"
            "    }\n"
            "    let w = bag[0] as i64\n"
            "    if w == -1 {\n"
            "        io.println(\"signed view\")\n"
            "    }\n"
            "    let small: u64 = 7\n"
            "    mut sb: shelf[dyn] = shelf[small, \"z\"]\n"
            "    let v = sb[0] as u64\n"
            "    let vi = v as i64\n"
            "    io.println(\"v {vi}\")\n"
            "    return 0\n"
            "}"
        )
        s1 = run_stage("stage1", program, "shelf52_s8_u64")
        s2 = run_stage("stage2", program, "shelf52_s8_u64")
        self.assertEqual(s1.returncode, 0, s1.stderr[-2000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-2000:])
        self.assertEqual(s1.stdout, s2.stdout, "S8 u64 roundtrip outputs diverged")
        self.assertEqual(
            s1.stdout.strip().splitlines(),
            ["exact", "signed view", "v 7"],
        )


# ======================================================================
# 5.2 slice 9 — ring[T] + bitset: FIFO rings with O(1) front removal
# (wrap-boundary battery, snapshot iteration, the fatal family) and the
# word-array bitset (set/clear/toggle/has/count/first_unset, the in-place
# pair ops). Both stages lower identical C onto the shared runtime engines.
# ======================================================================

RING_REJECTIONS = [
    ("use sys.io\nact main() -> i32 {\n    let r: ring = ring[]\n    return 0\n}",
     "a bare 'ring' needs an element type: use ring[T]", "r_bare_ring"),
    ("use sys.io\nact main() -> i32 {\n    mut r: ring[i32] = ring[]\n    r.put(\"s\")\n    return 0\n}",
     "ring.put element mismatch: expected i32 (got string)", "r_put_mismatch"),
    ("use sys.io\nact main() -> i32 {\n    mut r: ring[i32] = ring[]\n    r.put()\n    return 0\n}",
     "ring.put expects exactly 1 argument: (ring r, element value)", "r_put_arity"),
    ("use sys.io\nact main() -> i32 {\n    mut r: ring[i32] = ring[]\n    let v = r.pop(1)\n    return 0\n}",
     "ring.pop takes no arguments", "r_pop_arity"),
    ("use sys.io\nact main() -> i32 {\n    let r: ring[i32] = ring[]\n    r.put(1)\n    return 0\n}",
     "cannot put into a ring held by a let (declare with mut)", "r_put_on_let"),
    ("use sys.io\nact main() -> i32 {\n    let r: ring[i32] = ring[]\n    let v = r.pop()\n    return 0\n}",
     "cannot pop from a ring held by a let (declare with mut)", "r_pop_on_let"),
    ("use sys.io\nact main() -> i32 {\n    let r = ring[]\n    return 0\n}",
     "cannot infer element type of empty ring literal", "r_empty_infer"),
    ("use sys.io\nact main() -> i32 {\n    let a: i64 = 5\n    let r = ring[1, a]\n    return 0\n}",
     "ring literal element types differ: i32 vs i64", "r_lit_differ"),
    ("use sys.io\nact main() -> i32 {\n    mut bag: shelf[dyn] = shelf[1, \"x\"]\n    let r = ring[bag[0]]\n    return 0\n}",
     "ring element type dyn is not supported — use a @dyn pointer element", "r_dyn_elem"),
    ("use sys.io\nact main() -> i32 {\n    let r: ring[i32] = ring[1]\n    let v = r[0]\n    return 0\n}",
     "ring does not support subscript reads — use peek()", "r_subscript"),
    ("use sys.io\nact main() -> i32 {\n    let r: ring[i32] = ring[]\n    let n = r.push(1)\n    return 0\n}",
     "unknown ring member 'push' (put, pop, peek, len are available)", "r_unknown"),
    ("act show(r: ring[i64]) -> i32 {\n    return 0\n}\nuse sys.io\nact main() -> i32 {\n    mut r: ring[i32] = ring[5, 6]\n    show(r)\n    return 0\n}",
     "ring argument element types must match exactly: got ring[i32], expected ring[i64]", "r_cross_call"),
    # bitset walls
    ("use sys.io\nact main() -> i32 {\n    mut b: bitset = bitset[]\n    b.set(\"s\")\n    return 0\n}",
     "bitset index must be an integer (got string)", "r_bs_index"),
    ("use sys.io\nact main() -> i32 {\n    let b: bitset = bitset[]\n    b.set(1)\n    return 0\n}",
     "cannot mutate a bitset held by a let (declare with mut)", "r_bs_on_let"),
    ("use sys.io\nact main() -> i32 {\n    mut b: bitset = bitset[]\n    b.set()\n    return 0\n}",
     "bitset.set expects exactly 1 argument: (bitset b, index)", "r_bs_arity"),
    ("use sys.io\nact main() -> i32 {\n    mut a: bitset = bitset[]\n    a.and(5)\n    return 0\n}",
     "bitset.and expects a bitset argument (got i32)", "r_bs_arg"),
    ("use sys.io\nact main() -> i32 {\n    let b: bitset = bitset[]\n    let n = b.count2\n    return 0\n}",
     "unknown bitset member 'count2' (set, clear, toggle, has, count, first_unset, and, or_with, xor_with, flip are available)", "r_bs_unknown"),
    ("use sys.io\nact main() -> i32 {\n    let b: i32 = bitset[1]\n    return 0\n}",
     "bitset literal does not match annotation i32", "r_bs_ann"),
]

RING_FATALS = [
    ("use sys.io\nact main() -> i32 {\n    mut r: ring[i32] = ring[]\n    let v = r.pop()\n    io.println(\"never\")\n    return 0\n}",
     "Velo Fatal Error: ring pop from an empty ring!", "f_pop_empty"),
    ("use sys.io\nact main() -> i32 {\n    let r: ring[i32] = ring[]\n    let v = r.peek()\n    io.println(\"never\")\n    return 0\n}",
     "Velo Fatal Error: ring peek from an empty ring!", "f_peek_empty"),
    ("use sys.io\nact main() -> i32 {\n    mut b: bitset = bitset[]\n    b.set(-1)\n    io.println(\"never\")\n    return 0\n}",
     "Velo Fatal Error: bitset index out of bounds: -1!", "f_bs_neg"),
]


class TestRingBitset(unittest.TestCase):
    """gaps.md 5.2 slice 9 — the ring[T] + bitset surface parity."""

    def test_ring_fifo_and_of(self):
        # FIFO order across the wrap boundary: 12 puts (capacity 8 -> 16
        # unroll), 10 pops, 6 more puts; peek is non-destructive; `loop of`
        # walks the snapshot front-to-back and the live ring is untouched.
        program = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    mut r: ring[i32] = ring[]\n"
            "    loop 12 { r.put(it as i32) }\n"
            "    mut acc = 0\n"
            "    loop 10 { let v = r.pop() acc = acc + v }\n"
            "    loop 6 { r.put(100 + it as i32) }\n"
            "    let ln = r.len as i32\n"
            "    let fr = r.peek() as i32\n"
            "    io.println(\"len {ln} acc {acc} front {fr}\")\n"
            "    loop v, i of r {\n"
            "        io.println(\"v {v}\")\n"
            "    }\n"
            "    let ln2 = r.len as i32\n"
            "    io.println(\"after of {ln2}\")\n"
            "    return 0\n"
            "}"
        )
        s1 = run_stage("stage1", program, "ring9_fifo")
        s2 = run_stage("stage2", program, "ring9_fifo")
        self.assertEqual(s1.returncode, 0, s1.stderr[-2000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-2000:])
        self.assertEqual(s1.stdout, s2.stdout, "S9 ring FIFO outputs diverged")
        self.assertEqual(
            s1.stdout.strip().splitlines(),
            ["len 8 acc 45 front 10", "v 10", "v 11", "v 100", "v 101", "v 102", "v 103", "v 104", "v 105",
             "after of 8"],
        )

    def test_ring_literals_and_families(self):
        # The literal ladder: homogeneous i32, the f64 widen, strings; pops
        # run FIFO from a mut ring; peek reads the head on a let.
        program = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    let r = ring[1, 2, 3]\n"
            "    let ln = r.len as i32\n"
            "    io.println(\"len {ln}\")\n"
            "    mut w = ring[1, 2.5, 3]\n"
            "    let v = w.pop() as f64\n"
            "    io.println(\"v {v}\")\n"
            "    mut s = ring[\"a\", \"b\"]\n"
            "    let head = s.peek()\n"
            "    io.println(\"head {head}\")\n"
            "    return 0\n"
            "}"
        )
        s1 = run_stage("stage1", program, "ring9_lits")
        s2 = run_stage("stage2", program, "ring9_lits")
        self.assertEqual(s1.returncode, 0, s1.stderr[-2000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-2000:])
        self.assertEqual(s1.stdout, s2.stdout, "S9 ring literal outputs diverged")
        self.assertEqual(s1.stdout.strip().splitlines(), ["len 3", "v 1.00", "head a"])

    def test_bitset_surface(self):
        # set/clear/toggle/has/count/first_unset against hand-computed words;
        # the pair ops (and truncates to the other's coverage, or/xor
        # materialize it, flip complements the materialized words); `bitset[]`
        # infers with no annotation.
        program = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    mut b = bitset[1, 9, 100]\n"
            "    let c1 = b.count() as i32\n"
            "    let f1 = b.first_unset() as i32\n"
            "    let h1 = b.has(1)\n"
            "    let h2 = b.has(2)\n"
            "    io.println(\"c1 {c1} first {f1} h1 {h1} h2 {h2}\")\n"
            "    b.clear(9)\n"
            "    b.toggle(2)\n"
            "    let c2 = b.count() as i32\n"
            "    let h2b = b.has(2)\n"
            "    io.println(\"c2 {c2} h2b {h2b}\")\n"
            "    mut a = bitset[1, 9]\n"
            "    mut o = bitset[9, 100]\n"
            "    a.and(o)\n"
            "    let ca = a.count() as i32\n"
            "    a.or_with(o)\n"
            "    let cb = a.count() as i32\n"
            "    let h100 = a.has(100)\n"
            "    a.xor_with(o)\n"
            "    let cc = a.count() as i32\n"
            "    a.flip()\n"
            "    let h1f = a.has(1)\n"
            "    let h0f = a.has(0)\n"
            "    io.println(\"and {ca} or {cb} h100 {h100}\")\n"
            "    io.println(\"xor {cc} flip h1 {h1f} h0 {h0f}\")\n"
            "    let e = bitset[]\n"
            "    let ce = e.count() as i32\n"
            "    let fe = e.first_unset() as i32\n"
            "    io.println(\"empty {ce} {fe}\")\n"
            "    return 0\n"
            "}"
        )
        s1 = run_stage("stage1", program, "ring9_bitset")
        s2 = run_stage("stage2", program, "ring9_bitset")
        self.assertEqual(s1.returncode, 0, s1.stderr[-2000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-2000:])
        self.assertEqual(s1.stdout, s2.stdout, "S9 bitset outputs diverged")
        self.assertEqual(
            s1.stdout.strip().splitlines(),
            ["c1 3 first 0 h1 true h2 false", "c2 3 h2b true",
             "and 1 or 2 h100 true", "xor 0 flip h1 true h0 true", "empty 0 0"],
        )

    def test_ring_rejections(self):
        tmp = ROOT / ".velo_cache" / "ring9_reject"
        tmp.mkdir(parents=True, exist_ok=True)
        for program, want, name in RING_REJECTIONS:
            src = tmp / f"{name}.vl"
            src.write_text(program, encoding="utf-8")
            for stage, res in (("stage1", check_result("stage1", src)),
                               ("stage2", check_result("stage2", src))):
                text = res.stdout + res.stderr
                self.assertNotEqual(res.returncode, 0, f"{stage} accepted {name}:\n{text[-2000:]}")
                self.assertIn(want, text, f"{stage} wording mismatch for {name}:\n{text[-2000:]}")

    def test_ring_fatals(self):
        for program, want, name in RING_FATALS:
            for stage in ("stage1", "stage2"):
                res = run_stage(stage, program, f"ring9_{name}")
                self.assertNotEqual(res.returncode, 0, f"{stage} survived {name}!")
                text = res.stdout + res.stderr
                self.assertIn(want, text, f"{stage} fatal wording mismatch:\n{text[-2000:]}")


# ======================================================================
# 5.2 slice 10 — the memory model: `heap shelf` (the VeloShelf.src
# allocator selector — zone-backed NULL default, heap sentinel for
# outliving zones) and the shared-rows closure (the row-copy guard
# tests the row type's pointer-ness; @shelf rows share; value rows
# keep the reject). The `as @shelf` dyn unbox re-opens (identity
# roundtrip). Both stages lower identical C onto the shared runtime.
# ======================================================================

S10_REJECTIONS = [
    ("use sys.io\nact main() -> i32 {\n    let h: shelf[i32] = heap shelf[1]\n    return 0\n}",
     "shelf literal element type heap shelf[i32] does not match annotation shelf[i32]", "s10_h_to_zone"),
    ("use sys.io\nact main() -> i32 {\n    let h: heap shelf[i32] = shelf[1]\n    return 0\n}",
     "shelf literal element type shelf[i32] does not match annotation heap shelf[i32]", "s10_zone_to_h"),
    ("use sys.io\nact main() -> i32 {\n    let h: heap shelf = heap shelf[]\n    return 0\n}",
     "a bare 'heap shelf' needs an element type: use heap shelf[T]", "s10_bare"),
    ("use sys.io\nact main() -> i32 {\n    let h = heap shelf[]\n    return 0\n}",
     "cannot infer element type of empty shelf literal", "s10_empty_infer"),
    ("act show(h: shelf[i32]) -> i32 {\n    return 0\n}\nuse sys.io\nact main() -> i32 {\n    mut h = heap shelf[1]\n    show(h)\n    return 0\n}",
     "shelf argument element types must match exactly: got heap shelf[i32], expected shelf[i32]", "s10_cross_call"),
    ("use sys.io\nact main() -> i32 {\n    mut grid = shelf[shelf[1, 2]]\n    grid[0][1] = 5\n    return 0\n}",
     "cannot write through a shelf row copy (snapshot rows) — use @shelf[int] rows for in-place mutation", "s10_valrow"),
    ("use sys.io\nact main() -> i32 {\n    let h = heap shelf[1]\n    h.put(2)\n    return 0\n}",
     "cannot put into a shelf held by a let (declare with mut)", "s10_heap_on_let"),
]


class TestHeapShelf(unittest.TestCase):
    """gaps.md 5.2 slice 10 — the heap shelf + shared-rows surface parity."""

    def test_heap_outlives_zone_and_act(self):
        # The sheet's pinned rows: a heap shelf returned from an act, and a
        # heap shelf grown INSIDE a `zone { }` that stays intact after the
        # exit (the arena reclaims its own blocks; the heap ledger keeps the
        # shelf's).
        program = (
            "use sys.io\n"
            "act make() -> heap shelf[i32] {\n"
            "    mut h = heap shelf[1, 2]\n"
            "    loop 50 { h.put(it as i32) }\n"
            "    return h\n"
            "}\n"
            "act main() -> i32 {\n"
            "    let h = make()\n"
            "    mut g: heap shelf[i32] = heap shelf[]\n"
            "    zone 1024 {\n"
            "        loop 100 { g.put(it as i32) }\n"
            "    }\n"
            "    let ln = h.len as i32\n"
            "    let v51 = h[51]\n"
            "    let gn = g.len as i32\n"
            "    let last = g[99]\n"
            "    io.println(\"len {ln} v51 {v51} gn {gn} last {last}\")\n"
            "    return 0\n"
            "}"
        )
        s1 = run_stage("stage1", program, "s10_heap")
        s2 = run_stage("stage2", program, "s10_heap")
        self.assertEqual(s1.returncode, 0, s1.stderr[-2000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-2000:])
        self.assertEqual(s1.stdout, s2.stdout, "S10 heap outputs diverged")
        self.assertEqual(s1.stdout.strip().splitlines(), ["len 52 v51 49 gn 100 last 99"])

    def test_shared_rows(self):
        # The slice-1 residual (1) closure: @shelf rows share their storage —
        # `grid[i].put(v)` AND `grid[i][j] = v` mutate the SHARED row (the
        # sibling binding sees it); value rows keep the row-copy reject.
        program = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    mut r1: shelf[i32] = shelf[1, 2]\n"
            "    mut r2: shelf[i32] = shelf[3, 4]\n"
            "    mut grid: shelf[@shelf[i32]] = shelf[@r1, @r2]\n"
            "    grid[0].put(9)\n"
            "    grid[0][1] = 7\n"
            "    let a = r1[1]\n"
            "    let b = r1[2]\n"
            "    let c = r2.len as i32\n"
            "    io.println(\"a {a} b {b} c {c}\")\n"
            "    return 0\n"
            "}"
        )
        s1 = run_stage("stage1", program, "s10_shared")
        s2 = run_stage("stage2", program, "s10_shared")
        self.assertEqual(s1.returncode, 0, s1.stderr[-2000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-2000:])
        self.assertEqual(s1.stdout, s2.stdout, "S10 shared-row outputs diverged")
        self.assertEqual(s1.stdout.strip().splitlines(), ["a 7 b 9 c 2"])

    def test_as_shelfptr_roundtrip(self):
        # The slice-2 dangle reject retires: the PTR box holds a real pointer
        # the user owns; the unbox keeps IDENTITY (the same row comes back).
        program = (
            "use sys.io\n"
            "act main() -> i32 {\n"
            "    mut r1: shelf[i32] = shelf[5]\n"
            "    mut bag: shelf[dyn] = shelf[@r1, \"x\"]\n"
            "    mut p = bag[0] as @shelf[i32]\n"
            "    p.put(6)\n"
            "    let v = p[1]\n"
            "    mut back = bag[0] as @shelf[i32]\n"
            "    let ln = back.len as i32\n"
            "    io.println(\"v {v} ln {ln}\")\n"
            "    return 0\n"
            "}"
        )
        s1 = run_stage("stage1", program, "s10_unbox")
        s2 = run_stage("stage2", program, "s10_unbox")
        self.assertEqual(s1.returncode, 0, s1.stderr[-2000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-2000:])
        self.assertEqual(s1.stdout, s2.stdout, "S10 unbox outputs diverged")
        self.assertEqual(s1.stdout.strip().splitlines(), ["v 6 ln 2"])

    def test_s10_rejections(self):
        tmp = ROOT / ".velo_cache" / "s10_reject"
        tmp.mkdir(parents=True, exist_ok=True)
        for program, want, name in S10_REJECTIONS:
            src = tmp / f"{name}.vl"
            src.write_text(program, encoding="utf-8")
            for stage, res in (("stage1", check_result("stage1", src)),
                               ("stage2", check_result("stage2", src))):
                text = res.stdout + res.stderr
                self.assertNotEqual(res.returncode, 0, f"{stage} accepted {name}:\n{text[-2000:]}")
                self.assertIn(want, text, f"{stage} wording mismatch for {name}:\n{text[-2000:]}")



class TestHeapShelfTeardown(unittest.TestCase):
    """Task 7.1: Reallocation leak fix & explicit teardown for shelves."""

    def test_realloc_leak_free_and_teardown(self):
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act main() -> i32 {\n"
            "    let h0: usize = mem.heap_used()\n"
            "    mut s: heap shelf[i32] = heap shelf[]\n"
            "    loop 2000 {\n"
            "        s.put(it as i32)\n"
            "    }\n"
            "    let h1: usize = mem.heap_used()\n"
            "    let ln = s.len as i32\n"
            "    let v1999 = s[1999]\n"
            "    // Teardown with s.destroy()\n"
            "    s.destroy()\n"
            "    let h2: usize = mem.heap_used()\n"
            "    let ln_after = s.len as i32\n"
            "    io.println(\"h0 {h0} ln {ln} v1999 {v1999} h2 {h2} ln_after {ln_after}\")\n"
            "    return 0\n"
            "}"
        )
        s1 = run_stage("stage1", program, "t71_destroy")
        s2 = run_stage("stage2", program, "t71_destroy")
        self.assertEqual(s1.returncode, 0, s1.stderr[-2000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-2000:])
        self.assertEqual(s1.stdout, s2.stdout)
        self.assertEqual(s1.stdout.strip().splitlines(), ["h0 0 ln 2000 v1999 1999 h2 0 ln_after 0"])

    def test_teardown_methods_and_module_calls(self):
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act main() -> i32 {\n"
            "    // 1. s.free()\n"
            "    mut s1: heap shelf[i32] = heap shelf[1, 2, 3]\n"
            "    s1.free()\n"
            "    let h1: usize = mem.heap_used()\n"
            "    let len1 = s1.len as i32\n"
            "\n"
            "    // 2. shelf.free(@s)\n"
            "    mut s2: heap shelf[i32] = heap shelf[4, 5, 6]\n"
            "    shelf.free(@s2)\n"
            "    let h2: usize = mem.heap_used()\n"
            "    let len2 = s2.len as i32\n"
            "\n"
            "    // 3. shelf.destroy(@s)\n"
            "    mut s3: heap shelf[i32] = heap shelf[7, 8, 9]\n"
            "    shelf.destroy(@s3)\n"
            "    let h3: usize = mem.heap_used()\n"
            "    let len3 = s3.len as i32\n"
            "\n"
            "    // 4. zone shelf teardown is safe no-op on non-heap\n"
            "    mut s4: shelf[i32] = shelf[10, 11]\n"
            "    s4.destroy()\n"
            "    let len4 = s4.len as i32\n"
            "\n"
            "    io.println(\"h1 {h1} len1 {len1} h2 {h2} len2 {len2} h3 {h3} len3 {len3} len4 {len4}\")\n"
            "    return 0\n"
            "}"
        )
        s1 = run_stage("stage1", program, "t71_variants")
        s2 = run_stage("stage2", program, "t71_variants")
        self.assertEqual(s1.returncode, 0, s1.stderr[-2000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-2000:])
        self.assertEqual(s1.stdout, s2.stdout)
        self.assertEqual(s1.stdout.strip().splitlines(), ["h1 0 len1 0 h2 0 len2 0 h3 0 len3 0 len4 0"])

    def test_teardown_rejections(self):
        tmp = ROOT / ".velo_cache" / "t71_reject"
        tmp.mkdir(parents=True, exist_ok=True)
        rejections = [
            ("use sys.io\nact main() -> i32 {\n    let s: heap shelf[i32] = heap shelf[1]\n    s.destroy()\n    return 0\n}",
             "cannot destroy from a shelf held by a let (declare with mut)", "rej_destroy_let"),
            ("use sys.io\nact main() -> i32 {\n    let s: heap shelf[i32] = heap shelf[1]\n    s.free()\n    return 0\n}",
             "cannot free from a shelf held by a let (declare with mut)", "rej_free_let"),
            ("use sys.io\nact main() -> i32 {\n    let s: heap shelf[i32] = heap shelf[1]\n    shelf.destroy(@s)\n    return 0\n}",
             "cannot destroy from a shelf held by a let (declare with mut)", "rej_module_destroy_let"),
            ("use sys.io\nact main() -> i32 {\n    mut s: heap shelf[i32] = heap shelf[1]\n    s.free(1)\n    return 0\n}",
             "shelf.free takes no arguments", "rej_free_args"),
            ("use sys.io\nact main() -> i32 {\n    shelf.free(123)\n    return 0\n}",
             "shelf.free argument must be a shelf (got i32)", "rej_free_arg_type"),
            ("use sys.io\nact main() -> i32 {\n    mut s: heap shelf[i32] = heap shelf[1]\n    shelf.destroy(@s, 1)\n    return 0\n}",
             "shelf.destroy expects exactly 1 argument: (shelf s)", "rej_destroy_arity"),
            ("use sys.io\nact main() -> i32 {\n    mut s: heap shelf[i32] = heap shelf[1]\n    shelf.other(@s)\n    return 0\n}",
             "unknown shelf function 'other' (destroy, free are available)", "rej_unknown_shelf_fn"),
        ]
        for program, want, name in rejections:
            src = tmp / f"{name}.vl"
            src.write_text(program, encoding="utf-8")
            for stage, res in (("stage1", check_result("stage1", src)),
                               ("stage2", check_result("stage2", src))):
                text = res.stdout + res.stderr
                self.assertNotEqual(res.returncode, 0, f"{stage} accepted {name}:\n{text[-2000:]}")
                self.assertIn(want, text, f"{stage} wording mismatch for {name}:\n{text[-2000:]}")


class TestHeapMapTeardown(unittest.TestCase):
    """Task 7.2: Parameterized and heap-backed maps (heap map[K, V] & map.destroy)."""

    def test_heap_map_5000_keys_survives_zone(self):
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act make_key(i: i32) -> string {\n"
            "    mut n = i as i64\n"
            "    if n == 0 { return \"k_0\" }\n"
            "    mut buf: @u8 = mem.heap_alloc(@u8, 32)\n"
            "    mut count: usize = 0\n"
            "    loop n > 0 {\n"
            "        buf[count] = ('0' as u8) + ((n % 10) as u8)\n"
            "        n = n / 10\n"
            "        count += 1\n"
            "    }\n"
            "    mut res: @u8 = mem.heap_alloc(@u8, count + 3)\n"
            "    res[0] = 'k' as u8\n"
            "    res[1] = '_' as u8\n"
            "    mut pos: usize = 0\n"
            "    loop pos < count {\n"
            "        res[2 + pos] = buf[count - 1 - pos]\n"
            "        pos += 1\n"
            "    }\n"
            "    res[2 + count] = 0 as u8\n"
            "    mem.free(buf)\n"
            "    return res as string\n"
            "}\n"
            "act populate() -> heap Map[string, i32] {\n"
            "    mut m: heap Map[string, i32] = heap map[]\n"
            "    zone {\n"
            "        mut i: i32 = 0\n"
            "        loop i < 5000 {\n"
            "            m.put(make_key(i), i)\n"
            "            i += 1\n"
            "        }\n"
            "    }\n"
            "    return m\n"
            "}\n"
            "act main() -> i32 {\n"
            "    mut m = populate()\n"
            "    let ln = m.len as i32\n"
            "    let v0 = m.get(\"k_0\")\n"
            "    let v2500 = m.get(\"k_2500\")\n"
            "    let v4999 = m.get(\"k_4999\")\n"
            "    let has_mid = m.has(\"k_2500\")\n"
            "    let has_none = m.has(\"k_99999\")\n"
            "    io.println(\"ln {ln} v0 {v0} v2500 {v2500} v4999 {v4999} has {has_mid} none {has_none}\")\n"
            "    return 0\n"
            "}\n"
        )
        s1 = run_stage("stage1", program, "t72_5000_zone")
        s2 = run_stage("stage2", program, "t72_5000_zone")
        self.assertEqual(s1.returncode, 0, s1.stderr[-2000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-2000:])
        self.assertEqual(s1.stdout, s2.stdout)
        self.assertEqual(s1.stdout.strip().splitlines(), ["ln 5000 v0 0 v2500 2500 v4999 4999 has true none false"])

    def test_realloc_leak_free_and_teardown(self):
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act main() -> i32 {\n"
            "    let h0: usize = mem.heap_used()\n"
            "    mut m: heap Map[i32, i32] = heap map[]\n"
            "    mut i: i32 = 0\n"
            "    loop i < 2000 {\n"
            "        m.put(i, i * 10)\n"
            "        i += 1\n"
            "    }\n"
            "    let h1: usize = mem.heap_used()\n"
            "    let ln = m.len as i32\n"
            "    let v1999 = m.get(1999)\n"
            "    m.destroy()\n"
            "    let h2: usize = mem.heap_used()\n"
            "    let ln_after = m.len as i32\n"
            "    io.println(\"h0 {h0} ln {ln} v1999 {v1999} h2 {h2} ln_after {ln_after}\")\n"
            "    return 0\n"
            "}\n"
        )
        s1 = run_stage("stage1", program, "t72_destroy")
        s2 = run_stage("stage2", program, "t72_destroy")
        self.assertEqual(s1.returncode, 0, s1.stderr[-2000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-2000:])
        self.assertEqual(s1.stdout, s2.stdout)
        self.assertEqual(s1.stdout.strip().splitlines(), ["h0 0 ln 2000 v1999 19990 h2 0 ln_after 0"])

    def test_teardown_methods_and_module_calls(self):
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act main() -> i32 {\n"
            "    // 1. m.free()\n"
            "    mut m1: heap Map[i32, i32] = heap map[1: 10, 2: 20]\n"
            "    m1.free()\n"
            "    let h1: usize = mem.heap_used()\n"
            "    let len1 = m1.len as i32\n"
            "\n"
            "    // 2. map.free(@m)\n"
            "    mut m2: heap Map[i32, i32] = heap map[3: 30, 4: 40]\n"
            "    map.free(@m2)\n"
            "    let h2: usize = mem.heap_used()\n"
            "    let len2 = m2.len as i32\n"
            "\n"
            "    // 3. map.destroy(@m)\n"
            "    mut m3: heap Map[i32, i32] = heap map[5: 50, 6: 60]\n"
            "    map.destroy(@m3)\n"
            "    let h3: usize = mem.heap_used()\n"
            "    let len3 = m3.len as i32\n"
            "\n"
            "    // 4. zone map teardown is safe no-op on non-heap\n"
            "    mut m4: Map[i32, i32] = map[7: 70]\n"
            "    m4.destroy()\n"
            "    let len4 = m4.len as i32\n"
            "\n"
            "    io.println(\"h1 {h1} len1 {len1} h2 {h2} len2 {len2} h3 {h3} len3 {len3} len4 {len4}\")\n"
            "    return 0\n"
            "}\n"
        )
        s1 = run_stage("stage1", program, "t72_variants")
        s2 = run_stage("stage2", program, "t72_variants")
        self.assertEqual(s1.returncode, 0, s1.stderr[-2000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-2000:])
        self.assertEqual(s1.stdout, s2.stdout)
        self.assertEqual(s1.stdout.strip().splitlines(), ["h1 0 len1 0 h2 0 len2 0 h3 0 len3 0 len4 0"])

    def test_teardown_rejections(self):
        tmp = ROOT / ".velo_cache" / "t72_reject"
        tmp.mkdir(parents=True, exist_ok=True)
        rejections = [
            ("use sys.io\nact main() -> i32 {\n    let m: heap Map[i32, i32] = heap map[1: 2]\n    m.destroy()\n    return 0\n}",
             "cannot destroy from a map held by a let (declare with mut)", "rej_destroy_let"),
            ("use sys.io\nact main() -> i32 {\n    let m: heap Map[i32, i32] = heap map[1: 2]\n    m.free()\n    return 0\n}",
             "cannot free from a map held by a let (declare with mut)", "rej_free_let"),
            ("use sys.io\nact main() -> i32 {\n    let m: heap Map[i32, i32] = heap map[1: 2]\n    map.destroy(@m)\n    return 0\n}",
             "cannot destroy from a map held by a let (declare with mut)", "rej_module_destroy_let"),
            ("use sys.io\nact main() -> i32 {\n    mut m: heap Map[i32, i32] = heap map[1: 2]\n    m.free(1)\n    return 0\n}",
             "map.free takes no arguments", "rej_free_args"),
            ("use sys.io\nact main() -> i32 {\n    map.free(123)\n    return 0\n}",
             "map.free argument must be a map (got i32)", "rej_free_arg_type"),
            ("use sys.io\nact main() -> i32 {\n    mut m: heap Map[i32, i32] = heap map[1: 2]\n    map.destroy(@m, 1)\n    return 0\n}",
             "map.destroy expects exactly 1 argument: (map m)", "rej_destroy_arity"),
            ("use sys.io\nact main() -> i32 {\n    mut m: heap Map[i32, i32] = heap map[1: 2]\n    map.other(@m)\n    return 0\n}",
             "unknown map function 'other' (destroy, free are available)", "rej_unknown_map_fn"),
        ]
        for program, want, name in rejections:
            src = tmp / f"{name}.vl"
            src.write_text(program, encoding="utf-8")
            for stage, res in (("stage1", check_result("stage1", src)),
                               ("stage2", check_result("stage2", src))):
                text = res.stdout + res.stderr
                self.assertNotEqual(res.returncode, 0, f"{stage} accepted {name}:\n{text[-2000:]}")
                self.assertIn(want, text, f"{stage} wording mismatch for {name}:\n{text[-2000:]}")


if __name__ == "__main__":
    unittest.main()
