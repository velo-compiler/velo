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
# \x0b \x0c are VT/FF — Velo has no \v \f escapes.
EDGE = """use sys.io

act count_tokens(parts: @string) -> usize {
    mut n: usize = 0
    loop parts[n] != null { n += 1 }
    return n
}

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

    let s0: @string = str.split("no-delim", ",")
    let s0n: usize = count_tokens(s0)
    let s0t: string = s0[0]
    io.println("split(1-token) = {s0n} [{s0t}]")
    let s1: @string = str.split(e, ",")
    let s1n: usize = count_tokens(s1)
    let s1t: string = s1[0]
    io.println("split('') = {s1n} [{s1t}]")
    let s2: @string = str.split("x", "xy")
    let s2n: usize = count_tokens(s2)
    io.println("split(long-delim) = {s2n}")
    mem.free(s0)
    mem.free(s1)
    mem.free(s2)
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

# Single-block split ownership: one heap block holds the pointer array AND
# every token byte, so mem.free(parts) reclaims everything. held = 48 array
# bytes (6 pointers: 5 tokens + NULL terminator) + 20 token bytes
# ("one\0 two\0 three\0 \0 five\0") — 68 exactly, on every run of both stages.
# After the single free the ledger is back to exactly the starting value:
# the token leak is closed. DO NOT mem.free an individual token (interior
# pointer, no size header — the same non-header-pointer class as
# mem.free on any other bad pointer).
SPLIT_OWNERSHIP = """use sys.io
use sys.mem

act main() -> i32 {
    let base: usize = mem.heap_used()
    let parts: @string = str.split("one,two,three,,five", ",")
    let tok0: string = parts[0]
    let tok3: string = parts[3]
    let l0: usize = str.len(tok0)
    let l3: usize = str.len(tok3)
    let held: usize = mem.heap_used()
    io.println("lens = {l0} {l3}")
    io.println("held = {held}")
    mem.free(parts)
    let after: usize = mem.heap_used()
    io.println("after = {after}")
    if after == base { io.println("ledger balanced") }
    return 0
}
"""

SPLIT_OWNERSHIP_LINES = [
    "lens = 3 0",
    "held = 68",
    "after = 0",
    "ledger balanced",
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
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        text = res.stdout + res.stderr
        assert res.returncode != 0, f"{stage} accepted:\n{text[-2000:]}"
        assert want_msg in text, f"{stage} message mismatch:\n{text[-2000:]}"


def find_gcc() -> str:
    found = shutil.which("gcc")
    if found:
        return found
    for candidate in (r"C:\msys64\ucrt64\bin\gcc.exe", r"C:\msys64\mingw64\bin\gcc.exe"):
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

    def test_split_single_block_ownership(self):
        """One heap block owns the pointer array AND every token: a single
        mem.free(parts) returns the heap ledger to exactly its starting value."""
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
use sys.mem

act main() -> i32 {
    let parts: @string = str.split("a,b", "")
    io.println("unreachable")
    mem.free(parts)
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


if __name__ == "__main__":
    unittest.main()
