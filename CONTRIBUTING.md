# Contributing to Velo

Thanks for considering a contribution. This document is deliberately short and
specific, because Velo has an unusual build model and a few non-negotiable
gates. Read the whole thing before your first pull request.

By contributing you agree that your contribution is dual-licensed under
`MIT OR Apache-2.0`, as described in [`README.md`](README.md#license).

---

## 1. What Velo is, and what it is not

Velo is a systems language that compiles to C99. The compiler is self-hosted:
its source is Velo (`src/**/*.vl`), and `bootstrap.c` is a generated C snapshot
of that source, so a C compiler is all you need to build Velo from scratch.

Please read the "Known limitations" section of [`CHANGELOG.md`](CHANGELOG.md)
and the project decision and stability guidelines in [`GOVERNANCE.md`](GOVERNANCE.md)
before proposing a feature. The toolchain is **pre-publication**: the standard
library does not yet work outside Windows, and several subsystems are
deliberately not built yet. The authoritative, itemized list with severity and
fix plans is [`gaps.md`](gaps.md).

Not in scope (see `gaps.md` section 7): garbage collection, a lifetime borrow
checker, a macro system, non-C backends, and hosted package accounts.

---

## 2. Prerequisites

| Requirement | Notes |
| :--- | :--- |
| A C99 compiler | `gcc` (MSYS2 UCRT64 on Windows), `clang`, or MSVC `cl` |
| Python 3.11+ | Only for the test suite and the release scripts, not for the compiler itself |
| `pytest` | `pip install pytest` |

Nothing else. The compiler has no runtime dependency beyond libc, and the
standard library is pure Velo.

---

## 3. Build

```bash
# Step 1: bootstrap from the C snapshot (produces bin/velo)
scripts/bootstrap.bat --full      # Windows
bash scripts/bootstrap.sh --full  # Linux / macOS
```

`--full` rebuilds the whole chain: `bootstrap.c` -> Gen1 -> Gen2 -> Gen3, and
verifies Gen2 and Gen3 are byte-identical. If you have not touched compiler
source you only need `bin/velo`, so run the script with no argument on Windows
(`scripts/bootstrap.bat`) or `--quick` on Linux/macOS
(`bash scripts/bootstrap.sh --quick`); the shell script runs the full chain by
default, the batch script does not.

Manual equivalent, when you are iterating on compiler source:

```bash
bin/velo.exe build src/main.vl -o bin/velo_gen2.exe
bin/velo_gen2.exe build src/main.vl -o bin/velo_gen3.exe
cp bin/velo_gen3.exe bin/velo.exe
python scripts/check_determinism.py
bin/velo.exe emit-c src/main.vl -o bootstrap.c
```

---

## 4. The five gates

A change is not done until all five pass. CI enforces them; a reviewer will ask.

### 4.1 Tests

```bash
python -m pytest tests -q
```

The full suite takes roughly 15 minutes because it compiles and runs native
programs. Compiler-source changes additionally require:

```bash
python -m pytest tests/test_bootstrap_snapshot.py -q
```

which asserts that `bootstrap.c` is byte-identical to
`velo emit-c src/main.vl -o <fresh file>`. Compare **file output**, not stdout:
stdout is a different code path and legitimately differs.

### 4.2 Determinism

```bash
python scripts/check_determinism.py
```

Gen2 and Gen3 must produce identical output. A change that makes the bootstrap
chain non-deterministic is a bug even if every test passes.

### 4.3 Clean tree

```bash
python scripts/check_clean_tree.py -- python -m pytest tests -q
```

The suite must not create or modify files outside its own fixtures. Use pytest
`tmp_path`; never write to a relative `scratch/` directory.

### 4.4 File size ceiling

```bash
python scripts/count_lines.py
```

No file under `src/**/*.vl` may exceed 400 lines. Prefer a new focused module
over growing a file that is near the ceiling. (Phase 80 of `gaps.md` revisits
whether this ceiling should be a design driver; until then, it is enforced.)

### 4.5 No byte-order marks

Never write a `.vl` file with a UTF-8 BOM. The lexer rejects `U+FEFF` with
`[Velo Error] Unexpected character '\ufeff'`. On PowerShell:

```powershell
[System.IO.File]::WriteAllText($path, $text, (New-Object System.Text.UTF8Encoding($false)))
```

---

## 5. Test conventions

- Prefer a **red baseline first**: commit a failing test that pins the defect,
  then the fix. Every phase in `gaps.md` was done this way, and it is the
  reason the suite actually covers the bugs that existed.
- Assert **behaviour**, not generated C text, whenever a runtime assertion is
  possible. A test that greps emitted C pins a codegen detail that may
  legitimately change. Where emitted-C assertions are unavoidable, say so in a
  comment and explain what would break silently without it.
- Pass an explicit `encoding="utf-8"` to every subprocess call that captures
  text. Relying on the platform default locale codec has already caused one
  Windows-only CI failure.
- Give each test its own filesystem fixture under `tmp_path`. Tests must not
  depend on a directory an earlier run left behind.
- Do not run two pytest sessions concurrently: `velo check` writes
  `velo_check_capture.tmp` in the working directory (Phase 76.4 fixes this).

---

## 6. Documentation is part of the change

`gaps.md` is a living architectural audit, not a scratchpad. When you close an
item, mark it `COMPLETED` with the four-part pattern:

> Former defect -> fix applied -> residual limitation (if any) -> verification

New limitations you discover get an honest entry in the same file. Hiding a
limitation is treated as a defect in review, because it feeds the roadmap and
the release criteria.

Documentation updates that land with a change:

| Change | Also update |
| :--- | :--- |
| Language semantics | `docs/SPECIFICATION.md`, and `docs/STEP2_SPECIFICATION.md` for compiler internals. Append new numbered sections; never renumber existing ones — tests pin them. |
| Standard library surface | The module's doc comments, which `velo doc` extracts |
| Fixed defect | `gaps.md` phase body and its row in the backlog summary table |
| User-visible behaviour | `CHANGELOG.md` under `[Unreleased]` |
| Version | `VERSION` and `src/common/version.vl` in the same commit |

---

## 7. Commits

One conventional commit per unit of work, containing source, tests, and the
`gaps.md` update together. Do not split a fix from its test.

```
feat(scope): summary
fix(scope): summary
test(scope): summary
docs(scope): summary
refactor(scope): summary
perf(scope): summary
ci(scope): summary
chore(scope): summary
```

The body should state the defect, its cause, the fix, and how it was verified.
Commit `417e55d` is a good reference for the expected level of detail.

Do not commit:

- `.exe`, `.o`, `.obj` files, or `.velo_cache/` (gitignored; rebuilt locally)
- UTF-8 BOMs
- Secrets, credentials, or absolute paths from your machine in source

---

## 8. Pull request checklist

- [ ] `python -m pytest tests -q` passes
- [ ] `python scripts/check_determinism.py` reports `SHA-256 MATCH`
- [ ] `python scripts/count_lines.py` reports no file over 400 lines
- [ ] `python scripts/check_clean_tree.py -- python -m pytest tests -q` passes
- [ ] `bootstrap.c` regenerated if compiler source changed
- [ ] New behaviour has a test; new defects started with a failing test
- [ ] `gaps.md` updated; any new limitation recorded honestly
- [ ] `CHANGELOG.md` updated under `[Unreleased]` for user-visible changes
- [ ] No BOMs, no build products, no unrelated files staged

---

## 9. Reporting a bug

Include:

1. The output of `velo version`.
2. The smallest `.vl` file that reproduces it.
3. The exact command, and the full output including exit code.
4. Your OS and C compiler version.

A crash (a signal or an OS exception code such as `3221225725` or
`0xC00000FD`) is a bug of the highest severity in a compiler, even if the input
is malformed. See Phase 82 of `gaps.md`.

Security issues must **not** go through the public issue tracker. Follow
[`SECURITY.md`](SECURITY.md).
