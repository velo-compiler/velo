# Velo Compiler Architecture (Stage 1)

This document describes the internal engineering, pipeline stages, and runtime architecture of the Stage 1 Velo bootstrap compiler.

---

## 1. Pipeline Overview

The Stage 1 compiler is structured as a 5-phase pipeline written in Python:

```
Source (.vl)
   │
   ▼
[ 1. Lexer ] ────────────► Token Stream (line & col tracking)
   │
   ▼
[ 2. Parser ] ───────────► Abstract Syntax Tree (AST)
   │
   ▼
[ 3. Semantic Analyzer ] ─► Symbol Table + Type Resolution + Validation
   │
   ▼
[ 4. C99 Codegen ] ──────► Generated C Source (.c) + "velo_runtime.h"
   │
   ▼
[ 5. GCC Driver ] ───────► Native Executable (.exe)
```

---

## 2. Component Details

### 2.1 Lexer (`velo/lexer.py`)
* Converts raw UTF-8 source text into a sequential stream of `Token` instances.
* Tracks line numbers and column offsets for compiler diagnostic messages.
* Handles special Velo tokens:
  * `@` (Address-of / Pointer token)
  * `..` (Range token)
  * `->` (Return type arrow)
  * Compound operators: `+=`, `-=`, `*=`, `/=`, `==`, `!=`, `<=`, `>=`.
* String literal scanner extracts raw characters while preserving escaped characters.

### 2.2 Parser (`velo/parser.py`)
* Implemented as a **Recursive Descent Parser** with **Pratt parsing** (precedence climbing) for binary and unary expressions.
* Strictly enforces the **Operator Precedence Table** specified in `SPECIFICATION.md`:
  * Member access (`.`) binds tighter than address-of (`@`).
* Handles optional semicolons: newlines act as statement terminators, while semicolons `;` allow multiple statements on one line.

### 2.3 Semantic Analyzer & Symbol Table (`velo/checker.py`)
The Semantic Analyzer walks the AST and builds a **Symbol Table** before code generation. This solves the fundamental challenge of emitting correct C code:

```
Global Scope
  ├── Types: (Point, Particle, i32, f32...)
  ├── Functions: (update, main, puts...)
  └── Function Scope: act update(p: @Particle, dt: f32)
        ├── p  -> Type: Pointer(Particle), is_mut: false
        └── dt -> Type: Primitive(f32), is_mut: false
```

#### Responsibilities:
1. **Pointers vs. Values**: When inspecting `p.x`, the compiler checks the Symbol Table for `p`.
   * If `p` has type `Pointer(T)` $\to$ codegen emits `p->x`.
   * If `p` has type `T` $\to$ codegen emits `p.x`.
2. **Mutability Verification**: Assigning to a variable that was not declared with `mut` halts compilation with:
   `Error at line 14: cannot assign to immutable variable 'x'. Declare with 'mut x' to allow mutation.`
3. **Type Resolution for String Interpolation**:
   When lowering `"Frame: {step}"`, the analyzer inspects `step` in the Symbol Table. Seeing `step` is `i32`, it instructs the code generator to emit a `printf` call with `%d`.

### 2.4 C99 Code Generator (`velo/codegen_c.py`)
Translates the annotated AST into standard, portable C99:
* Automatically includes `#include "velo_runtime.h"`.
* Emits C struct definitions for all `data` declarations.
* Emits C function prototypes and implementations for all `act` declarations.
* Translates Velo pointers:
  * `@T` $\to$ `T*`
  * `@x` $\to$ `&x`
  * `p.@ = 20` $\to$ `*p = 20`
* Translates `zone` blocks into scoped arena pushes and pops:
  ```c
  // Velo: zone { ... }
  // Generated C:
  {
      size_t _zone_watermark = velo_zone_push();
      // ... allocations inside zone use the current arena ...
      velo_zone_pop(_zone_watermark);
  }
  ```

### 2.5 The Velo Runtime Header (`velo/runtime/velo_runtime.h`)
A lightweight, zero-dependency C header included in every generated C file:

```c
#ifndef VELO_RUNTIME_H
#define VELO_RUNTIME_H

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

// Standard primitive aliases
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

// 16 MB Hardware Arena Buffer
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
    // 8-byte alignment
    size_t aligned = (total + 7) & ~7;
    if (g_velo_arena_offset + aligned > VELO_ZONE_BUFFER_SIZE) {
        fprintf(stderr, "Velo Fatal Error: Zone Arena Out of Memory (16MB exceeded)!\n");
        exit(1);
    }
    void* ptr = &g_velo_arena[g_velo_arena_offset];
    g_velo_arena_offset += aligned;
    return ptr;
}

#endif // VELO_RUNTIME_H
```

### 2.6 Compiler Driver (`velo/driver.py`)
Coordinates the pipeline:
1. Compiles `.vl` source into a temporary `.c` file.
2. Locates `gcc.exe` in the system PATH.
3. Invokes:
   ```bash
   gcc -O2 -std=c99 <generated.c> -I <runtime_dir> -o <target.exe>
   ```
4. If running with `velo run`, executes the generated `.exe` and forwards any command-line arguments.
