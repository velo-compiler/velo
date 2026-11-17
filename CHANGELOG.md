# Changelog

All notable changes to the Velo language toolchain are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The authoritative version string is the repository-root [`VERSION`](VERSION)
file; `velo version` prints it. A release is a tag whose name is `v` plus that
exact string.

Phase numbers in the entries below refer to the audit registry in
[`gaps.md`](gaps.md), which carries the defect analysis, the fix rationale, and
the residual limitations for each change.

## [Unreleased]

Pre-publication hardening, tracked as Phases 70-85 in [`gaps.md`](gaps.md).
Nothing in this section is released yet.

### Known limitations of the current release

These are documented, reproducible gaps that block a public real-world release.
They are listed here rather than buried, because a consumer of `2.0.0-pre`
should know exactly what does not work:

- **The standard library is Windows-only.** `std.fs`, `std.net`, `std.crypto`,
  and `std.os` bind Win32 APIs (`GetFileAttributesExA`, `WSAStartup`,
  `SystemFunction036`, `CreateProcessA`, ...) with no platform guard, and
  `bootstrap.c` has no `_WIN32` conditions. Linux and macOS cannot link a
  program that imports them (Phase 70).
- **`velo pkg install` does not fetch dependencies.** It writes and verifies a
  lockfile but performs no network or VCS operation, and prints a success
  message regardless (Phase 72).
- **No TLS.** `std.http.client` is cleartext HTTP/1.1 only (Phase 73).
- **Signed integer overflow is C undefined behaviour**, divide-by-zero has no
  diagnostic, and a runtime index into `[N]T` is unchecked (Phase 74).
- **No DNS resolution, no sorting, no regular expressions, no time zones**
  (Phase 78).

## [2.0.0-pre] - 2026-11-17

First tagged preview of the self-hosted toolchain. `bootstrap.c` bootstraps the
compiler with a C99 compiler and no other dependency; Gen2 and Gen3 of the
compiler are byte-identical (SHA-256 fixed point), and `bootstrap.c` is
byte-identical to `velo emit-c src/main.vl -o`.

### Added

- **Language:** first-class tuples and multiple return values
  (`-> (A, B)`, `49b2010`).
- **Language:** fixed-size stack arrays `[N]T` with compile-time bounds checks
  on literal indices (`51fe178`).
- **Language:** native string concatenation with `+` and `+=` (`5ee0469`).
- **Language:** string pattern matching in `on` statements (`1b351bd`).
- **Language:** first-class `if`-`else` conditional expressions (`93071f2`).
- **Language:** flow-sensitive type narrowing for optional types so a
  null-checked `?T` is usable without unwrapping (`06644d7`).
- **Language:** compile-time null safety and optional types `?T` (`a9470bc`).
- **Language:** `unsafe { ... }` blocks plus `--strict-safety`, which requires
  an unsafe block for raw pointer operations and `extern` calls (`586da28`).
- **Language:** explicit casts required for truncating and signed/unsigned
  conversions (`4726c50`).
- **Language:** unsuffixed integer literals now use a documented widening type
  ladder with checked conversions, replacing truncating parsers for decimal,
  hex, octal, and binary literals (`5eab8eb`, `90ac50c`, `b6d7342`).
- **Standard library:** `std.async`, a portable non-blocking event loop with
  TCP support (`dddf4e1`).
- **Standard library:** `std.http`, including an asynchronous non-blocking
  client and server with a zero-allocation fast path and buffer pooling
  (`26ff0b0`, `5b0c17b`).
- **Tooling:** `velo fmt`, a standalone AST/token-based canonical formatter
  (`e15fdf0`).
- **Tooling:** `velo lsp`, a Language Server Protocol 3.17 server providing
  completion, go-to-definition, hover, rename, symbols, and code actions.
- **Tooling:** `velo doc`, Markdown API extraction from `///` comments.
- **Tooling:** `velo pkg` manifest parsing and `velo.lock` checksum
  verification (`17c2132`).
- **CI:** multi-platform matrix (Linux gcc/clang, macOS, Windows gcc/MSVC), a
  sanitizer lane, and a clean-checkout gate (`17a595d`, `4388b33`).
- **Docs:** `SECURITY.md` with disclosure policy and SLAs (`17c2132`).

### Changed

- **io:** `io.*` is now a closed namespace with an explicit member allowlist;
  unknown members are compile errors rather than silently routed to the
  standard library (`0be1409`, `bf978a3`, `e47cac0`, `c8dec8d`).
- **loops:** `loop` classification is decided by expression type rather than
  literal syntax, so a count loop and a condition loop are unambiguous
  (`1856708`, `2a60989`).
- **loops:** integer range endpoints now widen instead of truncating, and
  inclusive `..=` ranges terminate on distance rather than overflow
  (`e187039`, `2b61d70`, `d922937`, `fa7a5f4`).
- **loops:** dynamic range direction is selected at runtime with hoisted,
  single-evaluation endpoint temporaries (`48857d6`, `aadf6c1`, `a80589b`).
- **defer:** cleanup is block-scoped with explicit LIFO unwinding across nested
  scopes, loops, `if`, and `on` arms (`cf5c53f`, `9365d3f`, `f4dd76c`,
  `07f1a78`).
- **fmt:** integer formatting is split signed/unsigned, with portable `usize`
  and `isize` handling across 32-bit and 64-bit boundaries (`65f4217`,
  `5fb8ea6`).
- **cli:** compiler and linker paths are quoted against spaces and argument
  injection on both GCC and MSVC drivers (`eb3de36`).

### Fixed

- `defer return`, `defer break`, `defer continue`, and `defer fail` crashed both
  `velo check` and `velo emit-c` with a stack overflow and no diagnostic. Such
  deferred transfers are now rejected with a diagnostic, because a deferred
  transfer has no defined target at cleanup time (`417e55d`).
- `break` and `continue` outside a loop are rejected by the checker instead of
  crashing code generation (`a890c44`, `2ed7dbc`).
- `break` inside an `on` arm now lowers to an explicit loop-targeted `goto`
  instead of breaking the wrong construct (`3af7f33`).
- A zero or non-positive range step is rejected at compile time when constant
  and fails fast with a runtime guard when dynamic, instead of emitting
  `i += 0` and looping forever (`60e75ff`, `c25b294`, `d56c53e`).
- `loop <count>` evaluates its count expression exactly once into a temporary
  (`2ef5d83`).
- Function and method calls are now type-checked at every call path — free
  functions, methods, UFCS, and externs — for both arity and argument types
  (`ae579c6`, `8cc8443`, `da1b4c4`).
- `if`, `loop`, and `on` conditions must be boolean; the checker enforces it
  without weakening flow-sensitive narrowing (`12707d5`, `8b2f8da`,
  `9a7e85e`).
- String interpolation formats unsigned integers with `%llu` and an unsigned
  cast, and `INT32_MIN` formats correctly (`65f4217`, `a344719`).
- `mem.*` and `str.*` are closed intrinsic namespaces; an unknown member is a
  compile-time error instead of a code-generation failure (`002d566`,
  `19de8db`, `2325ae2`).
- The zone allocator no longer underflows on a corrupted watermark, never
  stores a watermark as a byte offset, and validates the arena struct before
  dereferencing it. Out-of-memory is a loud, deterministic fail-stop
  documented in `SECURITY.md` (`766d1ae`, `e398492`, `453abf5`, `49d43ef`).
- `scripts/check_determinism.py` emits ASCII only, so it no longer crashes on a
  cp1252 console, and its tests assert the reported hashes rather than a
  `MATCH` label (`b4f39cb`, `be0f549`, `47b6ed8`).
- Eight standard-library tests depended on an ambient `scratch/` directory and
  now create and remove their own fixtures, verified by a clean-checkout CI job
  (`2f7c17e`, `a68dd98`, `7341c47`, `4388b33`).

### Security

- Closed-set validation for the `io.*`, `mem.*`, and `str.*` intrinsic surfaces
  removes a class of silent standard-library bypass.
- Integer literal parsing produces checked 64-bit values; the previous
  truncating parsers silently accepted out-of-range literals.
- Range loops no longer depend on signed overflow, which was undefined
  behaviour.
- Zero-step ranges can no longer hang a program; the guard is a deterministic
  fatal.
- Raw pointer operations and `extern` calls can be required to appear inside
  `unsafe` blocks via `--strict-safety`.
- Compiler and linker invocations are quoted, closing an argument-injection
  path through filenames.
- The zone arena's allocation paths are executed under AddressSanitizer and
  UndefinedBehaviorSanitizer in CI.

[Unreleased]: CHANGELOG.md
[2.0.0-pre]: CHANGELOG.md
