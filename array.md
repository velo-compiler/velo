# array.md — 5.2 Dynamic Collections: complete build sheet

> Companion to `gaps.md` §5.2. Lists EVERYTHING still missing in the array
> (shelf) section, with the target contract for each remaining slice. Slices
> 1–3 are shipped (commits `7c442aa`, `a9c34e1`, `b04a9d2`); every remaining
> slice lands as one golden-rule unit: pin the final contract in gaps.md 5.2 →
> both compiler stages → parity suite → bootstrap chain rebuild + Gen2 ≡ Gen3
> emit-c SHA-256 fixed point → `scripts/count_lines.py` clean → one
> conventional commit with code + tests + `gaps.md` (this sheet kept in sync).

## Shipped so far (for reference)

* Slice 1 — shelf core: `shelf[...]` literal, `put`/`take`/`len`/`[i]` read-write, `loop v of xs`, homogeneous exact elements, mut doctrine, arena-backed growth. 150/150, fixed point `711BE6EB…`.
* Slice 2 — widening ladder + `shelf[dyn]` tagged boxes: int+float → f64, mixed → dyn, `as` unbox, raw-dyn gates. 155/155, fixed point `25FCFE58…`.
* Slice 3 — vector surface: `sorted()` / `insert(i, v)` / `remove_at(i)` (stash-copy by-value pop), six-member member list. 158/158, fixed point `B28FCDB9…`.

Current budget: `type_checker.vl` 399, `symbol_table.vl` 398, `stmt.vl` 398 —
ALL three are at the ceiling. Every new collection MUST land in its own
`src/analysis/*_checks.vl` + `src/backend/*_gen.vl` files wired via
`type_check_program.vl` / `codegen_expr.vl`; never grow the near-ceiling files.

---

## S4 — loop-index + `reversed()` (small)

Missing surface:

* [x] `loop v, i of xs { }` — two-binding OF-walk: value first, index second.
      Index is `usize` (same tier as `len`). Works for every element family
      (no comparators — supports dyn/bool/struct rows), works through the
      generic mono clone like the one-binding form does.
* [x] `xs.reversed()` — returns a NEW shelf, fresh arena backing, receiver
      untouched, legal on a `let` (mirrors `sorted()`'s copy-on-let doctrine).
      NO element-family restriction (no compares — any family incl. dyn,
      bool, struct, pointer rows; empty reverses to empty).
* [x] Unknown-shelf-member list grows to seven members on BOTH stages:
      `put, take, len, sorted, insert, remove_at, reversed are available`
      (property + call sites, byte-identical wording).
* [x] Decision pinned: copy `reversed()` (not in-place `reverse()`).

Runtime (`velo_runtime.h`):

* [x] `velo_shelf_reversed(const VeloShelf* s)` — one function for ALL
      element families (memmove/copy + swap pairs in place on the fresh copy).
      No per-width wrappers needed.

Tests:

* [x] Accept: `loop v, i of xs` prints values+indices for i32/strings/dyn
      battery; `reversed()` on ints/strings/dyn bag + receiver-untouched check.
* [x] Reject: third binding `loop of takes at most two bindings (value,
      then index)` (order swap is undetectable mechanically — the FIRST
      binding always gets the element, any two names are legal), reversed
      arity, unknown-member updates.

## S5 — `join(sep)` + the shared repr machinery (medium)

Missing surface:

* [x] `xs.join(sep)` → `string`. Separator must be a string (compile-reject
      otherwise). Legal on `let` (read-only). `len 0` → empty string.
* [x] Formatting MUST match io-interpolation print formatting exactly
      (pinned in a small table: i32 → `1`, i64 widths per printf ladder,
      f32/f64 → `0.50` style, bool → `true`/`false`, string pass-through
      verbatim). Elements are stringified per-family by the compiler.
* [x] Joinable families: all int widths, f32/f64, string, bool.
      Compile rejects (pinned wordings):
      - `shelf[dyn] join is not supported — cast elements first`
      - struct/pointer-row join (same closure of the reject).
      (Child `shelf[T]` rows also reject — join's family check catches them
      explicitly; sorted()'s pre-existing child-row hole left as-is.)
* [x] The per-family stringify acts become the SHARED repr machinery that
      §S6 map fatal wording reuses (`map key not found: <krepr>`).

Runtime:

* [x] `velo_shelf_join_<token>(const VeloShelf*, const char* sep)` →
      `const char*` (arena): one wrapper per joinable family, snprintf-based
      (stdio already linked; no new deps).

Tests:

* [x] Accept: ints (multi-width), floats (`0.50` style), strings (passthrough,
      no quotes), bools; custom separators incl. `", "` and `""`; empty shelf.
* [x] Reject: dyn bag join, struct-row join, non-string separator.
* [x] Parity: join output byte-identical to the equivalent interpolation
      print of each element (both stages).

## S6 — `Map[K, V]` core (largest slice)

Missing surface:

* [x] `Map[K, V]` in all type positions (annotations, params, returns,
      struct fields, `@Map[...]` pointers), literal `map[1: "a", 2: "b"]`,
      empty map needs an annotation (shelf precedent).
      First TWO-bracket generic type in the parser — generalize the shelf
      type path, do not fork it.
* [x] Key families (PINNED): all int widths, bool, string.
      String keys hash CONTENT (characters), not the pointer — differs
      from shelf strings and must be documented explicitly.
      Floats/struct/pointer/dyn keys reject at compile (NaN is unordered —
      the pinned reason).
* [x] Value family: ANY shelf-legal element — memcpy by-value semantics,
      including `shelf[dyn]` boxes and child shelves/child maps
      (snapshot-row doctrine applies).
* [x] Members: `m.put(k, v)` (upsert, mut-root, put-family element wording),
      `m.get(k)` → V fatal-on-miss, `m[k]` read (same as get),
      `m[k] = v` upsert (same bounds spirit as shelf writes),
      `m.has(k)` → bool, `m.len`.
* [x] Fatal wording (runtime source of truth, repr from §S5):
      `Velo Fatal Error: map key not found: <krepr>!`
* [x] Cross-call equality string-compared on BOTH type params
      (`Map[i32, string]` vs `Map[i64, string]` differ — shelf precedent).

Runtime:

* [x] `VeloMap` — open addressing, FNV-1a hash, power-of-two capacity,
      ×2 rehash at 0.75 load; *(tombstones deferred to S7 — S6 has no
      delete surface; the layout reserves growth shape so S7's `take`
      adds tombstate without a migration, per the pin in gaps.md)*.
* [x] Table storage in the ACTIVE arena (regenerate-on-rehash churn —
      exactly the shelf growth doctrine: no free inside a zone, no leak
      divergence from the allocator architecture).
* [x] Deterministic probe order ⇒ deterministic hash-order iteration;
      NOT insertion-ordered — pinned and documented.

Files (budget strategy):

* [x] NEW `src/analysis/map_checks.vl` (375) + NEW `src/backend/map_gen.vl`
      (276); wiring through `type_check_program.vl` (Pass-1.5 pin twin)
      AND `type_checker.vl` infer dispatches (the checker placements must
      mirror stage-1's `_map_expect` tier to keep reject order identical —
      in-place one-line dispatches, all files ≤399).

Tests:

* [x] Accept: literal + annotation maps over int/string keys, upsert
      overwrites, has/get/len battery, dyn values in V.
* [x] Reject: `Map[Point, i32]` / `Map[f32, i32]` key families, key-type
      mismatch on put/get cross-call, K literal/annotation mismatch wording.
* [x] Fatals: missing-key reprs (string key reprs vs int reprs), exit 1.

## S7 — Map advanced (medium)

Missing surface:

* [ ] `m.get_or(k, default)` → V (absence handled without an option type).
* [ ] `m.take(k)` → V removed by value (fatal on miss, same wording family).
* [ ] `loop k of m { }` — iterates KEYS (hash order, documented ordering
      caveat vs shelf iteration).
* [ ] V edges: `V = dyn` boxed put/get-or flow, V = child `Map[…]`/`shelf[…]`
      value-copied headers.

Tests:

* [ ] get_or default both taken and not-taken; take removes (len drops,
      second take fatals with repr); loop over map keys battery; empty-map
      loop is a no-op; nested map values mutate through their own copy only.

## S8 — dyn engine: auto-unbox operators + U64 tag (medium)

Missing surface:

* [ ] Raw dyn binary operators (currently ALL compile-rejected):
      `dyn ⊙ dyn`, `dyn ⊙ concrete`, `concrete ⊙ dyn` → result RE-BOXED as
      dyn. Numeric ladder (same spirit as slice 2): int family → I64 math
      (a concrete `i32` widens to i64), any float → F64.
* [ ] Same-family dyn compares → `bool`: int/int, float/float, string strcmp,
      bool/bool; mixed-family compares and `string + string` concat STAY
      rejected (one pinned wording; concat remains `str.concat`).
* [ ] `VELO_DYN_U64` tag — u64 boxes above 2^63 stay intact; `as u64`/`as i64`
      off the U64 box. Closes slice-2 residual (3). Fatal wording survives
      (families, not tag names, are what `velo_dyn_expect` prints).

Still rejected (pinned forever for this section):

* [ ] Struct-in-dyn BY VALUE (union would grow to the struct max size and
      slow every box read — `@T` pointers cover it; documented).
* [ ] Raw-dyn io printing (stays: one cast line is the idiomatic bar).

Tests:

* [ ] Accept: `bag[0] + 2`, `(bag[1] * bag[2]) as f64` chains, dyn-dyn and
      dyn-concrete and concrete-dyn both sides, mixed ladder to f64, U64
      roundtrip `shelf[18446744073709551615]` → `as u64` exact value.
* [ ] Reject: `dyn + string` (wording), `string + string`, mixed-family
      compare `<` across int-vs-string, raw-dyn io print regression (stays).
* [ ] Fatals: U64-tag unbox mismatch wording unchanged shape.

## S9 — `ring[T]` + `bitset` (medium)

Ring — missing surface:

* [ ] `ring[T]` UNBOUNDED (grows with capacity doubling, power-of-two
      masking, arena-backed): `r.put(v)` enqueue-back, `r.pop()`
      dequeue-front (take-style fatal: `Velo Fatal Error: ring pop from an
      empty ring!`), `r.peek()` (fatal on empty), `r.len`, `loop v of r`.
      Rationale pinned: the differentiator vs shelf is O(1) FRONT removal;
      bounded capacity can layer on later.

Bitset — missing surface:

* [ ] `bitset` — arena-backed word array (grow-on-set like shelf):
      `b.set(i)`, `b.clear(i)`, `b.toggle(i)`, `b.has(i)` → bool,
      `b.count()` → usize, `b.first_unset()` (ECS slug allocation helper).
* [ ] Pair ops logical in-place: `b.and(o)`, `b.or_with(o)`, `b.xor_with(o)`,
      `b.flip()` (mut-root doctrine for all four; Velo has no operator
      overloading — methods are the pinned surface).
* [ ] Literal `bitset[1, 9, 100]` (bits set), annotation `bitset` (empty).

Files:

* [ ] Runtime `VeloRing` / `VeloBitset`; NEW checks/gen files
      (`ring_checks.vl`, `bitset_checks.vl` or a shared `misc_checks.vl`
      depending on budget).

Tests:

* [ ] Ring FIFO order across the wrap boundary battery; ring fatals
      (pop/peek empty); bitset set/clear/toggle/has/count; pair ops vs
      hand-computed words; literal sizes; OOB on has/set is loud fatal.

## S10 — memory model: `heap shelf` + shared rows (large)

Missing surface:

* [ ] `heap shelf[T]` type spelling + `heap shelf[...]` literal prefix.
      Growth allocates via `velo_heap_alloc` so the shelf OUTLIVES its
      zone: returnable from acts, storable in globals/parents outside the
      Enclosing `zone { }`. Zone-backed shelves are the default; heap
      shelves pay persistent-block pricing (documented).
* [ ] `VeloShelf` grows a source field (`NULL` = active arena; zero-init =
      today's behavior, ALL helpers honor it via one allocator selector —
      layout change pinned in the runtime header).
* [ ] Shared rows closure (slice-1 residual (1) promise):
      `@shelf[T]` as a child element — `grid[i]` yields the pointer,
      `grid[i].put(v)` and `grid[i][j] = v` mutate the SHARED row; the
      row-copy guard only trips for value rows (non-pointer elements).
* [ ] `as @shelf[T]` unbox RE-OPENED (slice-2 reject retires): the box
      holds a real pointer the user owns; the dangle wording is replaced
      with a documented trust doctrine + pointer to slice-2 residual (2)
      (`@T{...}` inline temporaries remain the one footgun — heap shelf is
      the safe way to OWN shared rows).

Tests:

* [ ] Heap shelf returned from an act, kept past a `zone { }` exit, growth
      inside a zone leaks nothing into the zone ledger; shared-row battery
      (mutate through grid[i], sibling index sees it); `as @shelf` roundtrip
      keeps identity; copy-row `as shelf` behavior unchanged.

## S11 — section sweep: retitles 5.2 to ✅

Missing surface:

* [ ] `str.split` → `shelf[string]` HARD SWAP (breaking change): both stages,
      every call site, the example, and §2 docs updated in the same commit;
      the `@string` token-array spelling retires with a changelog note.
      Rationale: one owning-shelf return shape instead of the two idioms.
* [ ] Contextual `shelf`: usable as an identifier when NOT immediately
      followed by `[` — `shelf[` stays permanently keyword in expression
      position (the `let x = shelf[i]` literal-vs-index ambiguity is
      genuinely unresolvable, which is why slice 1 reserved the word; this
      resolves what is resolvable). Parser rule identical on both stages.
* [ ] `--unsafe-shelf-index` CLI knob (BOTH stages): lowers `xs[i]` to the
      unguarded `((T*)data)[i]` read. Silent-OOB warning documented; NOT
      exercised by the default suite (flag-gated).
* [ ] MSVC: MOVED OUT of 5.2 into a standalone infra gap — statement-
      expression-free lowering is a whole-emitter rewrite; GCC-only already
      matches the `__thread` precedent, and no collection feature depends
      on it. Honest carve-out, recorded in gaps.md.

Tests:

* [ ] split battery (existing split tests migrated to shelf[string]),
      contextuality accept (vars named `shelf`) + reject (`xs` named shelf
      still literal/index collision rules), unsafe flag compiles+runs with
      an intentionally-OOB program (flag-gated, not in default suite).

---

## End-state checks

* [ ] Suite target ~185–200 parity tests; every fatal pinned in the runtime
      header; every reject wording byte-identical across stages.
* [ ] `examples/` gains one example per milestone type (shelf/mixed/sorted
      plate → map/ring/bitset when they land).
* [ ] gaps.md 5.2 heading retitled: `slices 1..11 — full collections section ✅`.
* [ ] This sheet updated (checkboxes ticked) in the same commit as its slice.
