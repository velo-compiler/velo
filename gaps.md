# The Complete Velo Language Gap Analysis (Small to Big) 📋

> **Document Status**: Living Architectural Audit  
> **Target Version**: Velo 2.0+ (Towards Production Systems & Game Engine Viability)  
> **Scope**: An exhaustive, brutally honest breakdown of every single gap, limitation, and missing feature in the Velo programming language—from minor syntax nuances to major compiler subsystems.

---

## Executive Summary & Gap Severity Matrix

Velo is a working, self-hosted, triple-bootstrapped systems programming language that compiles to native machine code via C99. While its core foundation (zone memory, pointers, structs, basic control flow, and multi-file modules) is verified and leak-free, it currently lacks several language features, standard libraries, and compiler controls required to build full-scale desktop applications and modern game engines.

| Severity Level | Focus Area | Impact |
| :--- | :--- | :--- |
| 🔴 **P0: Critical Blockers** | Bitwise ops, `break`/`continue`, custom linker flags (`-l`), slices/dynamic arrays | Blocks building game engines, binary protocols, and real loops |
| 🟠 **P1: Major Language Gaps** | `enum`/tagged unions, `switch`/`match`, math library, multi-arena allocators | Forces cumbersome boilerplate, unsafe type tricks, and prevents DOD/ECS |
| 🟡 **P2: Ergonomic Gaps** | Operator overloading, method syntax, default values, raw strings, block comments | Slows down iteration speed, friction when writing math/vector code |
| 🟢 **P3: Ecosystem & Tooling** | Debug symbols (`-g`), LSP/IDE tooling, package manager, native test runner | Affects developer comfort, discovery, and large-scale collaboration |

---

## 1. Syntax, Lexer & Tokenizer Gaps

### 1.1 Bitwise Operators [COMPLETED] ✅
* **Supported Operators**: Binary `&`, `|`, `^`, `<<`, `>>`, unary `~`, and compound assignments `&=`, `|=`, `^=`, `<<=`, `>>=`.
* **Verified**: Full operator precedence hierarchy in Stage 1 and Stage 2 self-hosted compilers. Verified with `examples/14_bitwise_operators.vl` and `tests/test_bitwise_operators.py`.

### 1.2 Comments & Documentation [COMPLETED] ✅
* **Nested Block Comments**: Arbitrary-depth multi-line comments (`/* ... /* ... */ ... */`) implemented in both Stage 1 and Stage 2 self-hosted lexers with unclosed comment diagnostics.
* **Structured Documentation**: Single-line `///` and block `/** ... */` doc comment recognition for top-level structs, functions, and externs.
* **Native Doc Generator CLI**: Built-in CLI command `velo doc <source.vl> [-o output.md]` extracting clean GitHub-flavored Markdown API reference documentation tables and signatures directly from AST definitions. Verified with `examples/15_docs_and_comments.vl` and `tests/test_docs_and_comments.py`.

### 1.3 Literal Formatting [COMPLETED] ✅
* **Numeric Bases**: Hexadecimal (`0x` / `0X`), binary (`0b` / `0B`), and octal (`0o` / `0O`) literals with full type preservation and C99 emission.
* **Digit Separators**: Underscore digit separators supported in all integer, hex, binary, octal, and floating point literals (e.g. `1_000_000`, `0xFF_AA_BB_CC`, `0b1010_1010`).
* **Scientific Notation**: Full exponent support (`1e-4`, `2.5e6`, `1E3`, `3.14e+2`) in both Stage 1 and Stage 2 self-hosted compilers.
* **Explicit Literal Suffixes**: Explicit integer (`u8`, `u16`, `u32`, `u64`, `usize`, `i8`, `i16`, `i32`, `i64`, `isize`) and float (`f32`, `f64`) suffixes with automatic type inference and C99 suffix mapping (`LL`, `ULL`, `U`, `f`). Verified with `examples/16_literal_formatting.vl` and `tests/test_literal_formatting.py`.

### 1.4 String & Character Escapes [COMPLETED] ✅
* **Raw / Multi-line Strings**: Supported via backticks (`` `...` ``). Preserves literal backslashes, quotes, and newlines across multiple lines without escape decoding. Automatically normalized and formatted into standard C99 string literals.
* **Unicode Escapes (`\uXXXX`)**: Full 4-digit hexadecimal Unicode escape support in standard string and character literals, encoded automatically into compliant UTF-8 multi-byte sequences (`0x00A9` -> `0xC2 0xA9`, `0x2764` -> `0xE2 0x9D 0xA4`).
* **Character Literals & Escapes**: Character literals support standard escapes (`\n`, `\t`, `\r`, `\0`, `\\`, `\'`, `\"`), 2-digit hex escapes (`\xNN`), and 4-digit Unicode escapes (`\uXXXX`), correctly evaluating to their numeric integer values. Verified with `examples/17_string_escapes.vl` and `tests/test_string_escapes.py`.

---

## 2. Control Flow & Language Statements

### 2.1 Loop Controls: `break` and `continue` [COMPLETED] ✅
* **Supported Controls**: Native `break` and `continue` statements in both `while` loops and `loop <var> in <start>..<end>` range loops.
* **Semantics & Code Generation**: Direct mapping to C99 `break;` and `continue;` control flow with correct nested loop scoping and Go-style statement termination. Verified with `examples/18_break_continue.vl` and `tests/test_break_continue.py`.

### 2.2 Branching: `on` Statement [COMPLETED] ✅
* **Signature `on` Keyword**: Velo exclusively standardizes on the punchy, unique 2-letter **`on <expr> { ... }`** keyword tailored for game engines and state dispatching (`match` and `switch` completely eliminated from the language).
* **Multi-Value Patterns**: Matching comma-separated alternative values in a single branch (e.g. `201, 202 => { ... }`).
* **Default & Wildcard Fallbacks**: Clean fallback handling supporting `else => { ... }` and wildcard `_ => { ... }`.
* **Block and Single-Statement Arms**: Supports curly-brace scoped code blocks `{ ... }` as well as concise single-statement arm bodies (e.g. `1 => action = "jump"`).
* **High-Performance C99 Jump Tables**: Emits native scoped C99 `switch (...) { case ...: { ... break; } default: { ... break; } }` blocks enabling $O(1)$ constant-time jump table optimizations by C compilers without accidental fallthrough. Verified with `examples/19_match_switch.vl` and `tests/test_match_switch.py`.

### 2.3 Range Loop Flexibility [COMPLETED] 🛡️
* **Unified Loop Syntax**: Consolidated all loops (`while`, `loop .. in`, `repeat`, `infinite`) into a single expressive `loop` keyword.
* **Custom Step Increments**: Slicing syntax `loop i in 0..10:2` for forward custom steps.
* **Smart Auto-Countdown**: When $start > end$ (`loop 5..0`), loops automatically decrement by `-1` without needing `:-1`. Custom decrement steps like `loop 10..0:2` also supported.
* **Inclusive & Exclusive Ranges**: Supports both half-open ranges `0..10` and fully inclusive ranges `0..=10` via `..=` operator.
* **Implicit Variable**: Anonymous ranges (`loop 0..10:2`), repeat loops (`loop 5`), condition loops (`loop cond`), and infinite loops (`loop`) automatically provide the `it` iteration counter starting at 0.
* **Retirement of `while`**: Retired `while` keyword across the entire language, compiler, test suite, and examples. Verified with `examples/20_range_loops.vl` and `tests/test_range_loops.py`.

---

## 3. Type System & Data Modeling

### 3.1 First-Class Enums & Tagged Unions (`kind`) [COMPLETED] ✅
* **Unified 4-Letter Keyword**: Velo standardizes on `kind` (harmonizing with `data`, `act`, `zone`, `loop`).
* **Pure Scalar Enums**: Unit variants (`North`, `East`) and explicit discriminants (`Ok = 200`, `NotFound = 404`) with zero runtime overhead, lowering directly to C99 `int32_t` scalars.
* **Payload-Bearing Tagged Unions**: Supports single-payload variants (`KeyDown: i32`) and multi-field payloads (`Click(button: i32, x: f32, y: f32)`), lowering to C99 `struct { int32_t kind; union { ... } as; }`.
* **Contextual Dot-Shorthand**: `let d: Direction = .North`, `let e: Event = .KeyDown(65)`, `let c: Event = .Click(1, 10.0, 20.0)` whenever target type is known; fully-qualified `Direction.North` always valid.
* **Pattern Matching Destructuring (`on`)**: Directly match with `on e { .KeyDown(key) => ..., .Click(btn, x, y) => ... }` with automatic payload variable bindings scoped to each arm. Verified with `examples/21_enums_and_unions.vl` and `tests/test_enums_and_unions.py`.

### 3.2 Generics / Parametric Polymorphism [COMPLETED] ✅
* **Syntax Choice**: Proposal A (`[T]`): `data Box[T]`, `kind Option[T]`, `act min[T]`, `act swap[T](a: @T, b: @T)`, multi-param `data Pair[K, V]`.
* **Zero-Cost C99 Monomorphization**: AST specialization pass monomorphizes generic structs, kinds, and functions on demand into concrete C99 types (`Box_i32`, `Option_string`, `min_i32`, `Pair_string_i32`) with zero virtual dispatch or boxing overhead.
* **Call-Site Type Inference**: Functions can be invoked directly as `min(15, 25)` without type arguments, inferring type arguments from parameters; explicit instantiation `min[f32](3.14, 2.71)` also supported.
* **Pointer & Struct Specialization**: Pointer types like `@T` cleanly unify and specialize (e.g. `swap[i32](@x, @y)`).
* **Self-Hosted Monomorphizer**: Fully integrated into both Python (`velo/monomorphize.py`) and self-hosted Stage 2 compiler (`src/analysis/monomorphize.vl`). Verified with `examples/22_generics.vl` and `tests/test_generics.py`.

### 3.3 Function Pointers & First-Class Callbacks [COMPLETED] ✅
* **Native `act(...) -> Ret` Syntax**: First-class function type signature harmonizing with Velo's `act` keyword (e.g. `act(i32, i32) -> i32`, `act(@Button) -> void`, `act() -> void`).
* **Variable Storage & Higher-Order Functions**: Storing named functions in variables (`let op: act(i32, i32) -> i32 = add`), passing callbacks to higher-order functions (`apply_binary(7, 8, op)`).
* **Struct Function Pointer Fields (Callbacks & Vtables)**: Storing function pointers in struct data fields (e.g. `data Button { on_click: act(@Button) -> void }`).
* **Direct Execution & Null Safety**: Calling function pointers directly via variable (`op(10, 20)`) or member access (`btn.on_click(@btn)`). Full null check compatibility (`if btn.on_click != null { btn.on_click(@btn) }`).
* **Inline Anonymous Functions**: Anonymous callbacks with parameter inference and block bodies: `act(b: @Button) { ... }`, `act(x: i32, y: i32) -> i32 { return x - y }`.
* **C99 Function Pointer Typedef Lowering**: Zero-overhead function pointer typedefs (`typedef int32_t (*velo_act_i32_i32_to_i32)(int32_t, int32_t);`), with anonymous functions lifted to `static` C functions with forward prototypes. Verified across Stage 1 Python compiler and Stage 2 self-hosted native compiler with `examples/23_function_pointers.vl` and `tests/test_function_pointers.py`.

### 3.4 Method Syntax / Uniform Function Call Syntax (UFCS) [COMPLETED] ✅
* **Pure UFCS Without OOP Keywords**: Any free function `act foo(self: T, ...)` or `act foo(self: @T, ...)` can be invoked using method call syntax: `x.foo(...)`. No `class`, `struct impl`, or OOP ceremony required.
* **Smart Auto-Referencing & Auto-Dereferencing**:
  - If a function expects a pointer `@T` and the receiver is a value lvalue of type `T`, the compiler automatically passes its address (`&x`).
  - If a function expects a value `T` and the receiver is a pointer `@T`, the compiler automatically dereferences the pointer (`*x`).
  - If the receiver type matches the first parameter type directly, it is passed directly without modification.
* **Struct Field Priority**: Struct fields (such as callback function pointers `btn.on_click(...)`) always take priority over free functions with the same name, preserving callback and vtable mechanics.
* **Method Chaining & Extensibility**: Supports fluent chaining (e.g. `p.translate(1.0, 2.0).scale(2.0)`) and extension methods on both structs and primitive types (e.g. `7.square()`).
* **Generic Method Specialization**: Works seamlessly with generic functions and data types (e.g. `box.unwrap()`), inferring type arguments from the receiver and arguments. Verified across Stage 1 Python compiler and Stage 2 self-hosted native compiler with `examples/24_ufcs_methods.vl` and `tests/test_ufcs_methods.py`.

### 3.5 Operator Overloading for Game Math [COMPLETED] ✅
* **Signature `act op <symbol>` Syntax**: Clean 2-letter `op` prefix aligning with Velo's keyword philosophy (`on`, `in`, `as`, `op`). Supports both `act op +(...)` and `act op+(...)`.
* **Disambiguation by Parameter Count**: Single-parameter declarations define unary operators (e.g. `act op -(v: Vector2)` for negation); two-parameter declarations define binary operators (e.g. `+`, `-`, `*`, `/`, `%`, `==`, `!=`, `<`, `<=`, `>`, `>=`).
* **Zero Runtime Overhead & C99 Name Mangling**: Deterministic C function identifier mangling based on operator name and operand types (`velo_op_add_Vector2_Vector2`, `velo_op_mul_Vector2_f32`, `velo_op_neg_Vector2`).
* **Automatic Compound Assignment**: Statements like `pos += vel` and `pos *= 2.0` automatically desugar into `pos = pos + vel` and `pos = pos * 2.0`, executing overloaded operators without duplicate boilerplate.
* **Smart Auto-Referencing / Auto-Dereferencing**: Functions expecting pointer parameters `@Vector2` automatically receive `&v` when invoked with value lvalues.
* **Bit-for-Bit Triple-Bootstrap Determinism**: Verified with `examples/25_operator_overloading.vl` and `tests/test_operator_overloading.py` across Python reference compiler and Stage 2 self-hosted native compiler.

### 3.6 Advanced Struct Features (🟡 P2 Ergonomic)
* **Default Field Initializers**: [COMPLETED] ✅ — *"Cannot declare `data Point { x: f32 = 0.0, y: f32 = 0.0 }`"* (Former Defect).
  - **Fix Applied**: Constant-literal defaults (int / float / string / bool, optional unary `-`) parsed in both compilers; struct literals fill omitted defaulted fields via C99 designated initializers appended after the provided ones; omitted fields without a default are now a compile error in both compilers (Python Stage 1 codegen validation, Stage 2 self-hosted semantic checker). Defaults are carried into every generic specialization.
  - **Verification**: `examples/26_advanced_structs.vl` + `tests/test_advanced_structs.py` (Stage 1 CLI run/emit-c assertions and native `bin/velo.exe` run).
* **Struct Packing & Alignment**: [COMPLETED] ✅ — *"No `#align(16)` / `#packed` directives"* (Former Defect).
  - **Fix Applied**: `data Name #align(N) #packed { ... }` parsed after name/type parameters in both compilers; emitted as `struct __attribute__((aligned(N), packed)) Name { ... };` on the definition only (forward typedefs untouched). Attributes survive generic instantiation.
  - **Verification**: Emitted C asserted in `tests/test_advanced_structs.py` for both compilers; native run compiles the attributes with GCC.
  - **Residual Limitation**: Attribute support is GCC/Clang-shaped (`__attribute__`); MSVC layouts would need a separate pragma mapping.
* **Type Aliases**: [COMPLETED] ✅ — *"No `type EntityId = u64`"* (Former Defect).
  - **Fix Applied**: `type Name = <primitive|@primitive>` as a contextual keyword at top level only; target validated at parse time (no alias-of-alias). Both monomorphizers gained an always-running Pass 0 that canonicalizes alias names in every type string (fields, kind payloads, params/returns, locals, casts) order-free across the whole merged program, so aliases work even in programs without generics; codegen emits a decorative `typedef`.
  - **Verification**: Same example + test file; triple-bootstrap determinism re-verified (Gen2 vs Gen3 emit-c SHA-256 identical).
  - **Residual Limitation**: Aliases are primitive-only by design; alias declarations are not yet listed by `velo doc`, and `VELO.md` sync is owner material. The missing-field diagnostic wording differs slightly between the two compilers (both reject with the same exit behavior). Default-initializer values are not type-checked against their field type (constant-literal defaults only).

---

## 4. Memory Management & Hardware Access

### 4.1 Extensible Allocator Architecture (🟠 P1 Major)
* **Current State**: Fixed, single global 16MB zone arena (`VELO_ZONE_BUFFER_SIZE`) + a single global malloc heap.
* **Impact**:
  - The 16MB buffer cannot be dynamically resized or configured per game.
  - You cannot instantiate multiple distinct arenas (e.g. `PerFrameArena`, `LevelLoadingArena`, `UIArena`).
  - No `Allocator` interface (like Zig or Odin) where functions receive `allocator: @Allocator`.

### 4.2 Multithreaded Memory Safety (🟠 P1 Major)
* **Current State**: `g_velo_arena` and `g_velo_arena_offset` are global, unsynchronized C static variables.
* **Impact**: If two threads call `mem.alloc(...)` simultaneously, the arena watermark corrupts immediately. There is no Thread-Local Storage (`__thread` / `_Thread_local`) for per-thread zone arenas.

### 4.3 Low-Level Memory Intrinsics (🔴 P0 Critical)
* **Missing Primitives**:
  - `mem.copy(dest: @u8, src: @u8, count: usize)` (C `memcpy`).
  - `mem.set(dest: @u8, val: u8, count: usize)` (C `memset`).
  - `mem.move(...)` (C `memmove`).
  - `mem.realloc(...)` (Resizing persistent heap buffers).
* Currently, copying an array requires a manual Velo `while` loop indexing byte-by-byte.

---

## 5. Standard Library Gaps (`sys.*` and `std.*`)

Velo currently has a bare-minimum runtime (`velo_runtime.h`). To be a viable development language, the following libraries are missing:

### 5.1 String Processing Library (🔴 P0 Critical)
* Strings are currently raw C `const char*` with only `str.len(...)`.
* **Missing String Functions**:
  - `str.contains(s, sub)`
  - `str.starts_with(s, prefix)` / `str.ends_with(s, suffix)`
  - `str.split(s, delimiter)`
  - `str.trim(s)`
  - `str.replace(s, old, new)`
  - `str.to_upper(s)` / `str.to_lower(s)`
  - `str.index_of(s, char)`
  - `str.concat(a, b)`

### 5.2 Dynamic Collections (🔴 P0 Critical)
* No dynamic array (`List[T]` or `Vector[T]`).
* No hash map (`Map[K, V]` or `Dict[K, V]`).
* No ring buffer / circular queue.
* No bitset (critical for ECS component masks).

### 5.3 Math Library (`sys.math`) (🟠 P1 Major)
* There is no math standard library!
* **Missing Functions**:
  - Trigonometry: `sin`, `cos`, `tan`, `atan2`, `acos`, `asin`.
  - Exponential: `sqrt`, `cbrt`, `pow`, `exp`, `log`, `log2`.
  - Utility: `abs`, `min`, `max`, `floor`, `ceil`, `round`, `clamp`, `lerp`.
  - Constants: `PI`, `TAU`, `RAD2DEG`, `DEG2RAD`.

### 5.4 Extended File System & OS Primitives (`sys.fs`, `sys.os`) (🟠 P1 Major)
* **`sys.fs` Missing**:
  - `fs.read_dir(path)` (directory scanning).
  - `fs.create_dir(path)` / `fs.create_dir_all(path)`.
  - `fs.is_dir(path)` vs `fs.is_file(path)`.
  - `fs.copy(src, dst)` / `fs.rename(src, dst)`.
  - File streaming: `fopen`, `fread`, `fwrite`, `fseek` (currently only entire file read/write).
* **`sys.os` Missing**:
  - `os.get_env(key)` / `os.set_env(key, val)`.
  - `os.args()` (CLI argument access outside of `main(argc, argv)`).
  - `os.exit(code)` (immediate exit with status code).

### 5.5 High-Resolution Clock & Timing (`sys.time`) (🟠 P1 Major)
* No high-resolution timer (`time.now()`, `time.delta()`, `time.sleep_ms()`).
* In games, calculating `dt` (delta time) requires high-resolution performance counters (`QueryPerformanceCounter` on Windows, `clock_gettime` on Linux).

---

## 6. Compiler, Tooling & Build System Gaps

### 6.1 Linker Flags for Third-Party C Libraries (🔴 P0 Critical)
* **Current State**: `bin/velo.exe` hardcodes `gcc -O2 <c_file> -o <binary>`.
* **Impact**: You cannot link external libraries such as **Raylib, SDL2, OpenGL, Vulkan, Box2D, or SQLite** without manually running GCC in the terminal.
* **Needed Solution**:
  - `velo build main.vl -o game.exe -lraylib -lopengl32 -lgdi32 -lwinmm`
  - Or `#link "raylib"` / `#link "opengl32"` pragma in source code.

### 6.2 Optimization Flags & Build Modes (🟠 P1 Major)
* **Current State**: Always compiles with `-O2`.
* **Missing Modes**:
  - `velo build --debug` (emits `-O0 -g` with full debug symbols).
  - `velo build --release` (emits `-O3 -flto` with link-time optimization).

### 6.3 Diagnostic Formatting & Error Visuals (🟡 P2 Ergonomic)
* Current errors print: `[Velo Error] semantic:line:col - message`.
* Modern compilers (Clang, Rust, Zig) print colorized source code snippets with arrows pointing to the exact token:
  ```text
  examples/02_math_and_logic.vl:29:14: error: undeclared identifier 'foo'
     29 |     let x = foo + 10;
        |             ^^^
  ```

### 6.4 Developer Tooling: Language Server Protocol (LSP) (🟢 P3 Ecosystem)
* No VS Code syntax highlighter extension.
* No LSP server providing autocomplete, jump-to-definition, hover documentation, or red squiggly error diagnostics in the editor.

### 6.5 Native Integrated Test Runner (🟢 P3 Ecosystem)
* Currently, tests are driven via Python `pytest` and subprocess invocations.
* Velo lacks an in-language test primitive:
  ```velo
  test "vector addition" {
      let v = Vec2{ x: 1.0, y: 2.0 }
      assert(v.x == 1.0)
  }
  ```
  and a `velo test` CLI subcommand.

### 6.6 Lexer Token Buffer Sizing & Overflow Diagnostics [COMPLETED] ✅
* **Former Defect (Silent Compiler Corruption)**: The self-hosted lexer (`src/frontend/lexer.vl`) used a hardcoded **8,192-token** capacity, and `add_token` **silently discarded** tokens beyond it. Any valid file past the cap (~2,000+ statements; large real-world or generated modules) produced a truncated token stream, derailing the parser into a runaway allocation loop that crashed with a **misleading `Zone Arena Out of Memory` fatal error** — the message blamed memory while the actual cause was lexer truncation. Notably masked because the compiler's own corpus obeys the `<= 400 lines/file` standard and never crossed the cap.
* **Fix Applied**: `src/backend/driver.vl` now sizes the token buffer from the source at both `create_lexer` call sites (compilation and docgen): `create_lexer(source, slen, slen + 2)` — provably sufficient since a token can never consume less than one source character. The lexer records overflow in the new `Lexer.dropped_count` field (explicitly zero-initialized, as arena memory is reused across files), and the driver emits a real diagnostic — `[Velo Error] <file>: lexer token buffer too small; N tokens were truncated. Split this file into smaller modules.` — failing the build/notably the docgen cleanly instead of emitting garbage.
* **Residual Limitation**: Very large single files (~0.5 MB+ of source) still exhaust the fixed 16 MB global arena with a loud (honest) allocation failure; proper resolution belongs to the multi-arena allocator work in §4.1.
* **Verification**: Triple-bootstrap chain rebuilt (Gen1 → Gen2 → Gen3, `bin/velo.exe` updated); SHA-256 fixed point preserved (Gen2 ≡ Gen3 bit-for-bit). New regression suite `tests/test_lexer_capacity.py` covers (1) a 23,921-token file that previously phantom-OOM'd now compiling and executing correctly, and (2) the truncation diagnostic firing with a correct truncated count on a tiny-cap test build. Full suite: **85/85 passing** (was 83).

---

## 7. Game Engine Specific Technical Gaps

| Engine Subsystem | Missing Velo Feature | Workaround Today |
| :--- | :--- | :--- |
| **Windowing & Input** | No C library linking flag in CLI | Manually invoke GCC with `-lraylib` / `-lSDL2` |
| **Math & Physics** | No Operator Overloading (`+`, `*`) | Must write `vec3_add(a, b)` |
| **Physics / Collision** | No Bitwise Operators (`&`, `|`, `^`) | Must use integer arithmetic or avoid bitmasks |
| **Asset Loading** | No streaming file seek (`fseek`) | Must load entire audio/texture files into RAM at once |
| **Frame Allocations** | Single fixed 16MB buffer | Good for small demos, but overflows on 4K meshes |
| **Animation / Events** | No Function Pointers / Callbacks | Must use integer action IDs and `if/else` ladders |
| **Entity Component System (ECS)** | No Generics or Struct Reflection | Must write hardcoded component arrays |
| **SIMD Math** | No 128-bit / 256-bit SIMD intrinsics | Relies purely on GCC autovectorization |

---

## 8. Prioritized Strategic Roadmap to Game Readiness

```mermaid
flowchart TD
    G1["Phase 1: Game Foundations\n(Bitwise ops, break/continue, CLI -l linker flags)"] --> G2["Phase 2: Game Engine Essentials\n(sys.math, sys.time, List[T] dynamic collection)"]
    G2 --> G3["Phase 3: High-Performance Engine\n(Raylib 60 FPS demo, operator overloading, multiple arenas)"]
    G3 --> G4["Phase 4: Advanced Engine Architecture\n(Enums/tagged unions, function pointers, switch/match)"]
    style G1 fill:#e53935,stroke:#b71c1c,color:#ffffff
    style G2 fill:#fb8c00,stroke:#e65100,color:#ffffff
    style G3 fill:#1e88e5,stroke:#0d47a1,color:#ffffff
    style G4 fill:#43a047,stroke:#1b5e20,color:#ffffff
```

### Phase 1: Game Foundations (The "Make a Window" Milestone)
1. **Bitwise Operators**: Implement `&`, `|`, `^`, `~`, `<<`, `>>` in lexer, parser, semantics, and C codegen.
2. **Loop Controls**: Implement `break` and `continue` in `while` and `loop`.
3. **Linker Flag Passing**: Add `-l<lib>` and `-L<dir>` support to `velo build` and `velo run`.
4. **Validation**: Write an `extern` Raylib script that opens a window, captures keyboard input, and draws a rectangle at 60 FPS.

### Phase 2: Engine Essentials (The "Playable Gameplay" Milestone)
1. **`sys.math`**: Implement trigonometry, square root, powers, min/max, clamp, and lerp.
2. **`sys.time`**: Implement microsecond-accurate delta time calculation (`time.now()`).
3. **`mem.copy` / `mem.set`**: Native memory byte-block manipulation.
4. **Dynamic Array**: A standard resizable buffer library for managing game entities.

### Phase 3: Ergonomics & Scaling (The "Clean Code" Milestone)
1. **Operator Overloading**: Enable `+`, `-`, `*` on custom structs for vector and matrix math.
2. **Multiple Zone Arenas**: Parameterized arenas instead of a single global 16MB buffer.
3. **Enums & `switch`**: Clean state machines and event dispatching.
