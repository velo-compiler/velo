<p align="center">
  <a href="https://velo-compiler.github.io/velo/">
    <img src="website/public/velo-logo.svg" width="128" height="128" alt="Velo Logo" />
  </a>
</p>

<h1 align="center">Velo Programming Language</h1>

<p align="center">
  <b>Code at high velocity.</b><br>
  The raw speed and hardware control of C, with modern syntax as clean as TypeScript, and zero garbage collection pauses.
</p>

<p align="center">
  <a href="https://velo-compiler.github.io/velo/"><img src="https://img.shields.io/badge/docs-website-00d4f0?style=flat-square" alt="Documentation"></a>
  <a href="#license"><img src="https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue.svg?style=flat-square" alt="License"></a>
  <a href="https://github.com/velo-compiler/velo/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/velo-compiler/velo/ci.yml?branch=main&label=CI&style=flat-square" alt="CI Status"></a>
  <a href="https://velo-compiler.github.io/velo/"><img src="https://img.shields.io/badge/version-2.0%20Native-1d4ed8?style=flat-square" alt="Velo Version"></a>
</p>

<p align="center">
  <a href="https://velo-compiler.github.io/velo/"><b>🌐 Visit Website & Documentation &rarr;</b></a>
</p>

---

## Quick Install

One-liner installer downloads the standalone native compiler and sets up your environment:

<!-- not-compiled -->
```powershell
# Windows (PowerShell)
irm https://velo-compiler.github.io/velo/install.ps1 | iex
```

<!-- not-compiled -->
```bash
# Linux / macOS (Bash)
curl -fsSL https://velo-compiler.github.io/velo/install.sh | bash
```

---

## What is Velo?

Velo is a modern systems programming language designed for deterministic performance, zero garbage collection pauses, and direct hardware control.

Today, Velo is built and measured for:
* **Systems Tooling & Self-Hosted Compilers**: The Velo compiler (`src/`) is written entirely in Velo, self-hosts deterministically (Gen2 == Gen3 SHA-256 byte-for-byte), and bootstraps from a standalone C snapshot (`bootstrap.c`).
* **Fast CLI Utilities & Developer Tooling**: Produces standalone native binaries with sub-second compilation, a built-in Language Server (LSP), code formatter (`velo fmt`), and in-memory test runner.
* **Constrained-Memory Batch Jobs & Data Pipelines**: Zone-based arena memory management (`zone { ... }`) provides O(1) allocation and instant cleanup without garbage collection overhead, maintaining a lean ~4.0 MB baseline RSS and < 8.0 MB peak RSS under real-world I/O workloads (empirically measured in `benchmark/MEMORY_RESULTS.md`).

### Platform Support

| Platform | Architecture | Status | Notes |
| :--- | :--- | :--- | :--- |
| **Windows** | `x86_64` | **Supported** | Primary supported platform. Native compiler, CLI, and toolchain with GCC (MSYS2 UCRT64) or Clang. |
| **Linux** | `x86_64`, `aarch64` | *Work in Progress* | Core compiler transpiles to C99; POSIX runtime facade and platform driver convergence in progress (see Phase 70). |
| **macOS** | Apple Silicon, `x86_64` | *Work in Progress* | Core compiler transpiles to C99; Darwin runtime facade and platform driver convergence in progress (see Phase 70). |

See [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md) for the complete OS, architecture, C compiler, and standard library subsystem compatibility matrix.

---

## Key Features

* **Zero Garbage Collection Stutters**: No background GC pauses. Predictable, deterministic latency.
* **The `@` Pointer System**: A clean, unambiguous pointer and address operator. `@T` is a pointer to `T`; `@val` is the memory address of `val`. Auto-dereference on member access (`ptr.field`).
* **`zone` Arena Memory**: Stack-disciplined arena allocations with O(1) instantaneous reset. Clears all temporary frame allocations on block exit with zero fragmentation and zero leaks.
* **Clean & Modern Syntax**: Keyword-based (`act`, `data`, `mut`), curly braces `{}`, and optional semicolons.
* **Direct C Interoperability**: Call any standard C library (OpenGL, Raylib, SQLite, SDL) with zero glue code.
* **Native C Speed**: Generates clean, optimized C99/C11 code compiled by GCC or Clang.

---

## Quick Look

```rust
use std.io
use std.mem

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

    // 'zone' creates a fast arena that reclaims all frame allocations in O(1) time on block exit.
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
        loop step < 3 {
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

<!-- not-compiled -->
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

<!-- not-compiled -->
```bash
# Windows (requires GCC, e.g. MSYS2 UCRT64)
scripts\bootstrap.bat

# Linux / macOS (requires gcc or clang - work in progress)
bash scripts/bootstrap.sh
```

This builds `bin/velo.exe` (or `bin/velo`), which is the full self-hosted Velo compiler.

---

## CLI Usage

<!-- not-compiled -->
```bash
# Run a Velo script immediately (compile + link + execute)
bin/velo.exe run main.vl

# Compile to a standalone native executable
bin/velo.exe build main.vl -o game.exe

# Verify multi-stage compiler determinism (Gen2 == Gen3 SHA-256 fixed point)
bin/velo.exe build src/main.vl --verify-determinism

# View the generated C99/C11 code
bin/velo.exe emit-c main.vl

# Check syntax and semantic analysis without compiling
bin/velo.exe check main.vl

# Format Velo source files to canonical style
bin/velo.exe fmt src/main.vl
```

---

## Showcase Applications & Games

The repository includes complete, native showcase applications and interactive games built with Velo:

### 🎮 Games (`games/`)
* **[Flappy Bird](games/flappy_bird/)**: 2D arcade flapper with 60 FPS physics, sprite rendering, and sound effects powered by Raylib 6.0 C-FFI.
* **[Survivors](games/survivors/)**: 2D horde survival game with swarming AI entities, modular weapon systems, EXP progression, and zero-GC zone arena memory.
* **[VeloCraft](games/velocraft/)**: 3D first-person voxel sandbox engine featuring mouse-look camera, procedural chunk generation, DDA block raycasting, and terrain physics.

### 💼 Systems Applications (`apps/`)
* **[VeloKV](apps/velokv/)**: High-performance, Redis-compatible in-memory key-value database featuring full RESP protocol parsing, concurrent networking, and Append-Only File (AOF) persistence.
* **[VeloStudio](apps/velostudio/)**: Native desktop SQLite database manager with a graphical Raylib UI, table inspection, and C-FFI SQLite3 integration.

All showcase projects are continuously verified for syntactic, semantic, and C-codegen compatibility by automated tests in [`tests/test_showcase.py`](tests/test_showcase.py).

---

## Documentation

* **[Official Website & Interactive Docs](https://velo-compiler.github.io/velo/)**
* [Language Specification](docs/SPECIFICATION.md)
* [Step 2 Specification (Compiler Essentials)](docs/STEP2_SPECIFICATION.md)
* [Compiler Architecture (Stage 1)](docs/ARCHITECTURE.md)
* [Stage 1 Development Roadmap](docs/STAGE1_ROADMAP.md)
* [Step 2 Development Roadmap](docs/STEP2_ROADMAP.md)
* [Stage 2 Self-Hosting Architecture](docs/STAGE2_ARCHITECTURE.md)
* [Standard Library Architecture & Platform Contract](docs/STDLIB_ARCHITECTURE.md)
* [Stage 2 Development Roadmap](docs/STAGE2_ROADMAP.md)
* [Stage 2 Production Code Standards](docs/STAGE2_CODE_STANDARDS.md)
* [Empirical Performance & Multi-Language Benchmarks](benchmark/RESULTS.md)
* [Memory Footprint & RSS Audit](benchmark/MEMORY_RESULTS.md)
* [Platform & Toolchain Compatibility Matrix](docs/COMPATIBILITY.md)
* [Architectural Reviews & Audits Index](docs/REVIEWS.md)
* [Contributing](CONTRIBUTING.md)
* [Governance & Evolution](GOVERNANCE.md)
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



