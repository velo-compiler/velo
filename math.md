# math.md — 5.3 Math Library (`sys.math`): complete build sheet

> Companion to `gaps.md` §5.3. Lists EVERYTHING the math chapter still needs,
> with the target contract for each remaining slice. Every slice lands as one
> golden-rule unit: pin the slice in `gaps.md` 5.3 ✅ (＋ tests + `math.md`),
> both compiler stages in the same commit → parity suite → bootstrap chain
> rebuild + Gen2 ≡ Gen3 emit-c SHA-256 fixed point → `scripts/count_lines.py`
> clean → one conventional commit.

## House rules (shared with 5.1/5.2)

* `math` is the receiver name; `use sys.math` is the marker (no load-time
  validation, same as every `sys.*` module). Receiver semantics are IDENTICAL
  to `io`/`mem`/`str`/`fs`/`thread`: module branches win for the bare
  receiver name; a user local named `math` shadows through the normal
  identifier path per stage — do not invent new shadow rules.
* Budget rule: `type_checker.vl`, `monomorphize*.vl`, `symbol_table.vl`,
  `stmt.vl`, `lexer.vl` sit AT the 399-line ceiling; `codegen_expr.vl` at 398.
  All math logic lives in NEW files — Stage 2 `src/analysis/math_checks.vl`
  (+ later emit side) wired via `type_check_program.vl` / `codegen_expr.vl`;
  the ceiling files may grow at most 1–2 compressed lines, paid for by
  compressing existing multi-line blocks in the same file (line-count neutral
  or negative).
* `velo_runtime.h` is the SHARED runtime (both stages `-I velo/runtime`):
  its `#include <math.h>` is added once; NO velo_math_* helpers are planned —
  math lowers directly onto C99 libm via emitted `(double)` casts, so the
  stages cannot diverge on the arithmetic itself.
* Number-literal widening contract (pinned in slice 1, reused by every slice):
  `math.` scalar-call arguments accept `f64`, `f32` (the default float
  literal spell!), and every int width (`i32`, `i64`, `u64`, `usize`);
  int/float args widen through an emitted `(double)(...)` exactly. `bool`,
  `string`, shelves/maps, structs, pointers reject with the parity wording
  typical for the member (see S1). `f64` returns are printed through the
  existing printf ladder (`%f` / `%.2f` interpolation) — BOTH stages share
  the same libc formatting, so pins are byte-stable.
* libc-defined domains (NaN from sqrt(-1.0), Inf overflow, log(0)) are NOT
  pinned by batteries — identical C on both stages, but representation is
  libc property. Documented residual, not swept.

## S1 — module scaffold + constants + sqrt/pow/cbrt ✅ ([COMPLETED] in gaps.md 5.3)

Missing surface:

* [x] `use sys.math` accepted on both stages (module marker `driver.vl` whitelisted in both pass spots; no loader failure).
* [x] Constants as bare member properties on the `math` receiver, all `f64`,
      emitted as full-precision decimal literals (`(...)` wrapped):
      `math.PI` = `3.14159265358979323846`,
      `math.TAU` = `6.28318530717958647692`,
      `math.RAD2DEG` = `57.2957795130823208768`,
      `math.DEG2RAD` = `0.01745329251994329577`.
      Identical digit strings written by BOTH compilers (string bytes, not
      float round-trips).
* [x] Property rejects: `unknown math constant '<m>' (constants: PI, TAU, RAD2DEG, DEG2RAD)` + `(functions need parens: math.<fn>(...))` hint when the member names a known function — byte-identical wording both stages (sweep rows `rej_bare_function` / `rej_unknown_const`).
* [x] Function calls `math.sqrt(x)`, `math.pow(b, e)`, `math.cbrt(x)` → `f64` (sweep `sqrt_ladder` over ALL int spellings + f32/f64; `pow_family`; `cbrt_family`), widen through `(double)(...)` exactly; rejects mirror `math.<m> expects f64 (or int) arguments (got <t>)`.
* [x] Arity rejects `math.<m> expects exactly <n> arguments(<sig>)` byte-identical both stages (sweep `rej_pow_missing` / `rej_sqrt_zero` / `rej_cbrt_two`).
* [x] Unknown member CALL: the math namespace is CLOSED (shelf unknown-member precedent) — `unknown math member '<m>' (functions: sqrt, pow, cbrt; constants: PI, TAU, RAD2DEG, DEG2RAD are available)` (sweep `rej_unknown_member`).
* [x] Stage 2: `src/analysis/math_checks.vl` NEW (digits table `math_constant_digits`, sig `math_member_sig`, arity `math_member_arity`, ret `math_member_ret`, arg ladder `math_arg_ok`, got-msg `math_got_msg`, entries `check_math_call` / `check_math_constant`); wired via `type_checker.vl` (line 60 pseudo-type + call/property branches) and `codegen_io.vl` (interpolation constants guard). Ceiling discipline: `type_checker.vl` compressed 399→396.
* [x] Stage 1: `velo/codegen_c.py` `math` branches in `_resolve_expr_type` (property + call ladders), `_infer_raw_velo_type` (element estimation), `_emit_expression` (call emit + property emit), `_lower_io_call` path helpers (interpolation), and `_math_expect`/`_emit_math_call` (`MATH_CALLS` table).
* [x] `velo_runtime.h`: `#include <math.h>` — NO `-lm` needed (probe confirmed MinGW ucrt64 links libm via libmingwex/msvcrt defaults).
* [x] `monomorphize.py` module-receiver set gained `"math"` (Stage-2 twin verified absent by probe).
* [x] Tests: `tests/test_math_library.py` — 4 tests (accepts parity + 6 reject rows), byte-identical stdout; rejects compared after stripping house stage wrappers.
* [x] Sweep: `sweep_53_s1.py` 20/20 clean, 0 diffs.

Verification snapshot: suite 183/183 · sweep 20/20 · fixed point `30ED5F3C3F2EF7378A1695745E7C157DFAF378DAE7D99937A7208BE4A2F21EDB` (Gen2 ≡ Gen3) · count_lines max 399 (math logic in `math_checks.vl` = 130).


## S2 — trigonometry (sin/cos/tan/atan2/acos/asin) ✅ ([COMPLETED] in gaps.md 5.3)

Missing surface:

* [x] `math.sin(x)`, `math.cos(x)`, `math.tan(x)`, `math.atan2(y, x)`,
      `math.acos(x)`, `math.asin(x)` → `f64`, S1 widening/reject contract
      reused as-is (pure low-diff members; atan2 is 2-ary). Stage-1
      `MATH_CALLS`/`_emit_math_call`/`_math_expect` grew the 6 members;
      stage-2 `math_member_sig`/`math_member_arity` grew the same curves and
      `math_member_ret` SIMPLIFIED to arity-membership (`arity > -1` → f64),
      so every future family needs no ret-ladder edit.
* [x] Emit refactor: the stage-2 per-member emit ladder moved OUT of
      `codegen_expr.vl` (398→395) into NEW `src/backend/math_gen.vl` (36
      lines, `emit_math_call(sb, st, member, expr)` carrying all 9 forms
      with the S1 pow-split discipline — one closing paren for 2-arg
      members); `codegen_expr.vl`'s math branch is now a single call line.
* [x] Pins: exact-IEEE arc legs `acos(1)=0.000000`, `acos(0)=asin(1)=1.570796`
      (π/2); `sin(0)=0.000000`, `cos(0)=1.000000`, `tan(0)=0.000000`;
      `atan2(1.0, 1.0)` → `%.2f` = `0.79`; int/f32-widened spellings
      (`sin(i32)`, `atan2(i64, i64)`, `cos(f32)`) match stage 1 byte-for-byte.
      Domain-edge probes beyond these stay unpinned (libc residual).
* [x] Closed-set wording grew per slice rule: `unknown math member '<m>'
      (functions: sqrt, pow, cbrt, sin, cos, tan, atan2, acos, asin;
      constants: PI, TAU, RAD2DEG, DEG2RAD are available)` — updated in ALL
      copies (stage-1 `_math_expect`, stage-2 `check_math_call`, battery row,
      sweep row).
* [x] Batteries: `test_accepts_trig_family` (13 rows incl. `sin(1.0)+sin(0.0)`
      arithmetic and a math element in the shelf[f64] ladder), `atan2` arity
      wall (`rej_math_arity3`), unknown-member row moved to `math.floor`
      (still unshipped in S2).
* [x] Sweep: `sweep_53_s2.py` — cumulative rows for S1+S2, **25/25 clean,
      0 diffs** (15 accepts + 10 reject wordings).

Verification snapshot: suite **184/184** · sweep 25/25 · fixed point
`54DC6F7D9A504704D8D8651EE29691CDEB9DCE64D6246B60319A7E8ACA08EB08` (Gen2 ≡
Gen3) · count_lines max 399 (`math_gen.vl`=36, `math_checks.vl`=140,
`codegen_expr.vl` 395).

## S3 — exponentials & logs (exp/log/log2) ✅ ([COMPLETED] in gaps.md 5.3)

Missing surface:

* [x] `math.exp(x)`, `math.log(x)`, `math.log2(x)` → `f64`; S1 contract
      reused. `log10` deliberately NOT shipped (not on the gaps list — it
      rides the closed-set wording, which grew to the 12-function list in
      all copies: stage-1 `_math_expect`, stage-2 `check_math_call`,
      battery row, sweep row).
* [x] Pins: `exp(0.0)=1.000000` (exact IEEE), `exp(1.0)=2.718282`,
      `log(1.0)=0.000000` (exact), `log2(8.0)=3.000000` (exact);
      `exp(math.log(5.0))` round-trip at `%.2f` = `5.00`; int widening
      (`log2(i64 1024)=10.000000`, `exp(0)=1.000000`; plain int literal
      `log2(1024)=10.000000`); f32 widening (`log(f32 1.0)`);
      `shelf[f64]` mix element (`log2(8.0)` → `3.00`).
      Domain residuals (log(0)=-Inf, log(neg)=NaN, exp overflow=Inf) stay
      libc-defined on identical C — documented, unpinned.
* [x] Batteries: `test_accepts_explog_family` (10-row pinned fixture);
      sweep `sweep_53_s3.py` — cumulative S1+S2 rows re-swept + 8 accepts +
      5 reject wordings (incl. `s3_rej_log2_zero` arity wall and the grown
      unknown-member wording), **34/34 clean, 0 diffs**.

Verification snapshot: suite **185/185** · sweep 34/34 · fixed point
`8ED2798FA05D6554710754A4DEA0B5931483AD1E38937F0D800A55A5FD2EE67B` (Gen2 ≡
Gen3) · count_lines max 399 (`math_checks.vl`=144, `math_gen.vl`=41,
`codegen_expr.vl` 395 — ceiling-file compression from S2 still holds).

S4 batteries: `test_accepts_utility_family` (22-row pinned fixture —
floor/ceil/round pins incl. `round(-2.5) = -3.000000` half-away-from-zero;
abs through f64/i32/i64/u64-identity/usize/i8/f32; min/max same-spell via
bindings, width-mix → i64, float lanes, int+float widen; clamp rows;
int-arg lerp; chained `max(min(1.0, 2.0), 1.5)`) + `test_rejects_utility_family`
(abs/min got-walls, clamp/lerp arity walls); sweep `sweep_53_s4.py` —
cumulative S1+S2+S3 rows re-swept + 10 accepts + 5 reject wordings (incl.
the 3-ary walls and the 20-function unknown-member row moved onto `log10`),
**47/47 clean, 0 diffs**.

S4 verification snapshot: suite **187/187** · sweep 47/47 · fixed point
`634B77C5CFBCDABD1C8824011BC872E77644A6CB8405D1C813798A143AFB37B2` (Gen2 ≡
Gen3) · count_lines max 399 (`math_checks.vl`=188, `math_gen.vl`=147,
`type_checker.vl` held at 396 — the call branch COLLAPSED to one line,
`codegen_expr.vl` still 395).

## S4 — utility family (abs/floor/ceil/round/min/max/clamp/lerp)

Missing surface:

* [x] `math.floor(x)`, `math.ceil(x)`, `math.round(x)` → `f64` (C floor/ceil/
      round doubles; .5 rounding behaviour is libc C99 `round`, half away from
      zero — pinned modulo libc equality between stages only).
* [x] `math.abs(x)` — TYPE-DISPATCHED: `f32`/`f64` → `fabs` → pinned `f64`
      result (single-eval `fabs((double)(...))`); int widths return the SAME
      int type back. Shipped refinement vs the pre-S4 note (see gaps 5.3 S4):
      ALL signed spells (i8/i16/i32/i64/isize) ride ONE uniform
      `(({T})llabs((long long)(...)))` shape (labs would hard-depend on the
      target's `long` width for i64 — llabs keeps the emitted C portable);
      unsigned spells (u8/u16/u32/u64/usize) are the IDENTITY `({x})` (abs of
      a non-negative value — llabs on u64 past the sign bit is meaningless);
      bool/string reject.
* [x] `math.min(a, b)` / `math.max(a, b)` — 2-ary: any float arg →
      `fmin/fmax((double)(a), (double)(b))` → `f64` (each arg emitted once);
      both ints SAME spell → `(({T})((a) OP (b) ? (a) : (b)))` — same type
      back; mixed int widths (incl. u64 mixes) → pre-cast both sides
      `(i64)(...)` then ternary → `i64` (signedness-safe; u64 > i64 range
      documented residual). The ternary shapes re-evaluate each argument
      twice (documented residual — libm has no int min/max; battery pins
      literal/local spellings only).
* [x] `math.clamp(v, lo, hi)` → f64, canonical order:
      `fmin(fmax((double)(v), (double)(lo)), (double)(hi))` — inner fmax
      clamps the floor, outer fmin the ceiling; each argument emitted
      exactly once (no double-eval residual for clamp).
* [x] `math.lerp(a, b, t)` → f64, emitted as
      `(((double)(a)) + (((double)(b)) - ((double)(a))) * ((double)(t)))` —
      a appears twice (documented double-eval residual; battery pins
      literal/local spellings).
* [x] Batteries + sweep rows appended (S4 accept + 4 new walls; closed-set
      row moved off `floor` (shipped) onto `log10` + 20-function wording).

## S5 — example 33 + chapter close

Missing surface:

* [ ] `examples/33_math_library.vl` (example-30 house style: header comment,
      one deterministic program covering constants, sqrt/pow/cbrt, trig,
      exp/log, utility family; every interpolation binds locals first —
      gaps 6.7).
* [ ] `tests/test_math_library.py` gains the example-33 parity row
      (`EXAMPLE33_LINES`, byte-identical both stages).
* [ ] `gaps.md` 5.3 → `[COMPLETED] ✅` with the Final-form slice entry
      (Former Defect → Fix → Residual → Verification).
* [ ] Sweep finale (full-row recount) + chain fixed point + count_lines
      max ≤ 399 verified in the close commit.
* [ ] docs: array.md untouched (5.2 is closed); VELO.md stays untracked.

## Verification ladder (every slice)

1. `python -m pytest tests -q` — full suite green.
2. Dual-stage sweep script — 0 diffs on accept rows; identical stderr on
   rejects.
3. `python velo.py build src/main.vl -o bin/velo_gen1.exe` → Gen2 → Gen3 +
   `bin/velo.exe`; `emit-c` SHA-256 Gen2 ≡ Gen3 (re-verified from fresh Gen1
   counts as the fixed point for the slice).
4. `python scripts/count_lines.py` — max ≤ 399 (math logic lives in the NEW
   `math_checks.vl` file, clipped under the ceiling from birth).
