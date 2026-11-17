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
| **70** | POSIX / macOS Foundation Portability | P0 | yes | 8 | 8 |
| **71** | Release Engineering and Legal Provenance | P0 | **COMPLETED** | 6 | 5 |
| **72** | Package Ecosystem That Actually Fetches | P0 | yes | 7 | 7 |
| **73** | Transport Security and Cryptographic Completeness | P0 | yes | 8 | 8 |
| **74** | Undefined-Behavior Containment | P0 | yes | 7 | 7 |
| **75** | Silent POSIX Process/IO Stubs | P0 | yes | 5 | 5 |
| **76** | CI Reality and Platform Test Harness | P0 | yes | 6 | 6 |
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

# Phase 70: POSIX / macOS Foundation Portability (P0) - OPEN

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

**70.2** Move the six Win32 `extern` blocks out of the platform-neutral files:
`std/fs/stat.vl`, `std/fs/ops.vl`, `std/fs/dir.vl`, `std/net/socket.vl`,
`std/net/addr.vl`, `std/crypto/rand.vl`. Create `std/fs/stat_windows.vl` /
`stat_linux.vl` / `stat_macos.vl` (same for `ops`, `dir`, `socket`) and keep
`std/fs/stat.vl` as the facade. Alternatively route the whole family onto the
already-portable CRT helpers in `runtime/velo_runtime.h` (`velo_fs_is_dir` at
1377, `velo_fs_read_dir` at 2236) and delete the Win32 duplicates - prefer
this: it removes code rather than tripling it.

**70.3** Add `std/os/proc_macos.vl`, `std/os/env_macos.vl`, `std/io/handle_macos.vl`,
`std/time/clock_macos.vl`, `std/time/sleep_macos.vl`, `std/mem/page_macos.vl`,
`std/async/poller_macos.vl` (kqueue). Each may start as a thin POSIX
implementation; macOS and Linux differ only where noted.

**70.4** Replace `poll(2)` with `epoll(7)` in `std/async/poller_linux.vl`. The
current file (line 13 `extern act poll`) scales O(n) per wakeup and has no
edge-trigger mode; `poll` also cannot be used for file/descriptor watch on
all targets. Keep `poll` as the fallback for unknown POSIX targets.

**70.5** Remove every hardcoded `use "*_windows.vl"` facade line listed above;
each becomes a resolver-mediated import. Then delete `std/os/pipe_win32.vl`'s
`use "proc_windows.vl"` in favour of the same mechanism (line 8).

**70.6** Guard `bootstrap.c` generation itself: `emit-c src/main.vl` must emit a
`#include "velo_runtime.h"`-style preamble that is platform-neutral, i.e. the
Win32 externs must live in a platform section. Simplest correct fix: after
70.2 lands, `bootstrap.c` contains no Win32 symbol at all (they move into
`std/**_windows.vl`, which is only emitted when the target is Windows).

**70.7** Add `tests/test_posix_portability.py`: for each of `std.fs`, `std.net`,
`std.os`, `std.crypto`, `std.time`, `std.async`, emit C for a probe program and
assert the emitted text contains no symbol matching
`/(GetFileAttributesExA|GetFileAttributesA|CreateDirectoryA|RemoveDirectoryA|DeleteFileA|MoveFileExA|CopyFileA|FindFirstFileA|FindNextFileA|FindClose|CreateProcessA|GetEnvironmentVariableA|SetEnvironmentVariableA|ExitProcess|GetCurrentProcessId|VirtualAlloc|VirtualFree|SystemFunction036|WSAStartup|WSACleanup|closesocket|ioctlsocket)/`
when the build host is not Windows. Skip on Windows; the assertion is inverted
there.

**70.8** Add `tests/test_postgres_bootstrap_platform.py` (or extend
`test_bootstrap_snapshot.py`): compile `bootstrap.c` with `cc -c` and assert no
undefined symbol from the Win32 set, on every non-Windows host.

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

# Phase 72: Package Ecosystem That Actually Fetches (P0) - OPEN

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

**72.1** Implement `manifest_resolve_dep(dep) -> DepLocation` for `local` and
`git` kinds. `git` runs `git clone --depth 1 --branch <tag> <url>
.velo_cache/deps/<name>` and then `git rev-parse HEAD`. A missing `git`
executable is a hard error with an actionable message.

**72.2** Implement `registry` kind against a minimal HTTP index: `<registry>/ 
<name>/index.json` listing `version -> {url, sha256}`. Requires Phase 73's TLS
or an explicit `--insecure` flag that prints a warning. Document the index
format in `docs/PACKAGING.md`.

**72.3** Fix the lie: `pkg install` must call 72.1/72.2 for every dependency,
verify hashes (I72.2), and only then print success. Add
`tests/test_pkg_install_fetches.py` with a local `file://`-style registry
fixture and a `git` fixture; the test asserts the dependency directory exists
and its files match the lock hash.

**72.4** Add semver: parse `MAJOR.MINOR.PATCH`, support `=`, `^`, `~`, and
`>=` in manifests, reject ambiguous ranges with a diagnostic.

**72.5** Add `velo pkg tree` and `velo pkg verify` (read-only: recompute hashes
and report drift). `verify` is what CI calls.

**72.6** Add `velo pkg publish` that tars the manifest's declared `src/` and
`std/` subsets, computes the hash, and prints the index entry to paste. No
upload servers, no accounts - publishing is a pull request to a registry
repository. That keeps the trust model small enough to be honest.

**72.7** Add a `tests/test_pkg_semver.py` matrix and a `deps-lock` CI job that
builds a two-level dependency graph offline from fixtures.

## Phase Exit Criteria

- `velo pkg install` on a git dependency produces a working tree and a lock
  entry whose hash matches, proven by test.
- `velo pkg install` with a corrupted lock or a missing dependency exits
  non-zero and names the problem.
- A published index format exists in `docs/PACKAGING.md` and is exercised by
  at least one test fixture.

---

# Phase 73: Transport Security and Cryptographic Completeness (P0) - OPEN

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

**73.1** Move `md5` out of `std/crypto.vl` into `std/crypto/legacy.vl` with a
`use std.crypto.legacy` requirement and a doc comment saying it is for
interoperability only. Add `tests/test_crypto_umbrella.py` asserting MD5 is not
reachable from the umbrella.

**73.2** Change `crypto_random_bytes` to fail closed: return `bool or string`
and have `uuid_v4`/`uuid_v7` propagate (or abort with a named fatal). Delete the
SplitMix64 fallback fill entirely, or keep it behind an explicit
`crypto_unsafe_fallback` name. Add `tests/test_crypto_rand_failclosed.py` that
injects a failing entropy function.

**73.3** Add `crypto_secure_eq(a, b, len) -> bool` (constant time, no early
exit, no length-dependent branch) plus `hmac_sha256_verify(key, data, tag)`.
Add `tests/test_crypto_constant_time.py` with a statistical timing assertion
(loose bound, 1e6 iterations, assert ratio < 1.5x between equal-prefix and
differing-first-byte inputs) - document that this is a smoke test, not a proof.

**73.4** Add `crypto_zero(ptr, len)` that the compiler cannot optimize away
(`volatile` store loop in the runtime) and use it in `hmac.vl`'s temporaries.

**73.5** Implement SHA-512 and HMAC-SHA512 (`std/crypto/sha512.vl`), matching
the existing `sha256` structure. Test against RFC 4231 vectors.

**73.6** Implement ChaCha20-Poly1305 AEAD (`std/crypto/chacha20poly1305.vl`)
against RFC 8439 vectors, plus `crypto_random_bytes`-seeded nonce generation and
an authenticated-encryption API that refuses nonce reuse via a `?` handle.

**73.7** Implement TLS 1.3 client (`std/tls/`): record layer, key schedule
(HKDF-SHA256 from 73.5/73.6), and a certificate-verification interface backed by
the OS trust store where available. Minimum viable: X25519 key exchange
(`std/crypto/x25519.vl`), Ed25519 verification for certificates, and a clear
`tls_verify_peer` default of `true`. Test against a fixed local server with a
pinned certificate; include one negative test per verification failure mode.

**73.8** Wire `https://` into `std/http/client.vl` and fail with a named error
when TLS is unavailable rather than silently downgrading.

## Phase Exit Criteria

- `http_get("https://...")` against a local test server succeeds with
  certificate verification enabled, and fails with a named error against a
  self-signed certificate.
- No cryptographic path returns success after a degraded fallback.
- MD5 is not reachable from `std.crypto`.
- `hmac_sha256_verify` exists and is constant-time by construction, with a
  timing smoke test committed.

---

# Phase 74: Undefined-Behavior Containment (P0) - OPEN

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

**74.1** Decide and specify the overflow policy. Recommended: wrap by default
(matching the existing `hash`/`bits` code and the "systems language" promise),
enforced by adding `-fwrapv` to GCC/Clang and `/d2`-style wrap semantics for
MSVC, plus a documented `checked_add`/`checked_mul` family in `std.math.int`
(some `*_sat` helpers already exist at `std/math/int.vl:18-25`). Write the rule
into `docs/SPECIFICATION.md` section 2.1 and add the `-fwrapv` (and MSVC
equivalent) to `src/backend/driver_cc.vl:247-263`. Test: add 32-bit and 64-bit
overflow boundary rows to a new `tests/test_integer_overflow.py`, asserting
wraparound in both Debug and Release - the current behaviour is
`INT_MAX + 1` producing an UB-dependent value.

**74.2** Add a runtime divide-by-zero guard for the runtime path: emit
`velo_div_guard(b)` (a fatal with a Velo message and the `#line` of the
division) before `/` and `%` when the divisor is not a proven non-zero constant.
Test: `tests/test_div_zero.py` asserts a clean stderr message and a stable exit
code, replacing today's silent `0xC0000094`.

**74.3** Add runtime bounds checks for fixed-size array indexing that the
compiler cannot prove. Either reuse the shelf/bitset fatal tier
(`runtime/velo_runtime.h:1824` `velo_shelf_oob`, `2918` `velo_bitset_oob`) or add
`velo_arr_oob`. Emit the check only when `--unsafe-shelf-index`-style opt-out is
not requested. Test: `tests/test_fixed_array_runtime_bounds.py` with a dynamic
index probe (the exact program above) asserting a fatal, and a
`--unsafe-array-index` counterpart asserting the unchecked path for parity with
the shelf policy.

**74.4** Add `mem.overlaps(a, b, len_a, len_b) -> bool` and make `mem.copy` /
`mem.set` assert non-overlap in Debug builds (fatal with a named message),
documenting `mem.move` as the overlapping-safe primitive. Test: overlapping
`mem.copy` in Debug -> fatal; in Release -> documented memcpy behaviour.

**74.5** Add `mem.realloc`/`mem.free` provenance checks. Cheapest honest
version: a magic header + owner tag around heap allocations
(`std/mem/heap.vl:201` already has the freelist machinery), validating on free
and realloc and fataling on mismatch. Document the cost (8-16 bytes/allocation)
and the opt-out flag.

**74.6** Make the sanitizer lane real. Add `scripts/bootstrap_sanitized.sh`
that builds with `-fsanitize=address,undefined -fno-sanitize-recover=all` and
runs the full `.vl` battery; add a `sanitizer-local` section to
`docs/build_sheets/build_modes.md` listing the exact packages. Then run it once
on Linux CI and commit the green run link to this file (Phase 76 depends on
this).

**74.7** Add `tests/test_ub_probes.py` containing every probe in this phase's
evidence table as an executable row, so the phase cannot silently regress.

## Phase Exit Criteria

- `INT_MAX + 1` has a documented, tested result on all three compilers.
- Divide by zero produces a Velo message and a stable exit code.
- A dynamic out-of-bounds write into `[N]T` traps with a Velo message.
- The sanitizer lane has produced at least one green full-suite run, evidenced
  by a committed link and a date.

---

# Phase 75: Silent POSIX Process/IO Stubs (P0) - OPEN

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

**75.1** Replace `proc_linux.vl`'s `os_spawn_ex` with a real `posix_spawn` or
`fork`+`execvp` implementation: pipe redirection for `h_in`/`h_out`/`h_err`,
`proc_spawn_file_actions`/`dup2`, and a `ProcessHandle` carrying the pid.
Provide a `_macos` variant only if the flags differ.

**75.2** Replace `os_pipe_drain_streams` with a real reader: `read(2)` loop
until EOF on both fds, arena-accumulated strings, and the true `exit_code` from
`waitpid` (decoding `WIFEXITED`/`WEXITSTATUS`/`WIFSIGNALED`). Test with a child
that writes to both streams and exits 7.

**75.3** Implement signal decoding: `os_process_signal(proc)` returning the
terminating signal on POSIX and `0` on Windows. The current API cannot express
"killed by SIGSEGV", which matters for build tools.

**75.4** Add `tests/test_os_process_posix.py` covering: spawn+wait exit code,
stdout/stderr capture, signal termination, non-existent binary (named error,
not crash), and pipe close ordering. Gate on `sys.platform != "win32"`.

**75.5** Audit every remaining `stub` comment in `std/` and either implement,
delete, or convert into a compile-time unsupported-platform error.
`grep -rin "stub" std/` is the work list; the current count must go to zero
outside of explicitly documented `_unsupported` modules.

## Phase Exit Criteria

- `velo run` of a program doing `os_spawn_sync("echo hi")` prints `hi` and
  reports exit code 0 on Linux and macOS.
- Zero stub returns remain in `std/`.
- A child killed by a signal is reported as such through the public API.

---

# Phase 76: CI Reality and Platform Test Harness (P0) - OPEN

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

**76.2** Replace the `test_ci_matrix.py` string assertions with a check of the
workflow's actual required steps (parse the YAML, assert job matrix shape), and
add a separate `tests/test_ci_evidence.py` that reads a committed
`docs/CI_STATUS.md` containing the latest green run links per job. The test
fails when a job has no link or the link's commit SHA is not an ancestor of
`HEAD`.

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

**76.4** Replace `velo_check_capture.tmp` with a per-process temp path
(`velo_check_capture_<pid>.tmp`, or `mkstemp`-equivalent inside
`.velo_cache/`), making `velo check` safe to run concurrently. Test: run 8
`velo check` processes in parallel in the same directory and assert all
succeed and no stray tmp file remains (`tests/test_check_concurrency.py`).

**76.5** Add a `windows-msvc` full-suite job. Today `windows-msvc`
(`ci.yml:134-172`) runs only `test_cc_backend.py` and
`test_bootstrap_snapshot.py`, so the MSVC path is verified for two files out of
129.

**76.6** Split the suite into tiers and make CI honest about duration: a `fast`
marker (no C compiler invocation) running in under 2 minutes on every push, and
the full suite on PRs. The current suite is ~15.5 minutes; contributors will
not wait, and a 15-minute red X trains people to ignore CI.

## Phase Exit Criteria

- Actions runs on Linux (gcc + clang), macOS (clang), Windows (gcc + MSVC), and
  the sanitizer lane, all green on the same commit, with links committed to
  `docs/CI_STATUS.md`.
- `grep -rl "msys64" tests/` and `grep -rl "velo\.exe" tests/` are empty except
  in `conftest.py`.
- `velo check` is safe to run concurrently, proven by test.

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

**77.1** Document the four absences in a new `docs/SPECIFICATION.md` section
"Deliberate Limitations" with workarounds. This is a one-commit, high-value
task: it converts "unfinished" into "chosen", which is a legitimate position.

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
| 422 captured-subprocess test sites lack explicit encoding | recorded in the pre-Phase-69 audit baseline | Windows CI can fail on code-page-dependent output | Swept by Phase 76.3's conftest helper; assert `grep -c "text=True" without encoding` == 0 |
| ASan/UBSan unverifiable on the maintainer host | sanitizer libs absent locally; `.github/workflows/ci.yml:221` lane unproven | Memory bugs can ship unnoticed | One green full-suite sanitizer run committed (Phase 74.6) |
| `velo_check_capture.tmp` fixed CWD filename | fixed in 76.4: `check_capture_path()` embeds the pid (`src/backend/check.vl`) | Concurrent `velo check` is safe per process; not per thread | None for the CLI; a thread-safe variant needs the capture global made reentrant |
| 400-line ceiling forces sliver modules | 40+ files under 150 lines in `src/analysis`/`src/backend` | Concept fragmentation, duplicated header contracts | Phase 80.4 (ceiling becomes a consequence, not a constraint) |
| Frozen Stage-1 Python compiler still in the build story | `AGENTS.md`, `examples/12_stage2_semantics_test.vl` | Double maintenance, false parity signal | Phase 80.5 |
| `bootstrap.c` is a 2.3 MB generated artifact in review | 67,952 lines | Compiler diffs are unreviewable at the artifact level | Phase 80.6 budget warning + Phase 76 tiering |
| `std/async` is `poll(2)` on Linux | `std/async/poller_linux.vl:13` | O(n) wakeup scaling | Phase 70.4 (`epoll`) |
| Overlapping `mem.copy`/`mem.set` remain C UB | `docs/gaps_archive.md:181` | Silent corruption on aliased buffers | Phase 74.4 |
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
   release commit (Phase 76). `[ ]`
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
