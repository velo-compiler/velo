import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from conftest import cc_path

ROOT = Path(__file__).parent.parent.resolve()
RUNTIME = ROOT / "velo" / "runtime"

# gaps §4.2 Multithreaded Memory Safety — the zone runtime must be per-thread:
# default arenas, active pointers, and the private-arena reuse pool live in
# thread-local storage so concurrent `mem.alloc` bump watermarks cannot race.
#
# This test exercises the runtime *header* directly with a C harness compiled
# by the same GCC the drivers use, spawning real threads (winpthreads). The
# runtime itself stays thread-API-agnostic — no pthread/Win32 thread inside
# velo_runtime.h — the harness brings its own threading.

HARNESS = r"""
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include "velo_runtime.h"

#define THREADS 8
#define ITERATIONS 300

static VeloZoneArena* thread_defaults[THREADS];
static int thread_status[THREADS];

static void* worker(void* raw) {
    long id = (long)raw;
    // Check 1: each thread starts with a FRESH private default arena.
    // (The pre-4.2 global default would have exposed watermarks/offsets
    // written by the main thread or by other threads — and raced on them.)
    if (velo_mem_used() != 0) { thread_status[id] = 1; return NULL; }
    VeloZoneArena* mine = velo_zone_active();
    thread_defaults[id] = mine;
    for (size_t i = ITERATIONS; i > 0; --i) {
        VeloZoneArena* before = velo_zone_active();
        // Varying-capacity private arenas stress the per-thread reuse pool.
        VeloZoneArena* prev = velo_zone_enter((size_t)i * 4096 + 16);
        size_t wm0 = velo_zone_push();
        if (velo_mem_used() != 0) { thread_status[id] = 2; return NULL; }
        u8* p = (u8*)velo_mem_alloc(8, 64);
        if (!p) { thread_status[id] = 3; return NULL; }
        for (size_t j = 0; j < 64; ++j) p[j] = (u8)(id + j);
        // Check 2: data written into a thread's own arena is never clobbered.
        for (size_t j = 0; j < 64; ++j)
            if (p[j] != (u8)(id + j)) { thread_status[id] = 4; return NULL; }
        velo_zone_pop(wm0);
        velo_zone_leave(prev);
        // Check 3: the active pointer is restored exactly after zone exit.
        if (velo_zone_active() != before) { thread_status[id] = 5; return NULL; }
    }
    // Check 4: after 300 pool churns, this thread's default is untouched and active again.
    if (velo_mem_used() != 0) { thread_status[id] = 6; return NULL; }
    if (velo_zone_active() != mine) { thread_status[id] = 7; return NULL; }
    thread_status[id] = 0;
    return NULL;
}

int main(void) {
    pthread_t th[THREADS];
    for (long i = 0; i < THREADS; ++i) {
        if (pthread_create(&th[i], NULL, worker, (void*)i) != 0) {
            fprintf(stderr, "harness: pthread_create failed\n");
            return 2;
        }
    }
    for (long i = 0; i < THREADS; ++i) {
        if (pthread_join(th[i], NULL) != 0) { fprintf(stderr, "harness: join failed\n"); return 2; }
    }
    for (long i = 0; i < THREADS; ++i) {
        if (thread_status[i] != 0) {
            fprintf(stderr, "harness: thread %ld failed check %d\n", i, thread_status[i]);
            return 3;
        }
    }
    // Check 5: all default-arena handles must be distinct (never shared/moved).
    for (long i = 0; i < THREADS; ++i) {
        for (long k = i + 1; k < THREADS; ++k) {
            if (thread_defaults[i] == thread_defaults[k]) {
                fprintf(stderr, "harness: threads %ld and %ld share a default arena\n", i, k);
                return 4;
            }
        }
    }
    printf("TLS-OK\n");
    return 0;
}
"""

# Second harness (§4.2 thread surface): the runtime's own spawn/join/mutex
# API, driven from C. Three checks — zero-arg i32 fns (Velo acts) spawn and
# return their value through join; a shared mutex makes 4 threads × 1000
# increments land at exactly 4000; repeated spawn/join cycles stay stable
# (each thread releases its per-thread arena set on exit).
HARNESS_THREADS = r"""
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "velo_runtime.h"

#define WT 4
#define INC 1000

static i32 plain_fn(void) { return 42; }

static long long g_shared = 0;
static void* g_lock = NULL;

static i32 counting_fn(void) {
    for (i32 i = 0; i < INC; ++i) {
        velo_mutex_acquire(g_lock);
        g_shared += 1;
        velo_mutex_release(g_lock);
    }
    // also touch this thread's arena, so tls_release must free a live arena
    u8* p = (u8*)velo_mem_alloc(8, 64);
    for (i32 j = 0; j < 64; ++j) p[j] = (u8)j;
    return 7;
}

static i32 fn17(void) { return 17; }

int main(void) {
    g_lock = velo_mutex_create();
    if (!g_lock) { fprintf(stderr, "mutex create failed\n"); return 2; }

    // Check A: spawn/join of plain zero-arg i32 fns publishes return values.
    if (velo_thread_join(velo_thread_spawn((VeloThreadFn)plain_fn)) != 42) return 30;
    if (velo_thread_join(velo_thread_spawn((VeloThreadFn)fn17)) != 17) return 31;

    // Check B (lifecycle): a second join of the same handle must be caught
    // by the tombstone magic — this harness only exercises the healthy
    // paths; the fatal ones live in the mini-harnesses below.

    // Check C: 4 concurrent counting fns under one mutex.
    VeloThreadCtx* th[WT];
    for (long i = 0; i < WT; ++i) {
        th[i] = velo_thread_spawn((VeloThreadFn)counting_fn);
        if (!th[i]) { fprintf(stderr, "spawn %ld failed\n", i); return 2; }
    }
    for (long i = 0; i < WT; ++i) {
        if (velo_thread_join(th[i]) != 7) { fprintf(stderr, "join %ld value wrong\n", i); return 3; }
    }
    if (g_shared != (long long)WT * INC) return 40;  // lost/big update = broken mutex

    // Check D: repeated spawn/join cycles stay stable (release path re-runs).
    for (int cycle = 0; cycle < 100; ++cycle) {
        VeloThreadCtx* c = velo_thread_spawn((VeloThreadFn)plain_fn);
        if (!c) return 2;
        if (velo_thread_join(c) != 42) return 41;
    }
    velo_mutex_destroy(g_lock);
    printf("THREADS-OK\n");
    return 0;
}
"""


def find_gcc() -> str:
    found = shutil.which("gcc")
    if found:
        return found
    for candidate in (cc_path(), cc_path()):
        p = Path(candidate)
        if p.exists():
            return str(p)
    raise AssertionError("GCC not found — install GCC (MinGW/MSYS2) like the build drivers require")


# Fatal-path mini-harnesses (§4.2 lifecycle checking): each drives exactly one
# invalid runtime operation. exit(1) cannot be intercepted in-process, so each
# is compiled separately and expected to terminate non-zero with its specific
# "Velo Fatal Error" message. Tombstoned handles are *never freed* — their
# addresses can never be recycled by malloc — so replays always read the DEAD
# tag deterministically.
MINI_NULL_JOIN = r"""
#include "velo_runtime.h"
int main(void) {
    void* never_stored = 0;
    velo_thread_join(never_stored);
    return 0;
}
"""

MINI_DOUBLE_JOIN = r"""
#include "velo_runtime.h"
static i32 f42(void) { return 42; }
static i32 f7(void) { return 7; }
int main(void) {
    VeloThreadCtx* a = velo_thread_spawn((VeloThreadFn)f42);
    VeloThreadCtx* b = velo_thread_spawn((VeloThreadFn)f7);
    if (velo_thread_join(a) != 42) return 9;
    if (velo_thread_join(b) != 7) return 9;
    velo_thread_join(a);  // replayed handle: fatal, no UB
    return 0;
}
"""

MINI_MUTEX_AFTER_FREE = r"""
#include "velo_runtime.h"
int main(void) {
    void* m = velo_mutex_create();
    velo_mutex_acquire(m);
    velo_mutex_release(m);
    velo_mutex_destroy(m);
    velo_mutex_acquire(m);  // use after free: fatal, no silent UB
    return 0;
}
"""

MINI_MUTEX_DOUBLE_FREE = r"""
#include "velo_runtime.h"
int main(void) {
    void* m = velo_mutex_create();
    velo_mutex_destroy(m);
    velo_mutex_destroy(m);  // double free: fatal, no silent UB
    return 0;
}
"""


class TestThreadLocalZoneRuntime(unittest.TestCase):
    def test_zone_state_is_per_thread_under_concurrency(self):
        tmp = ROOT / ".velo_cache" / "thread_tls_test"
        tmp.mkdir(parents=True, exist_ok=True)
        c_file = tmp / "thread_tls_harness.c"
        exe = tmp / "thread_tls_harness.exe"
        c_file.write_text(HARNESS, encoding="utf-8")

        gcc = find_gcc()
        gcc_bin_dir = str(Path(gcc).parent.resolve())
        # Same flags as the drivers (-O2 -std=c99) plus -pthread (this harness
        # brings its own threading) and -static (no winpthreads DLL hunt).
        # Like velo/driver.py: prepend GCC's bin dir to PATH to avoid DLL Hell.
        env = os.environ.copy()
        env["PATH"] = f"{gcc_bin_dir}{os.pathsep}{env.get('PATH', '')}"
        cmd = [
            gcc, "-O2", "-std=c99",
            "-I", str(RUNTIME),
            str(c_file), "-o", str(exe),
            "-pthread", "-static",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, env=env)
        self.assertEqual(res.returncode, 0,
                         f"harness compile failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")

        run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=120)
        self.assertEqual(run.returncode, 0,
                         f"harness run failed:\nSTDOUT:\n{run.stdout}\nSTDERR:\n{run.stderr}")
        self.assertIn("TLS-OK", run.stdout)

    def test_runtime_lifecycle_fatals(self):
        cases = [
            (MINI_NULL_JOIN, "thread join on a null handle", "mini_null_join"),
            (MINI_DOUBLE_JOIN, "already-joined thread handle", "mini_double_join"),
            (MINI_MUTEX_AFTER_FREE, "mutex operation on a freed mutex", "mini_mutex_after_free"),
            (MINI_MUTEX_DOUBLE_FREE, "mutex operation on a freed mutex", "mini_mutex_double_free"),
        ]
        for src_code, want_msg, name in cases:
            tmp = ROOT / ".velo_cache" / "thread_lifecycle_test"
            tmp.mkdir(parents=True, exist_ok=True)
            c_file = tmp / f"{name}.c"
            exe = tmp / f"{name}.exe"
            c_file.write_text(src_code, encoding="utf-8")
            gcc = find_gcc()
            gcc_bin_dir = str(Path(gcc).parent.resolve())
            env = os.environ.copy()
            env["PATH"] = f"{gcc_bin_dir}{os.pathsep}{env.get('PATH', '')}"
            cmd = [
                gcc, "-O2", "-std=c99",
                "-I", str(RUNTIME),
                str(c_file), "-o", str(exe),
                "-static",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, env=env)
            self.assertEqual(res.returncode, 0,
                             f"{name} compile failed:\nSTDERR:\n{res.stderr}")
            run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=120)
            self.assertNotEqual(run.returncode, 0,
                                f"{name}: expected fatal exit, got rc=0 with stdout {run.stdout!r}")
            self.assertIn("Velo Fatal Error", run.stderr, f"{name}: stderr was {run.stderr!r}")
            self.assertIn(want_msg, run.stderr, f"{name}: stderr was {run.stderr!r}")

    def test_spawn_join_mutex_runtime_api(self):
        tmp = ROOT / ".velo_cache" / "thread_api_test"
        tmp.mkdir(parents=True, exist_ok=True)
        c_file = tmp / "thread_api_harness.c"
        exe = tmp / "thread_api_harness.exe"
        c_file.write_text(HARNESS_THREADS, encoding="utf-8")

        gcc = find_gcc()
        gcc_bin_dir = str(Path(gcc).parent.resolve())
        # Pure CRT threads (_beginthreadex): no -pthread needed on Windows.
        # The runtime stays thread-API-agnostic; this harness drives it
        # directly at the C level, exactly like a Velo-generated program.
        cmd = [
            gcc, "-O2", "-std=c99",
            "-I", str(RUNTIME),
            str(c_file), "-o", str(exe),
            "-static",
        ]
        env = os.environ.copy()
        env["PATH"] = f"{gcc_bin_dir}{os.pathsep}{env.get('PATH', '')}"
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, env=env)
        self.assertEqual(res.returncode, 0,
                         f"harness compile failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")

        run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=120)
        self.assertEqual(run.returncode, 0,
                         f"harness run failed:\nSTDOUT:\n{run.stdout}\nSTDERR:\n{run.stderr}")
        self.assertIn("THREADS-OK", run.stdout)


if __name__ == "__main__":
    unittest.main()
