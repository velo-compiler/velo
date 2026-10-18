# Velo Stage 2 Roadmap: Self-Hosting Native Compiler

> **Target Goal**: Transition Velo from a Python-hosted transpiler into a **standalone, self-hosted native compiler (`velo.exe`) written 100% in Velo itself**.

---

## Stage 2 Milestones Overview

```mermaid
flowchart TD
    M1["Milestone 2.1: Infrastructure & Native Lexer\n(src/common/, src/frontend/token.vl, lexer.vl)"] --> M2["Milestone 2.2: AST Layouts & Native Parser\n(src/ast/, src/frontend/parser.vl)"]
    M2 --> M3["Milestone 2.3: Symbol Table & Type Checker\n(src/analysis/symbol_table.vl, type_checker.vl)"]
    M3 --> M4["Milestone 2.4: Native C99 Code Generator\n(src/backend/codegen_c.vl, string_builder.vl)"]
    M4 --> M5["Milestone 2.5: Native CLI Driver & Binary Compilation\n(src/backend/driver.vl, src/main.vl -> velo.exe)"]
    M5 --> M6["Milestone 2.6: The Triple-Bootstrap Verification\n(Gen1 -> Gen2 -> Gen3 Determinism Verification)"]
    style M1 fill:#2196f3,stroke:#1565c0,color:#ffffff
    style M2 fill:#2196f3,stroke:#1565c0,color:#ffffff
    style M3 fill:#2196f3,stroke:#1565c0,color:#ffffff
    style M4 fill:#2196f3,stroke:#1565c0,color:#ffffff
    style M5 fill:#2196f3,stroke:#1565c0,color:#ffffff
    style M6 fill:#4caf50,stroke:#2e7d32,color:#ffffff
```

---

## Detailed Milestone Specifications

### Milestone 2.1: Infrastructure & Native Lexer in Velo
* **Goal**: Implement high-performance token scanning and common utilities in pure Velo.
* **Deliverables**:
  * `src/common/diagnostics.vl`: Source line/col error formatting.
  * `src/common/utils.vl`: ASCII character classifications (`is_alpha`, `is_digit`, `is_ident`).
  * `src/frontend/token.vl`: Token definitions (`Token` struct, token kind constants).
  * `src/frontend/lexer.vl`: Tokenizer supporting string literals, character literals, keywords, numbers, and Go-style newline insertion.
* **Verification**:
  - Compile with Stage 1 compiler (`python velo.py`).
  - Unit test `tests/test_stage2_lexer.py` tokenizing complex Velo code snippets and asserting exact token streams.

---

### Milestone 2.2: AST Layouts & Native Parser in Velo
* **Goal**: Implement the complete Abstract Syntax Tree and recursive descent parser in pure Velo.
* **Deliverables**:
  * `src/ast/types.vl`: Type descriptors (`i32`, `f32`, `usize`, `@T`, user structs).
  * `src/ast/expr.vl`: Expression nodes (Literals, Binary, Unary, Calls, Index, Struct Literals).
  * `src/ast/stmt.vl`: Statement nodes (`VarDecl`, `Assign`, `If`, `While`, `Loop`, `Zone`, `Defer`, `Return`).
  * `src/frontend/parser.vl`: Pratt precedence parser for expressions; recursive descent for statements.
* **Verification**:
  - Unit test `tests/test_stage2_parser.py` parsing function definitions, loops, and zone blocks into valid AST node graphs.

---

### Milestone 2.3: Symbol Table & Semantic Analysis in Velo
* **Goal**: Scope resolution, variable tracking, and type verification.
* **Deliverables**:
  * `src/analysis/symbol_table.vl`: Lexical scope stack, struct registry, function signatures.
  * `src/analysis/type_checker.vl`: Expression type inference, auto-dereference rules (`p.x` -> `p->x`), and type compatibility checks.
* **Verification**:
  - Unit test `tests/test_stage2_semantics.py` detecting type mismatches, undeclared variables, and verifying struct member resolution.

---

### Milestone 2.4: Native C99 Code Generator in Velo
* **Goal**: Translate Velo AST directly into standard, formatted C99 source code.
* **Deliverables**:
  * `src/common/string_builder.vl`: Fast heap-backed dynamic string buffer.
  * `src/backend/codegen_c.vl`: Emits struct declarations, prototypes, functions, control flow, defer unrolling (LIFO), and intrinsics (`mem.alloc`, `sys.fs`).
* **Verification**:
  - Unit test `tests/test_stage2_codegen.py` generating C code for all sample programs and confirming clean compilation via GCC.

---

### Milestone 2.5: Native CLI Driver & Binary Compilation (`velo.exe`)
* **Goal**: Build the full CLI executable that compiles `.vl` files into native `.exe` binaries.
* **Deliverables**:
  * `src/backend/driver.vl`: Handles `.velo_cache` directory, writes generated C files, and invokes GCC with proper include paths.
  * `src/main.vl`: Command-line dispatcher supporting `run`, `build`, and `emit-c`.
* **Verification**:
  - Build `velo.exe` using Stage 1 Python compiler.
  - Run `velo.exe run examples/01_hello.vl` and `velo.exe run examples/05_particles.vl` natively.

---

### Milestone 2.6: The Triple-Bootstrap Verification 🏆
* **Goal**: Prove 100% self-hosting through circular bootstrapping.
* **The 3 Generations**:
  1. **Generation 1**: Python Stage 1 compiles `src/main.vl` -> `bin/velo_gen1.exe`.
  2. **Generation 2**: `bin/velo_gen1.exe` compiles `src/main.vl` -> `bin/velo_gen2.exe`.
  3. **Generation 3**: `bin/velo_gen2.exe` compiles `src/main.vl` -> `bin/velo_gen3.exe`.
* **Verification Criteria**:
  - `velo_gen2.c` and `velo_gen3.c` are **100% bit-for-bit identical (matching SHA-256 hash)**!
  - All existing 9 example programs run flawlessly under `velo_gen3.exe`.
  - Formal deprecation of Python compiler! Velo is now fully self-hosted!
