# 🏛️ Velo Standard Library Architecture & Platform Contract

> **Scope**: Standard library design, cross-platform portability contract, compiler intrinsic boundaries, memory allocation tiers, and error model.
> **Living Document**: Enforces Architectural Invariants **I70.1–I70.4** and Documentation Invariants **I83.1–I83.2**.

---

## 1. Architectural Mission & Overview

The Velo standard library (`std/`) is engineered to deliver high-velocity, deterministic systems programming without garbage collection pauses. Unlike languages that rely on large, opaque C runtimes or monolithic standard libraries, Velo enforces a strict modular hierarchy:

1. **Clean C99 lowering**: Standard library modules compile down to human-readable, portable C99 code with zero hidden allocations.
2. **Strict platform neutrality**: User code targeting `std.*` compiles identically across Windows, Linux, and macOS without platform `#ifdef` pollution in user source.
3. **Fail-closed boundaries**: Compiler intrinsics (`sys.*`), standard library facilities (`std.*`), and operating system bindings (`std/*_<plat>.vl`) are cleanly partitioned into distinct architectural layers.

```
┌─────────────────────────────────────────────────────────────┐
│                    User Application (.vl)                   │
└──────────────────────────────┬──────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
 ┌──────────────────────┐             ┌──────────────────────┐
 │  Compiler Intrinsics │             │   Standard Library   │
 │       (sys.*)        │             │        (std.*)       │
 └──────────┬───────────┘             └──────────┬───────────┘
            │                                    │
            │ (Direct lowering)                  │ (Facade)
            ▼                                    ▼
 ┌──────────────────────┐             ┌──────────────────────┐
 │ runtime/velo_runtime.h│             │ Platform Resolver    │
 └──────────┬───────────┘             └──────────┬───────────┘
            │                                    │
            │                  ┌─────────────────┼─────────────────┐
            │                  ▼                 ▼                 ▼
            │           ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
            │           │   Windows   │   │    Linux    │   │    macOS    │
            │           │ (*_windows) │   │  (*_linux)  │   │  (*_macos)  │
            │           └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
            │                  │                 │                 │
            ▼                  ▼                 ▼                 ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                Target OS System Calls & C Libc              │
 └─────────────────────────────────────────────────────────────┘
```

---

## 2. The Platform-Model Contract

During early development (Phases 1–69), Windows-specific `extern` calls leaked directly into portable library facades. Phase 70 resolved this architectural defect and established the **Velo Platform Contract**.

### 2.1 The Facade + Target Variant Architecture

Standard library modules exposing operating system capabilities follow a **facade pattern**:

* **The Facade (`std/<module>/<submodule>.vl`)**:
  Exposes the canonical, platform-neutral public API, public data structures (`view data`), and typed outcomes. A facade **never** declares platform-specific `extern` functions or imports OS headers.
* **Target Sibling Implementations**:
  Operating system calls are isolated into target sibling files:
  * `<submodule>_windows.vl` — Win32 APIs (Kernel32, WS2_32, Advapi32).
  * `<submodule>_linux.vl` — Linux POSIX and kernel syscalls (`epoll`, `pipe2`, `eventfd`).
  * `<submodule>_macos.vl` — Darwin POSIX and Apple-specific frameworks (`kqueue`).
  * `<submodule>_posix.vl` — Generic POSIX implementations shared across UNIX targets.

### 2.2 Compile-Time Platform Resolution

The compiler driver (`src/backend/platform_resolve.vl`) acts as the single source of truth for platform dispatch:

1. **Target Selection**: When compiling with `--target <target>`, the driver binds the active platform (`windows`, `linux`, or `macos`).
2. **Selective Inclusion**: Modules carrying a `_<plat>.vl` suffix that do not match the active target are filtered out of lexical scanning and type analysis.
3. **Sibling Completeness (Invariant I70.2)**: Every platform-specific submodule must provide a sibling implementation for every supported target platform. If a facade requests a variant that does not exist for the target architecture, compilation halts with diagnostic `VELO-E0015: Unsupported platform target`.

### 2.3 The Extern Isolation Invariant (Invariant I70.1)

```
INVARIANT I70.1:
No .vl file in std/ outside a *_windows.vl or *_win32.vl file may declare
an extern bound to a kernel32, advapi32, or ws2_32 symbol. Symmetrically,
POSIX system headers (unistd.h, sys/socket.h) are restricted strictly to
POSIX target variants.
```

By enforcing Invariant I70.1, the emitted C for any portable Velo program is guaranteed to link cleanly with a standard toolchain (`cc -O2 -std=c99 -lm -lpthread`) on Linux and macOS without unresolved Win32 symbols.

---

## 3. The Intrinsic Boundary (`sys.*` vs `std.*`)

Velo maintains a fundamental distinction between **compiler intrinsics** (`sys.*`) and **standard library modules** (`std.*`):

| Property | Compiler Intrinsics (`sys.*`) | Standard Library (`std.*`) |
| :--- | :--- | :--- |
| **Origin** | Built into compiler backend (`src/common/intrinsics.vl`) | Shipped as source code in `std/` |
| **Import Syntax** | `use sys.io`, `use sys.mem`, `use sys.time` | `use std.fs`, `use std.net`, `use std.os` |
| **Compilation** | Lowered directly to C macros in `velo_runtime.h` | Parsed, type-checked, and emitted as C code |
| **Runtime Overhead** | Zero function call overhead (inlined) | Minimal inline/monomorphized function calls |
| **Dependencies** | None (self-contained, standalone C99) | Depends on `sys.*` and platform facades |
| **Memory Policy** | Zero heap allocations | Explicit memory tiers (Zone, Heap, Arena, Page) |

### 3.1 Intrinsics Scope (`sys.*`)

* **`sys.io`**: Bare-metal formatting and terminal stream output (`println`, `print`, `eprintln`). Lowered directly to `printf`/`fputs` in `runtime/velo_runtime.h`.
* **`sys.mem`**: Stack-disciplined zone arena watermark manipulation (`velo_zone_push`, `velo_zone_pop`), raw memory copying (`velo_mem_copy`), and type alignment queries.
* **`sys.time`**: High-resolution hardware performance counter ticks (`QueryPerformanceCounter` on Windows, `clock_gettime(CLOCK_MONOTONIC)` on POSIX).
* **CPU & Atomic Primitives**: Memory fences (`sys.mem.fence`), atomic fetch-and-add, atomic compare-and-swap, bit-counting (`clz`, `ctz`), and byte-order swaps.

### 3.2 Standard Library Scope (`std.*`)

* **`std.fs`**: High-level filesystem paths, directory streams, file metadata, and streaming I/O.
* **`std.net`**: Non-blocking TCP/UDP sockets, IPv4/IPv6 address parsing, DNS resolution.
* **`std.os`**: Process spawning, environment variable dictionaries, signal traps.
* **`std.crypto`**: Cryptographically secure pseudorandom numbers (CSPRNG), SHA-256 hashing.
* **`std.async`**: Cross-platform asynchronous event polling (wrapping Windows IOCP, Linux `epoll`, macOS `kqueue`).
* **`std.mem`**: Dynamic collections (`List[T]`, `Map[K, V]`), user arenas, and virtual page allocators.

---

## 4. Allocation Tiers & Memory Discipline

Memory management in Velo is explicit, deterministic, and devoid of non-deterministic garbage collection pauses. The standard library operates across four distinct memory allocation tiers:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Zone Arena Tier (zone { ... } / sys.mem)                 │
│    Fast bump pointer, O(1) instant watermark restoration    │
├─────────────────────────────────────────────────────────────┤
│ 2. Custom Arena Tier (std.mem.arena / Arena[T])             │
│    User-controlled arena instances, bulk reset / destroy    │
├─────────────────────────────────────────────────────────────┤
│ 3. Dynamic Heap Tier (std.mem.heap / heap_alloc)            │
│    Long-lived dynamic structures, paired with LIFO defer    │
├─────────────────────────────────────────────────────────────┤
│ 4. Virtual Page Tier (std.mem.page / page_alloc)            │
│    Direct OS page mappings (VirtualAlloc / mmap)            │
└─────────────────────────────────────────────────────────────┘
```

### 4.1 Tier 1: The Zone Arena (`zone { ... }`)
* **Mechanism**: Thread-local continuous memory arena with a hardware bump-pointer.
* **Cost**: $O(1)$ allocation (pointer increment); $O(1)$ instantaneous reclamation on block exit.
* **Discipline**: Strictly stack-disciplined. When entering a `zone` block, `sys.mem.zone_push()` records the current watermark; on exit, `sys.mem.zone_pop()` rolls the watermark back.
* **Use Cases**: Frame lifecycles in game engines, transient HTTP request parsing, compiler AST passes, temporary string concatenation.
* **Guarantee**: Zero memory fragmentation; zero GC pause stutters.

### 4.2 Tier 2: Custom Arenas (`std.mem.arena`)
* **Mechanism**: Programmatically instantiated arena objects (`Arena`).
* **Cost**: Bump-allocated inside user-sized buffers or multi-page blocks.
* **Discipline**: Explicit manual lifecycle (`arena_reset(a)` or `arena_free(a)`).
* **Use Cases**: Independent subsystem allocations (e.g. game level loads, worker thread pipelines).

### 4.3 Tier 3: Dynamic Heap (`std.mem.heap`)
* **Mechanism**: General-purpose heap allocator backed by C libc `malloc` and `free`.
* **Cost**: Dynamic block header traversal and OS allocator bookkeeping.
* **Discipline**: Manual ownership paired with deterministic LIFO `defer`:
  ```velo
  let buf = heap_alloc(size)
  defer heap_free(buf)
  ```
* **Use Cases**: Long-lived data structures, compiler symbol tables, persistent cache nodes.

### 4.4 Tier 4: Virtual Pages (`std.mem.page`)
* **Mechanism**: Direct kernel virtual memory allocation (`VirtualAlloc` on Windows; `mmap` with `MAP_ANONYMOUS` on POSIX).
* **Cost**: Direct system call; minimum granularity is the 4 KB operating system page.
* **Discipline**: Explicit `page_alloc(pages)` and `page_free(ptr, pages)`.
* **Use Cases**: Large contiguous memory mappings, ring buffers, backing blocks for custom allocators.

---

## 5. The Error Model & Resource Safety

Velo rejects hidden control flow, runtime unwinding, and C++-style exceptions. The standard library enforces an explicit, value-based error model.

### 5.1 Tagged Union Outcome Pattern

Standard library functions returning fallible results return typed tagged unions (`kind`):

```velo
view kind FsOutcome {
    Ok(@File)
    Err(FsError)
}

view kind FsError {
    NotFound
    PermissionDenied
    AlreadyExists
    DiskFull
    InvalidName
    IoError
}
```

Callers handle outcomes explicitly using pattern matching (`on`):

```velo
let res = fs.open("config.json", FileMode.Read)
on res {
    Ok(file) {
        defer file.close()
        // Read file contents safely
    }
    Err(err) {
        io.eprintln("Failed to open file: {err}")
    }
}
```

### 5.2 Deterministic LIFO Resource Cleanup (`defer`)

Velo guarantees that statements prefixed with `defer` execute in reverse declaration order (LIFO) upon leaving the enclosing scope, whether exit occurs normally or via early return.

```velo
act process_data(path: string) -> bool {
    let f = fs.open(path, FileMode.Read)
    if f == null { return false }
    defer f.close()

    let mem = heap_alloc(1024)
    defer heap_free(mem)

    // Resources are guaranteed to be freed in order:
    // 1. heap_free(mem)
    // 2. f.close()
    return true
}
```

### 5.3 Operating System Error Code Translation

Platform-specific error codes (`GetLastError()` on Windows, `errno` on POSIX) are **never leaked** into public standard library APIs. Sibling implementations translate raw operating system error codes into canonical Velo enum kinds at the facade boundary:

```
[Win32 ERROR_FILE_NOT_FOUND (2)] ──┐
                                   ├──► [FsError.NotFound]
[POSIX ENOENT (2)]                ──┘
```

---

## 6. Living Architectural Invariants

The standard library conforms to the following non-negotiable architectural invariants:

| Invariant | Name | Description |
| :--- | :--- | :--- |
| **I70.1** | **Extern Isolation** | No standard library file outside `*_windows.vl` or `*_win32.vl` may declare Win32 `extern` symbols. |
| **I70.2** | **Sibling Completeness** | Every platform-specific submodule must have a matching sibling for every supported platform. |
| **I70.3** | **Standalone Bootstrap** | `bootstrap.c` compiles and links with clean `-lm -lpthread` flags on POSIX with zero Win32 symbols. |
| **I70.4** | **Clean Codegen** | Programs importing standard modules emit C code free of target-foreign operating system symbols. |
| **I83.1** | **Claims Integrity** | Every quantitative performance or footprint claim in docs must be backed by a committed reproduction script. |
| **I83.2** | **Measurability** | A claim that cannot be measured is removed from user-facing documentation, not softened. |

---

## 7. Verification & Conformance Testing

Compliance with the Standard Library Architecture is continuously validated across the automated test suite:

* **Platform Resolution Tests**: `tests/test_platform_resolver.py`
* **Showcase Application Tests**: `tests/test_showcase.py`
* **Resource Ceiling Tests**: `tests/test_resource_ceilings.py`
* **Compiler Crash-Freedom Tests**: `tests/test_compiler_no_crash.py`
* **Empirical Benchmarks**: [`benchmark/RESULTS.md`](../benchmark/RESULTS.md) and [`benchmark/MEMORY_RESULTS.md`](../benchmark/MEMORY_RESULTS.md)
