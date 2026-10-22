import unittest

from test_allocators import assert_parity, run_stage, ROOT

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

# The heap ledger is thread-local (gaps 4.2): a worker's undeleted heap bytes
# must vanish from `mem.heap_used()` as seen by main after joining it.
HEAP_COUNTER_PER_THREAD = """use sys.io
use sys.mem
use sys.thread

act worker() -> i32 {
    let p: @i64 = mem.heap_alloc(@i64, 8)
    p[0] = 42
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


class TestThreadSurface(unittest.TestCase):
    """gaps.md 4.2 Multithreaded Memory Safety — the language-level thread
    surface (`use sys.thread`): spawn/join of zero-arg i32 acts, opaque
    @Thread handles, @Mutex acquire/release, per-thread arena isolation and
    per-thread heap accounting. Every case must run identically on both
    compilers."""

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

    def test_heap_counter_is_per_thread(self):
        assert_parity(
            HEAP_COUNTER_PER_THREAD,
            "thread_heap",
            expected_lines=[
                "w = 7", "w = 7", "main heap_used = 0",
            ],
        )


if __name__ == "__main__":
    unittest.main()
