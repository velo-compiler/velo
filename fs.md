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
  with result spells preserved exactly; wording lists ALL members (ship
  order: legacy six first, then the metadata family). Runtime helpers own
  the platform split — DECIDED DURING THIS SLICE: **pure CRT everywhere**
  (the kernel32/wide-string sketch in this plan was superseded — Velo
  paths are narrow `char*`, so `struct stat`+`S_ISDIR` classify,
  `_mkdir`/`mkdir(path, 0777)` create one level, a portable stdio loop
  ("rb"/"wb") copies, CRT `rename` moves; no kernel32, no windows.h, no
  `errno` — the "already exists" race is resolved by stat-verification).
* **S3 — `fs.read_dir(path) -> shelf[string]`**: entry NAMES only (no
  paths; "." and ".." filtered — the usable surface). Platform iteration
  in the runtime helper (Windows: the CRT's narrow `_findfirst/_findnext/
  _findclose` over a `<path>/*` probe — a bare directory path would match
  only itself; POSIX: <dirent.h> opendir/readdir/closedir). Shelf
  construction rides the `velo_str_split` owning-token pattern
  (`VeloShelf` + `velo_shelf_put`) — the helper lives BESIDE THE SHELF
  MACHINERY (next to `velo_os_args`/`velo_str_split`, after VeloShelf is
  defined — S1's forward-definition lesson). Contract: missing or
  unreadable dir ⇒ EMPTY shelf (the list never kills the program — pair
  with `fs.is_dir`); ordering is platform/filesystem-defined — pins use
  set-membership (`str.contains` over a joined subject), never sequence;
  the single-entry case pins the exact name. Member listing grows to 13
  (`..., copy, rename, read_dir`) in BOTH stages' wording lanes.
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

## S2 verification snapshot

* [x] Runtime: `#include <sys/stat.h>` (+ `direct.h` under `_WIN32`) and
      the six helpers after the legacy block — `velo_fs_is_dir/is_file`
      (stat + S_ISDIR/S_ISREG), `velo_fs_create_dir`,
      `velo_fs_create_dir_all` (segment walker: both separators normalized
      to `'/'` in the working copy, drive prefix skipped, EEXIST resolved
      by stat-verify — idempotent like `mkdir -p`), `velo_fs_copy`
      (portable 4 KiB stdio loop), `velo_fs_rename` (CRT rename).
* [x] Stage 1 `velo/codegen_c.py`: FS tables (12 members, arity/sig/funcs
      text) + `fs_member_result_type`; `_fs_expect` (closed set, arity
      walls with era-consistent sigs, homogeneous string got-walls) +
      `_emit_fs_call`; result lanes ×2 → one-line `fs_member_result_type`
      returns; emit dispatch → `_emit_fs_call` (legacy `_lower_fs_*`
      emitters kept byte-identically, their dead arity raises deleted);
      property twin after the os twin.
* [x] Stage 2: NEW `src/analysis/fs_checks.vl` (os_checks shape, 12-member
      tables + `check_fs_call`/`check_fs_constant`); NEW
      `src/backend/fs_gen.vl` (legacy six VERBATIM from codegen_expr.vl +
      the six new rows); `type_checker.vl` — the 3-line legacy fs block →
      one-liner `check_fs_call` dispatch (−3), use line (+1), property
      twin appended to the consolidated lane (0) → **397**;
      `codegen_expr.vl` — the inline ladder moved to fs_gen.vl (−11), use
      line (+1), one-liner dispatch → **388**. `driver.vl`/`monomorphize.py`
      needed NO edits (fs already whitelisted); THE COMPILER'S OWN
      `src/check.vl`/`src/driver.vl` fs uses passed the new walls live
      during the chain rebuild (Gen1→Gen3).
* [x] Sweep `sweep_54_s2.py` **18/18 clean, 0 diffs, rerun-clean** (4
      accepts — legacy six regression, metadata family, copy/rename,
      empty-payload round trip — + 14 rejects word-pinned after the
      stage-envelope strip). Fixture hygiene: per-STAGE tag files read
      through `fs.read_file` → unique fixtures per stage run; the obstacle
      row pins create_dir failing under a FILE parent (deterministic
      ENOTDIR). Lab note from the pass: the arity wall names the EXPECTED
      count — "expects exactly 1 argument" is the correct reject for a
      2-arg call of a 1-ary member (the first draft wanted the given
      count; both stages agreed on the expectation wording).
* [x] Battery `tests/test_fs_library.py` — 6 tests (legacy round trip,
      metadata family incl. fresh create rows + obstacle, copy/rename via
      unique tags honoring the Windows CRT rename no-overwrite rule,
      empty-payload round trip, 12 reject wordings, property pair).
* [x] Full suite **205/205**; chain rebuilt Gen1→Gen2→Gen3 +
      `bin/velo.exe`; fixed point
      `199933160AFB9DE44D753406CBB06B4EDD38BEA6387294832B089DCFFB76AB55`
      (Gen2 ≡ Gen3 — moved from S1's `73AD4D29…`); count_lines clean —
      fs-edited files at 397/397/388.

## S3 verification snapshot

* [x] Runtime: `io.h` (Windows) / `dirent.h` (POSIX) joins the platform
      include block; `velo_fs_read_dir` placed BESIDE THE SHELF MACHINERY
      (after `velo_os_args`, before the 5.2 map section) — the first chain
      build caught the S1 forward-definition lesson the hard way
      (`unknown type name 'VeloShelf'` when the helper sat in the fs
      block; one duplicated-insertion detour during the move, collapsed
      back to a single definition — grep-pinned before recompiling).
* [x] Stage 1: `FS_CALLS`/`FS_SIGS`/`FS_FUNCS_TEXT` grow read_dir;
      `fs_member_result_type` → `shelf[string]`; NO other stage-1 code
      changed — `_emit_fs_call`'s generic tail already lowers any member
      via `velo_fs_<member>(...)` (the S2 dispatch design paying off).
* [x] Stage 2: `fs_checks.vl` tables grow read_dir (arity/sig/ret) and
      BOTH unknown-member/constant wording strings grow to the 13-list;
      `fs_gen.vl` gains the one-liner `velo_fs_read_dir(...)` row.
      `type_checker.vl`/`codegen_expr.vl`/`codegen_c.vl`/`driver.vl`/
      `monomorphize.py` all UNCHANGED.
* [x] Sweep `sweep_54_s3.py` **8/8 clean, 0 diffs** (4 accepts — two-entry
      order-independent row, single-entry exact row, empty dir, missing
      dir pinning the empty-on-failure contract — + 4 rejects incl. the
      grown closed-set wording and read_dir's own walls + bare-read hint).
* [x] Battery `tests/test_fs_library.py` — S2 wording rows updated to the
      13-list (the unknown-member + shared property funcs var), and a
      `TestFsSlice3` class: two-entry listing (count + contains-pins),
      single-entry exact pin, empty+missing edges, read_dir reject
      surface (3 rows + the bare-read hint pair).
* [x] Full suite **209/209**; chain rebuilt (Gen1→Gen2→Gen3 + `bin/velo.exe`); fixed point `E99B1C7C517BA9F99BE7613F2C5F9BF87F7B619F91ADEAD51A0FEE7E0272DF3B` (Gen2 ≡ Gen3); count_lines clean —
      fs-edited ceilings unchanged at 397/397/388 (fs_checks 140, fs_gen
      58).

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
