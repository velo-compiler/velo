import { PlaygroundPreset } from '../types/docs';

export const PLAYGROUND_PRESETS: PlaygroundPreset[] = [
  {
    id: 'hello',
    title: 'Hello, World!',
    category: 'Fundamentals',
    description: 'The standard entry point into Velo with std.io string printing.',
    code: `use std.io

act main() {
    io.println("Hello, world from Velo 2.0!")
    io.println("Code at high velocity.")
}
`,
    expectedOutput: `Hello, world from Velo 2.0!
Code at high velocity.`,
    cEquivalent: `#include <stdio.h>

int main(int argc, char** argv) {
    puts("Hello, world from Velo 2.0!");
    puts("Code at high velocity.");
    return 0;
}`
  },
  {
    id: 'math-logic',
    title: 'Math, Logic & Loops',
    category: 'Fundamentals',
    description: 'Variables (let vs mut), recursive functions, while loops, and range iteration.',
    code: `use std.io

act fibonacci(n: i32) -> i32 {
    if n <= 1 {
        return n
    }
    return fibonacci(n - 1) + fibonacci(n - 2)
}

act main() {
    io.println("--- Velo Math, Logic & Loops ---")

    mut counter: i32 = 0
    loop counter < 3 {
        io.println("While counter: {counter}")
        counter += 1
    }

    loop i in 0..5 {
        io.println("Range step: {i}")
    }

    let n = 7
    let result = fibonacci(n)
    io.println("Fibonacci({n}) = {result}")
}
`,
    expectedOutput: `--- Velo Math, Logic & Loops ---
While counter: 0
While counter: 1
While counter: 2
Range step: 0
Range step: 1
Range step: 2
Range step: 3
Range step: 4
Fibonacci(7) = 13`,
    cEquivalent: `// Monomorphized C99 lowering with loop desugaring`
  },
  {
    id: 'pointers',
    title: 'The @ Pointer System',
    category: 'Memory & Pointers',
    description: 'Demonstrating @T pointers, address-of @x, auto-dereference on member access (ptr.field), and value dereference (.@).',
    code: `use std.io

data Point {
    x: f32
    y: f32
}

act move_point(p: @Point, dx: f32, dy: f32) {
    p.x += dx  // Auto-dereference translates to p->x += dx in C
    p.y += dy
}

act main() {
    io.println("--- The @ Pointer System ---")

    mut pt = Point{ x: 10.0, y: 20.0 }
    io.println("Initial Point: ({pt.x}, {pt.y})")

    ptr: @Point = @pt
    move_point(ptr, 5.5, -2.5)
    io.println("Point after move: ({pt.x}, {pt.y})")

    mut score: i32 = 42
    p_score: @i32 = @score
    p_score.@ = 99  // Direct pointer value dereference
    io.println("Modified score via p_score.@: {score}")
}
`,
    expectedOutput: `--- The @ Pointer System ---
Initial Point: (10.000000, 20.000000)
Point after move: (15.500000, 17.500000)
Modified score via p_score.@: 99`,
    cEquivalent: `typedef struct Point { float x; float y; } Point;
void move_point(Point* p, float dx, float dy) {
    p->x += dx;
    p->y += dy;
}`
  },
  {
    id: 'zone-memory',
    title: 'Zone Arena Allocator (0ms GC)',
    category: 'Memory & Pointers',
    description: 'Lexical hardware arena allocation with 1-CPU-cycle reset upon block exit.',
    code: `use std.io
use std.mem

data Particle {
    x: f32
    y: f32
    vx: f32
    vy: f32
}

act main() {
    io.println("--- Zone Arena Memory (0 GC Pauses) ---")

    let used_before = mem.used()
    io.println("Arena memory before zone: {used_before} bytes")

    zone {
        count: usize = 1000
        // Allocate 1000 Particles on the 16MB contiguous arena
        particles: @Particle = mem.alloc(@Particle, count)

        let used_inside = mem.used()
        io.println("Allocated 1000 Particles: {used_inside} bytes on arena")

        loop i in 0..count {
            p: @Particle = @particles[i]
            p.x = 0.0
            p.y = 0.0
            p.vx = 1.5
            p.vy = 2.0
        }

        p0: @Particle = @particles[0]
        io.println("Particle 0 initialized: pos=({p0.x}, {p0.y}) vel=({p0.vx}, {p0.vy})")
    } // Wiped in 1 instruction: watermark offset reset!

    let used_after = mem.used()
    io.println("Arena memory after zone: {used_after} bytes (instant reset)")
}
`,
    expectedOutput: `--- Zone Arena Memory (0 GC Pauses) ---
Arena memory before zone: 0 bytes
Allocated 1000 Particles: 16000 bytes on arena
Particle 0 initialized: pos=(0.000000, 0.000000) vel=(1.500000, 2.000000)
Arena memory after zone: 0 bytes (instant reset)`,
    cEquivalent: `size_t _velo_zone_mark = velo_arena_watermark();
// allocations increment watermark offset
velo_arena_reset(_velo_zone_mark); // 1-cycle O(1) rewind`
  },
  {
    id: 'enums-unions',
    title: 'Tagged Unions & Pattern Matching',
    category: 'Types & Modeling',
    description: 'The kind keyword for scalar enums and tagged unions, with dot-shorthand and on pattern matching.',
    code: `use std.io

kind Event {
    Quit
    KeyDown: i32
    Click(button: i32, x: f32, y: f32)
}

act handle_event(e: Event) {
    on e {
        .Quit => {
            io.println("Event: Quit application")
        }
        .KeyDown(key) => {
            io.println("Event: KeyDown = {key}")
        }
        .Click(button, x, y) => {
            io.println("Event: Click button {button} at ({x}, {y})")
        }
    }
}

act main() -> i32 {
    io.println("--- Tagged Unions & Pattern Matching ---")

    let e1: Event = .Quit
    let e2: Event = .KeyDown(65)
    let e3: Event = .Click(1, 100.0, 250.0)

    handle_event(e1)
    handle_event(e2)
    handle_event(e3)
    return 0
}
`,
    expectedOutput: `--- Tagged Unions & Pattern Matching ---
Event: Quit application
Event: KeyDown = 65
Event: Click button 1 at (100.000000, 250.000000)`,
    cEquivalent: `typedef struct Event {
    int32_t kind;
    union {
        int32_t KeyDown;
        struct { int32_t button; float x; float y; } Click;
    } as;
} Event;`
  },
  {
    id: 'ufcs-methods',
    title: 'UFCS & Method Syntax',
    category: 'Functions & Methods',
    description: 'Uniform Function Call Syntax turning top-level functions into natural chained methods with auto-borrowing.',
    code: `use std.io

data Vector2 {
    x: f32
    y: f32
}

act length_sq(v: Vector2) -> f32 {
    return v.x * v.x + v.y * v.y
}

act scale(v: @Vector2, factor: f32) {
    v.x = v.x * factor
    v.y = v.y * factor
}

act square(n: i32) -> i32 {
    return n * n
}

act main() {
    io.println("--- Uniform Function Call Syntax (UFCS) ---")

    mut v = Vector2{ x: 3.0, y: 4.0 }

    // Direct method call: calls length_sq(v)
    let len = v.length_sq()
    io.println("Initial length_sq: {len}")

    // Pointer method call: auto-borrows address: scale(&v, 2.0)
    v.scale(2.0)
    io.println("Scaled vector: ({v.x}, {v.y})")

    // Primitive extension method
    let s = 7.square()
    io.println("Primitive extension 7.square() = {s}")
}
`,
    expectedOutput: `--- Uniform Function Call Syntax (UFCS) ---
Initial length_sq: 25.000000
Scaled vector: (6.000000, 8.000000)
Primitive extension 7.square() = 49`,
    cEquivalent: `length_sq(v);
scale(&v, 2.0f);
square(7);`
  },
  {
    id: 'operator-overloading',
    title: 'Vector Math Operator Overloading',
    category: 'Types & Modeling',
    description: 'Custom operator overloading with act op +, op *, and unary op - compiling to zero-overhead C.',
    code: `use std.io

data Vector2 {
    x: f32
    y: f32
}

act op +(a: Vector2, b: Vector2) -> Vector2 {
    return Vector2{ x: a.x + b.x, y: a.y + b.y }
}

act op *(v: Vector2, s: f32) -> Vector2 {
    return Vector2{ x: v.x * s, y: v.y * s }
}

act op-(v: Vector2) -> Vector2 {
    return Vector2{ x: -v.x, y: -v.y }
}

act main() {
    io.println("--- Operator Overloading for Game Math ---")

    let pos = Vector2{ x: 10.0, y: 20.0 }
    let vel = Vector2{ x: 2.0, y: -3.0 }
    let dt: f32 = 0.5

    // Precedence preserved: vel * dt evaluated first, then added to pos
    let next_pos = pos + vel * dt
    io.println("next_pos: ({next_pos.x}, {next_pos.y})")

    let opposite = -vel
    io.println("opposite velocity: ({opposite.x}, {opposite.y})")
}
`,
    expectedOutput: `--- Operator Overloading for Game Math ---
next_pos: (11.000000, 18.500000)
opposite velocity: (-2.000000, 3.000000)`,
    cEquivalent: `Vector2 next_pos = velo_op_add_Vector2_Vector2(pos, velo_op_mul_Vector2_f32(vel, dt));`
  },
  {
    id: 'shelf-basics',
    title: 'Dynamic Shelf Collections',
    category: 'Collections',
    description: 'Built-in growable shelf[T] arrays with put/take LIFO operations and loop-of snapshot walks.',
    code: `use std.io

act main() -> i32 {
    io.println("--- Built-in shelf[T] Dynamic Collections ---")

    // Typed literals
    let nums: shelf[i32] = shelf[4, 8, 15, 16]
    io.println("Initial shelf len: {nums.len}")
    io.println("Index [2]: {nums[2]}")

    // Mutable shelf with put/take operations
    mut xs = shelf[10, 20, 30]
    xs.put(40)
    io.println("After put(40), len: {xs.len}")

    let top: i32 = xs.take()
    io.println("take() popped from end: {top}")
    io.println("Remaining len: {xs.len}")

    // Snapshot iteration
    mut sum: i32 = 0
    loop v of xs {
        sum += v
    }
    io.println("Sum of elements: {sum}")
    return 0
}
`,
    expectedOutput: `--- Built-in shelf[T] Dynamic Collections ---
Initial shelf len: 4
Index [2]: 15
After put(40), len: 4
take() popped from end: 40
Remaining len: 3
Sum of elements: 60`,
    cEquivalent: `velo_shelf_i32 xs = velo_shelf_create_i32(4);
velo_shelf_put_i32(&xs, 40);
int32_t top = velo_shelf_take_i32(&xs);`
  },
  {
    id: 'simd-math',
    title: '128-Bit SIMD Hardware Acceleration',
    category: 'Hardware Acceleration',
    description: 'Hardware vectorization using f32x4 and i32x4 primitives, vector dot products, and intrinsics.',
    code: `use std.io
use std.simd

act main() -> i32 {
    io.println("--- 128-Bit SIMD Hardware Operations ---")

    let a = f32x4(1.0, 2.0, 3.0, 4.0)
    let b = f32x4(2.0, 3.0, 4.0, 5.0)

    // Hardware dot product: 1*2 + 2*3 + 3*4 + 4*5 = 40.0
    let dot_res = simd.dot(a, b)
    io.println("SIMD Dot Product: {dot_res}")

    // Hardware vectorized square root
    let sq_in = f32x4(4.0, 9.0, 16.0, 25.0)
    let sq_res = simd.sqrt(sq_in)
    io.println("SIMD Sqrt result: ({sq_res.x}, {sq_res.y}, {sq_res.z}, {sq_res.w})")

    // Vector clamp using simd.min / simd.max
    let lo = f32x4(0.0, 0.0, 0.0, 0.0)
    let hi = f32x4(3.0, 3.0, 3.0, 3.0)
    let clamped = simd.min(simd.max(sq_res, lo), hi)
    io.println("Clamped result: ({clamped.x}, {clamped.y}, {clamped.z}, {clamped.w})")
    return 0
}
`,
    expectedOutput: `--- 128-Bit SIMD Hardware Operations ---
SIMD Dot Product: 40.000000
SIMD Sqrt result: (2.000000, 3.000000, 4.000000, 5.000000)
Clamped result: (2.000000, 3.000000, 3.000000, 3.000000)`,
    cEquivalent: `typedef float __attribute__((vector_size(16))) f32x4;
// Directly compiles to SSE / AVX / NEON instructions`
  }
];

