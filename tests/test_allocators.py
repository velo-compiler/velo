import unittest
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
VELO_PY = ROOT / "velo.py"
VELO_EXE = ROOT / "bin" / "velo.exe"


def run_stage(stage: str, program: str, name: str) -> subprocess.CompletedProcess:
    """Compile+run `program` on the given stage ('stage1' | 'stage2') and return
    the finished process (stdout/stderr captured)."""
    tmp = Path(__file__).parent.parent / ".velo_cache" / f"alloc_test_{name}"
    tmp.mkdir(parents=True, exist_ok=True)
    src = tmp / f"{name}.vl"
    src.write_text(program, encoding="utf-8")
    if stage == "stage1":
        exe = tmp / f"{name}_s1.exe"
        res = subprocess.run(
            [sys.executable, str(VELO_PY), "build", str(src), "-o", str(exe)],
            capture_output=True, text=True, cwd=ROOT,
        )
        if res.returncode != 0:
            raise AssertionError(f"stage1 build failed: {res.stderr[-2000:]}")
    else:
        exe = tmp / f"{name}_s2.exe"
        res = subprocess.run(
            [str(VELO_EXE), "build", str(src), "-o", str(exe)],
            capture_output=True, text=True, cwd=ROOT,
        )
        if res.returncode != 0:
            raise AssertionError(f"stage2 build failed: {res.stdout[-2000:]}")
    return subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)


def assert_parity(program: str, name: str, expected_lines=None):
    """Both compilers must produce byte-identical stdout (and pass)."""
    s1 = run_stage("stage1", program, name)
    s2 = run_stage("stage2", program, name)
    for label, res in (("stage1", s1), ("stage2", s2)):
        assert res.returncode == 0, f"{label} run failed: {res.stderr[-2000:]}"
    assert s1.stdout == s2.stdout, (
        f"stage1 vs stage2 output diverged:\n--- stage1 ---\n{s1.stdout}\n--- stage2 ---\n{s2.stdout}")
    if expected_lines:
        actual = s1.stdout.strip().splitlines()
        assert actual == expected_lines, f"expected {expected_lines}, got {actual}"
    return s1


class TestAllocatorArchitecture(unittest.TestCase):
    """gaps.md 4.1 Extensible Allocator Architecture — private `zone <bytes>`
    arenas, configurable capacity, active-arena semantics, on both compilers."""

    EXAMPLE = ROOT / "examples" / "27_multi_zone.vl"

    def test_example_multi_zone_run_and_parity(self):
        src = self.EXAMPLE.read_text(encoding="utf-8")
        s1 = run_stage("stage1", src, "example27")
        s2 = run_stage("stage2", src, "example27")
        self.assertEqual(s1.returncode, 0, s1.stderr)
        self.assertEqual(s2.returncode, 0, s2.stderr)
        self.assertEqual(s1.stdout, s2.stdout, "example outputs diverged")
        self.assertIn("default arena before = 0", s1.stdout)
        self.assertIn("private arena 1 used = 8192", s1.stdout)
        self.assertIn("private arena 2 used = 8192", s1.stdout)
        self.assertIn("frame arena used inside = 8192", s1.stdout)
        self.assertIn("default arena after = 0", s1.stdout)

    def test_emit_c_keeps_default_zone_and_adds_private_arena_calls(self):
        plain = "use sys.mem\nact main() { zone { let a: @i32 = mem.alloc(@i32, 1) } }"
        sized = "use sys.mem\nact main() { zone 4096 { let a: @i32 = mem.alloc(@i32, 1) } }"
        for mode, program in (("plain", plain), ("sized", sized)):
            tmp = ROOT / ".velo_cache" / "alloc_test_emit" / f"emit_{mode}.vl"
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(program, encoding="utf-8")
            res = subprocess.run(
                [sys.executable, str(VELO_PY), "emit-c", str(tmp)],
                capture_output=True, text=True, cwd=ROOT,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertIn("velo_zone_push();", res.stdout)
            self.assertIn("velo_zone_pop(", res.stdout)
            if mode == "sized":
                self.assertIn("velo_zone_enter((size_t)(", res.stdout)
                self.assertIn("velo_zone_leave(", res.stdout)
            else:
                self.assertNotIn("velo_zone_enter(", res.stdout)

    def test_private_arena_isolation_and_o1_reset(self):
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act main() {\n"
            "    let before: usize = mem.used()\n"
            "    io.println(\"before = {before}\")\n"
            "    zone 4096 {\n"
            "        let a: @i32 = mem.alloc(@i32, 1000)\n"
            "        let inside: usize = mem.used()\n"
            "        io.println(\"inside = {inside}\")\n"
            "    }\n"
            "    let after: usize = mem.used()\n"
            "    io.println(\"after = {after}\")\n"
            "}\n"
        )
        assert_parity(program, "isol", ["before = 0", "inside = 4000", "after = 0"])

    def test_capacity_from_runtime_parameter(self):
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act probe(cap: usize) -> usize {\n"
            "    mut live: usize = 0\n"
            "    zone cap {\n"
            "        let marks: @usize = mem.alloc(@usize, 1024)\n"
            "        live = mem.used()\n"
            "    }\n"
            "    return live\n"
            "}\n"
            "act main() -> i32 {\n"
            "    let p = probe(65536)\n"
            "    io.println(\"probe = {p}\")\n"
            "    return 0\n"
            "}\n"
        )
        assert_parity(program, "param", ["probe = 8192"])

    def test_zone_inside_generic_function(self):
        # Guards the monomorphization path: the capacity expression and the
        # Guards the monomorphization path: the zone node and its capacity
        # expression must survive generic instantiation. (Bare `mem.alloc(@T,
        # n)` inside generic acts is an unsupported language surface today and
        # belongs to the 4.1 step-2 Allocator interface design.)
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act probe[T](v: T, lo: usize) -> usize {\n"
            "    mut live: usize = 0\n"
            "    zone lo * 64 {\n"
            "        mut bump: usize = mem.used()\n"
            "        bump = bump + 0\n"
            "        live = bump\n"
            "    }\n"
            "    return live\n"
            "}\n"
            "act main() -> i32 {\n"
            "    let v1: i32 = 1\n"
            "    let lo: usize = 4\n"
            "    let r1: usize = probe(v1, lo)\n"
            "    let r2: usize = probe(v1, lo)\n"
            "    io.println(\"inside = {r1}\")\n"
            "    io.println(\"again = {r2}\")\n"
            "    return 0\n"
            "}\n"
        )
        assert_parity(program, "generic", ["inside = 0", "again = 0"])

    def test_default_zone_arena_unchanged(self):
        # Compat: bare `zone { }` keeps the pre-§4.1 semantics exactly — the
        # watermark wraps allocations on the DEFAULT arena and resets on exit.
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act main() {\n"
            "    let before: usize = mem.used()\n"
            "    zone {\n"
            "        let a: @f64 = mem.alloc(@f64, 100)\n"
            "        let inside: usize = mem.used()\n"
            "        io.println(\"inside = {inside}\")\n"
            "    }\n"
            "    let after: usize = mem.used()\n"
            "    io.println(\"after = {after}\")\n"
            "    let _keep_before: usize = before\n"
            "}\n"
        )
        assert_parity(program, "plainzone", ["inside = 800", "after = 0"])

    def test_defer_inside_zone_runs_before_watermark_reset(self):
        # Stage 2 used to flush zone defers at act end (after the arena had
        # popped); now both stages scope zone-local defers to the block.
        program = (
            "use sys.io\n"
            "act main() {\n"
            "    io.println(\"outer-1\")\n"
            "    zone {\n"
            "        io.println(\"zone-body\")\n"
            "        defer io.println(\"zone-defer\")\n"
            "    }\n"
            "    io.println(\"after-zone\")\n"
            "    defer io.println(\"outer-defer\")\n"
            "    io.println(\"outer-2\")\n"
            "}\n"
        )
        assert_parity(
            program, "zonefer",
            ["outer-1", "zone-body", "zone-defer", "after-zone", "outer-2", "outer-defer"],
        )

    def test_private_arena_oom_is_fatal(self):
        program = (
            "use sys.mem\n"
            "act main() {\n"
            "    zone 8 {\n"
            "        let a: @u64 = mem.alloc(@u64, 100)\n"
            "    }\n"
            "}\n"
        )
        for stage in ("stage1", "stage2"):
            res = run_stage(stage, program, "oom")
            self.assertNotEqual(res.returncode, 0, f"{stage} survived OOM!")
            self.assertIn("Out of Memory", res.stderr, f"{stage} stderr: {res.stderr}")

    def test_zero_capacity_is_fatal(self):
        program = (
            "use sys.io\n"
            "act main() {\n"
            "    zone 0 {\n"
            "        io.println(\"never\")\n"
            "    }\n"
            "}\n"
        )
        for stage in ("stage1", "stage2"):
            res = run_stage(stage, program, "zerocap")
            self.assertNotEqual(res.returncode, 0, f"{stage} survived zero capacity!")
            self.assertIn("capacity must be > 0", res.stderr, f"{stage} stderr: {res.stderr}")

    def test_alloc_size_overflow_is_fatal(self):
        """Bug 1.2: size_t integer overflow in allocation size (e.g. 8 * 2^61)
        must trigger a loud fatal error instead of wrapping around 0 and returning
        an overlapping pointer."""
        program = (
            "use sys.mem\n"
            "act main() {\n"
            "    let huge_count: usize = 2305843009213693952\n"
            "    let a: @u64 = mem.alloc(@u64, huge_count)\n"
            "}\n"
        )
        for stage in ("stage1", "stage2"):
            res = run_stage(stage, program, "allocoverflow")
            self.assertNotEqual(res.returncode, 0, f"{stage} survived size overflow!")
            self.assertIn("Allocation size overflow", res.stderr, f"{stage} stderr: {res.stderr}")

    def test_pool_reuse_across_repeated_entries(self):
        # Allocate far more than one huge arena worth of memory across
        # repeated re-entries; only pool reuse makes this cheap AND safe.
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act tick() -> usize {\n"
            "    mut live: usize = 0\n"
            "    zone 2097152 {\n"  # 2 MB private arena
            "        let data: @u8 = mem.alloc(@u8, 2097152)\n"
            "        live = mem.used()\n"
            "    }\n"
            "    return live\n"
            "}\n"
            "act main() -> i32 {\n"
            "    mut total: usize = 0\n"
            "    loop i in 0..16 {\n"
            "        total = total + tick()\n"
            "    }\n"
            "    io.println(\"total = {total}\")\n"
            "    let after: usize = mem.used()\n"
            "    io.println(\"after = {after}\")\n"
            "    return 0\n"
            "}\n"
        )
        assert_parity(program, "pool", ["total = 33554432", "after = 0"])

    def test_allocator_passable_handle(self):
        """§4.1: mem.current() captures active arena; mem.alloc_with(a, @T, n)
        allocates n elements of T into arena `a` rather than the implicit active arena."""
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act fill(a: @Allocator, n: usize) -> usize {\n"
            "    let buf: @u8 = mem.alloc_with(a, @u8, n)\n"
            "    return mem.used()\n"
            "}\n"
            "act main() {\n"
            "    zone 65536 {\n"
            "        let a: @Allocator = mem.current()\n"
            "        let used: usize = fill(a, 1024)\n"
            "        io.println(\"used = {used}\")\n"
            "    }\n"
            "}\n"
        )
        assert_parity(program, "allochandle", ["used = 1024"])

    def test_allocator_stored_in_struct(self):
        """§4.1: @Allocator can be stored in a data struct field and used later."""
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "data Pool {\n"
            "    a: @Allocator\n"
            "}\n"
            "act pool_alloc_bytes(p: @Pool, n: usize) -> @u8 {\n"
            "    return mem.alloc_with(p.a, @u8, n)\n"
            "}\n"
            "act main() {\n"
            "    zone 32768 {\n"
            "        mut p: Pool = Pool { a: mem.current() }\n"
            "        let buf: @u8 = pool_alloc_bytes(@p, 512)\n"
            "        let used: usize = mem.used()\n"
            "        io.println(\"used = {used}\")\n"
            "    }\n"
            "}\n"
        )
        assert_parity(program, "allocstruct", ["used = 512"])

    def test_allocator_oom_is_fatal(self):
        """§4.1: alloc_with into an @Allocator that has no space left must abort."""
        program = (
            "use sys.mem\n"
            "act main() {\n"
            "    zone 8 {\n"
            "        let a: @Allocator = mem.current()\n"
            "        let buf: @u8 = mem.alloc_with(a, @u8, 1000)\n"
            "    }\n"
            "}\n"
        )
        for stage in ("stage1", "stage2"):
            res = run_stage(stage, program, "allocoom")
            self.assertNotEqual(res.returncode, 0, f"{stage} survived alloc_with OOM!")
            self.assertIn("Out of Memory", res.stderr, f"{stage} stderr: {res.stderr}")

    def test_parameterized_scoped_arena(self):
        """Task 6.1: explicit arena instantiation outside global 64MB arena,
        scoped entry with zone custom_arena, O(1) pop, and defer destruction."""
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act main() {\n"
            "    let before: usize = mem.used()\n"
            "    let custom_arena: @Allocator = mem.create_arena(268435456)\n"
            "    defer mem.destroy_arena(custom_arena)\n"
            "    zone custom_arena {\n"
            "        let buf: @u8 = mem.alloc(1048576)\n"
            "        let inside: usize = mem.used()\n"
            "        io.println(\"inside = {inside}\")\n"
            "    }\n"
            "    let after: usize = mem.used()\n"
            "    io.println(\"before = {before}, after = {after}\")\n"
            "}\n"
        )
        assert_parity(program, "customarena", ["inside = 1048576", "before = 0, after = 0"])

    def test_parameterized_arena_pop_watermark(self):
        """Task 6.1: entering custom arena in multiple consecutive zones pops
        watermark without destroying arena."""
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act main() {\n"
            "    let custom = mem.create_arena(65536)\n"
            "    defer mem.destroy_arena(custom)\n"
            "    zone custom {\n"
            "        let buf: @u8 = mem.alloc(1024)\n"
            "        let u1: usize = mem.used()\n"
            "        io.println(\"u1 = {u1}\")\n"
            "    }\n"
            "    zone custom {\n"
            "        let buf2: @u8 = mem.alloc(2048)\n"
            "        let u2: usize = mem.used()\n"
            "        io.println(\"u2 = {u2}\")\n"
            "    }\n"
            "    let after: usize = mem.used()\n"
            "    io.println(\"default after = {after}\")\n"
            "}\n"
        )
        assert_parity(program, "custompop", ["u1 = 1024", "u2 = 2048", "default after = 0"])

    def test_raw_byte_alloc_one_arg(self):
        """Task 6.1: 1-arg mem.alloc(count) allocates raw @u8 buffer."""
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act main() {\n"
            "    zone 4096 {\n"
            "        let buf: @u8 = mem.alloc(1024)\n"
            "        let used: usize = mem.used()\n"
            "        io.println(\"used = {used}\")\n"
            "    }\n"
            "}\n"
        )
        assert_parity(program, "alloconearg", ["used = 1024"])

    def test_raw_byte_heap_alloc_one_arg(self):
        """Task 6.1: 1-arg mem.heap_alloc(count) allocates raw @u8 buffer."""
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act main() {\n"
            "    let buf: @u8 = mem.heap_alloc(512)\n"
            "    defer mem.free(buf)\n"
            "    let used: usize = mem.heap_used()\n"
            "    io.println(\"heap used >= 512: {used >= 512}\")\n"
            "}\n"
        )
        assert_parity(program, "heapalloconearg", ["heap used >= 512: true"])

    def test_dynamic_chunk_spilling_10000_exceeding_64mb(self):
        """Task 6.2: Allocating 10,000 chunks of 8,192 bytes (81.92 MB total)
        exceeds the 64 MB default arena capacity. The runtime must dynamically
        spill into secondary heap chunks without crashing, then free all secondary
        chunks and reset the primary watermark to 0 on zone exit."""
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act main() {\n"
            "    let before: usize = mem.used()\n"
            "    zone {\n"
            "        mut i: usize = 0\n"
            "        loop i < 10000 {\n"
            "            let buf: @u8 = mem.alloc(8192)\n"
            "            buf[0] = 42\n"
            "            buf[8191] = 99\n"
            "            i = i + 1\n"
            "        }\n"
            "        let inside: usize = mem.used()\n"
            "        io.println(\"inside >= 81920000: {inside >= 81920000}\")\n"
            "    }\n"
            "    let after: usize = mem.used()\n"
            "    io.println(\"before = {before}, after = {after}\")\n"
            "}\n"
        )
        assert_parity(
            program, "spill10000",
            ["inside >= 81920000: true", "before = 0, after = 0"]
        )

    def test_dynamic_chunk_spilling_consecutive_zones(self):
        """Task 6.2: Consecutive zone blocks that exceed capacity must each cleanly
        reclaim all spilled secondary chunks upon exit."""
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act main() {\n"
            "    zone {\n"
            "        mut i: usize = 0\n"
            "        loop i < 10000 {\n"
            "            let buf: @u8 = mem.alloc(8192)\n"
            "            i = i + 1\n"
            "        }\n"
            "    }\n"
            "    let mid: usize = mem.used()\n"
            "    zone {\n"
            "        mut j: usize = 0\n"
            "        loop j < 10000 {\n"
            "            let buf: @u8 = mem.alloc(8192)\n"
            "            j = j + 1\n"
            "        }\n"
            "    }\n"
            "    let final_used: usize = mem.used()\n"
            "    io.println(\"mid = {mid}, final = {final_used}\")\n"
            "}\n"
        )
        assert_parity(
            program, "spillconsecutive",
            ["mid = 0, final = 0"]
        )

    def test_dynamic_chunk_spilling_custom_arena(self):
        """Task 6.2: Custom arenas created via mem.create_arena also support
        dynamic chunk spilling beyond their initial capacity."""
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act main() {\n"
            "    let custom = mem.create_arena(1048576)\n"
            "    defer mem.destroy_arena(custom)\n"
            "    zone custom {\n"
            "        mut i: usize = 0\n"
            "        loop i < 1000 {\n"
            "            let buf: @u8 = mem.alloc(4096)\n"
            "            buf[0] = 7\n"
            "            i = i + 1\n"
            "        }\n"
            "        let inside: usize = mem.used()\n"
            "        io.println(\"inside >= 4096000: {inside >= 4096000}\")\n"
            "    }\n"
            "    let after: usize = mem.used()\n"
            "    io.println(\"after = {after}\")\n"
            "}\n"
        )
        assert_parity(
            program, "spillcustom",
            ["inside >= 4096000: true", "after = 0"]
        )

    def test_nested_zone_spilled_chunk_preservation(self):
        """Task 6.3 / Bug 1: When an outer zone spills into secondary chunks,
        nested zone { ... } blocks popping their watermarks must preserve
        all outer secondary chunks rather than prematurely freeing them (which
        caused use-after-free and aliasing corruption)."""
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act main() {\n"
            "    zone {\n"
            "        let filler: @u8 = mem.alloc(67108864)\n"
            "        let p: @u8 = mem.alloc(128)\n"
            "        p[0] = 42\n"
            "        p[127] = 99\n"
            "        zone {\n"
            "            let q: @u8 = mem.alloc(64)\n"
            "            q[0] = 7\n"
            "        }\n"
            "        let p0: u8 = p[0]\n"
            "        let p127: u8 = p[127]\n"
            "        let r: @u8 = mem.alloc(128)\n"
            "        r[0] = 88\n"
            "        let p0_after_r: u8 = p[0]\n"
            "        io.println(\"p0 = {p0}, p127 = {p127}, after_r = {p0_after_r}\")\n"
            "    }\n"
            "}\n"
        )
        assert_parity(
            program, "nestedspillpreserve",
            ["p0 = 42, p127 = 99, after_r = 42"]
        )

    def test_zone_watermark_popped_on_early_return(self):
        """Bug 2.1: Zone watermarks and active arenas must be popped/left on
        early return statements inside zone blocks to prevent permanent memory leaks."""
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act query_simple() -> i32 {\n"
            "    zone {\n"
            "        let p: @i32 = mem.alloc(@i32, 1000)\n"
            "        p[0] = 42\n"
            "        if p[0] == 42 {\n"
            "            return p[0]\n"
            "        }\n"
            "    }\n"
            "    return 0\n"
            "}\n"
            "act query_nested() -> i32 {\n"
            "    zone {\n"
            "        let p: @i32 = mem.alloc(@i32, 500)\n"
            "        p[0] = 10\n"
            "        zone {\n"
            "            let q: @i32 = mem.alloc(@i32, 500)\n"
            "            q[0] = 99\n"
            "            return p[0] + q[0]\n"
            "        }\n"
            "    }\n"
            "    return 0\n"
            "}\n"
            "act query_custom(custom: @Allocator) -> i32 {\n"
            "    zone custom {\n"
            "        let p: @i32 = mem.alloc(@i32, 500)\n"
            "        p[0] = 77\n"
            "        return p[0]\n"
            "    }\n"
            "    return 0\n"
            "}\n"
            "act query_sized() -> i32 {\n"
            "    zone 65536 {\n"
            "        let p: @i32 = mem.alloc(@i32, 500)\n"
            "        p[0] = 55\n"
            "        return p[0]\n"
            "    }\n"
            "    return 0\n"
            "}\n"
            "act main() {\n"
            "    let base: usize = mem.used()\n"
            "    let r1 = query_simple()\n"
            "    let d1: usize = mem.used() - base\n"
            "    let r2 = query_nested()\n"
            "    let d2: usize = mem.used() - base\n"
            "    let custom = mem.create_arena(1048576)\n"
            "    defer mem.destroy_arena(custom)\n"
            "    let r3 = query_custom(custom)\n"
            "    let d3: usize = mem.used() - base\n"
            "    let r4 = query_sized()\n"
            "    let d4: usize = mem.used() - base\n"
            "    io.println(\"r1={r1}, d1={d1}\")\n"
            "    io.println(\"r2={r2}, d2={d2}\")\n"
            "    io.println(\"r3={r3}, d3={d3}\")\n"
            "    io.println(\"r4={r4}, d4={d4}\")\n"
            "}\n"
        )
        res = run_stage("stage2", program, "earlyretzone")
        self.assertEqual(res.returncode, 0, res.stderr)
        lines = res.stdout.strip().splitlines()
        self.assertEqual(lines, [
            "r1=42, d1=0",
            "r2=109, d2=0",
            "r3=77, d3=0",
            "r4=55, d4=0",
        ])

    def test_zone_early_return_with_interleaved_defers(self):
        """Bug 2.1: Defer statements and zone scope exits must unroll in strict
        LIFO order on early return (inner defers -> zone pop -> outer defers)."""
        program = (
            "use sys.io\n"
            "use sys.mem\n"
            "act query_defer() -> i32 {\n"
            "    defer io.println(\"outer_defer\")\n"
            "    zone {\n"
            "        defer io.println(\"inner_defer\")\n"
            "        let p: @i32 = mem.alloc(@i32, 100)\n"
            "        p[0] = 123\n"
            "        return p[0]\n"
            "    }\n"
            "    return 0\n"
            "}\n"
            "act main() {\n"
            "    let base: usize = mem.used()\n"
            "    let r = query_defer()\n"
            "    let d: usize = mem.used() - base\n"
            "    io.println(\"r={r}, d={d}\")\n"
            "}\n"
        )
        res = run_stage("stage2", program, "earlyretdefer")
        self.assertEqual(res.returncode, 0, res.stderr)
        lines = res.stdout.strip().splitlines()
        self.assertEqual(lines, [
            "inner_defer",
            "outer_defer",
            "r=123, d=0",
        ])



if __name__ == "__main__":
    unittest.main()


