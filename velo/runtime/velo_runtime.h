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

// 32 MB Zone Arena Buffer
// (Doubled from 16 MB when the compiler source outgrew its margin during the
// 'velo check' milestone; §4.1 multi-arena remains the real long-term fix.)
#define VELO_ZONE_BUFFER_SIZE (32 * 1024 * 1024)

static uint8_t  g_velo_arena[VELO_ZONE_BUFFER_SIZE];
static size_t   g_velo_arena_offset = 0;

static inline size_t velo_zone_push(void) {
    return g_velo_arena_offset;
}

static inline void velo_zone_pop(size_t watermark) {
    g_velo_arena_offset = watermark;
}

static inline size_t velo_mem_used(void) {
    return g_velo_arena_offset;
}

static inline void* velo_mem_alloc(size_t size, size_t count) {
    size_t total = size * count;
    size_t aligned = (total + 7) & ~((size_t)7);
    if (g_velo_arena_offset + aligned > VELO_ZONE_BUFFER_SIZE) {
        fprintf(stderr, "Velo Fatal Error: Zone Arena Out of Memory (16MB exceeded)!\n");
        exit(1);
    }
    void* ptr = (void*)&g_velo_arena[g_velo_arena_offset];
    g_velo_arena_offset += aligned;
    return ptr;
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
