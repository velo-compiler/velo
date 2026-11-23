# Historical Artifact — Velo Stage 1 Bootstrap Compiler

> **Status: ARCHIVED / RETIRED (Phase 80.5)**  
> **Canonical Compiler:** [`src/`](../src/)  
> **Bootstrap Entry Point:** [`bootstrap.c`](../bootstrap.c) / [`scripts/bootstrap.bat`](../scripts/bootstrap.bat)

## Overview

This directory (`velo/`) and the root driver [`velo.py`](../velo.py) contain the original Stage 1 bootstrap prototype of the Velo programming language, implemented in Python 3.

Stage 1 was built to provide the initial lexer, parser, type inference, and C emitter needed to compile the first generation of the self-hosted Velo compiler (`src/main.vl`).

## Retirement & Invariants

Following the completion of self-hosting and Milestone 2.3+:
1. **No Active Development**: Stage 1 is frozen and retired. No new language features, syntax additions, or bug fixes are backported to this Python implementation.
2. **Exempt from Parity**: Parity between Python and self-hosted Velo is obsolete. Contributors and AI agents must implement features strictly in `src/**/*.vl`.
3. **Historical Testing**: Tests that reference `velo.py` are preserved for historical regression tracking, but new tests and CI gating must target `bin/velo.exe` (`src/`).
