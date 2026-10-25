"""Task 1.3 — Single-Evaluation Null Comparisons for Function Calls.

Verifies that function calls in null comparisons (`expr != null`, `null != expr`,
`expr == null`, `null == expr`) and string equality comparisons evaluate
arguments exactly once without duplicated side effects across Stage 1
(velo/codegen_c.py) and Stage 2 (src/backend/codegen_expr.vl).
"""
import unittest

from test_allocators import run_stage

NULL_CMP_PROGRAM = """use sys.io

mut counter: i32 = 0

act get_str(tag: string) -> string {
    counter += 1
    return tag
}

act get_null_str() -> string {
    counter += 1
    return null
}

data Node {
    val: i32
}

act get_node() -> @Node {
    counter += 1
    return null
}

act main() -> i32 {
    // 1. String != null (should increment counter once)
    if get_str("alpha") != null {
        io.println("alpha not null")
    }
    io.println("Count 1: {counter}")

    // 2. null != String (should increment counter once)
    if null != get_str("beta") {
        io.println("beta not null")
    }
    io.println("Count 2: {counter}")

    // 3. String == null (should increment counter once)
    if get_null_str() == null {
        io.println("null str is null")
    }
    io.println("Count 3: {counter}")

    // 4. Pointer == null (should increment counter once)
    if get_node() == null {
        io.println("node is null")
    }
    io.println("Count 4: {counter}")

    // 5. String == string call (should increment counter once)
    if get_str("gamma") == "gamma" {
        io.println("gamma matched")
    }
    io.println("Count 5: {counter}")

    // 6. String != string call (should increment counter once)
    if get_str("delta") != "epsilon" {
        io.println("delta not epsilon")
    }
    io.println("Count 6: {counter}")

    return 0
}
"""

EXPECTED_LINES = [
    "alpha not null",
    "Count 1: 1",
    "beta not null",
    "Count 2: 2",
    "null str is null",
    "Count 3: 3",
    "node is null",
    "Count 4: 4",
    "gamma matched",
    "Count 5: 5",
    "delta not epsilon",
    "Count 6: 6",
]


class TestNullComparisons(unittest.TestCase):
    """Parity tests for single-evaluation null and string comparisons."""

    def test_single_eval_parity_and_output(self):
        s1 = run_stage("stage1", NULL_CMP_PROGRAM, "null_cmp_s1")
        s2 = run_stage("stage2", NULL_CMP_PROGRAM, "null_cmp_s2")
        for label, res in (("stage1", s1), ("stage2", s2)):
            self.assertEqual(res.returncode, 0, f"{label} run failed: {res.stderr[-2000:]}")
        self.assertEqual(s1.stdout, s2.stdout, "null comparison outputs diverged between stages")
        self.assertEqual(
            s1.stdout.strip().splitlines(),
            EXPECTED_LINES,
            "null comparison outputs do not match expected single-eval counts",
        )
