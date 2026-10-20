# AGENTS.md — Project Conventions for AI Agents

## Golden Rule: Ship a Feature as a Complete Unit

After **fully completing** a feature or bug fix — code done and tests passing — always do all three steps:

### 1. Verify
- Run the test suite: `python -m pytest tests -q`
- If compiler source (`src/**/*.vl`) changed, rebuild the bootstrap chain (path `C:\msys64\ucrt64\bin` in PATH for GCC):
  ```bash
  python velo.py  build src/main.vl -o bin/velo_gen1.exe
  bin/velo_gen1.exe build src/main.vl -o bin/velo_gen2.exe
  bin/velo_gen2.exe build src/main.vl -o bin/velo_gen3.exe
  cp bin/velo_gen3.exe bin/velo.exe   # canonical standalone compiler
  ```
- If compiler source changed, re-verify determinism: SHA-256 of `emit-c src/main.vl` output must be identical between Gen2 and Gen3.
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
- The Python compiler (`velo/`) and the self-hosted compiler (`src/`) must stay **behaviorally identical**; any language change lands in both, with tests, in the same commit.
- Do not stage unrelated in-progress files (`VELO.md`, `editors/`, `real-world-prob-test/me/` are deliberately untracked owner material).
