# 🌐 Velo Platform & Toolchain Compatibility Matrix

> **Living Document**: Enforces Claims Integrity (**Invariant I83.1**) and Explicit Support Status (**Invariant I83.2** / **Task 83.6**).
> Refuses to imply or claim platform support that has not been delivered and empirically verified in CI.

---

## 1. Compatibility Policy & Tier Definitions

Velo evaluates platform and toolchain compatibility across three explicit support tiers:

* **Tier 1 (Supported & CI-Gated)**:
  * Full self-hosted compiler toolchain (`velo.exe`), Language Server Protocol (LSP), formatter (`velo fmt`), in-memory test runner, and showcase applications are fully operational.
  * Emitted C code compiles and links with native OS toolchains.
  * Covered by continuous automated integration tests on every commit.
* **Tier 2 (Work in Progress / Experimental)**:
  * Core language compiler transpiles valid, standard C99/C11 code.
  * Standalone bootstrap script compiles `bootstrap.c` into a working compiler binary.
  * Standard library POSIX facades and platform drivers are actively converging (see [`docs/STDLIB_ARCHITECTURE.md`](STDLIB_ARCHITECTURE.md) and Phase 70 in [`gaps.md`](../gaps.md)).
* **Tier 3 (Not Supported / Out of Scope)**:
  * Explicitly unsupported platforms, architectures, or environments.
  * Compilation is either not implemented, rejected by compiler drivers, or lacks operating system runtime dependencies.

---

## 2. Operating System & Architecture Matrix

| Operating System | Architecture | Supported C Toolchain | Status | Subsystems Verified | Explicitly Not Supported |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **Windows** (10 / 11 / Server) | `x86_64` (AMD64) | GCC (MSYS2 UCRT64), Clang | **Tier 1** | Compiler, CLI, LSP, `std.*`, Raylib C-FFI, Showcase | 32-bit `x86` (IA-32), ARM64 Windows, MSVC `cl.exe` |
| **Linux** (glibc / musl) | `x86_64` (AMD64) | GCC, Clang | **Tier 2** | Compiler C99 codegen, `sys.*`, bootstrap script | 32-bit `i686`, pre-POSIX kernels (< 3.2) |
| **Linux** (glibc / musl) | `aarch64` (ARM64) | GCC, Clang | **Tier 2** | Compiler C99 codegen, `sys.*`, bootstrap script | 32-bit `armv7` (ARM32/hardfloat) |
| **macOS** (12.0+ Monterey) | Apple Silicon (`arm64`) | Apple Clang (Xcode CLI) | **Tier 2** | Compiler C99 codegen, `sys.*`, bootstrap script | macOS < 11.0, 32-bit Darwin |
| **macOS** (11.0+ Big Sur) | `x86_64` (Intel) | Apple Clang (Xcode CLI) | **Tier 2** | Compiler C99 codegen, `sys.*`, bootstrap script | macOS < 11.0, 32-bit Darwin |
| **FreeBSD / OpenBSD / NetBSD**| Any | Any | **Tier 3** | None | Entire BSD operating system family |
| **Android / iOS** | Any | Android NDK / Xcode iOS | **Tier 3** | None | Mobile operating systems out of scope |
| **WebAssembly** | `wasm32`, `wasm64` | Emscripten | **Tier 3** | None | Wasm/WASI compilation targets |
| **Embedded / Bare-Metal** | Any | GCC bare-metal (`arm-none-eabi`)| **Tier 3** | None | Microcontrollers, no-OS environments (< 4 MB RAM) |

---

## 3. Standard Library Subsystem Support

The following matrix documents subsystem availability across operating systems:

| Subsystem | Module Namespace | Windows (`x86_64`) | Linux (`x86_64`/`arm64`) | macOS (`arm64`/`x86_64`) | Notes |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Compiler Intrinsics** | `sys.io`, `sys.mem`, `sys.time` | 🟢 **Tier 1** | 🟢 **Tier 1** | 🟢 **Tier 1** | Standard C99 / hardware ticks lowered directly |
| **Filesystem** | `std.fs` | 🟢 **Tier 1** | 🟡 Tier 2 | 🟡 Tier 2 | Win32 API vs POSIX `stat`/`open`/`opendir` |
| **Networking** | `std.net` | 🟢 **Tier 1** | 🟡 Tier 2 | 🟡 Tier 2 | Winsock2 (`ws2_32`) vs POSIX sockets |
| **Operating System** | `std.os` | 🟢 **Tier 1** | 🟡 Tier 2 | 🟡 Tier 2 | `CreateProcessA` vs `fork`/`exec` |
| **Cryptography (CSPRNG)** | `std.crypto` | 🟢 **Tier 1** | 🟡 Tier 2 | 🟡 Tier 2 | `RtlGenRandom` vs `getrandom` / `getentropy` |
| **Asynchronous I/O** | `std.async` | 🟢 **Tier 1** | 🟡 Tier 2 | 🟡 Tier 2 | IOCP wrapper vs `epoll` / `kqueue` |
| **Memory Allocation** | `std.mem` | 🟢 **Tier 1** | 🟢 **Tier 1** | 🟢 **Tier 1** | Zone arena, heap allocator, virtual pages |

---

## 4. C Compiler Toolchain Compatibility

Velo compiles source code to clean C99/C11 code, which is then lowered to a native binary by a backend C compiler:

| C Compiler Toolchain | Supported Versions | Platform | Status | Notes |
| :--- | :--- | :--- | :---: | :--- |
| **GCC (GNU Compiler Collection)** | $\ge 11.0$ (Tested: 16.1.0) | Windows (MSYS2 UCRT64), Linux | **Supported** | Primary supported backend compiler |
| **Clang / LLVM** | $\ge 14.0$ | Windows, Linux, macOS | **Supported** | Full AddressSanitizer (ASan) & UBSan support |
| **Apple Clang** | Xcode 13.0+ | macOS | **Supported** | Native macOS CLI compilation |
| **Microsoft Visual C++ (`cl.exe`)** | Any | Windows | **Not Supported** | Incompatible CLI flags and compound literal syntax |
| **Tiny C Compiler (`tcc`)** | Any | Any | **Not Supported** | Incomplete C99 atomic and literal support |

---

## 5. Hardware & System Constraints

* **Pointer Width**: 64-bit strictly required (`sizeof(usize) == 8`). 32-bit architectures are Tier 3 (unsupported).
* **Endianness**: Little-endian architectures (`x86_64`, `aarch64` little-endian). Big-endian architectures are untested and unsupported.
* **Minimum Host Memory (Compilation)**: 512 MB physical RAM. Self-hosted compiler peak RSS during full multi-file checking is ~182 MB.
* **Minimum Runtime Footprint**: ~4.0 MB baseline resident set size (RSS) for native standalone CLI binaries. Embedded systems targeting $< 4$ MB RAM are out of scope.

---

## 6. How to Report Portability Gaps

If you identify an undocumented platform failure, broken facade resolution, or compiler link error:
1. Review the living defect tracker in [`gaps.md`](../gaps.md).
2. Ensure your toolchain meets the minimum version requirements documented above.
3. Open an issue on GitHub with your exact operating system version, CPU architecture, C compiler version (`gcc --version` or `clang --version`), and a minimal reproducible `.vl` snippet.
