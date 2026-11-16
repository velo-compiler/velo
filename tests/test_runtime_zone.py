"""Phase 65: runtime zone allocator hardening.

`runtime/velo_runtime.h` has two defensive-path defects that the compiler
cannot see and no existing test exercises:

1. `velo_zone_enter` (~line 518) allocates the arena struct with `malloc` and
   then writes `z->base` before the `if (!z || !z->base)` check. When the
   struct allocation fails, that write dereferences NULL instead of reporting
   the documented fatal. The buffer allocation is checked correctly; only the
   struct is not.
2. `velo_zone_pop` (~line 449) falls into an else branch for an out-of-range
   watermark and assigns `z->offset = watermark`. `watermark` is a 1-based
   **watermark index**, not a byte offset, so the fallback can leave `offset`
   above `cap` and make the next `velo_mem_alloc` capacity check underflow
   (`z->cap - z->offset`) into a huge value.

Both are OOM/defensive-path bugs. This module is the Task 65.1 harness: it
compiles the runtime header directly with the same GCC the compiler drivers
use, plus a `malloc`-interposing shim so allocation failure is deterministic
rather than hoped-for. The red rows assert the *intended* contract; Tasks
65.2/65.3 make them pass.

ASan/UBSan are not available on this Windows host (no clang; MSVC sanitizers
need a different toolchain), so the OOM rows use fail-injection instead of a
sanitizer. That substitution is recorded in `gaps.md`.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
RUNTIME_DIR = REPO_ROOT / "runtime"

# malloc interposer: `velo_test_arm(n)` makes the nth subsequent allocation
# fail. Allocations are counted per call, so a harness arms immediately before
# the call it wants to fail and the index is 0.
PRELUDE = r"""
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

static int g_fail_at = -1;
static int g_malloc_calls = 0;

static void* velo_test_malloc(size_t n) {
    int idx = g_malloc_calls++;
    if (idx == g_fail_at) return NULL;
    return malloc(n);
}

static void velo_test_arm(int n) { g_malloc_calls = 0; g_fail_at = n; }

#define malloc velo_test_malloc
"""

# Normal-path contract: enter/pop balance, nested zones, watermark restore, and
# the active-arena identity after leave.
NORMAL_PATH = r"""
#include "velo_runtime.h"

int main(void) {
    if (velo_mem_used() != 0) { fprintf(stderr, "fresh default arena is not empty\n"); return 10; }

    // A. enter/push/alloc/pop/leave balances back to zero.
    VeloZoneArena* prev = velo_zone_enter(65536);
    size_t wm = velo_zone_push();
    if (velo_mem_used() != 0) { fprintf(stderr, "private arena started non-empty\n"); return 11; }
    u8* p = (u8*)velo_mem_alloc(64, 1);
    if (!p) { fprintf(stderr, "alloc returned NULL\n"); return 12; }
    for (int i = 0; i < 64; ++i) p[i] = (u8)i;
    if (velo_mem_used() != 64) { fprintf(stderr, "used != 64 after alloc\n"); return 13; }
    velo_zone_pop(wm);
    if (velo_mem_used() != 0) { fprintf(stderr, "pop did not restore the watermark\n"); return 14; }
    velo_zone_leave(prev);
    if (velo_zone_active() != prev) { fprintf(stderr, "leave did not restore the active arena\n"); return 15; }

    // B. Nested zones scope independently.
    VeloZoneArena* outer_prev = velo_zone_enter(32768);
    VeloZoneArena* outer_arena = velo_zone_active();
    size_t outer_wm = velo_zone_push();
    u8* outer_buf = (u8*)velo_mem_alloc(128, 1);
    if (!outer_buf) { fprintf(stderr, "outer alloc failed\n"); return 16; }
    size_t after_outer = velo_mem_used();
    {
        VeloZoneArena* inner_prev = velo_zone_enter(16384);
        size_t inner_wm = velo_zone_push();
        if (velo_mem_used() != 0) { fprintf(stderr, "inner arena inherited a watermark\n"); return 17; }
        u8* inner_buf = (u8*)velo_mem_alloc(256, 1);
        if (!inner_buf) { fprintf(stderr, "inner alloc failed\n"); return 18; }
        if (velo_mem_used() != 256) { fprintf(stderr, "inner used != 256\n"); return 19; }
        velo_zone_pop(inner_wm);
        velo_zone_leave(inner_prev);
    }
    if (velo_zone_active() != outer_arena) { fprintf(stderr, "nested leave broke the stack\n"); return 20; }
    if (velo_mem_used() != after_outer) { fprintf(stderr, "outer watermark changed\n"); return 21; }
    velo_zone_pop(outer_wm);
    if (velo_mem_used() != 0) { fprintf(stderr, "outer pop did not restore\n"); return 22; }
    velo_zone_leave(outer_prev);

    // C. Two sequential pushes: popping the inner one restores the outer offset.
    VeloZoneArena* seq_prev = velo_zone_enter(65536);
    size_t wm1 = velo_zone_push();
    u8* a = (u8*)velo_mem_alloc(32, 1);
    if (!a) { fprintf(stderr, "seq alloc 1 failed\n"); return 23; }
    size_t mark_outer = velo_mem_used();
    size_t wm2 = velo_zone_push();
    u8* b = (u8*)velo_mem_alloc(48, 1);
    if (!b) { fprintf(stderr, "seq alloc 2 failed\n"); return 24; }
    velo_zone_pop(wm2);
    if (velo_mem_used() != mark_outer) { fprintf(stderr, "inner pop did not restore the outer offset\n"); return 25; }
    velo_zone_pop(wm1);
    if (velo_mem_used() != 0) { fprintf(stderr, "outer pop did not restore zero\n"); return 26; }
    velo_zone_leave(seq_prev);

    printf("ZONE-OK\n");
    return 0;
}
"""

# Defect 1: the arena STRUCT allocation fails (index 0 of the zone_enter pair).
# Documented behaviour is a clean fatal; the current code writes `z->base`
# through the NULL struct first.
OOM_ENTER_STRUCT = r"""
#include "velo_runtime.h"

int main(void) {
    void* warm = velo_mem_alloc(8, 8);   // create the default arena first
    if (!warm) { fprintf(stderr, "warmup alloc failed\n"); return 30; }
    velo_test_arm(0);
    velo_zone_enter(4096);
    printf("SURVIVED\n");
    return 0;
}
"""

# Defect 1 control: the BUFFER allocation fails (index 1). The existing
# `if (!z || !z->base)` check catches this, so the row passes today — it proves
# the harness reaches the intended code path.
OOM_ENTER_BUFFER = r"""
#include "velo_runtime.h"

int main(void) {
    void* warm = velo_mem_alloc(8, 8);
    if (!warm) { fprintf(stderr, "warmup alloc failed\n"); return 30; }
    velo_test_arm(1);
    velo_zone_enter(4096);
    printf("SURVIVED\n");
    return 0;
}
"""

# Defect 2: an out-of-range watermark must leave the arena usable.
POP_OUT_OF_RANGE = r"""
#include "velo_runtime.h"

int main(void) {
    VeloZoneArena* prev = velo_zone_enter(4096);
    size_t wm = velo_zone_push();
    u8* p = (u8*)velo_mem_alloc(64, 1);
    if (!p) { fprintf(stderr, "alloc failed\n"); return 40; }
    velo_zone_pop(wm + 4096);            // watermark index far out of range
    VeloZoneArena* z = velo_zone_active();
    printf("offset=%llu cap=%llu\n", (unsigned long long)z->offset, (unsigned long long)z->cap);
    if (z->offset > z->cap) { printf("CORRUPTED\n"); return 41; }
    // A corrupted offset also breaks the capacity check in velo_mem_alloc: the
    // subtraction underflows and the next alloc is allowed past `base + cap`.
    u8* q = (u8*)velo_mem_alloc(64, 1);
    if (!q) { printf("CORRUPTED-ALLOC\n"); return 42; }
    if ((uint8_t*)q >= z->base + z->cap) { printf("OUT-OF-BOUNDS\n"); return 43; }
    velo_zone_leave(prev);
    printf("ZONE-FALLBACK-OK\n");
    return 0;
}
"""

# The index-vs-byte-offset confusion in isolation: after the fallback, `offset`
# is literally the index that was passed in.
POP_FALLBACK_STORES_INDEX = r"""
#include "velo_runtime.h"

int main(void) {
    VeloZoneArena* prev = velo_zone_enter(8192);
    velo_zone_push();
    velo_zone_push();
    velo_zone_pop(7);                    // > wm_count (2) -> else branch
    VeloZoneArena* z = velo_zone_active();
    size_t obs_offset = z->offset;       // read BEFORE leave: leave may pool/free z
    size_t obs_wm = z->wm_count;
    velo_zone_leave(prev);
    printf("wm_count=%llu offset=%llu\n",
           (unsigned long long)obs_wm, (unsigned long long)obs_offset);
    if (obs_offset == 7) { printf("INDEX-STORED-AS-OFFSET\n"); return 51; }
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


def _gcc_env():
    gcc = find_gcc()
    env = os.environ.copy()
    env["PATH"] = f"{Path(gcc).parent.resolve()}{os.pathsep}{env.get('PATH', '')}"
    return gcc, env


def build_and_run(tmp_path, name, body):
    """Compile `PRELUDE + body` against the runtime header and run it."""
    gcc, env = _gcc_env()
    tmp_path.mkdir(parents=True, exist_ok=True)
    c_file = tmp_path / f"{name}.c"
    exe = tmp_path / f"{name}.exe"
    c_file.write_text(PRELUDE + body, encoding="utf-8")

    build = subprocess.run(
        [gcc, "-O2", "-std=c99", "-I", str(RUNTIME_DIR), str(c_file), "-o", str(exe), "-static"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
    )
    assert build.returncode == 0, f"{name} compile failed:\n{build.stderr}"
    return subprocess.run([str(exe)], capture_output=True, text=True, timeout=120)


@pytest.fixture(scope="module")
def cache_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("zone_runtime")


def test_zone_enter_pop_nested_and_watermarks(cache_dir):
    """Normal paths must already be correct; this is the regression floor."""
    run = build_and_run(cache_dir, "normal_path", NORMAL_PATH)
    assert run.returncode == 0, f"stdout:\n{run.stdout}\nstderr:\n{run.stderr}"
    assert "ZONE-OK" in run.stdout


def test_zone_enter_buffer_oom_is_already_a_clean_fatal(cache_dir):
    """Control row: the existing `!z->base` check does catch the buffer OOM."""
    run = build_and_run(cache_dir, "oom_buffer", OOM_ENTER_BUFFER)
    assert run.returncode == 1, (
        f"expected the documented fatal exit, got rc={run.returncode}\n"
        f"stdout:\n{run.stdout}\nstderr:\n{run.stderr}"
    )
    assert "Velo Fatal Error" in run.stderr, run.stderr
    assert "Zone Arena allocation failed" in run.stderr, run.stderr


def test_zone_enter_struct_oom_reports_fatal_not_null_deref(cache_dir):
    """Task 65.2: the struct allocation must be checked before `z->base`."""
    run = build_and_run(cache_dir, "oom_struct", OOM_ENTER_STRUCT)
    assert "SURVIVED" not in run.stdout, (
        "velo_zone_enter returned normally after a failed struct allocation:\n" + run.stdout
    )
    assert run.returncode == 1, (
        f"expected the documented fatal (exit 1), got rc={run.returncode} "
        f"(a Windows NULL dereference shows up as 0xC0000005 = -1073741819)\n"
        f"stdout:\n{run.stdout}\nstderr:\n{run.stderr}"
    )
    assert "Velo Fatal Error" in run.stderr, (
        f"no fatal diagnostic; the NULL was not caught before the write:\n{run.stderr}"
    )
    assert "Zone Arena allocation failed" in run.stderr, run.stderr


@pytest.mark.xfail(strict=True, reason="Task 65.3 fixes the velo_zone_pop fallback")
def test_zone_pop_out_of_range_keeps_the_arena_usable(cache_dir):
    """Task 65.3: the fallback must not write a watermark index into offset."""
    run = build_and_run(cache_dir, "pop_out_of_range", POP_OUT_OF_RANGE)
    blob = run.stdout + run.stderr
    assert "CORRUPTED" not in blob, (
        f"velo_zone_pop left offset > cap; the arena is unusable:\n{blob}"
    )
    assert "OUT-OF-BOUNDS" not in blob, f"the next alloc ran out of bounds:\n{blob}"
    assert run.returncode == 0, blob
    assert "ZONE-FALLBACK-OK" in run.stdout, blob


@pytest.mark.xfail(strict=True, reason="Task 65.3 fixes the velo_zone_pop fallback")
def test_zone_pop_fallback_does_not_store_the_index(cache_dir):
    """The defect in isolation: offset must never equal the passed-in index."""
    run = build_and_run(cache_dir, "pop_index", POP_FALLBACK_STORES_INDEX)
    blob = run.stdout + run.stderr
    assert "INDEX-STORED-AS-OFFSET" not in blob, (
        "velo_zone_pop assigned a watermark index to a byte offset:\n" + blob
    )
    assert run.returncode == 0, blob


def test_runtime_header_copies_are_identical():
    """Stage 2 uses runtime/, Stage 1 uses velo/runtime/. A fix applied to one
    copy alone would leave the other stage broken while every test still
    passed, so the two copies must stay byte-identical."""
    stage2 = RUNTIME_DIR / "velo_runtime.h"
    stage1 = REPO_ROOT / "velo" / "runtime" / "velo_runtime.h"
    assert stage2.is_file(), stage2
    assert stage1.is_file(), stage1
    assert stage2.read_bytes() == stage1.read_bytes(), (
        "runtime/velo_runtime.h and velo/runtime/velo_runtime.h diverged; "
        "apply the change to both and re-copy"
    )
