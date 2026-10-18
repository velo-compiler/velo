# Velo Stage 2: Production Code & Quality Standards

To ensure the self-hosted Velo compiler is **clean, robust, maintainable, and enterprise-grade**, all Stage 2 code must strictly follow these engineering standards.

---

## 1. Modular File Organization & Sizing

1. **No Monolithic Files**:
   - No single source file shall exceed **400 lines of code**.
   - If a file approaches 400 lines, it must be subdivided into logical sub-modules (e.g. splitting `parser.vl` into `parser_stmt.vl` and `parser_expr.vl`).
2. **Single Responsibility Principle**:
   - Each file has exactly one clear role (e.g., `token.vl` only defines tokens; `string_builder.vl` only handles dynamic string buffers).
3. **Module Imports**:
   - Always group imports at the top of the file:
     ```rust
     // 1. System imports
     use sys.io
     use sys.fs
     use sys.mem

     // 2. Local module imports
     use "common/diagnostics.vl"
     use "frontend/token.vl"
     ```

---

## 2. Naming Conventions

| Entity | Convention | Example |
| :--- | :--- | :--- |
| **Structs / Data Types** | `PascalCase` | `data LexerState { ... }`, `data BinaryExpr { ... }` |
| **Functions (`act`)** | `snake_case` | `act parse_expression(p: @Parser) -> @Expr` |
| **Variables & Parameters** | `snake_case` | `let source_len = 100`, `mut current_token: Token` |
| **Constants / Enums** | `UPPER_SNAKE_CASE` | `let TOK_IDENTIFIER: i32 = 1`, `let MAX_SCOPE_DEPTH = 64` |
| **Pointer Variables** | Standard name with pointer type | `p: @Parser`, `node: @ASTNode` |

---

## 3. Commenting & Documentation Standards

Every public function (`act`) and data structure (`data`) must have a descriptive doc-comment explaining:
1. **Purpose**: What this component does.
2. **Parameters & Return value**: What inputs it requires and what it produces.
3. **Memory Ownership**: Whether allocations occur in `zone` (arena) or on the persistent heap.

### Example Function Doc-Comment:
```rust
// Tokenizes a source string into an array of token descriptors.
// 
// Parameters:
//   source: Null-terminated source buffer.
//   length: Total character count of source buffer.
// 
// Memory Ownership:
//   Allocates tokens inside the active `zone` arena. Caller does not
//   need to manually free individual tokens.
act tokenize(source: string, length: usize) -> @TokenList {
    // ...
}
```

### Example Struct Doc-Comment:
```rust
// Represents a binary operator expression (e.g. `a + b`, `x == y`).
// Left and right operands are pointers allocated within the AST arena.
data BinaryExpr {
    op: i32
    left: @Expr
    right: @Expr
    line: i32
    col: i32
}
```

---

## 4. Memory Discipline & Safety Invariants

1. **Arena Priority**:
   - All ephemeral compiler data (tokens, AST nodes, scopes) **MUST** be allocated in `zone` using `mem.alloc(@Type, count)`.
   - Never use manual heap allocation for temporary nodes.
2. **Mandatory `defer` on Persistent Heap**:
   - Whenever persistent memory is allocated using `mem.heap_alloc`, a matching `defer mem.free(...)` **MUST** appear on the next line or immediately after null validation:
     ```rust
     let buffer = mem.heap_alloc(@u8, size)
     if buffer == null {
         return false
     }
     defer mem.free(buffer)
     ```
3. **Heap Leak Accounting**:
   - Test suites must assert `mem.heap_used() == 0` at the completion of compilation runs.

---

## 5. Error Handling & Diagnostics

1. **No Silent Failures**:
   - Functions that can fail must return a status or nullable pointer, with clear error messages.
2. **Source Code Diagnostics**:
   - Compiler errors must report file path, line number, column number, and context:
     ```text
     [Velo Error] src/main.vl:42:15: Expected ';' or newline after variable declaration.
     ```

---

## 6. Testing & CI Verification Standards

1. **Unit Test Coverage**:
   - Each compiler sub-module must have an automated test suite verifying its specific functionality (`test_lexer.py`, `test_parser.py`, etc.).
2. **End-to-End Regression Test**:
   - Every existing example in `examples/` (`01_hello.vl` through `09_self_hosting_readiness/main.vl`) must continue to compile and run with 100% parity.
3. **Determinism Verification**:
   - Compiling the same Velo program twice must produce byte-for-byte identical output.
