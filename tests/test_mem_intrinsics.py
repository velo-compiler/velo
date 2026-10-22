import os
import subprocess
import sys
import unittest
from pathlib import Path

from test_allocators import assert_parity, run_stage, ROOT, VELO_PY, VELO_EXE

# §4.3 byte primitives + realloc: set, copy, move (overlapping via pointer
# arithmetic), realloc grow/shrink/null/zero-count, and the heap-ledger
# algebra across all of it. Every case must run identically on both stages.
MEM43 = """use sys.io
use sys.mem

act main() -> i32 {
    let src: @u8 = mem.alloc(@u8, 8)
    mem.set(src, 65, 8)
    let dst: @u8 = mem.alloc(@u8, 8)
    mem.copy(dst, src, 8)
    io.println("copy = {dst[0]} {dst[4]}")

    let shifted: @u8 = src + 1
    mem.move(shifted, src, 7)
    io.println("move = {src[0]} {src[2]} {src[4]}")

    let p: @i64 = mem.heap_alloc(@i64, 4)
    p[0] = 11
    p[1] = 22
    let q: @i64 = mem.realloc(p, @i64, 8)
    q[2] = 33
    q[3] = 44
    let h1: usize = mem.heap_used()
    io.println("grow = {q[0]} {q[1]} {q[2]} {q[3]} bytes={h1}")

    let r: @i64 = mem.realloc(q, @i64, 2)
    let h2: usize = mem.heap_used()
    io.println("shrink = {r[0]} {r[1]} bytes={h2}")

    let t: @i64 = mem.realloc(null, @i64, 3)
    t[0] = 7
    io.println("fresh = {t[0]}")

    let z: @i64 = mem.realloc(t, @i64, 0)
    if z == null { io.println("zero-freed = null") }
    mem.free(r)
    let h3: usize = mem.heap_used()
    io.println("end = {h3}")
    return 0
}
"""

# Byte-count semantics are explicit: copy counts BYTES, not elements —
# 8 bytes of an @i64 buffer is exactly one element; the rest stays zeroed.
BYTE_COPY = """use sys.io
use sys.mem

act main() -> i32 {
    let src: @i64 = mem.heap_alloc(@i64, 4)
    src[0] = 99
    src[1] = 11
    let dst: @i64 = mem.heap_alloc(@i64, 4)
    mem.set(dst, 0, 32)
    mem.copy(dst, src, 8)
    io.println("b = {dst[0]} {dst[1]}")
    mem.free(src)
    mem.free(dst)
    let h: usize = mem.heap_used()
    io.println("end = {h}")
    return 0
}
"""

# memmove-vs-memcpy proof: distinct payload under a true element-shifting
# overlap preserves the ORIGINAL values (as-if temp buffer); a wrong
# cascading memcpy would fabricate an all-10s run. count is bytes: a
# 7-element shift of @i64 is 56 bytes.
MEMMOVE_DISTINCT = """use sys.io
use sys.mem

act main() -> i32 {
    let src: @i64 = mem.alloc(@i64, 8)
    src[0] = 10
    src[1] = 11
    src[2] = 12
    src[3] = 13
    src[4] = 14
    src[5] = 15
    src[6] = 16
    src[7] = 17
    let off: @i64 = src + 1
    mem.move(off, src, 56)
    io.println("m = {src[0]} {src[1]} {src[2]} {src[3]}")
    io.println("n = {src[4]} {src[5]} {src[6]} {src[7]}")
    return 0
}
"""

BAD_COPY_INT = """use sys.io
use sys.mem
act main() -> i32 {
    let d: @u8 = mem.alloc(@u8, 8)
    mem.set(d, 65, 8)
    let s: @u8 = mem.alloc(@u8, 8)
    mem.copy(42, s, 4)
    return 0
}
"""

BAD_COPY_PTRCOUNT = """use sys.io
use sys.mem
act main() -> i32 {
    let d: @u8 = mem.alloc(@u8, 8)
    let s: @u8 = mem.alloc(@u8, 8)
    mem.copy(d, s, s)
    return 0
}
"""

BAD_SET_PTRVAL = """use sys.io
use sys.mem
act main() -> i32 {
    let d: @u8 = mem.alloc(@u8, 8)
    let s: @u8 = mem.alloc(@u8, 8)
    mem.set(d, s, 4)
    return 0
}
"""

BAD_SET_ARITY = """use sys.io
use sys.mem
act main() -> i32 {
    let d: @u8 = mem.alloc(@u8, 8)
    mem.set(d, 65)
    return 0
}
"""

BAD_REALLOC_TYPE = """use sys.io
use sys.mem
act main() -> i32 {
    let p: @i64 = mem.heap_alloc(@i64, 4)
    mem.realloc(p, i64, 8)
    return 0
}
"""

BAD_REALLOC_ARITY = """use sys.io
use sys.mem
act main() -> i32 {
    let p: @i64 = mem.heap_alloc(@i64, 4)
    let d: @u8 = mem.alloc(@u8, 8)
    mem.realloc(p, @i64, 8, d)
    return 0
}
"""

# A negative literal count is a caller bug the checker rejects statically
# when knowable; variable-held negatives die at runtime via the
# velo_byte_* wrappers instead of wrapping into gigantic size_t wipes.
BAD_COPY_NEG_LIT = """use sys.io
use sys.mem
act main() -> i32 {
    let d: @u8 = mem.alloc(@u8, 8)
    let s: @u8 = mem.alloc(@u8, 8)
    mem.copy(d, s, -1)
    return 0
}
"""

BAD_SET_NEG_LIT = """use sys.io
use sys.mem
act main() -> i32 {
    let d: @u8 = mem.alloc(@u8, 8)
    mem.set(d, 65, -1)
    return 0
}
"""

# Variable-held negatives: i32 -1 becomes (long long)(-1) at the runtime
# wrapper, which fatals instead of memset()ing SIZE_MAX bytes.
NEG_VAR_RUNTIME = """use sys.io
use sys.mem
act main() -> i32 {
    let d: @u8 = mem.alloc(@u8, 8)
    let n: i32 = -1
    mem.set(d, 65, n)
    io.println("unreachable")
    return 0
}
"""

# Four worker threads, ~120 reallocs each (grow to 120, shrink to 1),
# private blocks, shared atomic ledger — the final ledger must be exactly
# 0 regardless of interleaving: every op's delta is fixed, the atomics
# only change the ORDER. Exercises mem.realloc under real contention,
# which the single-threaded cases cannot.
THREAD_REALLOC = """use sys.io
use sys.mem
use sys.thread

act worker() -> i32 {
    mut p: @i64 = mem.heap_alloc(@i64, 2)
    mut k: i32 = 0
    loop k < 120 {
        mut n: i32 = k + 1
        if k > 60 { n = 120 - k }
        p = mem.realloc(p, @i64, n)
        k = k + 1
    }
    mem.free(p)
    return 0
}

act main() -> i32 {
    mut h1: @Thread = thread.spawn(worker)
    mut h2: @Thread = thread.spawn(worker)
    mut h3: @Thread = thread.spawn(worker)
    mut h4: @Thread = thread.spawn(worker)
    let r1: i32 = thread.join(h1)
    let r2: i32 = thread.join(h2)
    let r3: i32 = thread.join(h3)
    let r4: i32 = thread.join(h4)
    let h: usize = mem.heap_used()
    io.println("ledger = {h}")
    return 0
}
"""

# OOM: 8 * 2^58 = 2^61 bytes is beyond every sane VA space, so the
# underlying realloc/malloc deterministically fails and velo_heap_realloc
# must die with Velo's fatal (not return a lying non-null, not crash).
OOM_HARNESS = """#include "velo_runtime.h"
#include <stdio.h>
int main(void) {
    void* p = velo_heap_realloc(NULL, 8, 1LL << 58); /* 2^61 bytes > VA space */
    printf("NOT REACHED %p\\n", p);
    return 0;
}
"""


class TestMemIntrinsics(unittest.TestCase):
    """gaps.md 4.3 Low-Level Memory Intrinsics — mem.set/copy/move over the
    C memcpy trio and mem.realloc that preserves the heap size-header +
    shared atomic ledger. Invalid arguments are compile-time errors on BOTH
    stages with identical wording (same contract style as the thread
    surface, gaps 4.2)."""

    def _build_rejected(self, program: str, name: str, want_msg: str):
        """Both compilers must REJECT this program at build time with the
        same message substring."""
        tmp = ROOT / ".velo_cache" / f"mem_reject_{name}"
        tmp.mkdir(parents=True, exist_ok=True)
        src = tmp / f"{name}.vl"
        src.write_text(program, encoding="utf-8")
        for stage, cmd in (
            ("stage1", [sys.executable, str(VELO_PY), "build", str(src), "-o", str(src.with_suffix(".exe"))]),
            ("stage2", [str(VELO_EXE), "build", str(src), "-o", str(src.with_suffix(".exe"))]),
        ):
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
            assert res.returncode != 0, (
                f"{stage} accepted an invalid program ({name}):\n{res.stdout}")
            assert want_msg in (res.stdout + res.stderr), (
                f"{stage} rejected {name} but without expected message "
                f"{want_msg!r}:\n{res.stdout}\n{res.stderr}")

    def test_rejects_bad_mem_intrinsics(self):
        self._build_rejected(BAD_COPY_INT, "bad_copy_int",
                             "mem.copy expects pointer arguments (got i32)")
        self._build_rejected(BAD_COPY_PTRCOUNT, "bad_copy_ptrcount",
                             "mem.copy expects an integer byte count (got @u8)")
        self._build_rejected(BAD_SET_PTRVAL, "bad_set_ptrval",
                             "mem.set expects an integer fill value (got @u8)")
        self._build_rejected(BAD_SET_ARITY, "bad_set_arity",
                             "mem.set expects exactly 3 arguments: (pointer dest, byte value, byte count)")
        self._build_rejected(BAD_REALLOC_TYPE, "bad_realloc_type",
                             "mem.realloc expects a @Type argument (got i64)")
        self._build_rejected(BAD_REALLOC_ARITY, "bad_realloc_arity",
                             "mem.realloc expects exactly 3 arguments: (pointer, @Type, count)")
        self._build_rejected(BAD_COPY_NEG_LIT, "bad_copy_neg_lit",
                             "mem.copy expects a non-negative byte count")
        self._build_rejected(BAD_SET_NEG_LIT, "bad_set_neg_lit",
                             "mem.set expects a non-negative byte count")

    def test_runtime_negatives_not_statically_knowable(self):
        """A variable-held negative count slips past the compile-time
        check (it IS countable); the runtime wrapper must fatal loudly on
        BOTH stages rather than laundering -1 into a gigantic size_t."""
        tmp = ROOT / ".velo_cache" / "mem_neg_var"
        tmp.mkdir(parents=True, exist_ok=True)
        src = tmp / "neg_var.vl"
        src.write_text(NEG_VAR_RUNTIME, encoding="utf-8")
        want_msg = "negative byte count"
        for stage, cmd in (
            ("stage1", [sys.executable, str(VELO_PY), "build", str(src), "-o", str(src.with_suffix(".exe"))]),
            ("stage2", [str(VELO_EXE), "build", str(src), "-o", str(src.with_suffix(".exe"))]),
        ):
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
            assert res.returncode == 0, (
                f"{stage} rejected a valid program:\n{res.stdout}{res.stderr}")
            exe = src.with_suffix(".exe")
            run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=120)
            assert run.returncode != 0, (
                f"{stage} survived a negative count: {run.stdout}")
            assert want_msg in (run.stdout + run.stderr), (
                f"{stage} died without the fatal message:\n{run.stdout}\n{run.stderr}")

    def test_concurrent_realloc_ledger(self):
        """4 threads × ~120 reallocs (grow 1→120 → shrink), private blocks,
        shared atomic ledger. Every op's delta is fixed, so the final
        ledger must be exactly 0 no matter the interleaving."""
        assert_parity(
            THREAD_REALLOC,
            "mem43_threads",
            expected_lines=["ledger = 0"],
        )

    def test_oom_is_deterministic_fatal(self):
        """velo_heap_realloc(NULL, 8, 2^58) — 2^61 bytes, beyond any VA
        space — must reach OUR fatal ('Out of Heap Memory'), not return a
        lying handle nor crash before logging. C mini-harness, same
        pattern as the runtime lifecycle checks."""
        from test_thread_local_runtime import find_gcc, RUNTIME
        tmp = ROOT / ".velo_cache" / "mem_oom"
        tmp.mkdir(parents=True, exist_ok=True)
        c_file = tmp / "oom_harness.c"
        exe = tmp / "oom_harness.exe"
        c_file.write_text(OOM_HARNESS, encoding="utf-8")
        gcc = find_gcc()
        env = os.environ.copy()
        env["PATH"] = f"{Path(gcc).parent.resolve()}{os.pathsep}{env.get('PATH', '')}"
        res = subprocess.run(
            [gcc, "-O2", "-std=c99", "-I", str(RUNTIME), str(c_file), "-o", str(exe)],
            capture_output=True, text=True, cwd=ROOT, env=env)
        assert res.returncode == 0, f"harness compile failed:\n{res.stderr}"
        run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=120)
        assert run.returncode != 0, f"OOM survived silently: {run.stdout}"
        assert "Velo Fatal Error: Out of Heap Memory!" in (run.stdout + run.stderr), (
            f"wrong fatal:\n{run.stdout}\n{run.stderr}")

    def test_byte_primitives_and_realloc(self):
        assert_parity(
            MEM43,
            "mem43",
            expected_lines=[
                "copy = 65 65",
                "move = 65 65 65",
                "grow = 11 22 33 44 bytes=64",
                "shrink = 11 22 bytes=16",
                "fresh = 7",
                "zero-freed = null",
                "end = 0",
            ],
        )

    def test_copy_counts_bytes_not_elements(self):
        assert_parity(
            BYTE_COPY,
            "mem43_bytes",
            expected_lines=["b = 99 0", "end = 0"],
        )

    def test_move_overlap_preserves_originals(self):
        # memmove semantics under a real 7-element overlapping shift with
        # distinct payload - the committed MEM43 overlap case uses equal
        # bytes and could not distinguish memmove from a cascading memcpy.
        assert_parity(
            MEMMOVE_DISTINCT,
            "mem43_memoved",
            expected_lines=["m = 10 10 11 12", "n = 13 14 15 16"],
        )


if __name__ == "__main__":
    unittest.main()
