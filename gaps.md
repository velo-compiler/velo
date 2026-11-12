# The Velo Language Gap Analysis & Phased Engineering Roadmap 📋

> **Document Status**: Active Phased Roadmap & Open Engineering Backlog  
> **Target Version**: Velo 2.0+ (Production Systems & Game Engine Viability)  
> **Source Baseline**: Programming Language Review Report `PLR-VELO-2026-001` (Commit `49b2010`)  
> **Archive**: All completed historical gap audits (§1.1 through §44.1) are preserved in Git history.  
> **Workflow Rule**: An AI agent or engineer MUST only implement **one single Phase and one single Task at a time**. After completing each task, verify with tests (`python -m pytest tests -q`), rebuild the bootstrap chain (`bin/velo.exe`), and update this document.

---

## 1. Summary of Completed Milestones

All foundational milestones and language extensions implemented prior to Review `PLR-VELO-2026-001` are **100% completed, self-hosted, and passing all 636 regression tests**:

| Milestone Range | Scope & Capabilities Delivered | Status |
| :--- | :--- | :---: |
| **Foundational Milestones (§1 – §6)** | Bitwise ops, control flow, `kind` enums/tagged unions, generics, function pointers, UFCS, operator overloading, advanced structs, zone arena, collections (`shelf`, `map`, `ring`, `bitset`, `dyn`), math, fs, time, build modes, visual error diagnostics, LSP 3.17, native test runner, MSVC C99 portability. | **COMPLETED** ✅ |
| **Standard Library Modernization (Phases 1 – 29)** | Pure-Velo `std.*` migration (`io`, `str`, `fmt`, `coll`, `fs`, `json`, `time`, `math`, `os`, `net`, `crypto`, `http`, `log`, `test`, `encoding`, `csv`, `cli`, `url`, `rand`, `uuid`, `text`, `timer`, `validate`). | **COMPLETED** ✅ |
| **Language & Systems Hardening (Phases 30 – 44)** | Codegen error gating, algebraic error handling (`or` / `fail`), lexical zone escape analysis, compile-time null safety (`?T`), non-blocking async event loop (`std.async`), async HTTP client/server, zero-alloc HTTP server fast-path, flow-sensitive type narrowing, first-class `if-else` expressions, string pattern matching in `on`, string `+`/`+=` concatenation, fixed-size stack arrays (`[N]T`), and first-class tuples with multiple return values (`-> (A, B)`). | **COMPLETED** ✅ |

*(Full historical defect analyses, fix implementations, and verification proofs for Phases 1 through 44 are preserved in Git history).*

---

## 2. Active Phased Engineering Roadmap (Gaps from Review `PLR-VELO-2026-001`)

The following roadmap comprises strictly the open gaps and findings identified during the independent engineering review of Velo v2.0-beta.

```mermaid
flowchart TD
    P45["Phase 45 (P0): Specification Synchronization ✅\n(Sync SPECIFICATION.md with Phases 30-44)"] --> P46["Phase 46 (P1): Type System Strictness & Integer Safety ✅\n(Reject truncating int conversions without cast)"]
    P46 --> P47["Phase 47 (P2): Compiler Driver Command Quoting\n(Escape paths against argument injection)"]
    P47 --> P48["Phase 48 (P2): Syntactic Safety Boundaries & Unsafe Blocks\n(unsafe { ... } blocks & --strict-safety)"]
    P48 --> P49["Phase 49 (P2): Multi-Platform Automated CI\n(Linux & macOS GitHub Actions workflows)"]
    P49 --> P50["Phase 50 (P3): Package Provenance & Security Policy\n(velo.lock checksums & SECURITY.md)"]
    P50 --> P51["Phase 51 (P3): Standalone Source Formatter\n(velo fmt CLI subcommand)"]

    style P45 fill:#2e7d32,stroke:#1b5e20,color:#ffffff
    style P46 fill:#2e7d32,stroke:#1b5e20,color:#ffffff
    style P47 fill:#1e88e5,stroke:#0d47a1,color:#ffffff
    style P48 fill:#43a047,stroke:#1b5e20,color:#ffffff
    style P49 fill:#8e24aa,stroke:#4a148c,color:#ffffff
    style P50 fill:#00acc1,stroke:#006064,color:#ffffff
    style P51 fill:#546e7a,stroke:#263238,color:#ffffff
```

---

### Phase 45: Language Specification Synchronization & Contract Hardening (`PLR-VELO-001`) [COMPLETED] ✅

#### Task 45.1: Specification Modernization for Post-Phase 30 Features [COMPLETED] ✅
* **Former Defect**:
  - `docs/SPECIFICATION.md` covered only Stage 1 and early Stage 2 features up to §2.9 and §9.
  - Major language capabilities implemented and verified across Phases 30 through 44 were absent from the formal specification:
    1. Fixed-size stack arrays (`[N]T`, `buf.len`, `buf.ptr`, stack allocation semantics).
    2. First-class tuples and multiple return values (`-> (A, B)`, destructuring `let (a, b) = val`, wildcard `_`, member access `t.0`/`t.1`).
    3. Algebraic outcome types (`T or E`, `fail err`, and `or return` unwrapping).
    4. Compile-time null safety and optional types (`?T`, `opt.val`, `opt.has`, and `null` literal semantics).
    5. Flow-sensitive type narrowing (`if x != null { ... }` narrowing `?T` to `T`).
    6. First-class `if-else` expressions producing values (`let x = if cond { a } else { b }`).
    7. String pattern matching in `on` statements.
    8. Native string concatenation operators (`+` and `+=`).
* **Fix Applied**:
  - Updated `docs/SPECIFICATION.md` to Stage 2 Production Specification standard.
  - Formalized §1.4 (`fail` keyword), §1.6 (precedence table with string concat `+` and append `+=`), and §1.7 (strict left-to-right evaluation order and short-circuit semantics).
  - Authored comprehensive normative sections:
    * **§2.10: Fixed-Size Stack Arrays (`[N]T`)**: syntax, zero-initialization, array literals, constant compile-time bounds checking, immutability, `.len` and `.ptr` properties, array copy assignment via `memcpy`, and C99 compound literal lowering.
    * **§2.11: First-Class Tuples & Multiple Return Values (`-> (A, B)`)**: type annotations, tuple literals, destructuring declarations (`let (a, b) = ...`), wildcard discard `_`, member access (`.0`, `.1`), and zero-overhead mangled struct lowering.
    * **§2.12: Optional Types & Compile-Time Null Safety (`?T`)**: nullable pointer representation, boxed value structs (`_Velo_Opt_T`), `.has` and `.val` properties, and flow-sensitive type narrowing across branches and early returns.
    * **§2.13: Algebraic Outcome Types & Error Handling (`T or E`)**: outcome syntax, `fail` statements, `or return` error propagation, `.ok`, `.val`, `.err` properties, and C union lowering.
    * **§6.2: Native String Concatenation (`+` and `+=`)**: zone/heap dynamic allocation and desugaring.
    * **§7.3.2: String Pattern Matching in `on`**: string comparison lowering and wildcard matching.
    * **§7.4: First-Class Conditional Expressions (`if-else`)**: expression evaluation, branch typing, and automatic widening (`widen_if_branch_types`).
    * **§9: CLI Surface**: updated command reference table to include `test`, `pkg`, and `lsp`.
* **Residual Limitation**:
  - 1-tuples `(T,)` are not part of the grammar (parenthesized single expressions `(expr)` remain grouping expressions). Fixed-size stack arrays cannot be returned directly by value due to C99 return type limitations (pointers `@T` or enclosing structs should be returned).
* **Verification**:
  - Verified every specification code example compiles and runs cleanly with `bin/velo.exe`.
  - Audited `docs/SPECIFICATION.md` against parser AST definitions in `src/ast/` and `src/frontend/`.
  - Ran automated test suites with 100% pass rate.
  - Line standards verified (`scripts/count_lines.py`).

---

### Phase 46: Type System Strictness & Implicit Integer Narrowing Safety (`PLR-VELO-002`) [COMPLETED] ✅

#### Task 46.1: Enforce Explicit Casts for Truncating or Signed/Unsigned Conversions [COMPLETED] ✅
* **Former Defect**:
  - In `src/ast/types.vl` (lines 251–252), `types_are_compatible` previously allowed all integer and float types to implicitly convert to one another:
    ```rust
    if is_int_type(expected) and is_int_type(actual) { return true }
    if is_float_type(expected) and is_float_type(actual) { return true }
    ```
  - Any integer type (e.g. `u64`, `i64`) was treated as structurally compatible with any smaller integer type (e.g. `i8`, `u8`) without requiring an explicit cast (`x as i8`).
  - In systems and embedded code, this permitted silent integer truncation and unintended sign inversion at runtime.
  - Furthermore, `f64` could implicitly convert to narrower float type `f32` without explicit cast.
* **Fix Applied**:
  - Implemented strict integer and float compatibility rules in `src/ast/int_types.vl`:
    * Safe widening within the same signedness (`i8 -> i16 -> i32 -> i64 / isize`, `u8 -> u16 -> u32 -> u64 / usize`) and float widening (`f32 -> f64`) remain implicitly compatible.
    * Narrowing integer conversions (e.g. `u64 -> u8`, `i64 -> i32`, `usize -> u32`), signed/unsigned mismatches (e.g. `i32 -> u32`, `u32 -> i32`), and narrowing float conversions (`f64 -> f32`) are strictly rejected at compile time unless an explicit cast `as <type>` is used.
    * Descriptive error messages emitted:
      `[Velo Error] Cannot implicitly convert '{actual}' to narrower type '{expected}'. Use explicit cast 'as {expected}'.`
      `[Velo Error] Cannot implicitly convert '{actual}' to '{expected}'. Use explicit cast 'as {expected}'.`
      `[Velo Error] Cannot implicitly convert '{actual}' to narrower type '{expected}'. Use explicit cast 'as {expected}'.`
  - Created contextual literal adaptation in `src/analysis/literal_check.vl`:
    * Unsuffixed integer literals and arithmetic/bitwise expressions composed of unsuffixed literals adapt contextually to target integer types (`u8`, `i8`, `u16`, `i16`, `u32`, `i32`, `u64`, `i64`, `usize`, `isize`) if the constant value fits within the target range.
    * Compile-time out-of-range diagnostic emitted if the literal exceeds the target type range:
      `[Velo Error] Integer literal '{lit}' out of range for type '{target}'`.
    * Suffixed literals (`1000_u64`) are checked strictly according to their explicit type.
  - Integrated literal adaptation and strict type checking across:
    * Variable declarations (`STMT_VAR_DECL`).
    * Variable assignments and compound assignments (`STMT_ASSIGN`).
    * Return statements (`STMT_RETURN`).
    * Struct field initializers and default field values (`DECL_DATA`).
    * Function and method call arguments (`adapt_and_check_call_args`).
    * Binary arithmetic/bitwise expressions and fallback operators (`TOK_OR`, `??`).
    * Built-in `sizeof` expression support returning `"usize"`.
  - Audited compiler source and standard library, fixing latent signedness/narrowing bugs and adding explicit casts:
    * `src/frontend/parser_lit.vl`: fixed `parser_previous(p)` replacing invalid negative offset peek.
    * `src/backend/check.vl`: added explicit `usize` casts.
    * `src/analysis/reflect_checks.vl`, `src/backend/reflect_gen.vl`, `src/backend/shelf_gen.vl`, `src/analysis/mono_unroll.vl`, `src/analysis/monomorphize_expr.vl`: added explicit `as i32` casts for `sb_append_int` and `make_int_expr`.
    * `std/test/benchmark.vl`: typed `mut warmup_count: usize = 5`.
    * `std/tests/coll/shelf_test.vl`: typed `let slice_size: usize = 16`.
    * `std/tests/rand/rand_test.vl`: typed `mut f_min: f64 = 20.0`, `mut f_max: f64 = 10.0`.
* **Residual Limitation**:
  - Unchecked truncating conversions are only allowed when an explicit `as <type>` cast is written. Pointer-to-integer conversions continue to require `as usize` or `as isize`.
* **Verification**:
  - Added comprehensive test suite `tests/test_type_checker.py` (23/23 tests passing) covering unsigned/signed widening, narrowing rejection, explicit cast acceptance, signed/unsigned rejection, function arg/return/struct field narrowing, integer literal adaptation and out-of-range diagnostics, suffixed literal enforcement, and float widening/narrowing.
  - Passed full test suite: 659 passed in 555.47s (100% pass rate).
  - Maintained 3-generation self-hosting bootstrap determinism (Gen2 and Gen3 emit identical bit-for-bit C output matching `bootstrap.c` with SHA-256 `c79988a72057e0826814ec8dd630446190e62d70ef6d4630b685b3d776905310`).
  - Maintained line count standards across all 98 compiler source files in `src/` ($\le 394$ lines, ceiling 400).

---

### Phase 47: Compiler Driver Command Quoting & Injection Hardening (`PLR-VELO-003`) [COMPLETED] ✅

#### Task 47.1: Robust Escaped Path Quoting Across GCC and MSVC Compiler Drivers [COMPLETED] ✅
* **Former Defect**:
  - In `src/backend/driver_cc.vl`, compilation, linking, and execution commands assembled command strings without robustly quoting and escaping filesystem paths:
    ```rust
    sb_append_str(@cmd_sb, path_to_native_str(c_file_path))
    sb_append_str(@cmd_sb, " /Fe:")
    sb_append_str(@cmd_sb, path_to_native_str(out_exe_path))
    ```
  - If a workspace, project path, source file path, include directory, or output executable path contained spaces or special characters, GCC or MSVC split the path across arguments, causing compilation/linker errors or argument injection.
* **Fix Applied**:
  - Implemented `quote_path(path: string) -> string` in `src/common/utils.vl` following standard Windows `CommandLineToArgvW` rules: wraps paths in double quotes, escapes embedded quotes, and doubles trailing backslashes so that directory trailing separators (e.g. `C:\path\dir\`) do not escape the closing quote character.
  - In `src/backend/driver_cc.vl`:
    * Quoted source and output executable paths in `assemble_msvc_compile_cmd` (`/Fe:<quote_path>`) and `assemble_gcc_compile_cmd` (`-o <quote_path>`).
    * Quoted include paths in `append_include_flag` (`/I <quote_path>` / `-I <quote_path>`) and `append_runtime_includes` (`/I "runtime" /I "velo/runtime"` / `-I "runtime" -I "velo/runtime"`).
    * Quoted linker search paths (`/LIBPATH:<quote_path>`) in `append_msvc_linker_flags` with quote-aware token splitting (`in_quotes`).
    * Quoted runner command executable path in `assemble_runner_cmd`.
  - In `src/cli_cmd.vl`, `src/backend/driver_pkg.vl`, and `src/main.vl`:
    * Quoted `-L` library directory flags with `quote_path(path_to_native_str(...))`.
* **Residual Limitation**:
  - Single-token arbitrary raw linker flags passed via `-l` or `--link` containing unmatched quotes or custom shell pipeline operators are passed verbatim to the linker without shell interpolation.
* **Verification**:
  - Added regression test suite in `tests/test_cc_backend.py` testing build and run with paths containing spaces (both directories and file names) under both `--cc gcc` and `--cc cl` (10/10 tests passing).
  - Maintained 3-generation self-hosting bootstrap determinism (Gen2 and Gen3 emit identical bit-for-bit C output matching `bootstrap.c` with SHA-256 `0406a4b751c3e33b78ddbbc10ff35a033612f53f3fcd29deb097f92d64f31fd4`).
  - Ran full test suite: 663 passed in 552.48s (100% pass rate).
  - Line standards verified (`scripts/count_lines.py`): all compiler source files remain $\le 394$ lines (well below 400-line ceiling).

---

### Phase 48: Syntactic Safety Boundaries & Unsafe Blocks (`PLR-VELO-004`)

#### Task 48.1: `unsafe { ... }` Block Syntax and `--strict-safety` Verification [OPEN] ⏳
* **Defect**:
  - Velo provides compile-time zone escape analysis, but raw pointer dereferencing (`ptr.@`, `ptr.field`) and unchecked pointer arithmetic are syntactically permitted anywhere in user code.
  - Systems developers cannot easily audit where unsafe memory manipulations occur or enforce that high-level application logic remains free of raw pointer hazards.
* **Required Fix**:
  - Add `unsafe` keyword to lexical tokens and parser AST (`STMT_UNSAFE = 216`).
  - Add compiler flag `--strict-safety`:
    - When enabled, performing raw pointer dereferencing (`ptr.@`), pointer arithmetic, or unchecked foreign calls (`extern act`) outside of an `unsafe { ... }` block emits a compile error:
      `[Velo Error] Raw pointer dereference requires an 'unsafe { ... }' block when compiling with --strict-safety.`
    - When `--strict-safety` is omitted, `unsafe { ... }` blocks parse and execute normally with full backward compatibility.
  - In emitted C, `unsafe { ... }` lowers to an ordinary scoped C block `{ ... }`.
* **Acceptance & Verification**:
  - Add test suite `tests/test_strict_safety.py` verifying that raw pointer operations are permitted inside `unsafe { ... }` and rejected outside when `--strict-safety` is active.
  - Verify self-hosted compiler rebuilds cleanly with deterministic SHA-256 fixed point.

---

### Phase 49: Multi-Platform Automated Continuous Integration (`PLR-VELO-005`)

#### Task 49.1: Linux & macOS Automated Test and Bootstrap Matrix [OPEN] ⏳
* **Defect**:
  - `runtime/velo_runtime.h` implements POSIX threading (`pthread`), monotonic clock, and filesystem compatibility shims, but automated testing is conducted almost exclusively on Windows (`x86_64-pc-windows-msvc` and MinGW/UCRT64).
  - Cross-platform regressions on Linux (x86_64 / aarch64) and macOS (Apple Silicon) can go undetected until manual user testing.
* **Required Fix**:
  - Add `.github/workflows/ci.yml` multi-platform test matrix:
    - **Windows:** Windows Server 2022 with MSYS2 UCRT64 GCC and MSVC `cl.exe`.
    - **Linux:** Ubuntu 22.04 LTS / 24.04 LTS with GCC and Clang.
    - **macOS:** macOS 14 / 15 (Apple Silicon) with Apple Clang.
  - Provide a canonical POSIX bootstrap script `scripts/bootstrap.sh` that mirrors `scripts/bootstrap.bat`:
    - Compiles `bootstrap.c` using ambient `gcc` or `clang` with `-std=c99 -O2 -I runtime`.
    - Runs 3-stage self-hosting bootstrap (`bin/velo build src/main.vl -> Gen2 -> Gen3`).
    - Verifies SHA-256 determinism across generations.
  - Wire `python -m pytest tests -q` into CI across all platforms.
* **Acceptance & Verification**:
  - Verify `scripts/bootstrap.sh` executes cleanly on Linux/macOS environments.
  - All CI workflow jobs pass with zero failures.

---

### Phase 50: Package Supply Chain Integrity & Vulnerability Disclosure (`PLR-VELO-006`)

#### Task 50.1: Package Checksum Verification (`velo.lock`) and `SECURITY.md` Policy [OPEN] ⏳
* **Defect**:
  - The package manager (`velo pkg`) parses `velo.pkg` manifests, but lacks cryptographic checksum verification for fetched package sources, leaving users vulnerable to altered or tampered dependencies.
  - The repository lacks a formal `SECURITY.md` file establishing a vulnerability disclosure channel, supported version tiers, and incident response SLAs.
* **Required Fix**:
  1. **Lockfile & Hash Verification:**
     - Extend `src/common/manifest.vl` and `src/backend/driver_pkg.vl` to generate and verify `velo.lock`.
     - Store SHA-256 hashes for all resolved dependencies:
       ```
       package "raylib" = { source = "...", version = "5.0", hash = "sha256:..." }
       ```
     - During `velo pkg install` / `velo pkg update`, calculate SHA-256 of downloaded archives using `std.crypto` and reject mismatched digests.
  2. **Security Policy (`SECURITY.md`):**
     - Author `SECURITY.md` in repository root declaring:
       - Supported language and compiler release versions.
       - Vulnerability reporting procedures (private email contact).
       - Triage timeline (acknowledgement within 48 hours, patch targets).
       - Responsible disclosure policy.
* **Acceptance & Verification**:
  - Create test suite `tests/test_pkg_security.py` verifying that modified package contents fail checksum verification during install.
  - Verify `SECURITY.md` is present and valid markdown.

---

### Phase 51: Standalone Canonical Source Formatter (`velo fmt`) (`PLR-VELO-007`) [COMPLETED] ✅

#### Task 51.1: AST/Token-Based Standalone Code Formatter Subcommand [COMPLETED] ✅
* **Former Defect**:
  - Velo provided `velo check`, `velo doc`, `velo test`, and an LSP server, but lacked an automated, deterministic CLI formatter (`velo fmt <file>`).
  - Formatting inconsistencies in multi-developer projects had to be resolved manually without a canonical standard tool.
* **Fix Applied**:
  - Implemented standalone token-based code formatter across `src/tooling/formatter_token.vl`, `src/tooling/formatter_rules.vl`, and `src/tooling/formatter.vl`:
    * Scans all tokens and comments, preserving doc comments (`///`), line comments (`//`), and block comments (`/* ... */`).
    * Standardizes indentation to 4 spaces per block level (`{ ... }`), adjusting indent if a line starts with closing delimiters (`}`, `)`, `]`).
    * Normalizes spacing around binary operators (`+`, `-`, `*`, `/`, `%`, `==`, `!=`, `<`, `<=`, `>`, `>=`, `=`, `+=`, `-=`, etc.), type annotations (`: T`), function signatures, tuples, and control blocks (`if`, `loop`, `on`, `case`).
    * Correctly handles unary prefix operators (`@`, `?`, `!`, `-`), member access (`.`), and range expressions (`..`, `..=`).
    * Preserves single-line guard blocks (`if cond { return 0 }`) while canonicalizing internal spacing.
    * Collapses multiple consecutive empty lines to at most 1 blank line and trims trailing whitespace on all lines.
    * Dispatched `velo fmt [path] [--check]` in `src/main.vl`: formats files or directories in place, or checks formatting compliance with a line-level diff preview, returning exit code 0 when formatted and exit code 1 when unformatted (for CI).
* **Residual Limitation**:
  - Complex custom multi-line expressions broken across arbitrarily many lines are preserved per original newline boundaries while normalizing tokens on each line rather than reflowing expressions to a fixed line width column (e.g. 80/100 chars).
* **Verification**:
  - Added comprehensive test suite `tests/test_formatter.py` (7/7 passed) covering `--check` failure on unformatted files, in-place formatting, strict idempotency `format(format(x)) == format(x)`, comment preservation, recursive directory formatting, and compiler semantic preservation.
  - Rebuilt 3-generation self-hosting bootstrap chain with verified bit-for-bit SHA-256 determinism (Gen2 emit-c == Gen3 emit-c == bootstrap.c: `7ac2bd1bbfe77da751d1cc0b4fdd21f26fce7d4a8b087caf0ccba61cecb188b8`).
  - All 101 compiler source files $\le 394$ lines (under 400-line ceiling, zero UTF-8 BOM).
  - Full test suite passed: 670 passed in 561.09s (100% pass rate).
