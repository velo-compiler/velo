# build_modes.md — 6.2 Optimization Flags & Build Modes: complete build sheet

> Companion to `gaps.md` §6.2. Everything the chapter needs, with the target
> contract for each slice. Every slice lands as one golden-rule unit:
> pin in `gaps.md` §6.2, both compiler stages verified, parity suite,
> bootstrap chain rebuild + Gen2 ≡ Gen3 emit-c SHA-256 fixed point,
> `scripts/count_lines.py` clean (<= 399 lines), and one conventional commit.

## Goal

Provide standard, first-class build modes and optimization flag controls for
`velo build` and `velo run` on both Stage 1 (Python) and Stage 2 (self-hosted):

1. `velo build <source.vl> [-o <binary>] [--debug | --release] [-O<level>]`
2. `velo run <source.vl> [--debug | --release] [-O<level>] [args...]`

## Modes & Flag Resolution

* **Default Mode**: `-O2` (backward-compatible; identical to current behavior).
* **Debug Mode (`--debug`)**: `-O0 -g` (disables compiler optimizations, embeds full
  debug symbols for GDB/LLDB debugging and fast compilation).
* **Release Mode (`--release`)**: `-O3 -flto` (maximum compiler optimizations and
  Link-Time Optimization for high performance).
* **Optimization Flag (`-O<level>` or `-O <level>`)**:
  - Valid levels: `0`, `1`, `2`, `3`, `s`, `fast`.
  - Can be passed independently (e.g. `-O3` sets `-O3`) or combined with `--debug`
    (e.g. `--debug -O1` uses `-O1 -g`).
* **Conflict Policy**:
  - Passing both `--debug` and `--release` triggers an error:
    `[Velo Error] Cannot specify both --debug and --release` (exit code 1).

## The Plumbing Map

### Stage 1 (Python)
* `velo.py`:
  - `build_parser` gains `--debug`, `--release`, and `-O`/`--optimize`.
  - `run_parser` gains `--debug`, `--release`, and `-O`/`--optimize`.
* `velo/driver.py`:
  - `compile_to_binary(source_path, output_path=None, debug=False, release=False, opt_level=None)`:
    constructs GCC command with appropriate flags:
    - If `debug`: flags include `-g`
    - Optimization flag: `-O{opt_level}` if specified, else `-O0` if `debug`, else `-O3` if `release`, else `-O2`.
    - If `release`: flags include `-flto`
  - `run(source_path, args=None, debug=False, release=False, opt_level=None)`:
    passes build mode flags to `compile_to_binary`.

### Stage 2 (Self-Hosted)
* `src/main.vl`:
  - Scans `argv` for `--debug`, `--release`, and `-O<level>` / `-O <level>`.
  - Checks conflict: if both `debug` and `release` are active, emits error and exits 1.
  - Passes `opt_flags` / build mode flags to `build_executable` and `run_source_file`.
* `src/backend/driver.vl`:
  - `build_executable`: accepts mode parameters or assembled GCC optimization string.
  - Constructs GCC command substituting `-O2` with the resolved flags.
  - `run_source_file`: passes mode parameters to `build_executable`.

## Slices

* **S1 — Stage 1 implementation & test battery.**
  - Plumb `--debug`, `--release`, and `-O<level>` into `velo.py` and `velo/driver.py`.
  - Add test battery `tests/test_build_modes.py` verifying Stage 1 flags, GCC command assembly,
    conflict detection, and binary execution.

* **S2 — Stage 2 self-hosted implementation & bootstrap rebuild.**
  - Plumb `--debug`, `--release`, and `-O<level>` into `src/main.vl` and `src/backend/driver.vl`.
  - Rebuild triple bootstrap chain Gen1 → Gen2 → Gen3 → `bin/velo.exe`.
  - Verify Gen2 ≡ Gen3 emit-c SHA-256 fixed-point determinism.
  - Extend `tests/test_build_modes.py` to test native compiler builds and runs.

* **S3 — Finale sweep, gaps.md audit & chapter close.**
  - Cumulative sweep `sweep_62_final.py`: 23/23 clean across Stage 1 and Stage 2.
  - Flip `gaps.md` §6.2 to `[COMPLETED] ✅`.
  - Final audit snapshot and commit.

## Verification Snapshot (shipped 2026-10-25)

* [x] Stage 1: `velo/driver.py` `build` & `run` support `debug`, `release`, and `opt_level`;
  `velo.py` CLI parser accepts `--debug`, `--release`, and `-O`/`--optimize`, with mutual
  exclusion conflict error handling and flexible flag positioning.
* [x] Stage 2: `src/main.vl` parses `--debug`, `--release`, and `-O<level>` / `-O <level>`,
  resolves flags via `resolve_opt_flags`, and passes `opt_flags` to `build_executable`
  and `run_source_file` in `src/backend/driver.vl`.
* [x] Triple-bootstrap chain rebuilt (Gen1 → Gen2 → Gen3 → `bin/velo.exe`); bit-for-bit
  determinism verified with Gen2 ≡ Gen3 SHA-256 fixed point:
  `64B604F2B44C74C92C92494C396A9C9ED8945101AE999FFB2E75994C7167C911`.
* [x] Battery `tests/test_build_modes.py`: 12/12 tests passing.
* [x] Full pytest suite: **249/249 passing** (was 237).
* [x] Cumulative finale sweep `sweep_62_final.py`: **23/23 clean, 0 diffs**.
* [x] Ceilings: all files <= 399 lines (`driver.vl` 305, `main.vl` 262).
* [x] `gaps.md` §6.2 marked `[COMPLETED] ✅`.

THE CHAPTER SHIPS IN FULL: `--debug` (-O0 -g), `--release` (-O3 -flto), `-O<level>`
controls on `velo build` and `velo run`, mutual exclusion conflict enforcement, and
flag position flexibility across both compiler stages.

---

## Sanitizer Local Build Mode (`sanitizer-local`)

Task 74.6: Dedicated AddressSanitizer (ASan) and UndefinedBehaviorSanitizer (UBSan) configuration for local and CI instrumentation.

### Goal

Enable deep instrumentation of the compiler binary and generated native executables to trap memory corruption (use-after-free, double-free, out-of-bounds heap/stack accesses) and C undefined behaviour (signed integer overflow, unaligned pointer dereference, null pointer dereference) immediately at the point of occurrence.

### Required Host Packages

#### Ubuntu / Debian (x86_64 / aarch64)
```bash
sudo apt-get update
sudo apt-get install -y clang gcc libasan8 libubsan1 python3 python3-pytest
```

#### macOS (Apple Silicon / Intel)
```bash
brew install llvm python3
pip3 install pytest
```

#### Windows (MSYS2 UCRT64 / Clang64)
```bash
pacman -S --needed mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-clang
```

### Compiler & Linker Flags

* **C Compiler Flags (`VELO_CFLAGS`)**:
  `-fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer -g -fwrapv`
* **Linker Flags (`VELO_LDFLAGS`)**:
  `-fsanitize=address,undefined`
* **Runtime Trap Environment (`ASAN_OPTIONS` / `UBSAN_OPTIONS`)**:
  - `ASAN_OPTIONS="detect_leaks=1:halt_on_error=1:abort_on_error=1"`
  - `UBSAN_OPTIONS="halt_on_error=1:abort_on_error=1"`

### Invocation Commands

1. **Full 3-Stage Sanitized Bootstrap & Verification**:
   ```bash
   bash scripts/bootstrap_sanitized.sh --full
   ```
   Compiles `bootstrap.c` with Clang/GCC under ASan+UBSan into `bin/velo`, verifies `bin/velo version`, builds Gen2 with sanitizers, builds Gen3 with sanitizers, verifies SHA-256 fixed-point determinism (`scripts/check_determinism.py`), and executes the test battery.

2. **Quick Sanitized Bootstrap (Bootstrap Snapshot Only)**:
   ```bash
   bash scripts/bootstrap_sanitized.sh --quick --no-test
   ```

3. **Running Targeted Test Battery Under Sanitizers**:
   ```bash
   bash scripts/bootstrap_sanitized.sh tests/test_heap_provenance.py tests/test_mem_overlaps.py
   ```


