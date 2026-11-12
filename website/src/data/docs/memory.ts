import { DocCategory } from '../../types/docs';

export const MEMORY_CATEGORY: DocCategory = {
  id: 'memory',
  name: '07. Memory Management & Pointers',
  description: 'The @ pointer system, lexical zone arenas with 1-cycle reset, heap allocation, and defer cleanup.',
  iconName: 'Shield',
  pages: [
    {
      id: 'memory-pointers',
      slug: 'memory-pointers',
      title: 'The @ Pointer System',
      category: '07. Memory Management & Pointers',
      categoryOrder: 7,
      order: 1,
      description: 'Master Velo pointers: @T type declaration, @val address-of, auto-dereferencing, and direct value dereferencing (.@).',
      readTimeMinutes: 6,
      badge: 'Core Feature',
      whatYoullLearn: [
        'How @ resolves C pointer ambiguity',
        'Address-of operator: @variable',
        'Auto-dereferencing member access: ptr.field',
        'Direct value dereferencing: ptr.@ = value'
      ],
      sections: [
        {
          id: 'pointer-overview',
          title: 'The @ Operator',
          content: `Velo replaces the overloaded C asterisk \`*\` with the clean, unambiguous **\`@\`** operator:

1. **Pointer Type**: \`@T\` denotes a pointer to type \`T\` (e.g. \`@i32\`, \`@Player\`, \`@@f32\`).
2. **Address-Of**: Placing \`@\` before any expression takes its memory address (\`@player\`, \`@x\`).
3. **Auto-Dereference**: When accessing struct fields through a pointer, developers write \`.\` (e.g. \`player_ptr.health\`). The compiler automatically emits \`->\` in C.
4. **Value Dereference**: Accessing the scalar value pointed to by a pointer uses \`.@\` (e.g. \`p_val.@ = 42\`).`,
          codeExamples: [
            {
              title: 'pointers_in_action.vl',
              language: 'velo',
              code: `use std.io

data Player {
    health: i32
    armor: i32
}

act apply_damage(p: @Player, amount: i32) {
    // Auto-dereference on member access (emits p->health in C):
    p.health -= amount
}

act main() {
    mut hero = Player{ health: 100, armor: 50 }

    // 1. Take address with @:
    hero_ptr: @Player = @hero

    // 2. Pass pointer to function:
    apply_damage(hero_ptr, 25)
    io.println("Hero health: {hero.health}") // 75

    // 3. Direct pointer dereferencing with .@:
    mut score: i32 = 10
    score_ptr: @i32 = @score
    score_ptr.@ = 99 // Overwrites score in memory
    io.println("Score: {score}") // 99
}
`
            }
          ]
        },
        {
          id: 'unsafe-blocks-strict-safety',
          title: 'Unsafe Blocks & Strict Safety Mode (--strict-safety)',
          content: `While Velo provides ergonomic pointer references by default, low-level systems programming occasionally requires raw memory manipulation, untyped casts, and pointer arithmetic.

To prevent accidental memory corruption, Velo introduces **\`unsafe { ... }\` blocks** and the **\`--strict-safety\`** compiler mode:

\`\`\`rust
use std.io

act main() {
    mut val: i32 = 42
    let p: @i32 = @val

    // Unsafe block encapsulates raw pointer operations:
    unsafe {
        // Raw pointer arithmetic and direct byte manipulation:
        let raw_byte_ptr: @u8 = p as @u8
        let next_byte = raw_byte_ptr + 1
        io.println("Inspecting raw memory byte: {next_byte.@}")
    }
}
\`\`\`

### The \`--strict-safety\` Compiler Flag
When compiling with \`--strict-safety\`:
\`\`\`bash
velo build main.vl --strict-safety
\`\`\`
The compiler strictly enforces that:
1. **Pointer Arithmetic**: Offsetting raw pointers with \`+\` or \`-\` is prohibited outside \`unsafe\` blocks.
2. **Untyped Pointer Casts**: Casting pointers across different types (e.g. \`@i32\` to \`@u8\`) requires an \`unsafe\` block.
3. **Foreign C Calls**: Directly invoking \`extern act\` routines is flagged unless encapsulated in \`unsafe\`.

This design gives production systems complete safety guarantees across the majority of code while isolating low-level drivers, allocators, and kernel shims into audited \`unsafe\` blocks.`,
          callout: {
            type: 'note',
            title: 'Memory Safety Philosophy',
            text: 'Safe by default, explicit when dangerous. Standard code enjoys clean zero-overhead semantics without risking unintended undefined behavior.'
          }
        }
      ],
      prevPage: { title: 'Advanced Struct Features', slug: 'types-advanced-structs' },
      nextPage: { title: 'Lexical Zone Arenas', slug: 'memory-zone-arenas' }
    },
    {
      id: 'memory-zone-arenas',
      slug: 'memory-zone-arenas',
      title: 'Lexical Zone Arenas (0ms GC)',
      category: '07. Memory Management & Pointers',
      categoryOrder: 7,
      order: 2,
      description: 'Zero garbage collection pauses with hardware lexical arena memory and 1-CPU-cycle reset.',
      readTimeMinutes: 6,
      badge: 'Game Dev',
      whatYoullLearn: [
        'How zone arenas work under the hood',
        '16MB contiguous hardware pre-allocated arena buffer',
        'O(1) bump allocations via mem.alloc',
        'Instant 1-CPU-cycle watermark reset upon block exit'
      ],
      sections: [
        {
          id: 'how-zone-works',
          title: 'How Zone Arenas Work',
          content: `In interactive applications like games and network packet engines, allocating and freeing thousands of temporary objects each frame using traditional \`malloc\` causes **memory fragmentation and latency spikes**.

Velo introduces the **\`zone\` block**:
1. When entering a \`zone\` block, the runtime records the current arena memory offset (the watermark).
2. Inside the zone, allocations made with \`mem.alloc\` simply bump this pointer forward ($O(1)$ fast path).
3. Upon exiting the zone block, the runtime resets the offset back to the recorded watermark in **a single CPU instruction**. Every temporary allocation is wiped simultaneously with **zero memory leaks and zero GC pauses**.`,
          codeExamples: [
            {
              title: 'zone_demo.vl',
              language: 'velo',
              code: `use std.io
use std.mem

data Matrix {
    m: [16]f32
}

act main() {
    io.println("Arena used before: {mem.used()} bytes")

    // Hardware zone arena:
    zone {
        // Allocate 500 matrices (32 KB) on the arena in O(1) time:
        matrices: @Matrix = mem.alloc(@Matrix, 500)

        io.println("Arena used inside zone: {mem.used()} bytes")
        // Work with matrices...
    } // Wiped in 1 instruction here!

    io.println("Arena used after zone: {mem.used()} bytes (100% reset!)")
}`
            }
          ]
        },
        {
          id: 'zone-guarantees',
          title: 'Zone Guarantees',
          content: `- **Zero Garbage Collection**: No background collector threads, no stop-the-world pauses.
- **Cache-Friendly**: Allocations are packed contiguously in cache lines, minimizing CPU cache misses.
- **Leak-Proof**: Even if an early \`return\` occurs inside a \`zone\`, the compiler restores the arena watermark before returning.`
        }
      ],
      prevPage: { title: 'The @ Pointer System', slug: 'memory-pointers' },
      nextPage: { title: 'Persistent Heap & defer', slug: 'memory-heap-defer' }
    },
    {
      id: 'memory-heap-defer',
      slug: 'memory-heap-defer',
      title: 'Persistent Heap & defer',
      category: '07. Memory Management & Pointers',
      categoryOrder: 7,
      order: 3,
      description: 'Manage long-lived heap memory surviving zone resets, and ensure leak-free cleanup with defer.',
      readTimeMinutes: 5,
      whatYoullLearn: [
        'Allocating long-lived memory with mem.heap_alloc',
        'Freeing heap memory with mem.free',
        'The defer statement and LIFO reverse execution order',
        'Guaranteed cleanup across early returns'
      ],
      sections: [
        {
          id: 'heap-alloc',
          title: 'Persistent Heap Allocation',
          content: `Data structures that must outlive temporary frames (such as global game state, AST trees, or loaded assets) are allocated on the persistent heap via \`std.mem\`:`,
          codeExamples: [
            {
              title: 'heap_memory.vl',
              language: 'velo',
              code: `use std.io
use std.mem

act main() {
    // Allocate 1024 bytes of persistent heap memory:
    buffer: @u8 = mem.heap_alloc(@u8, 1024)

    // Ensure memory is safely freed upon function exit:
    defer mem.free(buffer)

    io.println("Active heap memory: {mem.heap_used()} bytes")
    // Use buffer...
} // mem.free(buffer) executes automatically here!`
            }
          ]
        },
        {
          id: 'defer-lifo',
          title: 'The defer Statement',
          content: `The \`defer\` keyword registers a statement to be executed when the enclosing block exits. If multiple \`defer\` statements are registered, they run in **LIFO order (Last-In, First-Out)**:

\`\`\`rust
defer io.println("Third")
defer io.println("Second")
defer io.println("First")
// Output on exit:
// First
// Second
// Third
\`\`\``
        }
      ],
      prevPage: { title: 'Lexical Zone Arenas', slug: 'memory-zone-arenas' },
      nextPage: { title: 'Custom Allocators', slug: 'memory-allocators' }
    },
    {
      id: 'memory-allocators',
      slug: 'memory-allocators',
      title: 'Custom Allocators & Scaling',
      category: '07. Memory Management & Pointers',
      categoryOrder: 7,
      order: 4,
      description: 'Build custom allocators (Slab, Pool, Bump) using Velo’s extensible @Allocator interface.',
      readTimeMinutes: 5,
      whatYoullLearn: [
        'The standard @Allocator struct contract',
        'Creating multi-arena environments for background threads',
        'Heap-spilling fallback strategies'
      ],
      sections: [
        {
          id: 'allocator-interface',
          title: 'The Allocator Interface',
          content: `Velo provides an extensible allocator contract in \`std.mem\`:

\`\`\`rust
data Allocator {
    alloc: act(usize) -> @void
    free: act(@void) -> void
}
\`\`\`

You can pass custom allocators to standard collections (\`shelf\`, \`map\`) to direct where dynamic memory is stored.`
        }
      ],
      prevPage: { title: 'Persistent Heap & defer', slug: 'memory-heap-defer' },
      nextPage: { title: 'Dynamic Collections Overview', slug: 'collections-overview' }
    }
  ]
};

