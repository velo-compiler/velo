# Velo Standard Library Specification (`std.*`)

> **Core Philosophy: True Systems Independence (No C Standard Library)**  
> A self-hosted systems language cannot claim true independence if its runtime is secretly dependent on C's standard library (`libc` — `malloc`, `free`, `printf`, `FILE*`, `string.h`).  
> In Velo, **`std` is the foundational, low-level standard library written in 100% pure Velo (`.vl`)**.  
> The standard library owns memory management, formatting, string processing, and buffered I/O from the ground up, reducing the external OS dependency to minimal raw syscall boundaries.

---

## Architecture: The Two-Tier System

```
┌────────────────────────────────────────────────────────────────────────┐
│                      User Code / Applications / Packages               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│  std.*  — Low-Level Pure Velo Standard Library (Zero Libc)             │
│                                                                        │
│  [Core Low-Level Foundation]                                           │
│  - std.mem   : Pure Velo Allocators (Page, Arena, Bump, Freelist)      │
│  - std.fmt   : itoa, ftoa, pure-Velo buffer formatting (no sprintf)   │
│  - std.str   : UTF-8 validation, slicing, search, zero-alloc views    │
│  - std.io    : Ring-buffered readers & writers over OS handles         │
│  - std.fs    : Path resolution, directory scanning, stream I/O         │
│  - std.math  : Bit-tricks, integer & float algorithms (no libm)       │
│  - std.coll  : Memory-conscious structures (shelves, maps, rings, sets)│
│                                                                        │
│  [Extended Capabilities]                                               │
│  - std.json, std.net, std.async, std.crypto, std.time, etc.            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│  sys.*  — Raw OS Kernel Boundary (Thin Primitives / Syscalls)          │
│  - Windows: kernel32 / NT syscalls (VirtualAlloc, GetStdHandle, etc.)  │
│  - Linux:   Direct x86_64 / arm64 syscalls (mmap, write, read, exit)   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Import Syntax

Standard library modules are imported with the concise, symmetrical `std.<module>` prefix.

### 1. Single Module Import
```velo
use sys.io
use std.mem
use std.fmt
use std.json
```

### 2. Grouped Module Import
To eliminate vertical import bloat at the top of files:
```velo
use sys.{io, os}
use std.{mem, fmt, io, str}
use std.{json, net, async}
```

### 3. Call-Site Access
Modules are referenced directly by their unqualified name:
```velo
use std.{mem, fmt, io}

act main() {
    let mut arena = mem.create_arena(65536)
    defer mem.destroy_arena(@arena)

    let formatted = fmt.int_to_str(42)
    io.print(formatted)
}
```

---

## Tier 1: The Low-Level Foundation (Replacing Libc)

These modules form the bedrock of the entire language and runtime:

### `std.mem` — Pure Velo Allocators
- **Page Allocator**: Directly requests large virtual memory pages from `sys` (`VirtualAlloc` on Windows, `mmap` on POSIX).
- **Arena / Bump Allocator**: Blazing fast regional allocation for compiler passes, request lifecycles, and temporary workspaces.
- **Slab / Freelist Allocator**: General-purpose dynamic allocation replacing C `malloc()` and `free()`.
- **Memory Ops**: Pure Velo memory copy (`mem.copy`), zeroing (`mem.zero`), and comparison (`mem.eq`).

### `std.fmt` — Zero-Dependency Formatting
- **Integer Formatting (`itoa`)**: Base-10, hexadecimal, binary, and octal integer-to-string encoding directly into caller-provided byte buffers.
- **Float Formatting (`ftoa`)**: Fast Grisu/Ryu float-to-string algorithms without C `sprintf`.
- **Buffer Formatting**: Pure Velo string interpolation and template formatting without format string vulnerabilities.

### `std.str` — Pure Velo Strings & UTF-8
- **Validation**: Strict branchless/lookup-based UTF-8 validation.
- **Slicing & Views**: Non-allocating byte and rune slices (`str.slice`, `str.substr`).
- **Inspection & Search**: Substring search (Boyer-Moore / Horspool), prefix/suffix checks, trimming, splitting.
- **String Builder**: Dynamic heap-backed or arena-backed byte accumulation.

### `std.io` — Ring-Buffered Streams
- **Handle Wrappers**: Wraps raw OS file descriptors / handles with standard `Reader` and `Writer` contracts.
- **Ring Buffering**: Built on Velo's native `ring[u8]`, eliminating C `FILE*` and `stdio.h` buffering overhead.
- **Standard Streams**: Pure Velo `io.stdin`, `io.stdout`, `io.stderr`.

### `std.fs` — Filesystem & Paths
- **Path Manipulation**: Lexical normalization, directory name, extension extraction, path joining.
- **Directory Traversal**: Native directory walking and file listing without C `dirent.h`.
- **File Utilities**: Chunked reading, streaming writes, and permission flags.

### `std.math` — Low-Level Numeric Primitives
- **Bit Manipulation**: Count leading/trailing zeros (`clz`, `ctz`), population count (`popcount`), byte swapping.
- **Integer Math**: Saturating arithmetic, checked overflow arithmetic, gcd/lcm.
- **Float Math**: Elementary pure-Velo functions (`abs`, `floor`, `ceil`, `round`, `sqrt`).

### `std.coll` — Core Memory-Managed Collections
- **Shelf Lifecycle**: Explicit allocation and deallocation for dynamic shelves (`shelf.destroy`, `shelf.free`).
- **Maps**: Pure Velo open-addressing hash maps with configurable growth policies.
- **Ring Buffers & Deques**: Cache-friendly contiguous FIFO/LIFO queues.

---

## Tier 2: Extended Standard Library Modules (A–Z)

High-level libraries built strictly on top of Tier 1 primitives:

### A
- `use std.async` — Async/await runtime, event loops, and futures/promises
- `use std.atomic` — Atomic operations and lock-free primitives
- `use std.archive` — Compression and archive handling (zip, tar, gzip)
- `use std.arrays` — Advanced array algorithms (binary search, partitioning, quickselect)

### B
- `use std.bigint` — Arbitrary-precision integer arithmetic
- `use std.bufio` — Specialized buffered stream adapters
- `use std.binary` — Binary serialization/deserialization and endian conversion
- `use std.bits` — High-level bitfields and bitsets
- `use std.base64` — Base64 and hex encoders/decoders

### C
- `use std.calendar` — Calendar systems, leap year calculations, date math
- `use std.channels` — Message-passing channels for concurrent workloads
- `use std.collections` — Specialized data structures (Priority Queue, Ordered Map, Trie)
- `use std.complex` — Complex numbers and arithmetic
- `use std.concurrency` — Thread pools, worker threads, condition variables
- `use std.crypto` — SHA-256, HMAC, ChaCha20, AES, cryptographically secure random bytes
- `use std.csv` — Zero-allocation streaming CSV parser and generator
- `use std.config` — INI, TOML, and key-value config parsers

### D
- `use std.date` — Timezone conversions, ISO 8601 parsing and rendering
- `use std.debug` — Stack traces, panic handlers, memory leak detectors
- `use std.decimal` — Fixed-point decimal arithmetic for financial systems
- `use std.di` — Dependency injection and service containers

### E
- `use std.encoding` — UTF-8, UTF-16, ASCII transcoding and validation
- `use std.env` — Command-line argument parser and environment variable access
- `use std.result` — Functional `Result[T, E]` and `Option[T]` combinators
- `use std.event` — Event dispatchers and observer utilities

### F
- `use std.path` — Dedicated path manipulation utilities
- `use std.functional` — Map, filter, fold, zip, and iterator transformers
- `use std.format` — Complex template engine and text layout
- `use std.fs_watch` — Native file-system change notification watcher

### G
- `use std.geometry` — 2D/3D vectors, points, bounding boxes, collision math
- `use std.graph` — Directed/undirected graph representation and shortest-path algorithms

### H
- `use std.http` — Pure Velo HTTP/1.1 client and server
- `use std.html` — HTML entity encoding/decoding and DOM tree parser
- `use std.map_life` — Explicit hash-map lifetime management (`map.destroy`)
- `use std.shelf_life` — Heap-backed shelf lifetime management (`shelf.destroy`)

### I
- `use std.image` — Image decoding (BMP, QOI, PNG) and pixel buffers
- `use std.i18n` — Localization tables and pluralization rules
- `use std.iter` — Lazy iterator chains and generators

### J
- `use std.json` — Streaming and DOM JSON parser/serializer
- `use std.json_schema` — JSON validation against schema rules
- `use std.jobs` — Task queues and background job dispatchers

### K
- `use std.kv` — Embedded key-value storage abstractions

### L
- `use std.log` — Leveled logging framework (debug, info, warn, error)
- `use std.locale` — System locale detection and formatting rules
- `use std.linalg` — Linear algebra, matrices, and vector math
- `use std.lock` — Mutexes, read-write locks, and scoped RAII guards

### M
- `use std.matrix` — 2D/3D/4D matrix math operations
- `use std.mem_profile` — Memory usage statistics and allocator diagnostics
- `use std.map_heap` — Heap-backed dynamic maps (`heap map[K, V]`)
- `use std.markdown` — CommonMark markdown parser and HTML converter

### N
- `use std.net` — Network sockets (TCP, UDP, DNS resolver)
- `use std.numfmt` — Human-readable numeric formatting (e.g. `10 MB`, `$1,234.56`)
- `use std.notify` — OS-level inter-thread notification events

### O
- `use std.proc` — Child process spawning, redirection, and exit tracking
- `use std.option` — Option unwrapping and monadic chains
- `use std.ordered` — Tree-based sorted collections (Red-Black, B-Tree)

### P
- `use std.parse` — Parser combinator primitives
- `use std.process` — Process lifecycle and signal handlers
- `use std.profile` — High-resolution benchmarking and CPU timing counters

### Q
- `use std.queue` — Deques, ring queues, and concurrent work-stealing queues
- `use std.query` — In-memory relational filtering and sorting DSL

### R
- `use std.rand` — High-performance pseudo-random generators (PCG, Xoroshiro)
- `use std.regex` — Regular expression engine (NFA/DFA)
- `use std.reflect` — Runtime reflection and type inspection helpers
- `use std.rpc` — Lightweight RPC and message framing

### S
- `use std.serialize` — Binary, TLV, and schema serialization
- `use std.set` — Hash and bitset collection variants
- `use std.socket` — Low-level raw socket operations
- `use std.sort` — Introsort, TimSort, and radix sorting
- `use std.stats` — Statistical functions (mean, median, standard deviation)
- `use std.str_zone` — Arena-backed string memory pooling
- `use std.sync` — Semaphores, barriers, and once-initialization

### T
- `use std.test` — Assertion libraries, mocking helpers, and benchmark runners
- `use std.text` — Word wrapping, column indentation, and text alignment
- `use std.timezone` — Olson/IANA timezone database parser
- `use std.timer` — High-resolution timers and scheduled callbacks

### U
- `use std.unicode` — Grapheme cluster break detection, uppercase/lowercase casing tables
- `use std.url` — RFC 3986 URL parser, builder, and query-string encoder
- `use std.uuid` — UUID v4 and v7 generators

### V
- `use std.validate` — Input data validators (email, URL, IP address)
- `use std.vecmath` — SIMD-accelerated 3D vector operations
- `use std.vfs` — Virtual filesystem abstraction (zip mount, memory fs)

### W
- `use std.web` — Fast HTTP router and request/response dispatch
- `use std.ws` — WebSocket protocol framing and client/server
- `use std.worker` — Work-stealing thread pools

### X
- `use std.xml` — Streaming XML pull parser

### Y
- `use std.yaml` — YAML parser and serializer

### Z
- `use std.zip` — Zip container extraction and compression
- `use std.zerocopy` — Zero-copy buffer views and slicing

---

## Phased Implementation Plan (Decoupling from Libc)

### Phase 1: Unify Existing Pure Velo Helpers into `std.*`
- Move existing compiler pure-Velo utilities (`src/common/string_builder.vl`, `src/common/path.vl`, `src/common/num_utils.vl`) into standard library modules (`std.str`, `std.path`, `std.fmt`).

### Phase 2: Implement Low-Level `std.mem` (Arena) & `std.fmt` (`itoa`)
- Implement an Arena allocator in pure Velo backed by direct OS page requests.
- Implement pure-Velo `itoa` / `ftoa` functions, eliminating C `printf` calls from basic programs.

### Phase 3: Pure Velo Buffered I/O (`std.io`)
- Wrap raw OS file handles in `std.io` with ring buffers.
- Redirect standard output to write directly via OS syscalls instead of C `fputs` / `fwrite`.

### Phase 4: Full Compiler Self-Hosting on `std.*`
- Update `src/main.vl` and backend drivers to use `std.mem`, `std.fmt`, and `std.io`.
- Verify deterministic self-hosting bootstrap without standard C runtime dependencies.

---

> For the granular, step-by-step task breakdown designed for AI agent execution, see [FOUNDATIONAL_STDLIB_ROADMAP.md](file:///c:/projects/easylang/FOUNDATIONAL_STDLIB_ROADMAP.md).

