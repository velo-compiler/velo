# Velo Step 2 Specification: The Compiler Essentials

Before Velo can compile itself in Stage 2 (Self-Hosting), it requires three fundamental capabilities:
1. **File System I/O (`sys.fs`)** — to read source code files from disk.
2. **Persistent Heap Allocation & `defer` (`sys.mem`)** — for AST trees and data structures that outlive temporary zones.
3. **Multi-File Module System (`use "file.vl"`)** — to split compiler code across clean, modular files.

This document formally specifies the syntax, semantics, and C runtime lowering for these three essentials.

---

## 1. File System I/O (`sys.fs`)

Velo provides native, zero-overhead file reading and writing via the `sys.fs` virtual namespace.

### 1.1 API Signatures

```rust
use sys.fs

// Reads the entire contents of a file into a null-terminated string buffer.
// Returns null if file cannot be opened or does not exist.
act fs.read_file(path: string) -> string

// Writes string content to a file. Overwrites existing files.
// Returns true on success, false on failure.
act fs.write_file(path: string, content: string) -> bool

// Checks if a file exists at the given path.
act fs.exists(path: string) -> bool

// Returns file size in bytes. Returns 0 if file does not exist.
act fs.size(path: string) -> usize
```

### 1.2 Memory Semantics of `fs.read_file`
* `fs.read_file` allocates a persistent buffer on the heap using standard OS memory (`malloc`).
* The developer is responsible for freeing the buffer when finished (recommended: using `defer mem.free(content)`).
* In C runtime, it is implemented using binary mode `fopen(path, "rb")`, measuring length via `fseek`/`ftell`, and reading the buffer in a single high-speed CPU chunk.

---

## 2. Persistent Heap Allocation & `defer`

In Stage 1, all dynamic allocations were temporary `zone` arena allocations. Step 2 introduces **Persistent Heap Memory** for long-lived compiler data structures.

### 2.1 Persistent Heap API (`sys.mem`)

```rust
use sys.mem

// Allocates persistent heap memory for 'count' instances of 'Type'.
// Guaranteed 8-byte aligned, backed by OS heap (malloc).
act mem.heap_alloc(@Type, count: usize) -> @Type

// Frees previously allocated persistent heap memory.
act mem.free(ptr: @void)

// Tracks total active heap bytes currently allocated.
act mem.heap_used() -> usize
```

### 2.2 The `defer` Statement
To prevent memory leaks when managing persistent heap memory, Velo provides the `defer` keyword:

```rust
act process_file(filename: string) {
    let content = fs.read_file(filename)
    if content == null {
        return
    }
    defer mem.free(content) // Guarantees mem.free runs when process_file exits!

    // Parse content...
    // Even if early return happens here, 'content' is safely freed!
}
```

#### Lowering Rules for `defer`:
* The compiler collects all `defer` statements in a block.
* Upon encountering any exit point (`return` or the closing `}` of the block), the compiler emits the deferred statements in **reverse order of declaration** (LIFO: Last-In, First-Out).

---

## 3. Multi-File Module System

A real compiler cannot exist in a single monolithic file. Step 2 introduces multi-file resolution.

### 3.1 Syntax

```rust
// Importing relative local files
use "tokens.vl"
use "compiler/lexer.vl"
use "compiler/parser.vl"
```

### 3.2 Module Resolution Rules
1. **Relative Paths**: Paths in quotes (e.g. `"tokens.vl"`) are resolved relative to the directory of the file containing the `use` statement.
2. **Include Guards / Deduplication**: 
   * The compiler maintains an internal `visited_modules` cache.
   * If file `A.vl` imports `tokens.vl` and `B.vl` also imports `tokens.vl`, the file is parsed and included **only once**.
3. **Visibility**:
   * All top-level `act` functions and `data` structs declared in an imported `.vl` file are placed in the global project scope.
   * Cross-calling between modules requires no header files.

---

## 4. C Runtime Lowering

The following functions are added directly to `velo_runtime.h`:

```c
// Persistent Heap
static inline void* velo_heap_alloc(size_t size, size_t count);
static inline void  velo_heap_free(void* ptr);
static inline size_t velo_heap_used(void);

// File System
static inline const char* velo_fs_read_file(const char* path);
static inline bool velo_fs_write_file(const char* path, const char* content);
static inline bool velo_fs_exists(const char* path);
static inline size_t velo_fs_size(const char* path);
```
