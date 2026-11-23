---
name: Feature Request / Language Proposal
about: Suggest an idea, language syntax proposal, or standard library enhancement for Velo
title: "[PROPOSAL] "
labels: enhancement
assignees: ''
---

## Problem & Motivation
<!-- What limitation, friction point, or missing capability are you trying to address?
Is this related to an open item or invariant in `gaps.md` or a real-world use case? -->

## Proposed Solution / Syntax Design
<!-- Describe your proposal and how it fits Velo's language philosophy (game-biased, zero-GC, 4-character keywords, explicit memory allocation, deterministic C99 emit). -->

```velo
// Provide illustrative Velo code snippets showing how the proposed feature is used
```

## Semantics & Runtime Model
- **Memory Tier:** Does this use Zone arena allocation, heap shelf allocation, custom arena, or virtual pages?
- **Resource Ownership:** How are resources cleaned up? (e.g. LIFO `defer`, explicit release)
- **Zero-GC Invariant:** Does this proposal guarantee zero garbage collection and predictable cache-line latency?
- **Platform Scope:** Is this cross-platform or platform-specific? (If stdlib, does it follow `docs/STDLIB_ARCHITECTURE.md` facade + `_<plat>` siblings?)

## Alternatives Considered & Tradeoffs
<!-- What other designs, syntax variations, or workarounds were considered? Why is this approach superior? What are the tradeoffs? -->

## Implementation Complexity & Compiler Invariants
- Does this require syntax/lexer changes (`src/frontend/`)?
- Does this affect semantic analysis or type checking (`src/analysis/`)?
- How will it be emitted in C99 (`src/backend/`)?
- Can the implementation adhere to the 400-line modular limit per source file (`python scripts/count_lines.py`)?
