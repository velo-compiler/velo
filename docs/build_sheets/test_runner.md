# Build Sheet: 6.5 Native Integrated Test Runner

## Summary
Implements first-class native testing support across both the Stage 1 Python (`velo/`) and Stage 2 self-hosted (`src/`) compilers:
- **Language Primitives**:
  - `test "name" { <body> }` top-level declarations.
  - Contextual keyword handling so `let test = ...` remains valid.
  - `assert(condition)` and `assert(condition, "message")` builtins.
- **Zero-Crash Test Execution**:
  - In test runs, assertion failures record file, line, condition expression (`#cond`), and failure message into thread-local `VeloTestContext`, then perform `longjmp` back to the test harness loop, enabling all subsequent tests to continue running.
  - In normal execution (or outside test mode), assertion failures print `[Velo Fatal] Assertion failed at file:line: assert(cond): msg` and exit with code 1.
- **Memory Isolation**:
  - Active arena watermark reset via `velo_mem_reset()` between consecutive tests ensures memory allocations in one test do not leak or exhaust the arena for subsequent tests.
  - Bumped default `VELO_ZONE_BUFFER_SIZE` to 64 MB to provide sufficient headroom for large multi-module compilation trees.
- **Production Build Stripping**:
  - In standard `velo build` and `velo run` modes, `test` blocks are completely omitted from generated C code.
  - User `main()` functions execute normally without test overhead. In test mode, user `main()` is renamed to `_velo_user_main()` to avoid symbol collisions with the harness.
- **Command-Line Interface**:
  - `velo test [file_or_dir] [--filter <pattern>]` on both Stage 1 (`python velo.py test`) and Stage 2 (`bin/velo.exe test`).
  - Standard reporting: `running N tests`, `test "..." ... ok`, `test "..." ... FAILED`, and summary line `test result: ok/FAILED. N passed; N failed`.
- **Tooling Parity**:
  - `velo/analysis.py` updated with document symbols for `test` declarations, hover tooltips for `assert`, and autocompletions.

## Files Modified & Added
- `velo/runtime/velo_runtime.h`: Added `VeloTestContext`, `g_velo_current_test`, `velo_mem_init`, `velo_mem_reset`, `velo_assert_fail`, `velo_assert` macro; bumped `VELO_ZONE_BUFFER_SIZE` to 64 MB.
- `velo/tokens.py`: Added `TokenType.TEST` and keyword `"test"`.
- `velo/ast_nodes.py`: Added `TestDecl`.
- `velo/parser.py`: Added `_parse_test_decl()` and contextual identifier acceptance for `TokenType.TEST`.
- `velo/monomorphize.py`: Preserved `TestDecl` during monomorphization Pass 2.
- `velo/codegen_c.py`: Handled `TestDecl`, `assert` expressions, user `main` renaming, and test harness code emission.
- `velo/driver.py`: Added `is_test` support to `compile_to_c` and `build`, and added `test` runner method.
- `velo.py`: Added `test` CLI parser subcommand and dispatcher.
- `velo/analysis.py`: Added document symbols for `TestDecl`, hover for `assert`, and `assert` completion.
- `src/frontend/token.vl`: Added `TOK_TEST: i32 = 153`.
- `src/frontend/lexer.vl`: Tokenized `"test"` keyword.
- `src/ast/stmt.vl`: Added `DECL_TEST: i32 = 307` and `make_test_decl`.
- `src/frontend/parser.vl`: Contextual identifier check and `parse_top_level_declaration` dispatch for `test`.
- `src/frontend/parser_decl.vl`: Added `parse_test_decl`.
- `src/analysis/symbol_table.vl`: Added `is_test: bool` and `source_file: string` fields.
- `src/analysis/type_checker.vl`: Supported `assert` identifier type and call checking.
- `src/analysis/type_check_program.vl`: Validated `DECL_TEST` bodies.
- `src/analysis/monomorphize.vl`: Cloned `DECL_TEST` in Pass 2.
- `src/backend/test_gen.vl`: Created test declarations counter, forward prototype emitter, test function body emitter, and test harness `main()` generator.
- `src/backend/codegen_expr.vl`: Emitted `velo_assert` calls.
- `src/backend/codegen_c.vl`: Integrated `test_gen.vl` prototypes, bodies, user `main` renaming, and harness generator.
- `src/backend/driver.vl`: Added `compile_source_to_c_test`, `test_source_file`, and `test_target`.
- `src/main.vl`: Added `test` CLI usage and command dispatcher.
- `examples/15_native_tests.vl`: Example demonstration file.
- `tests/test_native_tests.py`: Unit test suite.
- `gaps.md`: Marked §6.5 as `[COMPLETED] ✅`.

## Verification Results
1. **Pytest Suite**:
   `python -m pytest tests -q` -> **274 passed in 186.21s** (0 failures).
2. **Bootstrap Chain**:
   - `python velo.py build src/main.vl -o bin/velo_gen1.exe` -> Success.
   - `bin/velo_gen1.exe build src/main.vl -o bin/velo_gen2.exe` -> Success.
   - `bin/velo_gen2.exe build src/main.vl -o bin/velo_gen3.exe` -> Success.
   - `Copy-Item bin/velo_gen3.exe bin/velo.exe -Force` -> Success.
3. **Determinism (SHA-256 Fixed Point)**:
   - Gen2 SHA-256: `0e83dc130262d1483068de2fa3ccb81e383a6d78e0d2321124792a041c987c34`
   - Gen3 SHA-256: `0e83dc130262d1483068de2fa3ccb81e383a6d78e0d2321124792a041c987c34`
   - Result: Bit-for-bit identical!
4. **Line Count Ceiling**:
   - `python scripts/count_lines.py` -> All 57 files in `src/` strictly $\le 399$ lines.
