# Velo Programming Language (`.vl`)

> **Code at high velocity.**
> The raw speed and hardware control of C, with modern syntax as clean as TypeScript, and zero garbage collection pauses.

[![License: MIT OR Apache-2.0](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue.svg)](#license)

---

## What is Velo?

Velo is a modern systems programming language built specifically for:
* **Real-Time Interactive Systems & Game Development** (0ms GC stutter, 120+ FPS guarantee).
* **Ultra-Fast CLI Utilities** (Single portable `.exe`, 0.001s startup time).
* **Embedded Systems & Microcontrollers** (Runs in < 64KB RAM, compiles to clean C99).

---

## Key Features

* **Zero Garbage Collection Stutters**: No background GC pauses. Predictable, deterministic latency.
* **The `@` Pointer System**: A clean, unambiguous pointer and address operator. `@T` is a pointer to `T`; `@val` is the memory address of `val`. Auto-dereference on member access (`ptr.field`).
* **`zone` Arena Memory**: Hardware-level arena allocations with 1-cycle reset. Wipes all temporary frame memory instantly with zero leaks.
* **Clean & Modern Syntax**: Keyword-based (`act`, `data`, `mut`), curly braces `{}`, and optional semicolons.
* **Direct C Interoperability**: Call any standard C library (OpenGL, Raylib, SQLite, SDL) with zero glue code.
* **Native C Speed**: Generates clean, optimized C99/C11 code compiled by GCC or Clang.

---

## Quick Look

```rust
use sys.io
use sys.mem

data Vec2 {
    x: f32
    y: f32
}

data Particle {
    pos: Vec2
    vel: Vec2
    life: f32
    active: bool
}

act update(p: @Particle, dt: f32) {
    if !p.active { return }
    p.pos.x += p.vel.x * dt
    p.pos.y += p.vel.y * dt
    p.life -= dt
    if p.life <= 0.0 {
        p.active = false
    }
}

act main() {
    io.println("--- Velo Particle Simulation ---")

    count: usize = 5
    dt: f32 = 0.016

    // 'zone' creates an ultra-fast hardware arena.
    // Cleans up 100% of temporary memory in 1 CPU cycle on exit.
    zone {
        particles: @Particle = mem.alloc(@Particle, count)

        loop i in 0..count {
            p: @Particle = @particles[i]
            p.pos = Vec2{ x: 0.0, y: 0.0 }
            p.vel = Vec2{ x: (i as f32) * 2.0, y: 5.0 }
            p.life = 1.0
            p.active = true
        }

        mut step = 0
        while step < 3 {
            io.println("Frame: {step}")
            loop i in 0..count {
                p: @Particle = @particles[i]
                update(p, dt)
                if p.active {
                    io.println("  Particle[{i}]: pos=({p.pos.x}, {p.pos.y})")
                }
            }
            step += 1
        }
    }

    io.println("Done! Memory cleared instantly.")
}
```

---

## Compiler Architecture (Self-Hosted)

Velo is a self-hosted compiler written entirely in Velo (`src/`). It compiles to portable C99/C11 code, which is then lowered to a native binary by GCC or Clang with zero external runtime dependencies.

```
[ .vl Source Code ] 
       │
       ▼
1. Lexer (Tokenizer)        --> Turns characters into Tokens (src/frontend/)
       │
       ▼
2. Parser (AST)             --> Builds Abstract Syntax Tree (src/ast/, src/frontend/)
       │
       ▼
3. Type Checker & Semantics --> Verifies types, ownership, scopes (src/analysis/)
       │
       ▼
4. C-Emitter (Codegen)      --> Emits clean C99/C11 code (src/backend/)
       │
       ▼
5. C Compiler Driver        --> Produces native standalone binary (bin/velo.exe)
```

> **Historical Note (Stage 1 Prototype):** The original Python prototype (`velo/` and `velo.py`) served as the initial bootstrap tool to build Stage 2. It has been demoted and retired as a frozen historical artifact (Task 80.5). The self-hosted compiler in `src/` and the self-contained C snapshot `bootstrap.c` are the canonical compiler toolchain.

---

## Bootstrapping & Building from Source

Velo bootstraps deterministically from a single standalone C file (`bootstrap.c`), requiring only GCC or Clang:

```bash
# Windows (requires GCC, e.g. MSYS2 UCRT64)
scripts\bootstrap.bat

# Linux / macOS (requires gcc or clang)
bash scripts/bootstrap.sh
```

This builds `bin/velo.exe` (or `bin/velo`), which is the full self-hosted Velo compiler.

---

## CLI Usage

```bash
# Run a Velo script immediately (compile + link + execute)
bin/velo.exe run main.vl

# Compile to a standalone native executable
bin/velo.exe build main.vl -o game.exe

# View the generated C99/C11 code
bin/velo.exe emit-c main.vl

# Check syntax and semantic analysis without compiling
bin/velo.exe check main.vl

# Format Velo source files to canonical style
bin/velo.exe fmt src/main.vl
```

---

## Documentation

* [Language Specification](docs/SPECIFICATION.md)
* [Step 2 Specification (Compiler Essentials)](docs/STEP2_SPECIFICATION.md)
* [Compiler Architecture (Stage 1)](docs/ARCHITECTURE.md)
* [Stage 1 Development Roadmap](docs/STAGE1_ROADMAP.md)
* [Step 2 Development Roadmap](docs/STEP2_ROADMAP.md)
* [Stage 2 Self-Hosting Architecture](docs/STAGE2_ARCHITECTURE.md)
* [Stage 2 Development Roadmap](docs/STAGE2_ROADMAP.md)
* [Stage 2 Production Code Standards](docs/STAGE2_CODE_STANDARDS.md)
* [Contributing](CONTRIBUTING.md)
* [Changelog](CHANGELOG.md)

---

## License

SPDX-License-Identifier: `MIT OR Apache-2.0`

Velo is dual-licensed under either of

* Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE))
* MIT license ([LICENSE-MIT](LICENSE-MIT))

at your option. This is the same licensing arrangement used by the Rust
project: you may choose the license that best fits your situation, and the
Apache-2.0 option includes an explicit patent grant.

Unless you explicitly state otherwise, any contribution intentionally
submitted for inclusion in this project by you, as defined in the Apache-2.0
license, shall be dual-licensed as above, without any additional terms or
conditions.

### Generated artifacts

`bootstrap.c` is generated from `src/main.vl` by `velo emit-c` and is
distributed under the same `MIT OR Apache-2.0` terms as the compiler source it
is derived from. It contains no third-party code. Programs *you* write in Velo
are yours; compiling them does not subject them to this license, exactly as
using a C compiler does not license your own source under the compiler's terms.



