# CI Status

**No CI run has executed yet.** This repository has no git remote, so GitHub
Actions has never been triggered, and no job below has a run to link.

This file exists so that "CI is green" becomes a checkable claim instead of a
sentence in a README. `tests/test_ci_evidence.py` parses the table below and
fails when a job declared in `.github/workflows/ci.yml` has no entry, when an
entry is not an Actions run URL, or when the cited commit is not an ancestor of
`HEAD`. Until every row is filled in from a real run, that test fails — which is
the accurate state of the project, not a formality to be silenced by editing the
document.

## Jobs declared in the workflow

| Job | Latest green run | Commit | Date |
| :--- | :--- | :--- | :--- |
| `linux` | not yet — no remote | — | — |
| `macos` | not yet — no remote | — | — |
| `windows-gcc` | not yet — no remote | — | — |
| `windows-msvc` | not yet — no remote | — | — |
| `clean-checkout` | not yet — no remote | — | — |
| `sanitizer` | not yet — no remote | — | — |

## What is known without CI

These are verified on the maintainer host and recorded here so the gap between
"verified somewhere" and "verified in CI" stays visible:

| Check | Command | State |
| :--- | :--- | :--- |
| Full suite, Windows + MSYS2 gcc | `python -m pytest tests -q` | passes |
| Bootstrap fixed point | `python scripts/check_determinism.py` | `SHA-256 MATCH` |
| Snapshot freshness | `tests/test_bootstrap_snapshot.py` | byte-identical |
| Line ceiling | `python scripts/count_lines.py` | no file over 400 |
| Clean tree | `python scripts/check_clean_tree.py` | passes |

## Why the Linux and macOS jobs cannot pass yet

Not a configuration problem, and not fixable by editing this file:

1. `bootstrap.c` contains unguarded Win32 externs (`CreateProcessA`,
   `VirtualAlloc`, `SystemFunction036`, and others), so it cannot link against
   glibc or libSystem. Phase 70 tracks this.
2. Several standard-library modules are Win32-only: `std/fs/stat.vl`,
   `std/fs/ops.vl`, `std/fs/dir.vl`, `std/net/socket.vl` (Winsock), and
   `std/crypto/rand.vl` (`SystemFunction036`). Phase 70.
3. Until Phase 76.3, 62 test files appended `C:\msys64\ucrt64\bin` to `PATH` and
   99 hardcoded `bin/velo.exe`. That is now fixed; the compiler still is not.

## How to fill this table in

1. Push the repository to a remote and enable Actions.
2. Run the workflow on the commit you intend to release.
3. For each job, copy the run URL and the commit SHA into the row above.
4. Run `python -m pytest tests/test_ci_evidence.py -q` and confirm it passes.

A run that is green on a different commit than the one being released does not
count; the test enforces that by requiring ancestry, and the release script
enforces the same commit by refusing to package a dirty tree.
