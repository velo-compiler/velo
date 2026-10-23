#ifndef VELO_RUNTIME_H
#define VELO_RUNTIME_H

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stddef.h>
#include <time.h>

// §4.2 platform plumbing for the thread surface (spawn/join + mutex).
// Windows uses the CRT's _beginthreadex (no windows.h, no default-library
// change) plus a handful of kernel32 prototypes declared below; other
// platforms use pthreads directly.
#if defined(_WIN32)
#include <process.h>
#else
#include <pthread.h>
#endif

// Explicit bit-sized integer and float types
typedef int8_t   i8;
typedef int16_t  i16;
typedef int32_t  i32;
typedef int64_t  i64;
typedef uint8_t  u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
typedef float    f32;
typedef double   f64;
typedef size_t   usize;
typedef ptrdiff_t isize;

// ============================================================================
// §4.1 Extensible Allocator Architecture + §4.2 Multithreaded Memory Safety
//
// Allocation model (in allocation-cost order, all O(1)):
//   * Active zone arena  — bump region produced by `zone { ... }` / sized
//     `zone <bytes> { ... }` blocks and by `mem.alloc(...)` calls.
//   * Persistent heap    — malloc-backed, tracked (`mem.heap_alloc` / free).
//
// Zone arenas are first-class objects (VeloZoneArena). Per §4.2 the arena
// state is per-thread thread-local storage (TLS): every thread lazily gets
// its own 32 MB heap-backed default arena and its own reuse pool, so two
// threads calling `mem.alloc(...)` bump into independent watermarks and
// `velo_zone_enter/leave` pool operations cannot race. `zone <bytes> { }`
// blocks acquire a private arena from the thread's pool (capacity >=
// requested, reused across re-entries) for the block's duration.
// Allocation always targets the thread's ACTIVE arena, so nested zones
// scope independently. Explicit `@Allocator` handles (§4.1) are raw arena
// pointers and remain single-threaded until an atomic/locked variant lands.
// ============================================================================
typedef struct VeloZoneArena {
    uint8_t* base;    // start of the bump region
    size_t   cap;     // usable capacity in bytes
    size_t   offset;  // bump watermark (== allocated bytes right now)
} VeloZoneArena;

#define VELO_ZONE_BUFFER_SIZE (32 * 1024 * 1024)

#define VELO_ZONE_POOL_MAX 32

// §4.2 thread-local storage shim: both compilers emit C compiled with
// `-std=c99`, where the C11 keyword `_Thread_local` is unavailable. GCC and
// Clang still accept the GNU `__thread` extension; MSVC uses
// `__declspec(thread)`.
#if defined(_MSC_VER)
#define VELO_TLS __declspec(thread)
#else
#define VELO_TLS __thread
#endif

static inline VeloZoneArena* velo_zone_create_default(void) {
    VeloZoneArena* z = (VeloZoneArena*)malloc(sizeof(VeloZoneArena));
    uint8_t* buf = (uint8_t*)malloc((size_t)VELO_ZONE_BUFFER_SIZE);
    if (!z || !buf) {
        fprintf(stderr, "Velo Fatal Error: Zone Arena allocation failed (%llu bytes)!\n",
                (unsigned long long)VELO_ZONE_BUFFER_SIZE);
        exit(1);
    }
    z->base = buf;
    z->cap = (size_t)VELO_ZONE_BUFFER_SIZE;
    z->offset = 0;
    return z;
}

// Per-thread arena state (§4.2). The default arena and the reuse pool are
// created lazily on a thread's first allocation touch, keeping the zero-cost
// startup of the old static-buffer design.
static VELO_TLS VeloZoneArena* g_velo_zone_tls_default = NULL;
static VELO_TLS VeloZoneArena* g_velo_zone_tls_active  = NULL;
static VELO_TLS VeloZoneArena  g_velo_zone_tls_pool[VELO_ZONE_POOL_MAX];
static VELO_TLS size_t         g_velo_zone_tls_pool_count = 0;

static inline VeloZoneArena* velo_zone_active(void) {
    if (!g_velo_zone_tls_active) {
        g_velo_zone_tls_active = velo_zone_create_default();
        g_velo_zone_tls_default = g_velo_zone_tls_active;
    }
    return g_velo_zone_tls_active;
}

static inline size_t velo_zone_push(void) {
    return velo_zone_active()->offset;
}

static inline void velo_zone_pop(size_t watermark) {
    velo_zone_active()->offset = watermark;
}

static inline size_t velo_mem_used(void) {
    return velo_zone_active()->offset;
}

// Enters a private arena of exactly `bytes` capacity: acquires a pooled or
// fresh arena, makes it the active zone, and returns the previous active
// arena (pass it back to velo_zone_leave on block exit). Paired with
// velo_zone_pop this yields O(1) scoped allocation + O(1) reset.
// The returned struct is ALWAYS heap-owned (pool candidates are copied out),
// so velo_zone_leave can free it and so nested blocks can never alias pool
// slots while another zone is still active.
static inline VeloZoneArena* velo_zone_enter(size_t bytes) {
    if (bytes == 0) {
        fprintf(stderr, "Velo Fatal Error: Zone Arena capacity must be > 0!\n");
        exit(1);
    }
    VeloZoneArena* prev = velo_zone_active();  // §4.2: per-thread active state
    VeloZoneArena* z = (VeloZoneArena*)malloc(sizeof(VeloZoneArena));
    size_t pick = g_velo_zone_tls_pool_count;
    for (size_t i = 0; i < g_velo_zone_tls_pool_count; ++i) {
        if (g_velo_zone_tls_pool[i].cap >= bytes) {  // reuse any arena that fits
            pick = i;
            break;
        }
    }
    if (pick < g_velo_zone_tls_pool_count) {
        *z = g_velo_zone_tls_pool[pick];  // buffer ownership moves to the copy
        g_velo_zone_tls_pool[pick] = g_velo_zone_tls_pool[g_velo_zone_tls_pool_count - 1];
        g_velo_zone_tls_pool_count--;
    } else {
        z->base = (uint8_t*)malloc(bytes);
        if (!z || !z->base) {
            fprintf(stderr, "Velo Fatal Error: Zone Arena allocation failed (%llu bytes)!\n",
                    (unsigned long long)bytes);
            exit(1);
        }
        z->cap = bytes;
    }
    z->offset = 0;
    g_velo_zone_tls_active = z;
    return prev;
}

// Exits a zone block: returns the active arena to the thread-local reuse
// pool (dropping its buffer only if the pool is saturated) and restores the
// previous one (§4.2: the pool is per-thread, so this cannot race).
static inline void velo_zone_leave(VeloZoneArena* prev) {
    VeloZoneArena* z = g_velo_zone_tls_active;
    if (z != g_velo_zone_tls_default) {
        if (g_velo_zone_tls_pool_count < VELO_ZONE_POOL_MAX) {
            g_velo_zone_tls_pool[g_velo_zone_tls_pool_count++] = *z;
        } else {
            free(z->base);
        }
        free(z);
    }
    g_velo_zone_tls_active = prev;
}

static inline void* velo_mem_alloc(size_t size, size_t count) {
    VeloZoneArena* z = velo_zone_active();
    size_t total = size * count;
    size_t aligned = (total + 7) & ~((size_t)7);
    if (z->offset + aligned > z->cap) {
        fprintf(stderr, "Velo Fatal Error: Zone Arena Out of Memory (active arena capacity %llu bytes, requested %llu more)!\n",
                (unsigned long long)z->cap, (unsigned long long)aligned);
        exit(1);
    }
    void* ptr = (void*)&z->base[z->offset];
    z->offset += aligned;
    return ptr;
}

// ============================================================================
// §4.1 Passable Allocator handle
//
// `@Allocator` in Velo is a pointer to a VeloZoneArena (i.e. VeloZoneArena*).
// `mem.current()` returns the active arena pointer so it can be stored in a
// variable or passed as a function parameter — enabling Zig/Odin-style
// allocator-parameterised APIs without introducing a vtable.
// `mem.alloc_with(a, @T, n)` allocates n elements of type T into arena `a`
// instead of the implicit active arena, giving callers explicit control over
// which arena absorbs the allocation.
// §4.2 contract: `mem.current()` / `mem.alloc_with` are per-thread safe, but
// a handle captured in one thread must not be allocated through by another
// thread — bumping a shared watermark is not synchronized.
// ============================================================================
typedef VeloZoneArena* VeloAllocator;

static inline void* velo_alloc_with(VeloAllocator a, size_t size, size_t count) {
    size_t total = size * count;
    size_t aligned = (total + 7) & ~((size_t)7);
    if (a->offset + aligned > a->cap) {
        fprintf(stderr, "Velo Fatal Error: Allocator Out of Memory (capacity %llu bytes, requested %llu more)!\n",
                (unsigned long long)a->cap, (unsigned long long)aligned);
        exit(1);
    }
    void* ptr = (void*)&a->base[a->offset];
    a->offset += aligned;
    return ptr;
}

// Returns the number of bytes currently used in allocator `a`.
static inline size_t velo_alloc_used(VeloAllocator a) {
    return a->offset;
}

// ============================================================================
// §4.2 Thread Surface: spawn / join / mutex
//
// Runs zero-parameter, i32-returning Velo acts on real OS threads. Every
// spawned thread lazily builds its own zone arena state (§4.2 above) and,
// on exit, releases that whole per-thread set (default arena + pool
// buffers) — no arena reservation is left behind per dead thread.
// Handles are opaque and LIFECYCLE-CHECKED:
//   `@Thread` = VeloThreadCtx*   `@Mutex` = VeloMutexCell* (passed as void*)
// Both handle kinds carry a magic tag. Operating on an already-joined
// thread, on a freed mutex, or double-freeing either is a LOUD fatal error
// instead of silent UB: every released handle becomes a never-freed
// "tombstone" — its address is parked on a dead-list and can never be
// recycled by malloc, so a replayed or stale handle always reads the DEAD
// magic. join() on a null handle (never-spawned / OOM) is likewise fatal —
// join never fabricates a fake return value; it returns the entry act's
// real i32 exactly once. The trampoline publishes the status before
// thread exit; pthread_join / WaitForSingleObject synchronize that write
// with join's read (thread-creation/join is ordered in the OS).
// NOTE: spawning an act that does not match act() -> i32 is rejected at
// compile time by both stage checkers; the C-level (VeloThreadFn) cast is
// only for hand-written C using the runtime directly.
// ============================================================================

#define VELO_HANDLE_LIVE 0x1BF35A21u
#define VELO_HANDLE_DEAD 0x2E4C90B7u

static void velo_fatal_msg(const char* why) {
    fprintf(stderr, "Velo Fatal Error: %s\n", why);
    exit(1);
}

typedef i32 (*VeloThreadFn)(void);

typedef struct VeloThreadCtx {
    void* fn;      // entry act pointer (cast to VeloThreadFn)
    i32   status;  // entry act's return value, published before thread exit
    u32   magic;   // VELO_HANDLE_LIVE until joined, then DEAD (tombstone)
    struct VeloThreadCtx* next_reaped;
#if defined(_WIN32)
    void* native;  // Win32 thread handle (WaitForSingleObject + CloseHandle)
#else
    pthread_t native;  // pthread join target
#endif
} VeloThreadCtx;

typedef struct VeloMutexCell {
    void* native;  // Win32 HANDLE / pthread_mutex_t*
    u32   magic;   // VELO_HANDLE_LIVE until destroyed, then DEAD (tombstone)
    struct VeloMutexCell* next_reaped;
} VeloMutexCell;

static VeloThreadCtx* g_velo_thread_tombstones = NULL;
static VeloMutexCell* g_velo_mutex_tombstones = NULL;

// Rejects operations on null / freed / foreign mutex handles. Tombstones
// (never freed, address never recycled) guarantee a stale handle always
// reads VELO_HANDLE_DEAD — no heap-reuse false-positive is possible.
static inline void velo_mutex_assert_live(void* m) {
    VeloMutexCell* c = (VeloMutexCell*)m;
    if (!c) velo_fatal_msg("mutex operation on a null handle");
    if (c->magic != VELO_HANDLE_LIVE) {
        if (c->magic == VELO_HANDLE_DEAD) velo_fatal_msg("mutex operation on a freed mutex");
        velo_fatal_msg("mutex operation on an invalid mutex handle");
    }
}

static inline void velo_thread_assert_live(VeloThreadCtx* ctx) {
    if (!ctx) velo_fatal_msg("thread join on a null handle (spawn failed or handle never stored)");
    if (ctx->magic != VELO_HANDLE_LIVE) {
        if (ctx->magic == VELO_HANDLE_DEAD) velo_fatal_msg("thread join on an already-joined thread handle");
        velo_fatal_msg("thread join on an invalid thread handle");
    }
}

// Releases the calling thread's whole per-thread arena set. Idempotent.
// Threads must be OUTSIDE all zone blocks when this runs (invariant held:
// the entry act returns only after all its zone blocks have closed, which
// rests the active pointer on the default arena).
static inline void velo_thread_tls_release(void) {
    if (g_velo_zone_tls_active == g_velo_zone_tls_default) {
        g_velo_zone_tls_active = NULL;
    }
    if (g_velo_zone_tls_default) {
        free(g_velo_zone_tls_default->base);
        free(g_velo_zone_tls_default);
        g_velo_zone_tls_default = NULL;
    }
    for (size_t i = 0; i < g_velo_zone_tls_pool_count; ++i) {
        free(g_velo_zone_tls_pool[i].base);
    }
    g_velo_zone_tls_pool_count = 0;
}

// Opaque shared mutex: `@Mutex` in Velo is a `void*` VeloMutexCell handle.
// Semantics: create → acquire/release; sharing happens via Velo
// globals/structs, ordered by spawn/join. Destroy parks the cell for good,
// so every later operation on the same (or stale) address exits loudly.
#if defined(_WIN32)
unsigned long __stdcall WaitForSingleObject(void* h, unsigned long ms);
int __stdcall CloseHandle(void* h);
void* __stdcall CreateMutexW(void* attrs, int initial, void* name);
int __stdcall ReleaseMutex(void* h);
#define VELO_WAIT_INFINITE 0xFFFFFFFFu

static unsigned int __stdcall velo_thread_trampoline(void* raw) {
    VeloThreadCtx* ctx = (VeloThreadCtx*)raw;
    ctx->status = ((VeloThreadFn)ctx->fn)();
    velo_thread_tls_release();
    return 0;
}

static inline VeloThreadCtx* velo_thread_spawn(VeloThreadFn fn) {
    VeloThreadCtx* ctx = (VeloThreadCtx*)malloc(sizeof(VeloThreadCtx));
    if (!ctx) velo_fatal_msg("thread spawn out of memory");
    ctx->fn = (void*)fn;
    ctx->status = 0;
    ctx->magic = VELO_HANDLE_LIVE;
    uintptr_t raw = (uintptr_t)_beginthreadex(NULL, 0, velo_thread_trampoline, (void*)ctx, 0, NULL);
    if (raw == 0) {
        // Kernel refused the thread; park the (unused) ctx as a dead
        // tombstone and fail loudly — join would otherwise lie with -1.
        ctx->native = NULL;
        velo_fatal_msg("thread spawn failed (OS refused to create the thread)");
    }
    ctx->native = (void*)raw;
    return ctx;
}

static inline i32 velo_thread_join(VeloThreadCtx* ctx) {
    velo_thread_assert_live(ctx);
    WaitForSingleObject(ctx->native, VELO_WAIT_INFINITE);
    CloseHandle(ctx->native);
    i32 status = ctx->status;
    ctx->status = 0;
    ctx->magic = VELO_HANDLE_DEAD;
    ctx->next_reaped = g_velo_thread_tombstones;
    g_velo_thread_tombstones = ctx;
    return status;
}

static inline void* velo_mutex_create(void) {
    VeloMutexCell* c = (VeloMutexCell*)malloc(sizeof(VeloMutexCell));
    void* native = (c != NULL) ? CreateMutexW(NULL, 0, NULL) : NULL;
    if (!native) {
        free(c);  // frees NULL harmlessly
        velo_fatal_msg("mutex creation failed");
    }
    c->native = native;
    c->magic = VELO_HANDLE_LIVE;
    return (void*)c;
}

static inline void velo_mutex_acquire(void* m) {
    // WAIT_OBJECT_0 (0) and WAIT_ABANDONED (0x80) both mean ownership was
    // taken; anything else is an operating-system-level failure.
    velo_mutex_assert_live(m);
    unsigned long r = WaitForSingleObject(((VeloMutexCell*)m)->native, VELO_WAIT_INFINITE);
    if (!(r == 0 || r == 0x80u)) velo_fatal_msg("mutex acquire failed");
}

static inline void velo_mutex_release(void* m) {
    velo_mutex_assert_live(m);
    if (!ReleaseMutex(((VeloMutexCell*)m)->native)) velo_fatal_msg("mutex release failed");
}

static inline void velo_mutex_destroy(void* m) {
    velo_mutex_assert_live(m);
    VeloMutexCell* c = (VeloMutexCell*)m;
    if (!CloseHandle(c->native)) velo_fatal_msg("mutex destroy failed");
    c->magic = VELO_HANDLE_DEAD;
    c->next_reaped = g_velo_mutex_tombstones;
    g_velo_mutex_tombstones = c;
}

#else  // pthreads

static void* velo_thread_trampoline(void* raw) {
    VeloThreadCtx* ctx = (VeloThreadCtx*)raw;
    ctx->status = ((VeloThreadFn)ctx->fn)();
    velo_thread_tls_release();
    return NULL;
}

static inline VeloThreadCtx* velo_thread_spawn(VeloThreadFn fn) {
    VeloThreadCtx* ctx = (VeloThreadCtx*)malloc(sizeof(VeloThreadCtx));
    if (!ctx) velo_fatal_msg("thread spawn out of memory");
    ctx->fn = (void*)fn;
    ctx->status = 0;
    ctx->magic = VELO_HANDLE_LIVE;
    if (pthread_create(&ctx->native, NULL, velo_thread_trampoline, (void*)ctx) != 0) {
        velo_fatal_msg("thread spawn failed (OS refused to create the thread)");
    }
    return ctx;
}

static inline i32 velo_thread_join(VeloThreadCtx* ctx) {
    velo_thread_assert_live(ctx);
    pthread_join(ctx->native, NULL);
    i32 status = ctx->status;
    ctx->status = 0;
    ctx->magic = VELO_HANDLE_DEAD;
    ctx->next_reaped = g_velo_thread_tombstones;
    g_velo_thread_tombstones = ctx;
    return status;
}

static inline void* velo_mutex_create(void) {
    VeloMutexCell* c = (VeloMutexCell*)malloc(sizeof(VeloMutexCell));
    pthread_mutex_t* native = (c != NULL) ? (pthread_mutex_t*)malloc(sizeof(pthread_mutex_t)) : NULL;
    if (!native || pthread_mutex_init(native, NULL) != 0) {
        free(native);  // frees NULL harmlessly
        free(c);
        velo_fatal_msg("mutex creation failed");
    }
    c->native = (void*)native;
    c->magic = VELO_HANDLE_LIVE;
    return (void*)c;
}

static inline void velo_mutex_acquire(void* m) {
    velo_mutex_assert_live(m);
    pthread_mutex_lock((pthread_mutex_t*)((VeloMutexCell*)m)->native);
}

static inline void velo_mutex_release(void* m) {
    velo_mutex_assert_live(m);
    pthread_mutex_unlock((pthread_mutex_t*)((VeloMutexCell*)m)->native);
}

static inline void velo_mutex_destroy(void* m) {
    velo_mutex_assert_live(m);
    VeloMutexCell* c = (VeloMutexCell*)m;
    pthread_mutex_destroy((pthread_mutex_t*)c->native);
    free(c->native);
    c->magic = VELO_HANDLE_DEAD;
    c->next_reaped = g_velo_mutex_tombstones;
    g_velo_mutex_tombstones = c;
}

#endif  // §4.2 thread surface

// Persistent Heap Allocation with Memory Usage Tracking
// §4.2 (revised): the ledger is a single shared counter updated with true
// atomics — __sync_fetch_and_add (GCC, the only driver toolchain; on MinGW
// this emits native locked instructions) or _InterlockedExchangeAdd64
// (MSVC intrinsics, untested path). A per-thread ledger cannot attribute a
// cross-thread `mem.free` to the allocating thread, and a plain += would
// tear under concurrent alloc/free. malloc/free themselves were already
// thread-safe.
#if defined(_MSC_VER)
#include <intrin.h>
#define VELO_ATOMIC_ADD64(p, v) ((size_t)((unsigned long long)_InterlockedExchangeAdd64((long long volatile*)(p), (long long)(v))))
#else
#define VELO_ATOMIC_ADD64(p, v) ((size_t)((unsigned long long)__sync_fetch_and_add((long long volatile*)(p), (long long)(v))))
#endif

static size_t g_velo_heap_active = 0;

static inline void* velo_heap_alloc(size_t size, size_t count) {
    size_t total = size * count;
    size_t header_size = (sizeof(size_t) + 15) & ~((size_t)15);
    uint8_t* raw = (uint8_t*)malloc(total + header_size);
    if (!raw) {
        fprintf(stderr, "Velo Fatal Error: Out of Heap Memory!\n");
        exit(1);
    }
    *((size_t*)raw) = total;
    VELO_ATOMIC_ADD64(&g_velo_heap_active, (long long)total);
    return (void*)(raw + header_size);
}

static inline void velo_heap_free(void* ptr) {
    if (!ptr) return;
    size_t header_size = (sizeof(size_t) + 15) & ~((size_t)15);
    uint8_t* raw = ((uint8_t*)ptr) - header_size;
    size_t total = *((size_t*)raw);
    size_t prev = VELO_ATOMIC_ADD64(&g_velo_heap_active, -(long long)total);
    if (prev < total) {
        // Best-effort clamp: freeing a wild pointer can underflow the
        // diagnostic; restore it toward zero rather than letting it go
        // negative (accounting only — allocation safety is unaffected).
        VELO_ATOMIC_ADD64(&g_velo_heap_active, (long long)(total - prev));
    }
    free(raw);
}

// §4.3 hardening: byte-trio runtime wrappers. A negative byte count is a
// caller bug that the raw C trio would silently launder into a gigantic
// size_t (an instant wipe/write of huge size — UB); Velo turns it into a
// loud fatal instead. Both compilers emit these wrappers.
static inline void velo_byte_copy(void* dest, const void* src, long long count) {
    if (count < 0) {
        fprintf(stderr, "Velo Fatal Error: mem.copy got a negative byte count!\n");
        exit(1);
    }
    memcpy(dest, src, (size_t)count);
}

static inline void velo_byte_move(void* dest, const void* src, long long count) {
    if (count < 0) {
        fprintf(stderr, "Velo Fatal Error: mem.move got a negative byte count!\n");
        exit(1);
    }
    memmove(dest, src, (size_t)count);
}

static inline void velo_byte_set(void* dest, int val, long long count) {
    if (count < 0) {
        fprintf(stderr, "Velo Fatal Error: mem.set got a negative byte count!\n");
        exit(1);
    }
    memset(dest, val, (size_t)count);
}

// §4.3: realloc for persistent heap blocks that keeps the size-header
// protocol and the shared atomic ledger exact — plain C realloc can do
// neither. resizes the RAW block (header + payload) so the size word
// moves with it, then adjusts the ledger by the delta. `count == 0`
// frees and yields NULL (documented Velo semantics, like the C idiom
// realloc(p, 0)); a NULL pointer behaves like an allocation, mirroring
// C's realloc(NULL, n). A realloc on a non-heap pointer is the same
// raw-pointer UB class as `velo_heap_free` on one. OOM is fatal — the
// old block stays valid until exit, matching heap_alloc's philosophy.
// count is signed so a negative caller bug dies loudly instead of
// wrapping into a gigantic size_t.
static inline void* velo_heap_realloc(void* ptr, size_t size, long long count) {
    if (count < 0) {
        fprintf(stderr, "Velo Fatal Error: mem.realloc got a negative byte count!\n");
        exit(1);
    }
    if (!ptr) return velo_heap_alloc(size, (size_t)count);
    size_t header_size = (sizeof(size_t) + 15) & ~((size_t)15);
    uint8_t* raw = ((uint8_t*)ptr) - header_size;
    size_t old_total = *((size_t*)raw);
    size_t new_total = size * (size_t)count;
    if (new_total == 0) {
        velo_heap_free(ptr);
        return NULL;
    }
    uint8_t* nraw = (uint8_t*)realloc(raw, new_total + header_size);
    if (!nraw) {
        fprintf(stderr, "Velo Fatal Error: Out of Heap Memory!\n");
        exit(1);
    }
    *((size_t*)nraw) = new_total;
    if (new_total > old_total) {
        VELO_ATOMIC_ADD64(&g_velo_heap_active, (long long)(new_total - old_total));
    } else if (new_total < old_total) {
        VELO_ATOMIC_ADD64(&g_velo_heap_active, -(long long)(old_total - new_total));
    }
    return (void*)(nraw + header_size);
}

static inline size_t velo_heap_used(void) {
    return g_velo_heap_active;
}

// Built-in IO primitives
static inline void velo_io_println(const char* str) {
    printf("%s\n", str);
}

static inline void velo_io_print(const char* str) {
    printf("%s", str);
}

static inline void velo_io_print_char(char c) {
    putchar(c);
}


// Built-in File System primitives (sys.fs)
static inline char* velo_fs_read_file(const char* path) {
    if (!path) return NULL;
    FILE* f = fopen(path, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    if (sz < 0) {
        fclose(f);
        return NULL;
    }
    fseek(f, 0, SEEK_SET);
    char* buf = (char*)velo_heap_alloc(1, (size_t)sz + 1);
    if (!buf) {
        fclose(f);
        return NULL;
    }
    size_t read_bytes = fread(buf, 1, (size_t)sz, f);
    buf[read_bytes] = '\0';
    fclose(f);
    return buf;
}

static inline bool velo_fs_write_file(const char* path, const char* content) {
    if (!path) return false;
    FILE* f = fopen(path, "wb");
    if (!f) return false;
    if (content) {
        size_t len = strlen(content);
        if (len > 0) {
            size_t written = fwrite(content, 1, len, f);
            if (written != len) {
                fclose(f);
                return false;
            }
        }
    }
    fclose(f);
    return true;
}

static inline bool velo_fs_exists(const char* path) {
    if (!path) return false;
    FILE* f = fopen(path, "rb");
    if (f) {
        fclose(f);
        return true;
    }
    return false;
}

static inline size_t velo_fs_size(const char* path) {
    if (!path) return 0;
    FILE* f = fopen(path, "rb");
    if (!f) return 0;
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fclose(f);
    return sz > 0 ? (size_t)sz : 0;
}

static inline bool velo_fs_remove(const char* path) {
    if (!path) return false;
    return (remove(path) == 0);
}


// ============================================================================
// 5.1 String Processing Library (sys.str)
//
// Pure string helpers over NUL-terminated C strings. Every function that
// RETURNS a string (or a token array) allocates its result with
// velo_heap_alloc — the same base as velo_fs_read_file — so callers own the
// result and release it with mem.free (or let process exit reclaim it);
// heap blocks stay valid across zone { } exits, so results can outlive the
// zone they were produced in. Bool/index functions allocate nothing.
//
// Null arguments are caller bugs: each helper dies loudly instead of
// letting C strlen/strstr/strcmp walk a NULL (deterministic fatal, trade of
// the raw-pointer class — same tiering as the mem.* wrappers). Legacy
// str.len keeps its plain strlen lowering and is intentionally untouched.
//
// to_upper/to_lower are ASCII-only and locale-independent BY DESIGN: the C
// toupper/tolower tables are locale-dependent, and this project pins
// bit-for-bit cross-stage determinism.
// ============================================================================
static inline const char* velo_str_nonnull(const char* s, const char* fn) {
    if (!s) {
        fprintf(stderr, "Velo Fatal Error: %s got a null string!\n", fn);
        exit(1);
    }
    return s;
}

// One heap allocation holds the NUL-terminated copy: n bytes + terminator.
static inline char* velo_str_copy_heap(const char* src, size_t n) {
    char* out = (char*)velo_heap_alloc(1, n + 1);
    if (n > 0) memcpy(out, src, n);
    out[n] = 0;
    return out;
}

static inline bool velo_str_contains(const char* s, const char* sub) {
    return strstr(velo_str_nonnull(s, "str.contains"),
                  velo_str_nonnull(sub, "str.contains")) != NULL;
}

static inline bool velo_str_starts_with(const char* s, const char* prefix) {
    const char* a = velo_str_nonnull(s, "str.starts_with");
    const char* b = velo_str_nonnull(prefix, "str.starts_with");
    // strncmp over the prefix length: a shorter haystack stops at its NUL
    // (mismatch), an empty prefix matches anything (strncmp(_, _, 0) == 0).
    return strncmp(a, b, strlen(b)) == 0;
}

static inline bool velo_str_ends_with(const char* s, const char* suffix) {
    const char* a = velo_str_nonnull(s, "str.ends_with");
    const char* b = velo_str_nonnull(suffix, "str.ends_with");
    size_t slen = strlen(a);
    size_t flen = strlen(b);
    if (flen > slen) return false;
    return strcmp(a + (slen - flen), b) == 0;
}

// First byte offset of `needle` in `s`, or -1 when absent (i64 — a usize
// result has no room for "not found"). Empty needle found at 0, mirroring
// strstr; needle is a substring, which subsumes single-char search.
static inline i64 velo_str_index_of(const char* s, const char* needle) {
    const char* a = velo_str_nonnull(s, "str.index_of");
    const char* b = velo_str_nonnull(needle, "str.index_of");
    const char* hit = strstr(a, b);
    return hit ? (i64)(hit - a) : (i64)(-1);
}

// ASCII whitespace only (space, \t, \n, \v, \f, \r) — locale-independent,
// unlike C isspace. Always returns a fresh heap copy (even "": callers can
// mem.free either way without ownership ambiguity).
static inline char* velo_str_trim(const char* s) {
    const char* a = velo_str_nonnull(s, "str.trim");
    const char* p = a;
    while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\v' || *p == '\f' || *p == '\r') p++;
    const char* end = p + strlen(p);
    while (end > p && (end[-1] == ' ' || end[-1] == '\t' || end[-1] == '\n' ||
                       end[-1] == '\v' || end[-1] == '\f' || end[-1] == '\r')) end--;
    return velo_str_copy_heap(p, (size_t)(end - p));
}

// Replaces ALL non-overlapping occurrences left-to-right (C-style scanning,
// count pass then fill pass — allocation is exact with no over-reserve).
// An empty `from` cannot be replaced (would loop forever in any naive
// scheme): the result is a byte-identical heap copy of `s`. An empty `to`
// deletes occurrences.
static inline char* velo_str_replace(const char* s, const char* from, const char* to) {
    const char* a = velo_str_nonnull(s, "str.replace");
    const char* f = velo_str_nonnull(from, "str.replace");
    const char* t = velo_str_nonnull(to, "str.replace");
    size_t alen = strlen(a);
    size_t flen = strlen(f);
    size_t tlen = strlen(t);
    if (flen == 0) return velo_str_copy_heap(a, alen);
    size_t hits = 0;
    const char* p = a;
    const char* hit;
    while ((hit = strstr(p, f)) != NULL) {
        hits++;
        p = hit + flen;
    }
    char* out = (char*)velo_heap_alloc(1, alen - (hits * flen) + (hits * tlen) + 1);
    char* w = out;
    p = a;
    while ((hit = strstr(p, f)) != NULL) {
        size_t keep = (size_t)(hit - p);
        memcpy(w, p, keep);
        w += keep;
        if (tlen > 0) {
            memcpy(w, t, tlen);
            w += tlen;
        }
        p = hit + flen;
    }
    strcpy(w, p);
    return out;
}

static inline char* velo_str_to_upper(const char* s) {
    const char* a = velo_str_nonnull(s, "str.to_upper");
    size_t n = strlen(a);
    char* out = (char*)velo_heap_alloc(1, n + 1);
    for (size_t i = 0; i < n; i++) {
        char c = a[i];
        if (c >= 'a' && c <= 'z') c = (char)(c - 'a' + 'A');
        out[i] = c;
    }
    out[n] = 0;
    return out;
}

static inline char* velo_str_to_lower(const char* s) {
    const char* a = velo_str_nonnull(s, "str.to_lower");
    size_t n = strlen(a);
    char* out = (char*)velo_heap_alloc(1, n + 1);
    for (size_t i = 0; i < n; i++) {
        char c = a[i];
        if (c >= 'A' && c <= 'Z') c = (char)(c - 'A' + 'a');
        out[i] = c;
    }
    out[n] = 0;
    return out;
}

static inline char* velo_str_concat(const char* a, const char* b) {
    const char* x = velo_str_nonnull(a, "str.concat");
    const char* y = velo_str_nonnull(b, "str.concat");
    size_t flen = strlen(x);
    size_t tlen = strlen(y);
    char* out = (char*)velo_heap_alloc(1, flen + tlen + 1);
    memcpy(out, x, flen);
    if (tlen > 0) memcpy(out + flen, y, tlen);
    out[flen + tlen] = 0;
    return out;
}

// Python-style tokenization: delimiters SEPARATE, they do not merge — empty
// tokens are preserved ("a,,b" → "a","","b"), a trailing delimiter yields a
// trailing empty token ("a," → "a",""), and "" → one empty token. Returns a
// NULL-terminated @string array whose tokens AND pointer array live in ONE
// heap block (pointers first, token bytes behind them): mem.free(parts)
// reclaims everything exactly once and the heap ledger moves by a single
// atomic op — do NOT free an individual token (it has no header). The
// delimiter may be any length. An empty delimiter cannot split anything
// and dies loudly.
static inline const char** velo_str_split(const char* s, const char* delim) {
    const char* a = velo_str_nonnull(s, "str.split");
    const char* d = velo_str_nonnull(delim, "str.split");
    size_t dlen = strlen(d);
    if (dlen == 0) {
        fprintf(stderr, "Velo Fatal Error: str.split got an empty delimiter!\n");
        exit(1);
    }
    size_t ntok = 1;
    size_t tok_bytes = 0;
    const char* p = a;
    const char* hit;
    while ((hit = strstr(p, d)) != NULL) {
        tok_bytes += (size_t)(hit - p) + 1;
        ntok++;
        p = hit + dlen;
    }
    tok_bytes += strlen(p) + 1;
    // One block: (ntok + 1) pointers (pointer-aligned, the array slice is a
    // multiple of sizeof(char*)) followed by every token's bytes + NUL.
    size_t arr_bytes = (ntok + 1) * sizeof(char*);
    char* block = (char*)velo_heap_alloc(1, arr_bytes + tok_bytes);
    const char** parts = (const char**)block;
    char* w = block + arr_bytes;
    p = a;
    size_t k = 0;
    while ((hit = strstr(p, d)) != NULL) {
        size_t len = (size_t)(hit - p);
        parts[k] = w;
        memcpy(w, p, len);
        w[len] = 0;
        w += len + 1;
        k++;
        p = hit + dlen;
    }
    size_t len = strlen(p);
    parts[k] = w;
    memcpy(w, p, len);
    w[len] = 0;
    parts[k + 1] = NULL;
    return parts;
}


// ============================================================================
// 5.2 Dynamic Collections (shelf)
//
// ONE struct serves every element type: per-element C knowledge lives at each
// use site (the compiler casts `((T*)s->data)[i]` per element type and passes
// sizeof(elem) as esz). Payload grows in the ACTIVE arena (velo_mem_alloc):
// growth allocates a new block (capacity doubling from 4), copies, and
// continues — the arena reclaims every growth generation wholesale on
// `zone { }` exit, so a zone-lived shelf never needs a free.
//
// Elements are copied by BYTES (memcpy, esz wide) — a string element copies
// its pointer, not the characters (Velo strings are immutable C strings, so
// this is safe). Bounds/fatality tiering matches mem.*/str.*: an out-of-range
// index, an empty take, or a zero-size shell are loud deterministic fatals,
// never silent UB.
//
// take() returns a pointer INTO the payload, dereferenced by the compiler in
// the same expression — valid until the NEXT growth (a put may relocate data;
// take results are not put()'s argument since then, the compiler evaluates
// take results before the relocation).
// ============================================================================
typedef struct VeloShelf {
    void*  data;  // element storage (allocated in the active arena on growth)
    size_t len;   // element count
    size_t cap;   // element capacity
    size_t esz;   // element size in bytes (established at the first put)
} VeloShelf;

static inline void velo_shelf_oob(size_t idx, size_t len) {
    fprintf(stderr, "Velo Fatal Error: shelf index out of bounds: %llu (len %llu)!\n",
            (unsigned long long)idx, (unsigned long long)len);
    exit(1);
}

// Bounds-checked read slot (caller derefs immediately).
static inline void* velo_shelf_get(const VeloShelf* s, size_t idx) {
    if (idx >= s->len) velo_shelf_oob(idx, s->len);
    return (void*)((char*)s->data + idx * s->esz);
}

// Growth for one more element (put/insert): double the capacity, copy the
// live rows into fresh arena storage (put may relocate the payload — the
// take/remove_at stashes must be consumed before the next growth).
static inline void velo_shelf_reserve(VeloShelf* s) {
    if (s->data == NULL || s->len == s->cap) {
        size_t new_cap = s->cap ? s->cap : 4;
        while (new_cap < s->len + 1) new_cap *= 2;
        void* next = velo_mem_alloc(s->esz, new_cap);
        if (s->len > 0) memcpy(next, s->data, s->len * s->esz);
        s->data = next;
        s->cap = new_cap;
    }
}

static inline void velo_shelf_put(VeloShelf* s, const void* val, size_t esz) {
    if (esz == 0) {
        fprintf(stderr, "Velo Fatal Error: shelf put of a zero-size element!\n");
        exit(1);
    }
    if (s->esz == 0) s->esz = esz;
    else if (s->esz != esz) {
        fprintf(stderr, "Velo Fatal Error: shelf element size mismatch: %llu vs %llu!\n",
                (unsigned long long)esz, (unsigned long long)s->esz);
        exit(1);
    }
    velo_shelf_reserve(s);
    memcpy((char*)s->data + s->len * esz, val, esz);
    s->len += 1;
}

// Insert `val` at `idx`, shifting the tail right; idx == len appends (the
// nest way to grow), idx > len is a loud fatal matching the bounds tier.
static inline void velo_shelf_insert(VeloShelf* s, size_t idx, const void* val, size_t esz) {
    if (esz == 0) {
        fprintf(stderr, "Velo Fatal Error: shelf put of a zero-size element!\n");
        exit(1);
    }
    if (s->esz == 0) s->esz = esz;
    else if (s->esz != esz) {
        fprintf(stderr, "Velo Fatal Error: shelf element size mismatch: %llu vs %llu!\n",
                (unsigned long long)esz, (unsigned long long)s->esz);
        exit(1);
    }
    if (idx > s->len) {
        fprintf(stderr, "Velo Fatal Error: shelf insert index out of bounds: %llu (len %llu)!\n",
                (unsigned long long)idx, (unsigned long long)s->len);
        exit(1);
    }
    velo_shelf_reserve(s);
    char* base = (char*)s->data;
    memmove(base + (idx + 1) * s->esz, base + idx * s->esz, (s->len - idx) * s->esz);
    memcpy(base + idx * s->esz, val, esz);
    s->len += 1;
}

// Remove the element at `idx` and return it BY VALUE: the victim is
// stash-copied to fresh arena storage BEFORE the tail shift (a take-style
// pointer into the hole would read the shifted neighbor instead). Returns a
// pointer to the stash — deref it now, exactly like take().
static inline void* velo_shelf_remove_at(VeloShelf* s, size_t idx) {
    if ((s->len == 0) || (idx >= s->len)) {
        fprintf(stderr, "Velo Fatal Error: shelf remove index out of bounds: %llu (len %llu)!\n",
                (unsigned long long)idx, (unsigned long long)s->len);
        exit(1);
    }
    char* cell = (char*)s->data + idx * s->esz;
    void* stash = velo_mem_alloc(s->esz, 1);
    memcpy(stash, cell, s->esz);
    memmove(cell, cell + s->esz, (s->len - idx - 1) * s->esz);
    s->len -= 1;
    return stash;
}

// Bounds-checked write slot (memcpy esz bytes from val).
static inline void velo_shelf_set(VeloShelf* s, size_t idx, const void* val, size_t esz) {
    if (idx >= s->len) velo_shelf_oob(idx, s->len);
    memcpy((char*)s->data + idx * s->esz, val, esz);
}

// ============================================================================
// 5.2 (slice 3) — the vector-operations surface: sorted() / insert /
// remove_at. The comparators are macro-generated per element TOKEN (the
// wrapper names use the Velo element spelling so both compilers emit the
// same call: velo_shelf_sorted_i32 / velo_shelf_sorted_f64 /
// velo_shelf_sorted_string). sorted() copies to fresh arena storage — the
// receiver is untouched, so it is legal on a let shelf. insert/remove_at
// mutate (the compilers enforce the mut doctrine) and share take's loud
// deterministic fatal tiering.
// ============================================================================
#define VELO_SHELF_CMP_SCALAR(suffix, cty) \
    static int velo_shelf_cmp_##suffix(const void* a, const void* b) { \
        cty x = *(const cty*)a; cty y = *(const cty*)b; \
        return (x > y) - (x < y); \
    }
VELO_SHELF_CMP_SCALAR(i8, i8)
VELO_SHELF_CMP_SCALAR(i16, i16)
VELO_SHELF_CMP_SCALAR(i32, i32)
VELO_SHELF_CMP_SCALAR(i64, i64)
VELO_SHELF_CMP_SCALAR(u8, u8)
VELO_SHELF_CMP_SCALAR(u16, u16)
VELO_SHELF_CMP_SCALAR(u32, u32)
VELO_SHELF_CMP_SCALAR(u64, u64)
VELO_SHELF_CMP_SCALAR(usize, usize)
VELO_SHELF_CMP_SCALAR(isize, isize)
VELO_SHELF_CMP_SCALAR(f32, f32)
VELO_SHELF_CMP_SCALAR(f64, f64)
#undef VELO_SHELF_CMP_SCALAR

// Strings sort ascending by strcmp; equal pointers short-circuit and NULLs
// sort before everything. (f32/f64 rows sort with the plain compares — a NaN
// reports 0 forever, so its placement is unspecified, documented policy.)
static int velo_shelf_cmp_string(const void* a, const void* b) {
    const char* x = *(const char* const*)a;
    const char* y = *(const char* const*)b;
    if (x == y) return 0;
    if (x == NULL) return -1;
    if (y == NULL) return 1;
    return strcmp(x, y);
}

// Copy-and-sort engine: fresh backing storage (never the receiver's row).
static inline VeloShelf velo_shelf_sorted_copy(const VeloShelf* s, int (*cmp)(const void*, const void*)) {
    VeloShelf out = {0};
    out.esz = s->esz;
    out.len = s->len;
    out.cap = s->len;
    if (s->len > 0) {
        out.data = velo_mem_alloc(s->esz, s->len);
        memcpy(out.data, s->data, s->len * s->esz);
        qsort(out.data, s->len, s->esz, cmp);
    }
    return out;
}

#define VELO_SHELF_SORT(suffix) \
    static inline VeloShelf velo_shelf_sorted_##suffix(const VeloShelf* s) { \
        return velo_shelf_sorted_copy(s, velo_shelf_cmp_##suffix); \
    }
VELO_SHELF_SORT(i8)
VELO_SHELF_SORT(i16)
VELO_SHELF_SORT(i32)
VELO_SHELF_SORT(i64)
VELO_SHELF_SORT(u8)
VELO_SHELF_SORT(u16)
VELO_SHELF_SORT(u32)
VELO_SHELF_SORT(u64)
VELO_SHELF_SORT(usize)
VELO_SHELF_SORT(isize)
VELO_SHELF_SORT(f32)
VELO_SHELF_SORT(f64)
VELO_SHELF_SORT(string)
#undef VELO_SHELF_SORT

// Reversed COPY of a shelf: fresh arena backing, receiver untouched, no
// element-family restriction (a byte-swap orders nothing — every family
// ships, dyn boxes keep their tags).
static inline VeloShelf velo_shelf_reversed(const VeloShelf* s) {
    VeloShelf out = {0};
    out.esz = s->esz;
    out.len = s->len;
    out.cap = s->len;
    if (s->len > 0) {
        out.data = velo_mem_alloc(s->esz, s->len);
        const char* src = (const char*)s->data;
        char* dst = (char*)out.data;
        for (size_t i = 0; i < s->len; i++) {
            memcpy(dst + (s->len - 1 - i) * s->esz, src + i * s->esz, s->esz);
        }
    }
    return out;
}

// Pop the last element; returns a pointer INTO the payload (deref now).
// An empty shelf take is a loud fatal (same tiering as the byte helpers).
static inline void* velo_shelf_take(VeloShelf* s) {
    if (s->len == 0) {
        fprintf(stderr, "Velo Fatal Error: shelf take from an empty shelf!\n");
        exit(1);
    }
    s->len -= 1;
    return (void*)((char*)s->data + s->len * s->esz);
}

// ============================================================================
// 5.2 (slice 2) — shelf[dyn] tagged-box mixed shelves.
//
// A `shelf[dyn]` is a normal VeloShelf whose element size is sizeof(VeloDyn):
// every element is a tagged box. The compilers box at literal/put/set sites
// (by the value's Velo type) and unbox at `as`-cast reads. The tag set:
// one boxed-int tag (every Velo integer width boxes into I64 — u64 values
// above 2^63 wrap), F64, BOOL, STR (pointer copy — immutable C strings),
// PTR (any @T, unbox shape unchecked — C-pointer trust semantics), CHILD
// (a nested shelf header copied BY VALUE — snapshot doctrine applies).
//
// Plain struct values are NOT boxable: the compilers reject them at compile
// time (the runtime cannot learn their size later); use a @T pointer element.
// Unbox tag mismatches are loud deterministic fatals, and the wording lives
// here so both compiler stages cannot diverge on it.
// ============================================================================
typedef enum {
    VELO_DYN_NONE = 0,
    VELO_DYN_I64 = 1,
    VELO_DYN_F64 = 2,
    VELO_DYN_BOOL = 3,
    VELO_DYN_STR = 4,
    VELO_DYN_PTR = 5,
    VELO_DYN_CHILD = 6
} VeloDynTag;

typedef struct VeloDyn {
    uint8_t tag;
    union { int64_t i64; double f64; bool b; const char* s; void* p; VeloShelf child; } as;
} VeloDyn;

static inline const char* velo_dyn_tag_name(uint8_t tag) {
    switch (tag) {
        case VELO_DYN_I64:   return "int";
        case VELO_DYN_F64:   return "float";
        case VELO_DYN_BOOL:  return "bool";
        case VELO_DYN_STR:   return "string";
        case VELO_DYN_PTR:   return "pointer";
        case VELO_DYN_CHILD: return "shelf";
        default:             return "none";
    }
}

// Unbox gate: the box must carry the requested family (int widths read off
// the I64 box; f32/f64 off F64; child shelves come back as value copies).
// A wrong tag is a loud deterministic fatal (same tier as the shelf bounds).
static inline void velo_dyn_expect(VeloDyn v, uint8_t tag, const char* family) {
    if (v.tag != tag) {
        fprintf(stderr, "Velo Fatal Error: shelf[dyn] unbox: expected %s, found %s!\n",
                family, velo_dyn_tag_name(v.tag));
        exit(1);
    }
}


// --- stdout capture support (structured diagnostics for 'velo check --json') ---
// Redirects fd 1 into a file, isolating diagnostics from the JSON stream on
// stdout. The saved descriptor is not explicitly closed (process-exit reclaims).
#ifdef _WIN32
#include <io.h>
#define VELO_FILENO_(f) _fileno(f)
#define VELO_DUP_(fd) _dup(fd)
#define VELO_DUP2_(a, b) _dup2(a, b)
#else
#include <unistd.h>
#define VELO_FILENO_(f) fileno(f)
#define VELO_DUP_(fd) dup(fd)
#define VELO_DUP2_(a, b) dup2(a, b)
#endif

static FILE* g_velo_capture_file = NULL;
static int   g_velo_backup_fd    = -1;

static inline int velo_capture_begin(const char* path) {
    if (g_velo_capture_file) return 0;
    g_velo_capture_file = fopen(path, "w");
    if (!g_velo_capture_file) return -1;
    g_velo_backup_fd = VELO_DUP_(VELO_FILENO_(stdout));
    if (g_velo_backup_fd < 0) {
        fclose(g_velo_capture_file);
        g_velo_capture_file = NULL;
        return -2;
    }
    VELO_DUP2_(VELO_FILENO_(g_velo_capture_file), VELO_FILENO_(stdout));
    return 0;
}

static inline int velo_capture_end(void) {
    if (!g_velo_capture_file) return -1;
    fflush(stdout);
    if (g_velo_backup_fd >= 0) {
        VELO_DUP2_(g_velo_backup_fd, VELO_FILENO_(stdout));
        g_velo_backup_fd = -1;
    }
    fclose(g_velo_capture_file);
    g_velo_capture_file = NULL;
    return 0;
}

#endif // VELO_RUNTIME_H
