#ifndef VELO_RUNTIME_H
#define VELO_RUNTIME_H

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stddef.h>

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

// 16 MB Zone Arena Buffer
#define VELO_ZONE_BUFFER_SIZE (16 * 1024 * 1024)

static uint8_t  g_velo_arena[VELO_ZONE_BUFFER_SIZE];
static size_t   g_velo_arena_offset = 0;

static inline size_t velo_zone_push(void) {
    return g_velo_arena_offset;
}

static inline void velo_zone_pop(size_t watermark) {
    g_velo_arena_offset = watermark;
}

static inline void* velo_mem_alloc(size_t size, size_t count) {
    size_t total = size * count;
    // Align to 8 bytes for CPU speed
    size_t aligned = (total + 7) & ~((size_t)7);
    if (g_velo_arena_offset + aligned > VELO_ZONE_BUFFER_SIZE) {
        fprintf(stderr, "Velo Fatal Error: Zone Arena Out of Memory (16MB exceeded)!\n");
        exit(1);
    }
    void* ptr = (void*)&g_velo_arena[g_velo_arena_offset];
    g_velo_arena_offset += aligned;
    return ptr;
}

// Built-in IO primitives
static inline void velo_io_println(const char* str) {
    printf("%s\n", str);
}

static inline void velo_io_print(const char* str) {
    printf("%s", str);
}

#endif // VELO_RUNTIME_H
