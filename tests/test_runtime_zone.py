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
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import cc_path

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

static void* velo_test_realloc(void* p, size_t n) {
    int idx = g_malloc_calls++;
    if (idx == g_fail_at) return NULL;
    return realloc(p, n);
}

static void velo_test_arm(int n) { g_malloc_calls = 0; g_fail_at = n; }

#define malloc velo_test_malloc
#define realloc velo_test_realloc
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

    velo_thread_tls_release();   // leave no arena behind: leak check runs on this row
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
    velo_thread_tls_release();   // leak check runs on this row
    printf("ZONE-FALLBACK-OK\n");
    return 0;
}
"""

# Zero is also out of range: watermark indices are 1-based. The fallback must
# reset the arena rather than leave it pointing anywhere but a valid state.
POP_ZERO_WATERMARK = r"""
#include "velo_runtime.h"

int main(void) {
    VeloZoneArena* prev = velo_zone_enter(4096);
    velo_zone_push();
    u8* p = (u8*)velo_mem_alloc(64, 1);
    if (!p) { fprintf(stderr, "alloc failed\n"); return 60; }
    velo_zone_pop(0);
    VeloZoneArena* z = velo_zone_active();
    if (z->offset > z->cap) { printf("CORRUPTED\n"); return 61; }
    if (z->wm_count != 0 || z->wm_cap != 0 || z->wm_heap != NULL) {
        printf("WATERMARKS-NOT-RESET wm_count=%llu cap=%llu heap=%p\n",
               (unsigned long long)z->wm_count, (unsigned long long)z->wm_cap, (void*)z->wm_heap);
        return 62;
    }
    u8* q = (u8*)velo_mem_alloc(1024, 1);
    if (!q) { printf("ARENA-UNUSABLE-AFTER-ZERO-POP\n"); return 63; }
    if ((uint8_t*)q + 1024 > z->base + z->cap) { printf("OUT-OF-BOUNDS\n"); return 64; }
    velo_zone_leave(prev);
    velo_thread_tls_release();   // leak check runs on this row
    printf("ZERO-POP-OK\n");
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


# Task 65.4: every allocation site must be checked. These three probes reach
# the sites the earlier defects did not: the watermark heap array, and the two
# capacity subtractions that underflow when an arena watermark is corrupt.
WM_HEAP_OOM = r"""
#include "velo_runtime.h"

int main(void) {
    VeloZoneArena* prev = velo_zone_enter(65536);
    for (int i = 0; i < VELO_ZONE_WM_INLINE; ++i) velo_zone_push();
    velo_test_arm(0);        // the watermark heap realloc is the next allocation
    velo_zone_push();
    printf("SURVIVED\n");
    velo_zone_leave(prev);
    return 0;
}
"""

CORRUPTED_PRIMARY_OFFSET = r"""
#include "velo_runtime.h"

int main(void) {
    VeloZoneArena* prev = velo_zone_enter(4096);   // fixed budget: no spilling
    VeloZoneArena* z = velo_zone_active();
    z->offset = z->cap + 4096;                     // corrupt the arena watermark
    u8* p = (u8*)velo_mem_alloc(64, 1);
    if (p) {
        printf("ALLOWED-PAST-CAP p=%p base=%p cap=%llu\n",
               (void*)p, (void*)z->base, (unsigned long long)z->cap);
        return 70;
    }
    printf("NOT-REACHED\n");
    return 0;
}
"""

CORRUPTED_CHUNK_OFFSET = r"""
#include "velo_runtime.h"

static int in_chunks(VeloZoneArena* z, uint8_t* p, size_t n) {
    for (VeloZoneChunk* c = z->chunks; c; c = c->next)
        if (p >= c->base && p + n <= c->base + c->cap) return 1;
    if (z->base && p >= z->base && p + n <= z->base + z->cap) return 1;
    return 0;
}

int main(void) {
    VeloZoneArena* a = velo_mem_create_arena(4096);   // growable: can spill
    // Fill the primary buffer so the guarded chunk path is the one that runs;
    // otherwise a small request is served from the primary and never touches
    // the corrupted chunk.
    u8* fill = (u8*)velo_alloc_with(a, 4096, 1);
    if (!fill) { fprintf(stderr, "primary fill failed\n"); return 80; }
    u8* big = (u8*)velo_alloc_with(a, 8192, 1);
    if (!big) { fprintf(stderr, "spill alloc failed\n"); return 81; }
    if (!a->chunks) { fprintf(stderr, "expected a spilled chunk\n"); return 82; }
    a->chunks->offset = a->chunks->cap + 1;           // corrupt the chunk watermark
    u8* p = (u8*)velo_alloc_with(a, 64, 1);
    if (!p) { fprintf(stderr, "alloc failed\n"); return 83; }
    if (!in_chunks(a, (uint8_t*)p, 64)) { printf("OUT-OF-BOUNDS\n"); return 84; }
    velo_mem_destroy_arena(a);   // leak check runs on this row
    printf("CHUNK-GUARD-OK\n");
    return 0;
}
"""


def find_cc() -> str:
    """The compiler under test. `CC` wins so the sanitizer lane can point a
    clang+ASan/UBSan build at the same harness; otherwise use gcc, which is
    what both Velo build drivers use."""
    for name in (os.environ.get("CC"), "gcc", "cc"):
        if not name:
            continue
        found = shutil.which(name)
        if found:
            return found
    for candidate in (cc_path(), cc_path()):
        p = Path(candidate)
        if p.exists():
            return str(p)
    raise AssertionError("no C compiler found — install GCC (MinGW/MSYS2) like the build drivers require")


def _cc_env():
    cc = find_cc()
    env = os.environ.copy()
    env["PATH"] = f"{Path(cc).parent.resolve()}{os.pathsep}{env.get('PATH', '')}"
    return cc, env


def _extra_flags(var):
    return shlex.split(os.environ.get(var, ""))


def build_and_run(tmp_path, name, body, expected_fatal=False):
    """Compile `PRELUDE + body` against the runtime header and run it.

    Honours `VELO_CFLAGS`/`VELO_LDFLAGS` exactly like the CI sanitizer job, so
    the same probes can be built with `-fsanitize=address,undefined`.
    `-static` is a Windows convenience only: it does not link against the
    sanitizer runtimes, so it is dropped when sanitizers are requested.
    """
    cc, env = _cc_env()
    extra_c = _extra_flags("VELO_CFLAGS")
    extra_ld = _extra_flags("VELO_LDFLAGS")
    sanitized = any("sanitize" in flag for flag in extra_c + extra_ld)
    tmp_path.mkdir(parents=True, exist_ok=True)
    c_file = tmp_path / f"{name}.c"
    exe = tmp_path / f"{name}.exe" if os.name == "nt" else tmp_path / name
    c_file.write_text(PRELUDE + body, encoding="utf-8")

    cmd = [cc, "-O2", "-std=c99", "-I", str(RUNTIME_DIR), str(c_file), "-o", str(exe)]
    cmd += extra_c + extra_ld
    if os.name == "nt" and not sanitized:
        cmd.append("-static")

    build = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
    )
    assert build.returncode == 0, f"{name} compile failed:\n{build.stderr}"

    run_env = env
    if expected_fatal:
        # These rows terminate inside the runtime's fatal handler, so the
        # arena the probe was using is never released. Leak detection would
        # report that by design, so it is off for fatal rows only; every other
        # row runs with leak detection as the CI lane configured it.
        run_env = env.copy()
        opts = run_env.get("ASAN_OPTIONS", "")
        run_env["ASAN_OPTIONS"] = (opts + ":" if opts else "") + "detect_leaks=0"
    return subprocess.run([str(exe)], capture_output=True, text=True, timeout=120, env=run_env)


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
    run = build_and_run(cache_dir, "oom_buffer", OOM_ENTER_BUFFER, expected_fatal=True)
    assert run.returncode == 1, (
        f"expected the documented fatal exit, got rc={run.returncode}\n"
        f"stdout:\n{run.stdout}\nstderr:\n{run.stderr}"
    )
    assert "Velo Fatal Error" in run.stderr, run.stderr
    assert "Zone Arena allocation failed" in run.stderr, run.stderr


def test_zone_enter_struct_oom_reports_fatal_not_null_deref(cache_dir):
    """Task 65.2: the struct allocation must be checked before `z->base`."""
    run = build_and_run(cache_dir, "oom_struct", OOM_ENTER_STRUCT, expected_fatal=True)
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


def test_zone_pop_fallback_does_not_store_the_index(cache_dir):
    """The defect in isolation: offset must never equal the passed-in index."""
    run = build_and_run(cache_dir, "pop_index", POP_FALLBACK_STORES_INDEX)
    blob = run.stdout + run.stderr
    assert "INDEX-STORED-AS-OFFSET" not in blob, (
        "velo_zone_pop assigned a watermark index to a byte offset:\n" + blob
    )
    assert run.returncode == 0, blob


def test_zone_pop_zero_watermark_resets_the_arena(cache_dir):
    """Task 65.3: zero is out of range too; the arena must stay usable."""
    run = build_and_run(cache_dir, "pop_zero", POP_ZERO_WATERMARK)
    blob = run.stdout + run.stderr
    assert "CORRUPTED" not in blob, blob
    assert "WATERMARKS-NOT-RESET" not in blob, blob
    assert "ARENA-UNUSABLE-AFTER-ZERO-POP" not in blob, blob
    assert "OUT-OF-BOUNDS" not in blob, blob
    assert "ZERO-POP-OK" in run.stdout, blob
    assert run.returncode == 0, blob


def test_zone_watermark_heap_oom_is_fatal(cache_dir):
    """Task 65.4: the watermark heap array grows by `realloc`; failure is fatal."""
    run = build_and_run(cache_dir, "wm_heap_oom", WM_HEAP_OOM, expected_fatal=True)
    assert "SURVIVED" not in run.stdout, (
        "velo_zone_push continued after a failed watermark-heap realloc:\n" + run.stdout
    )
    assert run.returncode == 1, (
        f"expected a clean fatal, got rc={run.returncode}\n"
        f"stdout:\n{run.stdout}\nstderr:\n{run.stderr}"
    )
    assert "Velo Fatal Error" in run.stderr, run.stderr
    assert "Watermark Stack OOM" in run.stderr, run.stderr


def test_corrupted_zone_offset_cannot_allocate_past_cap(cache_dir):
    """Task 65.4: `cap - offset` must not underflow when offset > cap."""
    run = build_and_run(cache_dir, "corrupt_offset", CORRUPTED_PRIMARY_OFFSET, expected_fatal=True)
    blob = run.stdout + run.stderr
    assert "ALLOWED-PAST-CAP" not in blob, (
        f"velo_mem_alloc accepted a block past base + cap:\n{blob}"
    )
    # The fixed-budget arena has nowhere to spill, so the guarded path takes
    # the existing fatal. Either way the block is never handed out.
    assert run.returncode == 1, blob
    assert "Zone Arena Out of Memory" in run.stderr, blob


def test_corrupted_chunk_offset_cannot_allocate_past_chunk(cache_dir):
    """Task 65.4: the chunk fallback has the same subtraction, same guard."""
    run = build_and_run(cache_dir, "corrupt_chunk", CORRUPTED_CHUNK_OFFSET)
    blob = run.stdout + run.stderr
    assert "OUT-OF-BOUNDS" not in blob, (
        f"velo_alloc_with placed a block outside every chunk:\n{blob}"
    )
    assert "CHUNK-GUARD-OK" in run.stdout, blob
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


def test_oom_policy_is_documented_and_matches_the_code():
    """Task 65.6: the policy has to be written down and stay true.

    Checked in both directions so neither side can drift: every allocation-path
    diagnostic the runtime can print must appear in the OOM policy tables, and
    the policy must not describe diagnostics the runtime no longer has.

    Bounds and type diagnostics (`shelf index out of bounds`, `map key not
    found`, `shelf[dyn] unbox`, ...) are deliberately out of scope: they are
    caller-error traps, not OOM policy, and belong to their own subsystems.
    """
    header = (RUNTIME_DIR / "velo_runtime.h").read_text(encoding="utf-8")
    security = (REPO_ROOT / "SECURITY.md").read_text(encoding="utf-8")
    spec = (REPO_ROOT / "docs" / "SPECIFICATION.md").read_text(encoding="utf-8")
    documented = security + spec

    # Every fatal on an allocation path, as it appears in the source. Matched
    # verbatim against the header (so a reword fails here) and as a substring
    # of the docs (so a removal from the policy fails here too).
    ALLOC_FATALS = [
        "Zone Arena allocation failed",
        "Zone Arena Chunk Spilling allocation failed",
        "Zone Arena Watermark Stack OOM",
        "Zone Arena capacity must be > 0",
        "Zone Arena Out of Memory",
        "Arena allocation failed",
        "Arena capacity must be > 0",
        "Allocator Out of Memory",
        "Allocation size overflow",
        "Out of Heap Memory",
        "Cannot enter null arena",
        "got a negative byte count",
        "thread spawn out of memory",
    ]
    for msg in ALLOC_FATALS:
        assert msg in header, (
            f"'{msg}' is in the OOM policy but no longer raised by "
            "runtime/velo_runtime.h — update SECURITY.md/SPECIFICATION.md"
        )
        assert msg in documented, (
            f"runtime raises '{msg}' but the OOM policy does not document it"
        )

    assert "Out-of-Memory Policy" in security
    assert "fail-stop" in security.lower(), "SECURITY.md must state the fail-stop contract"
    assert "### 5.7 Out-of-Memory Behaviour" in spec
    assert "fail-stop" in spec.lower(), "SPECIFICATION.md §5.7 must state the contract"
    # The intrinsics are not optional-returning, which is WHY the policy is
    # fail-stop; the spec has to say so instead of leaving it unexplained.
    assert "never an optional" in spec, "§5.7 must explain the @T (not ?@T) reason"
    # The header itself must carry the policy for whoever edits it next.
    assert "OOM POLICY" in header, "runtime header must document its own OOM policy"
