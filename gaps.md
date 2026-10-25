# The Velo Language Gap Analysis & Phased Engineering Roadmap 📋

> **Document Status**: Active Phased Roadmap & Open Engineering Backlog  
> **Target Version**: Velo 2.0+ (Production Systems & Game Engine Viability)  
> **Archive**: All completed historical gap audits (§1.1 through §6.9) are preserved in [docs/gaps_archive.md](file:///c:/projects/easylang/docs/gaps_archive.md).  
> **Workflow Rule**: An AI agent or engineer MUST only implement **one single Phase and one single Task at a time**. After completing each task, verify with tests, rebuild the bootstrap chain (`bin/velo.exe`), and update this document.

---

## 1. Completed Foundation Milestones (Summary Audit)

All 26 foundational milestones from the initial language roadmap (§1 through §6) are **100% completed, tested, and self-hosted**:

| Section | Milestone Area | Core Capabilities Delivered | Status |
| :--- | :--- | :--- | :---: |
| **§1.1 – §1.4** | **Syntax & Lexer** | Binary/unary bitwise ops (`&`, `\|`, `^`, `~`, `<<`, `>>`), block/doc comments, numeric literals (`0x`, `0b`, `0o`, `_`), character/string escapes (`\uXXXX`, `` `raw` ``) | **COMPLETED** ✅ |
| **§2.1 – §2.3** | **Control Flow** | `break` and `continue` in loops, pattern matching `on` statements, safe range loops | **COMPLETED** ✅ |
| **§3.1 – §3.5** | **Type System** | `kind` enums/tagged unions, generic functions/structs, function pointers/callbacks, UFCS method calls, operator overloading (`+`, `-`, `*`, `/`, `[]`) | **COMPLETED** ✅ |
| **§3.6** | **Advanced Structs** | Default field initializers, struct alignment & packing (`#align`, `#packed`), type aliases (`aka`) | **COMPLETED** ✅ |
| **§4.1 – §4.3** | **Memory Subsystem** | Extensible `@Allocator` interface, multithreaded thread-locals (`thread.spawn`/`join`), memory intrinsics (`mem.copy`, `mem.set`) | **COMPLETED** ✅ |
| **§5.1 – §5.5** | **Standard Library** | `sys.str` string library, Dynamic collections (`shelf`, `map`, `ring`, `bitset`, `dyn`), `sys.math`, `sys.fs`/`sys.os`, `sys.time` | **COMPLETED** ✅ |
| **§6.1 – §6.2** | **Toolchain** | Linker flags (`-l<lib>`, `-L<dir>`), build modes (`--debug`, `--release`, `-O0`..`-O3`) | **COMPLETED** ✅ |
| **§6.3 – §6.5** | **Developer Tooling** | Visual snippet error diagnostics, LSP Language Server 3.17 (`velo lsp`), native integrated test runner (`test` / `assert`) | **COMPLETED** ✅ |
| **§6.6 – §6.8** | **Compiler Internals** | Dynamic lexer token sizing, `velo check [--json]` CLI, contextual keywords (`data`, `kind`, `op`) | **COMPLETED** ✅ |
| **§6.9** | **Portability** | MSVC C99 portability of emitted C (zero GCC statement expressions, `VELO_TLS`, `VELO_ALIGNED`) | **COMPLETED** ✅ |

*(Full historical audit logs, defect explanations, and verification proofs for §1.1–§6.9 are preserved in [docs/gaps_archive.md](file:///c:/projects/easylang/docs/gaps_archive.md)).*

---

## 2. Active Phased Engineering Roadmap (Unsolved Gaps)

Each phase is divided into self-contained, atomic tasks. **Do not combine tasks. Complete Task N.1 before proceeding to Task N.2.**

```mermaid
flowchart TD
    P1["Phase 1: Toolchain CLI & Codegen Hardening\n(--cc cl driver flag, string interpolation calls, ternary side-effects)"] --> P2["Phase 2: Language Ergonomics & Tooling Polish\n(Contextual keywords, struct dot-autocomplete in LSP)"]
    P2 --> P3["Phase 3: Hardware SIMD Math Library (sys.simd)\n(f32x4/i32x4 types, vector arithmetic, dot/min/max)"]
    P3 --> P4["Phase 4: Compile-Time Struct Reflection\n(Field metadata builtins, compile-time unrolled iteration)"]
    P4 --> P5["Phase 5: Package Manifest & Dependency Manager (velo pkg)\n(velo.toml format, multi-module packaging, dependency cache)"]
    P5 --> P6["Phase 6: Multi-Arena Memory Management & Scaling\n(Custom arena creation, heap-spilling fallback)"]
    style P1 fill:#e53935,stroke:#b71c1c,color:#ffffff
    style P2 fill:#fb8c00,stroke:#e65100,color:#ffffff
    style P3 fill:#1e88e5,stroke:#0d47a1,color:#ffffff
    style P4 fill:#43a047,stroke:#1b5e20,color:#ffffff
    style P5 fill:#8e24aa,stroke:#4a148c,color:#ffffff
    style P6 fill:#00acc1,stroke:#006064,color:#ffffff
```

---

### Phase 1: Toolchain CLI & Codegen Hardening

#### Task 1.1: MSVC CLI Driver Backend Flag (`--cc cl`) [COMPLETED] ✅
* **Former Defect**: In §6.9, emitted C was made 100% portable C99 for MSVC (`cl.exe`). However, the Velo CLI driver (`velo build`, `velo run`, `velo test`) hardcoded calling `gcc.exe`. To compile with MSVC, users had to run `velo emit-c` and manually invoke `cl.exe`.
* **Fix Applied**:
  - Implemented `--cc <gcc|cl>` option across Stage 1 (`velo.py`, `velo/driver.py`) and Stage 2 (`src/main.vl`, `src/backend/driver.vl`, `src/backend/driver_cc.vl`).
  - Added MSVC `cl.exe` command assembly and flag translation:
    * Passed `/nologo`, `/TC`, `/W3`, `/wd4090`, `/wd4996`, `/D_CRT_SECURE_NO_WARNINGS`.
    * Output executable translation `/Fe:<path>`.
    * Optimization flags `/O2` (default / release), `/Od /Zi` and `/DEBUG` (debug), `/O1` (`-O1`).
    * Linker flags: `/link`, `/LIBPATH:<dir>` for `-L`, `<lib>.lib` for `-l`.
    * Automatic discovery of Visual Studio `vcvars64.bat` if `cl` is not on ambient PATH.
  - Extracted compilation and execution command assembly into `src/backend/driver_cc.vl` (153 lines), reducing `src/backend/driver.vl` from 392 to 356 lines, comfortably respecting the 400-line file limit.
  - Fixed `@shelf[T]` dynamic unbox order in `src/backend/shelf_gen.vl` so unboxing a pointer cast `as @shelf[...]` emits `velo_dyn_unbox_ptr` matching Stage 1.
  - When `--cc` is omitted, default remains `gcc` with 100% backward compatibility.
* **Residual Limitation**: Compiling with MSVC requires MSVC C++ Build Tools or Visual Studio installed on Windows (standard MSVC requirement); automatic detection scans standard VS 2022 / VS 2019 install paths or ambient PATH.
* **Verification**:
  - Verified `python velo.py build examples/31_shelf_basics.vl --cc cl` and `run --cc cl` build and execute correctly.
  - Verified `bin/velo.exe build examples/31_shelf_basics.vl --cc cl` and `run --cc cl` build and execute correctly.
  - Verified `bin/velo.exe test examples/15_native_tests.vl --cc cl` executes and passes all 105 tests.
  - Added dedicated test suite `tests/test_cc_backend.py` covering Stage 1 & Stage 2 build, run, default fallback, and invalid backend rejection (all 6 tests passing).
  - 3-stage bootstrap chain completed (`Gen1 -> Gen2 -> Gen3 -> bin/velo.exe`) with bit-for-bit SHA-256 determinism verified (`DCECDA55AE81D1160EAD359435443B2DF5609F4E68455D8AA5222F4B34998C13`).
  - All source files in `src/` verified $\le 399$ lines (`scripts/count_lines.py`).
  - Full test suite passing (280 tests passed).

#### Task 1.2: Native String Interpolation Function Calls [COMPLETED] ✅
* **Former Defect**:
  - In Stage 1 (`velo/codegen_c.py`), string interpolation used regex `r'\{([a-zA-Z0-9_\.@\[\]]+)\}'`, which skipped any expression containing parentheses `(` or operators `+`, emitting `{fib(5)}` verbatim without interpolation.
  - In Stage 2 (`src/backend/codegen_io.vl`), `resolve_path_type_and_c` only handled simple variable identifiers and struct field paths. Calling functions inside `{...}` (e.g. `fib(5)`) defaulted to `i32` `%lld`, UFCS method calls (e.g. `p.get_name()`) were emitted as invalid C member accesses `p.get_name()` failing C compilation, and string-returning functions were formatted with `%lld` printing pointer addresses.
* **Fix Applied**:
  - In Stage 1 (`velo/codegen_c.py`), replaced the restrictive regex in `_lower_io_call` with a brace-depth scanner to extract balanced `{...}` regions, tokenized and parsed the inner expression with `Lexer` and `Parser`, resolved its type via `_resolve_expr_type`, emitted C code, and mapped to the proper format specifier (`%lld`, `%.2f`, `%s`, `%s`) with required casts.
  - In Stage 2 (`src/backend/codegen_io.vl`), added `parse_interp_expr(source: string) -> @ExprNode` leveraging `lexer.vl`, `parser.vl`, and `parser_expr.vl`. Interpolation regions are parsed into complete AST `@ExprNode` trees, typed with `infer_expr_type(st, parsed_expr)`, and emitted via `emit_c_expr(@c_sb, st, parsed_expr)`, enabling arbitrary expressions, function calls, UFCS method calls, and operators inside interpolation.
  - Maintained safe fallback to `resolve_path_type_and_c` if parsing fails.
  - Line count of `src/backend/codegen_io.vl` maintained at 319 lines (under the 400-line ceiling).
* **Residual Limitation**:
  - Expressions inside string interpolation containing unescaped quote characters are bounded by standard Velo string literal lexical rules. Variables, function arguments, UFCS methods, operators, and constants are fully supported.
* **Verification**:
  - Added dedicated test suite `tests/test_string_interpolation.py` validating function calls, UFCS method calls, arithmetic expressions, and types (`i32`, `f64`, `bool`, `string`) across Stage 1 and Stage 2.
  - 3-stage bootstrap chain completed (`Gen1 -> Gen2 -> Gen3 -> bin/velo.exe`) with bit-for-bit SHA-256 determinism verified (`ADC60D9D80B32607B6B0D6FB669F7EBECE3051E8A3C0384705DFEA6F06678BC3`).
  - All source files $\le 399$ lines (`scripts/count_lines.py`).
  - No UTF-8 BOM in any `.vl` file.
  - Full test suite passing (281 tests passed).

#### Task 1.3: Single-Evaluation Null Comparisons for Function Calls [COMPLETED] ✅
* **Former Defect**:
  - In Stage 2 (`src/backend/codegen_expr.vl`), checking a string-returning function call against `null` (e.g. `call_count() != null`) matched `if ltype == "string" or rtype == "string"` without checking for `null` literals (`EXPR_NULL` / `@void`). This lowered the check into a redundant null-guarded ternary: `((call_count() != NULL && NULL != NULL) ? (strcmp(call_count(), NULL) != 0) : (call_count() != NULL))`. As a result, `call_count()` was evaluated in both the ternary test and the else branch, executing its side effects twice.
  - In string equality comparisons (`call_count() == "hello"`), both Stage 1 and Stage 2 evaluated the function call twice across the condition and branches of the ternary.
* **Fix Applied**:
  - In `src/backend/codegen_expr.vl`, updated equality / inequality emission:
    * Gated the string comparison block with `expr.left.kind != EXPR_NULL and expr.right.kind != EXPR_NULL and ltype != "@void" and rtype != "@void" and (ltype == "string" and rtype == "string")`. When comparing against `null`, it falls through to direct C pointer comparisons `(expr != NULL)` / `(expr == NULL)`, evaluating `expr` exactly once.
    * For string comparisons where either operand is an `EXPR_CALL`, lowered the comparison to `velo_str_eq(left, right)` or `velo_str_neq(left, right)`, evaluating arguments exactly once.
    * Re-condensed the emission logic in `codegen_expr.vl`, reducing line count from 395 to 384 lines.
  - In `velo/codegen_c.py` (Stage 1), added `velo_str_eq` / `velo_str_neq` emission when comparing strings where either operand is a `CallExpr`.
  - In `velo/runtime/velo_runtime.h`, added C99 portable static inline helper functions `velo_str_eq` and `velo_str_neq`.
* **Residual Limitation**:
  - None. Both null comparisons (`!= null`, `== null`) and string comparisons with function calls evaluate arguments exactly once on both stages.
* **Verification**:
  - Added dedicated test suite `tests/test_null_comparisons.py` verifying single evaluation for `get_str() != null`, `null != get_str()`, `get_null_str() == null`, `get_node() == null`, `get_str() == "gamma"`, and `get_str() != "epsilon"` across Stage 1 and Stage 2.
  - 3-stage bootstrap chain completed (`Gen1 -> Gen2 -> Gen3 -> bin/velo.exe`) with bit-for-bit SHA-256 determinism verified (`3B0CE93693C8DA26BA366546F2976F80DC5A4B1899B22541A7901C68E1E93FD6`).
  - Native test suite `bin/velo.exe test examples/15_native_tests.vl` passed all 105 tests.
  - All source files $\le 399$ lines (`scripts/count_lines.py`).
  - No UTF-8 BOM in any `.vl` file.
  - Full test suite passing (282 tests passed).

---

### Phase 2: Language Ergonomics & Tooling Polish

#### Task 2.1: Contextual Re-acceptance of Remaining Reserved Keywords
* **Problem**: Currently, only `data`, `kind`, and `op` are treated contextually as identifiers (§6.8). Using keywords like `use`, `act`, `loop`, `zone`, `defer`, `return`, `break`, `continue`, `on`, `extern`, `aka` as struct field names (e.g. `event.action`, `node.return`, `token.kind`) or function arguments is rejected at parse time.
* **Specification**:
  - Modify `velo/parser.py` and `src/frontend/parser.vl` so that when parsing struct field definitions, field accesses (`x.<field>`), and variable declarations, identifiers can match any keyword that does not introduce syntactic ambiguity in that position.
* **Target Files**:
  - `velo/parser.py`
  - `src/frontend/parser.vl`
  - `src/frontend/parser_decl.vl`
* **Verification**:
  - New test `tests/test_contextual_keywords.py` exercising structs with field names `return`, `loop`, `use`, `defer`.
  - Both compilers pass with identical C emission.

#### Task 2.2: Struct Field Dot-Autocomplete in LSP (`velo lsp`)
* **Problem**: The LSP server (`velo/analysis.py` / `_server/velo_analysis.py`) provides autocompletion on module prefixes (`sys.`, `io.`), but does not provide completion items when typing `.` after a custom struct variable (`player.<caret>`).
* **Specification**:
  - In `VeloAnalysis.completion`, resolve the AST type of the expression preceding the `.` cursor.
  - When the type resolves to a `data` struct or `@Struct` pointer, query the symbol table for its declared fields and return them as `CompletionItemKind.Field` completions.
* **Target Files**:
  - `velo/analysis.py`
  - `editors/vscode/syntaxes/_server/velo_analysis.py`
* **Verification**:
  - Add LSP unit test in `tests/test_lsp.py` verifying completion on a struct instance returns its field names.

#### Task 2.3: Type Checking Default Struct Field Initializers
* **Problem**: In §3.6, default field values (`data Point { x: f32 = 0.0 }`) are parsed and emitted, but their constant values are not strictly type-checked against the field's declared type during semantic analysis (e.g. `x: f32 = "invalid"` was not caught at semantic time).
* **Specification**:
  - In `velo/codegen_c.py` and `src/analysis/type_checker.vl`, validate that the literal initializer's inferred type is compatible with the field's declared type.
  - Emit compile error `Default value type mismatch for field '<name>': expected <T>, got <U>` if types differ.
* **Target Files**:
  - `velo/codegen_c.py`
  - `src/analysis/type_checker.vl`
* **Verification**:
  - Add negative test ensuring invalid default values are rejected with exact error diagnostics.

---

### Phase 3: Hardware SIMD Math Library (`sys.simd`)

#### Task 3.1: 128-bit SIMD Vector Types (`f32x4`, `i32x4`)
* **Problem**: Modern game engines, physics, and particle simulations require vectorized 128-bit SIMD data types with 16-byte alignment.
* **Specification**:
  - Introduce primitive 128-bit types `f32x4` and `i32x4` into Stage 1 and Stage 2 type systems.
  - Define memory layouts in `velo_runtime.h` using portable alignment:
    * Under GCC/Clang: `typedef float f32x4 __attribute__((vector_size(16), aligned(16)));`
    * Under MSVC: `typedef __m128 f32x4;` (via `<immintrin.h>`).
  - Support vector constructors: `let v = f32x4(1.0, 2.0, 3.0, 4.0)` and splat constructor `f32x4_splat(1.0)`.
* **Target Files**:
  - `velo/runtime/velo_runtime.h`
  - `velo/codegen_c.py`
  - `src/ast/types.vl`
  - `src/backend/codegen_types.vl`
* **Verification**:
  - Compile and verify 16-byte alignment and data preservation across both Stage 1 and Stage 2.

#### Task 3.2: SIMD Vector Arithmetic & Lane Operations
* **Problem**: Performing vectorized math currently requires scalar loops or compiler autovectorization.
* **Specification**:
  - Enable binary arithmetic operators `+`, `-`, `*`, `/` directly between `f32x4` operands, lowering to hardware SIMD instructions:
    * GCC/Clang: native vector arithmetic operators.
    * MSVC: `_mm_add_ps`, `_mm_sub_ps`, `_mm_mul_ps`, `_mm_div_ps`.
  - Add lane accessor properties/methods: `v.x`, `v.y`, `v.z`, `v.w` (or lane indexing `v[0]`).
* **Target Files**:
  - `velo/codegen_c.py`
  - `src/backend/codegen_expr.vl`
* **Verification**:
  - Unit tests verifying vector addition, subtraction, multiplication, and division produce bit-exact float results.

#### Task 3.3: High-Performance SIMD Operations (`sys.simd`)
* **Problem**: Game math requires specialized vectorized primitives: dot products, minimums, maximums, and fast square roots.
* **Specification**:
  - Create standard library module `use sys.simd`:
    * `simd.dot(a: f32x4, b: f32x4) -> f32`
    * `simd.min(a: f32x4, b: f32x4) -> f32x4`
    * `simd.max(a: f32x4, b: f32x4) -> f32x4`
    * `simd.sqrt(a: f32x4) -> f32x4`
* **Target Files**:
  - `velo/runtime/velo_runtime.h`
  - `src/analysis/type_checker.vl`
  - `src/backend/driver.vl`
* **Verification**:
  - Write `examples/36_simd_math.vl` benchmarking vector transformations against scalar baseline.

---

### Phase 4: Compile-Time Struct Reflection & Introspection

#### Task 4.1: Compile-Time Field Metadata Builtins
* **Problem**: Game engines and entity-component systems (ECS) need to inspect struct fields at compile time for serialization, network replication, and debug inspectors without manual boilerplate.
* **Specification**:
  - Implement built-in compile-time query intrinsics:
    * `field_count(T)`: returns integer constant of the number of fields in struct `T`.
    * `field_name(T, index)`: returns string literal of the field name at `index`.
    * `field_type(T, index)`: returns string literal of the field type name at `index`.
* **Target Files**:
  - `velo/codegen_c.py`
  - `src/analysis/type_checker.vl`
  - `src/backend/codegen_expr.vl`
* **Verification**:
  - Compile and verify a generic struct inspector printing field names and counts.

#### Task 4.2: Compile-Time Field Iteration & Serialization
* **Problem**: Writing JSON/binary serializers currently requires manually writing every field for every struct.
* **Specification**:
  - Provide a mechanism to iterate fields of a struct at compile time:
    ```velo
    act serialize_struct[T](item: @T) {
        loop i in 0..field_count(T) {
            io.println(field_name(T, i))
        }
    }
    ```
  - Unroll the loop at compile time during monomorphization.
* **Target Files**:
  - `velo/monomorphize.py`
  - `src/analysis/monomorphize_expr.vl`
* **Verification**:
  - Automated JSON serializer example serializing nested custom structs.

---

### Phase 5: Package Manifest & Dependency Manager (`velo pkg`)

#### Task 5.1: Package Manifest Specification (`velo.toml`)
* **Problem**: Velo projects currently lack a standardized project configuration file; build flags, entrypoints, and library dependencies must be passed as CLI arguments.
* **Specification**:
  - Define `velo.toml` format:
    ```toml
    [package]
    name = "my_game"
    version = "0.1.0"
    entry = "src/main.vl"

    [dependencies]
    raylib = { git = "https://github.com/velo-lang/raylib-velo", tag = "v1.0" }

    [link]
    libraries = ["raylib", "gdi32", "winmm"]
    ```
  - Add native TOML parser into `velo/` and `src/common/`.
* **Target Files**:
  - `velo/manifest.py`
  - `src/common/manifest.vl`
* **Verification**:
  - Test manifest parsing and validation.

#### Task 5.2: Project Build Command (`velo pkg build`)
* **Problem**: Building a project with dependencies requires manually passing `-l` and `-L` flags.
* **Specification**:
  - Implement `velo pkg build` and `velo pkg run` which automatically reads `velo.toml`, applies link flags, compiles `entry`, and produces the target binary.
* **Target Files**:
  - `velo.py`
  - `src/main.vl`
* **Verification**:
  - Build a sample project using `velo pkg build`.

---

### Phase 6: Multi-Arena Memory Management & Scaling

#### Task 6.1: Parameterized Scoped Arenas
* **Problem**: Velo currently uses a global thread-local 64 MB arena for zone allocations. Large allocations (such as 4K textures or large audio files) can exhaust this buffer.
* **Specification**:
  - Add explicit arena instantiation:
    ```velo
    let custom_arena = mem.create_arena(256 * 1024 * 1024)
    defer mem.destroy_arena(custom_arena)
    zone custom_arena {
        let buf = mem.alloc(1024 * 1024)
    }
    ```
* **Target Files**:
  - `velo/runtime/velo_runtime.h`
  - `src/backend/codegen_stmt.vl`
* **Verification**:
  - Allocate and reclaim 256 MB in a custom arena without altering the global zone pool.

#### Task 6.2: Dynamic Arena Chunk Spilling
* **Problem**: When a zone allocation exceeds capacity, the compiler terminates with a loud `Zone Arena Out of Memory` fatal error.
* **Specification**:
  - Add chunked growth fallback: when an arena's primary block fills up, allocate a linked secondary chunk from the system heap (`malloc`), linking chunks in a linked list.
  - At zone exit, free all secondary linked chunks while resetting the primary block offset to 0.
* **Target Files**:
  - `velo/runtime/velo_runtime.h`
* **Verification**:
  - Test allocating 10,000 chunks that exceed 64 MB without crashing or leaking memory.

---

### Systems Application Case Study: VeloKV In-Memory Database (`apps/velokv/`) [COMPLETED] ✅
* **Architectural Findings & Systems Learnings**:
  - **Scoped Request Arenas vs. Permanent Storage (`zone <size>` vs. `@Allocator`)**:
    In bare `zone { ... }` blocks (without size), the runtime pushes the watermark of the active thread-local arena (`g_velo_zone_tls_default`). If database entries are stored while inside a request handler, their backing memory is wiped when `zone` pops. Using `zone 65536 { ... }` forces allocation into a separate private pool-backed arena (`velo_zone_enter`), cleanly isolating transient parsing/wire buffers from persistent state stored via `mem.alloc_with(s.allocator, ...)`.
  - **String Interpolation Lowering**:
    String interpolation syntax `"{expr}"` is strictly lowerable within `sys.io` print calls (`io.println`, `io.print`). Outside of `io`, strings are compiled as raw C string literals. Systems services requiring dynamic RESP/HTTP protocol frame construction must use `str.concat` and numeric-to-ASCII serializers (`int_to_str`) or dynamic string builders.
  - **Low-Latency Socket Event Loop**:
    Non-blocking socket polling with unconditional `time.sleep_ms(1)` yields a maximum throughput of ~65 ops/sec on Windows due to the default 15.6ms OS timer interrupt slice. Introducing adaptive yielding (spinning 500 loop iterations before yielding time-slice) elevated sequential throughput to **17,400+ ops/sec** with sub-millisecond latency.
  - **Persistence Durability**:
    Streaming file persistence (`sys.fs` streaming `fwrite`) buffers in C CRT user-space memory; adding explicit `fflush` ensures crash recovery integrity against sudden process termination.
* **Verification**:
  - `python -m pytest tests/test_velokv.py -v`: 9/9 tests passed (PING, GET/SET/DEL/EXISTS, INCR/DECR, MSET/DBSIZE, passive TTL expiration, inline telnet, INFO telemetry, 1,000-op benchmark at 17,400+ ops/sec, and AOF crash recovery).
  - Full test suite: 291/291 passed.
