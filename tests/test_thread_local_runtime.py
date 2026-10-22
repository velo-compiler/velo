import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

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


def find_gcc() -> str:
    found = shutil.which("gcc")
    if found:
        return found
    for candidate in (r"C:\msys64\ucrt64\bin\gcc.exe", r"C:\msys64\mingw64\bin\gcc.exe"):
        p = Path(candidate)
        if p.exists():
            return str(p)
    raise AssertionError("GCC not found — install GCC (MinGW/MSYS2) like the build drivers require")


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


if __name__ == "__main__":
    unittest.main()
