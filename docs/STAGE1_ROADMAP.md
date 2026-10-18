# Velo Stage 1 Roadmap: Bootstrap to Self-Hosting

This document tracks the phased milestones to complete Stage 1 of the Velo programming language and prepare for self-hosting.

---

## Stage 1 Milestones

### Milestone 1: The Walking Skeleton ("Hello World")
* **Goal**: End-to-end pipeline verification from `.vl` file to executable output.
* **Deliverables**:
  * Basic Lexer: Identifiers, strings, braces, keywords (`act`, `use`).
  * Basic Parser: Program with single `act main()` function calling `io.println("Hello")`.
  * Basic C-Codegen: Emits `#include <stdio.h>` and `int main()`.
  * Driver: `python velo.py run examples/01_hello.vl` prints `Hello, Velo!` to terminal.
* **Exit Criteria**: `examples/01_hello.vl` compiles with GCC and executes successfully.

---

### Milestone 2: Variables, Arithmetic, and Control Flow
* **Goal**: Support standard imperative programming and computation.
* **Deliverables**:
  * Lexer support for numbers, operators (`+`, `-`, `*`, `/`, `%`, `==`, `!=`, `<`, `>`, `<=`, `>=`).
  * Variable declarations: `x: i32 = 10`, `mut counter = 0`.
  * Statements: `if` / `else if` / `else`, `while`, and `loop i in start..end`.
  * Expression precedence parser (Pratt parsing).
* **Exit Criteria**: `examples/02_math_and_logic.vl` calculates fibonacci / math operations and prints correct output.

---

### Milestone 3: Structs (`data`) & The `@` Pointer System
* **Goal**: Core low-level data representation and memory address manipulation.
* **Deliverables**:
  * `data Point { x: f32, y: f32 }` struct definitions and instantiation.
  * Pointer types: `@T`.
  * Address-of operator: `@x`.
  * Auto-dereferencing member access: `p.x` translates to `p->x` in C.
  * Direct pointer value dereference: `p.@ = 42` translates to `*p = 42` in C.
* **Exit Criteria**: `examples/03_pointers.vl` passes pointer to function, modifies struct, and verifies changes.

---

### Milestone 4: Hardware `zone` Arena Allocator & C FFI
* **Goal**: Game-engine-ready memory management without a Garbage Collector.
* **Deliverables**:
  * C runtime header `velo_runtime.h` with bump-allocator arena.
  * `zone { ... }` block translation: automatic push/pop of arena offset.
  * `mem.alloc(@Type, count)` primitive.
  * `extern act` declaration for calling existing C functions.
* **Exit Criteria**: `examples/04_zone_memory.vl` allocates and cleans up memory across thousands of iterations with 0 bytes leaked.

---

### Milestone 5: The Benchmark (2D Particle Simulation)
* **Goal**: The flagship Stage 1 demonstration running at full native speed.
* **Deliverables**:
  * Compiles `examples/05_particles.vl` without warnings.
  * Runs multiple frame steps simulating particles with velocity and lifetime updates.
  * Verifies performance against a native C equivalent.
* **Exit Criteria**: Full particle demo completes with matching numerical results and 0 memory leaks.

---

## Looking Ahead: Stage 2 (Self-Hosting)

Once Milestone 5 is complete:
1. Write `compiler/lexer.vl` in Velo.
2. Write `compiler/parser.vl` in Velo.
3. Write `compiler/codegen.vl` in Velo.
4. Compile the Velo compiler using the Python bootstrap compiler.
5. The result is `velo.exe`—a 100% standalone, self-hosted native compiler!
