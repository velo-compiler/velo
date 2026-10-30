# Foundational Velo Standard Library (`std.*`) — AI Execution Roadmap

> **Mission:** Build the complete, bidirectional, pure-Velo foundational standard library (`std.mem`, `std.str`, `std.fmt`, `std.io`, `std.coll`) in deterministic, bite-sized micro-tasks.
> **Guiding Principle:** Zero C runtime dependency (`libc`). Every task is self-contained, strictly tested, under 400 lines of code, and executable by an AI agent without ambiguity or regressions.

---

## Golden Guardrails for AI Execution (Must Follow)
1. **File Line Budget:** No single `.vl` file may exceed **400 lines** (enforce with `python scripts/count_lines.py`).
2. **No UTF-8 BOM:** Always write raw UTF-8 without BOM (BOM triggers lexer error `\ufeff`).
3. **Pure Velo First:** Implement algorithms using `@u8` pointers, primitives, and memory offsets. Never call C library functions (`malloc`, `free`, `printf`, `sprintf`, `strlen`, `fopen`, `strtod`).
4. **Three-Step Completion Workflow (from `AGENTS.md`):**
   - **Verify:** Run test suite and dedicated module test.
   - **Update `gaps.md`:** Check off finished items with *Former Defect → Fix Applied → Verification*.
   - **Atomic Commit:** One conventional commit: `feat(std.<module>): <summary>`.

---

## Phase Dependency Order

$$\text{Phase 1: std.mem} \longrightarrow \text{Phase 2: std.str} \longrightarrow \text{Phase 3: std.fmt} \longrightarrow \text{Phase 4: std.io} \longrightarrow \text{Phase 5: std.coll}$$

---

# Phase 1: `std.mem` (Memory Allocation & Byte Operations)

Goal: Completely own raw memory allocation from the OS and provide both bump and general dynamic heap allocators.

### Task 1.1: Raw OS Page Allocator (`std/mem/page.vl`)
- **Objective:** Allocate and free raw virtual memory pages directly from the OS kernel.
- **Contract:**
  ```velo
  act os_page_alloc(size_bytes: usize) -> @u8
  act os_page_free(ptr: @u8, size_bytes: usize) -> bool
  ```
- **Implementation:**
  - On Windows: Use direct OS symbols `VirtualAlloc(null, size_bytes, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)` and `VirtualFree(ptr, 0, MEM_RELEASE)`.
  - On Linux: Direct syscalls `mmap(null, size_bytes, PROT_READ|PROT_WRITE, MAP_ANON|MAP_PRIVATE, -1, 0)` and `munmap(ptr, size_bytes)`.
- **Verification:** Write `tests/std_mem_page_test.vl`: allocate 64KB, write bytes at start and end, verify values, free memory.
- **Commit:** `feat(std.mem): implement raw OS virtual page allocator`

### Task 1.2: Pure Velo Byte Operations (`std/mem/ops.vl`)
- **Objective:** Pure Velo replacement for `memcpy`, `memset`, and `memcmp`.
- **Contract:**
  ```velo
  act copy(dest: @u8, src: @u8, n: usize)
  act set(dest: @u8, val: u8, n: usize)
  act eq(a: @u8, b: @u8, n: usize) -> bool
  ```
- **Implementation:**
  - Process unaligned head/tail bytes one byte at a time.
  - Process aligned interior in fast 8-byte (`u64`) words.
- **Verification:** Unit test comparing patterns across unaligned offsets (1–15 bytes) and large buffers (4096 bytes).
- **Commit:** `feat(std.mem): implement pure Velo copy, set, and eq byte operations`

### Task 1.3: Linear Arena Allocator (`std/mem/arena.vl`)
- **Objective:** Ultra-fast regional bump allocator with alignment support.
- **Contract:**
  ```velo
  struct Arena {
      buffer: @u8
      capacity: usize
      offset: usize
  }
  act arena_init(capacity: usize) -> Arena
  act arena_alloc(a: @Arena, size: usize, align: usize) -> @u8
  act arena_reset(a: @Arena)
  act arena_free(a: @Arena)
  ```
- **Implementation:**
  - `arena_alloc` calculates aligned offset: `(offset + align - 1) & ~(align - 1)`.
  - Increments offset by `size`. If exceeding `capacity`, returns `null`.
  - Backed by `os_page_alloc`.
- **Verification:** Test allocating 100 structs of varying alignment (1, 4, 8 bytes); verify addresses are aligned and reset restores offset to 0.
- **Commit:** `feat(std.mem): implement linear arena bump allocator`

### Task 1.4: Fixed-Size Freelist Allocator (`std/mem/slab.vl`)
- **Objective:** Recyclable node allocator for fixed-size elements (e.g. 32, 64, 128 bytes) to avoid fragmentation.
- **Contract:**
  ```velo
  struct SlabPool {
      block_size: usize
      free_head: @u8
      arena: Arena
  }
  act slab_init(block_size: usize, initial_capacity: usize) -> SlabPool
  act slab_alloc(p: @SlabPool) -> @u8
  act slab_free(p: @SlabPool, ptr: @u8)
  ```
- **Verification:** Allocate 50 blocks, free 25, reallocate 25; assert pointers are reused.
- **Commit:** `feat(std.mem): implement reusable slab pool allocator`

### Task 1.5: General Dynamic Heap Allocator (`std/mem/heap.vl`)
- **Objective:** Arbitrary-size allocator supporting `alloc`, `realloc`, and `free` (true replacement for C `malloc`, `realloc`, `free`).
- **Contract:**
  ```velo
  struct HeapHeader {
      size: usize
      is_free: bool
      next: @HeapHeader
  }
  act heap_init(initial_bytes: usize)
  act heap_alloc(size: usize) -> @u8
  act heap_realloc(ptr: @u8, new_size: usize) -> @u8
  act heap_free(ptr: @u8)
  ```
- **Implementation:**
  - Intrusive free-list with block coalescing on adjacent free blocks.
  - Backed by chunks requested via `os_page_alloc`.
- **Verification:** Allocate arbitrary sizes (16, 120, 2048 bytes), realloc to larger sizes verifying data preservation, free blocks, reallocate and verify block reuse.
- **Commit:** `feat(std.mem): implement general dynamic heap allocator with realloc and coalescing`

---

# Phase 2: `std.str` (Byte Slices, UTF-8 & Manipulation)

Goal: Provide fast, non-allocating string views, strict UTF-8 validation, and trimming/splitting without C `string.h`.

### Task 2.1: String Slice View (`std/str/slice.vl`)
- **Objective:** Pure Velo non-null-terminated string slice.
- **Contract:**
  ```velo
  struct StrSlice {
      ptr: @u8
      len: usize
  }
  act slice_from_raw(ptr: @u8, len: usize) -> StrSlice
  act slice_sub(s: StrSlice, start: usize, end: usize) -> StrSlice
  act slice_eq(a: StrSlice, b: StrSlice) -> bool
  ```
- **Verification:** Slicing substrings without memory allocation; assert equality on matching and non-matching slices.
- **Commit:** `feat(std.str): introduce StrSlice view and comparison`

### Task 2.2: UTF-8 Decoder & Validator (`std/str/utf8.vl`)
- **Objective:** Validate UTF-8 sequences and decode Unicode code points (runes).
- **Contract:**
  ```velo
  act utf8_is_valid(bytes: @u8, len: usize) -> bool
  act utf8_decode_next(bytes: @u8, len: usize, out_rune: @u32) -> usize // returns bytes consumed
  ```
- **Implementation:**
  - Branchless/table check: 1-byte (`0x00..0x7F`), 2-byte (`0xC2..0xDF`), 3-byte (`0xE0..0xEF`), 4-byte (`0xF0..0xF4`).
  - Rejects overlong encodings, surrogate halves (`0xD800..0xDFFF`), and values > `0x10FFFF`.
- **Verification:** Test valid ASCII, 2-byte (Cyrillic/Greek), 3-byte (CJK/accents), 4-byte (emojis), and assert false on invalid/truncated UTF-8 sequences.
- **Commit:** `feat(std.str): add pure Velo UTF-8 decoder and validation`

### Task 2.3: Substring Search & Inspection (`std/str/search.vl`)
- **Objective:** Pure Velo substring search and string queries.
- **Contract:**
  ```velo
  act str_index_of(haystack: StrSlice, needle: StrSlice) -> isize
  act str_starts_with(s: StrSlice, prefix: StrSlice) -> bool
  act str_ends_with(s: StrSlice, suffix: StrSlice) -> bool
  ```
- **Verification:** Unit tests with prefix, suffix, middle matches, empty strings, and needle longer than haystack.
- **Commit:** `feat(std.str): add index_of, starts_with, and ends_with search algorithms`

### Task 2.4: Arena-Backed Dynamic StringBuilder (`std/str/builder.vl`)
- **Objective:** High-performance buffer for string accumulation.
- **Contract:**
  ```velo
  struct StrBuilder {
      buffer: @u8
      len: usize
      capacity: usize
      arena: @Arena
  }
  act sb_init(arena: @Arena, initial_cap: usize) -> StrBuilder
  act sb_append_slice(sb: @StrBuilder, slice: StrSlice)
  act sb_append_byte(sb: @StrBuilder, b: u8)
  act sb_to_slice(sb: @StrBuilder) -> StrSlice
  ```
- **Verification:** Append 1,000 fragments, verify resulting slice content and length.
- **Commit:** `feat(std.str): implement arena-backed StrBuilder`

### Task 2.5: String Manipulation & Splitting (`std/str/manip.vl`)
- **Objective:** Trimming, splitting, and ASCII casing without extra heap allocation.
- **Contract:**
  ```velo
  struct StrSplitIter {
      src: StrSlice
      delim: u8
      pos: usize
  }
  act str_trim(s: StrSlice) -> StrSlice
  act str_trim_start(s: StrSlice) -> StrSlice
  act str_trim_end(s: StrSlice) -> StrSlice
  act str_split_init(s: StrSlice, delim: u8) -> StrSplitIter
  act str_split_next(it: @StrSplitIter, out_part: @StrSlice) -> bool
  act str_to_lower_ascii(s: StrSlice, dest: @u8)
  act str_to_upper_ascii(s: StrSlice, dest: @u8)
  ```
- **Verification:** Test trimming spaces/newlines/tabs on both ends; split `"a,b,c"` by `','` and verify 3 segments; test ASCII case conversion.
- **Commit:** `feat(std.str): add trimming, split iterator, and ASCII casing`

---

# Phase 3: `std.fmt` (Complete Formatting & Parsing)

Goal: Convert numbers (integers and floats) to text and text to numbers without C `printf`, `sprintf`, `strtod`, or `libm`.

### Task 3.1: Pure Velo Integer to String `itoa` (`std/fmt/itoa.vl`)
- **Objective:** Format `i64` and `u64` into ASCII digits in caller-provided stack buffers.
- **Contract:**
  ```velo
  act format_u64(val: u64, buf: @u8, buf_len: usize) -> StrSlice
  act format_i64(val: i64, buf: @u8, buf_len: usize) -> StrSlice
  act format_hex(val: u64, upper: bool, buf: @u8, buf_len: usize) -> StrSlice
  act format_bin(val: u64, buf: @u8, buf_len: usize) -> StrSlice
  ```
- **Implementation:**
  - Modulo/division by 10 into small stack buffer from back to front.
  - Handles negative numbers and `i64_MIN` without overflow.
- **Verification:** Test `0`, positive numbers, negative numbers, `i64_MIN`, `i64_MAX`, `u64_MAX`, hex `0xDEADBEEF`.
- **Commit:** `feat(std.fmt): implement pure Velo itoa, hex, and binary formatters`

### Task 3.2: String to Integer Parser `atoi` (`std/fmt/atoi.vl`)
- **Objective:** Parse text into numbers with sign handling and overflow detection.
- **Contract:**
  ```velo
  act parse_i64(s: StrSlice, out_val: @i64) -> bool
  act parse_u64(s: StrSlice, out_val: @u64) -> bool
  ```
- **Verification:** Test valid inputs, leading whitespace trimming, negative numbers, invalid characters, and overflow errors.
- **Commit:** `feat(std.fmt): implement pure Velo string-to-integer parser`

### Task 3.3: Interpolation Buffer Formatter (`std/fmt/buffer.vl`)
- **Objective:** Provide structured primitive formatting and padding into `StrBuilder`.
- **Contract:**
  ```velo
  act fmt_write_str(sb: @StrBuilder, s: StrSlice)
  act fmt_write_i64(sb: @StrBuilder, val: i64)
  act fmt_write_bool(sb: @StrBuilder, val: bool)
  act fmt_write_padded(sb: @StrBuilder, s: StrSlice, width: usize, pad_char: u8, right_align: bool)
  ```
- **Verification:** Format composite message `"code=" + -404` and padded numbers (`%04d` equivalent) and assert exact strings.
- **Commit:** `feat(std.fmt): implement composite formatting and padding helpers`

### Task 3.4: Pure Velo Float Formatting & Parsing (`std/fmt/ftoa.vl`)
- **Objective:** Complete float-to-string (`ftoa`) and string-to-float (`atof`) without C `sprintf` or `strtod`.
- **Contract:**
  ```velo
  act format_f64(val: f64, precision: i32, buf: @u8, buf_len: usize) -> StrSlice
  act parse_f64(s: StrSlice, out_val: @f64) -> bool
  ```
- **Implementation:**
  - Fast Grisu / integer-scaled decimal breakdown.
  - Handles special values: `NaN`, `+Inf`, `-Inf`, negative zero `-0.0`.
  - Parser handles integer part, decimal dot, fractional part, and optional exponent (`e+10`, `e-5`).
- **Verification:** Test `0.0`, `-0.0`, `3.14159`, `1e-4`, `NaN`, `Inf`, and round-trip parse/format assertions.
- **Commit:** `feat(std.fmt): implement pure Velo ftoa and atof float operations`

---

# Phase 4: `std.io` (Ring-Buffered Streams, Input & Output)

Goal: High-performance bidirectional I/O (both reading and writing) without C `stdio.h` (`printf`, `fgets`, `FILE*`).

### Task 4.1: OS Standard Handle Provider (`std/io/handle.vl`)
- **Objective:** Acquire raw OS handles for stdin, stdout, and stderr.
- **Contract:**
  ```velo
  struct FileHandle {
      os_handle: usize
  }
  act io_stdin_handle() -> FileHandle
  act io_stdout_handle() -> FileHandle
  act io_stderr_handle() -> FileHandle
  act io_raw_write(h: FileHandle, data: @u8, len: usize) -> usize
  act io_raw_read(h: FileHandle, buf: @u8, max_len: usize) -> isize
  ```
- **Implementation:**
  - Windows: Call `GetStdHandle(-10)` (stdin), `GetStdHandle(-11)` (stdout), `WriteFile`, `ReadFile`.
  - Linux: Syscalls `sys_read(0, ...)` and `sys_write(1, ...)`.
- **Verification:** Write 10 raw bytes to stdout and assert return code equals 10; test reading simulated pipe buffer.
- **Commit:** `feat(std.io): add raw OS handle stream read and write operations`

### Task 4.2: Ring-Buffered Stream Writer (`std/io/buffered_writer.vl`)
- **Objective:** Accumulate small writes in a 4KB internal buffer and flush in chunks.
- **Contract:**
  ```velo
  struct BufferedWriter {
      handle: FileHandle
      buf: [4096]u8
      count: usize
  }
  act writer_init(h: FileHandle) -> BufferedWriter
  act writer_write(w: @BufferedWriter, data: @u8, len: usize)
  act writer_flush(w: @BufferedWriter)
  ```
- **Verification:** Perform 100 small 8-byte writes; verify buffer flushes correctly and preserves sequence.
- **Commit:** `feat(std.io): implement 4KB buffered stream writer`

### Task 4.3: Console Print API (`std/io/print.vl`)
- **Objective:** Public pure Velo printing API replacing `sys.io`.
- **Contract:**
  ```velo
  act print(s: StrSlice)
  act println(s: StrSlice)
  act print_i64(val: i64)
  act println_i64(val: i64)
  act print_f64(val: f64, precision: i32)
  act println_f64(val: f64, precision: i32)
  ```
- **Implementation:**
  - Uses static `BufferedWriter` bound to stdout.
  - Automatically appends newline (`\n`) for `println`.
- **Verification:** Integration test invoking `println` and verifying console output in subprocess test runner.
- **Commit:** `feat(std.io): introduce pure Velo print and println`

### Task 4.4: Ring-Buffered Stream Reader & Line Input (`std/io/buffered_reader.vl`)
- **Objective:** Pure Velo input reading with line-buffering (true replacement for `fgets` and `scanf`).
- **Contract:**
  ```velo
  struct BufferedReader {
      handle: FileHandle
      buf: [4096]u8
      pos: usize
      limit: usize
  }
  act reader_init(h: FileHandle) -> BufferedReader
  act reader_read_byte(r: @BufferedReader, out_byte: @u8) -> bool
  act reader_read_line(r: @BufferedReader, sb: @StrBuilder) -> bool
  ```
- **Implementation:**
  - Fills 4KB buffer on demand from `io_raw_read`.
  - `reader_read_line` extracts bytes until `\n`, stripping optional `\r`.
- **Verification:** Feed multi-line mock stream data; read line by line and verify exact contents of each line.
- **Commit:** `feat(std.io): implement buffered reader and line-by-line input`

---

# Phase 5: `std.coll` (Core Pure Velo Collections)

Goal: Resizable arrays, circular rings, and dynamic hash maps with zero C runtime dependencies and full deletion support.

### Task 5.1: Dynamic Shelf (Vector) (`std/coll/shelf.vl`)
- **Objective:** Dynamic contiguous array with growth policy.
- **Contract:**
  ```velo
  struct RawShelf {
      data: @u8
      elem_size: usize
      len: usize
      cap: usize
  }
  act shelf_create(elem_size: usize, initial_cap: usize) -> RawShelf
  act shelf_push(s: @RawShelf, elem_ptr: @u8)
  act shelf_get(s: @RawShelf, index: usize) -> @u8
  ```
- **Implementation:**
  - Backed by `std.mem.heap_alloc` and `std.mem.heap_realloc`.
- **Verification:** Push 10,000 64-bit integers; check that reallocation succeeds and all elements match index.
- **Commit:** `feat(std.coll): implement pure Velo dynamic shelf array`

### Task 5.2: Shelf Lifecycle & Full Operations (`std/coll/shelf_ops.vl`)
- **Objective:** Full collection operations: pop, delete at index, shrink, and free.
- **Contract:**
  ```velo
  act shelf_pop(s: @RawShelf, out_elem: @u8) -> bool
  act shelf_delete_at(s: @RawShelf, index: usize) -> bool
  act shelf_clear(s: @RawShelf)
  act shelf_free(s: @RawShelf)
  ```
- **Verification:** Push 10 items, pop 3, delete item at index 2, assert element shift and final length; call `shelf_free` and verify memory release.
- **Commit:** `feat(std.coll): add shelf pop, delete_at, and explicit free operations`

### Task 5.3: Ring Buffer (FIFO) (`std/coll/ring.vl`)
- **Objective:** Circular ring buffer for queueing and packet streaming.
- **Contract:**
  ```velo
  struct RawRing {
      buffer: @u8
      elem_size: usize
      cap: usize
      head: usize
      tail: usize
      count: usize
  }
  act ring_create(elem_size: usize, cap: usize) -> RawRing
  act ring_push(r: @RawRing, elem: @u8) -> bool
  act ring_pop(r: @RawRing, out_elem: @u8) -> bool
  act ring_free(r: @RawRing)
  ```
- **Verification:** Push and pop 500 items in interleaved fashion; assert FIFO ordering.
- **Commit:** `feat(std.coll): implement pure Velo ring buffer`

### Task 5.4: Pure Velo Hash Algorithms (`std/coll/hash.vl`)
- **Objective:** Fast, high-entropy 64-bit hashing for strings, integers, and raw bytes.
- **Contract:**
  ```velo
  act hash_bytes(data: @u8, len: usize) -> u64
  act hash_str(s: StrSlice) -> u64
  act hash_u64(val: u64) -> u64
  ```
- **Implementation:** 64-bit FNV-1a or Wyhash (bitwise operations only, pure Velo).
- **Verification:** Hash 1,000 distinct strings and integers; verify zero collisions on distinct inputs.
- **Commit:** `feat(std.coll): implement 64-bit pure Velo hash functions`

### Task 5.5: Open-Addressing Hash Map (`std/coll/map.vl`)
- **Objective:** High-speed string-to-value hash map with linear probing.
- **Contract:**
  ```velo
  struct StrMap {
      keys: @StrSlice
      values: @usize
      occupied: @bool
      cap: usize
      count: usize
  }
  act map_create(initial_cap: usize) -> StrMap
  act map_insert(m: @StrMap, key: StrSlice, value: usize) -> bool
  act map_get(m: @StrMap, key: StrSlice, out_value: @usize) -> bool
  ```
- **Verification:** Insert 500 key-value pairs, verify lookup finds all 500, non-existent keys return false.
- **Commit:** `feat(std.coll): implement open-addressing string hash map`

### Task 5.6: Map Tombstone Deletion & Table Expansion (`std/coll/map_ops.vl`)
- **Objective:** Complete map lifecycle: key deletion with tombstones, dynamic rehashing on load-factor >= 0.70, and map free.
- **Contract:**
  ```velo
  act map_remove(m: @StrMap, key: StrSlice) -> bool
  act map_rehash(m: @StrMap, new_cap: usize) -> bool
  act map_free(m: @StrMap)
  ```
- **Verification:** Insert 1,000 keys causing rehash; delete 500 keys, assert deleted keys return false while remaining 500 succeed; verify `map_free` releases memory.
- **Commit:** `feat(std.coll): add tombstone deletion, dynamic rehashing, and map_free`

---

## AI Agent Check-off Table (24 Granular Tasks)

| Task ID | Component | Status | Target File | Verification |
|:---|:---|:---:|:---|:---|
| **1.1** | `std.mem.page` | [x] | `std/mem/page.vl` | `std/tests/mem/page_test.vl` |
| **1.2** | `std.mem.ops` | [x] | `std/mem/ops.vl` | `std/tests/mem/ops_test.vl` |
| **1.3** | `std.mem.arena` | [ ] | `std/mem/arena.vl` | `std/tests/mem/arena_test.vl` |
| **1.4** | `std.mem.slab` | [ ] | `std/mem/slab.vl` | `std/tests/mem/slab_test.vl` |
| **1.5** | `std.mem.heap` | [ ] | `std/mem/heap.vl` | `std/tests/mem/heap_test.vl` |
| **2.1** | `std.str.slice` | [ ] | `std/str/slice.vl` | `std/tests/str/slice_test.vl` |
| **2.2** | `std.str.utf8` | [ ] | `std/str/utf8.vl` | `std/tests/str/utf8_test.vl` |
| **2.3** | `std.str.search` | [ ] | `std/str/search.vl` | `std/tests/str/search_test.vl` |
| **2.4** | `std.str.builder` | [ ] | `std/str/builder.vl` | `std/tests/str/builder_test.vl` |
| **2.5** | `std.str.manip` | [ ] | `std/str/manip.vl` | `std/tests/str/manip_test.vl` |
| **3.1** | `std.fmt.itoa` | [ ] | `std/fmt/itoa.vl` | `std/tests/fmt/itoa_test.vl` |
| **3.2** | `std.fmt.atoi` | [ ] | `std/fmt/atoi.vl` | `std/tests/fmt/atoi_test.vl` |
| **3.3** | `std.fmt.buffer` | [ ] | `std/fmt/buffer.vl` | `std/tests/fmt/buffer_test.vl` |
| **3.4** | `std.fmt.ftoa` | [ ] | `std/fmt/ftoa.vl` | `std/tests/fmt/ftoa_test.vl` |
| **4.1** | `std.io.handle` | [ ] | `std/io/handle.vl` | `std/tests/io/handle_test.vl` |
| **4.2** | `std.io.buffered_writer` | [ ] | `std/io/buffered_writer.vl` | `std/tests/io/buffered_writer_test.vl` |
| **4.3** | `std.io.print` | [ ] | `std/io/print.vl` | `std/tests/io/print_test.vl` |
| **4.4** | `std.io.buffered_reader` | [ ] | `std/io/buffered_reader.vl` | `std/tests/io/buffered_reader_test.vl` |
| **5.1** | `std.coll.shelf` | [ ] | `std/coll/shelf.vl` | `std/tests/coll/shelf_test.vl` |
| **5.2** | `std.coll.shelf_ops` | [ ] | `std/coll/shelf_ops.vl` | `std/tests/coll/shelf_ops_test.vl` |
| **5.3** | `std.coll.ring` | [ ] | `std/coll/ring.vl` | `std/tests/coll/ring_test.vl` |
| **5.4** | `std.coll.hash` | [ ] | `std/coll/hash.vl` | `std/tests/coll/hash_test.vl` |
| **5.5** | `std.coll.map` | [ ] | `std/coll/map.vl` | `std/tests/coll/map_test.vl` |
| **5.6** | `std.coll.map_ops` | [ ] | `std/coll/map_ops.vl` | `std/tests/coll/map_ops_test.vl` |
