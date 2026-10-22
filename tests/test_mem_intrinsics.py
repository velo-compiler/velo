import subprocess
import sys
import unittest

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
            ("stage1", [sys.executable, str(VELO_PY), "build", str(src)]),
            ("stage2", [str(VELO_EXE), "build", str(src)]),
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


if __name__ == "__main__":
    unittest.main()
