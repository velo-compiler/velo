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
To prevent resource leaks and guarantee deterministic cleanup when managing memory, file handles, or system resources, Velo provides the `defer` keyword:

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

#### 2.2.1 Block-Scope Semantics & Boundaries
A `defer` statement schedules cleanup code to execute at the closing `}` of its immediately enclosing lexical block, **not** at function return. Lexical blocks forming cleanup boundaries include:
* **Function bodies**: `act name(...) { ... }`
* **Conditional branches**: `if cond { ... }` and `else { ... }`
* **Pattern match arms**: `on expr { pattern => { ... } }`
* **Loop iterations**: `loop ... { ... }`
* **Explicit bare & unsafe blocks**: `{ ... }` and `unsafe { ... }`
* **Zone arena blocks**: `zone { ... }`

#### 2.2.2 Reverse Declaration Order (LIFO)
Multiple `defer` statements declared within the same lexical block execute in strict Last-In, First-Out (LIFO) order upon block exit:
```rust
act example() {
    defer io.println("first declared, last executed (3)")
    defer io.println("second declared, middle executed (2)")
    defer io.println("third declared, first executed (1)")
}
```

#### 2.2.3 Loop Iteration Boundaries & Control Flow
* **Per-Iteration Cleanup**: Statements deferred inside a `loop` body execute at the end of each iteration before the condition for the next iteration is evaluated. Memory allocated in a loop cycle with a paired `defer mem.free(...)` is reclaimed on that same iteration, preventing cumulative heap leakage:
  ```rust
  loop 1000 {
      let buf = mem.heap_alloc(@u8, 1024)
      defer mem.free(buf)
      // buf is reclaimed at the end of each iteration (peak memory: 1024 bytes, not 1MB!)
  }
  ```
* **`continue` Handling**: Executing `continue` unwinds all deferred actions active within the current loop iteration before advancing to the next cycle.
* **`break` Handling**: Executing `break` unwinds all deferred actions active within the current loop iteration before breaking out of the loop. Statements deferred outside the loop body remain registered and are not executed by `break`.

#### 2.2.4 Early-Exit Unwinding (`return`, `fail`, `or return`)
* **Early `return`**: The return value expression (if any) is evaluated and saved into a temporary storage variable first. The compiler then unwinds all deferred statements across all currently active enclosing lexical blocks from innermost to outermost in LIFO order before emitting the C `return`.
* **Early `fail`**: The error expression is evaluated and stored into the algebraic outcome structure. All active enclosing deferred statements are unwound up to the function boundary in LIFO order before returning the error outcome.
* **`or return` Unwrapping**: When an expression followed by `or return` yields an error, active deferred statements in the current and enclosing scopes unwind in LIFO order before returning the failure.
* **Exited Blocks Isolation**: Blocks that completed normally have already executed their cleanups. Early exits unwind only blocks currently active on the stack, preventing double cleanup or double-free defects.

#### 2.2.5 Interaction with Zone Arenas
Deferred cleanups declared within a `zone` block execute *before* the zone watermark is rolled back (`velo_zone_pop`) or the arena is left (`velo_zone_leave`). This guarantees that deferred actions can safely inspect or copy data residing in the zone arena while its memory remains valid.

#### 2.2.6 Security & Memory Safety Invariants
* **Exactly-Once Execution**: Every deferred statement runs exactly once per dynamic entry of its declaring block.
* **Live Identifier Invariant**: Cleanups execute inside the block's C scope while all block-local identifiers remain declared in both the compiler symbol table and the generated C block scope, eliminating undeclared identifier and use-after-scope errors.
* **Zero Heap Leaks**: Allocations paired with `defer mem.free(...)` guarantee `mem.heap_used()` returns to baseline immediately upon block exit.
* **No Double-Free**: Cleanups are popped upon normal block exit, preventing re-execution on subsequent returns or function completion.

#### 2.2.7 Design Review Checklist
* [x] Block boundaries explicitly defined across `act`, `if`, `else`, `on`, `loop`, `{ ... }`, `unsafe`, and `zone`.
* [x] LIFO order guaranteed within blocks and across nested block unwinding.
* [x] Loop iteration boundary guarantees per-iteration cleanup with zero leak across iterations.
* [x] `break` and `continue` unwind current iteration only without affecting outer scopes.
* [x] Early `return`, `fail`, and `or return` evaluate return expressions first, then unwind active blocks.
* [x] Zone unwinding executes user defers before zone watermark rollback.
* [x] Cleanups emit inside the block's C scope where all block-local variables are live.
* [x] Exactly-once execution and zero-leak security invariants proven.

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
