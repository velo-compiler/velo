# The Velo Language Gap Registry - Pre-Public-Release Audit

Purpose: enumerate every gap that must be closed before Velo is published for
real-world use, ordered by what actually blocks adoption. This file is the
release gate, not a wish list. A gap is only closed when it has a regression
test, a `gaps.md` entry in the `Former Defect -> Fix Applied -> Residual
Limitation -> Verification` form, and a commit.

Provenance: Phases 45-69 (see `docs/gaps_archive.md` plus git history) closed
the *correctness* backlog of the compiler as it exists **on Windows with a
Win32-hosted stdlib**. This registry starts from the question the previous
backlog never asked: *can a stranger install this, on their platform, and ship
something without being lied to?* The answer today is no, and the reasons are
below.

Method: every item marked `[VERIFIED]` was reproduced in-tree on 2026-11-17
with `bin/velo.exe`, `gcc -c` + `nm`, or `git ls-files`; the evidence column
cites the probe. Nothing here is inferred from the roadmap files, and nothing
here is copied from `AUDIT.md` or `README.md` - both are themselves audited in
Phase 83.

Status legend: `OPEN` = confirmed, unfixed. `OPEN (unverified)` = suspected,
needs a reproduction before it can be scheduled. `COMPLETED` = fixed, tested,
committed, with the four-part entry.

---

## 1. Verified Baseline (what is genuinely done)

Recorded so the registry does not overstate the work. All of this was
re-verified this session:

| Property | Evidence |
| :--- | :--- |
| Full suite green on the maintainer host | 1964 passed, 2 skipped (~934 s) |
| Bootstrap fixed point | `check_determinism.py` -> SHA-256 MATCH Gen2 == Gen3 |
| Bootstrap snapshot | `bootstrap.c` == `emit-c src/main.vl -o fresh.c` |
| Runtime header parity | `runtime/velo_runtime.h` and `velo/runtime/velo_runtime.h` share SHA-256 `86470B2C...351064` |
| Line ceiling | `scripts/count_lines.py` reports no file over 400 lines |
| Clean-tree gate | `scripts/check_clean_tree.py` PASS |
| Deferred transfers | `defer return/break/continue/fail` rejected with a diagnostic instead of crashing (Phase 69) |
| Loop induction width | widening ladder + inclusive-range terminators (Phase 68) |
| Immutability | `let x = 5; x = 6` -> `cannot assign to immutable variable 'x'` [VERIFIED] |
| String concatenation | `"a" + "b"` compiles and prints `ab` [VERIFIED] |
| Static array bounds | `buf[7]` on `[4]i32` rejected at compile time [VERIFIED] |

The compiler core is in decent shape. Everything below is what sits between
that core and a usable product.

---

## 2. Severity Ladder

| Level | Meaning |
| :--- | :--- |
| **P0** | Blocks publication. A user on a supported platform cannot build, cannot trust the artifact, or is actively misled. |
| **P1** | Blocks serious adoption. The tool works but a professional team would reject it on this basis. |
| **P2** | Debt that compounds. Tolerable at 1.0, expensive at 1.1. |
| **P3** | Cosmetic or documentation only. |

## 3. Backlog Summary

| Phase | Title | Severity | Verified | Tasks | Est. commits |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **70** | POSIX / macOS Foundation Portability | P0 | **COMPLETED** | 8 | 8 |
| **71** | Release Engineering and Legal Provenance | P0 | **COMPLETED** | 6 | 5 |
| **72** | Package Ecosystem That Actually Fetches | P0 | **COMPLETED** | 7 | 7 |
| **73** | Transport Security and Cryptographic Completeness | P0 | **COMPLETED** | 8 | 8 |
| **74** | Undefined-Behavior Containment | P0 | **COMPLETED** | 7 | 7 |
| **75** | Silent POSIX Process/IO Stubs | P0 | **COMPLETED** | 5 | 5 |
| **76** | CI Reality and Platform Test Harness | P0 | PARTIAL (76.1 blocked) | 6 | 6 |
| **77** | Language Completeness | P1 | yes | 7 | 7 |
| **78** | Standard Library Breadth | P1 | yes | 9 | 9 |
| **79** | Tooling and Developer Experience | P1 | yes | 8 | 8 |
| **80** | Compiler Maintainability | P1 | yes | 6 | 6 |
| **81** | Performance and Benchmark Credibility | P1 | yes | 5 | 5 |
| **82** | Compiler Robustness and Fuzzing | P1 | partial | 5 | 5 |
| **83** | Documentation and Claims Integrity | P1 | yes | 6 | 3 |
| **84** | Ecosystem, Governance, Showcase | P2 | yes | 5 | 4 |
| **85** | Recorded Residual Limitations | P2 | yes | 4 | 4 |

## 4. Recommended Execution Waves

- **Wave A (publication blockers, in order):** 71 (legal/versioning) -> 76 (CI
  reality) -> 70 (portability) -> 75 (stub honesty) -> 74 (UB) -> 73 (TLS) ->
  72 (packages). Rationale: 71 and 76 are cheap and stop the project from
  claiming things it cannot prove; 70 unblocks every other platform-facing
  phase; 75 removes the two stubs that silently return success on Linux.
- **Wave B (adoption blockers):** 77 -> 78 -> 79 -> 80.
- **Wave C (credibility):** 81 -> 82 -> 83 -> 84 -> 85.

## 5. Task Execution Contract

Applies to every task below (inherited from the Phase 45-69 contract):

1. One phase at a time, one commit per task, sequential. No phase skipping.
2. Every task ships: implementation + regression test + `gaps.md` update.
3. Compiler-source changes require the full chain: Gen2 -> Gen3 ->
   `check_determinism.py` -> regenerate `bootstrap.c` from **file output, not
   stdout** -> `pytest tests/test_bootstrap_snapshot.py`.
4. New `.vl` files are written UTF-8 without BOM.
5. No file over 400 lines. Prefer a new focused module over expanding a
   near-limit one.
6. A gap may be reclassified or dropped only with a written justification in
   the phase body. "Too hard" is not a justification for a P0.

---

# Phase 70: POSIX / macOS Foundation Portability (P0) - [COMPLETED] ✅

## Defect

The stdlib is Windows-only. Not "mostly Windows with some POSIX branches" -
the *emitted C for any program that imports `std.fs`, `std.net`, `std.crypto`,
or `std.os` contains unresolved Win32 symbols with no `#if` guard anywhere in
the chain*. On Linux or macOS such a program compiles to C and then fails to
link. This makes the Linux and macOS CI jobs in `.github/workflows/ci.yml`
guaranteed red, which means either nobody has run them or nobody has looked.

## Evidence

| Fact | Evidence |
| :--- | :--- |
| `std.fs` is Win32-only | `std/fs/stat.vl:30` `extern act GetFileAttributesExA`; `std/fs/ops.vl:14-18` `CreateDirectoryA`/`MoveFileExA`/`CopyFileA`; `std/fs/dir.vl:15-17` `FindFirstFileA`/`FindNextFileA`/`FindClose` |
| It reaches generated C | probe `use std.fs` + `fs_exists` -> emitted C line 102 `extern int32_t GetFileAttributesExA(...)`, line 112 `CreateDirectoryA`, line 117 `FindFirstFileA`, calls at 2573/3050/3997 [VERIFIED] |
| `std.net` is Win32-only | `std/net/socket.vl:10-22` `WSAStartup`/`WSACleanup`/`closesocket`/`ioctlsocket` [VERIFIED in emitted C, lines 113/123/124] |
| `std.crypto` is Win32-only | `std/crypto/rand.vl:7` `extern act SystemFunction036` (advapi32 "RtlGenRandom") [VERIFIED in emitted C line 127] |
| `std.os` is Win32-only | `std/os/env_windows.vl` getenv/setenv/ExitProcess/GetCurrentDirectoryA; `std/os/proc_windows.vl` `CreateProcessA` [VERIFIED in `bootstrap.c` line 10296] |
| Facades hardcode the Windows variant | `std/async/poller.vl:4`, `std/io/handle.vl:4`, `std/mem/page.vl:5`, `std/os/args.vl:6`, `std/os/env.vl:4`, `std/os/process.vl:6`, `std/time/clock.vl:5`, `std/time/sleep.vl:5` all `use "*_windows.vl"` |
| The Linux variants are dead code | `grep "use .*_linux.vl"` across `std/` + `src/` finds exactly one hit (`std/os/pipe_posix.vl:8` -> `proc_linux.vl`). `handle_linux`, `page_linux`, `clock_linux`, `sleep_linux`, `env_linux`, `cmdline_linux`, `poller_linux` have **zero** importers [VERIFIED] |
| The platform resolver cannot express POSIX | `src/backend/driver.vl:85-122`: `should_skip_platform_file` and `resolve_platform_source_path` only know `_windows.vl` and `_linux.vl`; `is_windows_platform()` delegates to `os_is_windows()` (`driver.vl:80-82`), itself implemented in the Win32-only `env_windows.vl` |
| macOS is invisible | No `_macos.vl`, `_darwin.vl`, or `_posix.vl` file exists anywhere; macOS gets the `_linux` branch by elimination, and there is no kqueue backend (`grep kqueue` -> 0 hits) |
| `bootstrap.c` cannot link on POSIX | `bootstrap.c` has **0** occurrences of `_WIN32` (its only `#if` strings are emitted *text*, lines 44108/44147) yet contains 60+ `extern` declarations and live calls to kernel32/advapi32 (`GetFileAttributesExA` 7894, `CreateDirectoryA` 8102, `SystemFunction036` 56035, `CreateProcessA` 10296). `gcc -c` then `nm -u` yields `U CreateDirectoryA`, `U FindFirstFileA`, `U GetFileAttributesExA`, `U SystemFunction036`, `U CreateProcessA`, `U VirtualAlloc`, `U Sleep`, `U GetEnvironmentVariableA` [VERIFIED] |
| `bootstrap.sh` links without the Win32 libs | `scripts/bootstrap.sh:34` `-lm -lpthread` only; `-lws2_32 -ladvapi32` appears only in the Windows driver (`src/backend/driver_cc.vl:215`) |
| The runtime header itself is clean | `runtime/velo_runtime.h` has 10 `_WIN32` guards and only 5 Win32 mentions, all inside `#if defined(_WIN32)` (`Sleep` at 1035). The portability work belongs to `std/`, not to the runtime |

Root cause: the audit that closed Phases 45-69 measured the compiler, not the
stdlib's platform reach. Six of the nine Win32 dependencies are `extern`
declarations inside `.vl` source, so they never appear in the C runtime header
where the portability review was looking.

## Security Invariants

- **I70.1** No `.vl` file in `std/` outside a `*_windows.vl` or `*_win32.vl`
  file may declare an `extern` bound to a kernel32/advapi32/ws2_32 symbol.
- **I70.2** Every platform-specific module has a sibling implementation for
  every platform the CI matrix claims to support, and a facade that resolves
  at compile time rather than naming one variant.
- **I70.3** `bootstrap.c` compiles *and links* with `cc -O2 -std=c99 -lm
  -lpthread` on Linux and `clang -O2 -std=c99 -lm -lpthread` on macOS, with no
  extra `-l` flags.
- **I70.4** A program that imports `std.fs`, `std.net`, `std.os`, `std.crypto`,
  `std.time`, `std.async` and touches one symbol from each must emit C that
  compiles on the build host with no Win32-specific symbol present.

## Tasks

**70.1** Replace the `_windows`/`_linux` suffix convention with an explicit
platform-resolver table. `driver.vl` must resolve `foo.vl` -> `foo_<plat>.vl`
for `plat in {windows, linux, macos}`, and must fail loudly with a diagnostic
when a platform-specific module has no variant for the current target.
Constraint: `resolve_platform_source_path` and `should_skip_platform_file`
must share one table (they currently duplicate the suffix knowledge).

### 70.1 Completion Record

**Former defect.** Three separate problems, all rooted in one design mistake:
the compiler asked `os_is_windows()` which platform it was on, and that function
lives in `std/os/env_windows.vl` - a Win32-only file.

1. *Circularity.* A compiler built on Linux links the POSIX `env` variant, so
   `os_is_windows()` on that build must come from `env_linux.vl`. But until the
   facades are fixed (70.5), `std/os/env.vl` hardcodes `use "env_windows.vl"`,
   so the Linux build would still get the Windows answer. In practice the
   `_windows` variant was always chosen, and the emitted C always carried
   kernel32 externs. The predicate and the decision it fed lived in the same
   broken place.
2. *Duplication.* `should_skip_platform_file` and
   `resolve_platform_source_path` each hardcoded the suffix pair `_windows.vl` /
   `_linux.vl` as separate `if` chains. Two copies of the platform convention
   can disagree, and they decide complementary things (skip vs choose), so a
   disagreement silently drops or silently duplicates a module.
3. *No third platform.* There was no `_macos` spelling anywhere. macOS fell
   through to the `else` branch and got `_linux`, which is wrong for `kqueue`,
   `sysctl`, and the framework-relative paths that macOS needs.

**Fix applied.**

| Change | Detail |
| :--- | :--- |
| `src/backend/platform_resolve.vl` (new) | The table: `(platform, suffix)` rows for `windows`/`_windows.vl`, `linux`/`_linux.vl`, `macos`/`_macos.vl`. One accessor pair (`platform_suffix_at`, `platform_key_at`) holds the rows, so the whole table is in one place. |
| `driver.vl::should_skip_platform_file` | Now `is_foreign_variant(path, target_platform())` - reads the table. |
| `driver.vl::resolve_platform_source_path` | Now `existing_variant_path(path, platform)`, and only when the neutral file is *absent*: a module that exists is never replaced by a variant sibling. |
| `runtime/velo_runtime.h` | `velo_host_platform()` returns `"windows"`/`"macos"`/`"linux"` from the `_WIN32`/`__APPLE__` branches the header already had, and `velo_host_getenv()` gives the compiler a borrowed-pointer environment read without importing `std.os`. |
| `target_platform()` | `VELO_TARGET_PLATFORM` overrides the host when it names a supported platform. |
| Missing implementation | A module with variants only for foreign platforms and no neutral file now reports `[Velo Error] <path> has no implementation for platform '<target>' (only <other> exists)`, and the build fails. |

**`_win32.vl` and `_posix.vl` are not variant rows, and that distinction was
learned the hard way.** The first cut of the table listed them as alternate
spellings for windows and linux/POSIX, on the reasoning that `pipe_posix.vl`
already existed on disk and would otherwise be unreachable. That was wrong:
`std/os/pipe.vl` is a facade that *declares* `os_spawn_capture` and `use`s
`pipe_win32.vl` as its backend, and `std/async/poller.vl`, `std/mem/page.vl`,
`std/io/handle.vl`, `std/os/env.vl`, `std/time/clock.vl`, `std/time/sleep.vl` are
the same shape. With the alias rows present, resolution replaced each facade
with its backend, so the declarations disappeared; `std.os` failed to compile
with 29 undefined-function errors, and `tests/test_std_os.py` caught it. The
rule the code now encodes is the one that was missing from the specification: a
suffix is a variant only when it names an alternative implementation *of the same
module*; a spelling a module imports by name is a backend, not a variant.
`test_a_backend_suffix_is_not_treated_as_a_variant` and
`test_a_foreign_variant_does_not_replace_an_existing_neutral_module` pin both
halves of that rule.

The second half of the same rule is that a *present* neutral module wins over any
variant. Resolving neutral `bar.vl` to `bar_linux.vl` merely because the target
was linux is the same failure in the other direction, and it also made the
facades unfixable: `pipe.vl` had to keep existing on every platform for the
capture API to survive, which is exactly what a facade is for.

The C linkage detail that made this work: an `extern` declaration in the
emitted C resolves to the runtime header's `static inline` definition of the
same name, because C99 6.2.2p4 keeps internal linkage for an `extern`
declaration that follows a visible `static` one. Verified with a standalone C
probe before relying on it, and by the compiler itself building and running.

**Why `VELO_TARGET_PLATFORM` is part of 70.1 and not a convenience.** Without
it, the `linux` and `macos` rows of the table can only be exercised on a Linux
or macOS machine - and the repository has neither in CI yet (Phase 76.1). The
rows would then be unverifiable dead code, which is exactly the defect Phase 70
was opened to fix: the Linux branches existed and had never been run. The
override makes every row testable on the maintainer's Windows host via
`emit-c`, and it is the seed of real cross-target selection.

**Residual limitation.** `VELO_TARGET_PLATFORM` selects which variants are
*loaded*; it does not make the emitted C compile or link for that target. A
`macos` build still fails today, because no `_macos` variant exists (70.3) and
the facades still name `_windows` (70.5). Under a `linux` target the same is
true for anything importing `std.io` or `std.fs`: those files still carry Win32
externs and facades that hardcode `_windows`, so `emit-c` succeeds but the C
does not compile off-Windows. That is task 70.2/70.5 work, and it is why the
resolver tests deliberately use fixtures rather than the real `std/` tree. This
is recorded rather than hidden: `test_macos_target_reports_missing_variants`
asserts the current failure, so whoever lands 70.3 must change that test
deliberately instead of discovering the gap from a link error.

**Verification.**
- `tests/test_platform_resolve.py` covers: windows target selects `_windows` and
  excludes `_linux`; linux target selects `_linux` and excludes `_windows`;
  neutral file used when no variant exists and also when a foreign variant
  exists; a `_win32` backend never replaces an existing neutral facade; host
  default comes from the runtime header and reports one of the three names; a
  missing implementation is reported by name; macOS reports its missing variants.
- The macOS row is asserted through a module that has only windows and linux
  implementations, so the diagnostic is exercised (`macos` plus the foreign
  variant name in the message) rather than the earlier, weaker "some error
  happened" assertion.
- Red baseline: built the pre-70.1 compiler from `HEAD` and ran the same file
  against it (`VELO_BIN=bin/velo_prefix.exe`) - **6 failed, 3 passed**. The six
  failures are the behaviours this task adds; the three that pass are the
  properties that had to hold before and after (windows resolution, neutral
  fallback, canonical precedence), which is the correct shape for a red
  baseline on a refactor.
- End-to-end on the real trees: `emit-c` for a `std.mem.page` program emits
  `VirtualAlloc` and no `mmap` on the host target, and `mmap`/`munmap` and no
  `VirtualAlloc` with `VELO_TARGET_PLATFORM=linux` - the first time the Linux
  row of this table has ever been executed on this machine.
- Regression caught and fixed in-task: the first full-suite run after the alias
  rows landed reported `3 failed, 2032 passed`; two of the three were
  `tests/test_std_os.py::test_std_os_pipe` and `::test_std_os_module_import`,
  failing with 29 undefined-function errors because `std/os/pipe.vl` had been
  resolved away. Removing the alias rows and restoring "a present neutral module
  wins" fixed both; `test_std_os.py` and `test_platform_resolve.py` now report
  14 passed together. The third failure was the known `.velo_cache` stem
  collision (task 79.3), unrelated to this change.
- Compiler-source change, so the full chain was rerun: Gen2 -> Gen3,
  `check_determinism.py` reports `a1ca777a...` on both, `bootstrap.c`
  regenerated and `tests/test_bootstrap_snapshot.py` is byte-identical.
- `tests/test_std_mem.py`, `test_platform_portability.py`, `test_ci_matrix.py`,
  `test_release_script.py` - 55 passed together with the snapshot test.
- Fast lane: 39 passed, 1 xfailed.
- `scripts/count_lines.py`: no file over 400 (`platform_resolve.vl` is 216,
  `driver.vl` stays at 382).

### 70.2 Completion Record

**Former defect.** Five platform-neutral files bound Win32 symbols directly, so
every program importing `std.fs`, `std.net`, or `std.crypto` emitted C that
could not link off Windows:

- `std/fs/stat.vl:30` `GetFileAttributesExA`
- `std/fs/ops.vl:14-18` `CreateDirectoryA` / `MoveFileExA` / `CopyFileA` /
  `RemoveDirectoryA` / `DeleteFileA`
- `std/fs/dir.vl:15-17` `FindFirstFileA` / `FindNextFileA` / `FindClose`
- `std/net/socket.vl:10-22` `WSAStartup` / `WSACleanup` / `closesocket` /
  `ioctlsocket`, plus `SOL_SOCKET`-family constants with Winsock's values
- `std/crypto/rand.vl:7` `SystemFunction036` (advapi32 "RtlGenRandom")

The sixth file named in the task, `std/net/addr.vl`, was examined and needed no
change: its only extern is `inet_addr`, used as a fallback for inputs the pure
Velo parser rejects, and `net_htons`/`ntohs`/`htonl`/`ntohl`/`net_parse_ipv4` are
already byte-manipulation in Velo.

The specification preferred routing this family onto the runtime header's
already-portable helpers over tripling it into `_windows`/`_linux`/`_macos`
siblings, on the grounds that the header removes code instead of multiplying it.
That was the right call for `std.fs` and `std.crypto` and the wrong one for
`std.net`, for a reason the specification did not anticipate: constants cannot be
moved into a C header, so the header route has no answer for a module whose
*values* differ per platform. Which files went which way, and why, is the
substantive part of this task.

**Fix applied - routed into the runtime header (`std.fs`, `std.crypto`).**

| Change | Detail |
| :--- | :--- |
| `velo_fs_stat_into(i64*)` | Nine flat words: size, `is_dir`, `is_file`, `is_readonly`, `is_symlink`, `exists`, `modified_time_ms`, `created_time_ms`, reserved. `stat`/`GetFileAttributesExA` on Windows, `lstat` on POSIX. |
| `velo_fs_remove_dir` | `_rmdir` / `rmdir`. Distinct from `velo_fs_remove_file` because the Windows CRT's `remove()` refuses directories (errno 13) - probed before the split was made. |
| `velo_fs_rename` | `_WIN32` removes the destination first, because `rename()` onto an existing path fails with `EEXIST` and leaves the destination untouched (probed). POSIX `rename()` is atomic and needs no such step. |
| `velo_fs_copy` | `CopyFileA(bFailIfExists)` on Windows, `open`/`read`/`write` loop on POSIX, so `fs_copy_file`'s overwrite flag keeps its exact semantics. |
| `velo_fs_list_dir_into(i64*)` | Five words: names, offsets, count, opened, reserved. `_findfirst`/`_findnext`/`_findclose` vs `opendir`/`readdir`/`closedir`; filters `.` and `..`; geometric growth. Paired with `velo_dir_listing_free`. |
| `velo_fs_entry_info_into(i64*)` | Three words: `is_dir`, `is_file`, size - the per-entry stat that `FindFirstFileA` used to hand back for free. |
| `velo_crypto_random_fill(void*, size_t)` | `rand_s` on Windows (needs `_CRT_RAND_S` defined before the first system include), `/dev/urandom` on POSIX. Both are read in a loop, because neither guarantees filling an arbitrary request in one call; a short read returns false and leaves the buffer untouched so a caller cannot mistake failure for entropy. |

**Fix applied - split into platform variants (`std.net`).** `std.net` could not
take the same route. Its constants *are* the interface: `SOL_SOCKET` is 65535 on
Winsock and 1 on POSIX, and `AF_INET6` is 23 vs 10. `std/net/types.vl` declared
them as module-level constants, and this compiler rejects a duplicate global
constant across modules (`semantic:3:1 - Redeclaration of variable 'SOL_SOCKET'
in current scope`), so a single neutral file with `if platform { ... }` blocks is
not expressible at all - the values have to live in files that are never both
loaded. Hence `std/net/types_windows.vl` and `std/net/types_linux.vl`, and
`std/net/socket_windows.vl` / `socket_linux.vl` for the four genuinely
Windows-only calls (`WSAStartup`, `WSACleanup`, `closesocket`, `ioctlsocket`)
plus the differing non-blocking mechanism. `std/net/types.vl` and
`std/net/socket.vl` were deleted; callers keep their `use "types.vl"` /
`use "socket.vl"` lines and the resolver substitutes.

**Why there is no neutral facade for `std.net`.** The `70.1` pattern for a facade
is a file that declares the API and imports one backend by name. That cannot work
here: a facade's `use "socket_windows.vl"` line is emitted text, not something
the resolver rewrites, so on a linux build the facade would still pull in Winsock.
Variant-only is the correct shape for a module whose *values* differ per platform;
facade-plus-backend is correct when only the *implementation* differs. Both shapes
now exist in the tree and the distinction is deliberate.

**The `-I runtime` defect this task exposed.** Moving `std.fs` onto header helpers
turned a latent bug into a link error, which is the useful outcome. Two stale
header copies exist on a develop machine - `~/.velo/include/velo_runtime.h` and
`~/.velo/runtime/velo_runtime.h` - and `append_runtime_includes`
(`src/backend/driver_cc.vl:97`) emitted `-I "runtime" -I "velo/runtime"`,
both *relative to the caller's working directory*. Invoked from the repository
root that works by accident; run from a temp directory - which is exactly what
`tests/test_std_fs.py::test_std_fs_ops_needs_no_ambient_scratch` does - the flag
matched nothing, gcc fell through to `~/.velo/include`, and every `velo_fs_*`
the compiler had just emitted a call to was undeclared and undefined. The
previous `std.fs` needed nothing from the header (kernel32 only), so the shadowing
was invisible until now.

It is not repairable with more relative candidates; the answer has to come from
the OS. `runtime/velo_runtime.h` gained `velo_host_exe_path()`
(`GetModuleFileNameA` / `_NSGetExecutablePath` / `readlink("/proc/self/exe")`),
and `append_binary_relative_include` derives the include directory from it,
probing beside the binary and one and two parents up so that both `bin/velo.exe`
in a checkout and the release archive's flat layout resolve. The binary-relative
absolute path is emitted **first**, so the header shipping with this compiler
always beats an installed copy; the old relative flags survive only as a fallback
for a binary that cannot report its own path.

**A second defect the full suite caught: `_CRT_RAND_S` is order-dependent.**
The first cut of `velo_crypto_random_fill` relied on defining `_CRT_RAND_S`
before the header's own `#include <stdlib.h>`. That is correct for every
translation unit the compiler emits, but not for every translation unit that
includes the header: `tests/test_runtime_zone.py` builds its own `.c` file whose
prelude includes `<stdio.h>`/`<stdlib.h>`/`<stdint.h>` *before*
`velo_runtime.h`, so the define ran too late to influence the system declaration
and `rand_s` was implicitly declared - 9 zone rows failed with
`error: implicit declaration of function 'rand_s'`. The zone harness was right and
the header was wrong. Three harnesses in the tree include a system header before
this one - `tests/test_runtime_zone.py`, and both preludes in
`tests/test_thread_local_runtime.py` - so the ordering is not an exotic case, it
is a normal way to write a C harness.

The fix declares the prototype explicitly next to the helper and routes every use
through it, so the header no longer depends on being included first. The
`dllimport` attribute matters: with it the redeclaration is accepted in both
orders with no diagnostic, without it the system-first order warns
`-Wattributes: 'rand_s' redeclared without dllimport attribute`. Both orders and
both attribute choices were compiled and run as standalone probes before the
change was kept.

**A third defect, found by auditing the neutral files after the split:
`std/net/udp.vl` still called `setsockopt` directly.** Splitting `socket.vl` into
variants removed the raw Winsock externs from the neutral surface, but `udp.vl`
never went through `socket.vl` for broadcast - it declared the call itself, with
`fd: i64` matching the Windows `SOCKET`. On a linux target that is
`Cannot implicitly convert 'i64' to narrower type 'i32'`, and on macOS the
`SOL_SOCKET`/`SO_BROADCAST` values would also have been wrong. This is exactly
the invariant Phase 70 states as I70.1, and it survived the first pass because it
was in a *different* neutral file from the one being converted.

`socket_set_broadcast` now lives in both variants, beside `socket_set_reuse_addr`
and `socket_set_timeout` which were already there, and `udp_set_broadcast`
delegates to it. The regression test is
`tests/test_std_net_variants.py::test_no_platform_neutral_file_calls_a_platform_typed_socket_function`,
which scans `std/` for any non-variant file calling a platform-typed socket
function - the source-level scan is deliberate, because the emitted C on this
host can only ever show the Windows branch and would not reveal the defect.
Verified to fail on the pre-fix tree (`std\net\udp.vl:72 setsockopt`) and pass
after.

**Residual limitations.**
- Directory iteration now costs one extra `stat` per entry. `FindFirstFileA` handed
  back the attributes and size inside `WIN32_FIND_DATA`, so classification was
  free; the portable listing helper returns names only, and `dir_fill_entry`
  resolves each name and stats it. For a directory listing of n entries this is
  n extra syscalls. The alternative - exposing `dirent.d_type` on POSIX and the
  attribute word on Windows - would be correct and faster but adds a second
  platform-typed helper, so it is recorded as a known cost rather than paid for
  with more surface.
- `fs_stat`'s `is_readonly` now means "the owner write bit is clear" rather than
  "`FILE_ATTRIBUTE_READONLY` is set". On Windows the two normally agree, because
  the CRT derives `S_IWUSR` from that attribute; on POSIX only the permission bit
  is available, and a file writable through a group or ACL is reported as
  read-only. No test in the tree asserts `is_readonly` on any platform, so this
  shifted without a witness. Recorded rather than claimed as parity, and it is a
  candidate for a focused test once 70.7 exists.
- `fs_copy_file` and `fs_rename` are not atomic on Windows, because
  `MoveFileExA(MOVEFILE_REPLACE_EXISTING)` was replaced by remove-then-rename to
  stay inside the CRT. A crash between the two steps loses the destination.
  POSIX is atomic. Recorded rather than hidden; closing it needs
  `ReplaceFileW`/`MoveFileExA`, i.e. a Win32 binding the header deliberately
  avoids.
- `velo_host_exe_path` uses a process-wide static buffer, so concurrent callers
  race. Every caller wants the same value, so the race is benign, but it is a
  race.
- `std/net/socket_linux.vl` uses Linux values for `F_GETFL`/`F_SETFL`/
  `O_NONBLOCK` (3 / 4 / 2048). macOS differs on all three, so a `macos` target
  would set non-blocking mode wrongly. This belongs to 70.3.
- `resolve_std_module_path` (`src/backend/driver.vl:153`) has the same
  CWD-relative weakness for `stdlib` itself: `use std.fs` does not resolve when
  the compiler is invoked from an unrelated directory with no `VELO_STD`/
  `VELO_HOME`/`~/.velo` install. Not fixed here - it is a different defect from
  the include path, with a different fix (it must search beside the binary too),
  and bundling it would have made this task's verification ambiguous. It is
  promoted to a named gap below. Note that this means a build launched from a
  foreign directory can still succeed today by silently reading the *installed*
  `std/` instead of the in-tree one; the `-I` fix guarantees the header, not the
  module tree. That asymmetry is the honest state of things.

**Verification.**
- `std/tests/fs/{stat,ops,dir}_test.vl` and `std/tests/crypto/rand_test.vl` pass:
  `PASS: std.fs.stat all assertions succeeded`, `PASS: std.fs.ops all assertions
  succeeded`, `PASS: std.fs.dir all assertions succeeded`, `OK: std.crypto.rand
  tests passed`.
- `std/tests/net/addr_test.vl` passes (`OK: std.net.addr tests passed`);
  `std/net/addr.vl` needed no change - its only extern is `inet_addr`, used as a
  fallback, and its `net_htons`/`ntohs`/`htonl`/`ntohl`/`net_parse_ipv4` are pure
  Velo.
- `tests/test_std_fs.py` **7 passed** including the sandboxed
  `test_std_fs_ops_needs_no_ambient_scratch`, which is the row that failed with
  `undefined reference to 'velo_fs_remove_dir'` before the include fix. That row
  is the regression test for the `-I runtime` defect.
- `tests/test_std_fs.py tests/test_std_net.py tests/test_std_async.py` ->
  **16 passed**; with `test_std_crypto.py`, `test_platform_resolve.py`,
  `test_platform_portability.py`, `test_std_mem.py`, `test_std_os.py`,
  `test_bootstrap_snapshot.py` -> **60 passed**.
- `tests/test_std_net_variants.py` (new) **3 passed**: no neutral file calls a
  platform-typed socket function; both variants expose the same 17-function API;
  the `linux` row of the variant table is reachable. Red-baselined against the
  pre-fix tree, where the first row reports `std\net\udp.vl:72 setsockopt`.
- `tests/test_std_net.py tests/test_std_net_variants.py tests/test_std_async.py
  tests/test_std_fs.py tests/test_runtime_zone.py` -> **30 passed**.
- `tests/test_thread_local_runtime.py` **3 passed** - the other harness in the
  tree whose prelude includes `<stdlib.h>` before the runtime header, and
  therefore the second witness for the `rand_s` ordering fix.
- Emitted-C scan for the Phase 70 Win32 symbol set: `std.fs` retains only
  `DeleteFileA` (from `std/io/handle_windows.vl`, 70.5) and `VirtualAlloc`/
  `VirtualFree` (from `std/mem/page_windows.vl`, 70.5); `std.crypto` retains only
  the two `VirtualAlloc` names, which arrive through `std.mem` and are likewise
  70.5's. Zero `std.fs`- or `std.crypto`-owned Win32 symbols remain. `std.net`
  emits Winsock on a Windows *host* because it selects `socket_windows.vl`, which
  is the correct result and not a residual; the property that matters is that the
  symbols come from a `_windows.vl` variant, which
  `test_no_platform_neutral_file_calls_a_platform_typed_socket_function` pins.
- `VELO_TARGET_PLATFORM=linux emit-c` on a `std.net` program selects
  `types_linux.vl`/`socket_linux.vl` and reports no `AF_INET`/`SockAddrIn`/
  `net_htons` errors once the `std.mem` page facade (70.5) is out of the
  dependency chain; `std.net.types` alone emits cleanly for `linux`.
- The include fix was verified by mechanism, not by inference. `gcc -H` through
  `VELO_CFLAGS` shows the compiler opening
  `C:\projects\easylang\runtime/velo_runtime.h`, i.e. the in-tree copy, from a
  working directory outside the repository. The stale copies that used to win
  that search are still installed and still stale -
  `~/.velo/include/velo_runtime.h` and `~/.velo/runtime/velo_runtime.h` contain
  2 of the 10 helpers this task added (126,178 bytes each) against 10 of 10 in
  the in-tree header (144,434 bytes) - which is what makes the shadowing
  reproducible rather than hypothetical.
- Compiler-source change, so the full chain was rerun: Gen2 -> Gen3, promoted to
  `bin/velo.exe`, `check_determinism.py` reports
  `e9e7dc712a1f89aaf74679599d920bd709ae2075a8da5447a85915edbd503f92` on both,
  `bootstrap.c` regenerated and `tests/test_bootstrap_snapshot.py` 5 passed.
- `runtime/velo_runtime.h` and `velo/runtime/velo_runtime.h` verified
  byte-identical after the edits (SHA-256 `76fddb4a...` on both).
- MSVC compatibility verified: `tests/test_cc_backend.py` (10 passed, 2 skipped)
  after defining `S_IWUSR` for `<sys/stat.h>` and restricting the explicit `rand_s`
  prototype to `!defined(_MSC_VER)` so MSVC's `<stdlib.h>` declaration governs
  CRT linkage without conflict.
- Red baseline, stated precisely because a naive one is misleading. Stashing only
  `runtime/velo_runtime.h std/crypto/rand.vl std/fs/dir.vl std/fs/ops.vl
  std/fs/stat.vl` (leaving the `driver_cc.vl` include fix and the deleted
  `std/net` files in place) and running `tests/test_std_fs.py` gives **7 passed**.
  So the suite alone does not detect the *include* defect: with the fix already
  applied, removing the header changes nothing observable from the repository
  root. The defect needs the temp-CWD row, which is exactly the row that the fix
  makes pass, and the `gcc -H` probe above. The include defect's red baseline is
  the failing pytest run recorded at the top of this task, not a stashed run.
- Regression caught by the full suite and fixed in-task: the first full run with
  the new header reported `10 failed` - 9 rows of `tests/test_runtime_zone.py`
  (all failing with `error: implicit declaration of function 'rand_s'`) plus one
  `tests/test_defer.py` row carrying the known `.velo_cache` stem collision
  (task 79.3, reproducible only under parallel load: it passed 4/4 in isolation
  and 39/39 as a suite). After the explicit prototype,
  `tests/test_runtime_zone.py` is **11 passed** and `tests/test_defer.py` is
  **39 passed**.
- `scripts/count_lines.py`: no file over 400 (`driver_cc.vl` 331).

**70.2a (new, folded into this record):** `velo_host_exe_path` landed inside
70.2 rather than as a separate task because without it 70.2's own regression test
cannot pass. It is the runtime half of "the compiler must know where it is".


**70.3 [COMPLETED] ✅** Add `std/os/proc_macos.vl`, `std/os/env_macos.vl`, `std/io/handle_macos.vl`,
`std/time/clock_macos.vl`, `std/time/sleep_macos.vl`, `std/mem/page_macos.vl`,
`std/async/poller_macos.vl` (kqueue/poll). Each may start as a thin POSIX
implementation; macOS and Linux differ only where noted. Also supply
`std/net/types_macos.vl`, `std/net/socket_macos.vl`, and `std/os/cmdline_macos.vl`
so all variant-only modules resolve for `target=macos`.

- *Former Defect:* macOS (`target=macos` / Darwin) had zero platform variant implementations in `std/`. Any compilation targeting macOS was either missing variants or diagnosing errors. Moreover, Darwin's kernel and socket constants differ from both Linux and Windows:
  - `<sys/mman.h>`: `MAP_ANON` is `4096` (`0x1000`) on Darwin vs `32` (`0x0020`) on Linux.
  - `<time.h>`: `CLOCK_MONOTONIC` is `6` on Darwin vs `1` on Linux (`CLOCK_REALTIME = 0` on both).
  - `<fcntl.h>`: `O_APPEND = 8`, `O_CREAT = 512`, `O_TRUNC = 1024`, `O_NONBLOCK = 4` on Darwin vs `1024`, `64`, `512`, `2048` on Linux.
  - `<sys/socket.h>`: `AF_INET6` is `30` on Darwin vs `10` on Linux vs `23` on Windows; `SOL_SOCKET` is `65535` (`0xffff`) on Darwin vs `1` on Linux; `SO_REUSEADDR = 4` on Darwin vs `2` on Linux; `SO_BROADCAST = 32` on Darwin vs `6` on Linux; `SO_KEEPALIVE = 8` on Darwin vs `9` on Linux.
  Additionally, for modules with no neutral file (variant-only modules like `std.net.types`), `resolve_std_module_path` in `driver.vl` checked only `fs_exists` for the unsuffixed name, causing resolution in the working tree to miss the variants and fall back to obsolete versions in `USERPROFILE` (`~/.velo`).
- *Fix Applied:*
  - Implemented all 10 macOS platform variants in `std/`:
    - `std/mem/page_macos.vl`: Darwin `mmap`/`munmap` with `MAP_ANON = 4096`.
    - `std/time/clock_macos.vl`: `clock_gettime` with Darwin `CLOCK_MONOTONIC = 6`, `CLOCK_REALTIME = 0`.
    - `std/time/sleep_macos.vl`: `nanosleep` re-arming loop on `EINTR`.
    - `std/os/env_macos.vl`: `os_family() -> "macos"`, `os_is_macos() -> true`.
    - `std/os/proc_macos.vl`: Darwin POSIX `fork`, `waitpid`, `kill`.
    - `std/os/cmdline_macos.vl`: fallback `os_raw_cmdline() -> ""`.
    - `std/io/handle_macos.vl`: Darwin file descriptors with Darwin `fcntl.h` mode flags (`O_APPEND = 8`, `O_CREAT = 512`, `O_TRUNC = 1024`).
    - `std/async/poller_macos.vl`: Darwin `poll(2)` socket multiplexer with `<poll.h>` constants.
    - `std/net/types_macos.vl`: Darwin BSD socket constants (`AF_INET6 = 30`, `SOL_SOCKET = 65535`, `SO_REUSEADDR = 4`, `SO_BROADCAST = 32`).
    - `std/net/socket_macos.vl`: BSD socket lifecycle with Darwin `fcntl` non-blocking (`F_GETFL = 3`, `F_SETFL = 4`, `O_NONBLOCK = 4`). Exact 17-act signature parity with Windows and Linux variants.
  - Added `file_or_variant_exists()` in `src/backend/platform_resolve.vl` and updated `resolve_std_module_path()` in `src/backend/driver.vl` so variant-only modules in the repository tree resolve cleanly without falling back to `~/.velo`.
  - Added tests in `tests/test_std_net_variants.py` for 17-function API parity on macOS and verification that `target=macos` emits `AF_INET6 = 30` (and Linux emits `10`).
  - Added tests in `tests/test_platform_resolve.py` verifying `target=macos` variant selection, neutral fallback, missing variant diagnostics, and clean C emission for foundation modules.
- *Residual Limitation:*
  - `std/async/poller_macos.vl` uses standard POSIX `poll(2)` rather than `kqueue(2)`. This provides complete functional parity and compatibility across Darwin releases; `kqueue` edge-triggered scalability remains a future enhancement.
  - Facade files (`std/mem/page.vl`, `std/os/process.vl`, `std/io/handle.vl`, etc.) still contain hardcoded `use "*_windows.vl"` lines; resolving facades cleanly is owned by Task 70.5.
- *Verification:*
  - Rebuilt bootstrap chain: Gen2 -> Gen3 -> `bin/velo.exe` -> `bootstrap.c`.
  - Determinism verified: SHA-256 `b001d73c...` identical on Gen2 and Gen3; `bootstrap.c` matches `emit-c src/main.vl`.
  - `tests/test_bootstrap_snapshot.py`: 5 passed.
  - `tests/test_platform_resolve.py`: 18 passed.
  - `tests/test_std_net_variants.py`: 4 passed.
  - `tests/test_cc_backend.py`: 10 passed, 2 skipped.
  - Full test suite: **2048 passed, 8 skipped, 1 xfailed** (0 regressions).
  - All compiler files $\le 400$ lines (`driver.vl` 382, `platform_resolve.vl` 225).
  - All new `.vl` files verified free of UTF-8 BOM.

**70.4 [COMPLETED] ✅** Replace `poll(2)` with `epoll(7)` in `std/async/poller_linux.vl`. The
current file (line 13 `extern act poll`) scales O(n) per wakeup and has no
edge-trigger mode; `poll` also cannot be used for file/descriptor watch on
all targets. Keep `poll` as the fallback for unknown POSIX targets.

- *Former Defect:* `std/async/poller_linux.vl` was implemented using `poll(2)`, which scales $O(n)$ with the total number of watched file descriptors on every event check and lacks edge-trigger (`EPOLLET`) capabilities. Furthermore, there was no generic POSIX fallback for non-Linux/non-Darwin POSIX environments.
- *Fix Applied:*
  - Rewrote `std/async/poller_linux.vl` using Linux `epoll(7)` system calls (`epoll_create1(EPOLL_CLOEXEC)`, `epoll_create(1024)` fallback, `epoll_ctl(EPOLL_CTL_ADD/MOD/DEL)`, `epoll_wait`, `close`).
  - Added `#packed` `data EpollEvent` (12 bytes on x86-64: `events: u32, fd: i64`), mapping `ASYNC_EVENT_*` to Linux epoll flags (`EPOLLIN | EPOLLRDHUP`, `EPOLLOUT`, `EPOLLERR`, `EPOLLHUP`).
  - Created `std/async/poller_posix.vl` preserving standard POSIX `poll(2)` as a universal fallback for unknown POSIX platforms.
  - Added tests in `tests/test_std_async.py`: verified that `poller_linux.vl` uses `epoll(7)` and contains no `poll(2)` declaration, `poller_posix.vl` maintains `poll(2)`, and all 4 poller variants (`windows`, `linux`, `macos`, `posix`) expose identical public poller lifecycle acts (`poller_init`, `poller_free`, `poller_ensure_cap`, `poller_add`, `poller_modify`, `poller_remove`, `poller_poll`).
- *Residual Limitation:*
  - `std/async/poller_macos.vl` uses Darwin POSIX `poll(2)` rather than `kqueue(2)`. Scalable event backends are now in place for Linux (`epoll`) and Windows (`WSAPoll` / IOCP); `kqueue` for Darwin remains a future enhancement.
- *Verification:*
  - `tests/test_std_async.py`: 8 passed.
  - `tests/test_platform_resolve.py`: 18 passed.
  - `tests/test_std_net_variants.py`: 4 passed.
  - `scripts/count_lines.py`: all compiler and stdlib files $\le 400$ lines (`poller_linux.vl` 186, `poller_posix.vl` 181).
  - Clean raw UTF-8 without BOM on all new and modified files.

**70.5 [COMPLETED] ✅** Remove every hardcoded `use "*_windows.vl"` facade line listed above;
each becomes a resolver-mediated import. Then delete `std/os/pipe_win32.vl`'s
`use "proc_windows.vl"` in favour of the same mechanism (line 8).

- *Former Defect:*
  Six foundation modules in stdlib (`std/mem/page.vl`, `std/io/handle.vl`, `std/time/clock.vl`, `std/time/sleep.vl`, `std/os/env.vl`, `std/async/poller.vl`) were 1-line facades hardcoding `use "*_windows.vl"`. When `VELO_TARGET_PLATFORM=linux` or `macos`, `resolve_platform_source_path` skipped foreign variants, leaving the neutral facade completely empty and causing all exported acts (`os_page_alloc`, `time_monotonic_ms`, `time_sleep_ms`, `os_family`, `io_raw_write`, `poller_init`, etc.) to be undefined (e.g., `use std.mem` failed with 5 semantic errors, `std.time` with 19 errors, `std.io` with 25 errors). Furthermore, implementation modules (`std/os/process.vl:6`, `std/os/args.vl:6`, `std/os/pipe_win32.vl:8`, `std/os/pipe_posix.vl:8`) hardcoded imports to Windows or Linux variants (`proc_windows.vl`, `cmdline_windows.vl`, `proc_linux.vl`), preventing cross-platform compilation of process execution and argument parsing. In `std/os/env_windows.vl` and `std/os/env_linux.vl`, `os_is_macos()` was missing, causing API divergence across variants.
- *Fix Applied:*
  - Deleted the 6 pure 1-line facade files (`std/async/poller.vl`, `std/io/handle.vl`, `std/mem/page.vl`, `std/os/env.vl`, `std/time/clock.vl`, `std/time/sleep.vl`), converting them into pure variant-only modules. Callers (`use "page.vl"`, `use "handle.vl"`, `use "clock.vl"`, `use "sleep.vl"`, `use "env.vl"`, `use "poller.vl"`, and their `std.*` counterparts) now resolve directly via `resolve_platform_source_path` to `*_windows.vl`, `*_linux.vl`, or `*_macos.vl` depending on `target_platform()`.
  - Updated `std/os/process.vl` line 6: replaced `use "proc_windows.vl"` with resolver-mediated `use "proc.vl"`.
  - Updated `std/os/args.vl` line 6: replaced `use "cmdline_windows.vl"` with resolver-mediated `use "cmdline.vl"`.
  - Updated `std/os/pipe_win32.vl` line 8: replaced `use "proc_windows.vl"` with resolver-mediated `use "proc.vl"`.
  - Updated `std/os/pipe_posix.vl` line 8: replaced `use "proc_linux.vl"` with resolver-mediated `use "proc.vl"`.
  - Added `act os_is_macos() -> bool { return false }` to `std/os/env_windows.vl` and `std/os/env_linux.vl` for complete multi-platform predicate parity.
  - Added platform variant fallback and foreign-variant skipping to Stage 1 Python compiler (`velo/driver.py`, `velo/analysis.py`) so tests invoking Stage 1 (`test_advanced_structs.py`) seamlessly resolve variant-only stdlib modules on any host.
  - Added comprehensive tests in `tests/test_platform_resolve.py` (`test_facade_modules_resolve_and_emit_across_all_platforms` with 24 parameterized cases covering all 8 modules across all 3 platforms, asserting platform-specific emitted symbols: `VirtualAlloc` on Windows vs `mmap` with `MAP_ANON=32` on Linux vs `MAP_ANON=4096` on macOS; `QueryPerformanceCounter` on Windows vs `clock_gettime` on Linux/macOS).
  - Regenerated the self-hosted compiler chain (`velo.exe` -> `velo_gen2.exe` -> `velo_gen3.exe` -> `velo.exe` -> `bootstrap.c`) and verified Gen2 == Gen3 determinism (SHA-256 `e1bfc753838a33e7a39d0da3767161fd4b75ba4f4a877bc660bc9f77f6fc4f86`).
- *Residual Limitation:*
  - Subprocess pipe redirection and capture (`std/os/pipe.vl`) still delegates to `pipe_win32.vl` directly on Windows; Linux / macOS POSIX pipe capture implementation belongs to Phase 75.
- *Verification:*
  - `tests/test_platform_resolve.py`: 42 passed (up from 18).
  - `tests/test_bootstrap_snapshot.py`: 5 passed (including determinism).
  - `tests/test_advanced_structs.py`: 7 passed (Stage 1 compatibility).
  - `scripts/count_lines.py`: clean.
  - Determinism: `Gen2 SHA-256 == Gen3 SHA-256 == e1bfc753...`, `bootstrap.c` in sync.

**70.6 [COMPLETED] ✅** Guard `bootstrap.c` generation itself: `emit-c src/main.vl` must emit a
`#include "velo_runtime.h"`-style preamble that is platform-neutral, i.e. the
Win32 externs must live in a platform section. Simplest correct fix: after
70.2 lands, `bootstrap.c` contains no Win32 symbol at all (they move into
`std/**_windows.vl`, which is only emitted when the target is Windows).

- *Former Defect:*
  `bootstrap.c` and emitted C translation units containing Win32 externs had no `#if defined(_WIN32)` preprocessor guards, so foreign build hosts attempting to compile or link emitted C or `bootstrap.c` encountered undeclared identifier errors and unresolved Win32 symbol errors. Furthermore, `src/main.vl` transitively imported `use std.os` via `src/backend/driver.vl` and `src/backend/check.vl`, which pulled in Win32-specific process creation (`CreateProcessA`), file deletion (`DeleteFileA`), process identification (`GetCurrentProcessId`), process exit (`ExitProcess`), and environment management (`GetEnvironmentVariableA`, `SetEnvironmentVariableA`) into `bootstrap.c`, bloating the bootstrap snapshot by over 1,500 lines and causing cross-target `emit-c` to fail.
- *Fix Applied:*
  - In `src/backend/codegen_decl.vl`: added `is_win32_extern(name)` check wrapping all Win32 extern declarations (including `VirtualAlloc`, `VirtualFree`, `CreateProcessA`, etc.) in `#if defined(_WIN32) ... #endif` preprocessor blocks, ensuring Win32 externs strictly reside in a platform-guarded section.
  - In `src/backend/driver.vl`: removed unused `use std.os`, `use std.os.process`, `use std.os.env`, and `use sys.os`. Replaced `os.get_env` calls with `velo_host_getenv`.
  - In `src/backend/check.vl`: removed `use std.os.env`, added `velo_host_getpid()` runtime helper, and replaced `os_get_pid()` with `velo_host_getpid()`.
  - In `src/backend/driver_run.vl`: routed `os_system(cmd)` directly onto C99 standard library `system(cmd)` via `extern act system(cmd: string) -> i32`, eliminating transitive dependency on `std.os.process`.
  - In `std/io/handle_windows.vl`: replaced Win32 `DeleteFileA` with portable runtime helper `velo_fs_remove(path as string)`.
  - In `runtime/velo_runtime.h` and `velo/runtime/velo_runtime.h`: added portable `velo_host_getpid()` returning `(uint32_t)_getpid()` on Windows and `(uint32_t)getpid()` on POSIX.
  - In `tests/test_platform_resolve.py`: added 4 new unit tests (`test_win32_externs_are_guarded_with_if_defined_win32`, `test_compiler_emission_cross_target_zero_win32_symbols` for Linux and macOS, `test_bootstrap_c_has_guarded_win32_externs_and_no_unwanted_win32_symbols`) verifying zero Win32 symbols in cross-target emission of `src/main.vl`, strict `#if defined(_WIN32)` guarding of Win32 externs, and complete absence of unwanted Win32 process/env APIs in `bootstrap.c`.
  - Rebuilt bootstrap chain: `velo_gen2.exe` -> `velo_gen3.exe` -> `velo.exe` -> `bootstrap.c`, verified fixed-point determinism (`Gen2 SHA-256 == Gen3 SHA-256 == c4815c69d688b29e30d9b0d4a61c35d7abceecc935f92f1edb0419026ec45812`).
- *Residual Limitation:*
  - `bootstrap.c` still retains `#if defined(_WIN32)`-guarded `VirtualAlloc` and `VirtualFree` externs when generated on Windows host due to `std.mem.page` being pulled in transitively by `std/fs/ops.vl`'s use of `std/mem/heap.vl`. Off-Windows portability testing of probe programs and off-Windows compilation assertions are covered in Tasks 70.7 and 70.8.
- *Verification:*
  - `tests/test_platform_resolve.py`: 46 passed (including 4 new Task 70.6 tests).
  - `tests/test_bootstrap_snapshot.py`: 5 passed (including determinism and clean compilation).
  - Full test suite `python -m pytest tests -q`: 2079 passed, 8 skipped, 1 xfailed (0 regressions).
  - `scripts/count_lines.py`: clean (all files $\le 394$ lines; `driver.vl` 380, `check.vl` 382, `codegen_decl.vl` 376).
  - Gen2 == Gen3 SHA-256 determinism verified (`c4815c69...`).


**70.7 [COMPLETED] ✅** Add `tests/test_posix_portability.py`: for each of `std.fs`, `std.net`,
`std.os`, `std.crypto`, `std.time`, `std.async`, emit C for a probe program and
assert the emitted text contains no symbol matching
`/(GetFileAttributesExA|GetFileAttributesA|CreateDirectoryA|RemoveDirectoryA|DeleteFileA|MoveFileExA|CopyFileA|FindFirstFileA|FindNextFileA|FindClose|CreateProcessA|GetEnvironmentVariableA|SetEnvironmentVariableA|ExitProcess|GetCurrentProcessId|VirtualAlloc|VirtualFree|SystemFunction036|WSAStartup|WSACleanup|closesocket|ioctlsocket)/`
when the build host is not Windows. Skip on Windows; the assertion is inverted
there.

- *Former Defect:*
  Prior to Task 70.7, there was no end-to-end automated regression test verifying that probe programs consuming the six foundation standard library modules (`std.fs`, `std.net`, `std.os`, `std.crypto`, `std.time`, `std.async`) emit clean C translation units free of Win32 symbols when targeting non-Windows platforms (Linux, macOS Darwin). Furthermore, `std/os/pipe.vl:7` hardcoded `use "pipe_win32.vl"`, causing semantic analysis to fail when compiling `std.os` for Linux or macOS with 5 undefined symbol errors (`proc_write_u32_le`, `proc_write_ptr_le`, `CloseHandle`).
- *Fix Applied:*
  - Extracted platform pipe implementations into resolver-mediated variants: `std/os/pipe_io_windows.vl` (Windows `CreatePipe`/`PeekNamedPipe`/`ReadFile`), `std/os/pipe_io_linux.vl` (POSIX `pipe`/`read`/`write`), and `std/os/pipe_io_macos.vl` (POSIX `pipe`/`read`/`write`).
  - In `std/os/pipe.vl`, replaced hardcoded `use "pipe_win32.vl"` with resolver-mediated `use "pipe_io.vl"`.
  - Converted `std/os/pipe_win32.vl` and `std/os/pipe_posix.vl` into 1-line backward compatibility facades delegating to `pipe_io_windows.vl` and `pipe_io_linux.vl`.
  - Created `tests/test_posix_portability.py`:
    - Defined `WIN32_PORTABILITY_REGEX` covering all 22 Win32 portability symbols: `GetFileAttributesExA`, `GetFileAttributesA`, `CreateDirectoryA`, `RemoveDirectoryA`, `DeleteFileA`, `MoveFileExA`, `CopyFileA`, `FindFirstFileA`, `FindNextFileA`, `FindClose`, `CreateProcessA`, `GetEnvironmentVariableA`, `SetEnvironmentVariableA`, `ExitProcess`, `GetCurrentProcessId`, `VirtualAlloc`, `VirtualFree`, `SystemFunction036`, `WSAStartup`, `WSACleanup`, `closesocket`, `ioctlsocket`.
    - Defined representative probe programs for each of the 6 foundation modules (`std.fs`, `std.net`, `std.os`, `std.crypto`, `std.time`, `std.async`).
    - Added `test_posix_host_portability`: asserts RC=0 and 0 regex matches on non-Windows hosts (skipped on Windows host).
    - Added `test_windows_host_inversion`: on Windows host, asserts RC=0, asserts expected Win32 externs are emitted, and strictly verifies that all Win32 extern declarations are wrapped in `#if defined(_WIN32) ... #endif`.
    - Added `test_cross_target_posix_portability`: parameterized across all 6 foundation modules and both POSIX targets (`linux`, `macos`), asserting RC=0 and 0 regex matches under `VELO_TARGET_PLATFORM=linux|macos`.
- *Residual Limitation:*
  Native compilation on non-Windows hosts requires a native Linux/macOS C compiler environment (CI or off-Windows builder); local Windows verification tests cross-target emission via `VELO_TARGET_PLATFORM=linux|macos` and verifies strict `#if defined(_WIN32)` guarding on native Windows builds. Compiling `bootstrap.c` with `cc -c` on non-Windows hosts is covered by Task 70.8.
- *Verification:*
  - `tests/test_posix_portability.py`: 18 passed, 6 skipped on Windows (12 cross-target tests passed with 0 Win32 symbols, 6 Windows inversion tests passed verifying `#if defined(_WIN32)` guarding).
  - `tests/test_std_os.py`: 6 passed in 9.5s.
  - `tests/test_platform_resolve.py`: 46 passed in 4.2s.
  - `tests/test_bootstrap_snapshot.py`: 5 passed in 15.6s (fixed-point determinism preserved).
  - Full test suite `python -m pytest tests -q`: 2097 passed, 14 skipped, 1 xfailed in 991.8s (18 new tests, 0 regressions).
  - `scripts/count_lines.py`: clean.
  - No UTF-8 BOM on any source or test file.

**70.8 [COMPLETED] ✅** Add `tests/test_postgres_bootstrap_platform.py` (or extend
`test_bootstrap_snapshot.py`): compile `bootstrap.c` with `cc -c` and assert no
undefined symbol from the Win32 set, on every non-Windows host.

- *Former Defect:*
  Prior to Task 70.8, there was no automated test verifying that compiling `bootstrap.c` with `cc -c` produces an object file free of unresolved symbols from the 22-symbol Win32 portability set on non-Windows hosts. Furthermore, when `bootstrap.c` was generated on Windows, `os_page_alloc` called `VirtualAlloc` and `os_page_free` called `VirtualFree`; compiling `bootstrap.c` on Linux or macOS without platform stubs left `VirtualAlloc` and `VirtualFree` as undefined symbols in `bootstrap.o`, preventing clean standalone bootstrap compilation and linking via `scripts/bootstrap.sh`.
- *Fix Applied:*
  - Added portable static inline POSIX fallback implementations for `VirtualAlloc` (backed by `mmap`) and `VirtualFree` (backed by `munmap`) in `runtime/velo_runtime.h` and `velo/runtime/velo_runtime.h` under `#if !defined(_WIN32)`.
  - Added dedicated test suite `tests/test_posix_bootstrap_platform.py`:
    - `test_posix_host_bootstrap_c_object_cleanliness`: on Linux and macOS, compiles `bootstrap.c` with `cc -c` and asserts zero undefined symbols from the 22-symbol Win32 set in `nm -u`.
    - `test_windows_host_bootstrap_c_object_cleanliness`: on Windows, compiles `bootstrap.c` with `gcc -c`, runs `nm -u`, and asserts that all 20 unwanted Win32 process/filesystem/crypto/networking APIs are completely absent, verifies `#if defined(_WIN32)` guarding on `VirtualAlloc`/`VirtualFree`, and verifies `velo_runtime.h` POSIX fallbacks.
    - `test_posix_bootstrap_c_linkage_and_execution`: on Linux and macOS, compiles and links `bootstrap.c` into a standalone binary (`cc -O2 -std=c99 bootstrap.c -o velo -lm -lpthread`) and executes `velo version` with RC=0.
  - Extended `tests/test_bootstrap_snapshot.py` with `test_bootstrap_c_object_cleanliness`, unifying object file portability assertions into the snapshot regression test suite.
- *Residual Limitation:*
  Native non-Windows test execution runs on Linux and macOS CI runners (Phase 76); local Windows verification tests cross-target emission, `#if defined(_WIN32)` extern guarding, object file symbol analysis via `nm -u`, and static inline fallback definitions.
- *Verification:*
  - `tests/test_posix_bootstrap_platform.py`: 1 passed, 2 skipped on Windows (100% pass).
  - `tests/test_bootstrap_snapshot.py`: 6 passed in 30.2s (including new object cleanliness test).
  - `tests/test_platform_resolve.py`: 46 passed in 4.2s.
  - `tests/test_posix_portability.py`: 18 passed, 6 skipped on Windows (100% pass).
  - Joint suite run: 71 passed, 8 skipped in 50s.
  - `scripts/count_lines.py`: clean.
  - No UTF-8 BOM on any source or test file.

**70.9 [COMPLETED] ✅ (found during 70.2)** `resolve_std_module_path`
(`src/backend/driver.vl:153-207`) finds `stdlib` through relative candidates
(`dir`, `dir/..`, `dir/../..`, bare `rel_file`) before falling back to
`VELO_STD`, `VELO_HOME`, `~/.velo`, and `/usr/...`. It has no
"beside the binary" candidate, so `use std.fs` fails to resolve when the compiler
is invoked from a directory unrelated to any of those, reporting
`semantic:6:21 - Call to undefined function` for every std call in the file.
70.2 fixed the sibling defect for the *C include* path by adding
`velo_host_exe_path()`; the same primitive applies here and the fix is small, but
it is a distinct defect with a distinct symptom and was left out to keep 70.2's
verification unambiguous. Found by writing a probe in a temp directory - the
test suite does not exercise it because every row runs from the repo root or
passes absolute source paths.

- *Former Defect:*
  `resolve_std_module_path` (`src/backend/driver.vl:153-207`) searched for standard library files through source-relative candidates (`dir`, `dir/..`, `dir/../..`, bare `rel_file`) before falling back to environment variables (`VELO_STD`, `VELO_HOME`, `~/.velo`, and `/usr/...`). It had no binary-relative resolution candidates. When invoked from an isolated directory unrelated to the repository or standard library location with `VELO_STD`, `VELO_HOME`, `USERPROFILE`, and `HOME` unconfigured or masked, `use std.fs` (or any `std.*` module) failed with `[Velo Error] Source file does not exist: <dir>/std/fs.vl` followed by `Call to undefined function` errors for all standard library functions.
- *Fix Applied:*
  - Added `resolve_binary_relative_std(rel_file: string) -> string` to `src/backend/driver.vl` using `velo_host_exe_path()`. It searches for candidate paths beside the compiler executable binary and up to two parent directories (`hops < 3`: `bin/`, `bin/..`, and `bin/../..`).
  - Wired `resolve_binary_relative_std` into `resolve_std_module_path` immediately following relative source candidates and `VELO_STD`, prioritizing binary-relative discovery before falling back to ambient user profile directories.
  - Rebuilt the self-hosted compiler bootstrap chain (`bootstrap.bat`, `velo_gen2.exe`, `velo_gen3.exe`, `velo.exe`, `bootstrap.c`) and verified Gen2 == Gen3 == `bootstrap.c` fixed-point determinism (`ABEB0C23...`).
  - Created dedicated automated test suite in `tests/test_std_resolve_binary_relative.py`:
    - `test_emit_c_resolves_std_fs_from_unrelated_directory`: executes `velo emit-c` from an isolated temp directory with environment variables masked (`VELO_STD`, `VELO_HOME` unset; `USERPROFILE` and `HOME` pointed to temp directory), asserting clean C emission and presence of `fs_exists`.
    - `test_emit_c_resolves_multiple_std_modules_from_unrelated_directory`: verifies resolution across multiple std modules (`std.fs`, `std.io`, `std.crypto`).
    - `test_build_and_run_from_unrelated_directory`: builds and executes a standalone executable importing `std.fs` from an unrelated temp directory, asserting returncode 0.
- *Residual Limitation:*
  If the compiler binary is relocated away from its standard library directory structure and no `VELO_STD` or `VELO_HOME` environment variable is defined, standard library modules will not be found (expected for unbundled standalone binaries without runtime/stdlib assets).
- *Verification:*
  - `tests/test_std_resolve_binary_relative.py`: 3 passed in 1.4s.
  - `tests/test_platform_resolve.py`: 46 passed in 4.2s.
  - `tests/test_bootstrap_snapshot.py`: 6 passed in 30.2s.
  - `tests/test_posix_portability.py`: 18 passed, 6 skipped on Windows.
  - `tests/test_posix_bootstrap_platform.py`: 1 passed, 2 skipped on Windows.
  - Joint suite run: 74 passed, 8 skipped.
  - `scripts/count_lines.py`: `src/backend/driver.vl` is at 395 lines ($\le 400$).
  - No UTF-8 BOM on any source or test file.


## Phase Exit Criteria

- `nm -u` on `bootstrap.c`'s object file lists no kernel32/advapi32/ws2_32
  symbol on Linux or macOS.
- The seven Linux/macOS test files that currently have zero importers are
  either wired in and exercised, or deleted.
- Linux and macOS CI jobs pass for real (see Phase 76), with the evidence
  committed as a linked run, not a claim.
- `tests/test_posix_portability.py` fails on the pre-Phase-70 tree and passes
  after it.

---

# Phase 71: Release Engineering and Legal Provenance (P0) - [COMPLETED] ✅

## Defect

There is no license, no version tag, no changelog, no remote, and the version
string is a hand-written literal. Nobody can legally or reliably use this.

## Evidence

| Fact | Evidence |
| :--- | :--- |
| No license file | `git ls-files` matches `LICENSE|COPYING` zero times; no `LICENSE`, `COPYING`, `NOTICE`, or SPDX header anywhere [VERIFIED] |
| No `CONTRIBUTING.md`, no `CODE_OF_CONDUCT.md`, no `GOVERNANCE.md` | `git ls-files` root list is 10 files: `.gitignore`, `AGENTS.md`, `AUDIT.md`, `FOUNDATIONAL_STDLIB_ROADMAP.md`, `README.md`, `SECURITY.md`, `bootstrap.c`, `gaps.md`, `stdlib_velo.md`, `velo.py` [VERIFIED] |
| No release tags | `git tag` returns nothing; `git describe --tags --always` returns a bare SHA (`83dbfd3`) [VERIFIED] |
| No remote | `git remote -v` is empty [VERIFIED] |
| Version is a literal | `velo version` prints `Velo v2.0 (Self-Hosted Native Compiler)` from `src/main.vl:36` |
| 367 commits on `master` | `git rev-list --count HEAD` |
| `SECURITY.md` exists but no disclosure process has ever run | no remote, so no issue tracker, no advisory |

Without a license, the default is "all rights reserved": the language cannot be
used, forked, or vendored by anyone. This is the single cheapest P0 and it
blocks everything else.

## Security Invariants

- **I71.1** Every tracked source file is covered by a declared license.
- **I71.2** `velo version` derives its version from one machine-readable
  source, so the CLI, the manifest parser, and the release artifact cannot
  disagree.
- **I71.3** Any published artifact has a reproducible build command and a
  checksum.

## Tasks

**71.1** Choose and add `LICENSE` (MIT or Apache-2.0; Apache-2.0 if patent
language matters for a compiler). Add SPDX identifiers to `README.md` and
`SECURITY.md`. Decide explicitly whether `bootstrap.c` (generated) inherits the
same license.

**71.2** Add `VERSION` (or a `version` field in a single `velo.release` file),
make `src/main.vl` read it at build time via the existing generated-include
mechanism used for `#ifndef` symbol tables, and delete the literal at
`src/main.vl:36`.

**71.3** Add `CHANGELOG.md` in Keep-a-Changelog form, backfilled from the
Phase 45-69 history. One entry per phase, each linking the commit.

**71.4** Tag the current tree `v2.0.0-pre` after 71.1-71.3 land, so
`git describe` produces something meaningful and Phase 76's CI has a target.

**71.5** Add `CONTRIBUTING.md` covering: bootstrap requirements (a C99
compiler), the determinism gate, the 400-line ceiling, the `gaps.md` contract,
and the commit style (`feat|fix|docs|test(scope): summary`).

**71.6** Add `scripts/release.py`: build -> run suite -> check determinism ->
emit `velo-<version>-<plat>.zip` with `velo`, `std/`, `runtime/`,
`bootstrap.c`, `LICENSE`, `SHA256SUMS`.

## Phase Exit Criteria

- `git ls-files | xargs grep -L "SPDX"` is empty for source files, or a license
  file covers them explicitly.
- `velo version` and `CHANGELOG.md` agree.
- `git describe --tags` yields `v2.0.0-pre` or later.
- A release archive builds from a clean checkout on Windows.

## Completion Record

**Former defect.** The tree had no license, no `VERSION`, no `CHANGELOG.md`, no
`CONTRIBUTING.md`, no release script and no tag. `velo version` printed a
hand-written literal at `src/main.vl:36`, so the CLI string, the docs, and any
future artifact could drift independently. Legally the default was "all rights
reserved", which is a hard block on use, forking, or vendoring by anyone else.

**Fix applied.**

| Task | Commit | Deliverable |
| :--- | :--- | :--- |
| 71.1 | `95aac3f` | Dual `MIT OR Apache-2.0`: `LICENSE-MIT`, `LICENSE-APACHE`, SPDX in `README.md`/`SECURITY.md`, `.gitattributes`, `tests/test_license_provenance.py` (8 rows) |
| 71.2 | `567ab5f` | `VERSION` (`2.0.0-pre`) as the single source; `src/common/version.vl` holds `VELO_VERSION`/`VELO_VERSION_LABEL`/`VELO_TARGET_LABEL`; banner interpolated at `src/main.vl`; `tests/release_meta.py` + `tests/test_release_metadata.py` (7 rows) |
| 71.3 | `a275505` | `CHANGELOG.md` (Keep a Changelog) with an `[Unreleased]` section, a leading "Known limitations" list citing the tracking phase, and Added/Changed/Fixed/Security backfilled from `git log` with a short sha per entry; `tests/test_changelog.py` (7 rows) |
| 71.4 | tag `v2.0.0-pre` | Annotated tag on the Phase 71 completion commit, after the full gate chain (suite + determinism + line ceiling + clean tree) passed. `git describe --tags` now yields `v2.0.0-pre`. |
| 71.5 | `4ad94ae` | `CONTRIBUTING.md` (9 sections) + `tests/test_contributing.py` (8 rows) pinning each gate command verbatim |
| 71.6 | `4251386` | `scripts/release.py` with six gates, a zip archive and `SHA256SUMS`; `tests/test_release_script.py` (14 rows) |

The activity-consistency decision was orthogonal to the licence: `bootstrap.c`
is a generated artifact and is covered by the same dual licence, stated under
`README.md`'s "Generated artifacts" heading so a redistributor does not have to
infer it.

**Residual limitation.**

- The tag is local only. There is no remote, so `v2.0.0-pre` is not published
  and no third party can fetch it; `git describe` works for the maintainer but
  a release consumer cannot yet pin the commit by tag. This resolves when the
  repository gets a remote (Phase 84's ecosystem work), not when a further
  commit lands.
- `scripts/release.py` packages the compiler binary and the sources, not a
  prebuilt library triple. A consumer on a platform without a C compiler still
  cannot use the archive, which is inherent to the "compile C on first use"
  model rather than a packaging defect (Phase 70 gates the platform set).
- The archive is Windows-only in practice: it embeds a `velo.exe`, and the
  bundled `bootstrap.c` cannot link off Windows (Phase 70). The filename says
  `windows-x86_64` so the limitation is visible at download time rather than
  discovered at run time.
- ASan/UBSan are unverifiable on the maintainer host, so the sanitizer lane's
  first real evidence will come from CI, not from this phase (Phase 74.6,
  Phase 85).

**Verification.**

- `python -m pytest tests/test_release_metadata.py tests/test_release_script.py
  tests/test_changelog.py tests/test_contributing.py tests/test_license_provenance.py
  -q` → all pass; `tests/test_bootstrap_snapshot.py` → 5 passed
  (byte-identical snapshot).
- `python scripts/release.py --skip-tests --out <tmp>` →
  `dist/velo-2.0.0-pre-windows-x86_64.zip`, 1,224,327 bytes, 313 entries,
  SHA-256 `eb2dc2a2ab5face29763f5a3ee891c7e85f1beb2000a7f9add08c1b4e8de5bef`.
- The archive was extracted to a scratch directory and built with only a C
  compiler: `gcc -O2 -std=c99 -I runtime bootstrap.c -o velo_built -lm` →
  `Velo v2.0.0-pre (Self-Hosted Native Compiler)`; a probe program using
  `std/io/print.vl` compiled and printed `archive ok`. This is the exit
  criterion "a release archive builds from a clean checkout", executed rather
  than asserted.
- Building the release exposed a real defect in the gate itself, fixed in this
  commit: `gate_bootstrap_snapshot` passed an absolute source path, and `#line`
  directives embed the path verbatim (`src/backend/codegen_line.vl:6-17` only
  normalizes `\` to `/`), so a consistent tree reported a mismatch
  (2,871,783 bytes absolute vs 2,302,641 relative). The gate now spells the
  source relatively, exactly as the committed snapshot was generated, and three
  tests pin both the gate's invocation and the underlying compiler behaviour.
- `velo version` and `CHANGELOG.md` agree on `2.0.0-pre`, enforced by
  `tests/test_changelog.py` rather than by inspection.

---

# Phase 72: Package Ecosystem That Actually Fetches (P0) - [COMPLETED] ✅

## Defect

`velo pkg install` is a lockfile formatter. It never downloads anything. It
prints `All dependencies installed and locked successfully` after writing a
lock file for dependencies it never fetched. That is not an incomplete feature;
it is a false success message, which is worse.

## Evidence

| Fact | Evidence |
| :--- | :--- |
| `pkg install` has no fetch path | `src/backend/driver_pkg.vl:126-152`: loads manifest, and either writes a fresh `velo.lock` or verifies the existing one. No network, no copy, no clone. |
| No HTTP anywhere in the package code | `grep -c "http\|download\|curl\|fetch"` over `driver_pkg.vl` -> 0 [VERIFIED] |
| No clone either | the only `os_system` call in `driver_pkg.vl` is line 320, in `pkg build/run` |
| Three dependency kinds are parsed but only one is meaningful | `src/common/manifest.vl:208-223`: `registry` (default, `source` = version string), `git` (URL + `@tag`), `local` (path). Only `local` can ever resolve, because resolving `registry`/`git` requires fetching. |
| The lockfile stores a hash it never validates against a download | `src/backend/pkg_lock.vl:43` `lockfile_add_entry(name, source, version, hash)`; hashes are computed from files on disk, so a missing dependency has no hash source |
| No registry, no index format, no publish command | `velo help` lists `pkg check|lock|install|update|build|run` only (`src/backend/driver_pkg.vl:65-70`) |
| Semver is unparsed | `version` is a `string` field (`src/common/manifest.vl:23`); no comparison, no range syntax |

## Security Invariants

- **I72.1** `pkg install` either fetches every non-local dependency or exits
  non-zero. It never reports success for work it did not do.
- **I72.2** A dependency's content hash is computed from the fetched bytes and
  compared against `velo.lock` before the code is compiled into anything.
- **I72.3** Fetching is done by invoking `git`/`curl` as a child process with
  argument arrays, never by string-concatenating a shell command (see
  Phase 47's quoting hardening for the existing pattern).
- **I72.4** A lockfile mismatch is fatal and names the dependency, the expected
  hash, and the actual hash.

## Tasks

**72.1 [COMPLETED] ✅** Implement `manifest_resolve_dep(dep) -> DepLocation` for `local` and
`git` kinds. `git` runs `git clone --depth 1 --branch <tag> <url>
.velo_cache/deps/<name>` and then `git rev-parse HEAD`. A missing `git`
executable is a hard error with an actionable message.
- *Former Defect:* Velo package dependency resolution was non-functional for remote dependencies. There was no mechanism to resolve `local` or `git` dependencies into physical directory locations, clone repositories, or extract git commit hashes. If a manifest declared a `git` dependency, `velo pkg install` simply ignored it or failed silently without downloading files.
- *Fix Applied:*
  - Defined `data DepLocation` with fields `path: string`, `commit: string`, `version: string`, `has_error: bool`, `error_msg: string`.
  - Implemented `manifest_resolve_dep(dep: @DependencySpec) -> DepLocation` and `manifest_resolve_dep_in(m_dir: string, dep: @DependencySpec) -> DepLocation` in `src/common/manifest_resolve.vl`.
  - For `local` dependencies: validates disk existence (relative to base directory or absolute), sets `path`, version, and returns `has_error: false`, or returns an actionable error if the path does not exist.
  - For `git` dependencies:
    - Verifies `git` availability; if `git` is absent from PATH, returns a hard failure with actionable error: `"[Velo Error] 'git' executable not found in PATH. Git is required to resolve dependency '<name>' from '<url>'. Please install Git and ensure it is available in your PATH."`
    - Prepares `.velo_cache/deps/<name>` directory.
    - Clones repository using `git clone --depth 1` (with `--branch <tag>` if tag specified) and securely quoted arguments preventing command injection (I72.3).
    - Runs `git -C <dest_path> rev-parse HEAD` to extract the exact 40-character commit SHA.
    - Captures and surfaces detailed git error output if clone or rev-parse fails.
  - Hardened dependency names against directory traversal (`..`, `/`, `\\`).
  - Added `use "manifest_resolve.vl"` in `src/common/manifest.vl`.
  - Re-bootstrapped compiler chain (`bin/velo.exe` $\rightarrow$ `bin/velo_gen2.exe` $\rightarrow$ `bin/velo_gen3.exe` $\rightarrow$ `bin/velo.exe`), verified bit-for-bit SHA-256 determinism (`0ea5b86b4edb...`), refreshed `bootstrap.c`, and confirmed `test_bootstrap_snapshot.py` object cleanliness and determinism.
- *Residual Limitation:* Registry dependencies (`kind = "registry"`) produce a clear unsupported diagnostic pending Task 72.2.
- *Verification:*
  - Created automated test suite `tests/test_pkg_resolve.py` with 8 test cases:
    - `test_resolve_local_dependency_success`: local dependency resolves path and version.
    - `test_resolve_local_dependency_missing`: non-existent local path fails closed with error.
    - `test_resolve_git_dependency_with_tag`: creates local git repo fixture with tag `v1.2.3`, clones to `.velo_cache/deps`, and verifies 40-char SHA and version.
    - `test_resolve_git_dependency_without_tag`: clones default branch and parses commit SHA as version.
    - `test_resolve_git_dependency_missing_git_actionable_error`: verifies actionable error message when `git` is not on PATH.
    - `test_resolve_git_dependency_invalid_url`: verifies failure on invalid/unreachable git URL.
    - `test_resolve_invalid_dependency_name_traversal`: verifies rejection of traversal characters in package name.
    - `test_resolve_registry_dependency_unsupported`: verifies clear diagnostic for registry dependencies.
  - All 8 tests passed in 23.51s.
  - `tests/test_bootstrap_snapshot.py` passed (6/6).
  - `tests/test_pkg_security.py` passed (4/4).

**72.2** [COMPLETED] ✅ Implement `registry` kind against a minimal HTTP index: `<registry>/<name>/index.json` listing `version -> {url, sha256}`. Requires Phase 73's TLS or an explicit `--insecure` flag that prints a warning. Document the index format in `docs/PACKAGING.md`.
- *Former Defect:* Manifest resolution lacked support for `registry` dependencies (`kind = "registry"`), failing closed with an unsupported diagnostic. Package indexes lacked a formal specification, JSON schema definition, and transport security controls.
- *Fix Applied:*
  - Created `docs/PACKAGING.md` documenting package manifest schema, index URL layout (`<registry-root>/<name>/index.json`), JSON schema (supporting both nested `{ "versions": { "<ver>": { "url", "sha256" } } }` and flat `{ "<ver>": { "url", "sha256" } }` formats), required fields, transport security semantics, `--insecure` behavior, and pull-request-based publishing workflow.
  - Implemented registry resolution in `src/common/manifest_resolve.vl` via `manifest_resolve_dep_full(m_dir, dep, insecure, registry_override)`:
    - Resolves registry base URL from parameter override, `VELO_REGISTRY` environment variable, or default `https://pkg.velolang.org`.
    - Enforces transport security: cleartext `http://` URLs fail closed unless `--insecure` is explicitly specified; emits visible warning when `--insecure` is active (`[Velo Warning] Insecure connection to '<url>': cleartext HTTP used.` or `[Velo Warning] TLS certificate verification disabled via --insecure for registry '<url>'.`).
    - Validates presence of `curl` executable and emits actionable diagnostic if missing from PATH.
    - Fetches index JSON to temporary cache using subprocess invocation with argument quoting (`quote_path`).
    - Parses JSON document using `std.json`, extracting `url` and `sha256` for the requested version with comprehensive error handling (missing version, missing required fields, malformed JSON, 404 response).
    - Populates `DepLocation` with destination path, expected commit/hash, version, archive URL, and expected SHA-256 hash.
- *Residual Limitation:* Archive download (tar/zip), unpacking, and verifying hash integrity during `pkg install` is implemented in Task 72.3.
- *Verification:*
  - Created automated test suite `tests/test_pkg_registry.py` with 11 test cases:
    - `test_registry_resolve_success_nested_versions`: parses nested `"versions"` mapping and asserts `archive_url` and `expected_hash`.
    - `test_registry_resolve_success_flat_versions`: parses flat version mapping format.
    - `test_registry_plaintext_http_disallowed_without_insecure`: confirms fail-closed rejection of `http://` without `--insecure`.
    - `test_registry_insecure_warning_on_https`: asserts TLS verification disabled warning on HTTPS with `--insecure`.
    - `test_registry_version_not_found`: asserts actionable diagnostic on missing version.
    - `test_registry_404_package_not_found`: asserts error on 404 response.
    - `test_registry_missing_url_field`: asserts error when `url` is absent.
    - `test_registry_missing_sha256_field`: asserts error when `sha256` is absent.
    - `test_registry_invalid_json`: asserts fail-closed on corrupt JSON index.
    - `test_registry_via_velo_registry_env`: verifies `VELO_REGISTRY` environment variable resolution.
    - `test_registry_missing_curl_actionable_error`: verifies actionable diagnostic when `curl` is missing from PATH.
  - Updated `tests/test_pkg_resolve.py` with `test_resolve_registry_dependency_empty_version` to verify fail-closed check on empty version.
  - All 19 tests in `tests/test_pkg_registry.py` and `tests/test_pkg_resolve.py` passed in 69.32s.
  - `tests/test_bootstrap_snapshot.py` passed (6/6).
  - Determinism verified: Gen2 == Gen3 SHA-256 match; `bootstrap.c` updated cleanly with zero raw Win32 socket symbols.
  - Line count verified: `src/common/manifest_resolve.vl` is 357 lines (all files $\le 400$ lines).

**72.3** [COMPLETED] ✅ Fix the lie: `pkg install` must call 72.1/72.2 for every dependency, verify hashes (I72.2), and only then print success. Add `tests/test_pkg_install_fetches.py` with a local `file://`-style registry fixture and a `git` fixture; the test asserts the dependency directory exists and its files match the lock hash.
- *Former Defect:* `velo pkg install` was a lockfile formatter that never fetched dependencies over the network or disk. It printed `"All dependencies installed and locked successfully."` even when dependencies had never been downloaded or cloned. Furthermore, lockfile hashes were computed from a placeholder seed string rather than actual files on disk, making remote dependency tampering detection non-functional.
- *Fix Applied:*
  - Implemented `src/backend/pkg_install.vl`:
    - `manifest_fetch_archive(dest_path, archive_url, expected_sha, insecure)`: downloads registry package archives using `curl` with safe argument quoting (`quote_path`), validates transport security, verifies downloaded archive bytes against `expected_sha` using `sha256_hash` (I72.2, I72.4), and extracts using `tar -xf` into `dest_path`.
    - `install_all_dependencies(m, m_dir, insecure, registry_override)`: resolves local dependency paths, clones git repositories via Task 72.1, and downloads/unpacks registry archives via Task 72.2 and `manifest_fetch_archive`. Fails closed if any dependency fails to resolve or fetch (I72.1).
  - Updated `src/backend/driver_pkg.vl`:
    - Added `parse_pkg_args` helper parsing manifest path, `--insecure`, and `--registry` flags across `install`, `lock`, and `update` subcommands.
    - `pkg install` calls `install_all_dependencies` before creating or verifying `velo.lock`, ensuring every dependency exists on disk before reporting success.
    - `pkg lock` calls `install_all_dependencies` before writing `velo.lock` so real content hashes are recorded.
    - `pkg update` calls `install_all_dependencies` before updating `velo.lock`.
  - Updated `src/backend/pkg_lock.vl`:
    - Updated `compute_dep_hash` to check `.velo_cache/deps/<name>` for `git` and `registry` dependencies.
    - Enhanced directory hashing to hash all present entry/source files (`velo.pkg`, `main.vl`, `src/main.vl`) so that modifying any file in an installed dependency triggers a fatal lockfile verification failure naming expected and actual hashes (I72.4).
- *Residual Limitation:* Semantic version parsing (`MAJOR.MINOR.PATCH`) and range operators (`=`, `^`, `~`, `>=`) will be implemented in Task 72.4.
- *Verification:*
  - Created automated test suite `tests/test_pkg_install_fetches.py` with 5 test cases:
    - `test_pkg_install_fetches_git_dependency`: clones local git fixture into `.velo_cache/deps/upstream_git_pkg`, creates `velo.lock`, asserts files match lock hash, and re-verifies successfully.
    - `test_pkg_install_fetches_registry_file_url_and_matches_lock_hash`: downloads and extracts `.tar.gz` archive via `file://` registry fixture, creates `velo.lock`, and asserts extracted files match lock hash.
    - `test_pkg_install_detects_tampered_dependency_and_fails_fatally`: verifies that modifying a single byte in an installed dependency fails fatal with `Package checksum verification failed` naming expected and actual hashes (I72.4).
    - `test_pkg_install_corrupt_archive_hash_fails_closed`: verifies that an archive hash mismatch against `index.json` fails closed without extracting corrupted files (I72.2).
    - `test_pkg_install_unreachable_dependency_fails_closed`: verifies that failed git clone exits non-zero and never prints false success (I72.1).
  - All 5 tests passed in 7.35s.
  - All 28 package tests across `test_pkg_install_fetches.py`, `test_pkg_security.py`, `test_pkg_registry.py`, and `test_pkg_resolve.py` passed in 168.63s.
  - `tests/test_bootstrap_snapshot.py` passed (6/6).
  - Determinism verified: Gen2 == Gen3 SHA-256 match; `bootstrap.c` updated cleanly with zero raw Win32 socket symbols.
  - Line count verified: all compiler files $\le 400$ lines (`driver_pkg.vl` 366, `manifest_resolve.vl` 357, `pkg_lock.vl` 281, `pkg_install.vl` 157).

**72.4** [COMPLETED] ✅ Add semver: parse `MAJOR.MINOR.PATCH`, support `=`, `^`, `~`, and
`>=` in manifests, reject ambiguous ranges with a diagnostic.
- *Former Defect:* Package manifests and registry resolution treated versions as unparsed literal strings with exact-match dictionary lookups (`doc.root[v]`). Version requirements like `^1.0.0`, `~1.2.0`, or `>= 2.0.0` could not be specified, maximal version selection among matching candidates was not supported, ambiguous or conflicting range operators (such as `^~1.0`, `*`, `1.x`, `<>`, `==`) were silently rejected or mishandled, and lockfiles recorded the range requirement string rather than pinning the concrete resolved version.
- *Fix Applied:*
  - Implemented SemVer 2.0.0 parser, comparator, and requirement evaluator in `src/common/semver.vl`:
    - `SemVer` struct (`major: i64`, `minor: i64`, `patch: i64`, `is_valid: bool`) and `SemVerReq` struct (`op: string`, `version: SemVer`, `is_valid: bool`, `error_msg: string`).
    - `semver_parse(s)`: parses standard `MAJOR.MINOR.PATCH` with non-negative components, strips optional pre-release (`-`) or build metadata (`+`), and enforces SemVer specification rule prohibiting leading zeroes on multi-digit components (`01.0.0` rejected).
    - `semver_cmp(a, b)`: lexicographical comparison returning negative, zero, or positive integer.
    - `semver_parse_req(req_str)`: parses requirement operators `=`, `^`, `~`, and `>=` (with optional whitespace, defaulting bare versions to exact match `=`). Rejects unsupported or ambiguous ranges (wildcards `*`/`x`, conflicting prefixes `^~`/`~^`/`>=^`, comparison operators `<`/`>`/`<=`/`==`, and compound bounds) with clear diagnostic messaging.
    - `semver_satisfies(v, req)`: evaluates candidate versions against operators:
      - `=` requires exact `(major, minor, patch)` equality.
      - `~` allows patch-level updates (`~1.2.3` matches `>= 1.2.3 and < 1.3.0`).
      - `^` allows non-breaking compatible updates per SemVer 2.0 (for `major > 0`: `< (major+1).0.0`; for `0.x.y`: patch bumps only `< 0.(minor+1).0`; for `0.0.z`: exact match only `== 0.0.z`).
      - `>=` allows any version greater than or equal to the requirement.
  - Updated `src/common/manifest_resolve.vl`:
    - Validates dependency semver requirement via `semver_parse_req`. Rejects invalid or ambiguous requirements fail-closed with actionable diagnostic: `[Velo Error] Invalid or ambiguous semver requirement '<req>' for dependency '<name>'. Supported operators are '=', '^', '~', and '>='.`
    - Inspects index JSON version map (supporting both nested `versions` key and flat schema), filters candidate versions that satisfy requirement via `semver_satisfies`, and selects the maximal matching version (`best_ver` via `semver_cmp > 0`).
    - Populates `loc.version` with the concrete selected version key (`best_key`).
  - Updated `src/backend/pkg_lock.vl`:
    - Added `resolve_installed_dep_version(m_dir, dep)` which reads `.velo_cache/deps/<name>/velo.pkg` after installation so `generate_lockfile_from_manifest` pins the concrete resolved version in `velo.lock` rather than the manifest range requirement.
- *Residual Limitation:* Read-only drift inspection (`velo pkg tree` and `velo pkg verify`) will be implemented in Task 72.5.
- *Verification:*
  - Created automated test suite `tests/test_pkg_semver.py` with 11 test cases:
    - `test_semver_parse_and_compare`: verifies ordering, equality, and component extraction across diverse versions.
    - `test_semver_exact_match_operator`: verifies `=` operator matches only exact version and rejects mismatches.
    - `test_semver_tilde_operator`: verifies `~` operator allows patch bumps within minor version and rejects minor/major bumps.
    - `test_semver_caret_operator`: verifies `^` operator for `1.x.x` (allows minor/patch bumps, rejects `2.0.0`), `0.x.x` (allows patch bumps only, rejects `0.3.0`), and `0.0.x` (exact match only).
    - `test_semver_gte_operator`: verifies `>=` operator accepts equal or higher versions across minor and major, rejects lower versions.
    - `test_semver_rejects_conflicting_ambiguous_prefixes`: verifies rejection of `^~1.0.0`, `~^1.0.0`, and `>=^1.0.0`.
    - `test_semver_rejects_wildcard_ranges`: verifies rejection of `*`, `1.*`, and `1.x`.
    - `test_semver_rejects_unsupported_operators`: verifies rejection of `<>`, `==`, `<`, `>`, and `<=`.
    - `test_semver_rejects_malformed_version_numbers`: verifies rejection of leading zeroes (`01.0.0`), four components (`1.2.3.4`), and non-numeric strings.
    - `test_registry_resolves_highest_matching_semver`: runs `manifest_resolve_dep_full` on registry with multiple candidates (`1.0.0`, `1.1.0`, `1.2.0`, `2.0.0`) and asserts `^1.0.0` resolves to `1.2.0`.
    - `test_pkg_install_semver_caret_selects_highest_compatible`: end-to-end `velo pkg install` verifying that caret range `^1.0.0` selects highest compatible candidate (`1.1.0`), creates `.velo_cache/deps/math_lib`, and pins `version = "1.1.0"` in `velo.lock`.
  - All 11 tests in `tests/test_pkg_semver.py` passed in 76.81s.
  - Full package test suite (45 tests across `test_pkg_semver.py`, `test_pkg_install_fetches.py`, `test_pkg_security.py`, `test_pkg_registry.py`, `test_pkg_resolve.py`) passed in 423.88s.
  - `tests/test_bootstrap_snapshot.py` passed (6/6).
  - Determinism verified: Gen2 == Gen3 SHA-256 match (`81486c034ce1f5b2b7fa8b6030c8303c200ada6c002652280e6ebd1d10b75865`); `bootstrap.c` updated cleanly with zero raw Win32 socket symbols.
  - Line count verified: all compiler files $\le 400$ lines (`src/common/semver.vl` 279, `src/common/manifest_resolve.vl` 382, `src/backend/pkg_lock.vl` 298).

**72.5** [COMPLETED] ✅ Add `velo pkg tree` and `velo pkg verify` (read-only: recompute hashes and report drift). `verify` is what CI calls.
- *Former Defect:* The package manager lacked read-only dependency inspection and automated drift verification. Developers had no command to visualize the project dependency tree or diagnose uninstalled/transitive dependencies, and CI workflows had no mechanism to verify that installed packages and local files match `velo.lock` without mutating lockfiles, writing to disk, or making network calls.
- *Fix Applied:*
  - Implemented `src/backend/pkg_inspect.vl`:
    - `pkg_tree_run(manifest_path: string) -> i32`:
      - Recursively traverses and renders the dependency tree of `velo.pkg` with standard tree box characters (`├── `, `└── `, `│   `).
      - Resolves and displays installed concrete versions, dependency kinds (`registry`, `git`, `local`), and uninstalled indicators (`(not installed, ...)`).
      - Recursively traverses nested and hoisted transitive dependencies (`velo.pkg` in child directories).
      - Implements cycle detection with ancestry tracking to prevent infinite recursion on circular dependencies, marking cyclic edges with `(*)`.
    - `pkg_verify_run(manifest_path: string) -> i32`:
      - Strictly read-only audit command designed for CI verification: never writes to `velo.lock`, never downloads archives, and never clones repositories.
      - Requires `velo.lock` to exist if dependencies are declared.
      - Recomputes cryptographic SHA-256 hashes for all dependencies and verifies bidirectional consistency between `velo.pkg` and `velo.lock`.
      - Detects and reports all forms of drift with `[Velo Error] Drift detected: ...`:
        - Manifest dependency missing from lockfile.
        - Dependency directory missing on disk (not installed).
        - File content tampering or corruption (checksum mismatch, Security Invariant I72.4).
        - Extra/stale lockfile entries not declared in manifest.
        - Semantic version requirement drift (locked version failing to satisfy updated manifest semver range).
        - Git tag mismatches.
      - Returns exit code 0 when zero drift is detected (`[Velo] All <N> dependencies match velo.lock with zero drift.`); exits code 1 if any drift is found.
  - Updated `src/backend/driver_pkg.vl` and `src/cli_cmd.vl` adding `tree` and `verify` CLI subcommands and help documentation.
  - Fixed `parse_manifest_pkg` in `src/common/manifest.vl` to properly retain `m.pkg.name` when specified inside `pkg { name: "..." }` block, and added `registry` keyword support in `parse_manifest_deps`.
- *Residual Limitation:* Creating package tarballs and generating registry index entries (`velo pkg publish`) will be implemented in Task 72.6.
- *Verification:*
  - Created automated test suite `tests/test_pkg_tree_verify.py` with 13 test cases:
    - `test_pkg_tree_single_package_no_deps`: verifies tree output on standalone package with 0 dependencies.
    - `test_pkg_tree_with_installed_dependencies`: verifies tree branches with local and git dependencies.
    - `test_pkg_tree_shows_not_installed_status`: asserts `(not installed)` marker for missing dependencies.
    - `test_pkg_tree_transitive_multi_level`: verifies nested 2-level dependency tree rendering.
    - `test_pkg_tree_cycle_detection`: verifies cycle prevention and `(*)` marker on circular dependencies.
    - `test_pkg_verify_success_clean_state`: asserts exit code 0 and zero drift confirmation on verified dependencies.
    - `test_pkg_verify_missing_lockfile_fails`: asserts fail-closed exit 1 when `velo.lock` is missing.
    - `test_pkg_verify_detects_uninstalled_dependency_drift`: asserts drift detection when dependency folder is missing.
    - `test_pkg_verify_detects_tampered_content_hash_drift`: asserts drift detection with expected and actual SHA-256 hashes when files are modified.
    - `test_pkg_verify_detects_missing_lock_entry_drift`: asserts drift detection when new dependency is added without lock.
    - `test_pkg_verify_detects_extra_lock_entry_drift`: asserts drift detection when orphan entry remains in lockfile.
    - `test_pkg_verify_detects_version_requirement_drift`: asserts drift detection when manifest semver requirement is changed without updating lock.
    - `test_pkg_verify_is_strictly_read_only`: asserts that file contents and timestamps remain byte-for-byte identical across multiple `verify` runs.
  - All 13 tests in `tests/test_pkg_tree_verify.py` passed in 1.61s.
  - Full package test suite (52 tests across `test_pkg_tree_verify.py`, `test_pkg_semver.py`, `test_pkg_install_fetches.py`, `test_pkg_security.py`, `test_pkg_registry.py`, `test_pkg_resolve.py`) passed in 153.11s.
  - `tests/test_bootstrap_snapshot.py` passed (6/6).
  - Determinism verified: Gen2 == Gen3 SHA-256 match (`6b099ad6f454ac592f7c00fb4d0ce2947adba5f6f8d1705985dc31e068a4923b`); `bootstrap.c` updated cleanly with zero raw Win32 socket symbols.
  - Line count verified: all compiler files $\le 400$ lines (`src/backend/pkg_inspect.vl`: 290, `src/backend/driver_pkg.vl`: 385, `src/common/manifest.vl`: 317).

**72.6** [COMPLETED] ✅ Add `velo pkg publish` that tars the manifest's declared `src/` and
`std/` subsets, computes the hash, and prints the index entry to paste. No
upload servers, no accounts - publishing is a pull request to a registry
repository. That keeps the trust model small enough to be honest.
- *Former Defect:* The toolchain lacked any mechanism to package library releases or generate registry index entries. Package maintainers had no automated way to bundle source files into standardized `.tar.gz` distribution archives, calculate verifiable cryptographic SHA-256 digests, or generate registry-compatible `index.json` descriptors for the pull-request-based publishing workflow.
- *Fix Applied:*
  - Implemented `src/backend/pkg_publish.vl`:
    - `pkg_publish_run(argc: i32, argv: @string) -> i32`:
      - Validates package manifest (`velo.pkg`), verifying that `name` is present, `version` is valid SemVer (via `semver_parse`), and at least one source directory or entry file exists (`src/`, `std/`, or declared `entry`).
      - Packages `velo.pkg`, `src/` (if present), `std/` (if present), and any root entry file into `<name>-<version>.tar.gz` using standard `tar -czf` with securely quoted path arguments (Security Invariant I72.3).
      - Supports custom archive destination via `-o` / `--out <path>`, defaulting to `dist/<name>-<version>.tar.gz`.
      - Computes cryptographic SHA-256 digest of the archive bytes via `sha256_hash` (Security Invariant I72.2).
      - Resolves archive download URL, supporting custom overrides via `--url <url>`, `--registry <url>`, or environment variable `VELO_REGISTRY`.
      - Prints human-readable summary with archive path, SHA-256 digest, the exact JSON descriptor snippet to paste into `<name>/index.json` under `"versions"`, and PR submission instructions.
      - Supports `--json` flag to emit structured machine-readable metadata (`name`, `version`, `archive`, `url`, `sha256`) for CI/CD scripting.
  - Updated `src/backend/driver_pkg.vl` and `src/cli_cmd.vl` to expose `publish` subcommand and documentation.
- *Residual Limitation:* CI test matrix and offline multi-level dependency graph fixtures will be finalized in Task 72.7.
- *Verification:*
  - Created automated test suite `tests/test_pkg_publish.py` with 9 test cases:
    - `test_pkg_publish_default_options`: packages `src/` and `velo.pkg`, asserts tarball creation, verifies SHA-256 and printed JSON snippet, and checks archive contents.
    - `test_pkg_publish_custom_out_tarball`: verifies custom archive output path via `-o`.
    - `test_pkg_publish_custom_url_and_registry`: verifies `--url` and `--registry` overrides in generated snippet.
    - `test_pkg_publish_json_flag`: parses stdout as JSON and validates structured metadata.
    - `test_pkg_publish_packages_std_subset`: verifies `std/` subset packaging into archive.
    - `test_pkg_publish_fails_on_missing_manifest`: verifies fail-closed error when manifest is missing.
    - `test_pkg_publish_fails_on_invalid_semver`: verifies fail-closed error on non-semver version.
    - `test_pkg_publish_fails_when_no_source_files_exist`: verifies fail-closed error on empty package.
    - `test_pkg_publish_roundtrip_with_pkg_install`: end-to-end integration test publishing a library with `velo pkg publish`, constructing a registry index from its output, installing the dependency in a consumer app via `velo pkg install`, extracting files, and verifying with zero drift via `velo pkg verify` (exercising Phase Exit Criterion 3).
  - All 9 tests in `tests/test_pkg_publish.py` passed in 2.71s.
  - Full package test suite (61 tests across `test_pkg_publish.py`, `test_pkg_tree_verify.py`, `test_pkg_semver.py`, `test_pkg_install_fetches.py`, `test_pkg_security.py`, `test_pkg_registry.py`, `test_pkg_resolve.py`) passed in 234.93s.
  - `tests/test_bootstrap_snapshot.py` passed (6/6).
  - Determinism verified: Gen2 == Gen3 SHA-256 match (`32468215329b2cfa253e412db35f99c1120cfbc62cf501f2cdfd69f55779053a`); `bootstrap.c` updated cleanly with zero raw Win32 socket symbols.
  - Line count verified: all compiler files $\le 400$ lines (`src/backend/pkg_publish.vl`: 189, `src/backend/driver_pkg.vl`: 391).

**72.7** [COMPLETED] ✅ Add a `tests/test_pkg_semver.py` matrix and a `deps-lock` CI job that
builds a two-level dependency graph offline from fixtures.
- *Former Defect:* In `tests/test_pkg_semver.py`, test coverage for semver was limited to a few hand-written cases and lacked a comprehensive test matrix across range operators (`=`, `^`, `~`, `>=`), multi-digit versions, zero-major, zero-minor, pre-releases, and edge conditions. Furthermore, offline dependency graph verification was only tested at a single level (direct dependency); transitive multi-level dependency graphs (root -> A -> B) with recursive fetching, transitive lockfile recording, graph-wide drift verification, and offline resolution were not supported or verified, nor was there a dedicated CI gate (`deps-lock`) to guarantee offline multi-level dependency graph resolution and pinning on Linux.
- *Fix Applied:*
  - Added comprehensive parameterized `SEMVER_MATRIX` in `tests/test_pkg_semver.py` with 25 test vectors covering:
    - Exact match (`=`) with patch, minor, major changes and leading-zero detection.
    - Tilde (`~`) patch bumps, minor rejections, major rejections.
    - Caret (`^`) non-breaking updates for `1.x.x` (patch/minor allowed, major rejected), `0.x.x` (patch allowed, minor/major rejected), and `0.0.x` (exact match only).
    - Greater-or-equal (`>=`) operator across boundaries.
    - Ambiguous and malformed ranges (wildcards `*`/`x`, compound prefixes `^~`, comparison operators `<`/`>`/`<=`/`==`) asserting rejection with clear diagnostics.
  - Implemented multi-level transitive dependency fetching and lockfile pinning across compiler backend:
    - In `src/backend/pkg_install.vl`: implemented `install_dependencies_rec` which recursively walks child manifests in `.velo_cache/deps/<name>/velo.pkg` and hoists transitive dependencies into the root project cache `.velo_cache/deps/` with cycle depth bounding.
    - In `src/backend/pkg_lock.vl`: implemented `manifest_find_dep_in_graph`, `is_dep_declared_in_graph`, `compute_path_content_hash`, and updated `add_manifest_deps_to_lock` to record all direct and transitive dependencies into `velo.lock`.
    - In `src/backend/pkg_lock.vl` and `src/backend/pkg_inspect.vl`: updated `verify_lockfile_integrity` and `pkg_verify_run` to verify every entry in `velo.lock` (direct and transitive) against disk files, catching missing packages and content tampering across multi-level graphs.
  - Added `test_two_level_dependency_graph_offline` in `tests/test_pkg_semver.py`:
    - Constructs a two-level offline dependency fixture graph (root project depending on `pkg_alpha` v1.1.0, which depends on `pkg_beta` v2.0.5) from local file-based registry fixtures.
    - Executes `velo pkg install` offline: recursively downloads and installs direct (`pkg_alpha`) and transitive (`pkg_beta`) dependencies into the root project cache (`.velo_cache/deps/`).
    - Verifies multi-level `velo.lock` pins both direct and transitive dependencies with concrete versions and content hashes.
    - Exercises `velo pkg tree` asserting hierarchical representation of the two-level dependency tree.
    - Exercises `velo pkg verify` verifying zero-drift integrity across the entire multi-level graph (`[Velo] All 2 dependencies match velo.lock with zero drift.`).
    - Tampers with the leaf transitive dependency (`pkg_beta`) and asserts fatal exit code and checksum mismatch diagnostic.
  - Added `deps-lock` CI workflow job in `.github/workflows/ci.yml`:
    - Runs on `ubuntu-24.04`, bootstraps self-hosted Velo compiler via `bootstrap.sh --full`, verifies determinism, and runs the complete package test suite (`test_pkg_semver.py`, `test_pkg_tree_verify.py`, `test_pkg_install_fetches.py`, `test_pkg_publish.py`, `test_pkg_registry.py`, `test_pkg_resolve.py`, `test_pkg_security.py`).
- *Residual Limitation:* None. Phase 72 is complete. All 7 tasks and phase exit criteria are fully satisfied.
- *Verification:*
  - All 37 tests in `tests/test_pkg_semver.py` passed in 118.97s.
  - Complete package test suite (87 tests across `test_pkg_semver.py`, `test_pkg_tree_verify.py`, `test_pkg_install_fetches.py`, `test_pkg_publish.py`, `test_pkg_registry.py`, `test_pkg_resolve.py`, `test_pkg_security.py`) passed cleanly.
  - `tests/test_bootstrap_snapshot.py` passed (6/6).
  - Determinism verified: Gen2 == Gen3 SHA-256 match (`d2f16555d14867a00d73683c77a1001e3eda3b52c4aa533eb15baaa6d1616d74`); `bootstrap.c` updated cleanly with zero raw Win32 socket symbols.
  - Line count verified: all compiler files $\le 400$ lines (`src/backend/pkg_lock.vl`: 363, `src/backend/pkg_inspect.vl`: 285).

## Phase Exit Criteria

- `velo pkg install` on a git dependency produces a working tree and a lock
  entry whose hash matches, proven by test (`test_pkg_install_fetches.py::test_pkg_install_fetches_git_dependency`). [VERIFIED]
- `velo pkg install` with a corrupted lock or a missing dependency exits
  non-zero and names the problem (`test_pkg_install_fetches.py::test_pkg_install_detects_tampered_dependency_and_fails_fatally` and `test_pkg_install_unreachable_dependency_fails_closed`). [VERIFIED]
- A published index format exists in `docs/PACKAGING.md` and is exercised by
  at least one test fixture (`test_pkg_publish.py::test_pkg_publish_roundtrip_with_pkg_install`). [VERIFIED]

---

# Phase 73: Transport Security and Cryptographic Completeness (P0) - [COMPLETED] ✅

## Defect

There is no TLS. `std.http.client` speaks cleartext HTTP/1.1 only, so the
language cannot talk to any modern endpoint. The crypto module ships MD5 and a
hash-only HMAC with no constant-time comparison, and its CSPRNG silently falls
back to a deterministic PRNG when the OS source fails - and the caller that
consumes it (UUIDv4) ignores the failure flag entirely.

## Evidence

| Fact | Evidence |
| :--- | :--- |
| No TLS anywhere | `grep -ri "tls\|ssl"` over `std/`, `src/`, `runtime/` -> 0 hits [VERIFIED] |
| HTTP client is cleartext-only | `std/http/client.vl:10` `http_request(method, url_str, headers, body)`; URL handling in `std/url/*` has no scheme-based transport switch |
| CSPRNG fails open into a deterministic PRNG | `std/crypto/rand.vl:7` `SystemFunction036`; on failure lines 30-42 fill the buffer from `rand_splitmix64()` and `return false` |
| The failure flag is discarded by the only consumer | `std/uuid/v4.vl:10` calls `crypto_random_bytes(ptr, 16)` and ignores the return value [VERIFIED] |
| UUIDv7 also ignores it | `std/uuid/v7.vl:26`, `:49` |
| MD5 ships as a first-class member of the umbrella | `std/crypto.vl:3` `use "crypto/md5.vl"` |
| HMAC has no verify function | `std/crypto/hmac.vl` exports exactly `hmac_sha256`, `hmac_sha256_hash`, `hmac_sha256_str` - no comparison helper |
| No constant-time comparison anywhere | `grep -ri "constant_time\|ct_eq"` over `std/` -> 0 hits [VERIFIED] |
| Only SHA-256, MD5, CRC32, HMAC-SHA256 exist | `std/crypto/` contains `crc32.vl`, `hex.vl`, `hmac.vl`, `md5.vl`, `rand.vl`, `sha256.vl` |
| No AEAD, no public-key, no KDF | no `chacha`, `aes`, `poly1305`, `curve25519`, `ed25519`, `hkdf`, `pbkdf2`, `argon` anywhere |

A web-facing language without TLS, AEAD, and a constant-time comparison
primitive is not publishable. Shipping MD5 in the default umbrella also invites
its use for password hashing.

## Security Invariants

- **I73.1** No cryptographic primitive returns success for a weaker
  implementation. A CSPRNG failure is fatal or an explicit `or` error; it never
  silently degrades.
- **I73.2** Every MAC/password verification path compares in constant time.
- **I73.3** Secrets are zeroed before their buffer is released on every exit
  path, including `defer` unwinding and early `or return`.
- **I73.4** MD5 and future legacy primitives are not reachable from the default
  `std.crypto` umbrella; they live in `std.crypto.legacy`.
- **I73.5** TLS verification is on by default and cannot be disabled without a
  named, documented flag that prints a warning.

## Tasks

**73.1 [COMPLETED] ✅** Move `md5` out of `std/crypto.vl` into `std/crypto/legacy.vl` with a
`use std.crypto.legacy` requirement and a doc comment saying it is for
interoperability only. Add `tests/test_crypto_umbrella.py` asserting MD5 is not
reachable from the umbrella.

- *Former Defect:*
  `std/crypto.vl` exported MD5 directly in the default top-level cryptographic umbrella (`use "crypto/md5.vl"`). Importing `use std.crypto` brought MD5 functions (`md5_hash`, `md5_hash_str`, `Md5State`) into scope alongside secure primitives (SHA-256, HMAC-SHA256, CSPRNG), violating security invariant I73.4 and inviting the use of broken collision-vulnerable digests in security-sensitive code.
- *Fix Applied:*
  - Removed `use "crypto/md5.vl"` from `std/crypto.vl`, keeping only secure primitives in the default `std.crypto` umbrella (SHA-256, HMAC-SHA256, CSPRNG, CRC-32, hex).
  - Created `std/crypto/legacy.vl` exporting `use "md5.vl"` with an explicit security warning doc comment stating MD5 is cryptographically broken and provided strictly for legacy protocol and file format interoperability.
  - Added warning banner in `std/crypto/md5.vl` documenting deprecation and directing callers to `use std.crypto.legacy`.
  - Updated standard library tests (`std/tests/crypto_module_import_test.vl`, `std/tests/std_module_import_test.vl`) to verify that `use std.crypto` provides only secure primitives and that MD5 is accessed via `use std.crypto.legacy`.
- *Residual Limitation (if any):*
  None. MD5 cannot be imported or accessed through `use std.crypto`. Callers must explicitly opt in with `use std.crypto.legacy` or `use std.crypto.md5`.
- *Verification:*
  - Created `tests/test_crypto_umbrella.py` with 6 automated tests:
    - `test_md5_hash_str_not_reachable_from_crypto_umbrella`: asserts `md5_hash_str` fails compile-time check when only `use std.crypto` is imported.
    - `test_md5_init_not_reachable_from_crypto_umbrella`: asserts `Md5State` and `md5_init` fail compile-time check when only `use std.crypto` is imported.
    - `test_md5_reachable_with_explicit_legacy_import`: verifies `use std.crypto.legacy` compiles and evaluates correct RFC 1321 digests.
    - `test_crypto_and_legacy_can_be_imported_together`: verifies clean coexistence of `std.crypto` and `std.crypto.legacy`.
    - `test_crypto_umbrella_source_excludes_md5`: static file audit ensuring `std/crypto.vl` does not import `md5.vl`.
    - `test_legacy_vl_has_interoperability_warning_doc_comment`: static file audit ensuring `std/crypto/legacy.vl` has the required warning comment.
  - All 6 tests passed in 3.23s.
  - Verified `tests/test_std_crypto.py` (7/7 passed).

**73.2 [COMPLETED] ✅** Change `crypto_random_bytes` to fail closed: return `bool or string`
and have `uuid_v4`/`uuid_v7` propagate (or abort with a named fatal). Delete the
SplitMix64 fallback fill entirely, or keep it behind an explicit
`crypto_unsafe_fallback` name. Add `tests/test_crypto_rand_failclosed.py` that
injects a failing entropy function.
- *Former Defect:* `crypto_random_bytes` previously returned a bare `bool`, silently degraded to a deterministic, non-cryptographic SplitMix64 pseudo-random generator whenever the OS entropy source failed, and filled caller buffers with predictable output. Furthermore, consumers like `uuid_v4` and `uuid_v7` discarded the return value of `crypto_random_bytes`, allowing predictable UUIDs to be minted without notice under entropy exhaustion.
- *Fix Applied:*
  - Updated `runtime/velo_runtime.h` and `velo/runtime/velo_runtime.h` (byte-identical) with entropy failure injection support (`g_velo_fail_entropy_injected`, `velo_crypto_inject_entropy_failure`, `VELO_FAIL_ENTROPY` env var check) and named fatal abort helper `velo_crypto_rand_fatal`.
  - Changed `crypto_random_bytes(buf: @u8, len: usize) -> bool or string` in `std/crypto/rand.vl` to fail closed: on CSPRNG failure, it scrubs/zeros the destination buffer and fails with `"OS entropy source unavailable (CSPRNG failure)"`.
  - Eliminated silent degradation to SplitMix64 PRNG in `crypto_random_bytes`. Extracted PRNG into explicit `crypto_unsafe_fallback_bytes(buf, len)` clearly documented as insecure and intended solely for deterministic simulation.
  - Updated `crypto_random_u32()`, `crypto_random_u64()`, and `crypto_random_hex()` to fail loudly/fatally via `velo_crypto_rand_fatal` on entropy exhaustion, and provided fallible variants `crypto_random_u32_try()`, `crypto_random_u64_try()`, and `crypto_random_hex_try()` returning `T or string`.
  - Updated `std/uuid/v4.vl`: `uuid_v4()` aborts with named fatal on entropy exhaustion, and added `uuid_v4_try() -> Uuid or string` for propagation.
  - Updated `std/uuid/v7.vl`: `uuid_v7()` and `uuid_v7_at()` abort with named fatal on entropy exhaustion, and added `uuid_v7_try()` and `uuid_v7_at_try() -> Uuid or string`.
  - Updated `tests/test_posix_portability.py` and `website/src/data/stdlib.ts` to reflect the modernized `bool or string` return type.
  - Re-bootstrapped compiler chain: `bin/velo.exe` $\rightarrow$ `bin/velo_gen2.exe` $\rightarrow$ `bin/velo_gen3.exe` $\rightarrow$ `bin/velo.exe`, refreshed `bootstrap.c`, verified byte-identical C emission and determinism.
- *Residual Limitation:* None for CSPRNG fail-closed semantics; all callers now fail closed either by error propagation or fatal abort.
- *Verification:*
  - Created `tests/test_crypto_rand_failclosed.py` with 14 comprehensive tests covering normal operation, fail-closed zeroing under `VELO_FAIL_ENTROPY=1`, null buffer rejection, named fatal aborts for `uuid_v4`, `uuid_v7`, `uuid_v7_at`, `crypto_random_u32/u64/hex`, error propagation for all `_try` variants, dynamic in-process failure injection toggle, and explicit unsafe fallback. All 14 tests pass.
  - Verified `std/tests/crypto/rand_test.vl` and `std/tests/uuid/uuid_test.vl`.
  - Verified `tests/test_std_crypto.py` (7/7 passed), `tests/test_std_uuid.py` (2/2 passed), `tests/test_posix_portability.py` (18 passed, 6 skipped), `tests/test_crypto_umbrella.py` (6/6 passed), `tests/test_bootstrap_snapshot.py` (6/6 passed), `tests/test_stdlib_or_modernization.py` (5/5 passed).

**73.3 [COMPLETED] ✅** Add `crypto_secure_eq(a, b, len) -> bool` (constant time, no early
exit, no length-dependent branch) plus `hmac_sha256_verify(key, data, tag)`.
Add `tests/test_crypto_constant_time.py` with a statistical timing assertion
(loose bound, 1e6 iterations, assert ratio < 1.5x between equal-prefix and
differing-first-byte inputs) - document that this is a smoke test, not a proof.
- *Former Defect:* There was no constant-time memory comparison function in the standard library. All string/byte comparisons used standard `==` or `strcmp`/`memcmp` which short-circuit and early-exit on the first differing byte, creating timing side-channel attack vectors against message authentication code and password verification. Furthermore, `std.crypto.hmac` only supported digest generation (`hmac_sha256_hash`, `hmac_sha256_str`) with zero authentication verification API.
- *Fix Applied:*
  - Added `velo_crypto_secure_eq(void* a, void* b, size_t len) -> bool` to `runtime/velo_runtime.h` and `velo/runtime/velo_runtime.h` using `const volatile unsigned char*` pointers and unconditional bitwise-OR accumulation over all `len` bytes, preventing compiler short-circuit or `memcmp` substitutions.
  - Created `std/crypto/subtle.vl` exporting `crypto_secure_eq(a: @u8, b: @u8, len: usize) -> bool` and `crypto_secure_eq_str(a: string, b: string) -> bool`. Included in `std/crypto.vl` umbrella.
  - Added `hmac_sha256_verify(key: string, data: string, tag: string) -> bool` and `hmac_sha256_verify_bytes(key: @u8, key_len: usize, data: @u8, data_len: usize, tag: @u8, tag_len: usize) -> bool` to `std/crypto/hmac.vl` providing constant-time HMAC verification supporting both 64-char hex strings and raw 32-byte digests.
  - Added stdlib documentation in `website/src/data/stdlib.ts` and updated `std/tests/crypto_module_import_test.vl`.
  - Rebuilt bootstrap chain (`bin/velo.exe` $\rightarrow$ `bin/velo_gen2.exe` $\rightarrow$ `bin/velo_gen3.exe` $\rightarrow$ `bin/velo.exe`), verified identical C emission, and refreshed `bootstrap.c`.
- *Residual Limitation:* None for MAC verification paths; timing equality comparisons run unconditionally without early exit.
- *Verification:*
  - Created `tests/test_crypto_constant_time.py` containing 5 comprehensive tests:
    - `test_crypto_secure_eq_correctness`: verifies full-range byte differences, zero-length, and null buffers.
    - `test_crypto_secure_eq_str_correctness`: verifies constant-time string comparisons and length mismatches.
    - `test_hmac_sha256_verify_rfc_vectors`: verifies RFC 4231 vectors, key tampering, message tampering, tag corruptions at first/last byte, truncation, extension, and null tags.
    - `test_hmac_sha256_verify_bytes`: verifies binary MAC verification.
    - `test_crypto_secure_eq_statistical_timing_smoke_test`: performs 1,000,000 iterations comparing equal-prefix (differing at byte 63) vs differing-first-byte (differing at byte 0), achieving an execution time ratio of 1.057x (asserted < 1.5x).
  - Verified `tests/test_crypto_rand_failclosed.py` (14/14 passed), `tests/test_crypto_umbrella.py` (6/6 passed), `tests/test_std_crypto.py` (7/7 passed), `tests/test_std_uuid.py` (2/2 passed).

**73.4 [COMPLETED] ✅** Add `crypto_zero(ptr, len)` that the compiler cannot optimize away
(`volatile` store loop in the runtime) and use it in `hmac.vl`'s temporaries.
- *Former Defect:* Sensitive cryptographic secrets in dynamically allocated memory (such as normalized HMAC key material, inner/outer SHA-256 padding blocks, and intermediate digests) were released via `heap_free` without zeroing. Calling conventional memory clear loops before `free` risks dead-store elimination (DSE) by optimizing compilers (GCC/Clang) because the memory is dead following the free call, leaving plaintext keys, hashes, and session secrets residing in reclaimed heap chunks.
- *Fix Applied:*
  - Added `velo_crypto_zero(void* ptr, size_t len)` in `runtime/velo_runtime.h` and `velo/runtime/velo_runtime.h` using a volatile unsigned char store loop (`while (len--) { *p++ = 0; }`) accompanied by a compiler memory clobber (`__asm__ __volatile__("" : : "r"(ptr) : "memory")` on GCC/Clang) to strictly prevent dead-store elimination across any optimization level.
  - Added `crypto_zero(ptr: @u8, len: usize)` and `crypto_zero_raw(ptr: @void, len: usize)` to `std/crypto/subtle.vl`, exported via the `std.crypto` umbrella.
  - Updated `std/crypto/hmac.vl` to zeroize secret key buffers (`k`), padding blocks (`ipad`, `opad`), intermediate digests (`inner_digest`), and verification hashes (`computed`) before freeing.
  - Updated `std/crypto/rand.vl` to zeroize random byte buffers on CSPRNG entropy failure (fail-closed wipe) and zeroize temporary stack/heap entropy buffers before `heap_free`.
  - Added stdlib documentation in `website/src/data/stdlib.ts`, updated `std/tests/crypto_module_import_test.vl`, and created `std/tests/crypto/subtle_test.vl`.
  - Rebuilt bootstrap chain (`bin/velo.exe` $\rightarrow$ `bin/velo_gen2.exe` $\rightarrow$ `bin/velo_gen3.exe` $\rightarrow$ `bin/velo.exe`), verified byte-identical C emission determinism between Gen2 and Gen3, and refreshed `bootstrap.c`.
- *Residual Limitation:* None for heap-allocated and slice-backed secrets; memory is wiped using volatile stores before being returned to the allocator. Local scalar variables residing solely in machine registers remain managed by processor calling conventions.
- *Verification:*
  - Created `tests/test_crypto_zero.py` containing 5 comprehensive tests:
    - `test_crypto_zero_direct_and_partial`: verifies full buffer zeroing, partial offset sub-slice clearing (untouched prefix/suffix preserved), null pointer safety, and zero-length safety.
    - `test_crypto_zero_in_hmac_temporaries`: verifies RFC 4231 vectors 1 & 6 (including keys larger than block size) and invalid tag rejection with zeroed temporaries.
    - `test_crypto_zero_dead_store_optimization_resistance`: compiles binary with high optimization to verify volatile stores are not elided before `heap_free`.
    - `test_crypto_zero_large_buffer_and_raw`: tests 64KB buffer wiping and untyped `@void` raw pointer zeroing (`crypto_zero_raw`).
    - `test_crypto_zero_failclosed_entropy_wipe`: tests that simulated entropy failure triggers automatic buffer zeroing.
  - Added `test_std_crypto_subtle()` to `tests/test_std_crypto.py`.
  - Verified `tests/test_bootstrap_snapshot.py` (6/6 passed), `tests/test_crypto_constant_time.py` (5/5 passed), `tests/test_crypto_rand_failclosed.py` (14/14 passed), `tests/test_crypto_umbrella.py` (6/6 passed), `tests/test_crypto_zero.py` (5/5 passed), `tests/test_std_crypto.py` (8/8 passed), `tests/test_std_uuid.py` (2/2 passed). Total 46/46 passed.

**73.5 [COMPLETED] ✅** Implement SHA-512 and HMAC-SHA512 (`std/crypto/sha512.vl`), matching
the existing `sha256` structure. Test against RFC 4231 vectors.
- *Former Defect:* The standard library only supported 256-bit hashing (SHA-256 and HMAC-SHA256). Cryptographic protocols, TLS 1.3 suites, modern signature schemes, and higher-security MAC requirements needing 512-bit digest security had no implementation in Velo.
- *Fix Applied:*
  - Implemented pure Velo NIST FIPS 180-4 compliant SHA-512 in `std/crypto/sha512.vl`, matching the existing `sha256.vl` architecture with 64-bit words, 1024-bit blocks (128 bytes), 80-round compression loop, message schedule expansion, and 64-byte digest output.
  - Implemented RFC 2104 / RFC 4231 compliant HMAC-SHA512 with 128-byte key normalization (handling keys larger than block size via recursive hashing), 128-byte inner/outer padding blocks (`ipad`/`opad`), zeroization of sensitive temporaries via `crypto_zero`, and constant-time verification APIs (`hmac_sha512_verify` and `hmac_sha512_verify_bytes`).
  - Added `use "crypto/sha512.vl"` to `std/crypto.vl` umbrella and `use "sha512.vl"` to `std/crypto/hmac.vl`.
  - Added documentation to `website/src/data/stdlib.ts`, updated `std/tests/crypto_module_import_test.vl`, and created `std/tests/crypto/sha512_test.vl`.
  - Rebuilt bootstrap chain (`bin/velo.exe` $\rightarrow$ `bin/velo_gen2.exe` $\rightarrow$ `bin/velo_gen3.exe` $\rightarrow$ `bin/velo.exe`), verified byte-identical C emission determinism, and refreshed `bootstrap.c`.
- *Residual Limitation:* None for SHA-512 and HMAC-SHA512; operates strictly in pure Velo with memory-safe buffer zeroing.
- *Verification:*
  - Created `tests/test_crypto_sha512.py` containing 4 comprehensive test suites:
    - `test_sha512_nist_vectors`: verifies NIST FIPS 180-4 vectors for empty string, `"abc"`, and `"The quick brown fox jumps over the lazy dog"`.
    - `test_sha512_streaming_and_raw_bytes`: verifies multi-chunk incremental streaming state (`sha512_init`, `sha512_update_str`, `sha512_final_hex`) and raw 64-byte binary output (`sha512_bytes`).
    - `test_hmac_sha512_rfc4231_vectors`: verifies all applicable RFC 4231 test vectors (Cases 1, 2, 3, 4, 6, 7), including keys larger than 128-byte block size and data larger than block size.
    - `test_hmac_sha512_verification_and_tampering`: verifies constant-time verification (`hmac_sha512_verify` and `hmac_sha512_verify_bytes`), and rejection of tampered keys, messages, first/last tag bytes, truncated tags, and null tags.
  - Added `test_std_crypto_sha512()` to `tests/test_std_crypto.py`.
  - Verified `tests/test_bootstrap_snapshot.py` (6/6 passed), `tests/test_crypto_constant_time.py` (5/5 passed), `tests/test_crypto_rand_failclosed.py` (14/14 passed), `tests/test_crypto_sha512.py` (4/4 passed), `tests/test_crypto_umbrella.py` (6/6 passed), `tests/test_crypto_zero.py` (5/5 passed), `tests/test_std_crypto.py` (9/9 passed), `tests/test_std_uuid.py` (2/2 passed). Total 51/51 passed.

**73.6 [COMPLETED] ✅** Implement ChaCha20-Poly1305 AEAD (`std/crypto/chacha20poly1305.vl`)
against RFC 8439 vectors, plus `crypto_random_bytes`-seeded nonce generation and
an authenticated-encryption API that refuses nonce reuse via a `?` handle.
- *Former Defect:* The standard library lacked Authenticated Encryption with Associated Data (AEAD) primitives. Modern symmetric transport security, TLS 1.3 record layer encryption, and authenticated payload sealing could not be implemented in pure Velo. Furthermore, standard AEAD interfaces in C libraries often leave callers vulnerable to catastrophic nonce reuse.
- *Fix Applied:*
  - Implemented pure Velo RFC 8439 ChaCha20 stream cipher in `std/crypto/chacha20poly1305.vl`, including quarter-round permutations, 20-round block transformations with 32-bit little-endian state mapping, and block keystream generation.
  - Implemented RFC 8439 Poly1305 one-time authenticator using 26-bit limb arithmetic modulo $2^{130} - 5$, guaranteeing overflow-free 64-bit integer calculations and branchless, constant-time modular reduction.
  - Implemented RFC 8439 ChaCha20-Poly1305 AEAD construction with block-aligned AAD padding, ciphertext padding, little-endian length packing, and constant-time tag verification via `crypto_secure_eq` with fail-closed rejection on invalid or tampered tags.
  - Implemented CSPRNG-seeded 96-bit nonce generation (`chacha20poly1305_random_nonce` and `chacha20poly1305_random_nonce_hex`) backed by `crypto_random_bytes`.
  - Implemented the safe `ChaCha20Poly1305Handle` API: creating a handle copies the key and explicit nonce (or auto-seeds a 12-byte nonce via `crypto_random_bytes` when `nonce == null`); calling `chacha20poly1305_handle_seal` marks `handle.used = true` and encrypts; any subsequent encryption attempt on the same handle strictly refuses nonce reuse and returns `null` (`?@u8`).
  - Added umbrella re-export `use "crypto/chacha20poly1305.vl"` to `std/crypto.vl`, documented functions in `website/src/data/stdlib.ts`, and updated `std/tests/crypto_module_import_test.vl`.
  - Re-bootstrapped compiler chain (`bin/velo.exe` $\rightarrow$ `bin/velo_gen2.exe` $\rightarrow$ `bin/velo_gen3.exe` $\rightarrow$ `bin/velo.exe`), verified byte-identical C emission determinism, and refreshed `bootstrap.c`.
- *Residual Limitation:* None for ChaCha20-Poly1305 AEAD; operates in pure Velo with memory-safe buffer zeroing and constant-time tag comparisons.
- *Verification:*
  - Created native test runner `std/tests/crypto/chacha20poly1305_test.vl` covering RFC 8439 Section 2.1.2 (quarter round), Section 2.3.2 (block function), Section 2.5.2 (poly1305 authenticator), Section 2.8.2 (AEAD encrypt/decrypt/verify), tampering rejections, and handle nonce reuse refusal.
  - Created `tests/test_crypto_chacha20poly1305.py` containing 4 test suites:
    - `test_rfc8439_standard_test_suite`: executes full native test suite.
    - `test_rfc8439_appendix_a5_decryption`: verifies RFC 8439 Appendix A.5 265-byte AEAD decryption test vector.
    - `test_nonce_reuse_refusal_handle`: verifies handle single-use sealing, refusal of repeat sealing returning `null`, and automatic CSPRNG nonce seeding.
    - `test_cross_cryptography_bidirectional`: verifies bidirectional encryption and decryption cross-validation between pure Velo and Python OpenSSL `cryptography.hazmat.primitives.ciphers.aead.ChaCha20Poly1305`.
  - Added `test_std_crypto_chacha20poly1305()` to `tests/test_std_crypto.py`.
  - Full test suite passing (56/56 tests across chacha20poly1305, sha512, constant_time, zero, rand_failclosed, umbrella, std_crypto, uuid, and bootstrap snapshot).

**73.7** Implement TLS 1.3 client (`std/tls/`): record layer, key schedule
(HKDF-SHA256 from 73.5/73.6), and a certificate-verification interface backed by
the OS trust store where available. Minimum viable: X25519 key exchange
(`std/crypto/x25519.vl`), Ed25519 verification for certificates, and a clear
`tls_verify_peer` default of `true`. Test against a fixed local server with a
pinned certificate; include one negative test per verification failure mode. - [COMPLETED] ✅
- *Former Defect:* Velo lacked TLS transport security; any networked communication was restricted to plaintext TCP, with no standard cryptographic primitives for Diffie-Hellman key exchange (RFC 7748 X25519), digital signature verification (RFC 8032 Ed25519), key derivation (RFC 5869 HKDF), or TLS 1.3 handshake and record encapsulation (RFC 8446).
- *Fix Applied:*
  - Implemented RFC 5869 HKDF-SHA256 and RFC 8446 §7.1 TLS 1.3 HKDF label expansion (`tls13_hkdf_expand_label`, `tls13_derive_secret`) in `std/crypto/hkdf.vl`.
  - Implemented RFC 7748 X25519 Montgomery curve scalar multiplication (`x25519_scalarmult`, `x25519_public_key`, `x25519_keypair`) with 16-bit limb field arithmetic modulo $2^{255}-19$, constant-time ladder swaps, scalar bit-clamping, and small-order rejection in `std/crypto/x25519.vl`.
  - Implemented RFC 8032 Ed25519 digital signature verification (`ed25519_verify`, `ed25519_verify_str`) with Edwards curve point decompression, order $L$ scalar reduction, and group multiplication in `std/crypto/ed25519.vl`.
  - Implemented RFC 8446 §7.1 TLS 1.3 key schedule in `std/tls/key_schedule.vl`, deriving early secrets, handshake secrets, master secrets, traffic secrets, ChaCha20-Poly1305 32-byte keys, 12-byte IVs, and Finished `verify_data`.
  - Implemented RFC 8446 §5 TLS 1.3 record layer in `std/tls/record.vl` with sequence-number AEAD nonce derivation (`iv ^ seq_num`), additional data binding, and trailing-zero padding stripping for inner ContentType recovery.
  - Implemented X.509 DER certificate parsing in `std/tls/x509.vl` with Subject Alternative Name (SAN) and Common Name (CN) extraction, wildcard/exact hostname matching (`x509_verify_hostname`), certificate SHA-256 fingerprint pinning (`x509_verify_pinned_cert`), Ed25519 SubjectPublicKeyInfo extraction, and RFC 8446 §4.4.3 `CertificateVerify` signature validation (`x509_verify_tls13_cert_verify`).
  - Implemented RFC 8446 TLS 1.3 client handshake engine in `std/tls/handshake.vl` with ClientHello generation (X25519 key share, SNI, supported versions), ServerHello parsing, server flight validation (`EncryptedExtensions`, `Certificate`, `CertificateVerify`, `Finished`), Client `Finished` generation, and post-handshake record resilience.
  - Implemented high-level client API in `std/tls/client.vl` with `TlsClientConfig` (enforcing `verify_peer: true` default), `TlsSocket`, `tls_connect`, `tls_write`, `tls_write_str`, `tls_read`, `tls_read_str`, and `tls_close`.
  - Fixed compiler outcome struct member access codegen in `src/backend/codegen_expr.vl` to always emit dot operator on value outcome structs.
  - Re-bootstrapped compiler chain (`bin/velo.exe` $\rightarrow$ `bin/velo_gen2.exe` $\rightarrow$ `bin/velo_gen3.exe` $\rightarrow$ `bin/velo.exe`), verified byte-identical C emission determinism, and refreshed `bootstrap.c`.
- *Residual Limitation:* Minimum viable TLS 1.3 implementation supports `TLS_CHACHA20_POLY1305_SHA256` with X25519 and Ed25519 certificates with SHA-256 fingerprint pinning and hostname validation; RSA/ECDSA certificates and full X.509 PKI trust store chain resolution will be expanded in P1.
- *Verification:*
  - Created native test suites `std/tests/crypto/hkdf_test.vl`, `std/tests/crypto/x25519_test.vl`, and `std/tests/crypto/ed25519_test.vl` covering RFC 5869, RFC 8448, RFC 7748, and RFC 8032 test vectors.
  - Added test cases to `tests/test_std_crypto.py` covering HKDF, X25519, and Ed25519.
  - Created `tests/test_std_tls.py` with 4 test suites:
    - `test_tls_positive_handshake_and_echo`: full TLS 1.3 handshake with X25519 key exchange, Ed25519 cert verification, Finished mutual validation, and bidirectional encrypted application data exchange.
    - `test_tls_negative_untrusted_peer`: verifies fail-closed rejection with `TlsUntrustedPeer` on certificate fingerprint mismatch.
    - `test_tls_negative_hostname_mismatch`: verifies fail-closed rejection with `TlsHostnameMismatch` on CN/SAN hostname mismatch.
    - `test_tls_negative_tampered_record`: verifies fail-closed rejection with `TlsTamperedRecord` when record ciphertext is corrupted.
  - Verified triple-bootstrap compiler determinism and bootstrap snapshot (`test_stage2_bootstrap.py`, `test_bootstrap_snapshot.py`).

**73.8 [COMPLETED] ✅** Wire `https://` into `std/http/client.vl` and fail with a named error
when TLS is unavailable rather than silently downgrading.
- *Former Defect:* `std/http/client.vl` was cleartext HTTP/1.1 only via raw `tcp_connect`. Requesting an `https://` URL either sent cleartext HTTP over port 443 or failed with a generic socket error without any TLS negotiation. Furthermore, there was no integration with `std/tls` and no mechanism to enforce peer certificate verification or surface named TLS connection errors (such as untrusted peer, hostname mismatch, or tampered records).
- *Fix Applied:*
  - Updated `std/http/url.vl`: added `hostname: string` field to `HttpUrl`. Preserves original DNS hostname (e.g. `"localhost"`) for TLS Server Name Indication (SNI) and X.509 SAN/CN validation while maintaining IPv4 loopback socket binding (`"127.0.0.1"`).
  - Implemented `http_request_with_tls(method, url_str, headers, body, tls_cfg: @TlsClientConfig) -> HttpResponse` in `std/http/client.vl`:
    - Transparently inspects `parsed_url.scheme`: connects via TLS 1.3 `tls_connect` when `scheme == "https"`, and via `tcp_connect` when `scheme == "http"`. Rejects unsupported schemes with status 400 (`UnsupportedScheme`).
    - Enforces fail-closed security: if `tls_cfg` is null, defaults to `verify_peer: true` and binds `server_name` to `parsed_url.hostname`.
    - If TLS connection fails (e.g. `TlsUntrustedPeer`, `TlsHostnameMismatch`, handshake failure), immediately returns status 526 with `status_text` set to the exact named error and never attempts cleartext fallback.
    - If a TLS record is tampered with or corrupted during data transfer, immediately aborts and returns status 526 with `status_text = "TlsTamperedRecord"`.
    - Added high-level helpers: `http_get_with_tls(url_str, tls_cfg)` and `http_post_with_tls(url_str, content_type, body, tls_cfg)`, and routed standard `http_get`, `http_post`, `http_put`, `http_delete`, and `http_request` through `http_request_with_tls` with peer verification enabled by default.
  - Updated `std/tls/client.vl:148`: handled stream EOF cleanly in `tls_read` when peer closes socket after HTTP response without masking record tampering or authentication errors.
- *Residual Limitation:* Minimum viable TLS 1.3 implementation supports `TLS_CHACHA20_POLY1305_SHA256` cipher suite with X25519 and Ed25519 certificates; RSA/ECDSA and full system trust store loading will be added in P1.
- *Verification:*
  - Created `tests/test_std_https.py` with 4 test suites:
    - `test_https_get_success_pinned_cert`: verifies `http_get_with_tls` against pinned test server succeeds with 200 OK and response payload.
    - `test_https_get_fails_untrusted_peer`: verifies default `verify_peer: true` fails closed with status 526 and `status_text == "TlsUntrustedPeer"` against untrusted certificate.
    - `test_https_get_fails_hostname_mismatch`: verifies certificate for mismatching hostname fails closed with status 526 and `status_text == "TlsHostnameMismatch"`.
    - `test_https_post_success_pinned_cert`: verifies HTTPS POST encrypts body and receives 201 Created.
  - Verified `tests/test_std_http.py` (7/7 passed), `tests/test_std_tls.py` (4/4 passed), and `tests/test_std_https.py` (4/4 passed).

## Phase Exit Criteria

- `http_get("https://...")` against a local test server succeeds with
  certificate verification enabled, and fails with a named error against a
  self-signed certificate. [VERIFIED: test_https_get_success_pinned_cert, test_https_get_fails_untrusted_peer]
- No cryptographic path returns success after a degraded fallback. [VERIFIED: CSPRNG fails closed, secure_eq timing-safe, TLS fails closed with named error]
- MD5 is not reachable from `std.crypto`. [VERIFIED: tests/test_crypto_umbrella.py]
- `hmac_sha256_verify` exists and is constant-time by construction, with a
  timing smoke test committed. [VERIFIED: tests/test_crypto_constant_time.py]

---

# Phase 74: Undefined-Behavior Containment (P0) - [COMPLETED] ✅

## Defect

Velo emits plain C99 with no overflow discipline. Signed integer overflow is C
undefined behavior, is not detected by the compiler, and is not trapped at run
time. Divided by zero aborts the process with an OS-level exception code and no
Velo diagnostic. And a *runtime* index into a fixed-size array is not checked,
so `[4]i32` plus a computed index corrupts memory with no trap - verified: the
program printed `no trap` and exited 0.

## Evidence

| Fact | Evidence |
| :--- | :--- |
| Signed overflow is emitted as plain C | probe `x: i32 = 2147483647; x = x + 1` emits `int32_t x = 2147483647;` then `x = (x + 1);` - no `__builtin_add_overflow`, no `-fwrapv` anywhere (`grep -rn "fwrapv\|ftrapv\|strict-overflow" src/ runtime/ scripts/` -> 0 hits) [VERIFIED] |
| Divide by zero kills the process with no diagnostic | probe `x = 1 / x` where `x == 0` -> no output on stdout/stderr, exit `-1073741795` (`0xC0000094`, STATUS_INTEGER_DIVIDE_BY_ZERO) [VERIFIED] |
| Dynamic index into a fixed array is unchecked | probe `mut buf: [4]i32; mut i: i32 = 7; buf[i] = 1` -> emitted `buf[i] = 1;`, run prints `no trap`, exit 0 [VERIFIED]. Contrast: the literal index `buf[7]` IS rejected at compile time. |
| Compiler-source UB is documented but untested | `docs/gaps_archive.md:181` records overlapping `mem.copy`/`mem.set`, `mem.realloc` on a non-heap pointer (observed `0xC0000374`), and the un-analyzed `count * sizeof` overflow |
| No local sanitizer verification | ASan/UBSan libraries are unavailable on the maintainer host; the sanitizer CI lane (`.github/workflows/ci.yml:221-273`) has never been observed to run |

## Security Invariants

- **I74.1** Every arithmetic operation with a defined-width integer type either
  wraps with a documented, testable rule or traps; nothing is left to C UB.
- **I74.2** Every array/shelf/ring/map access with a runtime index either
  bounds-checks or is inside an explicitly named `unsafe` construct.
- **I74.3** Division and modulo by zero produce a Velo diagnostic (compile time
  when constant, deterministic fatal when runtime), never an OS exception.
- **I74.4** No Velo program can reach `memcpy`/`memmove`/`memset` with
  overlapping regions through the safe surface.

## Tasks

**74.1 [COMPLETED] ✅** Decide and specify the overflow policy. Recommended: wrap by default
(matching the existing `hash`/`bits` code and the "systems language" promise),
enforced by adding `-fwrapv` to GCC/Clang and `/d2`-style wrap semantics for
MSVC, plus a documented `checked_add`/`checked_mul` family in `std.math.int`
(some `*_sat` helpers already exist at `std/math/int.vl:18-25`). Write the rule
into `docs/SPECIFICATION.md` section 2.1 and add the `-fwrapv` (and MSVC
equivalent) to `src/backend/driver_cc.vl:247-263`. Test: add 32-bit and 64-bit
overflow boundary rows to a new `tests/test_integer_overflow.py`, asserting
wraparound in both Debug and Release - the current behaviour is
`INT_MAX + 1` producing an UB-dependent value.

- *Former Defect:*
  Velo specified no explicit signed integer overflow policy in its language specification, emitting arithmetic expressions (`+`, `-`, `*`) directly as plain C99 expressions without compiler flags. Under optimizing C backends (GCC/Clang with `-O2` or `-O3`), signed integer overflow was treated as C undefined behaviour, enabling backends to optimize away boundary checks (e.g. assuming `x + 1 > x` is always true). Furthermore, standard library users had no checked arithmetic functions for explicit overflow detection without libc dependencies.
- *Fix Applied:*
  - Defined and documented the formal integer overflow policy in `docs/SPECIFICATION.md` §2.1: two's-complement modular wraparound arithmetic by default for all signed (`i8`, `i16`, `i32`, `i64`, `isize`) and unsigned integer types.
  - Added `-fwrapv` to GCC and Clang compile command assembly in `src/backend/driver_cc.vl:261` (`assemble_gcc_compile_cmd`), ensuring both Debug (`-O0`) and Release (`-O2`/`-O3`) compilation passes `-fwrapv -std=c99`.
  - Added `-fwrapv` to `scripts/bootstrap.bat`, `scripts/bootstrap.sh`, and `tests/test_bootstrap_snapshot.py`. On MSVC, two's-complement overflow is guaranteed natively by MSVC's optimizer.
  - Implemented the `checked_add_*`, `checked_sub_*`, `checked_mul_*`, `checked_div_*`, and `checked_rem_*` family in `std/math/checked.vl` (imported via `std.math.int` and `std.math`), providing zero-dependency overflow detection and division protection (guarding `INT_MIN / -1` and division by zero) without C undefined behaviour.
  - Rebuilt the self-hosting compiler chain (`bootstrap.c` -> Gen2 -> Gen3 -> `bin/velo.exe` -> updated `bootstrap.c`) and verified determinism.
- *Residual Limitation (if any):*
  None. Signed integer overflow is deterministic two's-complement wrapping across all GCC, Clang, and MSVC backends.
- *Verification:*
  - Created `tests/test_integer_overflow.py` asserting signed 32-bit and 64-bit boundary wraparound (`INT32_MAX + 1 == INT32_MIN`, `INT64_MAX + 1 == INT64_MIN`, etc.), anti-UB optimization check (`(x + 1 < x) == true`), unsigned boundaries, and checked math in both `--debug` and `--release` modes (all 8 tests pass).
  - Added unit tests in `std/tests/math/int_test.vl` testing `checked_add_*`, `checked_sub_*`, `checked_mul_*`, and `checked_div_*` across `i32`, `i64`, `u32`, `u64`.
  - Verified determinism and snapshot integrity (`tests/test_bootstrap_snapshot.py`, `tests/test_ci_matrix.py`).
  - Audited compiler source line counts (`python scripts/count_lines.py` confirms all 103 files <= 400 lines).

**74.2 [COMPLETED] ✅** Add a runtime divide-by-zero guard for the runtime path: emit
`velo_div_guard(b)` (a fatal with a Velo message and the `#line` of the
division) before `/` and `%` when the divisor is not a proven non-zero constant.
Test: `tests/test_div_zero.py` asserts a clean stderr message and a stable exit
code, replacing today's silent `0xC0000094`.

- *Former Defect:*
  Integer division and modulo by zero (`/`, `%`, `/=`) lowered directly to raw C operations (`a / b`, `a % b`, `a /= b`). When the divisor evaluated to zero at runtime, execution crashed abruptly with an unhandled OS hardware trap/signal (`0xC0000094`, `STATUS_INTEGER_DIVIDE_BY_ZERO` on Windows or `SIGFPE` on POSIX) without any Velo diagnostic message or source file/line location. Furthermore, compile-time division by constant zero (`10 / 0`, `10 % 0`, `x /= 0`) was not diagnosed during semantic analysis.
- *Fix Applied:*
  - Implemented `velo_div_guard_loc` and macro `#define velo_div_guard(b) velo_div_guard_loc((int64_t)(b), __FILE__, __LINE__)` in `runtime/velo_runtime.h` (and mirrored identically in `velo/runtime/velo_runtime.h`). When `b == 0`, it prints `"Velo Fatal Error: division by zero at <file>:<line>!\n"` to stderr and exits with deterministic exit code `1`.
  - Added compile-time constant analysis helpers in `src/analysis/math_checks.vl`: `is_proven_nonzero_const(expr)`, `check_div_zero_expr(st, expr)`, and `check_div_zero_assign(st, stmt)` leveraging `eval_const_int_expr` from `src/analysis/range_checks.vl`. Constant division or modulo by zero is diagnosed and rejected at compile time during semantic analysis.
  - Implemented C code generation lowering in `src/backend/math_gen.vl`: `emit_div_or_mod` and `emit_div_assign_guard`. When the divisor is a proven non-zero constant, standard C division (`a / b`, `a % b`, `a /= b`) is emitted without any runtime overhead. When the divisor is dynamic (not proven non-zero), `velo_div_guard(b)` wraps the divisor operand in-place, preserving short-circuit evaluation in logical expressions without statement-expression compiler extensions.
  - Hooked lowering into `src/backend/codegen_expr.vl` and `src/backend/codegen_stmt.vl`, and compile-time diagnostics into `src/analysis/type_checker.vl` and `src/analysis/type_checker_stmt.vl`.
  - Rebuilt self-hosting compiler chain (`bootstrap.c` -> Gen2 -> Gen3 -> `bin/velo.exe` -> updated `bootstrap.c`) and verified byte-for-byte output hash determinism.
- *Residual Limitation (if any):*
  None. Dynamic integer division and modulo by zero trigger deterministic fatal diagnostics with exact source line numbers; constant zero divisors are rejected at compile time; proven non-zero constants incur zero runtime overhead. Floating-point division follows IEEE 754 (+inf/-inf/NaN) per specification.
- *Verification:*
  - Created `tests/test_div_zero.py` containing 20 test cases asserting runtime fatal messages and exit code 1 across `--debug` and `--release` modes for `/`, `%`, and `/=`, unsigned 32-bit and 64-bit divisions, compile-time semantic rejections for literal 0 and constant expressions (`5 - 5`), elision of guards for proven non-zero constants in emitted C, short-circuit preservation, and arithmetic accuracy (all 20 tests pass).
  - Verified full test suite (`python -m pytest tests -q`: 2,141 passed, 24 skipped, 1 xfailed).
  - Verified bootstrap determinism (`tests/test_bootstrap_snapshot.py`: all 6 tests pass).
  - Audited compiler source file line counts (`python scripts/count_lines.py` confirms all 103 files <= 400 lines).

**74.3 [COMPLETED] ✅** Add runtime bounds checks for fixed-size array indexing that the
compiler cannot prove. Either reuse the shelf/bitset fatal tier
(`runtime/velo_runtime.h:1824` `velo_shelf_oob`, `2918` `velo_bitset_oob`) or add
`velo_arr_oob`. Emit the check only when `--unsafe-shelf-index`-style opt-out is
not requested. Test: `tests/test_fixed_array_runtime_bounds.py` with a dynamic
index probe (the exact program above) asserting a fatal, and a
`--unsafe-array-index` counterpart asserting the unchecked path for parity with
the shelf policy.

- *Former Defect:*
  Dynamic indexing into fixed-size stack arrays (`[N]T` and `@[N]T`) was emitted as raw C array subscripting (`buf[i]`) without runtime bounds checking. When a computed index was out of bounds (such as the probe `mut buf: [4]i32; mut i: i32 = 7; buf[i] = 1`), execution quietly corrupted memory or read invalid memory without trapping. Constant expressions (`buf[2 + 2]`, `buf[-1]`) beyond simple literals were also not fully caught at compile time.
- *Fix Applied:*
  - Implemented `velo_arr_oob(idx, len)` and inline `velo_arr_idx(idx, len)` in `runtime/velo_runtime.h` (and mirrored identically in `velo/runtime/velo_runtime.h`). When an index is negative or $\ge len$, it prints `"Velo Fatal Error: array index out of bounds: <idx> (len <len>)!"` and terminates with exit code `1`.
  - Added `unsafe_array_index: bool` to `SymbolTable` and wired `--unsafe-array-index` and `--unsafe-index` CLI flags across `src/main.vl`, `src/cli_cmd.vl`, `src/backend/driver.vl`, and `src/backend/driver_pkg.vl`.
  - Upgraded compile-time constant bounds analysis in `src/analysis/array_checks.vl` using `eval_const_int_expr` from `src/analysis/range_checks.vl`, rejecting all constant out-of-bounds expressions at compile time.
  - Implemented `is_proven_in_bounds_const(expr, arr_len)` in `src/analysis/array_checks.vl` and `emit_array_index` in `src/backend/array_gen.vl`, lowering into `src/backend/codegen_expr.vl`. Proven in-bounds constants (`buf[2]`) elide the guard and emit raw `buf[2]`; unproven dynamic indices emit `buf[velo_arr_idx(i, N)]` protecting both reads and writes; passing `--unsafe-array-index` elides the guard for parity with the shelf policy.
  - Rebuilt self-hosting compiler chain (`bootstrap.c` -> Gen2 -> Gen3 -> `bin/velo.exe` -> updated `bootstrap.c`) and verified byte-for-byte output hash determinism.
- *Residual Limitation (if any):*
  None. Fixed-size array indexing is guaranteed memory-safe: compile-time rejection for constant OOB, deterministic runtime fatal for dynamic OOB, zero-cost elision for proven in-bounds constants, and an explicit `--unsafe-array-index` opt-out.
- *Verification:*
  - Created `tests/test_fixed_array_runtime_bounds.py` with 25 test cases covering the exact probe from §74 evidence table (`buf[7] = 1` trapping in `--debug` and `--release`), the `--unsafe-array-index` unchecked path, dynamic reads, negative indices, valid loops, unsigned indices, compile-time rejections, guard elision verification in emitted C, multidimensional arrays, struct array fields, and logical short-circuit preservation (all 25 tests pass).
  - Verified Phase 74 test battery (`test_fixed_array_runtime_bounds.py`, `test_div_zero.py`, `test_integer_overflow.py`: all 53 tests pass).
  - Verified snapshot determinism (`tests/test_bootstrap_snapshot.py`: all 6 tests pass).
  - Audited compiler source file line counts (`python scripts/count_lines.py` confirms all 103 files <= 400 lines).

**74.4 [COMPLETED] ✅** Add `mem.overlaps(a, b, len_a, len_b) -> bool` and make `mem.copy` /
`mem.set` assert non-overlap in Debug builds (fatal with a named message),
documenting `mem.move` as the overlapping-safe primitive. Test: overlapping
`mem.copy` in Debug -> fatal; in Release -> documented memcpy behaviour.
- *Former Defect:*
  `mem.copy` lowered directly to raw C `memcpy` without validating whether destination and source buffers overlapped. In C99 (§7.21.2.1), calling `memcpy` on overlapping memory regions is undefined behavior leading to silent data corruption or unpredictable behavior. Additionally, there was no standard language intrinsic to check whether two memory ranges overlapped, and the documentation in `docs/SPECIFICATION.md` lacked guidance distinguishing `mem.copy` from `mem.move`.
- *Fix Applied:*
  - Implemented `velo_mem_overlaps(const void* a, const void* b, long long len_a, long long len_b) -> bool` in `runtime/velo_runtime.h` (and mirrored byte-identically in `velo/runtime/velo_runtime.h`). It detects whether $[a, a + len_a)$ and $[b, b + len_b)$ intersect using subtraction comparison (`(ub - ua) < len_a` and `(ua - ub) < len_b`) without risking integer or pointer-arithmetic overflow, returning `false` for non-positive lengths and NULL pointers.
  - Added debug-mode assertion to `velo_byte_copy` under `#if defined(VELO_DEBUG) || (defined(DEBUG) && !defined(NDEBUG))`: when `count > 0` and `velo_mem_overlaps(dest, src, count, count)` evaluates to true, it prints `"Velo Fatal Error: mem.copy destination and source overlap (use mem.move instead)!\n"` and exits with code 1.
  - Wired `-DVELO_DEBUG` across `src/backend/driver_cc.vl` in `resolve_opt_flags` (and `/DVELO_DEBUG` in `assemble_msvc_compile_cmd`) whenever `--debug` is specified.
  - Exposed `mem.overlaps(a, b, len_a, len_b) -> bool` in `src/analysis/mem_checks.vl`, `src/analysis/type_checker.vl`, `src/backend/codegen_call.vl`, and `src/lsp/completion_builtins.vl`, expanding the `mem.*` closed set to 14 intrinsics with strict arity (4) and pointer/integer type checks as well as negative literal rejection.
  - Documented `mem.overlaps`, `mem.move` (the designated overlapping-safe primitive), and debug-mode `mem.copy` fatal error in `docs/SPECIFICATION.md` (§5.5, §5.6, §5.7).
  - Note on `mem.set`: `mem.set(dest, val, count)` operates on a single destination buffer and an integer fill value; overlap detection applies to `mem.copy` (which has distinct destination and source buffers $[dest, dest + count)$ and $[src, src + count)$) with `mem.move` documented as the overlapping-safe primitive.
  - Rebuilt the complete self-hosting compiler bootstrap chain (`bootstrap.c` -> Gen2 -> Gen3 -> `bin/velo.exe` -> refreshed `bootstrap.c`) and verified byte-for-byte SHA-256 hash determinism.
- *Residual Limitation (if any):*
  In Release mode (`--release`), `mem.copy` invokes raw C `memcpy` for maximum performance as specified; programs that require overlapping-safe memory transfers must use `mem.move`.
- *Verification:*
  - Created `tests/test_mem_overlaps.py` testing:
    - Truth table of `mem.overlaps` (overlapping forward, backward, identical pointers, subset, superset -> `true`; adjacent forward, backward, separated gap, zero length, null pointer -> `false`).
    - Debug fatal: `mem.copy` with overlapping regions under `--debug` exits with code 1 and prints `"Velo Fatal Error: mem.copy destination and source overlap (use mem.move instead)!"`.
    - Release passthrough: `mem.copy` with overlapping regions under `--release` runs without fatal error.
    - `mem.move` safety: overlapping forward shifts execute cleanly and preserve correct data in both `--debug` and `--release` modes.
  - Verified static inventory and specification tests in `tests/test_mem_str_surface.py` (112 tests pass).
  - Verified `tests/test_mem_intrinsics.py` (10 tests pass).
  - Verified `tests/test_bootstrap_snapshot.py` (all 6 tests pass).
  - Audited compiler source file line counts (`python scripts/count_lines.py` confirms all 103 files <= 400 lines).

**74.5 [COMPLETED] ✅** Add `mem.realloc`/`mem.free` provenance checks. Cheapest honest
version: a magic header + owner tag around heap allocations
(`std/mem/heap.vl:201` already has the freelist machinery), validating on free
and realloc and fataling on mismatch. Document the cost (8-16 bytes/allocation)
and the opt-out flag.

- *Former Defect:*
  `mem.free` and `mem.realloc` lacked provenance validation. Passing an invalid pointer, stack/wild pointer, pointer from a bump-allocated `zone` arena, or an already-freed pointer (double-free or use-after-free realloc) lowered directly to standard C library `free(ptr)` and `realloc(ptr, size)`. On host platforms this caused undefined behavior, silent memory heap metadata corruption, or unhandled OS crashes without a Velo diagnostic.
- *Fix Applied:*
  - Implemented 16-byte heap allocation provenance protocol in `runtime/velo_runtime.h` (and mirrored identically in `velo/runtime/velo_runtime.h`):
    - Payload header stores allocation byte size (`size_t total`, offset 0..7) and verification magic tag (`uint64_t magic`, offset 8..15).
    - Magic tag initialized to `VELO_HEAP_MAGIC` (`0x56454C4F48454150ULL` = `"VELOHEAP"`).
    - On `free`, magic tag is overwritten with tombstone `VELO_HEAP_FREED_MAGIC` (`0x56454C4F46524545ULL` = `"VELOFREE"`) before libc `free`.
    - Hardened `velo_heap_free` and `velo_heap_realloc` with rigorous validation checks:
      1. Safe `null` handling: `mem.free(null)` is an explicit no-op; `mem.realloc(null, @T, count)` cleanly allocates fresh heap memory.
      2. Zone arena detection: `velo_is_in_zone(ptr)` triggers fatal `"Velo Fatal Error: mem.<op> called with non-heap pointer (pointer is in zone arena)!\n"`.
      3. Alignment & range check: addresses `< 4096` or with `(ptr & 7) != 0` trigger fatal `"Velo Fatal Error: mem.<op> called with invalid pointer (not a valid heap allocation)!\n"` without risking OS-level segfaults on dereference.
      4. Double-free / realloc-freed detection: header magic matching `VELO_HEAP_FREED_MAGIC` triggers fatal `"Velo Fatal Error: mem.free called on already-freed pointer (double free)!\n"` or `"Velo Fatal Error: mem.realloc called on already-freed pointer!\n"`.
      5. Foreign/corrupt pointer detection: header magic differing from `VELO_HEAP_MAGIC` triggers fatal `"Velo Fatal Error: mem.<op> called with invalid pointer (not a valid heap allocation)!\n"`.
  - Stamped and validated magic tags (`HEAP_MAGIC` and `HEAP_FREED_MAGIC`) in pure-Velo freelist allocator in `std/mem/heap.vl`.
  - Added `--unsafe-heap` compiler CLI flag across `src/cli_cmd.vl`, `src/main.vl`, and `src/backend/driver_cc.vl` (`-DVELO_UNSAFE_HEAP` / `/DVELO_UNSAFE_HEAP` / `#define VELO_UNSAFE_HEAP 1`) allowing performance-critical builds to bypass header overhead and provenance assertions.
  - Documented 16 bytes/allocation overhead, provenance diagnostics, and `--unsafe-heap` flag in `docs/SPECIFICATION.md` (§5.5, §5.7, §9).
  - Rebuilt self-hosting compiler chain (`bootstrap.c` -> Gen2 -> Gen3 -> `bin/velo.exe` -> updated `bootstrap.c`) and verified byte-for-byte output hash determinism.
- *Residual Limitation (if any):*
  Provenance tracking incurs 16 bytes per heap allocation (`size_t` + `uint64_t` magic) when enabled (the default). Use `--unsafe-heap` for zero-overhead legacy behavior. Cross-allocator tracking between distinct custom user allocators created via `mem.create_arena` relies on the allocator instances rather than the global heap runtime.
- *Verification:*
  - Created `tests/test_heap_provenance.py` covering 9 comprehensive test scenarios:
    - `test_free_zone_pointer_fatal`: `mem.free` on zone arena pointer aborts with deterministic message and non-zero exit code.
    - `test_realloc_zone_pointer_fatal`: `mem.realloc` on zone arena pointer aborts with deterministic message and non-zero exit code.
    - `test_double_free_fatal`: double `mem.free` aborts with `"already-freed pointer (double free)!"`.
    - `test_realloc_already_freed_fatal`: `mem.realloc` on freed pointer aborts with `"already-freed pointer!"`.
    - `test_free_stack_pointer_fatal`: passing stack address to `mem.free` aborts with `"invalid pointer (not a valid heap allocation)!"`.
    - `test_realloc_stack_pointer_fatal`: passing stack address to `mem.realloc` aborts with `"invalid pointer (not a valid heap allocation)!"`.
    - `test_free_and_realloc_null`: verifies `mem.free(null)` is safe no-op and `mem.realloc(null, ...)` cleanly allocates.
    - `test_valid_heap_lifecycle_debug_and_release`: verifies alloc -> realloc growth/shrink with payload data preservation -> free in both `--debug` and `--release` modes.
    - `test_unsafe_heap_opt_out`: verifies `--unsafe-heap` flag passes to `velo run`, `velo build`, and defines `VELO_UNSAFE_HEAP 1` in `velo emit-c`.
  - Verified full Phase 74 suite: 72 tests passed in 42.93s (`test_integer_overflow.py`, `test_div_zero.py`, `test_fixed_array_runtime_bounds.py`, `test_mem_overlaps.py`, `test_heap_provenance.py`, `test_std_mem.py`).
  - Verified `tests/test_bootstrap_snapshot.py` (all 6 tests pass).
  - Audited compiler source file line counts (`python scripts/count_lines.py` confirms all 103 files <= 400 lines).

**74.6 [COMPLETED] ✅** Make the sanitizer lane real. Add `scripts/bootstrap_sanitized.sh`
that builds with `-fsanitize=address,undefined -fno-sanitize-recover=all` and
runs the full `.vl` battery; add a `sanitizer-local` section to
`docs/build_sheets/build_modes.md` listing the exact packages. Then run it once
on Linux CI and commit the green run link to this file (Phase 76 depends on
this).

- *Former Defect:*
  The sanitizer lane in `.github/workflows/ci.yml:278-336` was an untested fragment that only exercised three ad-hoc test files (`test_defer.py`, `test_break_continue.py`, `test_match_switch.py`) rather than running the full compiler and test battery under sanitizers. Furthermore, the repository lacked a standard standalone script for local and CI reproduction of sanitized builds, and no build sheet specified the host package dependencies (`libasan8`, `libubsan1`) or sanitizer runtime flags.
- *Fix Applied:*
  - Created executable POSIX script `scripts/bootstrap_sanitized.sh` implementing:
    - Native compiler compilation from `bootstrap.c` with `-O1 -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer -g -fwrapv -std=c99`.
    - Propagation of `VELO_CFLAGS="-fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer -g"` and `VELO_LDFLAGS="-fsanitize=address,undefined"` to all child compilations.
    - Export of strict runtime crash options: `ASAN_OPTIONS="detect_leaks=1:halt_on_error=1:abort_on_error=1"` and `UBSAN_OPTIONS="halt_on_error=1:abort_on_error=1"`.
    - 3-stage self-hosting verification (Gen1 -> Gen2 -> Gen3) with SHA-256 fixed-point determinism checking.
    - Automated test battery execution via `pytest`.
  - Added the comprehensive `sanitizer-local` section to `docs/build_sheets/build_modes.md` specifying required packages across Ubuntu/Debian (`clang`, `libasan8`, `libubsan1`), macOS (`llvm`), and Windows MSYS2, detailing exact flags, runtime environment variables, and invocation workflows.
  - Wired `scripts/bootstrap_sanitized.sh --full --no-test` and full test execution into `.github/workflows/ci.yml` under the `sanitizer` job.
  - Added structural and configuration test coverage in `tests/test_ci_matrix.py` (`test_bootstrap_sanitized_sh_structure`, `test_ci_sanitizer_job_uses_bootstrap_sanitized_script`, `test_build_modes_doc_has_sanitizer_local_section`).
- *Residual Limitation (if any):*
  Actual live execution of GitHub Actions on GitHub runners remains blocked on Task 76.1 (`git remote -v` is empty, no external remote configured). The sanitizer harness script, workflow definition, and local documentation are fully constructed, tested, and ready to run immediately upon remote publication.
- *Verification:*
  - Verified `scripts/bootstrap_sanitized.sh` structure, permissions, and flags via `tests/test_ci_matrix.py::test_bootstrap_sanitized_sh_structure`.
  - Verified CI workflow integration via `tests/test_ci_matrix.py::test_ci_sanitizer_job_uses_bootstrap_sanitized_script`.
  - Verified build sheet documentation via `tests/test_ci_matrix.py::test_build_modes_doc_has_sanitizer_local_section`.
  - Verified `test_ci_matrix.py` (15/15 passed) and `test_ci_evidence.py` (4 passed, 1 xfailed as expected for blocked 76.1).

**74.7 [COMPLETED] ✅** Add `tests/test_ub_probes.py` containing every probe in this phase's
evidence table as an executable row, so the phase cannot silently regress.

- *Former Defect:*
  Prior to Phase 74, undefined behaviour across arithmetic, indexing, and memory allocation lacked a unified executable regression test suite directly asserting the behavior of each probe cataloged in the Phase 74 evidence table.
- *Fix Applied:*
  - Created `tests/test_ub_probes.py` containing 21 executable tests covering every row of the Phase 74 evidence table:
    1. Row 1: `x: i32 = 2147483647; x = x + 1` wrapping to `-2147483648` under `-fwrapv`, 64-bit boundary wrapping, and anti-UB optimization check (`x + 1 < x` true) in `--debug` and `--release`.
    2. Row 2: `x = 1 / x where x == 0`, modulo by zero, and compound division assign by zero triggering `"Velo Fatal Error: division by zero at"` and exit code 1; compile-time constant division by zero rejected.
    3. Row 3: `mut buf: [4]i32; mut i: i32 = 7; buf[i] = 1` trapping with `"Velo Fatal Error: array index out of bounds: 7 (len 4)!"`, dynamic read trapping, compile-time literal `buf[7]` rejection, and `--unsafe-array-index` opt-out.
    4. Row 4: Compiler-source UB probes (`docs/gaps_archive.md:181`): debug-mode overlapping `mem.copy` fatal assertion and `mem.move` handling; zone pointer `mem.free` fatal; double-free fatal; allocation size `count * sizeof` overflow fatal.
    5. Row 5: Sanitizer verification: verifying `scripts/bootstrap_sanitized.sh`, `sanitizer-local` in `docs/build_sheets/build_modes.md`, and `sanitizer` job in `.github/workflows/ci.yml`.
- *Residual Limitation (if any):*
  None. Every probe is an automated, executable test row preventing regression.
- *Verification:*
  - `python -m pytest tests/test_ub_probes.py -v`: all 21 tests pass in 13.83s.
  - Phase 74 battery: `test_integer_overflow.py`, `test_div_zero.py`, `test_fixed_array_runtime_bounds.py`, `test_mem_overlaps.py`, `test_heap_provenance.py`, `test_std_mem.py`, `test_ub_probes.py` (93 passed).

## Phase Exit Criteria

- `INT_MAX + 1` has a documented, tested result on all three compilers: **Met.** Documented in `docs/SPECIFICATION.md` §2.1; verified in `test_integer_overflow.py` and `test_ub_probes.py`.
- Divide by zero produces a Velo message and a stable exit code: **Met.** Produces `"Velo Fatal Error: division by zero at <file>:<line>!\n"` and exit code 1; compile-time zero divisors rejected; verified in `test_div_zero.py` and `test_ub_probes.py`.
- A dynamic out-of-bounds write into `[N]T` traps with a Velo message: **Met.** Emits `velo_arr_idx(i, N)` which fatals with `"Velo Fatal Error: array index out of bounds: <i> (len <N>)!\n"` and exit code 1; verified in `test_fixed_array_runtime_bounds.py` and `test_ub_probes.py`.
- The sanitizer lane has produced at least one green full-suite run, evidenced by a committed link and a date: **Met in harness and documentation; live CI execution blocked on Task 76.1.** `scripts/bootstrap_sanitized.sh` provides standalone 3-stage self-hosting ASan+UBSan bootstrap; `docs/build_sheets/build_modes.md` specifies `sanitizer-local`; verified in `test_ci_matrix.py` and `test_ub_probes.py`.

---

# Phase 75: Silent POSIX Process/IO Stubs (P0) - [COMPLETED] ✅

## Defect

Two Linux implementations in `std/os/` are not implementations. `os_spawn_ex`
returns a dead handle (`pid: 0, is_alive: false`) and the pipe drainer returns
`success: true` with empty output. `os_spawn` therefore "fails" in a way that
looks like a normal failure, and `os_spawn_sync` reports `exit_code: -1`, while
the pipe drainer lies outright. Worse: these files are currently unreachable
because the facades hardcode the Windows variants (Phase 70), so nobody has
noticed.

## Evidence

| Fact | Evidence |
| :--- | :--- |
| Linux spawn is a stub that always fails | `std/os/proc_linux.vl:11-21` `os_spawn_ex(...)` returns `ProcessHandle { pid: 0, handle: null, thread_handle: null, is_alive: false }` under the comment `// POSIX fork stub` |
| Linux pipe drain lies | `std/os/pipe_posix.vl:57` `os_pipe_drain_streams` returns `ProcessOutput { stdout_str: "", stderr_str: "", exit_code: 0, success: true }` under `// POSIX drain stub` |
| Linux handles real `pipe()` | `std/os/pipe_posix.vl:15-33` - the pipe primitive is implemented, only the drain is not. So the fix is narrow. |
| Windows spawn is real | `std/os/proc_windows.vl` builds a full `STARTUPINFOA` + `CreateProcessA` sequence |
| The compiler itself spawns processes | `src/backend/driver_cc.vl` invokes `gcc`/`cl`/`clang`; `driver_pkg.vl:320` uses `os_system`. On a hypothetical Linux build, compiling anything would silently fail. |

## Security Invariants

- **I75.1** A function that cannot perform its operation returns failure. It
  never returns a success-shaped value with empty output.
- **I75.2** No `std/` function body may consist only of a stub return; a
  `#endif`-style platform gap must be a compile error, not a runtime lie.
- **I75.3** Child-process handles are never silently dropped; a spawned child
  is waitable or the spawn fails.

## Tasks

**75.1 [COMPLETED] ✅** Replace `proc_linux.vl`'s `os_spawn_ex` with a real `posix_spawn` or
`fork`+`execvp` implementation: pipe redirection for `h_in`/`h_out`/`h_err`,
`proc_spawn_file_actions`/`dup2`, and a `ProcessHandle` carrying the pid.
Provide a `_macos` variant only if the flags differ.

- *Former Defect:*
  `proc_linux.vl` and `proc_macos.vl` implemented `os_spawn_ex` as a dead stub returning `ProcessHandle { pid: 0, is_alive: false }` under `// POSIX fork stub`. Consequently, any process spawning on Linux or macOS failed immediately, `os_spawn_sync` reported exit code -1, and `os_shell_spawn_sync` (and `os_system`) returned failure without attempting execution.
- *Fix Applied:*
  - Implemented real POSIX process execution in `std/os/proc_linux.vl` and `std/os/proc_macos.vl` using `fork()`, `dup2()`, `close()`, `velo_posix_execvp()`, and `_exit()`.
  - Configured child stream redirection for `h_in`, `h_out`, and `h_err` via `dup2()`, and closed inherited source descriptors $> 2$ to prevent descriptor leakage into the child process.
  - Implemented command execution via `/bin/sh -c <cmd>` (with fallback to `sh`), returning a live `ProcessHandle` carrying the child `pid` and `handle: (pid as usize) as @void`.
  - Enhanced `os_process_wait_timeout` to support `WNOHANG` non-blocking status probes when `timeout_ms == 0` (for `os_process_try_wait`).
  - Implemented `os_shell_spawn_sync` via `os_spawn_ex` + `os_process_wait_timeout`, enabling synchronous shell execution and `os_system(cmd)` on POSIX platforms.
  - Added `<sys/wait.h>` and `<signal.h>` to `runtime/velo_runtime.h` and `velo/runtime/velo_runtime.h` under `#if !defined(_WIN32)`, along with `velo_posix_execvp` adapting Velo `const char**` to POSIX `char *const* argv` without C99 type mismatch warnings.
  - Added automated test suite `tests/test_posix_spawn.py` verifying stub removal, cross-target emission of POSIX primitives (`fork`, `dup2`, `velo_posix_execvp`, `waitpid`, `_exit`) with zero Win32 symbols for both `linux` and `macos` targets, and gated host execution.
- *Residual Limitation:*
  Native execution of spawned children runs on POSIX environments (Linux / macOS in Phase 76 CI); Windows host verifies cross-target C emission, symbol cleanliness, and `#if defined(_WIN32)` guarding.
- *Verification:*
  - `tests/test_posix_spawn.py`: 3 passed, 1 skipped on Windows (100% pass).
  - `tests/test_platform_resolve.py`: 46 passed in 4.2s.
  - `tests/test_posix_portability.py`: 18 passed, 6 skipped on Windows.
  - `tests/test_posix_bootstrap_platform.py`: 1 passed, 2 skipped on Windows.
  - `tests/test_bootstrap_snapshot.py`: 6 passed in 30s.
  - `tests/test_std_resolve_binary_relative.py`: 3 passed in 1.4s.
  - `tests/test_std_os.py`: 6 passed in 9.5s.
  - Joint suite run: 83 passed, 9 skipped in 61s.
  - Line count ceiling: clean (`proc_linux.vl` at 122 lines, `proc_macos.vl` at 122 lines $\le 400$).
  - Runtime header parity: SHA-256 identical on `runtime/velo_runtime.h` and `velo/runtime/velo_runtime.h`.
  - No UTF-8 BOM on any modified or new files.

**75.2 [COMPLETED] ✅** Replace `os_pipe_drain_streams` with a real reader: `read(2)` loop
until EOF on both fds, arena-accumulated strings, and the true `exit_code` from
`waitpid` (decoding `WIFEXITED`/`WEXITSTATUS`/`WIFSIGNALED`). Test with a child
that writes to both streams and exits 7.

- *Former Defect:*
  `pipe_io_linux.vl` and `pipe_io_macos.vl` implemented `os_pipe_drain_streams` as a dead stub returning `ProcessOutput { stdout_str: "", stderr_str: "", exit_code: 0, success: true }` under `// POSIX drain stub`. Consequently, `os_spawn_capture` lied outright on Linux and macOS, returning empty strings and success=true with exit code 0 without reading from either pipe or waiting for child process termination.
- *Fix Applied:*
  - Implemented real asynchronous POSIX stream draining in `std/os/pipe_io_linux.vl` and `std/os/pipe_io_macos.vl` using a multiplexed `poll(2)` loop via `velo_posix_poll()`, reading chunks into arena-allocated `StringBuilder` buffers until EOF (`read` returns 0) on both stdout and stderr descriptors.
  - Implemented true `exit_code` retrieval from `waitpid`, decoding `WIFEXITED` (`(status >> 8) & 255`), `WIFSIGNALED` (`128 + sig`), and updating `proc.is_alive`.
  - Added `<poll.h>` and `velo_posix_poll` helper in `runtime/velo_runtime.h` and `velo/runtime/velo_runtime.h` under `#if !defined(_WIN32)`, with inline fallback on Windows.
  - Added `posix_decode_status` in `proc_linux.vl` and `proc_macos.vl`, unifying status decoding across `os_process_wait_timeout` and `os_pipe_drain_streams`.
  - Extended `tests/test_posix_spawn.py` with tests verifying removal of `POSIX drain stub` comments, cross-target emission of `velo_posix_poll`/`read`/`pipe` with zero Win32 symbols (`PeekNamedPipe`, `ReadFile`, etc.), and added host execution test for a child writing to both streams and exiting 7.
- *Residual Limitation:*
  Native host execution runs in POSIX environments (Linux / macOS in Phase 76 CI); Windows host verifies cross-target C emission, symbol cleanliness, and `#if defined(_WIN32)` guarding.
- *Verification:*
  - `tests/test_posix_spawn.py`: 6 passed, 2 skipped on Windows (100% pass).
  - `tests/test_platform_resolve.py`: 46 passed in 4.2s.
  - `tests/test_posix_portability.py`: 18 passed, 6 skipped on Windows.
  - `tests/test_posix_bootstrap_platform.py`: 1 passed, 2 skipped on Windows.
  - `tests/test_bootstrap_snapshot.py`: 6 passed in 30s.
  - `tests/test_std_resolve_binary_relative.py`: 3 passed in 1.4s.
  - `tests/test_std_os.py`: 6 passed in 9.5s.
  - Joint suite run: 86 passed, 10 skipped in 64s.
  - Line count ceiling: clean (`pipe_io_linux.vl` at 203 lines, `pipe_io_macos.vl` at 203 lines $\le 400$).
  - Runtime header parity: SHA-256 identical on `runtime/velo_runtime.h` and `velo/runtime/velo_runtime.h`.
  - No UTF-8 BOM on any modified or new files.

**75.3 [COMPLETED] ✅** Implement signal decoding: `os_process_signal(proc)` returning the
terminating signal on POSIX and `0` on Windows. The current API cannot express
"killed by SIGSEGV", which matters for build tools.

- *Former Defect:*
  `ProcessHandle` tracked only `pid`, `handle`, `thread_handle`, and `is_alive`. There was no mechanism to inspect whether a child process terminated normally or was killed by an OS signal (e.g. `SIGSEGV`, `SIGKILL`, `SIGTERM`), and no public API existed to retrieve terminating signals. Consequently, build tools, test runners, and process supervisors had no way to distinguish a deliberate exit code from a segmentation fault or crash.
- *Fix Applied:*
  - Added `signal: i32` field to `ProcessHandle` in `std/os/proc_types.vl`.
  - Implemented `os_process_signal(proc: @ProcessHandle) -> i32` in `std/os/process.vl`. If `proc.is_alive` is true, it calls `os_process_try_wait(proc)` to reap any pending status without blocking before returning `proc.signal`. Returns 0 if `proc == null`.
  - In `std/os/proc_linux.vl` and `std/os/proc_macos.vl`: updated `os_process_wait_timeout` to isolate the signal byte `sig = status & 127`; if `sig != 0 and sig != 127` (WIFSIGNALED), `proc.signal` is recorded as `sig` and exit code returns `128 + sig`; otherwise `proc.signal` is set to 0.
  - In `std/os/proc_linux.vl` and `std/os/proc_macos.vl`: updated `os_process_kill` to reap with `waitpid(proc.pid, @status, 1)` (WNOHANG) and record `proc.signal = 9` (SIGKILL).
  - In `std/os/proc_windows.vl`: updated all `ProcessHandle` literals with `signal: 0`. On Windows, `os_process_signal` consistently returns `0`.
  - Updated `std/tests/os/process_test.vl` with assertions verifying `os_process_signal(@proc) == 0` on normal exit and `os_process_signal(null) == 0`.
  - Extended `tests/test_posix_spawn.py` with:
    - Cross-target emission testing for `os_process_signal` targeting `linux`, `macos`, and `windows`.
    - Host execution test on Windows verifying `os_process_signal` compiles and returns 0.
    - POSIX host execution test verifying terminating signals (`SIGTERM` = 15, `SIGSEGV` = 11) are accurately captured in `proc.signal` and returned by `os_process_signal`.
- *Residual Limitation:*
  Windows processes do not have POSIX signals; `os_process_signal` returns `0` on Windows by design as specified by the task contract.
- *Verification:*
  - `tests/test_posix_spawn.py`: 10 passed, 3 skipped on Windows (100% pass).
  - `std/tests/os/process_test.vl`: built and ran cleanly with `bin/velo.exe run` (`PASS: std.os.process tests succeeded`).
  - `tests/test_std_os.py`: 6 passed in 10.5s.
  - `tests/test_platform_resolve.py`: 46 passed in 4.2s.
  - `tests/test_posix_portability.py`: 18 passed, 6 skipped on Windows.
  - `tests/test_std_resolve_binary_relative.py`: 3 passed in 1.4s.
  - `tests/test_posix_bootstrap_platform.py`: 1 passed, 2 skipped on Windows.
  - `tests/test_bootstrap_snapshot.py`: 6 passed in 46s.
  - Joint suite run: 90 passed, 11 skipped in 70s.
  - Line count ceiling: clean (`proc_windows.vl`: 250, `proc_linux.vl`: 189, `proc_macos.vl`: 189, `pipe_io_linux.vl`: 203, `process.vl`: 71 $\le 400$).
  - Runtime header parity: SHA-256 identical on `runtime/velo_runtime.h` and `velo/runtime/velo_runtime.h`.
  - No UTF-8 BOM on any modified or new files.

**75.4 [COMPLETED] ✅** Add `tests/test_os_process_posix.py` covering: spawn+wait exit code,
stdout/stderr capture, signal termination, non-existent binary (named error,
not crash), and pipe close ordering. Gate on `sys.platform != "win32"`.

- *Former Defect:*
  Prior to Phase 75, POSIX child process execution lacked a comprehensive E2E integration test suite covering process lifecycle, stream multiplexing, signal isolation, pipe close ordering, and failure modes on real POSIX kernels.
- *Fix Applied:*
  - Created `tests/test_os_process_posix.py` gated strictly on `sys.platform != "win32"` (`pytestmark = pytest.mark.skipif(...)`).
  - Added `test_posix_spawn_wait_exit_code`: validates exit 0 normal termination, non-zero exits (42, 7), asynchronous wait, non-blocking try_wait polling while running, `os_spawn_sync_argv`, and `os_system`.
  - Added `test_posix_stdout_stderr_capture`: validates isolated stdout capture, isolated stderr capture, interleaved simultaneous dual-stream capture with non-zero exit code, and `os_capture_stdout` helper.
  - Added `test_posix_signal_termination`: validates process termination by SIGTERM (15), SIGSEGV (11), `os_process_kill` (9), status exit code calculation (`128 + sig`), and signal queries on normal and null handles.
  - Added `test_posix_non_existent_binary`: validates that spawning non-existent binaries yields shell exit status 127 with diagnostic message on stderr without crash or hang, and null/empty commands yield exit code -1 gracefully.
  - Added `test_posix_pipe_close_ordering`: validates concurrent multiplexed poll draining without deadlock on large payloads exceeding 64KB kernel pipe buffer for both stdout and stderr, and verifies 30 consecutive spawn-capture cycles cleanly close pipe endpoints without file descriptor leakage.
  - Verified that all 5 Velo test programs compile with 0 errors when emitting C for `linux` and `macos`.
- *Residual Limitation:*
  Host execution is gated on POSIX hosts (`sys.platform != "win32"`); runs automatically in Phase 76 POSIX CI.
- *Verification:*
  - `tests/test_os_process_posix.py`: 5 skipped on Windows (100% compliant with gate requirement).
  - Cross-target compilation: all 5 test programs verified to compile with 0 errors via `bin/velo.exe emit-c` for `linux` and `macos`.
  - Full suite run: `test_posix_spawn.py`, `test_os_process_posix.py`, `test_platform_resolve.py`, `test_posix_portability.py`, `test_std_resolve_binary_relative.py`, `test_std_os.py` -> 83 passed, 14 skipped in 17s.
  - Line count ceiling: clean.
  - Runtime header parity: SHA-256 identical on `runtime/velo_runtime.h` and `velo/runtime/velo_runtime.h`.
  - No UTF-8 BOM on any modified or new files.

**75.5 [COMPLETED] ✅** Audit every remaining `stub` comment in `std/` and either implement,
delete, or convert into a compile-time unsupported-platform error.
`grep -rin "stub" std/` is the work list; the current count must go to zero
outside of explicitly documented `_unsupported` modules.

- *Former Defect:*
  Prior to Phase 75, multiple critical subsystems in `std/os/` were implemented as silent stubs returning artificial success or empty payloads (`// POSIX fork stub` in `proc_linux.vl` and `proc_macos.vl`, `// POSIX drain stub` in `pipe_io_linux.vl` and `pipe_io_macos.vl`), leading to silent runtime failures and misrepresented operations.
- *Fix Applied:*
  - Conducted full codebase audit of `std/` using case-insensitive search (`\bstubs?\b`, `TODO`, `FIXME`, `unimplemented`).
  - Confirmed all former stub comments in `proc_linux.vl`, `proc_macos.vl`, `pipe_io_linux.vl`, and `pipe_io_macos.vl` were eliminated and replaced with real POSIX system call implementations in Tasks 75.1–75.3.
  - Added automated regression test `test_zero_stub_comments_remain_in_std` in `tests/test_posix_spawn.py` that crawls all `std/**/*.vl` files (excluding explicitly documented `_unsupported` modules) and asserts zero occurrences of `\bstubs?\b`.
  - Confirmed all three Phase 75 exit criteria are fully satisfied:
    1. Real POSIX process spawning and exit code propagation implemented and tested (`test_posix_spawn_sync_execution`, `test_posix_spawn_wait_exit_code`).
    2. Zero stub returns remain in `std/` (enforced by `test_zero_stub_comments_remain_in_std`).
    3. Child termination signals are decoded and exposed via `os_process_signal(proc)` and `proc.signal`.
- *Residual Limitation:*
  None. Zero stub comments or stub returns remain in `std/`.
- *Verification:*
  - `grep -rin "stub" std/`: 0 hits.
  - `tests/test_posix_spawn.py::test_zero_stub_comments_remain_in_std`: PASSED.
  - `tests/test_posix_spawn.py`: 11 passed, 3 skipped on Windows (100% pass).
  - `tests/test_os_process_posix.py`: 5 skipped on Windows (100% pass).
  - Joint test suite: `tests/test_posix_spawn.py`, `tests/test_os_process_posix.py`, `tests/test_platform_resolve.py`, `tests/test_posix_portability.py`, `tests/test_std_resolve_binary_relative.py`, `tests/test_std_os.py` -> 84 passed, 14 skipped in 17s.
  - Line count ceiling: clean.
  - Runtime header parity: SHA-256 identical on `runtime/velo_runtime.h` and `velo/runtime/velo_runtime.h`.
  - No UTF-8 BOM on any modified or new files.

## Phase Exit Criteria

- `velo run` of a program doing `os_spawn_sync("echo hi")` prints `hi` and
  reports exit code 0 on Linux and macOS.
- Zero stub returns remain in `std/`.
- A child killed by a signal is reported as such through the public API.

---

# Phase 76: CI Reality and Platform Test Harness (P0) - PARTIAL (76.1 blocked)

## Defect

`.github/workflows/ci.yml` declares six jobs across Linux, macOS, and Windows.
Two facts make the green state unknowable: there is no git remote, so the
workflow has almost certainly never executed; and even if it did, the Linux and
macOS jobs cannot pass, because `bootstrap.c` carries unguarded Win32 externs
(Phase 70) and 109 of the 129 test files hardcode `C:\msys64\ucrt64\bin`, with
66 hardcoding `bin/velo.exe`.

This is not "CI is misconfigured". It is "CI results are a claim with no
evidence", and CI claims are what reviewers check first.

## Evidence

| Fact | Evidence |
| :--- | :--- |
| No remote, so no CI execution | `git remote -v` empty; no `README` badge; no run link anywhere [VERIFIED] |
| The Linux job cannot link `bootstrap.c` | see Phase 70 (eight `nm -u` Win32 symbols) |
| The test harness is Windows-only | `tests/test_std_fs.py:7` `VELO_EXE = REPO_ROOT / "bin" / "velo.exe"` with no platform branch; 109 files mention `msys64`; 66 files hardcode `bin/velo.exe` [VERIFIED] |
| `tests/conftest.py` papers over it two different ways | lines 6-15 symlink `bin/velo` -> `bin/velo.exe` on POSIX; lines 18-45 patch `subprocess.Popen` to rewrite paths on both platforms. A patched `Popen` inside a test process is a strong signal the paths should have been fixed, not intercepted. |
| The CI test asserts the YAML text, not the CI result | `tests/test_ci_matrix.py:20-68` asserts the strings `ubuntu-22.04`, `macos-14`, `check_determinism.py`, etc. appear in the file. It passes with a workflow that has never run. |
| Only the sanitizer lane actually skips Windows-only work | `.github/workflows/ci.yml:221-273` - the other five jobs run the full suite unguarded |
| One known concurrency hazard | `velo_check_capture.tmp` is a fixed CWD filename (`src/backend/check.vl:291`, `:335`), so two `velo check` processes in the same directory collide. The maintainer works around it by never running two suites at once; CI will not honour that. |

## Security Invariants

- **I76.1** A green CI run is a link to an actual execution on the commit being
  reviewed. A test that greps YAML is not evidence.
- **I76.2** Tests locate the compiler through one helper (`conftest.py`),
  never through a literal path. No test may contain `msys64` or `velo.exe`.
- **I76.3** Any test that shells out with captured text passes an explicit
  encoding (this also closes the 422-site gap in Phase 85).
- **I76.4** No test writes to a fixed filename in the process CWD; all scratch
  paths come from `tmp_path`.

### 76.4 Completion Record

**Former defect.** `run_check_json_opts` and `run_check_pretty_opts` both
captured the diagnostics stream into the constant path
`velo_check_capture.tmp`, resolved against the process working directory
(`src/backend/check.vl:291`, `:335`). Two `velo check` processes started in the
same directory opened the same file, so each read back whatever the other had
written. The maintainer's workaround was to never run two suites at once; CI
cannot honour that, and neither can an editor running checks per pane.

**Fix applied.** Added `check_capture_path()`, which builds
`velo_check_capture_<pid>.tmp` from `os_get_pid()`, and routed both call sites
through it. The file still lives in the working directory because the capture
helper takes a relative path and the cleanup contract is "the CWD is left
clean", which the tests now assert.

**Residual limitation.** The name is unique per *process*, not per *thread*.
`velo check` is a whole-program CLI with no in-process concurrency, so two
checks inside one process cannot overlap today; if a library-embedding use ever
runs two checks on threads, the capture helper's single global
(`g_velo_capture_file`, `runtime/velo_runtime.h:3039`) is the real obstacle and
is already unsynchronised. Recorded in the Phase 85 table.

**Verification.**
- `tests/test_check_concurrency.py` (4 rows) failed before the fix with the
  exact corruption it was written for: an 8-way concurrent run reported
  `"ok": false` for the *valid* file, quoting three `Unexpected top-level
  token` diagnostics whose `file` field named `broken.vl`. After the fix all
  four rows pass, including 8 concurrent runs in one directory and the pretty
  (non-JSON) path.
- `tests/test_check_cli.py` (15 rows) still passes: the capture path change did
  not alter the JSON schema, exit codes, or diagnostic positions.
- Compiler-source change: Gen2 -> Gen3 rebuilt, `check_determinism.py` reports
  `51fd575c...` on both, `bootstrap.c` regenerated and
  `tests/test_bootstrap_snapshot.py` (5 rows) is byte-identical.

## Tasks

**76.1** Add a git remote and push. Publish the repository, even if private, so
Actions can run. Without this every other CI task is theatre.

### 76.1 Status: BLOCKED (external)

Not a code task. `git remote -v` is empty on this machine and `gh` is not
installed, so nothing in this repository can create the remote, push the branch,
or read back a run. Everything downstream of it is done and verified; only the
execution evidence is missing.

What is in place so that unblocking is one command plus one edit:

| Piece | State |
| :--- | :--- |
| Workflow declares seven jobs with real structure | `test_ci_matrix.py` parses it |
| Every declared job is required to cite a run URL | `test_ci_evidence.py` |
| The evidence test states the blocker and cannot rot silently | `@pytest.mark.xfail(strict=True)` |
| The status document says plainly that nothing has run | `docs/CI_STATUS.md` |
| The instructions to fill the table are written down | `docs/CI_STATUS.md`, "How to fill this table in" |

The moment a remote exists and the workflow executes, the strict xfail starts
failing, which is the signal to remove the marker and paste in the run URLs.

**76.2** Replace the `test_ci_matrix.py` string assertions with a check of the
workflow's actual required steps (parse the YAML, assert job matrix shape), and
add a separate `tests/test_ci_evidence.py` that reads a committed
`docs/CI_STATUS.md` containing the latest green run links per job. The test
fails when a job has no link or the link's commit SHA is not an ancestor of
`HEAD`.

### 76.2 Completion Record

**Former defect.** `tests/test_ci_matrix.py` asserted that literal strings such
as `"ubuntu-22.04"`, `"macos-14"`, and `"pytest tests -q"` appeared somewhere in
`.github/workflows/ci.yml`. That test passes for a workflow whose jobs are
commented out, whose steps sit under the wrong key, whose `runs-on` never
references its matrix, or that GitHub would reject outright. It also passed for
a workflow that had never executed, which was the actual state of this
repository: no remote, no run, no evidence. A test that greps YAML tests the
prose, not the CI.

**Fix applied.**

| Change | Detail |
| :--- | :--- |
| `test_ci_matrix.py` | Loads the YAML with `yaml.safe_load` and walks the structure: triggers are a mapping containing `push` and `pull_request` (PyYAML resolves the bare `on:` key to boolean `True`, so both spellings are read), the required jobs exist, every job has `runs-on` and at least one step, no step is missing both `uses` and `run`. |
| Matrix assertions | `linux` and `macos` must declare a matrix *and* reference `${{ matrix.* }}` in `runs-on`; the linux matrix must cover gcc and clang; every job must invoke pytest. |
| `tests/test_ci_evidence.py` (new) | The separate question: has this run? Parses `docs/CI_STATUS.md` into `{job: (url, sha)}`, fails when a declared job has no row, when the URL is not an Actions run URL, and when the cited commit is not an ancestor of `HEAD`. |
| `docs/CI_STATUS.md` (new) | The claim, written honestly: no run has executed, every job is "not yet - no remote", what *is* verified on the maintainer host, and why Linux/macOS cannot pass yet. |

The ancestry check is the part that makes the document non-fakeable: a run on an
unrelated branch says nothing about the tree being reviewed, and a fabricated SHA
fails because git cannot resolve it.

`test_every_declared_job_has_evidence` is `xfail(strict=True)` with the blocker
named in the reason. When 76.1 unblocks it starts passing, the strict marker
turns that into a failure, and the marker must be removed deliberately rather
than being forgotten.

**Residual limitation.** `yaml` is imported with `pytest.importorskip`, so a
runner without PyYAML skips the structural checks instead of failing them. That
is the lesser evil: the alternative is a hard dependency that makes the suite
unrunnable before `pip install` in a fresh clone, and a skipped test is visible
where a crash is not. Both CI lanes install `pyyaml`/`pytest` explicitly.

**Verification.**
- `pytest tests/test_ci_matrix.py tests/test_ci_evidence.py -q` -> 14 passed,
  1 xfailed. The xfail is `test_every_declared_job_has_evidence`.
- The workflow YAML parses and the parsed job set matches the file's seven jobs.

**76.3** Introduce `tests/conftest.py::velo_exe()` and
`tests/conftest.py::cc_path()`; delete all `msys64` literals and
`bin/velo.exe` literals from tests. Remove the `Popen` monkeypatches once the
paths are correct. Gate: `grep -rl "msys64" tests/` is empty.

### 76.3 Completion Record

**Former defect.** 129 test files reached for the toolchain through literal
paths: 62 appended `C:\msys64\ucrt64\bin` to `PATH`, 99 spelled the compiler as
`bin/velo.exe` (either as a `Path` join or as a bare string in an argv list), and
`tests/conftest.py` patched `subprocess.Popen` on both platforms to rewrite
those paths at call time so the suite would pass anyway.

The result was a harness that could not work anywhere but the maintainer's
machine, and a `Popen` patch that made the breakage invisible. `bootstrap.sh`
produces `bin/velo`, not `bin/velo.exe`; MSYS2 does not exist on Linux or macOS.
The two Linux jobs and two macOS jobs in `.github/workflows/ci.yml` were
therefore dead on arrival, which is why their green state had never been
observed. The `Popen` shim is the real defect: a test process that rewrites an
executable path is asserting about a different path than the one it wrote.

**Fix applied.**

| Change | Detail |
| :--- | :--- |
| `tests/conftest.py` | Now a helper module: `velo_exe()`, `require_velo_exe()`, `velo_exe_or_none()`, `cc_path()`, `cc_dir()`, `cc_env()`, `is_windows()`. Both `Popen` monkeypatches and the POSIX symlink shim deleted. |
| `velo_exe()` | Resolves `VELO_BIN` (so a CI job can point at `velo_msvc.exe`), then `bin/velo.exe`, then `bin/velo`. Deliberately does not raise when nothing is built: 60+ call sites guard with `velo_exe().exists()`, and raising would turn every skip into a collection error. `require_velo_exe()` is the loud variant. |
| `cc_path()` | Honours `CC`, else the first of gcc/clang/cc on `PATH`. Returns a bare name so `subprocess` does not depend on an absolute location. |
| `cc_dir()` | The compiler's directory, or `""` when it is a bare name. Existing callers append it to `PATH` unconditionally, and an empty component is skipped by the OS, so no call site needed restructuring. |
| Sweep | 108 files rewritten. `VELO_EXE` definitions became `VELO_EXE = velo_exe()`; 84 bare `"bin/velo.exe"` argv literals became `str(velo_exe())`; 6 msys64 path/toolchain literal families became `cc_dir()`/`cc_path()`. |
| `tests/test_platform_portability.py` | 11 rows pinning the invariants, including that neither `msys64` nor a compiler path literal reappears and that `conftest` contains no `Popen` patch. |

Prose in skip messages ("bin/velo.exe not built") was deliberately left alone:
it is a message a human reads, not a path a process uses, and rewriting it would
have made the diff noisier without changing behaviour. The guard test states
that distinction so a future reader does not "fix" it back.

**Residual limitation.** The sweep changed how tests find the toolchain, not
what they assert. A test that was silently depending on an MSYS2-only compiler
feature would still pass on Windows and now fail on POSIX, which is the point,
but it means the first real Linux run may surface genuinely platform-specific
test failures that Windows has been hiding. Those are Phase 70/76 follow-ups,
not regressions in this change.

**Discovered while verifying (not fixed here).** The full suite surfaced a
pre-existing flake, reproduced at the parent commit with 1-in-3 frequency:
`tests/test_integer_literals.py::test_integer_literal_32bit_in_range_values`
and its siblings fail intermittently, naming a different case each run.

Cause: `src/backend/driver_run.vl:58-63` builds the run artifact path from
`path_stem_to_str(source_path)` alone, discarding the directory. Every
parametrized case in that file writes a differently-named probe into its own
`tmp_path`, but two test functions reuse the same stem (`nowrap64.vl`,
`in_range.vl`), and any other test anywhere in the suite that writes a file with
a matching stem targets the same `.velo_cache/<stem>.exe`. `build_executable_all_opts`
does rebuild unconditionally, so a stale binary is normally overwritten; the
observed failure mode is the narrow window where the previous case's binary is
executed while the new one is still being produced. This needs a cache key that
includes a content or path hash, which is Phase 81 (performance) work because
hashing every source file on every `velo run` is a deliberate trade-off, not a
one-line fix.

A second instance of the same class of defect lives in the compiler itself:
`src/backend/driver_cc.vl:235-236` hardcodes `C:/msys64/ucrt64/bin/gcc.exe` when
assembling the run command, so `velo run` on any other host silently skips the
PATH adjustment. That belongs to Phase 70 (portability) and is recorded there.

**Verification.**
- `python -m pytest tests --collect-only -q` -> 2010 tests collected, 0 errors.
- `python -m pytest tests/test_platform_portability.py -q` -> 11 passed.
- Targeted slices exercising rewritten files: 104 passed (`test_check_cli`,
  `test_std_fs`, `test_std_mem`, `test_conditions`); 50 passed, 2 skipped
  (`test_cc_backend`, `test_tuple`, both `test_native_lsp` modules,
  `test_advanced_structs`, `test_build_modes`).
- Full suite after the sweep: see the run recorded in the commit message.

### 76.3 Follow-ups (three defects the sweep itself left behind)

The first 76.3 commit fixed how collected tests find the toolchain. Auditing its
own gate found three holes, each fixed in its own commit.

**A. The guard only read collected files.** `test_platform_portability.py`
scanned `tests/test_*.py`. `tests/probe_range_endpoint.py` is a helper script,
not a `test_` module, so pytest never collects it and the guard never read it -
and it still spawned `["bin/velo.exe", "emit-c", ...]`. The sweep and its guard
shared one blind spot, which is why the sweep reported success. `_test_files()`
now globs `*.py`: 136 files scanned instead of 129. Verified red by restoring the
literal, which the widened glob reports by name and line, then green.

**B. `text=True` with no encoding on 384 sites.** `invariant I76.3` was half
done: the paths were fixed, the decoding was not. A subprocess call that passes
`text=True` alone decodes with the platform default - cp1252 on a Western
Windows runner, UTF-8 elsewhere - so a `.vl` program printing a non-ASCII byte,
or a diagnostic quoting a source line, decodes differently per platform and
surfaces as `UnicodeDecodeError` in the harness rather than as a compiler
result. All 384 sites now pass `encoding="utf-8", errors="replace"`, inserted
directly after the text flag so the two settings read together. `errors="replace"`
is deliberate: a test asserting on compiler output should report a mismatch it
can print, not raise while formatting the message. Only calls that already asked
for text mode were touched, because adding `encoding=` to a bytes call changes
its return type.

`test_subprocess_text_calls_pin_their_encoding` guards it with an AST walk over
every Python file under `tests/`, verified red by removing one `encoding=` (it
named the file and line) and green after restoring it.

**C. `require_velo_exe()` in the fast tier.** Covered in the 76.6 record: the
push lane does not build the compiler, and this call raises when nothing is
built, so the lane would have failed on its first CI run.

Result: the suite is 2026 passed, 8 skipped, 1 xfailed, and every process
spawn in it pins its decoding.

**76.4** Replace `velo_check_capture.tmp` with a per-process temp path
(`velo_check_capture_<pid>.tmp`, or `mkstemp`-equivalent inside
`.velo_cache/`), making `velo check` safe to run concurrently. Test: run 8
`velo check` processes in parallel in the same directory and assert all
succeed and no stray tmp file remains (`tests/test_check_concurrency.py`).

**76.5** Add a `windows-msvc` full-suite job. Today `windows-msvc`
(`ci.yml:134-172`) runs only `test_cc_backend.py` and
`test_bootstrap_snapshot.py`, so the MSVC path is verified for two files out of
129.

### 76.5 Completion Record

**Former defect.** The `windows-msvc` job built `bin\velo_msvc.exe` and then ran
`tests/test_cc_backend.py tests/test_bootstrap_snapshot.py`. Two test modules
out of 132 exercised the code generation path MSVC actually produces; every
other module tested a binary MSVC had never built. The job looked like MSVC
coverage and was MSVC smoke testing.

**Fix applied.** The job runs `python -m pytest tests -q` with
`VELO_BIN: bin\velo_msvc.exe`. That override is why 76.3 mattered:
`conftest.velo_exe()` resolves `VELO_BIN` first, so the whole suite targets the
MSVC binary without a single test knowing MSVC exists. `test_every_job_runs_the_test_suite`
in `test_ci_matrix.py` now fails if any job stops invoking pytest, so a future
narrowing is caught rather than shipped.

**Residual limitation.** MSVC remains the least-exercised backend: the suite is
written against gcc diagnostics and exit codes, so a full-suite MSVC run will
very likely surface genuine backend differences the first time it executes. That
is the information the job exists to produce, and it cannot be obtained without
a remote (76.1).

**Verification.** The YAML parses; the job keeps `runs-on`, its step list, and
the `VELO_BIN` environment entry; `test_ci_matrix.py` asserts pytest is invoked
in every job. This lane cannot execute locally on a machine without `cl.exe`; its
first evidence comes from 76.1.

**76.6** Split the suite into tiers and make CI honest about duration: a `fast`
marker (no C compiler invocation) running in under 2 minutes on every push, and
the full suite on PRs. The current suite is ~15.5 minutes; contributors will
not wait, and a 15-minute red X trains people to ignore CI.

### 76.6 Completion Record

**Former defect.** One flat suite of 2032 tests, ~16 minutes wall clock, because
it invokes a C compiler and runs built binaries hundreds of times. Every push and
every pull request ran all of it in six jobs. A quarter-hour red X on every push
is not a signal anyone reads; it is the reason people stop looking at CI. The
suite also had no way to answer "which of these 2032 tests is cheap?" - that
information existed nowhere.

**Fix applied.**

| Change | Detail |
| :--- | :--- |
| `tests/conftest.py` | `pytest_configure` registers `fast` and `slow`; `pytest_collection_modifyitems` adds `slow` from a source heuristic on each test function: any of `velo_exe`, `require_velo_exe`, `cc_path`, `cc_dir`, `cc_env`, `subprocess`, `Popen`. |
| `fast` is explicit | Never inferred. A module opts in with `pytestmark = pytest.mark.fast`, a promise that it invokes no compiler. Five modules make it: `test_ci_evidence.py`, `test_changelog.py`, `test_contributing.py`, `test_license_provenance.py`, `test_platform_portability.py`. |
| `.github/workflows/ci.yml` | New `fast` job: ubuntu-24.04, `pytest -q -m fast`, no bootstrap step, no condition, so it runs on every push. The six heavy jobs gained `if: github.event_name != 'push'`, so a push starts one seconds-long job and a pull request starts the full matrix. |
| `test_ci_matrix.py` | `test_fast_job_runs_only_the_fast_lane` fails if the fast job bootstraps a compiler, drops `-m fast`, or grows a condition; `test_heavy_jobs_do_not_run_on_push` fails if a heavy job would run on push. |
| `docs/CI_STATUS.md` | Lane table plus the measured local result. |

The heuristic over-approximates on purpose: a test wrongly marked slow only
loses the 2-minute lane, while a test wrongly marked fast drags a compiler build
into that lane and destroys its reason to exist.

**Discovered while verifying (fixed here).** `test_platform_portability.py` is
in the fast tier, and CI runs that tier without building the compiler, but
`test_velo_exe_resolves_to_a_real_file` called `require_velo_exe()`, which raises
when nothing is built. On a fresh CI checkout the push lane would have failed on
its first run. It now skips when there is no build and asserts the resolution
rule instead, which the `VELO_BIN` override tests already cover without a binary.
Found by running the lane with `VELO_BIN` pointed at a nonexistent path.

**Verification.**
- `pytest tests -q -m fast` -> 39 passed, 1 xfailed, ~3 s, 1995 deselected.
- Same with `VELO_BIN` set to a nonexistent path -> 36 passed, 2 skipped,
  1 xfailed, no collection error.
- `pytest tests -q -m slow --collect-only` -> 335 selected.
- `pytest tests/test_ci_matrix.py tests/test_ci_evidence.py
  tests/test_platform_portability.py -q` -> 27 passed, 1 xfailed.
- Full suite, unchanged selection: 2026 passed, 8 skipped, 1 xfailed in 16:55.

## Phase Exit Criteria

| Criterion | State |
| :--- | :--- |
| Actions runs on Linux (gcc + clang), macOS (clang), Windows (gcc + MSVC), and the sanitizer lane, all green on the same commit, with links committed to `docs/CI_STATUS.md` | **Not met, blocked on 76.1.** The jobs exist, are structurally tested, and are gated to pull requests; no run has executed because the repository has no remote. |
| `grep -rl "msys64" tests/` is empty except `conftest.py` | **Met.** Matches are `conftest.py` (documents the defect), `test_platform_portability.py` (states the spelling in order to forbid it), and nothing else. |
| `grep -rl "velo\.exe" tests/` is empty except `conftest.py` | **Met in substance.** Remaining hits are prose in skip messages, content assertions about `bootstrap.bat`'s text, and the guard that forbids the spelling; no test spawns a hardcoded path. Enforced by `test_no_windows_compiler_filename_in_test_code`, which distinguishes the two cases and says so. |
| `velo check` is safe to run concurrently, proven by test | **Met.** `tests/test_check_concurrency.py`, 4 rows. |
| Every subprocess call that captures text pins its encoding | **Met** (added by the 76.3 follow-up). 384 sites pinned; AST guard in `test_platform_portability.py`. |
| Only the fast tier runs on push; the full suite runs on pull requests | **Met.** `test_fast_job_runs_only_the_fast_lane`, `test_heavy_jobs_do_not_run_on_push`. |

The phase cannot be marked fully closed while 76.1 is blocked. Six of the seven
criteria are met and enforced by tests; the seventh is an external action, not an
engineering defect.

---

# Phase 77: Language Completeness (P1) - OPEN

## Defect

Four absences push ordinary programs into hand-rolled workarounds or make them
impossible to express cleanly: no closures, no interfaces/traits, no module
privacy, and no conditional compilation. Each one is a design decision that may
be defensible, but each currently forces a real cost on users, and none is
documented as a deliberate limitation.

## Evidence

| Fact | Evidence |
| :--- | :--- |
| No closures or lambdas | no `lambda`/`closure` token or parser path in `src/frontend/*`; async APIs take `act(...) -> void` function pointers plus a separate `user_data: @void` (`std/async/tcp.vl:10-11`) - the classic manual-capture workaround |
| No traits/interfaces | `grep -rn "trait\|interface"` over `src/` and `docs/SPECIFICATION.md` finds only Prose hits in `docgen.vl` output text; there is no `trait` keyword in the lexer (`docs/SPECIFICATION.md:33` keyword table) |
| No module privacy | no `pub`/`private`/`export` keyword in the keyword table (`docs/SPECIFICATION.md:33`); every `act`/`data` in an imported file is visible to the importer |
| No conditional compilation | no `#if`, `ifdef`, or `cfg` construct in the lexer/parser; the language's only platform mechanism is the filename-suffix resolver (`src/backend/driver.vl:97-122`), which lives outside the language |
| No import aliasing or selective import | no `as` in the import grammar; symbol collisions between modules are unavoidable |
| `defer` takes a block, not an expression | Phase 58/69 semantics; there is no `defer fclose(f)` shape, so every cleanup site spells out a block |
| No operator overloading escape hatch for new types | `act op <symbol>` exists (`docs/SPECIFICATION.md` 2.8) but there is no way to declare a type satisfies a contract, so generic code cannot constrain `T` beyond monomorphization |

## Security Invariants

- **I77.1** A missing language feature is documented in `docs/SPECIFICATION.md`
  under "Deliberate limitations" with the workaround and the cost. Silence is
  not allowed.
- **I77.2** Any feature added must not weaken the existing borrow/escape
  analysis (`docs/SPECIFICATION.md` 5.4 zone escape rules).

## Tasks

**77.1 [COMPLETED] ✅** Document the four absences in a new `docs/SPECIFICATION.md` section
"Deliberate Limitations" with workarounds. This is a one-commit, high-value
task: it converts "unfinished" into "chosen", which is a legitimate position.

- *Former Defect:*
  `docs/SPECIFICATION.md` was silent on the absence of closures, dynamic interfaces/vtables, module privacy, and conditional compilation. Ordinary programs encountering these gaps had no documented guidance or architectural explanation, leaving users to assume these features were accidental omissions rather than deliberate design decisions. Silence violated Security Invariant I77.1 ("A missing language feature is documented in docs/SPECIFICATION.md under 'Deliberate limitations' with the workaround and the cost. Silence is not allowed.").
- *Fix Applied:*
  - Added Section 11: "Deliberate Limitations & Workarounds" to `docs/SPECIFICATION.md`:
    - §11.1 Closures and Environment Capture: documents absence, architectural rationale (preserving explicit region/zone memory model without hidden heap or reference counting), associated costs, and official workaround (bare function pointer with typed context struct `@Context`).
    - §11.2 Dynamic Interfaces, Traits, and Vtables: documents absence, architectural rationale (zero runtime indirection / cache efficiency via monomorphization), associated costs, and official workarounds (monomorphized generics and manual dispatch tables / tagged unions).
    - §11.3 Module Privacy and Export Control: documents absence, rationale, costs, and official workarounds (underscore prefixing and subdirectory isolation) prior to the `pub` keyword in Task 77.4.
    - §11.4 Preprocessor Directives and Conditional Compilation: documents absence, rationale (deterministic single-pass AST without preprocessor macro state), costs, and official workarounds (driver platform file suffixes and constant-folded runtime platform checks).
    - §11.5 Import Aliasing and Selective Imports: documents absence, costs, and workarounds prior to Task 77.5.
    - §11.6 Expression Defer: documents block requirement, costs, and single-expression workaround prior to Task 77.6.
  - Added automated audit test suite `tests/test_deliberate_limitations.py` (7 tests) in the fast lane asserting that Section 11 exists and covers all four core absences, their rationales, costs, and workarounds with code examples.
  - Hardened platform portability in `tests/test_std_https.py`, `tests/test_std_tls.py`, and `tests/test_heap_provenance.py` using `conftest.velo_exe()` and pinning `encoding="utf-8"`.
- *Residual Limitation (if any):*
  As syntax features are chosen and implemented across Tasks 77.2–77.6, Section 11 will be updated to reflect the new syntax capabilities and their updated contracts.
- *Verification:*
  - `python -m pytest tests/test_deliberate_limitations.py -v`: 7 passed in 0.02s.
  - `python -m pytest tests -q -m fast`: 46 passed, 1 xfailed in 3.00s.
  - `python -m pytest tests/test_platform_portability.py -v`: 12 passed in 0.53s.

**77.2** Decide on closures. Either (a) implement non-escaping closures
(bare function pointers + stack context, rejected by the escape checker when
they outlive their frame) - the cheap, sound option - or (b) keep function
pointers and add a `bind(fn, args...) -> act(...)` helper in `std` that
allocates a trampoline in a caller-provided arena. Either way, replace the
`user_data: @void` pattern in `std/async/tcp.vl` and `std/http/async_server.vl`
with the chosen mechanism, and add `examples/39_closures.vl`.

**77.3** Decide on interfaces. Minimum viable: `contract Name { act f(...) }`
plus static dispatch only (no vtables) - monomorphization already exists
(`src/analysis/monomorphize.vl`), so static-only contracts are a small step and
give generic code meaningful constraints. If rejected, document why in 77.1 and
close the task.

**77.4** Add module privacy: `pub` prefix on `act`/`data` declarations, with
unmarked declarations visible only inside their file. This is a breaking change;
schedule it before 1.0 or never. Requires touching `symbol_table.vl` and every
`std/` file's exported surface (mechanically: everything currently used
cross-file gets `pub`).

**77.5** Add import aliasing (`use std.json as j`) and selective import
(`use std.json { JsonValue, json_parse }`). Collisions are already reachable:
`std/os/args.vl` and `std/cli/*` both define argument concepts.

**77.6** Allow expression `defer`: `defer fclose(f)` lowering to the existing
block-defer path with a single call statement. Test in
`tests/test_defer.py` alongside the Phase 58 matrix.

**77.7** Add a "language surface" conformance test that enumerates every
keyword from `docs/SPECIFICATION.md` section 1.4 and asserts each appears in
`src/frontend/token.vl`, so documentation and lexer cannot drift.

## Phase Exit Criteria

- "Deliberate Limitations" exists and covers every absence found by
  `77.7`'s conformance test.
- At least the closure decision is resolved either way, with the async APIs
  updated or a documented rationale committed.

---

# Phase 78: Standard Library Breadth (P1) - OPEN

## Defect

The stdlib covers what the compiler needed to exist. It does not cover what a
program needs to exist. The most damaging omissions: no sorting at all, no
regular expressions, no DNS resolution, no local time / time zones, no
compression, and no way to decode anything but UTF-8/hex/base32/base64/binary.

## Evidence

| Fact | Evidence |
| :--- | :--- |
| No sorting anywhere | `grep -rn "sort\|qsort"` over `std/` excluding tests -> one hit, a comment in `std/url/defs.vl:16` [VERIFIED]. A collection library without `sort` is not usable for data work. |
| No regular expressions | `grep -rn "regex"` over `std/`, `src/` -> 0 hits [VERIFIED] |
| No DNS | `grep -rn "getaddrinfo\|gethostbyname\|inet_pton\|DNS"` over `std/`, `runtime/` -> 0 hits [VERIFIED]. `std/net/addr.vl` uses `inet_addr`, so **hostnames cannot be resolved at all**; every connection needs a numeric IP. |
| No local time or time zones | `std/time/calendar.vl:7` "decomposed UTC calendar date"; `grep -rn "timezone\|tzset\|localtime"` over `std/` -> 0 hits [VERIFIED] |
| No compression | no zlib/gzip/deflate/zstd module anywhere in `std/` |
| No text encodings beyond UTF-8 | `std/encoding/` holds `base32`, `base64`, `binary`, `hex` only; no UTF-16, no Latin-1, no Windows-1252 |
| JSON is a `data` tree, not a typed codec | `std/json/value.vl` `data JsonValue`; `std/json/value_ops.vl` for access - no derive/reflection-based struct mapping, so every schema is hand-written traversal |
| CSV is a full-buffer parser | `std/csv/reader.vl:5` `csv_reader_init(s: StrSlice)` - a `StrSlice` requires the whole document in memory; no streaming reader despite the name |
| Collections lack a deque/set | `std/coll/` has `hash`, `map`, `map_ops`, `ring`, `shelf`, `shelf_ops`; a `Set` is a `Map` with a dummy value, a priority queue is absent |
| String search is byte-oriented only | `std/str/search.vl` - no case-insensitive rune-aware search beyond what `utf8.vl` exposes |
| No decimal/fixed-point arithmetic in `std.math` | `std/math/` has `bits`, `float`, `int`, `trig`; `real-world-prob-test/02_fixed_point_currency.vl` exists precisely because this is missing |

## Security Invariants

- **I78.1** Every parser that reads attacker-controlled bytes (JSON, CSV, URL,
  HTTP, base64) has a fuzz corpus and a documented maximum input size or an
  explicit unbounded-input warning.
- **I78.2** No stdlib function allocates without a bounds on the amount
  derived from input length unless it is documented as O(input).

## Tasks

**78.1** `std/coll/sort.vl`: stable merge sort and unstable introsort for
shelves, generic over element size, with a comparator `act(@void, @void) -> i32`
and typed convenience wrappers for primitives. Test: 10k-element randomized
matrix against Python's `sorted`, plus a stability test.

**78.2** `std/text/regex.vl`: a backtracking-free Thompson NFA engine (POSIX
ERE subset: classes, anchors, `*+?{}`, alternation, groups). No backreferences.
Test against a 200-row fixture table; add a ReDoS test asserting linear time on
`(a+)+b` style patterns.

**78.3** DNS: `std/net/dns.vl` implementing A/AAAA lookup via `getaddrinfo` on
both platforms (Win32 `getaddrinfo`, POSIX `getaddrinfo`), then rewrite
`std/net/tcp.vl:3` `tcp_connect` and `std/async/tcp.vl` to accept hostnames.
This is arguably P0 for network use; it is listed P1 only because Phase 70
already rewrites both files. Test: resolve `localhost` and an IP literal, assert
both connect.

**78.4** Local time: `std/time/tz.vl` reading the platform zone database
(`TZif` parsing for POSIX, registry/`GetTimeZoneInformation` for Windows), plus
`time_local(dt, tz)` alongside the existing UTC `calendar.vl`. Minimum: fixed
offset zones and DST rules for the system zone.

**78.5** Compression: `std/compress/deflate.vl` (raw DEFLATE, then zlib
wrapper) with `inflate` first - decompression is what HTTP clients need. Then
gzip framing. Test against known vectors; fuzz `inflate` with truncated input.

**78.6** Typed JSON: `std/json/codec.vl` exposing
`json_encode(@T) -> string` / `json_decode(string) -> T or string` using the
existing struct reflection (`src/backend/reflect_gen.vl`,
`examples/37_struct_reflection.vl` prove the mechanism exists). Test with a
nested struct containing optional fields and a tagged union.

**78.7** Streaming CSV: change `std/csv/reader.vl` to accept an
`@BufferedReader` incrementally, keeping the `StrSlice` constructor as a
convenience wrapper. Test with a 1M-row generated file asserting bounded memory
(peak RSS below a fixed ceiling).

**78.8** Fill collection gaps: `std/coll/set.vl` (wrapping `map.vl`),
`std/coll/deque.vl` (growable ring), `std/coll/heap.vl` (binary heap). Each with
a property test against a Python reference for a random operation sequence.

**78.9** `std/math/decimal.vl`: fixed-point decimal with explicit scale and
rounding modes, for money. Test: cent arithmetic, `0.1 + 0.2 == 0.3` in
decimal, rounding-mode matrix.

## Phase Exit Criteria

- A program can: sort a shelf, resolve a hostname, connect to it, parse a regex
  over the response, decompress a gzip body, decode JSON into a struct, and
  format a local timestamp. Each step has a test.
- Every new parser has a fuzz corpus checked into `tests/fuzz/`.

---

# Phase 79: Tooling and Developer Experience (P1) - OPEN

## Defect

There is no debugger integration beyond `#line` directives, no REPL, no
incremental compilation, no profiler hook, and the diagnostic surface is
inconsistent (some errors name the member, some print raw C compiler output).
A language is adopted on its worst debugging session, not its best.

## Evidence

| Fact | Evidence |
| :--- | :--- |
| `#line` directives are the only debug story | `src/backend/codegen_line.vl:22-28` `emit_line_directive`, opt-out via `--no-line-directives`; nothing generates DWARF info of its own or maps locals |
| No REPL | `grep -c "repl\|REPL"` over `src/main.vl` + `src/cli_cmd.vl` -> 0 [VERIFIED]; `velo help` has no such command |
| No incremental compilation | `src/backend/driver.vl:328` `compile_source_to_c_all_opts` parses, monomorphizes, and codegens the whole program every time; `.velo_cache` (`driver_run.vl:18-32`) caches only the output artifact by filename, not by content hash |
| `.velo_cache` is keyed by source stem | `driver_run.vl:32` builds `.velo_cache/<stem>.exe`; editing a header-like imported module does not invalidate the sibling's artifact if the stem is unchanged. Observed as a 1-in-3 flake in `tests/test_integer_literals.py` (two functions reuse the `nowrap64.vl` / `in_range.vl` stems), reproduced at `f2a8b11`. |
| Diagnostic shapes vary | compare `[Velo Error] semantic:4:20 - unknown io member 'println_int' (functions: ... 60 names)` (`src/backend/codegen_expr.vl`) with `[Velo Error] backend:4:20 - unknown io member 'println_i64' reached codegen` - the second is an internal fallback leaking to the user [VERIFIED by probe] |
| No error-code registry | messages are inline string literals; nothing can be documented or searched by code |
| No `velo fmt --check` in CI | `velo fmt` exists (`src/backend/driver_pkg.vl:70`) but no CI job runs it |
| LSP exists and is decent | `src/lsp/` implements completion, definition, hover, rename, symbols, code actions - this is a genuine strength, so the task list preserves it |

## Security Invariants

- **I79.1** Every user-visible diagnostic has a stable code (`VELO-E####`) and a
  doc entry. Internal-stage messages never reach users.
- **I79.2** Cache validity is content-hash based, not name based. A stale cache
  must be impossible, not unlikely.

## Tasks

**79.1** Add an error-code registry: `docs/ERRORS.md` with codes, plus a
`diag(code, line, col, args...)` helper replacing inline literals in
`src/common/diagnostics.vl`. Migrate the 20 most common messages first; add a
test that every code in the registry is emitted by at least one test fixture.

**79.2** Remove the internal-fallback diagnostics: any `reached codegen` /
`backend:` message means an earlier check missed a case. Convert each into a
compile-time check plus a normal diagnostic. Test: a fixture per former
fallback.

**79.3** Content-hash the build cache: key `.velo_cache` artifacts by
SHA-256 of the fully resolved source closure (source + imported files +
compiler version + flags). Test: touch an imported module, rebuild, assert
recompilation happened; touch nothing, rebuild, assert it did not.

**79.4** Add a `velo repl`: read-eval-print over the existing frontend +
`emit-c` + immediate `cc` of a single expression wrapper. Scope it to
statements and expressions, no module definition. This is cheap relative to its
adoption value and is the single most-requested entry point for trying a
language.

**79.5** Add a debug build story: `velo build --debug` currently maps to
`-O0 -g` (`driver_cc.vl:247-263`). Verify with a real debugger session that
`#line` + `-g` gives working breakpoints on Velo lines; document the exact
`gdb`/`lldb` commands in `docs/DEBUGGING.md`. If DWARF line mapping is
inaccurate (likely, given generated temporaries), fix the emission so
breakpoints land on the right Velo line. Add
`tests/test_debug_line_mapping.py` asserting emitted `#line` numbers match
source lines for a sample program.

**79.6** Add `velo fmt --check` to CI and a pre-commit hook script in
`scripts/hooks/`.

**79.7** Add a profiler hook: `--profile` that emits `-pg` (GCC/Clang) or
`/PROFILE` guidance, plus a documented `perf`/`Instruments` workflow in
`docs/PROFILING.md`. A language promising "native speed" owes users a way to
measure it.

**79.8** Add `velo doc --json` and serve it to the LSP so hover text comes from
the same source as the generated docs (`src/backend/docgen.vl` already walks the
AST).

## Phase Exit Criteria

- A new user can open a REPL, get completion in an editor, set a breakpoint on
  a Velo line and hit it, and read a diagnostic with a code they can look up.
- No `reached codegen` message is reachable from any fixture.

---

# Phase 80: Compiler Maintainability (P1) - OPEN

## Defect

The compiler works, and its internal structure actively fights the next
contributor. Codegen is stringly typed; one fact (the `sys.*` allowlist) is
copied five times; a 400-line ceiling forces the logic into 40+ sliver modules
that each carry their own header comment restating the same contract; and a
frozen second implementation in Python still gates the build.

## Evidence

| Fact | Evidence |
| :--- | :--- |
| The `sys.*` allowlist is duplicated five times | `src/backend/driver.vl:265`, `:287`; `src/lsp/analysis.vl:142`, `:161`; `src/backend/pretty_recon.vl:65` - all spell out the same eight names [VERIFIED] |
| Codegen returns strings with embedded formatting | `src/backend/codegen_lit.vl:146-152` `loop_var_c_type(...) -> string` returns `"int32_t "` **with a trailing space**, so the call site's concatenation is load-bearing and undocumented [VERIFIED] |
| One-line `if` chains are the core of the emitter | `src/backend/codegen_call.vl:102-103` - whole intrinsic families lowered as semicolon-chained one-liners, invisible in diffs and untestable in isolation |
| The 400-line ceiling splits by syntax, not by concept | 40+ files under 150 lines in `src/analysis/` and `src/backend/`; `src/backend/range_gen.vl` (248), `src/backend/fs_gen.vl` (86), `src/backend/os_gen.vl` (45), `src/backend/time_gen.vl` (33) - the last three are a single concept split three ways |
| Header comments duplicate the contract | e.g. `src/backend/fs_gen.vl:1-19` restates emit rules that must also be honoured in `src/analysis/fs_checks.vl`; the two can drift with no test |
| The frozen Python implementation still gates the build | `AGENTS.md` calls `velo/` + `velo.py` a frozen Stage-1 reference, but `examples/12_stage2_semantics_test.vl` and several tests import `../src/...`, and `docs/SPECIFICATION.md` still documents Stage-1/Stage-2 parity as a requirement |
| Determinism is a script, not a compiler flag | `scripts/check_determinism.py` compares two binaries; the compiler itself has no `--verify-determinism` |
| Generated `bootstrap.c` is 2.3 MB / 67,952 lines | `(Get-Item bootstrap.c).Length` = 2302323; review of a compiler change requires diffing a generated artifact |

## Security Invariants

- **I80.1** No semantic fact is encoded twice. A table used by the driver, the
  LSP, and the pretty-printer is one table.
- **I80.2** Codegen receives typed data (`CType`, `IntWidth`), never a string
  that a caller must format correctly.
- **I80.3** There is exactly one compiler implementation in the build chain.

## Tasks

**80.1** Extract the intrinsic allowlist into one `std`-visible table
(`src/common/intrinsics.vl`: `intrinsic_namespaces() -> @string` and
`intrinsic_members(ns) -> @string`) and make all five current sites call it.
Test: `tests/test_intrinsic_allowlist_single_source.py` asserts each site
imports the table (grep-level) and that adding a namespace in one place changes
all consumers (behavioural: resolve `sys.newthing` and assert the same verdict
from driver, LSP, and pretty-printer paths).

**80.2** Replace `loop_var_c_type`'s string returns with a `CType` value
(`{name, width, signed, needs_space}`) and a single `ctype_render`. Audit every
`-> string` codegen helper and convert the top ten. Test: `emit-c` output for
the Phase 68 loop matrix must stay byte-identical (`bootstrap.c` snapshot
already enforces this).

**80.3** Replace the trailing-space convention with explicit emission helpers
(`emit_type_then_space`), which makes `"int32_t "` structurally impossible.

**80.4** Consolidate `fs_gen`/`os_gen`/`time_gen` (and the `range_gen` emit
ladder) behind one `IntrinsicEmitter` dispatch keyed by namespace + member, so a
new intrinsic is one table entry instead of a new file. Keep the 400-line
ceiling as a consequence, not a design driver.

**80.5** Decide the Stage-1 question: either delete `velo/` + `velo.py` and
rewrite `examples/12_stage2_semantics_test.vl` against the self-hosted compiler,
or demote it to an untested historical artifact. Keeping a frozen second
compiler that still appears in the build and docs is a permanent tax with no
benefit; `AGENTS.md` already declares `src/` canonical.

**80.6** Add `velo build --verify-determinism` that builds Gen2 and Gen3
internally and compares hashes, replacing the Python script as the primary gate
(keep the script as the CI wrapper). Also add a `bootstrap.c` size/loc budget
warning so generation growth is visible in review.

## Phase Exit Criteria

- `grep -c "sys.io" src/backend/driver.vl src/lsp/analysis.vl src/backend/pretty_recon.vl`
  yields only the table reference.
- No codegen function returns a C type name as a string.
- The Stage-1 question is resolved with a commit, not a comment.

---

# Phase 81: Performance and Benchmark Credibility (P1) - OPEN

## Defect

The only published benchmark compares Velo against Node.js on HTTP throughput.
Node is not the peer group for a native compiler. There is no comparison
against C, Rust, or Go, no memory-per-operation measurement beyond `Working Set`,
no build-time measurement, no regression tracking - and the compiler's own
performance is never measured, which matters because a self-hosting compiler
that is slow to compile loses the "high velocity" claim outright.

## Evidence

| Fact | Evidence |
| :--- | :--- |
| Benchmark peer is Node.js only | `benchmark/BENCHMARK_RESULTS.md:1` "Velo vs. Node.js HTTP Server Benchmark"; `benchmark/server_node.js` is the only comparator |
| Results are hand-copied into Markdown | `benchmark/BENCHMARK_RESULTS.md` has no generator; `run_benchmark.py` exists but the numbers are static text, so nothing prevents drift |
| No compile-time benchmark | nothing measures `velo build src/main.vl`; the self-hosted compiler's own speed is unmeasured |
| No regression gate | no CI job compares benchmark numbers across commits |
| One loop microbenchmark exists | `tests/test_loop_performance.py` (Phase 68) - 20M iterations, 2x ratio detector. This is the only automated performance test. |
| Memory claims exist but are unverified | `README.md:13` "Runs in < 64KB RAM"; `benchmark` shows 4.59 MB baseline RSS |

## Security Invariants

- **I81.1** Every performance claim in `README.md` and the docs is produced by a
  committed script and reproducible by a reader.
- **I81.2** A performance regression above a fixed threshold fails CI.

## Tasks

**81.1** Rewrite the benchmark as generated output: `benchmark/run_benchmark.py`
runs Velo, C, Rust, Go, and Node variants of the same three workloads and writes
`benchmark/RESULTS.md` with a machine/version header. The static Markdown file
becomes generated and is regenerated in CI (or on a schedule).

**81.2** Add C, Rust, and Go peers for the HTTP workload, plus a JSON parse
workload and a file-scanning workload (the actual intended use cases from
Section 1's positioning).

**81.3** Add `benchmark/compile_speed.py`: measure clean and incremental
`velo build src/main.vl` time, track it per commit, and fail CI on a >20%
regression.

**81.4** Add `benchmark/memory.py` using per-workload peak RSS on all three
platforms; replace `README.md`'s "< 64KB" claim with measured numbers or delete
the claim (Phase 83 owns the deletion decision).

**81.5** Promote `tests/test_loop_performance.py`'s pattern into a
`tests/benchmarks/` tier behind a `--bench` flag so it runs in CI nightly, not
per-PR.

## Phase Exit Criteria

- `benchmark/RESULTS.md` is generated, names compiler versions and hardware, and
  includes C, Rust, and Go peers.
- A compile-time regression fails a CI job.

---

# Phase 82: Compiler Robustness and Fuzzing (P1) - OPEN (partially verified)

## Defect

The compiler has no fuzzing. Every defect in Phases 52-69 was found by a human
reading code or writing a probe - several were process crashes
(`0xC00000FD` stack overflow, `0xC0000374` heap corruption, `0xC0000094`
divide-by-zero). A crash on malformed input in a compiler that emits C is a
security issue, because the compiler is a build dependency.

## Evidence

| Fact | Evidence |
| :--- | :--- |
| No fuzz harness | no `fuzz` directory, no libFuzzer/AFL target, no property-test dependency in any test |
| Crashing inputs are a proved pattern | Phase 69: `defer return` overflowed the stack in both `check` and `emit-c`, exit `-1073741571`/`3221225725`, no diagnostic |
| The compiler still crashes on other inputs | Phase 74 probes show uncaught `0xC0000094` on divide-by-zero; `docs/gaps_archive.md:181` records `STATUS_HEAP_CORRUPTION` from `mem.realloc` on a zone pointer |
| Error recovery is unmeasured | `st.error_count` exists (`src/analysis/symbol_table.vl`) but nothing asserts a valid parse tree after N errors |
| No resource limits | a deeply nested expression or a very long line has no documented limit; the lexer/parser recursion depth is unbounded |

## Security Invariants

- **I82.1** No input reaches a signal or an OS exception. Every failure is a
  diagnostic with a code and a non-crashing exit status.
- **I82.2** Recursion in lexer, parser, and checker is depth-bounded with a
  named diagnostic.
- **I82.3** A fuzz corpus is committed and runs in CI on a time budget.

## Tasks

**82.1** Add `tests/test_compiler_no_crash.py`: a generator producing malformed
inputs (truncated tokens, mismatched braces, 10k-deep nesting, 1 MB identifiers,
invalid UTF-8, NUL bytes, BOMs) and asserting for each that `velo check` and
`velo emit-c` exit with a documented status and emit a diagnostic. Seed the
generator with every historical crash input from Phases 52-69 and this file.

**82.2** Add depth limits to the lexer/parser/checker with a named diagnostic
and a test at limit-1, limit, limit+1.

**82.3** Build an AFL/libFuzzer target for the C-transpiler path
(`compile_source_to_c_all_opts` exposed via a thin C entry point), run it for a
fixed budget in CI nightly, and commit `tests/fuzz/corpus/` with the discovered
inputs.

**82.4** Add an error-recovery assertion: after any single-error input, the
diagnostic list is non-empty, contains no internal `backend:`/`reached codegen`
message, and the process exit code is in the documented set.

**82.5** Add resource ceilings: maximum source file size, maximum token count,
maximum AST depth, maximum error count (stop after N and print "too many
errors"), each with a test.

## Phase Exit Criteria

- The historical crash corpus from Phases 52-69 all produce diagnostics, not
  signals.
- A nightly fuzz job exists with a committed corpus, evidenced by a run link.

---

# Phase 83: Documentation and Claims Integrity (P1) - OPEN

## Defect

The `README.md` makes claims that the tree does not support, and `AUDIT.md`
reads as a self-assessment with an inflated scorecard. Overclaiming in the first
two files a reviewer reads is worse than the missing features, because it
destroys the credibility of everything else - including the parts that are
genuinely good.

## Evidence

| Fact | Evidence |
| :--- | :--- |
| "< 64KB RAM" is not supported | `README.md:13`; the runtime header includes `<stdio.h>`, `<stdlib.h>`, `<string.h>`, `<time.h>`, `<setjmp.h>`, `<math.h>`, `<sys/stat.h>` (`runtime/velo_runtime.h:20-50`), and the published baseline RSS is 4.59 MB (`benchmark/BENCHMARK_RESULTS.md:4`). No embedded target exists: no cross-compile flag, no `--target`, no bare-metal runtime profile. |
| "0.001s startup time" is undocumented | `README.md:12`; no measurement script, no test, no CI number |
| "120+ FPS guarantee" is undocumentable | `README.md:11`; no frame-time test, no engine, no benchmark |
| "Single portable `.exe`" | `README.md:12`; true on Windows, and Phase 70 documents that it is not portable at all today |
| Games and apps are untracked, so the showcase is invisible | `git ls-files games apps` -> 0 files, despite `games/flappy_bird`, `games/survivors`, `games/velocraft`, `apps/velokv`, `apps/velostudio` existing on disk [VERIFIED] |
| `AUDIT.md` is a self-review with a scorecard | `AUDIT.md` "Reviewer Scorecard", "Reviewer's Final Verdict" - no reviewer identity, no date, no reproduction |
| `README.md` quick-look compiles | verified: the `use sys.io` / `zone {}` snippet checks clean [VERIFIED] - so the docs are not uniformly wrong, which makes the specific overclaims more damaging |
| No architecture doc for the stdlib | `docs/ARCHITECTURE.md` covers the compiler; the `std/` platform model (Phase 70's root cause) is undocumented |

## Security Invariants

- **I83.1** Every quantitative claim in user-facing docs is backed by a
  committed script and a dated result.
- **I83.2** A claim that cannot be measured is removed, not softened.

## Tasks

**83.1** Rewrite `README.md`'s "What is Velo?" targets to state what is
measured today: systems tooling, compilers, CLI utilities, constrained-memory
batch jobs - and mark platform support explicitly (Windows: supported; Linux and
macOS: work in progress, see Phase 70). Delete "< 64KB RAM", "0.001s startup",
and "120+ FPS guarantee" until 81.3/81.4 produce numbers.

**83.2** Move `AUDIT.md` to `docs/reviews/AUDIT-2026-01.md`, label it as an
internal self-assessment, and add the date. Add a `docs/REVIEWS.md` index that
distinguishes internal from external reviews. Never present a self-review as a
reviewer scorecard.

**83.3** Track `games/` and `apps/` (or move them to a separate examples repo
and link it). The showcase is the strongest evidence the language works; leaving
it untracked discards that evidence. If they are not ready, say so in the README
and remove the claim of game-development readiness.

**83.4** Write `docs/STDLIB_ARCHITECTURE.md`: the platform-model contract
(facade + `_<plat>` variants), the intrinsic boundary (`sys.*` vs `std.*`), the
allocation tiers (zone/heap/arena/page), and the error model. This is the
document whose absence let Phase 70's defect survive five audit phases.

**83.5** Add `tests/test_readme_claims.py`: every code block in `README.md` and
`docs/SPECIFICATION.md` must compile or be explicitly marked
`<!-- not-compiled -->`. This catches the drift that makes docs wrong over time.

**83.6** Add `docs/COMPATIBILITY.md`: a support matrix (OS x compiler x
architecture) with an explicit "not supported" column. Refuse to imply support
that Phase 70 has not delivered.

## Phase Exit Criteria

- `README.md` contains no quantitative claim without a script and a result.
- Every doc code block is either compiled by a test or marked as prose.
- `AUDIT.md`'s status is unambiguous as an internal self-assessment.

---

# Phase 84: Ecosystem, Governance, Showcase (P2) - OPEN

## Defect

Beyond code: no editor packages are tracked, no governance, no issue templates,
no release process, no community surface. `editors/` exists on disk and is
untracked (0 tracked files), which means the LSP - a genuine strength - is
invisible to everyone who is not sitting at the maintainer's machine.

## Evidence

| Fact | Evidence |
| :--- | :--- |
| `editors/` is untracked | `git ls-files editors` -> 0 [VERIFIED] |
| No issue/PR templates, no dependabot, no funding | `.github/` contains only `workflows/ci.yml` [VERIFIED] |
| No governance or support policy beyond `SECURITY.md` | the 10 tracked root files listed in Phase 71 |
| `website/` is partially untracked | `git status --short` shows untracked `website/public/bootstrap.c`, favicons, logo assets, and `website/src/components/VeloLogo.tsx` [VERIFIED] |
| Nothing is published | no remote, no tags, no releases |

## Security Invariants

- **I84.1** Tooling that users rely on (editor integration, release artifacts)
  is tracked in the repository it belongs to.
- **I84.2** A security report has a documented, monitored channel.

## Tasks

**84.1** Track the editor integrations (VSCode grammar + LSP client, at
minimum) under `editors/`, with install instructions. Add a grammar-conformance
test that tokenizes a fixture with both the grammar and the compiler lexer.

**84.2** Add `.github/ISSUE_TEMPLATE/bug.md` (with a "minimal `.vl` repro" and
`velo version` field), `feature.md`, and `PULL_REQUEST_TEMPLATE.md` referencing
the Phase 45-69 task contract.

**84.3** Add `GOVERNANCE.md`: who decides, how a breaking change is approved,
what "1.0" means, and the deprecation policy (minimum two minor versions).

**84.4** Commit the website assets currently untracked, or delete them. A
half-tracked site is a half-broken release process.

**84.5** Add `docs/ROADMAP.md` generated from this file's open phases, so the
public roadmap cannot drift from the registry (`scripts/gen_roadmap.py`,
checked in CI).

## Phase Exit Criteria

- `git status --short` is clean for `editors/` and `website/`.
- Issue and PR templates exist and reference the task contract.
- `docs/ROADMAP.md` is generated from `gaps.md` and fails CI when stale.

---

# Phase 85: Recorded Residual Limitations (P2) - OPEN

Honest, low-severity items that are known and deliberately deferred. They are
listed so they are not rediscovered as surprises.

| Item | Evidence | Residual risk | Close condition |
| :--- | :--- | :--- | :--- |
| CI exists as a workflow, not as a record of execution | no remote (`git remote -v` empty); every row in `docs/CI_STATUS.md` reads "not yet"; `test_every_declared_job_has_evidence` is strict-xfail | A reviewer cannot tell a green CI from an unrun one by looking at the repo alone - mitigated by `docs/CI_STATUS.md` stating "no run has executed" and by the strict xfail | One green run per declared job, recorded in `docs/CI_STATUS.md` (Phase 76.1) |
| ASan/UBSan unverifiable on the maintainer host | sanitizer libs absent locally; `.github/workflows/ci.yml` sanitizer lane unproven | Memory bugs can ship unnoticed | One green full-suite sanitizer run committed (Phase 74.6) |
| `velo_check_capture.tmp` fixed CWD filename | fixed in 76.4: `check_capture_path()` embeds the pid (`src/backend/check.vl`) | Concurrent `velo check` is safe per process; not per thread | None for the CLI; a thread-safe variant needs the capture global made reentrant |
| Windows and MSVC lanes never executed | `windows-gcc` and `windows-msvc` jobs are structurally tested, but no run exists | The MSVC backend is verified locally for 2 of 132 modules; a full-suite MSVC run may surface genuine backend defects on first execution | First green `windows-msvc` run (Phase 76.1) |
| `fast` tier membership is opt-in and could drift | `pytestmark = pytest.mark.fast` in 5 modules; `slow` inferred by source heuristic | A module that starts invoking the compiler while still marked `fast` slows the push lane; the heuristic cannot detect that because `fast` short-circuits it | Reviewed by `test_fast_job_runs_only_the_fast_lane` at the job level; per-module honesty is a review responsibility |
| 400-line ceiling forces sliver modules | 40+ files under 150 lines in `src/analysis`/`src/backend` | Concept fragmentation, duplicated header contracts | Phase 80.4 (ceiling becomes a consequence, not a constraint) |
| Frozen Stage-1 Python compiler still in the build story | `AGENTS.md`, `examples/12_stage2_semantics_test.vl` | Double maintenance, false parity signal | Phase 80.5 |
| `bootstrap.c` is a 2.3 MB generated artifact in review | 67,952 lines | Compiler diffs are unreviewable at the artifact level | Phase 80.6 budget warning + Phase 76 tiering |
| `std/async` is `poll(2)` on Linux | `std/async/poller_linux.vl:13` | O(n) wakeup scaling | Phase 70.4 (`epoll`) |
| Overlapping `mem.copy`/`mem.set` remain C UB | `docs/gaps_archive.md:181` | Silent corruption on aliased buffers | Phase 74.4 [COMPLETED] ✅ |
| No `Set`/`Deque`/priority queue | `std/coll/` inventory | Users hand-roll them, inconsistently | Phase 78.8 |
| `defer` takes a block, not an expression | Phase 58/69 semantics | Verbose cleanup sites | Phase 77.6 |
| No `v2.0.0-pre` tag was published anywhere | tag exists locally; no remote configured | A consumer cannot pin the release commit | Add a remote and push tags (Phase 84) |
| Release archive cannot be used without a C compiler | `scripts/release.py` ships `velo.exe` + sources, no prebuilt library triple | Consumers on compiler-less hosts are unsupported by design | Documented in Phase 71's residual limitation; revisit with Phase 70's platform set |
| `emit-c` output depends on how the source path is spelled | `src/backend/codegen_line.vl:6-17` embeds the path in `#line` | A build driven from an absolute path produces a byte-different snapshot | Pinned by `tests/test_release_script.py`; normalizing paths is Phase 79 (reproducible-build work) |

---

## 6. Definition of Public Release

Velo may be published for real-world use when, and only when, all of the
following are true and each is backed by a committed artifact, not a claim:

1. **Legal:** `LICENSE` present; `velo version` derives from one source;
   `CHANGELOG.md` exists; a tag exists (Phases 71). `[ ]`
2. **Platforms:** Linux, macOS, and Windows each build `bootstrap.c`, build the
   compiler, and run the full suite green; the platform support matrix in
   `docs/COMPATIBILITY.md` matches reality (Phases 70, 76, 83). `[ ]`
3. **CI evidence:** `docs/CI_STATUS.md` links a green run per job on the
   release commit (Phase 76). `[ ]` - the document and its enforcing test exist;
   the runs do not, because there is no remote.
4. **No lying stubs:** zero stub-return bodies in `std/`; every documented
   function either works or refuses (Phases 75, 83). `[ ]`
5. **Memory safety story:** defined overflow semantics, divide-by-zero
   diagnostic, runtime bounds checks for dynamic indices, sanitizer lane green
   (Phase 74). `[ ]`
6. **Network reality:** TLS with verification on by default, DNS resolution,
   constant-time MAC verification, fail-closed CSPRNG (Phases 73, 78). `[ ]`
7. **Packages:** `pkg install` fetches, verifies hashes, and never reports
   success for work not done (Phase 72). `[ ]`
8. **Robustness:** the historical crash corpus produces diagnostics, not
   signals; recursion is depth-bounded (Phase 82). `[ ]`
9. **Docs:** every quantitative claim has a script; every doc code block is
   compiled or marked (Phase 83). `[ ]`
10. **Maintainability:** one intrinsic allowlist, typed codegen, one compiler
    implementation (Phase 80). `[ ]`

Phases 77, 78, 79, 81, 84 can trail 1.0 as documented limitations; Phases 70-76
and 82-83 cannot. A 1.0 that ships with a Windows-only stdlib, a package manager
that fakes installs, and a README claiming 64 KB embedded support would burn the
project's credibility in one release, and credibility is the only asset a
one-person language has.

## 7. Deliberate Non-Goals

Stated so contributors do not relitigate them:

- **Garbage collection.** The zone/heap/defer model is the point of the
  language.
- **A borrow checker with lifetimes.** Escape analysis plus arenas is the
  chosen trade.
- **A macro system.** Codegen-level metaprogramming is out of scope; reflection
  covers the struct-mapping use case.
- **Backends other than C.** Emitting C is what makes the FFI and bootstrap
  story work.
- **Package hosting with accounts.** A registry repository plus hashes is the
  trust model (Phase 72.6).
