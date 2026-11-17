# Security Policy

<!-- SPDX-License-Identifier: MIT OR Apache-2.0 -->

The Velo team is dedicated to providing a hardware-grade, high-performance systems programming environment that is robust, reliable, and secure. We welcome responsible security research and appreciate early notification of potential vulnerabilities.

---

## Supported Versions

Only the current major self-hosted release branch receives active security updates and patch releases:

| Version | Supported | Notes |
|:---|:---:|:---|
| **Velo v2.0 (Self-Hosted)** | :white_check_mark: | Canonical self-hosted compiler chain (`src/**/*.vl`, `bootstrap.c`) |
| **Velo v1.x (Python Reference)** | :x: | Frozen Stage 1 historical reference compiler; not for production use |
| **Velo < 1.0 (Pre-Alpha)** | :x: | End of Life (EOL) |

---

## Reporting a Vulnerability

If you discover a security vulnerability in the Velo compiler, runtime, standard library, or package management infrastructure:

> [!IMPORTANT]
> **Do not report security vulnerabilities via public GitHub issues, pull requests, or public discussions.**

Please submit your vulnerability report confidentially through one of the following channels:
1. **GitHub Private Vulnerability Reporting:** Navigate to the repository's **Security** tab and click **Report a vulnerability**.
2. **Security Email:** Send an encrypted or plain-text email to `security@velolang.org`.

### What to Include in Your Report
To accelerate triage and remediation, please provide:
- **Component Affected:** Compiler front-end/back-end, runtime shim (`runtime/velo_runtime.h`), standard library module (`std.*`), or package manager (`velo pkg`).
- **Platform & Environment:** Operating system (Windows / Linux / macOS), CPU architecture (x86_64 / aarch64), and C compiler backend (`gcc`, `clang`, or MSVC `cl.exe`).
- **Minimal Reproduction:** A self-contained `.vl` source file or minimal reproduction repository demonstrating the defect.
- **Impact Assessment:** Explanation of the exploitability and security consequences (e.g. memory corruption, arbitrary code execution, supply chain tampering, or sandbox escape).
- **Proof-of-Concept (PoC):** Reproduction commands or exploit script if applicable.

---

## Response & Triage SLAs

The Velo core security team adheres to the following response timeline:

| Milestone | Target SLA |
|:---|:---|
| **Initial Acknowledgement** | Within **48 hours** of receipt |
| **Triage & Severity Classification** | Within **5 business days** with preliminary assessment |
| **Critical Severity Patch Target** | Within **14 calendar days** (RCE, compiler execution injection, supply chain tampering) |
| **High Severity Patch Target** | Within **30 calendar days** (memory corruption, unsafe boundary escape under `--strict-safety`) |
| **Medium / Low Patch Target** | Next scheduled maintenance release |

---

## Coordinated Disclosure Policy

- **Embargo Window:** Velo follows a standard **90-day coordinated disclosure policy**. We ask security researchers not to disclose details publicly until a patched release is published or the 90-day window expires.
- **CVE Assignment:** If appropriate, the Velo team will request and assign a CVE identifier for the reported vulnerability.
- **Credit & Recognition:** Security researchers who report valid vulnerabilities following this policy will be credited in release notes and security advisories (unless anonymity is requested).

---

## Security Architecture & Invariants

Velo enforces several key architectural guarantees designed to minimize attack surface:

1. **Compile-Time Zone Escape Analysis:** Lexical zone allocators track allocation depth at compile time, statically rejecting attempts to return or escape pointers to frame-local or zone-allocated data.
2. **Explicit Safety Boundaries (`--strict-safety`):** Under `--strict-safety`, raw pointer dereferencing (`ptr.@`, `ptr.field`, `ptr[i]`), pointer arithmetic, and foreign `extern act` calls are rejected outside explicit `unsafe { ... }` blocks.
3. **Compiler Driver Command Hardening:** The compiler driver escapes all file paths and compiler flags passed to ambient C compilers (`gcc`, `clang`, MSVC `cl.exe`), preventing command injection or argument smuggling.
4. **Cryptographic Package Supply Chain Integrity (`velo.lock`):** The package manager calculates and verifies cryptographic SHA-256 digests (`sha256:...`) using `std.crypto` for all resolved dependencies, detecting and rejecting tampered or modified archives during `velo pkg install`, `velo pkg check`, and `velo pkg build`.

---

## Out-of-Memory Policy

The runtime (`runtime/velo_runtime.h`) is **fail-stop on allocation failure**. There
is no recoverable OOM path and no silent truncation: every allocation that cannot be
satisfied terminates the process with a diagnostic on stderr.

| Allocation site | Behaviour on failure |
|:---|:---|
| `velo_zone_create_default`, `velo_zone_enter`, `velo_mem_create_arena` (arena struct or buffer) | `Zone Arena allocation failed (<n> bytes)` / `Arena allocation failed (<n> bytes)` → `exit(1)` |
| `velo_zone_enter`, `velo_mem_create_arena` with a zero capacity | `Zone Arena capacity must be > 0` / `Arena capacity must be > 0` → `exit(1)` |
| `velo_zone_new_chunk` (spilled chunk struct or buffer) | `Zone Arena Chunk Spilling allocation failed (<n> bytes)` → `exit(1)` |
| `velo_zone_push` (watermark heap growth; includes wrap and byte-size overflow) | `Zone Arena Watermark Stack OOM` → `exit(1)` |
| `velo_zone_enter(NULL)` / entering a null arena handle | `Cannot enter null arena` → `exit(1)` |
| `velo_heap_alloc`, `velo_heap_realloc` | `Out of Heap Memory` → `exit(1)`; a failed `realloc` leaves the old block intact until exit |
| `velo_thread_spawn`, `velo_mutex_create` | `thread spawn out of memory` / `mutex creation failed` → `exit(1)` |
| Fixed-budget arena overflow (`can_grow == 0`) | `Zone Arena Out of Memory (...)` → `exit(1)` |
| `mem.alloc_with` on a fixed-budget arena | `Allocator Out of Memory (...)` → `exit(1)` |
| Size computation overflow (`size * count`, `+ header`) | `Allocation size overflow (...)` → `exit(1)` |

Why fail-stop rather than returning `null`:

1. **A `null` return from the intrinsics is not observable.** `mem.alloc` and
   `mem.heap_alloc` are declared to return `@T`/`@u8`, not `?@T`; there is no
   language-level way to check for failure without adding an optional type to
   every allocation. A `null` pointer would therefore be dereferenced immediately,
   converting a diagnosable condition into undefined behaviour.
2. **Partial failure is not a valid arena state.** A bump allocator cannot give back
   an allocation it failed to satisfy, and a half-grown watermark stack or chunk
   list has no consistent interpretation. Terminating keeps every observable arena
   state either untouched or fully valid.
3. **Defensive paths never guess.** An out-of-range watermark (`velo_zone_pop`
   with `0` or an index above the stack depth) is treated as caller corruption:
   the arena is reset to empty and its watermark stack cleared. The runtime does
   not rewind to a "probably right" offset, because doing so would hide a
   bookkeeping bug behind plausible-looking behaviour.

Capacity arithmetic is checked before subtraction: every `cap - offset` test in the
arena and chunk paths verifies `offset <= cap` first, so a corrupted watermark can
never make the capacity check underflow and hand out a pointer past the buffer. Those
paths are covered by `tests/test_runtime_zone.py` with deterministic allocation
fail-injection, and that harness is executed under ASan/UBSan in the CI `sanitizer`
job.

A program that must tolerate memory pressure should pre-size its arena
(`mem.create_arena(capacity)` / `zone` with an explicit budget) and check
`mem.used()` / `mem.heap_used()` against its own budget before allocating, rather
than relying on allocation failure being recoverable — it is not.

