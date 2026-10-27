# linker_flags.md — 6.1 Linker Flags for Third-Party C Libraries: complete build sheet

> Companion to `gaps.md` §6.1. Everything the chapter needs, with the target
> contract. Every change lands as one golden-rule unit:
> pin in `gaps.md` §6.1, both compiler stages verified, parity suite,
> bootstrap chain rebuild + Gen2 ≡ Gen3 emit-c SHA-256 fixed point,
> `scripts/count_lines.py` clean (<= 399 lines), and one conventional commit.

## Goal

Enable Velo programs to link against external C and system libraries
(e.g. `raylib`, `SDL2`, `opengl32`, `gdi32`, `winmm`, `m`, etc.) via standard
linker flags `-l<lib>` and library search paths `-L<dir>`:

```bash
velo build main.vl -o game.exe -lraylib -lopengl32 -lgdi32 -lwinmm
velo run main.vl -lwinmm
```

## Syntax & Contract

* **Library Linking (`-l<lib>` or `-l <lib>`)**:
  - Direct translation to GCC linker argument `-l<lib>`.
  - Multiple libraries can be specified in any order (e.g. `-lwinmm -lgdi32`).
  - Supports both attached (`-lwinmm`) and separated (`-l winmm`) forms.
* **Search Path (`-L<dir>` or `-L <dir>`)**:
  - Direct translation to GCC library search directory `-L<dir>`.
  - Supports both attached (`-L./lib`) and separated (`-L ./lib`) forms.
* **Placement in GCC Invocation**:
  - GCC linker flags `-L<dir>` and `-l<lib>` MUST appear **after** the compiled
    C source file (`.velo_cache/<stem>.c`), guaranteeing that undefined external
    references from Velo C codegen are resolved in GCC's left-to-right link pass.
* **Command Surface**:
  - Supported on both `velo build` and `velo run`.
  - Fully combinable with §6.2 build modes (`--debug`, `--release`) and `-O<level>`.

## The Plumbing Map

### Stage 1 (Python)
* `velo.py`:
  - `build_parser` gains `-l` (`action="append"`) and `-L` (`action="append"`).
  - `run_parser` gains `-l` and `-L` arguments; raw trailing args are scanned for
    `-l` / `-L` passed after the file path.
* `velo/driver.py`:
  - `build(..., libs=None, lib_dirs=None)` and `run(..., libs=None, lib_dirs=None)`.
  - Formats `-L<dir>` and `-l<lib>` into linker flags placed after `c_file` in `cmd`.

### Stage 2 (Self-Hosted)
* `src/main.vl`:
  - Scans `argv` in `build` and `run` commands for `-l<lib>`, `-l <lib>`, `-L<dir>`, `-L <dir>`.
  - Assembles `linker_flags: string`.
  - Passes `linker_flags` to `build_executable` and `run_source_file`.
* `src/backend/driver.vl`:
  - `build_executable(..., opt_flags: string, linker_flags: string) -> bool`.
  - `run_source_file(..., opt_flags: string, linker_flags: string) -> i32`.
  - Appends `linker_flags` immediately after `to_native_path(c_file_path)` in `cmd_sb`.

## Verification Snapshot [SHIPPED ✅ 2026-10-25]

* **Unit Tests** (`tests/test_linker_flags.py`):
  - 11/11 passing across Stage 1 and Stage 2.
  - Verifies GCC command includes `-l<lib>` and `-L<dir>` strictly after the `.c` file.
  - Compile and run actual programs with `extern act` calling linked C functions (`timeGetTime` from `winmm`).
  - Verifies missing `-lwinmm` fails linking with undefined reference on both Stage 1 and Stage 2.
  - Attached (`-lwinmm`, `-L./lib`) and separated (`-l winmm`, `-L ./lib`) flag forms verified.
  - Flag position flexibility: works before or after input file or output binary.
  - Combination with §6.2 build modes (`--debug`, `--release`, `-O1`, `-O2`, `-O3`).
* **Finale Sweep** (`.velo_cache/sweep_61_final.py`):
  - **22/22 clean, 0 diffs** covering all linker and library path scenarios across both compilers.
* **Full Test Suite**: **260/260 passing** (was 249).
* **Bootstrap Chain & Determinism**:
  - Triple-bootstrap chain rebuilt: Gen1 → Gen2 → Gen3 → `bin/velo.exe`.
  - Bit-for-bit determinism verified: Gen2 ≡ Gen3 `emit-c src/main.vl` SHA-256 fixed point:
    `D5F9F45C607718895C8AC9A5C7E7AA68E485EC3F53B614358F5706C000945E3D`.
* **Line Count Ceilings**:
  - All source files ≤ 399 lines (`scripts/count_lines.py`):
    `src/backend/driver.vl` 309 lines, `src/main.vl` 298 lines.

