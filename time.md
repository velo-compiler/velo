# 5.5 High-Resolution Clock & Timing (`sys.time`) — Build Sheet

## Goal

Close the gaps.md 5.5 contract: a high-resolution, monotonic clock module for
game-loop timing on both compiler stages. Three members, a CLOSED namespace,
and one deterministic margin-based battery row set:

* `time.now() -> i64` — microseconds since boot (monotonic; QPC on Windows,
  `clock_gettime(CLOCK_MONOTONIC)` on POSIX).
* `time.delta() -> i64` — microseconds since the previous `delta()` call
  (the first call anchors and returns 0; the "last" state is a module-static
  inside the runtime helper — the thread-surface precedent for runtime state;
  single-threaded usage contract, documented residual).
* `time.sleep_ms(ms)` — void; int duration ONLY (every int spell rides an
  emitted `(long long)(...)` widen; f32/f64/bool/string/collections reject).

## Contract

* **Both stages, one unit**: Python stage 1 (`velo/codegen_c.py` +
  `velo/monomorphize.py`) and self-hosted stage 2
  (`src/analysis/time_checks.vl`, `src/backend/time_gen.vl`,
  `src/analysis/type_checker.vl`, `src/backend/codegen_expr.vl`,
  `src/backend/driver.vl`) land in the same commit with byte-identical emit
  and identical checker wording.
* **Runtime helpers**: `velo_time_now_us()` / `velo_time_delta_us()` /
  `velo_time_sleep(long long ms)` in `velo/runtime/velo_runtime.h`. The
  platform `#if` lives HERE, once — both compilers emit the same call shape,
  so emitted C differs only in the program body. Windows rides
  QueryPerformanceCounter/QueryPerformanceFrequency through self-declared
  `__stdcall` prototypes (the §4.2 thread-surface precedent: no `windows.h`,
  kernel32 is default-linked). Sleep rides kernel32 `Sleep(DWORD)`. POSIX
  defines `_POSIX_C_SOURCE 199309L` before the first `<time.h>` include so
  the SYSTEM declares clock_gettime/nanosleep (no redeclaration risk).
* **Overflow-safe µs**: `whole = counter / freq; rem = counter % freq;
  now = whole * 1000000LL + rem * 1000000LL / freq` — the naive
  `counter * 1e6 / freq` overflows i64 after ~2 weeks at a 10 MHz counter.
* **Clock failure is loud**: QPC/QPF failure or `clock_gettime` failure →
  `velo_fatal_msg(...)`.
* **Closed namespace wording** (mirror of the shelf/math precedents):
  * CALL lane unknown member: `unknown time member '<m>' (functions: now, delta, sleep_ms)`
  * PROPERTY lane: `unknown time constant '<m>' (time functions are: now, delta, sleep_ms)`
    with the hint ` (functions need parens: time.<m>())` when the member
    names a known function (math's bare-`math.sqrt` precedent; time has NO
    constants, so the property lane rejects everything).
  * Arity walls: `time.now expects exactly 0 arguments` /
    `time.delta expects exactly 0 arguments` (0-ary → no sig tail) /
    `time.sleep_ms expects exactly 1 argument: (i64 ms)`.
  * Got wall: `time.sleep_ms expects int arguments (got <t>)`.
* **Result spell**: `now`/`delta` → `i64` on both result-inference lanes;
  `sleep_ms` → `void` (statement-lane calls ride the io.println mechanism).
* **The window problem**: elapsed times are nondeterministic, so battery
  rows must be margin-validated per stage and print DETERMINISTIC strings
  for the byte-equal cross-stage comparison (window assertions live on each
  stage separately; the byte-equal pin holds because the printed strings are
  window-checked, not raw tick prints).
* **Determinism/parity mechanics**: `emit-c src/main.vl` must stay byte-
  identical Gen2≡Gen3; the runtime header is shared, so no emitter-side
  `#if` is ever needed.

## S1 — module scaffold + now/delta/sleep_ms + closed namespace (BOTH stages)

Missing surface:

* [x] `velo/runtime/velo_runtime.h`: `#define _POSIX_C_SOURCE 199309L`
      (non-Windows, before the first `<time.h>` include), the §5.5 clock
      block after the §4.2 thread surface — `velo_time_li` union (Win64
      LARGE_INTEGER layout, LLP64), kernel32 prototypes
      (`QueryPerformanceCounter` / `QueryPerformanceFrequency` / `Sleep`),
      the three `static inline` helpers, POSIX `#else` branch.
* [x] Stage 1 `velo/codegen_c.py`: TIME tables + `_time_expect` (closed set,
      arity, int-wall) + `_emit_time_call` (helper calls); result branches at
      `_infer_raw_velo_type` / `_resolve_expr_type`; emit dispatch twin;
      property-lane rejects on both property paths (infer + emit).
* [x] Stage 1 `velo/monomorphize.py`: `time` joins the module-receiver set.
* [x] Stage 2 NEW `src/analysis/time_checks.vl` (math_checks.vl shape:
      arity/sig/ret/arg_ok/got acts + `check_time_call -> string` +
      `check_time_constant`); NEW `src/backend/time_gen.vl` (3-form emit
      ladder); `type_checker.vl` wiring (use + pseudo-type set + property
      twin + call branch); `codegen_expr.vl` (use + emit twin);
      `driver.vl` whitelist `sys.time` in BOTH spots.
* [x] Probe accepts (byte-equal: first delta pins 0, sleep window prints ok)
      and rejects (closed-set wording, 0-ary walls, sleep arity + got walls,
      property lane) on BOTH stages; every `.vl` probe written without a BOM.
* [x] `tests/test_time_library.py`: margin windows per stage + deterministic
      string equality across stages + reject rows (wording-normalized).
* [x] Sweep `sweep_55_s1.py` (accepts byte-equal, rejects wording-normalized).
* [x] Full suite green; chain rebuild Gen1→Gen2→Gen3 + `bin/velo.exe`;
      fixed point (Gen2 ≡ Gen3 SHA-256 on `emit-c src/main.vl`);
      `count_lines.py` max ≤ 399 (compiler `.vl` sources only).
* [x] `gaps.md`: 5.5 S1 `[COMPLETED] ✅` entry (header stays 🟠 until close).

S1 verification snapshot: suite **192/192** (188 + the 4-test time battery) ·
sweep 21/21 (9 accepts with pinned in-program verdict strings + 12 rejects) ·
fixed point
`60791243D6D09B187E9EB4341FD6B45DA9C0B278697BA9DB83872D1560EB220F`
(Gen2 ≡ Gen3) · count_lines max 399 (`type_checker.vl` exactly at budget) ·
chain Gen1→Gen2→Gen3 rebuilt + `bin/velo.exe` copied. Lab note: the sweep's
f64-pin row initially expected `got f64` for `time.sleep_ms(1.5)` — the
literal is f32 by default (house literal curve) and both stages agreed on
`got f32`; the battery pins f32-literal + annotated-f64-local rows instead.

## S2 — example 34 + chapter close (mirrors 5.3 S5)

Missing surface:

* [x] `examples/34_time_basics.vl` (example-30 house style: header comment,
      deterministic single-sweep program — six numbered sections: the zero
      anchor, the monotonic pair across a real sleep, the delta round trip,
      plain i64 dt arithmetic, the statement-lane sleep across int spells
      (i8 word, default literal, negative clamp), and the shelf[i64] tick
      log; every margin validated IN the program so only fixed verdict
      strings reach stdout; every interpolation binds locals first —
      gaps 6.7. Lab note: locals deliberately dodge the libc-shadow class —
      `log` (libc log!) and the C-keyword `short` were both avoided at
      authoring time; the file aired clean on the FIRST build on both
      stages).
* [x] `tests/test_time_library.py` gains the example-34 parity row
      (`EXAMPLE34_LINES`, byte-identical both stages) — 6-line fixture,
      `TestTimeExample34` returncode + byte-equal + exact-line pins.
* [x] `gaps.md` 5.5 → `[COMPLETED] ✅` with the Final-form slice entry
      (Former Defect → Fix → Residual → Verification) — chapter header is
      now `COMPLETE (slices 1–2)`.
* [x] Sweep finale (full-row recount) + chain fixed point + count_lines
      max ≤ 399 verified in the close commit — `sweep_55_final.py` 22/22;
      fixed point `60791243…` re-verified (no compiler source touched in
      S2 — nothing to rebuild); count_lines 399 max.
* [x] docs: math.md untouched (5.3 is closed); VELO.md stays untracked.

S2 verification snapshot: suite **193/193** (192 + the example-34 parity
row) · finale sweep 22/22 (the full 21-row S1 recount + the example-34 row
run from the repo root) · fixed point
`60791243D6D09B187E9EB4341FD6B45DA9C0B278697BA9DB83872D1560EB220F`
(unchanged — no compiler source in the close) · count_lines max 399.

## Verification ladder (S1)

1. Runtime block compiles standalone (the chain build exercises it).
2. Probe matrix on both stages — every row's wording byte-identical after
   the stage-2 envelope strip (`semantic:l:c - ` prefix + error-count tail).
3. Battery margins: sleep 50 ms ⇒ measured elapsed in [45_000, 2_000_000] µs;
   `now` monotonic (`now2 >= now1`) with a < 10 s span; first `delta()` == 0
   exactly; post-sleep `delta()` in the sleep window.
4. Sweep + full suite + fixed point + ceilings.
