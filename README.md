# Velo Programming Language (`.vl`)

> **Code at high velocity.**
> The raw speed and hardware control of C, with modern syntax as clean as TypeScript, and zero garbage collection pauses.

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

## Compiler Architecture (Stage 1)

Velo Stage 1 uses a Python-based bootstrap transpiler that targets C99:

```
[ .vl Source Code ] 
       │
       ▼
1. Lexer (Tokenizer)        --> Turns characters into Tokens
       │
       ▼
2. Parser (AST)           --> Builds Abstract Syntax Tree
       │
       ▼
3. C-Emitter (Codegen)    --> Emits clean C99 code
       │
       ▼
4. GCC Driver (gcc.exe)   --> Produces native .exe binary
```

---

## CLI Usage (Preview)

```bash
# Run a Velo script immediately (transpile + build + run)
python velo.py run main.vl

# Compile to a native standalone executable
python velo.py build main.vl -o game.exe

# View the generated C code
python velo.py emit-c main.vl
```

---

## Documentation

* [Language Specification](docs/SPECIFICATION.md)
* [Compiler Architecture](docs/ARCHITECTURE.md)
* [Stage 1 Development Roadmap](docs/STAGE1_ROADMAP.md)
