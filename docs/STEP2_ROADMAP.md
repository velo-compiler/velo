# Velo Step 2 Roadmap: The Compiler Essentials

This roadmap defines the engineering milestones to complete **Step 2** and prepare Velo for **Stage 2 (Self-Hosting)**.

---

## Step 2 Milestones

### Milestone 2.1: Persistent Heap Allocation & `defer`
* **Goal**: Support long-lived heap memory with zero-leak safety via `defer`.
* **Deliverables**:
  * Lexer/Parser support for `defer <statement>` and `null`.
  * Runtime implementation of `velo_heap_alloc`, `velo_heap_free`, and `velo_heap_used`.
  * Codegen support for LIFO execution of `defer` statements at block exits and returns.
* **Test Case**: `examples/06_heap_and_defer.vl` allocates memory, exits through early returns, and asserts zero heap memory leaked.

---

### Milestone 2.2: File System I/O (`sys.fs`)
* **Goal**: Enable Velo to read and write files on disk at native speed.
* **Deliverables**:
  * Runtime implementation of `fs.read_file`, `fs.write_file`, `fs.exists`, and `fs.size`.
  * Safe memory management of read buffers using `defer mem.free(content)`.
* **Test Case**: `examples/07_file_io.vl` writes a test file, checks existence and file size, reads it back, asserts content match, and cleans up.

---

### Milestone 2.3: Multi-File Imports (`use "module.vl"`)
* **Goal**: Split programs across multiple `.vl` files with automatic deduplication.
* **Deliverables**:
  * Parser support for string module paths in `use "filename.vl"`.
  * Recursive AST resolver with dependency graph cycle detection and deduplication.
  * Cross-module function calls and struct sharing.
* **Test Case**: `examples/08_multifile/main.vl` imports `math_utils.vl` and `types.vl`, sharing structs and functions across files.

---

### Milestone 2.4: The "Self-Hosting Readiness" Test
* **Goal**: A Velo program that reads another Velo source file from disk, processes tokens across modules, and prints results.
* **Deliverables**:
  * Complete integrated demo verifying all three essentials work harmoniously.
  * Formal sign-off to begin **Stage 2 (Self-Hosting)**!
