import { DocCategory } from '../../types/docs';

export const STDLIB_DOCS_CATEGORY: DocCategory = {
  id: 'stdlib',
  name: '11. Standard Library (std.*)',
  description: '100% pure Velo standard library with zero libc dependencies: memory, formatting, strings, I/O, FS, and math.',
  iconName: 'Archive',
  pages: [
    {
      id: 'stdlib-overview',
      slug: 'stdlib-overview',
      title: 'Standard Library Architecture',
      category: '11. Standard Library (std.*)',
      categoryOrder: 11,
      order: 1,
      description: 'The two-tier pure Velo standard library system: decoupling completely from libc.',
      readTimeMinutes: 5,
      whatYoullLearn: [
        'Why Velo eliminates C libc dependencies',
        'Tier 1 (Foundational: std.mem, std.fmt, std.str, std.io, std.fs, std.math)',
        'Tier 2 (Extended capabilities: json, net, async, crypto, time)',
        'Thin OS boundary (sys.*) on Windows and POSIX'
      ],
      sections: [
        {
          id: 'two-tier-system',
          title: 'The Two-Tier Architecture',
          content: `In Velo, the standard library is divided into two distinct layers:

1. **\`std.*\` (Pure Velo Standard Library)**: Written in 100% pure Velo (\`.vl\`). Owns memory allocators, string formatting (\`itoa\`, \`ftoa\`), buffer slicing, search, ring-buffered streams, and data structures. It has zero reliance on \`printf\`, \`malloc\`, \`free\`, or \`FILE*\`.
2. **\`sys.*\` (Thin OS Syscall Boundary)**: Direct bindings to raw OS kernel primitives (\`VirtualAlloc\` / \`GetStdHandle\` on Windows; \`mmap\` / raw syscalls on Linux).`,
          callout: {
            type: 'note',
            title: 'Systems Independence',
            text: 'Because std is pure Velo, your binaries are not bound to specific C runtime versions (msvcrt.dll, glibc) and enjoy predictable behavior across all platforms.'
          }
        }
      ],
      prevPage: { title: 'Foreign Function Interface (extern)', slug: 'c-interop-ffi' },
      nextPage: { title: 'std.mem & std.fmt', slug: 'stdlib-mem-fmt' }
    },
    {
      id: 'stdlib-mem-fmt',
      slug: 'stdlib-mem-fmt',
      title: 'std.mem & std.fmt',
      category: '11. Standard Library (std.*)',
      categoryOrder: 11,
      order: 2,
      description: 'Pure Velo page allocators, arena memory, slab freelists, and zero-dependency integer and float formatting.',
      readTimeMinutes: 6,
      badge: 'Core Stdlib',
      whatYoullLearn: [
        'Allocators in std.mem: Page, Arena, and Slab',
        'Direct OS virtual memory requests without malloc',
        'Integer formatting with fmt.int_to_str (itoa)',
        'Float formatting with fmt.float_to_str (Grisu ftoa)'
      ],
      sections: [
        {
          id: 'std-mem',
          title: 'std.mem: Memory Management',
          content: `\`std.mem\` implements pure Velo allocators:
- \`mem.alloc(@Type, count)\`: Arena allocation on the thread zone buffer.
- \`mem.heap_alloc(@Type, count)\`: Persistent heap allocation backed by OS virtual pages.
- \`mem.free(ptr)\`: Explicit deallocation.
- \`mem.copy(dst, src, bytes)\`: Fast word-aligned memory copy.
- \`mem.zero(dst, bytes)\`: Fast memory zeroing.`,
          codeExamples: [
            {
              title: 'mem_demo.vl',
              language: 'velo',
              code: `use std.mem

act main() {
    // Persistent heap buffer:
    buf: @u8 = mem.heap_alloc(@u8, 256)
    defer mem.free(buf)

    mem.zero(buf, 256)
}`
            }
          ]
        },
        {
          id: 'std-fmt',
          title: 'std.fmt: Zero-Sprintf Formatting',
          content: `\`std.fmt\` formats numbers directly into caller-provided byte buffers without dynamically allocating strings or risking buffer overflows:`,
          codeExamples: [
            {
              title: 'fmt_demo.vl',
              language: 'velo',
              code: `use std.fmt
use std.io

act main() {
    mut buf: [32]u8
    let written = fmt.int_to_str(123456, @buf, 32)
    io.println("Formatted integer: {written} bytes written")

    let hex_len = fmt.uint_to_hex(0xCAFEBABE, @buf, 32)
    io.println("Formatted hex: {hex_len} bytes written")
}`
            }
          ]
        }
      ],
      prevPage: { title: 'Standard Library Architecture', slug: 'stdlib-overview' },
      nextPage: { title: 'std.str & std.io', slug: 'stdlib-str-io' }
    },
    {
      id: 'stdlib-str-io',
      slug: 'stdlib-str-io',
      title: 'std.str & std.io',
      category: '11. Standard Library (std.*)',
      categoryOrder: 11,
      order: 3,
      description: 'Zero-allocation StrSlice byte views, Boyer-Moore search, StrBuilder, and ring-buffered streams.',
      readTimeMinutes: 6,
      badge: 'Core Stdlib',
      whatYoullLearn: [
        'Non-allocating string slicing with StrSlice',
        'Boyer-Moore substring search (str.find)',
        'Dynamic string accumulation with StrBuilder',
        'Ring-buffered stream I/O replacing C FILE*'
      ],
      sections: [
        {
          id: 'std-str',
          title: 'std.str: Zero-Allocation Views',
          content: `In systems applications, creating substrings by copying bytes kills performance. \`std.str\` operates on non-owning byte windows (\`StrSlice\`):`,
          codeExamples: [
            {
              title: 'str_demo.vl',
              language: 'velo',
              code: `use std.str
use std.io

act main() {
    let text = "GET /index.html HTTP/1.1"

    // Zero-allocation slice:
    let method = str.slice(text, 0, 3) // "GET"

    // Fast substring search:
    let path_idx = str.find(text, "/index.html")
    io.println("Path found at index: {path_idx}")

    // String builder:
    mut sb = str.builder_create(64)
    sb.append("Velo ")
    sb.append("Language")
    io.println("Built string: {sb.to_string()}")
}`
            }
          ]
        },
        {
          id: 'std-io',
          title: 'std.io: Ring-Buffered Streams',
          content: `\`std.io\` wraps OS handles with circular ring buffers, avoiding system call overhead when reading or writing small chunks of data.`
        }
      ],
      prevPage: { title: 'std.mem & std.fmt', slug: 'stdlib-mem-fmt' },
      nextPage: { title: 'std.fs & std.path', slug: 'stdlib-fs-path' }
    },
    {
      id: 'stdlib-fs-path',
      slug: 'stdlib-fs-path',
      title: 'std.fs & std.path',
      category: '11. Standard Library (std.*)',
      categoryOrder: 11,
      order: 4,
      description: 'Cross-platform filesystem operations, directory traversal, and path normalization.',
      readTimeMinutes: 5,
      whatYoullLearn: [
        'Reading entire files with fs.read_file',
        'Atomic file writes with fs.write_file',
        'Cross-platform path manipulation and normalization with std.path'
      ],
      sections: [
        {
          id: 'fs-operations',
          title: 'Filesystem Operations',
          content: `\`std.fs\` provides clean, reliable file I/O:`,
          codeExamples: [
            {
              title: 'fs_demo.vl',
              language: 'velo',
              code: `use std.fs
use std.mem
use std.io

act main() {
    let path = "config.toml"
    if fs.exists(path) {
        let size = fs.size(path)
        io.println("File size: {size} bytes")

        let content = fs.read_file(path)
        defer mem.free(content)
        io.println("Content: {content}")
    } else {
        fs.write_file(path, "name = \\"my_app\\"\\nversion = \\"1.0\\"")
        io.println("Created default config.toml")
    }
}`
            }
          ]
        }
      ],
      prevPage: { title: 'std.str & std.io', slug: 'stdlib-str-io' },
      nextPage: { title: 'Standard Library A–Z Catalog', slug: 'stdlib-catalog-az' }
    },
    {
      id: 'stdlib-catalog-az',
      slug: 'stdlib-catalog-az',
      title: 'Standard Library A–Z Catalog',
      category: '11. Standard Library (std.*)',
      categoryOrder: 11,
      order: 5,
      description: 'The complete directory of all 127 pure-Velo modules across mathematics, cryptography, networking, and serialization.',
      readTimeMinutes: 7,
      badge: 'Catalog',
      whatYoullLearn: [
        'Directory of Tier 1 and Tier 2 standard library modules',
        'Module categories: crypto, networking, async, testing, serialization',
        'How to import any standard module'
      ],
      sections: [
        {
          id: 'catalog-table',
          title: 'Module Directory (A to Z)',
          content: `All modules in \`std.*\` are documented and accessible via \`use std.<module>\`:`,
          table: {
            headers: ['Module', 'Category', 'Description'],
            rows: [
              ['std.async', 'Concurrency', 'Cooperative lightweight task schedulers, future/promise combinators'],
              ['std.atomic', 'Concurrency', 'Hardware atomic primitives: load, store, CAS, and fetch-and-add'],
              ['std.coll', 'Collections', 'Core memory-managed dynamic collections (shelf, map, ring, bitset)'],
              ['std.crypto', 'Security', 'SHA-256, HMAC, ChaCha20, AES, and cryptographically secure random bytes'],
              ['std.fmt', 'Formatting', 'Zero-dependency integer (itoa), float (ftoa), and template formatting'],
              ['std.fs', 'Filesystem', 'Cross-platform path resolution, directory scanning, and file streaming'],
              ['std.io', 'I/O', 'Ring-buffered stream readers and writers wrapping native OS handles'],
              ['std.json', 'Serialization', 'Zero-allocation JSON streaming tokenizer, DOM AST, and serializer'],
              ['std.math', 'Math', 'Bit manipulation (popcount, clz, ctz), integer math, and IEEE-754 floats'],
              ['std.mem', 'Memory', 'Pure Velo page allocators, lexical arena watermarking, and slab freelists'],
              ['std.net', 'Networking', 'Low-latency TCP/UDP network sockets, listeners, and DNS resolution'],
              ['std.os', 'System', 'Process spawning, anonymous inter-process pipes, environment variables'],
              ['std.path', 'Filesystem', 'Dedicated cross-platform path normalization and extension parsing'],
              ['std.simd', 'Hardware', 'Direct bindings to 128-bit hardware vector instructions (f32x4, i32x4)'],
              ['std.str', 'Strings', 'Zero-allocation StrSlice non-owning byte views and UTF-8 decoders'],
              ['std.test', 'QA', 'Native test assertion framework (assert) and benchmark runner'],
              ['std.time', 'Time', 'Monotonic nanosecond timers, high-precision sleep, and calendar math']
            ]
          }
        }
      ],
      prevPage: { title: 'std.fs & std.path', slug: 'stdlib-fs-path' },
      nextPage: { title: 'Built-in LSP Server (velo lsp)', slug: 'tooling-lsp' }
    }
  ]
};

