"""5.1 String Processing Library — the sys.str built-ins beyond legacy
str.len: contains / starts_with / ends_with / index_of / trim / replace /
to_upper / to_lower / concat / split. Every case runs identically on the
Stage 1 Python compiler and the self-hosted Stage 2 native compiler
(gaps.md 5.1)."""
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from test_allocators import run_stage, ROOT, VELO_PY, VELO_EXE
from conftest import cc_path

RUNTIME = ROOT / "velo" / "runtime"

EXAMPLE30 = ROOT / "examples" / "30_string_library.vl"
EXAMPLE30_LINES = [
    "contains: yes",
    "contains empty: yes",
    "starts_with: yes",
    "ends_with: yes",
    "index_of: 4 / miss: -1",
    "trim: [trim me] len: 7",
    "replace: [a + b + c] [abc] [a-b-c]",
    "upper: MIXED 1337 _-!",
    "lower: mixed 1337 _-!",
    "concat: Velo rocks",
    "split[0] = 'v1'",
    "split[1] = '2'",
    "split[2] = ''",
    "split[3] = '7'",
    "split count: 4",
    "multi-char delim: a / b / c",
    "composed: there",
]

# Edge cases the happy-path example cannot show: empty inputs, non-overlap
# rules, position 0, single-token splits, no-match delimiters, and a
# function-call argument (each argument must be evaluated exactly once).
# \x0b \x0c are VT/FF — Velo has no \v \f escapes. Split reads ride the 5.2
# slice-11 owning shelf[string] (.len + bounds-checked indexing).
EDGE = """use sys.io

act heap_seed() -> string {
    return "abcabc"
}

act main() -> i32 {
    let e: string = ""
    let t0: string = str.trim(e)
    io.println("trim('') = [{t0}]")
    let t1: string = str.trim(" \\t\\r\\n\\x0b\\x0c ")
    io.println("trim(all-blank) = [{t1}]")
    let t2: string = str.trim("  x  y ")
    io.println("trim(keep-inner) = [{t2}]")

    let u0: string = str.to_upper(e)
    let l0: string = str.to_lower(e)
    io.println("case('') = [{u0}][{l0}]")

    let r0: string = str.replace(e, "a", "b")
    io.println("replace('','a','b') = [{r0}]")
    let r1: string = str.replace("aaa", "aa", "b")
    io.println("replace(non-overlap) = [{r1}]")
    let r2: string = str.replace(heap_seed(), "zz", "y")
    io.println("replace(no-occurrence) = [{r2}]")

    let c0: string = str.concat(e, "solo")
    let c1: string = str.concat("solo", e)
    io.println("concat = [{c0}][{c1}]")

    let i0: i64 = str.index_of("pos0", "p")
    io.println("index_of(at-0) = {i0}")
    if str.contains(e, e) { io.println("contains('','') = yes") }
    if str.contains(e, "x") { io.println("bad") } else { io.println("contains('','x') = no") }
    if str.ends_with(e, e) { io.println("ends('','') = yes") }
    if str.starts_with("solo", e) { io.println("starts('solo','') = yes") }

    let s0: shelf[string] = str.split("no-delim", ",")
    let s0n: usize = s0.len
    let s0t: string = s0[0]
    io.println("split(1-token) = {s0n} [{s0t}]")
    let s1: shelf[string] = str.split(e, ",")
    let s1n: usize = s1.len
    let s1t: string = s1[0]
    io.println("split('') = {s1n} [{s1t}]")
    let s2: shelf[string] = str.split("x", "xy")
    let s2n: usize = s2.len
    io.println("split(long-delim) = {s2n}")
    return 0
}
"""

EDGE_LINES = [
    "trim('') = []",
    "trim(all-blank) = []",
    "trim(keep-inner) = [x  y]",
    "case('') = [][]",
    "replace('','a','b') = []",
    "replace(non-overlap) = [ba]",
    "replace(no-occurrence) = [abcabc]",
    "concat = [solo][solo]",
    "index_of(at-0) = 0",
    "contains('','') = yes",
    "contains('','x') = no",
    "ends('','') = yes",
    "starts('solo','') = yes",
    "split(1-token) = 1 [no-delim]",
    "split('') = 1 []",
    "split(long-delim) = 1",
]

# Slice 11 ownership story: str.split returns an OWNING shelf[string] whose
# tokens are arena strings — the zone reclaims the tokens *and* the payload
# wholesale, so the HEAP ledger does not move at all (held == base == 0).
# The old single-block + single mem.free rows retired with the @string
# spelling; a shelf is NOT mem.free-able (mem_checks rejects it — residuals).
SPLIT_OWNERSHIP = """use sys.io
use sys.mem

act main() -> i32 {
    let base: usize = mem.heap_used()
    let parts: shelf[string] = str.split("one,two,three,,five", ",")
    let tok0: string = parts[0]
    let tok3: string = parts[3]
    let l0: usize = str.len(tok0)
    let l3: usize = str.len(tok3)
    let held: usize = mem.heap_used()
    let n: usize = parts.len
    io.println("lens = {l0} {l3} n = {n}")
    io.println("held = {held}")
    if held == base { io.println("zone-owned (ledger untouched)") }
    return 0
}
"""

SPLIT_OWNERSHIP_LINES = [
    "lens = 3 0 n = 5",
    "held = 0",
    "zone-owned (ledger untouched)",
]

# One fatal per runtime guard: each mini-harness is its own process (a fatal
# exits the process) and must die loudly with the exact message instead of
# letting C strlen/strstr walk a NULL or scan on an empty delimiter.
MINI_TEMPLATE = r"""
#include "velo_runtime.h"
int main(void) {
%s
}
"""

FATAL_CASES = [
    ('velo_str_contains(NULL, "x");', "str.contains got a null string", "str51_null_contains"),
    ('velo_str_starts_with("a", NULL);', "str.starts_with got a null string", "str51_null_starts"),
    ('velo_str_ends_with(NULL, "a");', "str.ends_with got a null string", "str51_null_ends"),
    ('velo_str_index_of(NULL, "x");', "str.index_of got a null string", "str51_null_index"),
    ('velo_str_trim(NULL);', "str.trim got a null string", "str51_null_trim"),
    ('velo_str_replace(NULL, "a", "b");', "str.replace got a null string", "str51_null_replace1"),
    ('velo_str_replace("a", NULL, "b");', "str.replace got a null string", "str51_null_replace2"),
    ('velo_str_to_upper(NULL);', "str.to_upper got a null string", "str51_null_upper"),
    ('velo_str_to_lower(NULL);', "str.to_lower got a null string", "str51_null_lower"),
    ('velo_str_concat("a", NULL);', "str.concat got a null string", "str51_null_concat"),
    ('velo_str_split(NULL, ",");', "str.split got a null string", "str51_null_split"),
    ('velo_str_split("a", "");', "str.split got an empty delimiter", "str51_empty_delim"),
    ('velo_str_format(NULL);', "str.format got a null string", "str82_null_format"),
    ('velo_str_heap_format(NULL);', "str.heap_format got a null string", "str82_null_heap_format"),
]

# Compile-time arity / argument-type rejections — identical wording on both
# stages (per-compiler position prefixes are the historical taxonomy, gaps 6.7).
REJECTIONS = [
    ('io.println(str.trim("a", "b"))',
     "str.trim expects exactly 1 argument: (string s)",
     "rej_trim_arity"),
    ('io.println(str.replace("a", "b"))',
     "str.replace expects exactly 3 arguments: (string s, string old, string new)",
     "rej_replace_arity"),
    ('io.println(str.concat("a", "b", "c"))',
     "str.concat expects exactly 2 arguments: (string a, string b)",
     "rej_concat_arity"),
    ('if str.contains("abc", 42) { io.println("y") }',
     "str.contains expects string arguments (got i32)",
     "rej_contains_int"),
    ("let buf: @u8 = mem.alloc(@u8, 4)\n    io.println(str.to_upper(buf))",
     "str.to_upper expects string arguments (got @u8)",
     "rej_upper_ptr"),
    ('if str.split("a,b", str.contains("a", "a")) != null { io.println("y") }',
     "str.split expects string arguments (got bool)",
     "rej_split_bool"),
    ("let p: @string = str.split(\"a,b\", \",\")",
     "str.split returns shelf[string] — annotating @string is retired (slice 11)",
     "rej_split_retired_anno"),
    ('io.println(str.heap_concat("a"))',
     "str.heap_concat expects exactly 2 arguments: (string a, string b)",
     "rej_heap_concat_arity"),
    ('io.println(str.heap_trim(42))',
     "str.heap_trim expects string arguments (got i32)",
     "rej_heap_trim_int"),
    ('io.println(str.format())',
     "str.format expects at least 1 argument: (string fmt, ...)",
     "rej_format_arity"),
    ('io.println(str.format(42))',
     "str.format expects string arguments (got i32)",
     "rej_format_int"),
    ('io.println(str.format("count: %d %d", 1))',
     "str.format format string expects 2 arguments (got 1)",
     "rej_format_spec_under"),
    ('io.println(str.format("count: %d", 1, 2))',
     "str.format format string expects 1 argument (got 2)",
     "rej_format_spec_over"),
    ('io.println(str.heap_format())',
     "str.heap_format expects at least 1 argument: (string fmt, ...)",
     "rej_heap_format_arity"),
    ('io.println(str.heap_format(42))',
     "str.heap_format expects string arguments (got i32)",
     "rej_heap_format_int"),
]

REJ_PROGRAM = """use sys.io
use sys.mem

act main() -> i32 {{
    {body}
    return 0
}}
"""


def expect_build_failure(body: str, name: str, want_msg: str):
    """Both stages must reject the program with the exact wording."""
    tmp = ROOT / ".velo_cache" / "str51_reject"
    tmp.mkdir(parents=True, exist_ok=True)
    src = tmp / f"{name}.vl"
    src.write_text(REJ_PROGRAM.format(body=body), encoding="utf-8")
    for stage, cmd in (("stage1", [sys.executable, str(VELO_PY), "check", str(src)]),
                       ("stage2", [str(VELO_EXE), "check", str(src)])):
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT,
                             encoding="utf-8", errors="replace")
        text = res.stdout + res.stderr
        assert res.returncode != 0, f"{stage} accepted:\n{text[-2000:]}"
        assert want_msg in text, f"{stage} message mismatch:\n{text[-2000:]}"


def find_gcc() -> str:
    found = shutil.which("gcc")
    if found:
        return found
    for candidate in (cc_path(), cc_path()):
        if Path(candidate).exists():
            return candidate
    raise RuntimeError("gcc not found — needed for the runtime fatal harnesses")


class TestStringLibrary(unittest.TestCase):
    """gaps.md 5.1 String Processing Library — sys.str surface parity."""

    def test_example30_parity_and_output(self):
        src = EXAMPLE30.read_text(encoding="utf-8")
        for stage, name in (("stage1", "example30_s1"), ("stage2", "example30_s2")):
            res = run_stage(stage, src, name)
            self.assertEqual(res.returncode, 0, f"{stage} run failed: {res.stderr[-2000:]}")
            self.assertEqual(
                res.stdout.strip().splitlines(), EXAMPLE30_LINES, f"{stage} example output diverged"
            )

    def test_edge_cases_parity(self):
        s1 = run_stage("stage1", EDGE, "str51_edge_s1")
        s2 = run_stage("stage2", EDGE, "str51_edge_s2")
        for label, res in (("stage1", s1), ("stage2", s2)):
            self.assertEqual(res.returncode, 0, f"{label} run failed: {res.stderr[-2000:]}")
        self.assertEqual(s1.stdout, s2.stdout, "edge outputs diverged between stages")
        self.assertEqual(
            s1.stdout.strip().splitlines(), EDGE_LINES, "edge-case outputs unrecognized"
        )

    def test_split_zone_owned_tokens(self):
        """Slice 11: split tokens are ARENA-owned (the shelf owns them, the
        zone reclaims wholesale) — the heap ledger never moves and indexing
        is bounds-checked."""
        for stage, name in (("stage1", "str51_owners_s1"), ("stage2", "str51_owners_s2")):
            res = run_stage(stage, SPLIT_OWNERSHIP, name)
            self.assertEqual(res.returncode, 0, f"{stage} run failed: {res.stderr[-2000:]}")
            self.assertEqual(
                res.stdout.strip().splitlines(), SPLIT_OWNERSHIP_LINES, f"{stage} ownership output diverged"
            )

    def test_compile_time_rejections(self):
        for body, want_msg, name in REJECTIONS:
            expect_build_failure(body, name, want_msg)

    def test_empty_delimiter_fatal_via_language(self):
        program = """use sys.io

act main() -> i32 {
    let parts: shelf[string] = str.split("a,b", "")
    io.println("unreachable")
    return 0
}
"""
        for stage in ("stage1", "stage2"):
            res = run_stage(stage, program, f"str51_ed_{stage}")
            self.assertNotEqual(res.returncode, 0, f"{stage} survived an empty delimiter")
            self.assertIn("str.split got an empty delimiter!", res.stderr)

    def test_runtime_null_and_delim_guards_fatal(self):
        gcc = find_gcc()
        tmp = ROOT / ".velo_cache" / "str51_fatals"
        tmp.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["PATH"] = f"{Path(gcc).parent.resolve()}{os.pathsep}{env.get('PATH', '')}"
        for call, want_msg, name in FATAL_CASES:
            c_file = tmp / f"{name}.c"
            exe = tmp / f"{name}.exe"
            c_file.write_text(MINI_TEMPLATE % call, encoding="utf-8")
            res = subprocess.run(
                [gcc, "-O2", "-std=c99", "-I", str(RUNTIME), str(c_file), "-o", str(exe)],
                capture_output=True, text=True, cwd=ROOT, env=env,
            )
            self.assertEqual(res.returncode, 0, f"{name} compile failed:\n{res.stderr[-1500:]}")
            run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=120)
            self.assertNotEqual(run.returncode, 0, f"{name} survived: {call}")
            self.assertIn(want_msg, run.stderr, f"{name} message mismatch:\n{run.stderr}")

    def test_shelf_contextual_and_unsafe_knob(self):
        """Slice 11: contextual `shelf` accepts (indentifiers/params named
        shelf; `shelf[` still parses as a literal — the pinned trade), the
        split result runs through the flag-gated --unsafe-shelf-index knob
        on both stages (OOB stays SILENT with the flag, loud without)."""
        ctx_program = """use sys.io

act f(shelf: i32) -> i32 {
    return shelf
}

act main() -> i32 {
    let shelf = 5
    io.println("var shelf: {shelf}")
    let pr = f(7)
    io.println("param shelf: {pr}")
    let lit = shelf[3]
    let n: usize = lit.len
    io.println("shelf[3] rides the literal path: {n}")
    let parts: shelf[string] = str.split("a,b,c", ",")
    let pn: usize = parts.len
    let w: string = parts[1]
    io.println("pinned token: {w} of {pn}")
    return 0
}
"""
        ctx_lines = [
            "var shelf: 5",
            "param shelf: 7",
            "shelf[3] rides the literal path: 1",
            "pinned token: b of 3",
        ]
        oob_program = """use sys.io

act main() -> i32 {
    let parts: shelf[string] = str.split("a,b,c", ",")
    let w: string = parts[7]
    io.println("oob token = [{w}]")
    return 0
}
"""
        for stage, name in (("stage1", "str51_ctx_s1"), ("stage2", "str51_ctx_s2")):
            res = run_stage(stage, ctx_program, name)
            self.assertEqual(res.returncode, 0, f"{stage} contextuality failed: {res.stderr[-2000:]}")
            self.assertEqual(
                res.stdout.strip().splitlines(), ctx_lines, f"{stage} contextuality output diverged"
            )
        # WITHOUT the flag the OOB read is a loud fatal on both stages
        for stage, name in (("stage1", "str51_oob_safe_s1"), ("stage2", "str51_oob_safe_s2")):
            res = run_stage(stage, oob_program, name)
            self.assertNotEqual(res.returncode, 0, f"{stage} survived an OOB shelf read")
            self.assertIn("shelf index out of bounds: 7 (len 3)!", res.stderr)
        # WITH the flag the read lowers unguarded: silent, exit 0, no fatal
        flag_programs = {
            "stage1": [sys.executable, str(VELO_PY), "run", "--unsafe-shelf-index", "{src}"],
            "stage2": [str(VELO_EXE), "run", "{src}", "--unsafe-shelf-index"],
        }
        for stage, cmd in flag_programs.items():
            tmp = ROOT / ".velo_cache" / f"str51_oob_unsafe_{stage}.vl"
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(oob_program, encoding="utf-8")
            cmd = [c.replace("{src}", str(tmp)) for c in cmd]
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=300)
            self.assertEqual(res.returncode, 0, f"{stage} unsafe knob crashed:\n{res.stderr[-1500:]}")
            self.assertNotIn("shelf index out of bounds", res.stderr)

    def test_zone_string_allocation_and_zero_heap_leak(self):
        """Task 8.1: 10,000 str.concat operations inside a zone { } block
        allocate out of the active zone arena (velo_mem_alloc), leaving
        mem.heap_used() at 0 before and after zone exit."""
        prog = """use sys.io
use sys.mem

act main() -> i32 {
    let base: usize = mem.heap_used()
    zone {
        mut i: i32 = 0
        loop i < 10000 {
            let s1 = str.concat("item_", "test")
            let s2 = str.to_upper(s1)
            let s3 = str.to_lower(s2)
            let s4 = str.replace(s3, "item", "val")
            let s5 = str.trim("  done  ")
            i += 1
        }
        let inside: usize = mem.heap_used()
        if inside == base {
            io.println("inside zone: 0 heap leak")
        }
    }
    let after: usize = mem.heap_used()
    if after == base {
        io.println("after zone: 0 heap leak")
    }
    return 0
}
"""
        expected = [
            "inside zone: 0 heap leak",
            "after zone: 0 heap leak",
        ]
        for stage, name in (("stage1", "str81_zone_s1"), ("stage2", "str81_zone_s2")):
            res = run_stage(stage, prog, name)
            self.assertEqual(res.returncode, 0, f"{stage} failed: {res.stderr[-2000:]}")
            self.assertEqual(res.stdout.strip().splitlines(), expected, f"{stage} output mismatch")

    def test_heap_string_allocation_and_free(self):
        """Task 8.1: str.heap_* allocates on persistent heap and survives zone exit."""
        prog = """use sys.io
use sys.mem

act main() -> i32 {
    let base: usize = mem.heap_used()
    mut h_str: string = ""
    zone {
        h_str = str.heap_concat("hello, ", "world!")
        let u: string = str.heap_to_upper(h_str)
        let l: string = str.heap_to_lower(u)
        let r: string = str.heap_replace(l, "world", "velo")
        let t: string = str.heap_trim("  trimmed  ")
        io.println("heap string: {h_str}")
        io.println("heap upper: {u}")
        io.println("heap lower: {l}")
        io.println("heap replace: {r}")
        io.println("heap trim: [{t}]")
        mem.free(u)
        mem.free(l)
        mem.free(r)
        mem.free(t)
    }
    io.println("survived zone: {h_str}")
    let held: usize = mem.heap_used()
    if held > base {
        io.println("heap allocated active")
    }
    mem.free(h_str)
    let end: usize = mem.heap_used()
    if end == base {
        io.println("clean teardown")
    }
    return 0
}
"""
        expected = [
            "heap string: hello, world!",
            "heap upper: HELLO, WORLD!",
            "heap lower: hello, world!",
            "heap replace: hello, velo!",
            "heap trim: [trimmed]",
            "survived zone: hello, world!",
            "heap allocated active",
            "clean teardown",
        ]
        for stage, name in (("stage1", "str81_heap_s1"), ("stage2", "str81_heap_s2")):
            res = run_stage(stage, prog, name)
            self.assertEqual(res.returncode, 0, f"{stage} failed: {res.stderr[-2000:]}")
            self.assertEqual(res.stdout.strip().splitlines(), expected, f"{stage} output mismatch")

    def test_in_memory_string_interpolation_and_zero_heap_leak(self):
        """Task 8.2: String interpolation in general expressions (returns, let-bindings,
        args) lowers to arena-backed velo_str_format and leaves mem.heap_used() at 0."""
        prog = """use sys.io
use sys.mem

act greet(name: string, score: i32) -> string {
    let msg: string = "Hello {name}, score={score + 10}!"
    return msg
}

act pass_through(s: string) -> string {
    return s
}

act main() -> i32 {
    let base: usize = mem.heap_used()
    zone {
        let name: string = "Alice"
        let score: i32 = 42
        let msg1: string = "Hello {name}, score={score + 10}!"
        io.println(msg1)
        let msg2: string = greet("Bob", 85)
        io.println(msg2)
        let msg3: string = pass_through("Count: {score * 2}")
        io.println(msg3)
        mut i: i32 = 0
        loop i < 1000 {
            let temp: string = "Loop {i}: {name}"
            i += 1
        }
        let inside: usize = mem.heap_used()
        if inside == base {
            io.println("inside zone: 0 heap leak")
        }
    }
    let after: usize = mem.heap_used()
    if after == base {
        io.println("after zone: 0 heap leak")
    }
    return 0
}
"""
        expected = [
            "Hello Alice, score=52!",
            "Hello Bob, score=95!",
            "Count: 84",
            "inside zone: 0 heap leak",
            "after zone: 0 heap leak",
        ]
        for stage, name in (("stage1", "str82_interp_s1"), ("stage2", "str82_interp_s2")):
            res = run_stage(stage, prog, name)
            self.assertEqual(res.returncode, 0, f"{stage} failed: {res.stderr[-2000:]}")
            self.assertEqual(res.stdout.strip().splitlines(), expected, f"{stage} output mismatch")

    def test_str_format_and_heap_format(self):
        """Task 8.2: str.format and str.heap_format formatted string emission."""
        prog = """use sys.io
use sys.mem

act main() -> i32 {
    let base: usize = mem.heap_used()
    mut h_msg: string = ""
    zone {
        let s_fmt: string = str.format("Value: %d, Float: %.2f, Name: %s", 123, 3.14159, "velo")
        io.println(s_fmt)
        h_msg = str.heap_format("Heap: %s = %d", "counter", 999)
        io.println(h_msg)
        let inside: usize = mem.heap_used()
        if inside > base {
            io.println("heap string allocated")
        }
    }
    io.println("survived zone: {h_msg}")
    let held: usize = mem.heap_used()
    if held > base {
        io.println("heap string still alive")
    }
    mem.free(h_msg)
    let end: usize = mem.heap_used()
    if end == base {
        io.println("clean teardown")
    }
    return 0
}
"""
        expected = [
            "Value: 123, Float: 3.14, Name: velo",
            "Heap: counter = 999",
            "heap string allocated",
            "survived zone: Heap: counter = 999",
            "heap string still alive",
            "clean teardown",
        ]
        for stage, name in (("stage1", "str82_fmt_s1"), ("stage2", "str82_fmt_s2")):
            res = run_stage(stage, prog, name)
            self.assertEqual(res.returncode, 0, f"{stage} failed: {res.stderr[-2000:]}")
            self.assertEqual(res.stdout.strip().splitlines(), expected, f"{stage} output mismatch")


if __name__ == "__main__":
    unittest.main()
