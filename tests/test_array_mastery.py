"""5.2 Array Mastery — example 32: the full advanced-collection toolkit.

One example crossing every shipped 5.2 family in a single deterministic
program: indexed writes / insert / remove_at / sorted() / reversed() /
join over a typed shelf, the widening ladder through shelf[dyn] tags with
`as` unboxing, the slice-11 str.split -> shelf[string] text pipeline,
Map has/get/upsert-put with hash-order key iteration, ring FIFO across
the wrap boundary, bitset masks set/has/clear/toggle/count/first_unset,
shared @shelf[i32] rows writing through to their source shelves, and heap
shelves that outlive both zones and acts while the heap ledger accounts
them. Every interpolation binds locals first (gaps 6.7 — no calls or
indices inside {..}).

Parity contract: the Stage 1 Python compiler and the self-hosted Stage 2
compiler must produce BYTE-IDENTICAL output for this program.
"""
import unittest
from pathlib import Path

from test_allocators import run_stage, ROOT

EXAMPLE32 = ROOT / "examples" / "32_array_mastery.vl"

EXAMPLE32_LINES = [
    "gone: 7 hi: 11 sum: 24 len: 5",
    "asc: 2 / 2 / 4 / 5 / 11",
    "desc: 5 / 2 / 2 / 4 / 11",
    "bag: 2.50 15 sx len: 4",
    "part 0 = 'kilo'",
    "part 1 = 'victor'",
    "part 2 = 'alpha'",
    "part 3 = 'echo'",
    "split count: 4 sorted: alpha | echo | kilo | victor",
    "stock: bow 1 cup 9 dye 4 size 4",
    "bow present",
    "inv 0: dye x 4",
    "inv 1: bow x 1",
    "inv 2: axe x 3",
    "inv 3: cup x 9",
    "front: 0 head pops: 0 1 left: 3",
    "ring 0 holds 2",
    "ring 1 holds 3",
    "ring 2 holds 4",
    "mask bits: 3",
    "bit 3 armed",
    "bit 3 disarmed",
    "first open slot: 1",
    "bit 1 toggled off",
    "write-through: 70 len 3 row: 1,70,9",
    "stock len 6 second 200 zone-grown 3 last 2",
    "heap ledger: 48",
]


class TestArrayMastery(unittest.TestCase):
    """gaps.md 5.2 collections — the advanced-manipulation example parity."""

    def test_example32_parity_and_output(self):
        src = EXAMPLE32.read_text(encoding="utf-8")
        s1 = run_stage("stage1", src, "example32")
        s2 = run_stage("stage2", src, "example32")
        self.assertEqual(s1.returncode, 0, s1.stderr[-3000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-3000:])
        self.assertEqual(s1.stdout, s2.stdout, "example 32 outputs diverged")
        self.assertEqual(s1.stdout.strip().splitlines(), EXAMPLE32_LINES)


if __name__ == "__main__":
    unittest.main()
