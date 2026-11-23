# AGENTS.md — Project Conventions for AI Agents

## Golden Rule: Ship a Feature as a Complete Unit

After **fully completing** a feature or bug fix — code done and tests passing — always do all three steps:

### 1. Verify
- Run the test suite: `python -m pytest tests -q`
- If compiler source (`src/**/*.vl`) changed, rebuild the bootstrap chain (path `C:\msys64\ucrt64\bin` in PATH for GCC):
  ```bash
  # Step 1: Bootstrap from C snapshot or standalone script
  scripts\bootstrap.bat        # compiles bootstrap.c into bin/velo.exe
  # Step 2: Re-generate and verify self-hosted compiler chain
  bin\velo.exe build src/main.vl -o bin/velo_gen2.exe
  bin\velo_gen2.exe build src/main.vl -o bin/velo_gen3.exe
  cp bin/velo_gen3.exe bin/velo.exe   # canonical standalone compiler
  # Step 3: Refresh bootstrap.c snapshot
  bin\velo.exe emit-c src/main.vl -o bootstrap.c
  ```
- If compiler source changed, re-verify determinism: SHA-256 of `emit-c src/main.vl` output must be identical between Gen2 and Gen3, and `bootstrap.c` must match `emit-c src/main.vl`.
- Keep code standards: no compiler source file over 400 lines (`python scripts/count_lines.py`).

### 2. Update `gaps.md`
`gaps.md` is the project's **living architectural audit** and ships with every change:
- Completed items get marked `[COMPLETED] ✅` with this pattern: *Former Defect → Fix Applied → Residual Limitation (if any) → Verification* (see §6.6 for the reference example).
- New limitations or gaps the change revealed get honest entries — never hide them; they feed the roadmap.

### 3. Commit
- One conventional commit per unit of work, containing **code + tests + `gaps.md`**.
- Style: `feat|fix|docs|test(scope): summary` with a short body explaining defect, cause, fix, and verification (see commit `c8f67af` for the reference format).

## Guardrails
- Git history rules everything: no work is "done" until it is committed and documented.
- `*.exe` and `.velo_cache/` are gitignored — only source is committed; toolchain binaries (`bin/velo_gen*.exe`, `bin/velo.exe`) are rebuilt locally by whoever needs them.
- Never write `.vl` files with a UTF-8 BOM — the lexer rejects the `\ufeff` character (`[Velo Error] Unexpected character '\ufeff'`).
- The Python compiler (`velo/` and `velo.py`) is an **untested historical artifact** (Stage 1 bootstrap prototype, retired per Task 80.5). The self-hosted compiler (`src/`) and `bootstrap.c` are the canonical compiler source and bootstrap entry point. Language parity between Python and Velo is permanently retired and forbidden; all compiler modifications and new features are implemented strictly in `src/**/*.vl` without dual-implementation tax.
- Do not stage unrelated in-progress files (`VELO.md`, `editors/`, `real-world-prob-test/me/` are deliberately untracked owner material).
