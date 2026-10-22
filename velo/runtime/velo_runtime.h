#ifndef VELO_RUNTIME_H
#define VELO_RUNTIME_H

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stddef.h>
#include <time.h>

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
// §4.1 Extensible Allocator Architecture
//
// Allocation model (in allocation-cost order, all O(1)):
//   * Active zone arena  — bump region produced by `zone { ... }` / sized
//     `zone <bytes> { ... }` blocks and by `mem.alloc(...)` calls.
//   * Persistent heap    — malloc-backed, tracked (`mem.heap_alloc` / free).
//
// Zone arenas are first-class objects (VeloZoneArena): the default arena uses
// a static buffer so bare `zone { }` blocks keep their exact previous
// behavior and zero startup cost; `zone <bytes> { }` blocks acquire a
// private heap-backed arena from a reuse pool (capacity >= requested, reused
// across re-entries) for the block's duration. Allocation always targets the
// ACTIVE arena, so nested zones scope independently.
// ============================================================================
typedef struct VeloZoneArena {
    uint8_t* base;    // start of the bump region
    size_t   cap;     // usable capacity in bytes
    size_t   offset;  // bump watermark (== allocated bytes right now)
} VeloZoneArena;

#define VELO_ZONE_BUFFER_SIZE (32 * 1024 * 1024)
static uint8_t        g_velo_arena_buffer[VELO_ZONE_BUFFER_SIZE];
static VeloZoneArena  g_velo_arena_default = { g_velo_arena_buffer, VELO_ZONE_BUFFER_SIZE, 0 };
static VeloZoneArena* g_velo_zone_active    = &g_velo_arena_default;

// Reuse pool for private arenas (cycled across re-entries of `zone <b> { }`)
#define VELO_ZONE_POOL_MAX 32
static VeloZoneArena  g_velo_zone_pool[VELO_ZONE_POOL_MAX];
static size_t         g_velo_zone_pool_count = 0;

static inline size_t velo_zone_push(void) {
    return g_velo_zone_active->offset;
}

static inline void velo_zone_pop(size_t watermark) {
    g_velo_zone_active->offset = watermark;
}

static inline size_t velo_mem_used(void) {
    return g_velo_zone_active->offset;
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
    VeloZoneArena* prev = g_velo_zone_active;
    VeloZoneArena* z = (VeloZoneArena*)malloc(sizeof(VeloZoneArena));
    size_t pick = g_velo_zone_pool_count;
    for (size_t i = 0; i < g_velo_zone_pool_count; ++i) {
        if (g_velo_zone_pool[i].cap >= bytes) {  // reuse any arena that fits
            pick = i;
            break;
        }
    }
    if (pick < g_velo_zone_pool_count) {
        *z = g_velo_zone_pool[pick];  // buffer ownership moves to the copy
        g_velo_zone_pool[pick] = g_velo_zone_pool[g_velo_zone_pool_count - 1];
        g_velo_zone_pool_count--;
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
    g_velo_zone_active = z;
    return prev;
}

// Exits a zone block: returns the active arena to the reuse pool (dropping
// its buffer only if the pool is saturated) and restores the previous one.
static inline void velo_zone_leave(VeloZoneArena* prev) {
    VeloZoneArena* z = g_velo_zone_active;
    if (z != &g_velo_arena_default) {
        if (g_velo_zone_pool_count < VELO_ZONE_POOL_MAX) {
            g_velo_zone_pool[g_velo_zone_pool_count++] = *z;
        } else {
            free(z->base);
        }
        free(z);
    }
    g_velo_zone_active = prev;
}

static inline void* velo_mem_alloc(size_t size, size_t count) {
    VeloZoneArena* z = g_velo_zone_active;
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

// Persistent Heap Allocation with Memory Usage Tracking
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
    g_velo_heap_active += total;
    return (void*)(raw + header_size);
}

static inline void velo_heap_free(void* ptr) {
    if (!ptr) return;
    size_t header_size = (sizeof(size_t) + 15) & ~((size_t)15);
    uint8_t* raw = ((uint8_t*)ptr) - header_size;
    size_t total = *((size_t*)raw);
    if (g_velo_heap_active >= total) {
        g_velo_heap_active -= total;
    } else {
        g_velo_heap_active = 0;
    }
    free(raw);
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
