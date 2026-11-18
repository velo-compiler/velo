#ifndef VELO_RUNTIME_H
#define VELO_RUNTIME_H

#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif

// 5.5 High-Resolution Clock & Timing (sys.time): the POSIX clock surface
// (clock_gettime / CLOCK_MONOTONIC / nanosleep) is only declared by <time.h>
// under POSIX feature-test flags, and -std=c99 withholds the defaults — so
// the flags are requested here, BEFORE the first system include (glibc and
// friends chain <time.h> through stdio as well). 5.4 bumps 199309L to
// 200112L (strict superset — the clock APIs stay declared) so that
// setenv joins the surface. Windows keeps its own branches below, untouched
// by these flags.
#if !defined(_WIN32) && !defined(_POSIX_C_SOURCE)
#define _POSIX_C_SOURCE 200112L
#endif

// Phase 70 / Task 70.2: rand_s (the CRT's CSPRNG) is declared by <stdlib.h> only
// when this is defined BEFORE the first system include. It replaces the direct
// advapi32 SystemFunction036 binding that std/crypto/rand.vl used to carry.
// Confirmed available on the maintenance toolchain before being relied on.
//
// The define is necessary but not sufficient, and the gap was found by
// tests/test_runtime_zone.py rather than by the compiler: that harness includes
// <stdlib.h> in its own prelude BEFORE this header, so by the time we get here
// the define is too late to affect the declaration and `rand_s` was implicitly
// declared. Any translation unit that includes stdlib.h first hits the same
// thing -- the guard is in the wrong place to be relied on alone.
//
// So the prototype is also declared explicitly below and every use of rand_s
// goes through it. Measured: with the dllimport attribute present the
// redeclaration is accepted in both orders with no diagnostic, while omitting it
// produces -Wattributes ("redeclared without dllimport attribute") when the
// system declaration came first.
#if !defined(_CRT_RAND_S)
#define _CRT_RAND_S
#endif

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stddef.h>
#include <stdarg.h>
#include <time.h>
#include <setjmp.h>
// 5.3 Math Library: sys.math lowers directly onto C99 libm (sqrt/pow/cbrt
// shipped in slice 1); no -lm is needed — MinGW ucrt64 satisfies these via
// libmingwex/msvcrt, which the driver links by default.
#include <math.h>
// 5.4 (sys.fs): struct stat + S_ISDIR/S_ISREG classify paths for
// is_dir/is_file; direct.h (Windows only) declares _mkdir for create_dir.
#include <sys/stat.h>
#ifndef S_ISDIR
#define S_ISDIR(mode) (((mode) & S_IFMT) == S_IFDIR)
#endif
#ifndef S_ISREG
#define S_ISREG(mode) (((mode) & S_IFMT) == S_IFREG)
#endif
#ifndef S_IWUSR
#if defined(_S_IWRITE)
#define S_IWUSR _S_IWRITE
#elif defined(S_IWRITE)
#define S_IWUSR S_IWRITE
#else
#define S_IWUSR 0200
#endif
#endif
#if defined(_WIN32)
#include <direct.h>
// 5.4 (S3): _findfirst/_findnext/_findclose + struct _finddata_t for the
// directory listing helper.
#include <io.h>
#pragma comment(lib, "ws2_32.lib")
#else
// 5.4 (S3): POSIX directory iteration (declared under the 200112L flags).
#include <dirent.h>
// Phase 70 / Task 70.2: the BSD socket surface. `socket`, `bind`, `listen`,
// `accept`, `recv`, `send`, `recvfrom`, `sendto`, `setsockopt`, `connect` and
// `inet_addr` are declared by these three headers under the SAME names the
// std library already uses, so the emitted extern declarations agree with the
// declarations here and no per-platform socket module is needed for them.
// Only WSAStartup/WSACleanup/closesocket/ioctlsocket are Windows-specific.
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
// Phase 70 / Task 70.2: _NSGetExecutablePath is the only supported way to ask
// a macOS process where its own binary lives; /proc/self/exe does not exist there.
#if defined(__APPLE__)
#include <mach-o/dyld.h>
#endif
#endif

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
// 128-bit SIMD Vector Types (Task 3.1: f32x4, i32x4)
// ============================================================================
#if defined(_MSC_VER)
#include <immintrin.h>
typedef __m128  f32x4;
typedef __m128i i32x4;

static inline f32x4 velo_f32x4(float x, float y, float z, float w) {
    return _mm_setr_ps(x, y, z, w);
}

static inline f32x4 velo_f32x4_splat(float val) {
    return _mm_set1_ps(val);
}

static inline i32x4 velo_i32x4(int32_t x, int32_t y, int32_t z, int32_t w) {
    return _mm_setr_epi32(x, y, z, w);
}

static inline i32x4 velo_i32x4_splat(int32_t val) {
    return _mm_set1_epi32(val);
}

static inline f32x4 velo_f32x4_add(f32x4 a, f32x4 b) { return _mm_add_ps(a, b); }
static inline f32x4 velo_f32x4_sub(f32x4 a, f32x4 b) { return _mm_sub_ps(a, b); }
static inline f32x4 velo_f32x4_mul(f32x4 a, f32x4 b) { return _mm_mul_ps(a, b); }
static inline f32x4 velo_f32x4_div(f32x4 a, f32x4 b) { return _mm_div_ps(a, b); }
static inline f32x4 velo_f32x4_neg(f32x4 a) { return _mm_sub_ps(_mm_setzero_ps(), a); }

static inline i32x4 velo_i32x4_add(i32x4 a, i32x4 b) { return _mm_add_epi32(a, b); }
static inline i32x4 velo_i32x4_sub(i32x4 a, i32x4 b) { return _mm_sub_epi32(a, b); }
static inline i32x4 velo_i32x4_mul(i32x4 a, i32x4 b) { return _mm_mullo_epi32(a, b); }
static inline i32x4 velo_i32x4_neg(i32x4 a) { return _mm_sub_epi32(_mm_setzero_si128(), a); }

static inline bool velo_f32x4_eq(f32x4 a, f32x4 b) {
    return _mm_movemask_ps(_mm_cmpeq_ps(a, b)) == 0x0F;
}
static inline bool velo_f32x4_neq(f32x4 a, f32x4 b) {
    return !velo_f32x4_eq(a, b);
}

static inline bool velo_i32x4_eq(i32x4 a, i32x4 b) {
    return _mm_movemask_epi8(_mm_cmpeq_epi32(a, b)) == 0xFFFF;
}
static inline bool velo_i32x4_neq(i32x4 a, i32x4 b) {
    return !velo_i32x4_eq(a, b);
}

static inline float velo_f32x4_get(f32x4 v, int32_t lane) {
    union { f32x4 vec; float arr[4]; } u;
    u.vec = v;
    return u.arr[lane & 3];
}

static inline int32_t velo_i32x4_get(i32x4 v, int32_t lane) {
    union { i32x4 vec; int32_t arr[4]; } u;
    u.vec = v;
    return u.arr[lane & 3];
}

// 3.3 High-Performance SIMD Operations (sys.simd)
static inline float velo_simd_dot(f32x4 a, f32x4 b) {
    __m128 m = _mm_mul_ps(a, b);
    __m128 shuf = _mm_shuffle_ps(m, m, _MM_SHUFFLE(2, 3, 0, 1));
    __m128 sums = _mm_add_ps(m, shuf);
    shuf = _mm_movehl_ps(shuf, sums);
    sums = _mm_add_ss(sums, shuf);
    return _mm_cvtss_f32(sums);
}
static inline f32x4 velo_simd_sqrt_f32x4(f32x4 a) { return _mm_sqrt_ps(a); }
static inline f32x4 velo_simd_min_f32x4(f32x4 a, f32x4 b) { return _mm_min_ps(a, b); }
static inline f32x4 velo_simd_max_f32x4(f32x4 a, f32x4 b) { return _mm_max_ps(a, b); }
static inline i32x4 velo_simd_min_i32x4(i32x4 a, i32x4 b) {
    union { i32x4 vec; int32_t arr[4]; } ua, ub, ur;
    ua.vec = a; ub.vec = b;
    for (int i = 0; i < 4; ++i) ur.arr[i] = ua.arr[i] < ub.arr[i] ? ua.arr[i] : ub.arr[i];
    return ur.vec;
}
static inline i32x4 velo_simd_max_i32x4(i32x4 a, i32x4 b) {
    union { i32x4 vec; int32_t arr[4]; } ua, ub, ur;
    ua.vec = a; ub.vec = b;
    for (int i = 0; i < 4; ++i) ur.arr[i] = ua.arr[i] > ub.arr[i] ? ua.arr[i] : ub.arr[i];
    return ur.vec;
}
#else
typedef float   f32x4 __attribute__((vector_size(16), aligned(16)));
typedef int32_t i32x4 __attribute__((vector_size(16), aligned(16)));

static inline f32x4 velo_f32x4(float x, float y, float z, float w) {
    return (f32x4){x, y, z, w};
}

static inline f32x4 velo_f32x4_splat(float val) {
    return (f32x4){val, val, val, val};
}

static inline i32x4 velo_i32x4(int32_t x, int32_t y, int32_t z, int32_t w) {
    return (i32x4){x, y, z, w};
}

static inline i32x4 velo_i32x4_splat(int32_t val) {
    return (i32x4){val, val, val, val};
}

static inline f32x4 velo_f32x4_add(f32x4 a, f32x4 b) { return a + b; }
static inline f32x4 velo_f32x4_sub(f32x4 a, f32x4 b) { return a - b; }
static inline f32x4 velo_f32x4_mul(f32x4 a, f32x4 b) { return a * b; }
static inline f32x4 velo_f32x4_div(f32x4 a, f32x4 b) { return a / b; }
static inline f32x4 velo_f32x4_neg(f32x4 a) { return -a; }

static inline i32x4 velo_i32x4_add(i32x4 a, i32x4 b) { return a + b; }
static inline i32x4 velo_i32x4_sub(i32x4 a, i32x4 b) { return a - b; }
static inline i32x4 velo_i32x4_mul(i32x4 a, i32x4 b) { return a * b; }
static inline i32x4 velo_i32x4_neg(i32x4 a) { return -a; }

static inline bool velo_f32x4_eq(f32x4 a, f32x4 b) {
    union { f32x4 vec; float arr[4]; } ua, ub;
    ua.vec = a; ub.vec = b;
    return ua.arr[0] == ub.arr[0] && ua.arr[1] == ub.arr[1] &&
           ua.arr[2] == ub.arr[2] && ua.arr[3] == ub.arr[3];
}
static inline bool velo_f32x4_neq(f32x4 a, f32x4 b) {
    return !velo_f32x4_eq(a, b);
}

static inline bool velo_i32x4_eq(i32x4 a, i32x4 b) {
    union { i32x4 vec; int32_t arr[4]; } ua, ub;
    ua.vec = a; ub.vec = b;
    return ua.arr[0] == ub.arr[0] && ua.arr[1] == ub.arr[1] &&
           ua.arr[2] == ub.arr[2] && ua.arr[3] == ub.arr[3];
}
static inline bool velo_i32x4_neq(i32x4 a, i32x4 b) {
    return !velo_i32x4_eq(a, b);
}

static inline float velo_f32x4_get(f32x4 v, int32_t lane) {
    union { f32x4 vec; float arr[4]; } u;
    u.vec = v;
    return u.arr[lane & 3];
}

static inline int32_t velo_i32x4_get(i32x4 v, int32_t lane) {
    union { i32x4 vec; int32_t arr[4]; } u;
    u.vec = v;
    return u.arr[lane & 3];
}

// 3.3 High-Performance SIMD Operations (sys.simd)
static inline float velo_simd_dot(f32x4 a, f32x4 b) {
    f32x4 m = a * b;
    return (m[0] + m[1]) + (m[2] + m[3]);
}
static inline f32x4 velo_simd_sqrt_f32x4(f32x4 a) {
    return (f32x4){ sqrtf(a[0]), sqrtf(a[1]), sqrtf(a[2]), sqrtf(a[3]) };
}
static inline f32x4 velo_simd_min_f32x4(f32x4 a, f32x4 b) {
    return (f32x4){
        a[0] < b[0] ? a[0] : b[0],
        a[1] < b[1] ? a[1] : b[1],
        a[2] < b[2] ? a[2] : b[2],
        a[3] < b[3] ? a[3] : b[3]
    };
}
static inline f32x4 velo_simd_max_f32x4(f32x4 a, f32x4 b) {
    return (f32x4){
        a[0] > b[0] ? a[0] : b[0],
        a[1] > b[1] ? a[1] : b[1],
        a[2] > b[2] ? a[2] : b[2],
        a[3] > b[3] ? a[3] : b[3]
    };
}
static inline i32x4 velo_simd_min_i32x4(i32x4 a, i32x4 b) {
    return (i32x4){
        a[0] < b[0] ? a[0] : b[0],
        a[1] < b[1] ? a[1] : b[1],
        a[2] < b[2] ? a[2] : b[2],
        a[3] < b[3] ? a[3] : b[3]
    };
}
static inline i32x4 velo_simd_max_i32x4(i32x4 a, i32x4 b) {
    return (i32x4){
        a[0] > b[0] ? a[0] : b[0],
        a[1] > b[1] ? a[1] : b[1],
        a[2] > b[2] ? a[2] : b[2],
        a[3] > b[3] ? a[3] : b[3]
    };
}
#endif

// ============================================================================
// Safe mixed signed vs unsigned integer comparisons (Bug 4.2)
// Prevents C integer promotion bugs where signed operands are converted to
// unsigned, causing e.g. (-1 < 1u) to evaluate to false or (-1 == UINT32_MAX)
// to evaluate to true.
// ============================================================================
static inline bool velo_cmp_eq_s_u(int64_t a, uint64_t b) { return (a >= 0) && ((uint64_t)a == b); }
static inline bool velo_cmp_ne_s_u(int64_t a, uint64_t b) { return (a < 0) || ((uint64_t)a != b); }
static inline bool velo_cmp_lt_s_u(int64_t a, uint64_t b) { return (a < 0) || ((uint64_t)a < b); }
static inline bool velo_cmp_le_s_u(int64_t a, uint64_t b) { return (a < 0) || ((uint64_t)a <= b); }
static inline bool velo_cmp_gt_s_u(int64_t a, uint64_t b) { return (a > 0) && ((uint64_t)a > b); }
static inline bool velo_cmp_ge_s_u(int64_t a, uint64_t b) { return (a >= 0) && ((uint64_t)a >= b); }

static inline bool velo_cmp_eq_u_s(uint64_t a, int64_t b) { return (b >= 0) && (a == (uint64_t)b); }
static inline bool velo_cmp_ne_u_s(uint64_t a, int64_t b) { return (b < 0) || (a != (uint64_t)b); }
static inline bool velo_cmp_lt_u_s(uint64_t a, int64_t b) { return (b > 0) && (a < (uint64_t)b); }
static inline bool velo_cmp_le_u_s(uint64_t a, int64_t b) { return (b >= 0) && (a <= (uint64_t)b); }
static inline bool velo_cmp_gt_u_s(uint64_t a, int64_t b) { return (b < 0) || (a > (uint64_t)b); }
static inline bool velo_cmp_ge_u_s(uint64_t a, int64_t b) { return (b <= 0) || (a >= (uint64_t)b); }

// ============================================================================
// §4.1 Extensible Allocator Architecture + §4.2 Multithreaded Memory Safety
//
// Allocation model (in allocation-cost order, all O(1)):
//   * Active zone arena  — bump region produced by `zone { ... }` / sized
//     `zone <bytes> { ... }` blocks and by `mem.alloc(...)` calls.
//   * Persistent heap    — malloc-backed, tracked (`mem.heap_alloc` / free).
//
// OOM POLICY: allocation is FAIL-STOP. An unsatisfiable request prints
// `Velo Fatal Error: ...` to stderr and calls exit(1); no allocation returns
// a NULL that a caller is expected to test, because the `mem.*` intrinsics
// are typed to return @T/@u8 rather than ?@T (there is nothing to test with).
// Consequences for every function in this section:
//   * Allocate first, publish second — never store into a pointer whose
//     allocation was not checked (see velo_zone_enter: the struct is checked
//     before either the pool copy or the z->base write).
//   * Capacity tests guard the subtraction: test `offset <= cap` BEFORE
//     `cap - offset`, so a corrupted watermark cannot underflow the test and
//     hand out a pointer past the buffer.
//   * Defensive paths reset to a known-valid state (empty arena) rather than
//     guessing a rewind target — a wrong watermark means caller bookkeeping
//     is already untrustworthy, so it must surface rather than be smoothed
//     over (see velo_zone_pop's out-of-range branch).
// The policy is documented for users in SPECIFICATION.md §5.7 and SECURITY.md
// § Out-of-Memory Policy; tests/test_runtime_zone.py exercises every fatal
// site with deterministic fail-injection.
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
typedef struct VeloZoneChunk {
    struct VeloZoneChunk* next;
    uint8_t* base;
    size_t   cap;
    size_t   offset;
} VeloZoneChunk;

#define VELO_ZONE_WM_INLINE 32

typedef struct VeloZoneWatermark {
    size_t         primary_offset;
    VeloZoneChunk* chunk;
    size_t         chunk_offset;
} VeloZoneWatermark;

typedef struct VeloZoneArena {
    uint8_t*           base;      // start of the primary bump region
    size_t             cap;       // usable primary capacity in bytes
    size_t             offset;    // primary bump watermark (== allocated bytes in primary block)
    int                can_grow;  // 1 = dynamic secondary chunk spilling fallback; 0 = fixed budget
    VeloZoneChunk*     chunks;    // secondary linked chunks allocated when primary overflows
    VeloZoneWatermark* wm_heap;   // extra heap capacity when wm_count > VELO_ZONE_WM_INLINE
    size_t             wm_count;  // active nested watermarks count
    size_t             wm_cap;    // heap capacity in entries
    VeloZoneWatermark  wm_inline[VELO_ZONE_WM_INLINE]; // inline stack for fast zero-alloc push/pop
} VeloZoneArena;

static inline VeloZoneChunk* velo_zone_new_chunk(VeloZoneArena* z, size_t min_bytes) {
    size_t chunk_cap = 8 * 1024 * 1024; // 8 MB standard secondary chunk
    if (z->cap < chunk_cap && z->cap >= 65536) {
        chunk_cap = z->cap;
    }
    if (min_bytes > chunk_cap) {
        chunk_cap = min_bytes;
    }
    VeloZoneChunk* c = (VeloZoneChunk*)malloc(sizeof(VeloZoneChunk));
    uint8_t* buf = (uint8_t*)malloc(chunk_cap);
    if (!c || !buf) {
        fprintf(stderr, "Velo Fatal Error: Zone Arena Chunk Spilling allocation failed (%llu bytes)!\n",
                (unsigned long long)chunk_cap);
        exit(1);
    }
    c->next = z->chunks;
    c->base = buf;
    c->cap = chunk_cap;
    c->offset = 0;
    z->chunks = c;
    return c;
}

static inline void velo_zone_free_chunks(VeloZoneArena* z) {
    if (!z) return;
    VeloZoneChunk* cur = z->chunks;
    while (cur) {
        VeloZoneChunk* next = cur->next;
        if (cur->base) {
            free(cur->base);
            cur->base = NULL;
        }
        free(cur);
        cur = next;
    }
    z->chunks = NULL;
}

#define VELO_ZONE_BUFFER_SIZE (64 * 1024 * 1024)

#define VELO_ZONE_POOL_MAX 32

// §4.2 thread-local storage shim: both compilers emit C compiled with
// `-std=c99`, where the C11 keyword `_Thread_local` is unavailable. GCC and
// Clang still accept the GNU `__thread` extension; MSVC uses
// `__declspec(thread)`.
#if defined(_MSC_VER)
#define VELO_TLS __declspec(thread)
#define VELO_ALIGNED(n) __declspec(align(n))
#else
#define VELO_TLS __thread
#define VELO_ALIGNED(n) __attribute__((aligned(n)))
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
    z->can_grow = 1;
    z->chunks = NULL;
    z->wm_heap = NULL;
    z->wm_count = 0;
    z->wm_cap = 0;
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
    VeloZoneArena* z = velo_zone_active();
    VeloZoneWatermark wm;
    wm.primary_offset = z->offset;
    wm.chunk = z->chunks;
    wm.chunk_offset = z->chunks ? z->chunks->offset : 0;

    if (z->wm_count < VELO_ZONE_WM_INLINE) {
        z->wm_inline[z->wm_count] = wm;
    } else {
        size_t heap_idx = z->wm_count - VELO_ZONE_WM_INLINE;
        if (heap_idx >= z->wm_cap) {
            size_t new_cap = z->wm_cap == 0 ? 32 : z->wm_cap * 2;
            // Task 65.4: the doubling must not wrap. A wrapped (small) new_cap
            // would under-allocate the array and the store below would write
            // past it, so treat overflow like OOM: loud, fatal, no write.
            if (new_cap < z->wm_cap || new_cap > SIZE_MAX / sizeof(VeloZoneWatermark)) {
                fprintf(stderr, "Velo Fatal Error: Zone Arena Watermark Stack OOM!\n");
                exit(1);
            }
            VeloZoneWatermark* new_heap = (VeloZoneWatermark*)realloc(z->wm_heap, new_cap * sizeof(VeloZoneWatermark));
            if (!new_heap) {
                fprintf(stderr, "Velo Fatal Error: Zone Arena Watermark Stack OOM!\n");
                exit(1);
            }
            z->wm_heap = new_heap;
            z->wm_cap = new_cap;
        }
        z->wm_heap[heap_idx] = wm;
    }
    z->wm_count++;
    return z->wm_count;
}

static inline void velo_zone_pop(size_t watermark) {
    VeloZoneArena* z = velo_zone_active();
    if (watermark > 0 && watermark <= z->wm_count) {
        size_t target_idx = watermark - 1;
        VeloZoneWatermark wm = (target_idx < VELO_ZONE_WM_INLINE)
            ? z->wm_inline[target_idx]
            : z->wm_heap[target_idx - VELO_ZONE_WM_INLINE];
        z->wm_count = target_idx;

        VeloZoneChunk* cur = z->chunks;
        while (cur && cur != wm.chunk) {
            VeloZoneChunk* next = cur->next;
            if (cur->base) {
                free(cur->base);
                cur->base = NULL;
            }
            free(cur);
            cur = next;
        }
        z->chunks = wm.chunk;
        if (z->chunks) {
            z->chunks->offset = wm.chunk_offset;
        }
        z->offset = wm.primary_offset;
    } else {
        // Out-of-range watermark (0, or above wm_count): a defensive reset, not
        // a partial rewind. `watermark` is a 1-based watermark INDEX, so it
        // must never be stored as a byte offset — doing so leaves offset > cap
        // and makes the capacity check in velo_mem_alloc underflow. Dropping
        // the spilled chunks and rewinding to empty is always a valid state.
        velo_zone_free_chunks(z);
        z->offset = 0;
        if (z->wm_heap) {
            free(z->wm_heap);
            z->wm_heap = NULL;
        }
        z->wm_count = 0;
        z->wm_cap = 0;
    }
}

static inline size_t velo_arena_total_used(VeloZoneArena* a) {
    if (!a) return 0;
    size_t total = a->offset;
    VeloZoneChunk* cur = a->chunks;
    while (cur) {
        total += cur->offset;
        cur = cur->next;
    }
    return total;
}

static inline size_t velo_mem_used(void) {
    return velo_arena_total_used(velo_zone_active());
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
    if (bytes > SIZE_MAX - 31) {
        fprintf(stderr, "Velo Fatal Error: Allocation size overflow (%llu bytes)!\n",
                (unsigned long long)bytes);
        exit(1);
    }
    VeloZoneArena* prev = velo_zone_active();  // §4.2: per-thread active state
    VeloZoneArena* z = (VeloZoneArena*)malloc(sizeof(VeloZoneArena));
    if (!z) {
        fprintf(stderr, "Velo Fatal Error: Zone Arena allocation failed (%llu bytes)!\n",
                (unsigned long long)bytes);
        exit(1);
    }
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
    z->can_grow = 0; // sized zone <bytes> acts as a fixed-budget scratch arena
    z->chunks = NULL;
    z->wm_heap = NULL;
    z->wm_count = 0;
    z->wm_cap = 0;
    g_velo_zone_tls_active = z;
    return prev;
}

// Exits a zone block: returns the active arena to the thread-local reuse
// pool (dropping its buffer only if the pool is saturated) and restores the
// previous one (§4.2: the pool is per-thread, so this cannot race).
static inline void velo_zone_leave(VeloZoneArena* prev) {
    VeloZoneArena* z = g_velo_zone_tls_active;
    if (z != g_velo_zone_tls_default) {
        velo_zone_free_chunks(z);
        if (z->wm_heap) {
            free(z->wm_heap);
            z->wm_heap = NULL;
        }
        z->wm_count = 0;
        z->wm_cap = 0;
        if (g_velo_zone_tls_pool_count < VELO_ZONE_POOL_MAX) {
            z->offset = 0;
            z->chunks = NULL;
            g_velo_zone_tls_pool[g_velo_zone_tls_pool_count++] = *z;
        } else {
            free(z->base);
        }
        free(z);
    }
    g_velo_zone_tls_active = prev;
}

#ifndef SIZE_MAX
#define SIZE_MAX ((size_t)-1)
#endif

static inline size_t velo_check_alloc_size(size_t size, size_t count) {
    if (size == 0 || count == 0) return 0;
    if (count > (SIZE_MAX - 31) / size) {
        fprintf(stderr, "Velo Fatal Error: Allocation size overflow (%llu * %llu bytes)!\n",
                (unsigned long long)size, (unsigned long long)count);
        exit(1);
    }
    return size * count;
}

static inline void* velo_mem_alloc(size_t size, size_t count) {
    size_t total = velo_check_alloc_size(size, count);
    VeloZoneArena* z = velo_zone_active();
    size_t aligned = (total + 7) & ~((size_t)7);
    // `offset <= cap` is checked first: if a corrupted arena ever has
    // offset > cap, `z->cap - z->offset` underflows to a huge value and the
    // capacity test would pass for any request, writing past the buffer.
    // Task 65.4 hardening — the invariant should hold, but the check must not
    // depend on it.
    if (z->offset <= z->cap && aligned <= z->cap - z->offset) {
        void* ptr = (void*)&z->base[z->offset];
        z->offset += aligned;
        memset(ptr, 0, aligned);
        return ptr;
    }
    if (!z->can_grow) {
        fprintf(stderr, "Velo Fatal Error: Zone Arena Out of Memory (active arena capacity %llu bytes, requested %llu more)!\n",
                (unsigned long long)z->cap, (unsigned long long)aligned);
        exit(1);
    }
    VeloZoneChunk* cur = z->chunks;
    if (!cur || cur->offset > cur->cap || aligned > cur->cap - cur->offset) {
        cur = velo_zone_new_chunk(z, aligned);
    }
    void* ptr = (void*)&cur->base[cur->offset];
    cur->offset += aligned;
    memset(ptr, 0, aligned);
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
    size_t total = velo_check_alloc_size(size, count);
    size_t aligned = (total + 7) & ~((size_t)7);
    if (a->offset <= a->cap && aligned <= a->cap - a->offset) {
        void* ptr = (void*)&a->base[a->offset];
        a->offset += aligned;
        memset(ptr, 0, aligned);
        return ptr;
    }
    if (!a->can_grow) {
        fprintf(stderr, "Velo Fatal Error: Allocator Out of Memory (capacity %llu bytes, requested %llu more)!\n",
                (unsigned long long)a->cap, (unsigned long long)aligned);
        exit(1);
    }
    VeloZoneChunk* cur = a->chunks;
    if (!cur || cur->offset > cur->cap || aligned > cur->cap - cur->offset) {
        cur = velo_zone_new_chunk(a, aligned);
    }
    void* ptr = (void*)&cur->base[cur->offset];
    cur->offset += aligned;
    memset(ptr, 0, aligned);
    return ptr;
}

// Returns the number of bytes currently used in allocator `a`.
static inline size_t velo_alloc_used(VeloAllocator a) {
    return velo_arena_total_used(a);
}

// ============================================================================
// Task 6.1: Parameterized Scoped Arenas (mem.create_arena / mem.destroy_arena)
// ============================================================================
static inline VeloZoneArena* velo_mem_create_arena(size_t cap) {
    if (cap == 0) {
        fprintf(stderr, "Velo Fatal Error: Arena capacity must be > 0!\n");
        exit(1);
    }
    if (cap > SIZE_MAX - 31) {
        fprintf(stderr, "Velo Fatal Error: Allocation size overflow (%llu bytes)!\n",
                (unsigned long long)cap);
        exit(1);
    }
    VeloZoneArena* z = (VeloZoneArena*)malloc(sizeof(VeloZoneArena));
    uint8_t* buf = (uint8_t*)malloc(cap);
    if (!z || !buf) {
        fprintf(stderr, "Velo Fatal Error: Arena allocation failed (%llu bytes)!\n",
                (unsigned long long)cap);
        exit(1);
    }
    z->base = buf;
    z->cap = cap;
    z->offset = 0;
    z->can_grow = 1; // custom arenas support dynamic chunk spilling
    z->chunks = NULL;
    z->wm_heap = NULL;
    z->wm_count = 0;
    z->wm_cap = 0;
    return z;
}

static inline void velo_mem_destroy_arena(VeloZoneArena* a) {
    if (a) {
        velo_zone_free_chunks(a);
        if (a->wm_heap) {
            free(a->wm_heap);
            a->wm_heap = NULL;
        }
        a->wm_count = 0;
        a->wm_cap = 0;
        if (a->base) {
            free(a->base);
            a->base = NULL;
        }
        if (g_velo_zone_tls_active == a) {
            g_velo_zone_tls_active = g_velo_zone_tls_default;
        }
        free(a);
    }
}

static inline VeloZoneArena* velo_zone_enter_arena(VeloZoneArena* a) {
    if (!a) {
        fprintf(stderr, "Velo Fatal Error: Cannot enter null arena!\n");
        exit(1);
    }
    VeloZoneArena* prev = velo_zone_active();
    g_velo_zone_tls_active = a;
    return prev;
}

static inline void velo_zone_leave_arena(VeloZoneArena* prev) {
    g_velo_zone_tls_active = prev;
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
        velo_zone_free_chunks(g_velo_zone_tls_default);
        if (g_velo_zone_tls_default->wm_heap) {
            free(g_velo_zone_tls_default->wm_heap);
            g_velo_zone_tls_default->wm_heap = NULL;
        }
        g_velo_zone_tls_default->wm_count = 0;
        g_velo_zone_tls_default->wm_cap = 0;
        free(g_velo_zone_tls_default->base);
        free(g_velo_zone_tls_default);
        g_velo_zone_tls_default = NULL;
    }
    for (size_t i = 0; i < g_velo_zone_tls_pool_count; ++i) {
        velo_zone_free_chunks(&g_velo_zone_tls_pool[i]);
        if (g_velo_zone_tls_pool[i].wm_heap) {
            free(g_velo_zone_tls_pool[i].wm_heap);
            g_velo_zone_tls_pool[i].wm_heap = NULL;
        }
        g_velo_zone_tls_pool[i].wm_count = 0;
        g_velo_zone_tls_pool[i].wm_cap = 0;
        free(g_velo_zone_tls_pool[i].base);
    }
    g_velo_zone_tls_pool_count = 0;
}

// Opaque shared mutex: `@Mutex` in Velo is a `void*` VeloMutexCell handle.
// Semantics: create → acquire/release; sharing happens via Velo
// globals/structs, ordered by spawn/join. Destroy parks the cell for good,
// so every later operation on the same (or stale) address exits loudly.
#if defined(_WIN32)
uint32_t __stdcall WaitForSingleObject(void* h, uint32_t ms);
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

// ============================================================================
// 5.5 High-Resolution Clock & Timing (sys.time): the shared clock/sleep
// helpers. Windows rides QueryPerformanceCounter/QueryPerformanceFrequency
// through self-declared kernel32 prototypes (the §4.2 thread-surface
// precedent: no windows.h, kernel32 is default-linked); Sleep rides the
// kernel32 Sleep. POSIX rides clock_gettime(CLOCK_MONOTONIC) / nanosleep —
// declared by <time.h> itself once the _POSIX_C_SOURCE flags above are set.
// Both compiler emitters lower onto these helpers, so the platform #if
// lives here — once — with identical emitted call shapes on both stages.
// The clock is MONOTONIC microseconds since boot: perfect for game-loop dt,
// deliberately NOT wall-epoch time.
// ============================================================================
#if defined(_WIN32)
int __stdcall QueryPerformanceCounter(int64_t* counter);
int __stdcall QueryPerformanceFrequency(int64_t* frequency);
void __stdcall Sleep(uint32_t ms);

static inline i64 velo_time_now_us(void) {
    int64_t counter;
    int64_t frequency;
    if (!QueryPerformanceCounter(&counter) || !QueryPerformanceFrequency(&frequency) || frequency <= 0) {
        velo_fatal_msg("qpc clock failure");
    }
    // Overflow-safe microseconds split: seconds * 1e6 + remainder * 1e6 / freq.
    // The naive (counter * 1e6) / freq overflows i64 after ~2 weeks of uptime
    // at a 10 MHz counter; this split never does (rem * 1e6 < 1e13 for any
    // sane frequency).
    long long whole = counter / frequency;
    long long rem = counter % frequency;
    return (i64)(whole * 1000000LL + rem * 1000000LL / frequency);
}

static inline void velo_time_sleep(long long ms) {
    // Windows Sleep takes a 32-bit unsigned DWORD; clamp at the API's own
    // ceiling (49.7 days — no game-loop dt ever gets there).
    if (ms < 0) { ms = 0; }
    if (ms > 4294967294LL) { ms = 4294967294LL; }
    Sleep((unsigned long)ms);
}
#else
#include <errno.h>  // nanosleep's EINTR re-arm reads errno

static inline i64 velo_time_now_us(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) {
        velo_fatal_msg("clock_gettime failure");
    }
    return (i64)(ts.tv_sec * 1000000LL + ts.tv_nsec / 1000);
}

static inline void velo_time_sleep(long long ms) {
    // nanosleep reports mid-sleep interrupts with EINTR and hands the
    // remainder back through its second argument — re-arm until it squares.
    struct timespec req;
    long long m = ms > 0 ? ms : 0;
    req.tv_sec = (time_t)(m / 1000LL);
    req.tv_nsec = (long)((m % 1000LL) * 1000000LL);
    while (nanosleep(&req, &req) != 0 && errno == EINTR) { }
}
#endif

// time.delta(): microseconds since the previous call — the FIRST call
// anchors and returns 0 (so the battery can pin it exactly). The anchor is
// a function-local static: single translation unit per binary, and the dt
// loop is one thread's job (single-threaded usage contract — documented
// residual; mutex-guarding a timer read would measure the mutex).
static inline i64 velo_time_delta_us(void) {
    static long long g_velo_time_delta_anchor = -1;
    long long now_us = velo_time_now_us();
    if (g_velo_time_delta_anchor < 0) {
        g_velo_time_delta_anchor = now_us;
        return 0;
    }
    long long elapsed = now_us - g_velo_time_delta_anchor;
    g_velo_time_delta_anchor = now_us;
    return (i64)elapsed;
}

// ============================================================================
// 5.4 Extended File System & OS Primitives (sys.os): environment + argv.
// The argv statics are stashed by BOTH compilers' main wrappers (the two
// identical stash lines they emit at the top of main). getenv returns a
// borrowed pointer — the helper copies it into owned arena memory (str
// token doctrine: velo_mem_alloc, zone-reclaimed); an unset key reads as
// the empty string. set_env splits per platform: CRT _putenv_s on Windows,
// setenv(key, val, 1) on POSIX (declared via the 200112L flags above).
// velo_os_args itself lives with the shelf machinery (needs VeloShelf).
// ============================================================================
static int g_velo_os_argc = 0;
static char** g_velo_os_argv = NULL;

static inline char* velo_os_get_env(const char* key) {
    const char* raw = (key != NULL) ? getenv(key) : NULL;
    size_t len = (raw != NULL) ? strlen(raw) : 0;
    char* out = (char*)velo_mem_alloc(1, len + 1);
    if (raw != NULL) {
        memcpy(out, raw, len + 1);
    }
    return out;
}

static inline bool velo_os_set_env(const char* key, const char* val) {
#if defined(_WIN32)
    return _putenv_s(key, val) == 0;
#else
    return setenv(key, val, 1) == 0;
#endif
}

// ============================================================================
// Phase 70 / Task 70.2: portable CSPRNG fill.
//
// `std/crypto/rand.vl` bound advapi32's SystemFunction036 directly, in a file
// with no platform suffix, so every program that imported `std.crypto` -- which
// includes this compiler, through `pkg_lock` -- carried a Win32-only extern and
// could not build off Windows.
//
// The portable answer is the CRT's own entropy source: rand_s on Windows (the
// documented SystemFunction036 replacement, and confirmed working on this
// toolchain), /dev/urandom on POSIX. Both are read in a loop because neither
// guarantees filling a large request in one call.
//
// Returns true when every byte was produced by the OS source. A false return
// means the caller's fallback should run; the buffer is left untouched then
// rather than filled with partial entropy, so a caller can never mistake a
// failed read for random output.
// ============================================================================
#if defined(_WIN32) && !defined(_MSC_VER)
// Declared here for MinGW rather than relying on the _CRT_RAND_S guard at the top
// of this file, which cannot help a translation unit that included <stdlib.h> first.
// On MSVC, _CRT_RAND_S is defined before <stdlib.h> so the system declaration matches
// the configured CRT linkage (_ACRTIMP for /MD vs /MT).
// The dllimport attribute makes this compatible with MinGW's system declaration in
// either order (no diagnostic, measured both ways). errno_t is int on this CRT,
// so the int return type agrees with it.
__declspec(dllimport) int __cdecl rand_s(unsigned int* randomValue);
#endif

static inline bool velo_crypto_random_fill(void* buf, size_t len) {
    if (buf == NULL) return false;
    if (len == 0) return true;
#if defined(_WIN32)
    unsigned int* words = (unsigned int*)buf;
    size_t remaining = len;
    while (remaining > 0) {
        unsigned int r = 0;
        if (rand_s(&r) != 0) return false;
        size_t take = remaining < sizeof(unsigned int) ? remaining : sizeof(unsigned int);
        memcpy(words, &r, take);
        words = (unsigned int*)((char*)words + take);
        remaining -= take;
    }
    return true;
#else
    FILE* f = fopen("/dev/urandom", "rb");
    if (f == NULL) return false;
    size_t got = fread(buf, 1, len, f);
    fclose(f);
    return got == len;
#endif
}

// ============================================================================
// Phase 70 / Task 70.1: host platform identity for the compiler itself.
//
// The compiler has to know which platform it is running on in order to resolve
// `foo.vl` to `foo_<platform>.vl`. It used to ask std/os/env_windows.vl's
// os_is_windows() -- a Win32-only module -- so a compiler built on Linux still
// believed it was on Windows and emitted Win32 externs. The predicate and the
// thing it was deciding about lived in the same place.
//
// This helper moves the answer into the runtime header, which every emitted
// program links and which already carries the _WIN32 branches. A `static
// inline` definition is visible to the compiler's own emitted code, and an
// `extern` declaration in the Velo source reuses it (verified: C99 allows an
// extern declaration after a static inline definition, and the linker resolves
// it to the inline copy in this translation unit).
//
// Returns one of "windows", "linux", "macos". Any other POSIX host returns
// "linux": the POSIX variants are the right fallback there, and a distinct name
// would have to be added to the suffix table to mean anything.
// ============================================================================
static inline const char* velo_host_platform(void) {
#if defined(_WIN32)
    return "windows";
#elif defined(__APPLE__)
    return "macos";
#else
    return "linux";
#endif
}

// Borrowed-pointer environment lookup for the compiler's own configuration
// (VELO_TARGET_PLATFORM and friends). Distinct from velo_os_get_env, which
// allocates an owned copy: this returns the getenv pointer directly, or "" when
// the key is unset, so a caller that only compares or copies it never leaks and
// never needs a free. The pointer is valid until the environment is modified.
static inline const char* velo_host_getenv(const char* key) {
    const char* raw = (key != NULL) ? getenv(key) : NULL;
    return (raw != NULL) ? raw : "";
}

// ============================================================================
// Phase 70 / Task 70.2: path of the running binary.
//
// The compiler located its own `runtime/` header directory with the relative
// paths "-I runtime" and "-I velo/runtime", i.e. relative to the *caller's*
// working directory. That is only correct when the caller happens to sit at the
// repository root. Run from a temp directory -- which is exactly what the test
// suite does -- the flag silently matched nothing, gcc fell back to a stale
// installed copy under ~/.velo/include, and a program using a helper that only
// exists in the in-tree header failed to link.
//
// A relative path cannot be repaired by trying more relative candidates; the
// answer has to come from the OS. So the runtime reports where this process was
// loaded from, and the caller derives the include directory from that.
//
// The returned pointer is a process-wide static buffer: valid until the next
// call, never freed. Concurrent callers can race, which is harmless here
// because every caller wants the same value.
// ============================================================================
#if defined(_WIN32)
uint32_t __stdcall GetModuleFileNameA(void* hmod, char* buf, uint32_t size);
#endif

static inline const char* velo_host_exe_path(void) {
    static char buf[4096];
#if defined(_WIN32)
    uint32_t n = GetModuleFileNameA(NULL, buf, (uint32_t)sizeof(buf));
    if (n == 0 || n >= (uint32_t)sizeof(buf)) return "";
    buf[n] = '\0';
    return buf;
#elif defined(__APPLE__)
    uint32_t size = (uint32_t)sizeof(buf);
    if (_NSGetExecutablePath(buf, &size) != 0) return "";
    return buf;
#else
    ssize_t n = readlink("/proc/self/exe", buf, sizeof(buf) - 1);
    if (n <= 0) return "";
    buf[n] = '\0';
    return buf;
#endif
}




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

#define VELO_HEAP_MAGIC 0x56454C4F48454150ULL

static size_t g_velo_heap_active = 0;

static inline bool velo_is_in_zone(const void* ptr) {
    if (!ptr) return false;
    const uint8_t* p = (const uint8_t*)ptr;
    VeloZoneArena* z = velo_zone_active();
    if (z && z->base && p >= z->base && p < z->base + z->cap) return true;
    if (z) {
        const VeloZoneChunk* cur = z->chunks;
        while (cur) {
            if (p >= cur->base && p < cur->base + cur->cap) return true;
            cur = cur->next;
        }
    }
    if (g_velo_zone_tls_default && g_velo_zone_tls_default != z) {
        if (g_velo_zone_tls_default->base && p >= g_velo_zone_tls_default->base && p < g_velo_zone_tls_default->base + g_velo_zone_tls_default->cap) return true;
        const VeloZoneChunk* cur = g_velo_zone_tls_default->chunks;
        while (cur) {
            if (p >= cur->base && p < cur->base + cur->cap) return true;
            cur = cur->next;
        }
    }
    return false;
}

static inline void* velo_heap_alloc(size_t size, size_t count) {
    size_t total = velo_check_alloc_size(size, count);
    size_t header_size = (sizeof(size_t) + 15) & ~((size_t)15);
    uint8_t* raw = (uint8_t*)malloc(total + header_size);
    if (!raw) {
        fprintf(stderr, "Velo Fatal Error: Out of Heap Memory!\n");
        exit(1);
    }
    *((size_t*)raw) = total;
    *((uint64_t*)(raw + sizeof(size_t))) = VELO_HEAP_MAGIC;
    VELO_ATOMIC_ADD64(&g_velo_heap_active, (long long)total);
    return (void*)(raw + header_size);
}

static inline void velo_heap_free(void* ptr) {
    if (!ptr) return;
    if (velo_is_in_zone(ptr)) return;
    size_t header_size = (sizeof(size_t) + 15) & ~((size_t)15);
    uint8_t* raw = ((uint8_t*)ptr) - header_size;
    if (*((uint64_t*)(raw + sizeof(size_t))) != VELO_HEAP_MAGIC) {
        return;
    }
    *((uint64_t*)(raw + sizeof(size_t))) = 0;
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
    if (*((uint64_t*)(raw + sizeof(size_t))) != VELO_HEAP_MAGIC) {
        return NULL;
    }
    size_t old_total = *((size_t*)raw);
    size_t new_total = velo_check_alloc_size(size, (size_t)count);
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
    *((uint64_t*)(nraw + sizeof(size_t))) = VELO_HEAP_MAGIC;
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
// 5.4 (slice 2): the fs metadata family — same doctrine as the legacy six
// (bool results over narrow char* paths, zero allocations), built on the
// plain CRT: stat() classifies (is_dir/is_file also answer the fopen-trick
// exists blind spot for directories), _mkdir/mkdir create one level,
// rename is its own CRT call, and copy is a portable stdio loop with
// binary modes (no text translation on either platform). create_dir_all
// walks the path segment by segment (both separators normalized to '/'
// inside the working copy; the drive prefix "C:" is skipped — it always
// exists) and treats an existing level as success (idempotent, like every
// language's mkdir -p). No kernel32, no windows.h.
// ============================================================================
static inline bool velo_fs_is_dir(const char* path) {
    if (!path) return false;
    struct stat st;
    if (stat(path, &st) != 0) return false;
    return S_ISDIR(st.st_mode) ? true : false;
}

static inline bool velo_fs_is_file(const char* path) {
    if (!path) return false;
    struct stat st;
    if (stat(path, &st) != 0) return false;
    return S_ISREG(st.st_mode) ? true : false;
}

static inline bool velo_fs_create_dir(const char* path) {
    if (!path) return false;
#if defined(_WIN32)
    return _mkdir(path) == 0;
#else
    return mkdir(path, 0777) == 0;
#endif
}

static inline bool velo_fs_create_dir_all(const char* path) {
    if (!path) return false;
    size_t len = strlen(path);
    if (len == 0) return false;
    // Working copy of the path, separators normalized to '/'. Every
    // separator boundary (and the NUL) triggers a create of everything
    // accumulated so far.
    char* acc = (char*)velo_mem_alloc(1, len + 1);
    if (!acc) return false;
    size_t out = 0;
    for (size_t i = 0; i <= len; ++i) {
        char c = path[i];
        if (c == '/' || c == '\\' || c == '\0') {
            acc[out] = '\0';
            // Pure drive prefixes ("C:") are never created — they always
            // exist, and _mkdir("C:") is meaningless.
            if (out > 0 && acc[out - 1] != ':') {
                if (!velo_fs_create_dir(acc)) {
                    // Already there? Then keep going (idempotent target).
                    struct stat st;
                    if (stat(acc, &st) != 0 || !S_ISDIR(st.st_mode)) {
                        return false;
                    }
                }
            }
            if (c != '\0' && out > 0 && acc[out - 1] != '/') {
                acc[out++] = '/';
            } else if (c != '\0' && out == 0) {
                // Leading separator — keep it (absolute paths).
                acc[out++] = c;
            }
            continue;
        }
        acc[out++] = c;
    }
    return true;
}

static inline bool velo_fs_copy(const char* src, const char* dst) {
    if (!src || !dst) return false;
    FILE* in = fopen(src, "rb");
    if (!in) return false;
    FILE* out = fopen(dst, "wb");
    if (!out) {
        fclose(in);
        return false;
    }
    char chunk[4096];
    size_t n;
    bool ok = true;
    while ((n = fread(chunk, 1, sizeof(chunk), in)) > 0) {
        if (fwrite(chunk, 1, n, out) != n) {
            ok = false;
            break;
        }
    }
    if (ferror(in) != 0) ok = false;
    if (fclose(out) != 0) ok = false;
    fclose(in);
    return ok;
}

// Renames/moves `src` to `dst`, REPLACING `dst` when it already exists.
//
// The overwrite clause is why this is not a bare rename() call. Measured on this
// toolchain: POSIX rename() replaces the target atomically, but the Windows CRT
// rename() fails with EEXIST (errno 17) and leaves the destination untouched --
// while the MoveFileExA(MOVEFILE_REPLACE_EXISTING) call the std library used to
// make did replace it. A plain rename() would therefore have silently changed
// documented behaviour on Windows. The destination is removed first there.
//
// Residual: the Windows path is remove-then-rename, so it is not atomic. POSIX
// keeps the atomic single call. Callers that need atomicity on Windows need a
// different primitive, which is stated rather than implied.
//
// velo_fs_remove_dir is defined below (Task 70.2 section), so it is declared
// here rather than relying on definition order.
static inline bool velo_fs_remove_dir(const char* path);

static inline bool velo_fs_rename(const char* src, const char* dst) {
    if (!src || !dst) return false;
#if defined(_WIN32)
    if (velo_fs_is_file(dst) || velo_fs_is_dir(dst)) {
        if (velo_fs_is_dir(dst)) {
            if (!velo_fs_remove_dir(dst)) return false;
        } else {
            if (!velo_fs_remove(dst)) return false;
        }
    }
#endif
    return rename(src, dst) == 0;
}

// ============================================================================
// Phase 70 / Task 70.2: the metadata and directory-removal gap in the CRT set.
//
// Three operations the std/ modules needed could not be expressed with the
// helpers above, so they were written as Win32 kernel32 calls inside
// platform-NEUTRAL files: `stat` rode GetFileAttributesExA, directory removal
// rode RemoveDirectoryA, and the directory iterator rode
// FindFirstFileA/FindNextFileA/FindClose. That is what made `std.fs`
// unbuildable off Windows while claiming to be portable -- the extern block
// lived in `std/fs/stat.vl`, not in a `_windows.vl` variant.
//
// Each is added here instead, because the header is the one place already
// allowed to carry a `#if defined(_WIN32)` branch. Two facts were measured
// before writing them rather than assumed:
//
//   * remove() cannot delete a directory on this CRT. It returns -1 with
//     EACCES (probe: errno 13 "Permission denied"), so directory removal needs
//     _rmdir on Windows and rmdir on POSIX. remove() stays file-only.
//   * There is no POSIX lstat in this CRT, so `is_symlink` cannot be answered
//     portably from stat(). It stays false on Windows, where the attribute bit
//     is available, and is answered by lstat on POSIX.
//
// mtime is reported in epoch MILLISECONDS because that is the unit FileStat
// documents and the one the platform variants' callers already consume. The
// loss of sub-second precision on POSIX hosts whose stat() has only whole
// seconds is stated rather than hidden -- it is a property of the CRT
// surface, not of this helper.
// ============================================================================
// Returns the metadata of `path` into a caller-supplied flat buffer of nine
// machine words laid out as:
//
//   [0] size (i64)      [1] is_dir      [2] is_file    [3] is_readonly
//   [4] is_symlink      [5] exists      [6] modified_time_ms (i64)
//   [7] created_time_ms (i64)           [8] (reserved, always 0)
//
// A flat i64 array rather than a struct return, because a struct return would
// have to name a type both this header and the Velo file declare, and the
// emitted C defines Velo `data` types itself -- two definitions of one name is
// a redefinition error (measured, not assumed). An out-parameter of plain
// integers keeps the ABI identical on every target and lets the Velo side keep
// its own FileStat type with no naming overlap.
//
// Returns false when the path does not exist or cannot be stat'ed; the buffer
// is zeroed in that case so a caller can never read stale fields as "exists".
static inline bool velo_fs_stat_into(const char* path, i64* out) {
    if (out == NULL) return false;
    for (int i = 0; i < 9; i++) out[i] = 0;
    if (path == NULL) return false;

    struct stat st;
    if (stat(path, &st) != 0) return false;

    out[0] = (i64)st.st_size;
    out[1] = S_ISDIR(st.st_mode) ? 1 : 0;
    out[2] = S_ISREG(st.st_mode) ? 1 : 0;
    out[3] = ((st.st_mode & S_IWUSR) == 0) ? 1 : 0;
    out[5] = 1;
    out[6] = (i64)st.st_mtime * 1000LL;
    // A portable creation/birth time does not exist in C99 <sys/stat.h>:
    // Windows st_ctime is creation time, POSIX st_ctime is inode-change time.
    // Reporting POSIX ctime as "created" would be a lie, so it stays 0 there and
    // the field is documented as Windows-meaningful only.
#if defined(_WIN32)
    out[7] = (i64)st.st_ctime * 1000LL;
    out[4] = 0;  // the reparse-point bit is not exposed through the CRT here
#else
    out[7] = 0;
    struct stat lst;
    out[4] = (lstat(path, &lst) == 0 && S_ISLNK(lst.st_mode)) ? 1 : 0;
#endif
    return true;
}

// Removes an EMPTY directory. remove() is file-only on the Windows CRT, so the
// platform call is explicit on both sides rather than relying on remove()'s
// divergent behaviour.
static inline bool velo_fs_remove_dir(const char* path) {
    if (path == NULL) return false;
#if defined(_WIN32)
    return _rmdir(path) == 0;
#else
    return rmdir(path) == 0;
#endif
}

// Directory-entry classification for the iterator family. Writes into a flat
// buffer of three i64 words: [0] is_dir, [1] is_file, [2] size.
//
// A flat scalar out-parameter for the same reason as velo_fs_stat_into: the
// emitted C defines Velo `data` types itself, so a struct shared with this
// header would be declared twice and fail to compile (measured).
static inline bool velo_fs_entry_info_into(const char* path, i64* out) {
    if (out == NULL) return false;
    out[0] = 0;
    out[1] = 0;
    out[2] = 0;
    if (path == NULL) return false;
    struct stat st;
    if (stat(path, &st) != 0) return false;
    out[0] = S_ISDIR(st.st_mode) ? 1 : 0;
    out[1] = S_ISREG(st.st_mode) ? 1 : 0;
    out[2] = (i64)st.st_size;
    return true;
}

// Reads one directory level into owned storage and reports it through a flat
// 5-word out-buffer:
//
//   [0] names   (pointer to a NUL-separated block of entry names)
//   [1] offsets (pointer to a size_t array of byte offsets into `names`)
//   [2] count   (number of entries)
//   [3] opened  (1 when the directory opened; 0 when missing, empty result)
//   [4] reserved (always 0)
//
// Names come back in one block with a parallel offset table so the caller can
// free exactly twice regardless of entry count. `opened` distinguishes "no such
// directory" from "a directory with no entries" -- the distinction the old
// FindFirstFileA code got for free from an invalid handle.
//
// The offsets array is `size_t`, so this module also exposes the element width
// through velo_dir_listing_elem_size() rather than letting a caller assume it.
//
// Returns nothing; the caller inspects [3]. Allocation failure reports
// opened=0, because a caller cannot use a listing it cannot read.
static inline void velo_fs_list_dir_into(const char* path, i64* out) {
    if (out == NULL) return;
    for (int i = 0; i < 5; i++) out[i] = 0;
    if (path == NULL) return;

    size_t block_cap = 256;
    size_t block_len = 0;
    char* block = (char*)malloc(block_cap);
    size_t idx_cap = 16;
    size_t* offsets = (size_t*)malloc(idx_cap * sizeof(size_t));
    if (block == NULL || offsets == NULL) {
        free(block);
        free(offsets);
        return;
    }

    size_t count = 0;
#if defined(_WIN32)
    char pattern[1024];
    size_t plen = strlen(path);
    if (plen == 0 || plen + 3 >= sizeof(pattern)) {
        free(block);
        free(offsets);
        return;
    }
    memcpy(pattern, path, plen);
    if (pattern[plen - 1] != '/' && pattern[plen - 1] != '\\') {
        pattern[plen++] = '/';
    }
    pattern[plen++] = '*';
    pattern[plen] = '\0';
    struct _finddata_t fd;
    intptr_t h = _findfirst(pattern, &fd);
    if (h == -1) {
        free(block);
        free(offsets);
        return;
    }
    do {
        const char* nm = fd.name;
        if (nm[0] == '.' && (nm[1] == '\0' || (nm[1] == '.' && nm[2] == '\0'))) continue;
        size_t len = strlen(nm);
        if (count + 1 > idx_cap) {
            idx_cap *= 2;
            size_t* grown = (size_t*)realloc(offsets, idx_cap * sizeof(size_t));
            if (grown == NULL) break;
            offsets = grown;
        }
        if (block_len + len + 1 > block_cap) {
            while (block_len + len + 1 > block_cap) block_cap *= 2;
            char* grown = (char*)realloc(block, block_cap);
            if (grown == NULL) break;
            block = grown;
        }
        offsets[count++] = block_len;
        memcpy(block + block_len, nm, len);
        block_len += len;
        block[block_len++] = '\0';
    } while (_findnext(h, &fd) == 0);
    _findclose(h);
#else
    DIR* dir = opendir(path);
    if (dir == NULL) {
        free(block);
        free(offsets);
        return;
    }
    struct dirent* ent;
    while ((ent = readdir(dir)) != NULL) {
        const char* nm = ent->d_name;
        if (nm[0] == '.' && (nm[1] == '\0' || (nm[1] == '.' && nm[2] == '\0'))) continue;
        size_t len = strlen(nm);
        if (count + 1 > idx_cap) {
            idx_cap *= 2;
            size_t* grown = (size_t*)realloc(offsets, idx_cap * sizeof(size_t));
            if (grown == NULL) break;
            offsets = grown;
        }
        if (block_len + len + 1 > block_cap) {
            while (block_len + len + 1 > block_cap) block_cap *= 2;
            char* grown = (char*)realloc(block, block_cap);
            if (grown == NULL) break;
            block = grown;
        }
        offsets[count++] = block_len;
        memcpy(block + block_len, nm, len);
        block_len += len;
        block[block_len++] = '\0';
    }
    closedir(dir);
#endif
    out[0] = (i64)(intptr_t)block;
    out[1] = (i64)(intptr_t)offsets;
    out[2] = (i64)count;
    out[3] = 1;
}

// Releases a listing produced by velo_fs_list_dir_into. Takes the same flat
// 5-word buffer so the caller passes one consistent thing to free as to read.
static inline void velo_dir_listing_free(i64* out) {
    if (out == NULL) return;
    if (out[0] != 0) free((void*)(intptr_t)out[0]);
    if (out[1] != 0) free((void*)(intptr_t)out[1]);
    out[0] = 0;
    out[1] = 0;
    out[2] = 0;
    out[3] = 0;
}

// 5.4 (slice 4): the streaming family — FILE* handles pass through Velo
// (@File lowers onto FILE* in both stages' type maps). Contracts: fopen is
// the CRT call (NULL on failure); fclose false on a NULL handle; fread
// NEVER returns NULL — an owned empty string covers a dead handle, a
// non-positive count, or a count over the 1 GiB chunk cap — and it
// NUL-terminates at the bytes actually read (EOF surfaces naturally as a
// zero-length read). fwrite reports ALL-BYTES-WRITTEN (empty data is a
// trivial true, mirroring write_file's empty-contents success). fseek is
// a SEEK_SET-only jump: negative offsets and anything beyond the Windows
// CRT's 32-bit long reach reject (rewind/0 is the common case; bigger
// positioning rides the chapter's whole-file members). Pure CRT, no
// kernel32 — same doctrine as the whole fs block.
static inline FILE* velo_fs_fopen(const char* path, const char* mode) {
    if (path == NULL || mode == NULL) return NULL;
    return fopen(path, mode);
}

static inline bool velo_fs_fclose(FILE* f) {
    if (f == NULL) return false;
    return fclose(f) == 0;
}

static inline char* velo_fs_fread(FILE* f, i64 count) {
    if (f != NULL && count > 0 && count <= 1073741824LL) {
        char* buf = (char*)velo_mem_alloc(1, (size_t)count + 1);
        size_t got = fread(buf, 1, (size_t)count, f);
        buf[got] = '\0';
        return buf;
    }
    // dead handle / non-positive count / over-cap: owned empty (never NULL)
    char* empty = (char*)velo_mem_alloc(1, 1);
    empty[0] = '\0';
    return empty;
}

static inline bool velo_fs_fwrite(FILE* f, const char* data) {
    if (f == NULL || data == NULL) return false;
    size_t len = strlen(data);
    if (len == 0) return true;
    return fwrite(data, 1, len, f) == len;
}

static inline bool velo_fs_fseek(FILE* f, i64 offset) {
    if (f == NULL) return false;
    if (offset < 0 || offset > 2147483647LL) return false;  // CRT long reach
    return fseek(f, (long)offset, SEEK_SET) == 0;
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

static inline bool velo_str_eq(const char* a, const char* b) {
    if (a == b) return true;
    if (!a || !b) return false;
    return strcmp(a, b) == 0;
}

static inline bool velo_str_neq(const char* a, const char* b) {
    if (a == b) return false;
    if (!a || !b) return true;
    return strcmp(a, b) != 0;
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

// ============================================================================
// Zone vs Heap String Allocations (Task 8.1):
// Standard string operations (trim, replace, to_upper, to_lower, concat)
// allocate out of the active zone arena (velo_mem_alloc) for automatic O(1)
// reclamation on zone exit with zero persistent heap leaks.
// Explicit heap counterparts (heap_trim, heap_replace, heap_to_upper,
// heap_to_lower, heap_concat) allocate on the persistent heap (velo_heap_alloc)
// and are tracked on g_velo_heap_active.
// ============================================================================

static inline char* velo_str_copy_zone(const char* src, size_t n) {
    char* out = (char*)velo_mem_alloc(1, n + 1);
    if (n > 0) memcpy(out, src, n);
    out[n] = 0;
    return out;
}

static inline char* velo_str_trim_impl(const char* s, const char* fn_name, bool on_heap) {
    const char* a = velo_str_nonnull(s, fn_name);
    const char* p = a;
    while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\v' || *p == '\f' || *p == '\r') p++;
    const char* end = p + strlen(p);
    while (end > p && (end[-1] == ' ' || end[-1] == '\t' || end[-1] == '\n' ||
                       end[-1] == '\v' || end[-1] == '\f' || end[-1] == '\r')) end--;
    size_t len = (size_t)(end - p);
    return on_heap ? velo_str_copy_heap(p, len) : velo_str_copy_zone(p, len);
}

static inline char* velo_str_trim(const char* s) {
    return velo_str_trim_impl(s, "str.trim", false);
}

static inline char* velo_str_heap_trim(const char* s) {
    return velo_str_trim_impl(s, "str.heap_trim", true);
}

static inline char* velo_str_replace_impl(const char* s, const char* from, const char* to, const char* fn_name, bool on_heap) {
    const char* a = velo_str_nonnull(s, fn_name);
    const char* f = velo_str_nonnull(from, fn_name);
    const char* t = velo_str_nonnull(to, fn_name);
    size_t alen = strlen(a);
    size_t flen = strlen(f);
    size_t tlen = strlen(t);
    if (flen == 0) return on_heap ? velo_str_copy_heap(a, alen) : velo_str_copy_zone(a, alen);
    size_t hits = 0;
    const char* p = a;
    const char* hit;
    while ((hit = strstr(p, f)) != NULL) {
        hits++;
        p = hit + flen;
    }
    size_t out_len = alen - (hits * flen) + (hits * tlen) + 1;
    char* out = (char*)(on_heap ? velo_heap_alloc(1, out_len) : velo_mem_alloc(1, out_len));
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

static inline char* velo_str_replace(const char* s, const char* from, const char* to) {
    return velo_str_replace_impl(s, from, to, "str.replace", false);
}

static inline char* velo_str_heap_replace(const char* s, const char* from, const char* to) {
    return velo_str_replace_impl(s, from, to, "str.heap_replace", true);
}

static inline char* velo_str_to_upper_impl(const char* s, const char* fn_name, bool on_heap) {
    const char* a = velo_str_nonnull(s, fn_name);
    size_t n = strlen(a);
    char* out = (char*)(on_heap ? velo_heap_alloc(1, n + 1) : velo_mem_alloc(1, n + 1));
    for (size_t i = 0; i < n; i++) {
        char c = a[i];
        if (c >= 'a' && c <= 'z') c = (char)(c - 'a' + 'A');
        out[i] = c;
    }
    out[n] = 0;
    return out;
}

static inline char* velo_str_to_upper(const char* s) {
    return velo_str_to_upper_impl(s, "str.to_upper", false);
}

static inline char* velo_str_heap_to_upper(const char* s) {
    return velo_str_to_upper_impl(s, "str.heap_to_upper", true);
}

static inline char* velo_str_to_lower_impl(const char* s, const char* fn_name, bool on_heap) {
    const char* a = velo_str_nonnull(s, fn_name);
    size_t n = strlen(a);
    char* out = (char*)(on_heap ? velo_heap_alloc(1, n + 1) : velo_mem_alloc(1, n + 1));
    for (size_t i = 0; i < n; i++) {
        char c = a[i];
        if (c >= 'A' && c <= 'Z') c = (char)(c - 'A' + 'a');
        out[i] = c;
    }
    out[n] = 0;
    return out;
}

static inline char* velo_str_to_lower(const char* s) {
    return velo_str_to_lower_impl(s, "str.to_lower", false);
}

static inline char* velo_str_heap_to_lower(const char* s) {
    return velo_str_to_lower_impl(s, "str.heap_to_lower", true);
}

static inline char* velo_str_concat_impl(const char* a, const char* b, const char* fn_name, bool on_heap) {
    const char* x = velo_str_nonnull(a, fn_name);
    const char* y = velo_str_nonnull(b, fn_name);
    size_t flen = strlen(x);
    size_t tlen = strlen(y);
    char* out = (char*)(on_heap ? velo_heap_alloc(1, flen + tlen + 1) : velo_mem_alloc(1, flen + tlen + 1));
    memcpy(out, x, flen);
    if (tlen > 0) memcpy(out + flen, y, tlen);
    out[flen + tlen] = 0;
    return out;
}

static inline char* velo_str_concat(const char* a, const char* b) {
    return velo_str_concat_impl(a, b, "str.concat", false);
}

static inline char* velo_str_heap_concat(const char* a, const char* b) {
    return velo_str_concat_impl(a, b, "str.heap_concat", true);
}

// ============================================================================
// General In-Memory String Formatting (Task 8.2):
// velo_str_format formats into active zone arena (automatic O(1) reclamation).
// velo_str_heap_format formats onto persistent heap (tracked on g_velo_heap_active).
// ============================================================================

static inline char* velo_str_format_impl(const char* fmt, va_list ap, const char* fn_name, bool on_heap) {
    const char* f = velo_str_nonnull(fmt, fn_name);
    va_list ap_len;
    va_copy(ap_len, ap);
    int len = vsnprintf(NULL, 0, f, ap_len);
    va_end(ap_len);
    if (len < 0) return (char*)"";
    char* out = (char*)(on_heap ? velo_heap_alloc(1, (size_t)len + 1)
                                : velo_mem_alloc(1, (size_t)len + 1));
    vsnprintf(out, (size_t)len + 1, f, ap);
    out[len] = '\0';
    return out;
}

static inline char* velo_str_format(const char* fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    char* res = velo_str_format_impl(fmt, ap, "str.format", false);
    va_end(ap);
    return res;
}

static inline char* velo_str_heap_format(const char* fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    char* res = velo_str_format_impl(fmt, ap, "str.heap_format", true);
    va_end(ap);
    return res;
}

// str.split lives BELOW the 5.2 shelf helpers (slice 11: it returns an owning
// VeloShelf by value, so the shelf struct + put must already be in scope).



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
//
// 5.2 (slice 10) — the memory-model selector: VeloShelf grows `src`, the
// allocation source. NULL (zero-init) = the ACTIVE arena — every shelf built
// before slice 10 behaves byte-identically. A non-NULL src = HEAP storage
// (velo_heap_alloc, persistent blocks on the shared ledger): the shelf
// outlives its zone and can be returned from acts. ONE selector serves every
// allocating helper (growth, the take/remove_at victim stashes, and the
// sorted()/reversed() result rows — a derived shelf inherits the receiver's
// source). Freeing heap shelves is a later slice; the heap ledger accounts
// them (persistent-block pricing).
// ============================================================================
typedef struct VeloShelf {
    void*  data;  // element storage (allocated via the src selector on growth)
    size_t len;   // element count
    size_t cap;   // element capacity
    size_t esz;   // element size in bytes (established at the first put)
    VeloAllocator src;  // slice 10: NULL = active arena; non-NULL = heap
} VeloShelf;

// The pinned sentinel the compilers store into `src` for `heap shelf` — any
// non-NULL source selects heap allocation.
#define VELO_SHELF_HEAP_SRC ((VeloAllocator)1)

// The one allocator selector (slice 10): zone-backed shelves bump the active
// arena (reclaimed wholesale at the zone exit); heap shelves allocate
// persistent blocks on the shared ledger and never touch the zone.
static inline void* velo_shelf_alloc(const VeloShelf* s, size_t esz, size_t count) {
    if (s->src) return velo_heap_alloc(esz, count);
    return velo_mem_alloc(esz, count);
}

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
        void* old_data = s->data;
        void* next = velo_shelf_alloc(s, s->esz, new_cap);   // slice 10: the src selector
        if (s->len > 0 && old_data != NULL) memcpy(next, old_data, s->len * s->esz);
        if (s->src && old_data != NULL) velo_heap_free(old_data);
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
    void* stash = velo_shelf_alloc(s, s->esz, 1);   // slice 10: heap stashes survive the zone
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

static inline VeloShelf velo_shelf_create_empty(size_t esz, VeloAllocator src) {
    VeloShelf s = {0};
    s.esz = esz;
    s.src = src;
    return s;
}

static inline VeloShelf velo_shelf_create_lit(size_t esz, size_t count, const void* elems, VeloAllocator src) {
    VeloShelf s = {0};
    s.esz = esz;
    s.src = src;
    if (count > 0 && elems != NULL) {
        size_t cap = 4;
        while (cap < count) cap *= 2;
        s.data = velo_shelf_alloc(&s, esz, cap);
        s.cap = cap;
        s.len = count;
        memcpy(s.data, elems, count * esz);
    }
    return s;
}

// Task 7.1: Explicit teardown for shelves (shelf.destroy / shelf.free).
// If the shelf is heap-backed (s->src != NULL), frees its data buffer from
// the persistent heap ledger. Resets data pointer, length, and capacity to 0.
static inline void velo_shelf_free(VeloShelf* s) {
    if (!s) return;
    if (s->src && s->data != NULL) {
        velo_heap_free(s->data);
    }
    s->data = NULL;
    s->len = 0;
    s->cap = 0;
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

// Copy-and-sort engine: fresh backing storage (never the receiver's row);
// slice 10: the result inherits the receiver's allocation source.
static inline VeloShelf velo_shelf_sorted_copy(const VeloShelf* s, int (*cmp)(const void*, const void*)) {
    VeloShelf out = {0};
    out.esz = s->esz;
    out.len = s->len;
    out.cap = s->len;
    out.src = s->src;
    if (s->len > 0) {
        out.data = velo_shelf_alloc(&out, s->esz, s->len);
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
    out.src = s->src;   // slice 10: a derived shelf inherits the source
    if (s->len > 0) {
        out.data = velo_shelf_alloc(&out, s->esz, s->len);
        const char* src = (const char*)s->data;
        char* dst = (char*)out.data;
        for (size_t i = 0; i < s->len; i++) {
            memcpy(dst + (s->len - 1 - i) * s->esz, src + i * s->esz, s->esz);
        }
    }
    return out;
}

// ============================================================================
// 5.2 slice 5: shelf join + the shared repr machinery. Each writer renders
// ONE element exactly the way io-string interpolation renders it (ints
// `snprintf("%lld", (long long))`, floats `%.2f` of (double), bool
// `true`/`false`, string characters verbatim). Called with dst == NULL the
// writer is the MEASURE pass (the C99 "snprintf(NULL, 0)" would-be length);
// with a real dst it renders in place. The wrappers are the compiler's
// `xs.join(sep)` targets — one per joinable family token.
// ============================================================================
typedef size_t (*VeloJoinWriteFn)(char* dst, const void* elem);

#define VELO_JOIN_MEASURE_CAP(dst) ((dst) != NULL ? (size_t)-1 : (size_t)0)

#define VELO_JOIN_W_INT(token, ctype) \
    static inline size_t velo_join_w_##token(char* dst, const void* e) { \
        return (size_t)snprintf(dst, VELO_JOIN_MEASURE_CAP(dst), "%lld", \
                                (long long)(*(const ctype*)e)); \
    }

VELO_JOIN_W_INT(i8, int8_t)
VELO_JOIN_W_INT(i16, int16_t)
VELO_JOIN_W_INT(i32, int32_t)
VELO_JOIN_W_INT(i64, int64_t)
VELO_JOIN_W_INT(u8, uint8_t)
VELO_JOIN_W_INT(u16, uint16_t)
VELO_JOIN_W_INT(u32, uint32_t)
VELO_JOIN_W_INT(u64, uint64_t)
VELO_JOIN_W_INT(usize, size_t)
VELO_JOIN_W_INT(isize, ptrdiff_t)
#undef VELO_JOIN_W_INT

#define VELO_JOIN_W_FLOAT(token, ctype) \
    static inline size_t velo_join_w_##token(char* dst, const void* e) { \
        return (size_t)snprintf(dst, VELO_JOIN_MEASURE_CAP(dst), "%.2f", \
                                (double)(*(const ctype*)e)); \
    }

VELO_JOIN_W_FLOAT(f32, float)
VELO_JOIN_W_FLOAT(f64, double)
#undef VELO_JOIN_W_FLOAT

static inline size_t velo_join_w_bool(char* dst, const void* e) {
    const char* word = (*(const uint8_t*)e) ? "true" : "false";
    size_t len = strlen(word);
    if (dst != NULL) {
        memcpy(dst, word, len);
    }
    return len;
}

static inline size_t velo_join_w_string(char* dst, const void* e) {
    const char* s = *(const char* const*)e;
    size_t len = s != NULL ? strlen(s) : 0;
    if (dst != NULL && len > 0) {
        memcpy(dst, s, len);
    }
    return len;
}

// Two-pass join: measure (exact byte count), then render into one fresh
// arena buffer. The separator is copied verbatim between rendered elements.
static inline const char* velo_shelf_join_generic(const VeloShelf* s, const char* sep, VeloJoinWriteFn wr) {
    size_t seplen = sep != NULL ? strlen(sep) : 0;
    size_t total = 0;
    for (size_t i = 0; i < s->len; i++) {
        if (i > 0) {
            total += seplen;
        }
        total += wr(NULL, (const char*)s->data + i * s->esz);
    }
    char* out = (char*)velo_mem_alloc(1, total + 1);
    size_t at = 0;
    for (size_t i = 0; i < s->len; i++) {
        if (i > 0) {
            if (seplen > 0) {
                memcpy(out + at, sep, seplen);
            }
            at += seplen;
        }
        at += wr(out + at, (const char*)s->data + i * s->esz);
    }
    out[at] = '\0';
    return out;
}

#define VELO_SHELF_JOIN(suffix) \
    static inline const char* velo_shelf_join_##suffix(const VeloShelf* s, const char* sep) { \
        return velo_shelf_join_generic(s, sep, velo_join_w_##suffix); \
    }
VELO_SHELF_JOIN(i8)
VELO_SHELF_JOIN(i16)
VELO_SHELF_JOIN(i32)
VELO_SHELF_JOIN(i64)
VELO_SHELF_JOIN(u8)
VELO_SHELF_JOIN(u16)
VELO_SHELF_JOIN(u32)
VELO_SHELF_JOIN(u64)
VELO_SHELF_JOIN(usize)
VELO_SHELF_JOIN(isize)
VELO_SHELF_JOIN(f32)
VELO_SHELF_JOIN(f64)
VELO_SHELF_JOIN(bool)
VELO_SHELF_JOIN(string)
#undef VELO_SHELF_JOIN

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
// 5.2 (slice 11) — str.split returns an OWNing shelf. Python-style
// tokenization: delimiters SEPARATE, they do not merge — empty tokens are
// preserved ("a,,b" → "a","","b"), a trailing delimiter yields a trailing
// empty token ("a," → "a",""), and "" → one empty token. Each token is a
// fresh arena string; the shelf payload backs onto the ACTIVE arena
// (zone-scoped, the sorted() copy precedent — the shelf owns its tokens and
// they live and die together). The old NULL-terminated @string array + the
// mem.free idiom RETIRED with this hard swap (one owning-shelf return shape
// instead of two idioms). The delimiter may be any length. An empty
// delimiter cannot split anything and dies loudly.
// ============================================================================
static inline VeloShelf velo_str_split(const char* s, const char* delim) {
    const char* a = velo_str_nonnull(s, "str.split");
    const char* d = velo_str_nonnull(delim, "str.split");
    size_t dlen = strlen(d);
    if (dlen == 0) {
        fprintf(stderr, "Velo Fatal Error: str.split got an empty delimiter!\n");
        exit(1);
    }
    VeloShelf out = {0};
    out.esz = sizeof(const char*);
    const char* p = a;
    const char* hit;
    while ((hit = strstr(p, d)) != NULL) {
        size_t len = (size_t)(hit - p);
        char* tok = (char*)velo_mem_alloc(1, len + 1);
        memcpy(tok, p, len);
        tok[len] = 0;
        velo_shelf_put(&out, &tok, sizeof(const char*));
        p = hit + dlen;
    }
    size_t len = strlen(p);
    char* tok = (char*)velo_mem_alloc(1, len + 1);
    memcpy(tok, p, len);
    tok[len] = 0;
    velo_shelf_put(&out, &tok, sizeof(const char*));
    return out;
}

// 5.4 (sys.os): full argv as a shelf[string] — argv[0] (the program) is
// INCLUDED (documented); every entry is an OWNED copy off the argv table,
// so later CRT rewrites of argv can never alias into the Velo surface.
// An argv-less run (argc 0 — never seen on a hosted OS) yields an empty
// shelf.
static inline VeloShelf velo_os_args(void) {
    VeloShelf out = {0};
    out.esz = sizeof(const char*);
    if (g_velo_os_argv != NULL) {
        for (int i = 0; i < g_velo_os_argc; ++i) {
            const char* arg = (g_velo_os_argv[i] != NULL) ? g_velo_os_argv[i] : "";
            size_t len = strlen(arg);
            char* tok = (char*)velo_mem_alloc(1, len + 1);
            memcpy(tok, arg, len);
            tok[len] = 0;
            velo_shelf_put(&out, &tok, sizeof(const char*));
        }
    }
    return out;
}
// 5.4 (slice 3): fs.read_dir — the directory listing as a shelf[string] of
// entry NAMES (bare names, no paths; "." and ".." are filtered — the
// usable surface). A missing or unreadable directory yields an EMPTY
// shelf: the list operation never kills the program — pair it with
// fs.is_dir when the missing-vs-empty distinction matters. Ordering is
// platform/filesystem-defined (callers that need order must sort
// themselves — the batteries pin set-membership, never sequence).
// Windows rides the CRT's narrow _findfirst/_findnext/_findclose (<io.h> —
// always probed as "<path>/*" because a bare directory path would match
// only itself); POSIX rides <dirent.h> (declared under the 200112L
// flags). Shelf construction is the velo_str_split owning-token pattern
// (velo_mem_alloc + velo_shelf_put). No kernel32, no windows.h.
static inline VeloShelf velo_fs_read_dir(const char* path) {
    VeloShelf out = {0};
    out.esz = sizeof(const char*);
    if (path == NULL) return out;
#if defined(_WIN32)
    char pattern[1024];
    size_t plen = strlen(path);
    if (plen == 0 || plen + 3 >= sizeof(pattern)) return out;
    memcpy(pattern, path, plen);
    // Normalize the joiner so both separators accept sub-listing.
    if (pattern[plen - 1] != '/' && pattern[plen - 1] != '\\') {
        pattern[plen++] = '/';
    }
    pattern[plen++] = '*';
    pattern[plen] = '\0';
    struct _finddata_t fd;
    intptr_t h = _findfirst(pattern, &fd);
    if (h == -1) return out;
    do {
        const char* nm = fd.name;
        if (nm[0] == '.' && (nm[1] == '\0' || (nm[1] == '.' && nm[2] == '\0'))) continue;
        size_t len = strlen(nm);
        char* tok = (char*)velo_mem_alloc(1, len + 1);
        memcpy(tok, nm, len);
        tok[len] = 0;
        velo_shelf_put(&out, &tok, sizeof(const char*));
    } while (_findnext(h, &fd) == 0);
    _findclose(h);
#else
    DIR* dir = opendir(path);
    if (dir == NULL) return out;
    struct dirent* ent;
    while ((ent = readdir(dir)) != NULL) {
        const char* nm = ent->d_name;
        if (nm[0] == '.' && (nm[1] == '\0' || (nm[1] == '.' && nm[2] == '\0'))) continue;
        size_t len = strlen(nm);
        char* tok = (char*)velo_mem_alloc(1, len + 1);
        memcpy(tok, nm, len);
        tok[len] = 0;
        velo_shelf_put(&out, &tok, sizeof(const char*));
    }
    closedir(dir);
#endif
    return out;
}
// ============================================================================
// 5.2 (slice 6) — Map[K, V] core.
//
// ONE struct serves every key/value pairing: per-slot C knowledge lives at
// each use site (the compiler copies keys by VALUE off the typed key slot
// and passes sizeof(K)/sizeof(V) plus one key-family token at build time).
// Open addressing with linear probing; 64-bit FNV-1a over the key BYTES.
// STRING keys hash CONTENT (the characters — equality via strcmp), NOT the
// pointer: safe only because Velo strings are immutable, so a stored key can
// never alias-mutate away from its recorded hash. All other families hash
// their bytes and compare with memcmp (pinned key families never mix widths).
//
// Capacity is a power of two, growing ×2 when occupancy (len + tombstones)
// passes 0.75. Every table stores its 64-bit hash pre-OR'ed with 1, so a
// real mark is always ODD (≥ 1) — hash == 0 is the unambiguous EMPTY sentinel
// and VELO_MAP_TOMB (2) the TAKEN marker. Because tomb is even and every
// stored hash odd, the has/copy_out probe loops needed NO new guard when the
// slice-7 take() landed the reserved migration. Storage (keys, values,
// hashes) grows in the ACTIVE arena (velo_mem_alloc) and REGENERATES on
// rehash — no per-entry frees, zones reclaim wholesale (shelf doctrine).
//
// Assignment copies the HEADER; two headers share backing storage until
// either one rehashes (severed sharing — the put-through-copy window is
// documented, not an error).
//
// Probe order derives from the hash bits: patch-order iteration (S7) is
// HASH-ordered, not insertion-ordered — pinned.
// ============================================================================
#define VELO_MAP_TOMB ((uint64_t)2)
#define VELO_MAP_HEAP_SRC ((VeloAllocator)1)
typedef struct VeloMap {
    void*         keys;    // cap * ksz key bytes (inline; strings store the pointer)
    void*         vals;    // cap * vsz value bytes
    uint64_t*     hashes;  // cap hash slots (0 = empty; live hold h | 1; TOMB = 2)
    size_t        len;     // live entries
    size_t        tomb;    // tombstone slots (probes skip them; put recycles)
    size_t        cap;     // capacity (power of two)
    size_t        ksz;     // key size in bytes (sizeof(K))
    size_t        vsz;     // value size in bytes (sizeof(V))
    bool          kstring; // string keys: content hash + strcmp equality
    VeloAllocator src;     // NULL = active zone bump arena; non-NULL = persistent heap
} VeloMap;

static inline void velo_map_init(VeloMap* m, size_t ksz, bool kstring, size_t vsz) {
    m->keys = NULL; m->vals = NULL; m->hashes = NULL;
    m->len = 0; m->tomb = 0; m->cap = 0; m->ksz = ksz; m->vsz = vsz; m->kstring = kstring;
    m->src = NULL;
}

static inline void* velo_map_alloc(const VeloMap* m, size_t sz, size_t count) {
    if (m->src) return velo_heap_alloc(sz, count);
    return velo_mem_alloc(sz, count);
}

static inline uint64_t velo_map_fnv1a(const uint8_t* p, size_t n) {
    uint64_t h = (uint64_t)14695981039346656037ULL;
    for (size_t i = 0; i < n; i++) {
        h ^= (uint64_t)p[i];
        h *= (uint64_t)1099511628211ULL;
    }
    return h;
}

static inline uint64_t velo_map_key_hash(const VeloMap* m, const void* key) {
    if (m->kstring) {
        const char* s = *(const char* const*)key;
        size_t n = s != NULL ? strlen(s) : 0;
        if (n > 0) return velo_map_fnv1a((const uint8_t*)s, n) | 1;
        return 1; // ("" and NULL share the lowest hash; strcmp still orders them)
    }
    return velo_map_fnv1a((const uint8_t*)key, m->ksz) | 1;
}

static inline bool velo_map_key_eq(const VeloMap* m, const void* a, const void* b) {
    if (m->kstring) {
        const char* x = *(const char* const*)a;
        const char* y = *(const char* const*)b;
        if (x == y) return true;
        if (x == NULL || y == NULL) return false;
        return strcmp(x, y) == 0;
    }
    return memcmp(a, b, m->ksz) == 0;
}

// Regenerate: rebuild every LIVE row into fresh tables. When m->src != NULL (heap map),
// allocates via persistent heap and frees the previous keys/vals/hashes buffers.
// `new_cap` carries the ×2 grow AND the slice-7 half-cap compact (same cap,
// tomb purge) through one code path.
static inline void velo_map_regen(VeloMap* m, size_t new_cap) {
    void* nkeys = velo_map_alloc(m, m->ksz, new_cap);
    void* nvals = velo_map_alloc(m, m->vsz, new_cap);
    uint64_t* nhash = (uint64_t*)velo_map_alloc(m, sizeof(uint64_t), new_cap);
    memset(nhash, 0, sizeof(uint64_t) * new_cap);
    if (m->cap > 0) {
        for (size_t i = 0; i < m->cap; i++) {
            if (m->hashes[i] == 0 || m->hashes[i] == VELO_MAP_TOMB) continue;
            size_t at = (size_t)m->hashes[i] & (new_cap - 1);
            while (nhash[at] != 0) at = (at + 1) & (new_cap - 1);
            nhash[at] = m->hashes[i];
            memcpy((char*)nkeys + at * m->ksz, (const char*)m->keys + i * m->ksz, m->ksz);
            memcpy((char*)nvals + at * m->vsz, (const char*)m->vals + i * m->vsz, m->vsz);
        }
        if (m->src) {
            if (m->keys) velo_heap_free(m->keys);
            if (m->vals) velo_heap_free(m->vals);
            if (m->hashes) velo_heap_free(m->hashes);
        }
    }
    m->keys = nkeys;
    m->vals = nvals;
    m->hashes = nhash;
    m->cap = new_cap;
    m->tomb = 0;
}

static inline void velo_map_grow(VeloMap* m) {
    velo_map_regen(m, m->cap != 0 ? m->cap * 2 : 8);
}

// Upsert: overwrite the value when the key is already home (len unchanged,
// no growth), else take a tombstone (the slice-7 recycle: len unchanged,
// tomb -= 1) or the first empty slot past the probe start. Growth happens
// BEFORE the probe so the table always retains an empty slot (the probe
// loop below can then never wrap a full table).
static inline void velo_map_put(VeloMap* m, const void* key, const void* val) {
    if (m->ksz == 0 || m->vsz == 0) {
        fprintf(stderr, "Velo Fatal Error: map put with a zero-size key or value!\n");
        exit(1);
    }
    if ((m->len + m->tomb + 1) * 4 > m->cap * 3) velo_map_grow(m);
    uint64_t h = velo_map_key_hash(m, key);
    size_t at = (size_t)h & (m->cap - 1);
    size_t reuse = m->cap;
    while (m->hashes[at] != 0) {
        if (m->hashes[at] == h && velo_map_key_eq(m, key, (const char*)m->keys + at * m->ksz)) {
            memcpy((char*)m->vals + at * m->vsz, val, m->vsz);
            return;
        }
        if (m->hashes[at] == VELO_MAP_TOMB && reuse == m->cap) reuse = at;
        at = (at + 1) & (m->cap - 1);
    }
    if (reuse != m->cap) { at = reuse; m->tomb -= 1; }
    m->hashes[at] = h;
    memcpy((char*)m->keys + at * m->ksz, key, m->ksz);
    memcpy((char*)m->vals + at * m->vsz, val, m->vsz);
    m->len += 1;
}

static inline bool velo_map_has(const VeloMap* m, const void* key) {
    if (m->cap == 0) return false;
    uint64_t h = velo_map_key_hash(m, key);
    size_t at = (size_t)h & (m->cap - 1);
    while (m->hashes[at] != 0) {
        if (m->hashes[at] == h && velo_map_key_eq(m, key, (const char*)m->keys + at * m->ksz)) return true;
        at = (at + 1) & (m->cap - 1);
    }
    return false;
}

// Look up and copy the value OUT into the caller's slot (the deref happens
// in the same expression, so a later rehash cannot strand the pointer —
// the take() discipline applies without pointer exposure).
static inline bool velo_map_copy_out(const VeloMap* m, const void* key, void* out) {
    if (m->cap == 0) return false;
    uint64_t h = velo_map_key_hash(m, key);
    size_t at = (size_t)h & (m->cap - 1);
    while (m->hashes[at] != 0) {
        if (m->hashes[at] == h && velo_map_key_eq(m, key, (const char*)m->keys + at * m->ksz)) {
            memcpy(out, (const char*)m->vals + at * m->vsz, m->vsz);
            return true;
        }
        at = (at + 1) & (m->cap - 1);
    }
    return false;
}

// 5.2 slice 7: remove by key — the value copies out FIRST (the take()
// discipline), then the slot parks a tombstone, len drops by one. When
// tombstones pass half the cap the table compacts in place (same cap, no
// growth) so probe chains cannot rot on delete-heavy traffic. Miss returns
// false and the caller fires the loud fatal family (get/subscript words).
static inline bool velo_map_take(VeloMap* m, const void* key, void* out) {
    if (m->cap == 0) return false;
    uint64_t h = velo_map_key_hash(m, key);
    size_t at = (size_t)h & (m->cap - 1);
    while (m->hashes[at] != 0) {
        if (m->hashes[at] == h && velo_map_key_eq(m, key, (const char*)m->keys + at * m->ksz)) {
            memcpy(out, (const char*)m->vals + at * m->vsz, m->vsz);
            m->hashes[at] = VELO_MAP_TOMB;
            m->len -= 1;
            m->tomb += 1;
            if (m->tomb > (m->cap >> 1)) velo_map_regen(m, m->cap);
            return true;
        }
        at = (at + 1) & (m->cap - 1);
    }
    return false;
}

// The fatal repr: one dispatch per key-family token onto the slice-5 writers
// (dst == NULL measure pass, then render into a fresh exact fatal buffer) —
// `map key not found: <krepr>` is byte-identical to interpolation by design.
static inline size_t velo_map_key_repr(const void* key, const char* token, char* dst) {
    if (0) {}
#define VELO_MAP_REPR_T(fam) \
    else if (strcmp(token, #fam) == 0) { return velo_join_w_##fam(dst, key); }
    VELO_MAP_REPR_T(i8) VELO_MAP_REPR_T(i16) VELO_MAP_REPR_T(i32) VELO_MAP_REPR_T(i64)
    VELO_MAP_REPR_T(u8) VELO_MAP_REPR_T(u16) VELO_MAP_REPR_T(u32) VELO_MAP_REPR_T(u64)
    VELO_MAP_REPR_T(usize) VELO_MAP_REPR_T(isize) VELO_MAP_REPR_T(bool) VELO_MAP_REPR_T(string)
#undef VELO_MAP_REPR_T
    return velo_join_w_string(dst, key); // total family (tokens are compiler-pinned)
}

static inline void velo_map_fatal_missing(const VeloMap* m, const void* key, const char* token) {
    size_t need = velo_map_key_repr(key, token, NULL) + 1;
    char* buf = (char*)velo_mem_alloc(1, need);
    velo_map_key_repr(key, token, buf);
    fprintf(stderr, "Velo Fatal Error: map key not found: %s!\n", buf);
    exit(1);
}

static inline VeloMap velo_map_create_empty(size_t ksz, bool kstring, size_t vsz) {
    VeloMap m = {0};
    velo_map_init(&m, ksz, kstring, vsz);
    return m;
}

static inline VeloMap velo_map_create_lit(size_t ksz, bool kstring, size_t vsz, size_t count, const void* keys, const void* vals) {
    VeloMap m = {0};
    velo_map_init(&m, ksz, kstring, vsz);
    for (size_t i = 0; i < count; i++) {
        velo_map_put(&m, (const char*)keys + i * ksz, (const char*)vals + i * vsz);
    }
    return m;
}

static inline VeloMap velo_map_create_empty_heap(size_t ksz, bool kstring, size_t vsz) {
    VeloMap m = {0};
    velo_map_init(&m, ksz, kstring, vsz);
    m.src = VELO_MAP_HEAP_SRC;
    return m;
}

static inline VeloMap velo_map_create_lit_heap(size_t ksz, bool kstring, size_t vsz, size_t count, const void* keys, const void* vals) {
    VeloMap m = {0};
    velo_map_init(&m, ksz, kstring, vsz);
    m.src = VELO_MAP_HEAP_SRC;
    for (size_t i = 0; i < count; i++) {
        velo_map_put(&m, (const char*)keys + i * ksz, (const char*)vals + i * vsz);
    }
    return m;
}

static inline void velo_map_free(VeloMap* m) {
    if (!m) return;
    if (m->src) {
        if (m->keys) velo_heap_free(m->keys);
        if (m->vals) velo_heap_free(m->vals);
        if (m->hashes) velo_heap_free(m->hashes);
    }
    m->keys = NULL;
    m->vals = NULL;
    m->hashes = NULL;
    m->len = 0;
    m->tomb = 0;
    m->cap = 0;
}

static inline const void* velo_map_get_ptr(const VeloMap* m, const void* key) {
    if (m->cap == 0) return NULL;
    uint64_t h = velo_map_key_hash(m, key);
    size_t at = (size_t)h & (m->cap - 1);
    while (m->hashes[at] != 0) {
        if (m->hashes[at] == h && velo_map_key_eq(m, key, (const char*)m->keys + at * m->ksz)) {
            return (const char*)m->vals + at * m->vsz;
        }
        at = (at + 1) & (m->cap - 1);
    }
    return NULL;
}

static inline const void* velo_map_get_ref(const VeloMap* m, const void* key, const char* token) {
    const void* ptr = velo_map_get_ptr(m, key);
    if (!ptr) {
        velo_map_fatal_missing(m, key, token);
    }
    return ptr;
}

static inline void* velo_map_take_ref(VeloMap* m, const void* key, const char* token) {
    if (m->cap == 0) { velo_map_fatal_missing(m, key, token); }
    uint64_t h = velo_map_key_hash(m, key);
    size_t at = (size_t)h & (m->cap - 1);
    while (m->hashes[at] != 0) {
        if (m->hashes[at] == h && velo_map_key_eq(m, key, (const char*)m->keys + at * m->ksz)) {
            void* out = velo_mem_alloc(1, m->vsz);
            memcpy(out, (const char*)m->vals + at * m->vsz, m->vsz);
            m->hashes[at] = VELO_MAP_TOMB;
            m->len -= 1;
            m->tomb += 1;
            if (m->tomb > (m->cap >> 1)) velo_map_regen(m, m->cap);
            return out;
        }
        at = (at + 1) & (m->cap - 1);
    }
    velo_map_fatal_missing(m, key, token);
    return NULL;
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
// 5.2 (slice 8) — the U64 tag closes the wrap residual: u64-typed sources
// (and integer literals above the i64 range at the dyn box sites) box as
// VELO_DYN_U64 with the full uint64 payload. The tag NAME stays "int" —
// families, not tag names, are what the fatals print.
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
    VELO_DYN_CHILD = 6,
    VELO_DYN_U64 = 7
} VeloDynTag;

typedef struct VeloDyn {
    uint8_t tag;
    union { int64_t i64; uint64_t u64; double f64; bool b; const char* s; void* p; VeloShelf child; } as;
} VeloDyn;

static inline const char* velo_dyn_tag_name(uint8_t tag) {
    switch (tag) {
        case VELO_DYN_I64:   return "int";
        case VELO_DYN_U64:   return "int";   // slice 8: same family name
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

// ============================================================================
// 5.2 (slice 8) — raw-dyn operators. Both compiler stages lower a binop with
// a raw dyn operand to the same C: both operands bound once into VeloDyn
// temps (left first — evaluation order pinned), the concrete side boxed by
// its Velo type, then one of the helpers below. The numeric ladder and the
// family rules live ONLY here, so the stages cannot diverge on them.
// ============================================================================

// The int-family unbox ring: I64 and U64 boxes both serve integer reads
// (the union's i64/u64 members bit-alias). Same fatal wording shape as
// velo_dyn_expect — `expected int, found <family>!`.
static inline void velo_dyn_expect_int(VeloDyn v) {
    if (v.tag != VELO_DYN_I64 && v.tag != VELO_DYN_U64) {
        fprintf(stderr, "Velo Fatal Error: shelf[dyn] unbox: expected int, found %s!\n",
                velo_dyn_tag_name(v.tag));
        exit(1);
    }
}

static inline int64_t velo_dyn_unbox_i64(VeloDyn d) { velo_dyn_expect_int(d); return d.as.i64; }
static inline int32_t velo_dyn_unbox_i32(VeloDyn d) { velo_dyn_expect_int(d); return (int32_t)d.as.i64; }
static inline int16_t velo_dyn_unbox_i16(VeloDyn d) { velo_dyn_expect_int(d); return (int16_t)d.as.i64; }
static inline int8_t  velo_dyn_unbox_i8(VeloDyn d)  { velo_dyn_expect_int(d); return (int8_t)d.as.i64; }
static inline uint64_t velo_dyn_unbox_u64(VeloDyn d) { velo_dyn_expect_int(d); return d.as.u64; }
static inline uint32_t velo_dyn_unbox_u32(VeloDyn d) { velo_dyn_expect_int(d); return (uint32_t)d.as.u64; }
static inline uint16_t velo_dyn_unbox_u16(VeloDyn d) { velo_dyn_expect_int(d); return (uint16_t)d.as.u64; }
static inline uint8_t  velo_dyn_unbox_u8(VeloDyn d)  { velo_dyn_expect_int(d); return (uint8_t)d.as.u64; }
static inline size_t  velo_dyn_unbox_usize(VeloDyn d) { velo_dyn_expect_int(d); return (size_t)d.as.u64; }
static inline int64_t velo_dyn_unbox_isize(VeloDyn d) { velo_dyn_expect_int(d); return d.as.i64; }
static inline double  velo_dyn_unbox_f64(VeloDyn d) { velo_dyn_expect(d, VELO_DYN_F64, "float"); return d.as.f64; }
static inline float   velo_dyn_unbox_f32(VeloDyn d) { velo_dyn_expect(d, VELO_DYN_F64, "float"); return (float)d.as.f64; }
static inline bool    velo_dyn_unbox_bool(VeloDyn d) { velo_dyn_expect(d, VELO_DYN_BOOL, "bool"); return d.as.b; }
static inline const char* velo_dyn_unbox_string(VeloDyn d) { velo_dyn_expect(d, VELO_DYN_STR, "string"); return d.as.s; }
static inline void*   velo_dyn_unbox_ptr(VeloDyn d) { velo_dyn_expect(d, VELO_DYN_PTR, "pointer"); return d.as.p; }
static inline VeloShelf velo_dyn_unbox_shelf(VeloDyn d) { velo_dyn_expect(d, VELO_DYN_CHILD, "shelf"); return d.as.child; }

static inline void velo_shelf_put_dyn(VeloShelf* s, VeloDyn val) {
    velo_shelf_put(s, &val, sizeof(VeloDyn));
}

static inline void velo_shelf_insert_dyn(VeloShelf* s, size_t idx, VeloDyn val) {
    velo_shelf_insert(s, idx, &val, sizeof(VeloDyn));
}

static inline void velo_map_put_dyn(VeloMap* m, const void* key, VeloDyn val) {
    velo_map_put(m, key, &val);
}

// Compare-lattice rank: 1 = int ring (I64/U64), 2 = float, 3 = string,
// 4 = bool, 0 = pointer/shelf/none (boxed but not comparable).
static inline int velo_dyn_family_rank(uint8_t tag) {
    switch (tag) {
        case VELO_DYN_I64: case VELO_DYN_U64: return 1;
        case VELO_DYN_F64:  return 2;
        case VELO_DYN_STR:  return 3;
        case VELO_DYN_BOOL: return 4;
        default:            return 0;
    }
}

// fmod equivalent without <math.h> (no link-surface dependency): C99
// truncation toward zero gives fmod semantics exactly while the quotient
// fits int64 — the realistic range for display/game math.
static inline double velo_dyn_fmod(double a, double b) {
    double t = (double)(int64_t)(a / b);
    return a - t * b;
}

// Raw-dyn arithmetic. Numeric pairs only: int ring → i64 math (the i64
// VIEW of a U64 box — wrap residual, exact u64 math stays concrete); any
// float in the pair → f64 math (an int side promotes). Result re-boxed at
// the ladder's tag. Any other pair is a loud deterministic fatal.
static inline VeloDyn velo_dyn_arith(char op, VeloDyn l, VeloDyn r) {
    int lf = velo_dyn_family_rank(l.tag), rf = velo_dyn_family_rank(r.tag);
    if ((lf != 1 && lf != 2) || (rf != 1 && rf != 2)) {
        fprintf(stderr, "Velo Fatal Error: shelf[dyn] arith: cannot apply '%c' to %s and %s!\n",
                op, velo_dyn_tag_name(l.tag), velo_dyn_tag_name(r.tag));
        exit(1);
    }
    if (lf == 2 || rf == 2) {
        double a = (lf == 2) ? l.as.f64 : (double)l.as.i64;
        double b = (rf == 2) ? r.as.f64 : (double)r.as.i64;
        double v = 0;
        if (op == '+') { v = a + b; }
        else if (op == '-') { v = a - b; }
        else if (op == '*') { v = a * b; }
        else if (op == '/') { v = a / b; }
        else { v = velo_dyn_fmod(a, b); }
        return (VeloDyn){ .tag = VELO_DYN_F64, .as = { .f64 = v } };
    }
    int64_t a = l.as.i64, b = r.as.i64, v = 0;
    if (op == '+') { v = a + b; }
    else if (op == '-') { v = a - b; }
    else if (op == '*') { v = a * b; }
    else if (op == '/') { v = a / b; }
    else { v = a % b; }
    return (VeloDyn){ .tag = VELO_DYN_I64, .as = { .i64 = v } };
}

// Raw-dyn compare: tri-state (<0 / 0 / >0) — the caller maps the operator
// against 0. Same family required: mixed pairs fatal with the unbox wording
// (expected <right-family>, found <left-family>); same-tag pointer/shelf
// pairs are boxed but outside the compare lattice and get their own words.
static inline int64_t velo_dyn_compare(VeloDyn l, VeloDyn r) {
    int lf = velo_dyn_family_rank(l.tag), rf = velo_dyn_family_rank(r.tag);
    if (lf == 0 || rf == 0 || lf != rf) {
        if (lf == 0 && rf == 0 && l.tag == r.tag) {
            fprintf(stderr, "Velo Fatal Error: shelf[dyn] compare: %s boxes are not comparable!\n",
                    velo_dyn_tag_name(l.tag));
        } else {
            fprintf(stderr, "Velo Fatal Error: shelf[dyn] unbox: expected %s, found %s!\n",
                    velo_dyn_tag_name(r.tag), velo_dyn_tag_name(l.tag));
        }
        exit(1);
    }
    if (lf == 1) {
        if (l.tag == VELO_DYN_U64 && r.tag == VELO_DYN_U64) {
            return (l.as.u64 < r.as.u64) ? -1 : ((l.as.u64 > r.as.u64) ? 1 : 0);
        }
        int64_t a = l.as.i64, b = r.as.i64;
        return (a < b) ? -1 : ((a > b) ? 1 : 0);
    }
    if (lf == 2) {
        double a = l.as.f64, b = r.as.f64;
        return (a < b) ? -1 : ((a > b) ? 1 : 0);
    }
    if (lf == 3) {
        return (int64_t)strcmp(l.as.s, r.as.s);
    }
    return (int64_t)(l.as.b ? 1 : 0) - (int64_t)(r.as.b ? 1 : 0);
}

// ============================================================================
// 5.2 (slice 9) — ring[T]: an unbounded FIFO queue with O(1) front removal.
//
// A `ring[T]` is a zero-init VeloRing header; slots are esz-sized bytes in
// the ACTIVE arena. `head` names the front element in mask space; put
// enqueues at (head + len) & (cap-1), pop/peek read head and advance it.
// Growth doubles the capacity (min 8) and REGENERATES the slot array
// unrolled (front -> slot 0) in fresh arena storage — no per-element frees
// (the shelf/map regeneration doctrine). The differentiator vs shelf is
// O(1) FRONT removal; bounded capacity can layer on later.
// ============================================================================
typedef struct VeloRing {
    size_t esz;     // element size (compiler-known slot layout knowledge)
    size_t cap;     // power-of-two slot capacity (0 = empty)
    size_t head;    // front index in mask space
    size_t len;     // live elements
    void* data;     // arena-backed slot array (esz * cap bytes)
} VeloRing;

static inline void velo_ring_fatal_empty(const char* what) {
    fprintf(stderr, "Velo Fatal Error: ring %s from an empty ring!\n", what);
    exit(1);
}

// Growth for the next enqueue: double the capacity, copy the live elements
// UNROLLED (front first) into fresh arena storage.
static inline void velo_ring_reserve(VeloRing* r, size_t esz) {
    if (r->data != NULL && r->len < r->cap) return;
    size_t new_cap = r->cap ? r->cap * 2 : 8;
    void* next = velo_mem_alloc(esz, new_cap);
    for (size_t i = 0; i < r->len; ++i) {
        memcpy((char*)next + i * esz,
               (const char*)r->data + ((r->head + i) & (r->cap - 1)) * esz, esz);
    }
    r->data = next;
    r->cap = new_cap;
    r->head = 0;
}

static inline void velo_ring_put(VeloRing* r, const void* val, size_t esz) {
    if (r->esz == 0) r->esz = esz;
    else if (r->esz != esz) {
        fprintf(stderr, "Velo Fatal Error: ring element size mismatch: %llu vs %llu!\n",
                (unsigned long long)esz, (unsigned long long)r->esz);
        exit(1);
    }
    velo_ring_reserve(r, esz);
    memcpy((char*)r->data + ((r->head + r->len) & (r->cap - 1)) * esz, val, esz);
    r->len += 1;
}

// Dequeue-front: the value copies out FIRST, then the head advances (the
// take discipline). Empty is the loud deterministic fatal family.
static inline void velo_ring_pop(VeloRing* r, void* out, size_t esz) {
    if (r->esz == 0) r->esz = esz;
    else if (r->esz != esz) {
        fprintf(stderr, "Velo Fatal Error: ring element size mismatch: %llu vs %llu!\n",
                (unsigned long long)esz, (unsigned long long)r->esz);
        exit(1);
    }
    if (r->len == 0) velo_ring_fatal_empty("pop");
    memcpy(out, (const char*)r->data + r->head * esz, esz);
    r->head = (r->head + 1) & (r->cap - 1);
    r->len -= 1;
}

// Read-front without consuming (read tier — legal on a let). The empty
// check comes FIRST: a zero-init ring has esz 0, which is not a mismatch.
static inline void velo_ring_peek(const VeloRing* r, void* out, size_t esz) {
    if (r->len == 0) velo_ring_fatal_empty("peek");
    if (r->esz != esz) {
        fprintf(stderr, "Velo Fatal Error: ring element size mismatch: %llu vs %llu!\n",
                (unsigned long long)esz, (unsigned long long)r->esz);
        exit(1);
    }
    memcpy(out, (const char*)r->data + r->head * esz, esz);
}

static inline VeloRing velo_ring_create_empty(size_t esz) {
    VeloRing r = {0};
    r.esz = esz;
    return r;
}

static inline VeloRing velo_ring_create_lit(size_t esz, size_t count, const void* elems) {
    VeloRing r = {0};
    r.esz = esz;
    for (size_t i = 0; i < count; i++) {
        velo_ring_put(&r, (const char*)elems + i * esz, esz);
    }
    return r;
}

static inline void* velo_ring_pop_ref(VeloRing* r, size_t esz) {
    if (r->esz == 0) r->esz = esz;
    else if (r->esz != esz) {
        fprintf(stderr, "Velo Fatal Error: ring element size mismatch: %llu vs %llu!\n",
                (unsigned long long)esz, (unsigned long long)r->esz);
        exit(1);
    }
    if (r->len == 0) velo_ring_fatal_empty("pop");
    void* val_ptr = (char*)r->data + r->head * esz;
    r->head = (r->head + 1) & (r->cap - 1);
    r->len -= 1;
    return val_ptr;
}

static inline const void* velo_ring_peek_ref(const VeloRing* r, size_t esz) {
    if (r->len == 0) velo_ring_fatal_empty("peek");
    if (r->esz != esz) {
        fprintf(stderr, "Velo Fatal Error: ring element size mismatch: %llu vs %llu!\n",
                (unsigned long long)esz, (unsigned long long)r->esz);
        exit(1);
    }
    return (const char*)r->data + r->head * esz;
}

// ============================================================================
// 5.2 (slice 9) — bitset: an arena-backed u64 word array, grow-on-set.
//
// A `bitset` is a zero-init VeloBitset header; set/toggle GROW the word
// array to cover the index (grow-on-set like shelf), clear beyond coverage
// is a no-op (the bit is already unset) and has beyond coverage reads false
// (an unset bit — required so first_unset composes). A NEGATIVE index is
// the only out-of-bounds: a loud deterministic fatal on every index-taking
// op. Pair ops (and/or_with/xor_with) operate IN PLACE over the target's
// words with the other's out-of-range words read as 0; flip complements the
// MATERIALIZED words (a bitset models its materialized words, not an
// infinite bit plane — documented).
// ============================================================================
typedef struct VeloBitset {
    size_t words;   // materialized 64-bit words
    uint64_t* bits; // arena-backed
} VeloBitset;

static inline void velo_bitset_oob(int64_t i) {
    fprintf(stderr, "Velo Fatal Error: bitset index out of bounds: %lld!\n",
            (long long)i);
    exit(1);
}

static inline void velo_bitset_grow(VeloBitset* b, size_t need_words) {
    if (b->words >= need_words) return;
    uint64_t* next = (uint64_t*)velo_mem_alloc(sizeof(uint64_t), need_words);
    for (size_t i = 0; i < b->words; ++i) next[i] = b->bits[i];
    for (size_t i = b->words; i < need_words; ++i) next[i] = 0;
    b->bits = next;
    b->words = need_words;
}

static inline void velo_bitset_set(VeloBitset* b, int64_t i) {
    if (i < 0) velo_bitset_oob(i);
    size_t w = (size_t)i / 64;
    velo_bitset_grow(b, w + 1);
    b->bits[w] |= (uint64_t)1 << (i % 64);
}

static inline void velo_bitset_clear(VeloBitset* b, int64_t i) {
    if (i < 0) velo_bitset_oob(i);
    size_t w = (size_t)i / 64;
    if (w >= b->words) return;   // beyond coverage: already unset
    b->bits[w] &= ~((uint64_t)1 << (i % 64));
}

static inline void velo_bitset_toggle(VeloBitset* b, int64_t i) {
    if (i < 0) velo_bitset_oob(i);
    size_t w = (size_t)i / 64;
    velo_bitset_grow(b, w + 1);
    b->bits[w] ^= (uint64_t)1 << (i % 64);
}

static inline bool velo_bitset_has(const VeloBitset* b, int64_t i) {
    if (i < 0) velo_bitset_oob(i);
    size_t w = (size_t)i / 64;
    if (w >= b->words) return false;
    return (b->bits[w] >> (i % 64)) & 1;
}

static inline size_t velo_bitset_count(const VeloBitset* b) {
    size_t n = 0;
    for (size_t w = 0; w < b->words; ++w) {
        uint64_t v = b->bits[w];
        while (v) { v &= v - 1; n += 1; }   // Kernighan popcount (no builtins)
    }
    return n;
}

// The first zero bit from index 0; on an all-ones bitset this is words*64
// (the next unset — the slot the next set would grow into). Total function.
static inline int64_t velo_bitset_first_unset(const VeloBitset* b) {
    for (size_t w = 0; w < b->words; ++w) {
        if (b->bits[w] != UINT64_MAX) {
            uint64_t inv = ~b->bits[w];
            int64_t bit = 0;
            while (((inv >> bit) & 1) == 0) bit += 1;
            return (int64_t)(w * 64) + bit;
        }
    }
    return (int64_t)(b->words * 64);
}

static inline void velo_bitset_and(VeloBitset* a, const VeloBitset* o) {
    for (size_t w = 0; w < a->words; ++w) {
        uint64_t other = (w < o->words) ? o->bits[w] : 0;
        a->bits[w] &= other;
    }
}

// or/xor must MATERIALIZE the other's beyond-coverage bits (a union that
// drops them is not a union), so both grow the target first; and treats the
// other's out-of-range words as 0 (zeroing target bits beyond — exact).
static inline void velo_bitset_or(VeloBitset* a, const VeloBitset* o) {
    if (o->words > a->words) velo_bitset_grow(a, o->words);
    for (size_t w = 0; w < a->words; ++w) {
        uint64_t other = (w < o->words) ? o->bits[w] : 0;
        a->bits[w] |= other;
    }
}

static inline void velo_bitset_xor(VeloBitset* a, const VeloBitset* o) {
    if (o->words > a->words) velo_bitset_grow(a, o->words);
    for (size_t w = 0; w < a->words; ++w) {
        uint64_t other = (w < o->words) ? o->bits[w] : 0;
        a->bits[w] ^= other;
    }
}

static inline void velo_bitset_flip(VeloBitset* b) {
    for (size_t w = 0; w < b->words; ++w) b->bits[w] = ~b->bits[w];
}

static inline VeloBitset velo_bitset_create_lit(size_t count, const int64_t* items) {
    VeloBitset b = {0};
    for (size_t i = 0; i < count; i++) {
        velo_bitset_set(&b, items[i]);
    }
    return b;
}


// --- stdout capture support (structured diagnostics for 'velo check --json') ---
// Redirects fd 1 into a file, isolating diagnostics from the JSON stream on
// stdout. The saved descriptor is not explicitly closed (process-exit reclaims).
#ifdef _WIN32
#include <io.h>
#pragma comment(lib, "ws2_32.lib")
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

// ============================================================================
// 6.5 Native Integrated Test Runner: assertions & test context
// ============================================================================

typedef struct VeloTestContext {
    jmp_buf jmp;
    int current_test_failed;
    const char* failure_file;
    int failure_line;
    const char* failure_expr;
    const char* failure_msg;
} VeloTestContext;

static VELO_TLS VeloTestContext* g_velo_current_test = NULL;

static inline void velo_mem_init(void) {
    velo_zone_active();
}

static inline void velo_mem_reset(void) {
    if (g_velo_zone_tls_active) {
        velo_zone_free_chunks(g_velo_zone_tls_active);
        if (g_velo_zone_tls_active->wm_heap) {
            free(g_velo_zone_tls_active->wm_heap);
            g_velo_zone_tls_active->wm_heap = NULL;
        }
        g_velo_zone_tls_active->wm_count = 0;
        g_velo_zone_tls_active->wm_cap = 0;
        g_velo_zone_tls_active->offset = 0;
    }
}

static inline void velo_assert_fail(const char* expr_str, const char* file, int line, const char* msg) {
    if (g_velo_current_test) {
        g_velo_current_test->current_test_failed = 1;
        g_velo_current_test->failure_file = file;
        g_velo_current_test->failure_line = line;
        g_velo_current_test->failure_expr = expr_str;
        g_velo_current_test->failure_msg = msg;
        longjmp(g_velo_current_test->jmp, 1);
    } else {
        if (msg && msg[0]) {
            fprintf(stderr, "[Velo Fatal] Assertion failed at %s:%d: assert(%s): %s\n", file, line, expr_str, msg);
        } else {
            fprintf(stderr, "[Velo Fatal] Assertion failed at %s:%d: assert(%s)\n", file, line, expr_str);
        }
        exit(1);
    }
}

#define velo_assert(cond, file, line, msg) do { \
    if (!(cond)) { \
        velo_assert_fail(#cond, file, line, msg); \
    } \
} while (0)

/* Velo Compile-Time Null Safety & Optional Types (?T) */
typedef struct { bool has; int8_t val; } _Velo_Opt_i8;
typedef struct { bool has; int16_t val; } _Velo_Opt_i16;
typedef struct { bool has; int32_t val; } _Velo_Opt_i32;
typedef struct { bool has; int64_t val; } _Velo_Opt_i64;
typedef struct { bool has; uint8_t val; } _Velo_Opt_u8;
typedef struct { bool has; uint16_t val; } _Velo_Opt_u16;
typedef struct { bool has; uint32_t val; } _Velo_Opt_u32;
typedef struct { bool has; uint64_t val; } _Velo_Opt_u64;
typedef struct { bool has; float val; } _Velo_Opt_f32;
typedef struct { bool has; double val; } _Velo_Opt_f64;
typedef struct { bool has; bool val; } _Velo_Opt_bool;
typedef struct { bool has; size_t val; } _Velo_Opt_usize;
typedef struct { bool has; ptrdiff_t val; } _Velo_Opt_isize;

static inline void* velo_opt_unwrap_ptr(const void* ptr, const char* file, int line, int col) {
    if (!ptr) {
        fprintf(stderr, "[Velo Panic] Unexpected null unwrap at %s:%d:%d\n", file, line, col);
        exit(1);
    }
    return (void*)ptr;
}

static inline void* velo_opt_coalesce_ptr(const void* ptr, const void* fallback) {
    return ptr ? (void*)ptr : (void*)fallback;
}

static inline int32_t velo_opt_unwrap_i32(_Velo_Opt_i32 opt, const char* file, int line, int col) {
    if (!opt.has) {
        fprintf(stderr, "[Velo Panic] Unexpected null unwrap at %s:%d:%d\n", file, line, col);
        exit(1);
    }
    return opt.val;
}

static inline int64_t velo_opt_unwrap_i64(_Velo_Opt_i64 opt, const char* file, int line, int col) {
    if (!opt.has) {
        fprintf(stderr, "[Velo Panic] Unexpected null unwrap at %s:%d:%d\n", file, line, col);
        exit(1);
    }
    return opt.val;
}

static inline uint64_t velo_opt_unwrap_u64(_Velo_Opt_u64 opt, const char* file, int line, int col) {
    if (!opt.has) {
        fprintf(stderr, "[Velo Panic] Unexpected null unwrap at %s:%d:%d\n", file, line, col);
        exit(1);
    }
    return opt.val;
}

static inline double velo_opt_unwrap_f64(_Velo_Opt_f64 opt, const char* file, int line, int col) {
    if (!opt.has) {
        fprintf(stderr, "[Velo Panic] Unexpected null unwrap at %s:%d:%d\n", file, line, col);
        exit(1);
    }
    return opt.val;
}

static inline bool velo_opt_unwrap_bool(_Velo_Opt_bool opt, const char* file, int line, int col) {
    if (!opt.has) {
        fprintf(stderr, "[Velo Panic] Unexpected null unwrap at %s:%d:%d\n", file, line, col);
        exit(1);
    }
    return opt.val;
}

static inline void velo_panic_range_step(int line, int col) {
    if (line > 0 && col > 0) {
        fprintf(stderr, "[Velo Panic] Range loop step must be greater than zero at line %d, col %d\n", line, col);
    } else {
        fprintf(stderr, "[Velo Panic] Range loop step must be greater than zero\n");
    }
    exit(1);
}

#endif // VELO_RUNTIME_H
