import subprocess
import sys
import unittest

from test_allocators import assert_parity, run_stage, ROOT, VELO_PY, VELO_EXE

PROBE_SPAWN_JOIN = """use sys.io
use sys.mem
use sys.thread

mut glock: @Mutex
mut gcount: i64 = 0

act worker() -> i32 {
    if mem.used() != 0 { return 1 }
    let buf: @u8 = mem.alloc(@u8, 128)
    if mem.used() != 128 { return 2 }
    thread.acquire(glock)
    gcount = gcount + 1
    thread.release(glock)
    if mem.used() != 128 { return 3 }
    return 7
}

act main() -> i32 {
    glock = thread.mutex()
    mut h1: @Thread = thread.spawn(worker)
    mut h2: @Thread = thread.spawn(worker)
    mut h3: @Thread = thread.spawn(worker)
    mut h4: @Thread = thread.spawn(worker)
    let r1: i32 = thread.join(h1)
    let r2: i32 = thread.join(h2)
    let r3: i32 = thread.join(h3)
    let r4: i32 = thread.join(h4)
    io.println("r1 = {r1}")
    io.println("r2 = {r2}")
    io.println("r3 = {r3}")
    io.println("r4 = {r4}")
    io.println("count = {gcount}")
    return 0
}
"""

ANON_SPAWN = """use sys.io
use sys.thread

act main() -> i32 {
    mut h: @Thread = thread.spawn(act() -> i32 { return 11 })
    let r: i32 = thread.join(h)
    io.println("anon = {r}")
    return 0
}
"""

MUTEX_BASIC = """use sys.io
use sys.thread

act main() -> i32 {
    let m: @Mutex = thread.mutex()
    thread.acquire(m)
    thread.release(m)
    thread.acquire(m)
    thread.release(m)
    thread.free(m)
    io.println("mutex basic = ok")
    return 0
}
"""

# §4.2 heap ledger: a single shared counter updated with true atomics, so a
# cross-thread `mem.free` is attributed correctly and workers' alloc/free
# storms keep the diagnostic exactly consistent — after joining both
# workers, the whole process reports 0 outstanding heap bytes.
HEAP_COUNTER_BUSY_WORKERS = """use sys.io
use sys.mem
use sys.thread

act worker() -> i32 {
    let p: @i64 = mem.heap_alloc(@i64, 8)
    p[0] = 42
    mem.free(p)
    return 7
}

act main() -> i32 {
    mut h1: @Thread = thread.spawn(worker)
    mut h2: @Thread = thread.spawn(worker)
    let r1: i32 = thread.join(h1)
    let r2: i32 = thread.join(h2)
    let h: usize = mem.heap_used()
    io.println("w = {r1}")
    io.println("w = {r2}")
    io.println("main heap_used = {h}")
    return 0
}
"""


BAD_SPAWN_INT = """use sys.io
use sys.thread

act main() -> i32 {
    let h: @Thread = thread.spawn(42)
    return 0
}
"""

BAD_SPAWN_SIG = """use sys.io
use sys.thread

act wrongsig(a: i32) -> i32 { return a }

act main() -> i32 {
    let h: @Thread = thread.spawn(wrongsig)
    return 0
}
"""

BAD_JOIN_INT = """use sys.io
use sys.thread

act main() -> i32 {
    thread.join(42)
    return 0
}
"""

BAD_JOIN_NONE = """use sys.io
use sys.thread

act main() -> i32 {
    thread.join()
    return 0
}
"""

BAD_MUTEX_ARG = """use sys.io
use sys.thread

act main() -> i32 {
    let m: @Mutex = thread.mutex()
    thread.acquire(42)
    return 0
}
"""

BAD_MUTEX_EXTRA = """use sys.io
use sys.thread

act main() -> i32 {
    let m: @Mutex = thread.mutex(1)
    return 0
}
"""


class TestThreadSurface(unittest.TestCase):
    """gaps.md 4.2 Multithreaded Memory Safety — the language-level thread
    surface (`use sys.thread`): spawn/join of zero-arg i32 acts, opaque
    @Thread handles, @Mutex acquire/release, per-thread arena isolation and
    a shared atomic heap ledger. Invalid thread intrinsic arguments are
    compile-time errors on BOTH stages with identical wording. Every case
    must run identically on both compilers."""

    def _build_rejected(self, program: str, name: str, want_msg: str):
        """Both compilers must REJECT this program at build time with the
        same message substring (threads surface contract, gaps §4.2)."""
        tmp = ROOT / ".velo_cache" / f"thread_reject_{name}"
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

    def test_compile_rejects_bad_thread_args(self):
        self._build_rejected(BAD_SPAWN_INT, "bad_spawn_int",
                             "thread.spawn expects act() -> i32 (got i32)")
        self._build_rejected(BAD_SPAWN_SIG, "bad_spawn_sig",
                             "thread.spawn expects act() -> i32 (got act(i32) -> i32)")
        self._build_rejected(BAD_JOIN_INT, "bad_join_int",
                             "thread.join expects @Thread (got i32)")
        self._build_rejected(BAD_MUTEX_ARG, "bad_mutex_arg",
                             "thread.acquire expects @Mutex (got i32)")
        self._build_rejected(BAD_MUTEX_EXTRA, "bad_mutex_extra",
                             "thread.mutex takes no arguments")
        self._build_rejected(BAD_JOIN_NONE, "bad_join_none",
                             "thread.join takes exactly 1 argument")

    def test_spawn_join_arena_isolation_and_mutex_counter(self):
        assert_parity(
            PROBE_SPAWN_JOIN,
            "thread_spawn",
            expected_lines=[
                "r1 = 7", "r2 = 7", "r3 = 7", "r4 = 7", "count = 4",
            ],
        )

    def test_anonymous_act_spawn(self):
        assert_parity(ANON_SPAWN, "thread_anon", expected_lines=["anon = 11"])

    def test_mutex_basic_ops_single_thread(self):
        assert_parity(MUTEX_BASIC, "thread_mutex", expected_lines=["mutex basic = ok"])

    def test_heap_ledger_consistent_under_threads(self):
        assert_parity(
            HEAP_COUNTER_BUSY_WORKERS,
            "thread_heap",
            expected_lines=[
                "w = 7", "w = 7", "main heap_used = 0",
            ],
        )


if __name__ == "__main__":
    unittest.main()
