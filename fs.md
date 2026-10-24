# 5.4 Extended File System & OS Primitives (`sys.fs`, `sys.os`) — Build Sheet

## Goal

Close the gaps.md 5.4 contract on both compiler stages: filesystem metadata
+ directory + streaming operations, plus an operating-system module for
environment/arguments/exit. Slices ship per the golden-rule cadence — both
stages in one commit, wording-mirrored closed namespaces, byte-equal emit,
battery + sweep each slice.

## Contract

* **Both stages, one unit**: Python stage 1 (`velo/codegen_c.py` +
  `velo/monomorphize.py`) and self-hosted stage 2 (`src/analysis/*_checks.vl`,
  `src/backend/*_gen.vl`, `src/analysis/type_checker.vl`,
  `src/backend/codegen_expr.vl`, `src/backend/driver.vl`) land in the same
  commit with identical checker wording and byte-identical emit.
* **Closed naming**: modules have NO constants — the property lane rejects
  every bare read with the time-family wording (`unknown <mod> constant...`
  + parens hint when the member names a known function). Unknown CALL
  members report the closed-set listing (functions: ...).
* **Line discipline**: this chapter starts with `type_checker.vl` AT its
  399 ceiling and `codegen_expr.vl` at 397. New twin lanes MUST consolidate
  onto single lines (the `;`-joined one-liner style the file already uses)
  so the files never cross 400. New per-member logic goes into the NEW
  `*_checks.vl` / `*_gen.vl` files exclusively.
* **Runtime helpers own the platform `#if`**: Windows rides CRT/kernel32
  APIs through self-declared prototypes (no `windows.h`); POSIX flags come
  from `_POSIX_C_SOURCE` (bumped where the surface needs it — superset
  values only). Both compilers emit the same helper-call bytes.
* **argv plumbing**: both emitters already wrap main as
  `int main(int argc, char** argv)`; the runtime gets file-scope
  `g_velo_os_argc`/`g_velo_os_argv` statics and BOTH emitters inject the
  identical stash bytes (`g_velo_os_argc = argc;` / `g_velo_os_argv = argv;`)
  as the first two lines of main (stage 1 at indent 0 via `_emit_line`,
  stage 2 as raw `sb_append_str` — byte-equal by construction).
* **Nondeterministic-surface rule** (5.5 mechanic): anything
  machine/environment-dependent prints in-program VALIDATED verdicts or
  round-trip values only — raw paths/ticks never touch stdout.

## Slice plan

* **S1 — `sys.os` scaffold**: `os.args() -> shelf[string]` (full argv,
  argv[0] included; deep coverage via DIRECT exe invocation in the battery —
  `velo run` cannot pass program args), `os.get_env(key) -> string`
  (unset ⇒ owned empty string), `os.set_env(key, val) -> bool`
  (Windows `_putenv_s` / POSIX `setenv` — `_POSIX_C_SOURCE` bumps to
  200112L, superset), `os.exit(code)` (void; direct C `exit((int)(...))`
  lowering, 1 int arg). Closed namespace wording + result lanes + property
  rejects; battery (incl. exit-code-7 and custom-argv rows driven per stage)
  + sweep + docs.
* **S2 — `sys.fs` metadata family**: `fs.is_dir(path) -> bool`,
  `fs.is_file(path) -> bool`, `fs.create_dir(path) -> bool`,
  `fs.create_dir_all(path) -> bool`, `fs.copy(src, dst) -> bool`,
  `fs.rename(src, dst) -> bool`. The fs namespace goes CLOSED: the six
  legacy members (`read_file`, `write_file`, `size`, `exists`, `remove`,
  `remove_file` — old §4.2 unchecked era) migrate INTO the checked umbrella
  with result spells preserved exactly; wording lists ALL members. Runtime
  helpers own the platform split (Windows kernel32 `GetFileAttributesW` /
  `CreateDirectoryW` / `CopyFileW` / `MoveFileW` self-declared prototypes,
  wide-string conversion helpers for Velo `char*` paths; POSIX `stat`/
  `mkdir -p` loop / rename(2)).
* **S3 — `fs.read_dir(path) -> shelf[string]`**: entry NAMES split across
  the platform directory iteration (Windows `FindFirstFileW`/`FindNextFileW`
  self-declared; POSIX <dirent.h> — system-declared, no feature risk);
  shelf construction rides the `velo_str_split` owning-token pattern
  (`VeloShelf` + `velo_shelf_put`). The listing itself is
  order-nondeterministic — battery sorts in-program before printing.
* **S4 — file streaming**: `fs.fopen(path, mode) -> @File`,
  `fs.fread(file, count) -> string`?/buffer shape,
  `fs.fwrite(file, data)`, `fs.fseek(...)` (+ close implied by RAII-less
  explicit `fs.fclose`), mirroring the @Thread/@Mutex opaque-handle
  doctrine. OPEN design questions at S4 start: the fread buffer shape
  (owned string return vs read-into shelf[u8]), mode validation (CRT mode
  string "rb"/"wb"), and whether @FILE* values ride var storage unboxed.
  Final check/emit shapes land with the slice.
* **S5 — example 35 + chapter close** (mirrors 5.3 S5 / 5.5 S2).

## S1 — sys.os scaffold (SHIPPING NOW)

Missing surface:

* [x] `velo/runtime/velo_runtime.h`: `_POSIX_C_SOURCE` 199309L → 200112L;
      os block after the time block — argv statics + `velo_os_get_env`
      (getenv + owned-copy, unset ⇒ ""), `velo_os_set_env`
      (Windows `_putenv_s` / POSIX `setenv(key, val, 1)`),
      `velo_os_args` (VeloShelf of owned token copies, argv[0] included;
      lives with the shelf machinery next to `velo_str_split` — needs
      `velo_shelf_put`).
* [x] Stage 1 `velo/codegen_c.py`: OS tables + `_os_expect` (closed set,
      arity walls, string/int got-walls) + `_emit_os_call`
      (helper calls + direct `exit((int)(...))`); result branches in BOTH
      infer lanes; property rejects on BOTH property paths; emit dispatch
      twin; main-wrapper argv stash (indent-0 lines, byte-matched with
      stage 2).
* [x] Stage 1 `velo/monomorphize.py`: `os` joins the module-receiver set.
* [x] Stage 2 NEW `src/analysis/os_checks.vl` (time_checks.vl shape);
      NEW `src/backend/os_gen.vl`; `type_checker.vl` wiring — the use line
      added, property/call twins CONSOLIDATED onto the existing single-line
      lanes (file now 398); `codegen_expr.vl` (use + twin, same-line
      consolidation — 398); `codegen_c.vl` staging the same two stash bytes
      (397); `driver.vl` whitelist `sys.os` in BOTH spots.
* [x] Probe accepts (byte-equal: set/get round trip prints the env VALUE;
      args count verdicts; exit(7) pins rc 7 with prior stdout intact) and
      rejects (closed-set wording, arity walls, got walls, property lane)
      on BOTH stages; `.vl` probes BOM-less.
* [x] `tests/test_os_library.py`: round-trip + verdict rows (byte-equal),
      per-stage DIRECT exe invocation with custom argv pinning count 3 +
      "tok alpha beta", exit(7) returncode row, rejects word-pinned.
* [x] Sweep `sweep_54_s1.py` (accepts byte-equal verdicts + the exit rc
      row, rejects wording-normalized; direct-argv rows stay battery-only —
      `velo run` cannot pass program args — documented in the sheet).
* [x] Full suite green; chain rebuild Gen1→Gen2→Gen3 + `bin/velo.exe`;
      fixed point (Gen2 ≡ Gen3 SHA-256); `count_lines.py` max ≤ 399.
* [x] `gaps.md`: 5.4 S1 `[COMPLETED] ✅` entry (header stays 🟠 until close).

S1 verification snapshot: suite **199/199** (193 + the 6-test os battery) ·
sweep 17/17 (4 accepts — incl. the exit-rc row driven through the normal
runner — + 13 rejects) · fixed point
`73AD4D29AFDFDA65488F6361617B7DF34DBB6C85B5C8A2A43005DA2F62FB3837`
(Gen2 ≡ Gen3 — the argv stash changed the emit text) · count_lines max
398 (`codegen_c.vl` 397) · chain Gen1→Gen2→Gen3 rebuilt + `bin/velo.exe`
copied. Lab notes: (1) `use sys.str` is NOT a whitelisted marker on stage
2 — the str pseudo-module needs NO use line (example-30 precedent), the
sweep's first args row probed it and was rewritten bare; (2) `1.5`
defaults to f32, so `os.exit(1.5)` reads "got f32" — battery pins the
f32-literal row (5.5 lesson, applied directly this time).

## S1 verification ladder

1. Chain build exercises the new runtime block (POSIX branch is
   best-effort — the live toolchain is mingw ucrt64).
2. Probe matrix both stages — wording byte-identical after the
   stage-envelope strip.
3. Battery margins: set/get round trip on a unique env key (value byte-
   pinned); unset read pins ""; args count ≥ 1 verdict via `run`; direct
   invocation rows pin exact count + tokens; os.exit(7) pins rc 7 with
   prior output intact.
4. Sweep + full suite + fixed point + ceilings.
