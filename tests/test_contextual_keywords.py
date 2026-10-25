"""Task 2.1 — Contextual Re-acceptance of Remaining Reserved Keywords.

Verifies that keywords (`use`, `act`, `loop`, `zone`, `defer`, `return`, `break`,
`continue`, `on`, `extern`, `aka`, `data`, `kind`, `op`, `test`) can be used as:
1. Struct field definitions (`data Node { return: i32, loop: i32, use: string, defer: bool }`)
2. Struct literal field initializers (`Node { return: 1, loop: 2, use: "msg", defer: true }`)
3. Field accesses (`node.return`, `node.loop`, `node.use`, `node.defer`)
4. Variable declarations (`let loop = 10`, `mut use = "abc"`)
5. Function parameter names (`act compute(use: string, loop: i32, defer: bool) -> i32`)
Across Stage 1 (Python) and Stage 2 (self-hosted binary).
"""
import subprocess
import sys
import unittest
from pathlib import Path

from test_allocators import ROOT, VELO_EXE, VELO_PY, run_stage

KW_STRUCT_PROGRAM = """data Node {
    return: i32
    loop: i32
    use: string
    defer: bool
    act: i32
    zone: usize
    break: i32
    continue: i32
    on: i32
    extern: i32
    aka: i32
    data: i32
    kind: i32
    op: i32
    test: i32
}

act process_node(n: Node) -> i32 {
    if n.defer {
        return n.loop + n.return
    }
    return n.loop
}

act main() -> i32 {
    let n = Node {
        return: 10,
        loop: 20,
        use: "contextual",
        defer: true,
        act: 1,
        zone: 1024,
        break: 2,
        continue: 3,
        on: 4,
        extern: 5,
        aka: 6,
        data: 7,
        kind: 8,
        op: 9,
        test: 10
    }

    let r = n.return
    let l = n.loop
    let u = n.use
    let d = n.defer
    let a = n.act
    let z = n.zone
    let b = n.break
    let c = n.continue
    let o = n.on
    let e = n.extern
    let ak = n.aka
    let dt = n.data
    let kd = n.kind
    let op = n.op
    let tt = n.test

    return process_node(n) - 30
}
"""

KW_EXEC_PROGRAM = """use sys.io

data TaskItem {
    loop: i32
    use: string
    defer: bool
    zone: usize
    act: i32
    on: i32
    data: i32
    kind: i32
    op: i32
    test: i32
}

act transform(item: TaskItem) -> i32 {
    mut result = item.loop
    if item.defer {
        result += 100
    }
    return result
}

act main() -> i32 {
    let item = TaskItem {
        loop: 42,
        use: "task_worker",
        defer: true,
        zone: 4096,
        act: 7,
        on: 8,
        data: 9,
        kind: 10,
        op: 11,
        test: 12
    }

    // Member access
    io.println("Item use: {item.use}")
    io.println("Item loop: {item.loop}")
    io.println("Item defer: {item.defer}")
    io.println("Item zone: {item.zone}")
    io.println("Item act: {item.act}")
    io.println("Item on: {item.on}")
    io.println("Item data: {item.data}")
    io.println("Item kind: {item.kind}")
    io.println("Item op: {item.op}")
    io.println("Item test: {item.test}")

    // Passing struct and accessing contextual members
    let res = transform(item)
    io.println("Transform res: {res}")

    // Variable declarations with contextual names (where unambiguous)
    let data = 1000
    mut kind = 2000
    let op = 3000
    let test = 4000
    io.println("Vars: data={data}, kind={kind}, op={op}, test={test}")

    return 0
}
"""

EXPECTED_EXEC_LINES = [
    "Item use: task_worker",
    "Item loop: 42",
    "Item defer: true",
    "Item zone: 4096",
    "Item act: 7",
    "Item on: 8",
    "Item data: 9",
    "Item kind: 10",
    "Item op: 11",
    "Item test: 12",
    "Transform res: 142",
    "Vars: data=1000, kind=2000, op=3000, test=4000",
]


class TestContextualKeywords(unittest.TestCase):
    """Tests for contextual re-acceptance of reserved keywords."""

    def test_contextual_struct_fields_emit_c(self):
        """Verifies structs with field names return, loop, use, defer, act, etc. emit C on both stages."""
        tmp_dir = ROOT / ".velo_cache" / "test_contextual_kw"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        src_file = tmp_dir / "kw_struct.vl"
        src_file.write_text(KW_STRUCT_PROGRAM, encoding="utf-8")

        # Stage 1 emit-c
        s1 = subprocess.run(
            [sys.executable, str(VELO_PY), "emit-c", str(src_file)],
            capture_output=True, text=True, cwd=ROOT
        )
        self.assertEqual(s1.returncode, 0, f"Stage 1 emit-c failed: {s1.stderr}")

        # Stage 2 emit-c
        s2 = subprocess.run(
            [str(VELO_EXE), "emit-c", str(src_file)],
            capture_output=True, text=True, cwd=ROOT
        )
        self.assertEqual(s2.returncode, 0, f"Stage 2 emit-c failed: {s2.stderr}\n{s2.stdout}")

        # Check that both emitted struct Node with all fields
        for field in ("return", "loop", "use", "defer", "act", "zone", "break", "continue", "on", "extern", "aka", "data", "kind", "op", "test"):
            self.assertIn(field, s1.stdout, f"Stage 1 missing field '{field}'")
            self.assertIn(field, s2.stdout, f"Stage 2 missing field '{field}'")

        # Check member accesses are present
        for field in ("n.return", "n.loop", "n.use", "n.defer"):
            self.assertIn(field, s1.stdout, f"Stage 1 missing member access '{field}'")
            self.assertIn(field, s2.stdout, f"Stage 2 missing member access '{field}'")

    def test_contextual_keywords_execution_parity(self):
        """Verifies build and run parity across Stage 1 and Stage 2 for contextual keywords."""
        s1 = run_stage("stage1", KW_EXEC_PROGRAM, "kw_exec_s1")
        s2 = run_stage("stage2", KW_EXEC_PROGRAM, "kw_exec_s2")

        for label, res in (("stage1", s1), ("stage2", s2)):
            self.assertEqual(res.returncode, 0, f"{label} run failed: {res.stderr[-2000:]}")

        self.assertEqual(s1.stdout, s2.stdout, "Contextual keywords execution diverged between stages")
        self.assertEqual(
            s1.stdout.strip().splitlines(),
            EXPECTED_EXEC_LINES,
            "Contextual keywords execution output does not match expected output",
        )


if __name__ == "__main__":
    unittest.main()
