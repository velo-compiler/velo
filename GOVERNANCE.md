# Velo Project Governance

<!-- SPDX-License-Identifier: MIT OR Apache-2.0 -->

This document formalizes the decision-making model, breaking change approval process, stability guarantees for the 1.0 release, and deprecation policy for the **Velo programming language**.

---

## 1. Decision-Making Model ("Who Decides")

The Velo project operates under a transparent, consensus-seeking technical maintainer model designed to preserve language coherence, hardware-grade performance, and long-term architectural stability.

### 1.1 Project Roles

| Role | Responsibilities | Scope of Authority |
| :--- | :--- | :--- |
| **Project Lead & Core Maintainers** | Overall architectural vision, language design, specification integrity, breaking change approval, release stewardship, and arbitration in `gaps.md`. | Final decision authority across the compiler, standard library, toolchain, and repository governance. |
| **Subsystem Stewards** | Technical oversight and code review within specific functional domains: Compiler Frontend (`src/frontend`), Semantic Analysis (`src/analysis`), Backend & C99 Codegen (`src/backend`), Standard Library (`std/`), Tooling & LSP (`src/lsp`, `editors/vscode`), and Packaging (`src/backend/pkg_*`). | Authoritative review for subsystem pull requests; recommend approval or rejection of domain-specific proposals. |
| **Contributors & Community** | Feature proposals, bug reports, implementations, documentation, and benchmark verification. | Submit RFCs via `.github/ISSUE_TEMPLATE/` and pull requests compliant with the Phase 45-69 Task Execution Contract. |

### 1.2 Decision Process

1. **RFC & Public Discussion:** Technical proposals, language alterations, and architectural adjustments begin with an RFC issue using [`.github/ISSUE_TEMPLATE/feature.md`](.github/ISSUE_TEMPLATE/feature.md) or a discussion topic.
2. **Consensus-Seeking:** Subsystem Stewards and Core Maintainers review the proposal against Velo's core invariants:
   - **Zero-GC:** Predictable cache-friendly execution without runtime garbage collection pauses.
   - **Deterministic C99 Emit:** Byte-identical compilation across rebuild cycles.
   - **Explicit Memory Tiers:** Zone arena, heap shelf, custom arena, or virtual page management.
   - **Modular Code Budget:** Strict enforcement of the $\le 400$ lines ceiling per compiler source file (`python scripts/count_lines.py`).
3. **Consensus & Maintainer Approval:** If consensus is achieved among stewards, the change proceeds to implementation. If consensus cannot be reached, the Project Lead and Core Maintainers arbitrate based on alignment with the project's foundational goals and recorded limitations in `gaps.md`.

---

## 2. Breaking Change Approval Process

A breaking change is any modification that could invalidate previously compiling Velo source code, alter runtime semantics unexpectedly, or disrupt external tooling.

### 2.1 What Constitutes a Breaking Change

- Any addition, modification, or removal of language keywords, grammar productions, or syntax in `docs/SPECIFICATION.md`.
- Any modification to semantic analysis or type checking rules that causes previously valid `.vl` source code to fail `velo check`.
- Any backward-incompatible alteration to the standard library public API contract (`std.*`), calling conventions, or `sys.*` runtime intrinsic boundaries (`docs/STDLIB_ARCHITECTURE.md`).
- Any backward-incompatible alteration to compiler CLI flags, diagnostic formats, or package manifest schemas (`velo.pkg`).

### 2.2 Approval Pipeline for Breaking Changes

All breaking changes must strictly follow a 5-stage pipeline before landing on the default branch:

```
[1. Proposal RFC] ──> [2. Invariant Review] ──> [3. Two-Maintainer Sign-Off] ──> [4. Deprecation Notice] ──> [5. Release Landing]
```

1. **Stage 1 (RFC & Motivation):** The proposer opens an RFC issue documenting:
   - Exact motivation and the deficiency or defect being addressed.
   - Precise syntax and semantic delta with before/after Velo code examples.
   - An impact analysis quantifying codebases affected (including `examples/`, `games/`, `apps/`, and tests).
   - Migration guide describing how existing code will be updated.
2. **Stage 2 (Invariant & Architecture Review):** The proposal is evaluated to guarantee it does not violate zero-GC, determinism, or platform portability invariants.
3. **Stage 3 (Two-Maintainer Sign-Off):** Approval requires written affirmative consensus from **at least two Core Maintainers** (or one Core Maintainer and the relevant Subsystem Steward).
4. **Stage 4 (Deprecation Grace Period):** If the change removes or modifies existing syntax/APIs, it must enter the Deprecation Cycle (Section 4) before physical deletion.
5. **Stage 5 (Audit Trail & Release):** The change must ship with an update to `gaps.md` (recording Former Defect, Fix Applied, Residual Limitation, and Verification), migration notes in `CHANGELOG.md`, and an atomic conventional commit.

---

## 3. What "1.0" Means

Velo is currently pre-publication and in active development (`2.0.0-pre` designates the self-hosted Stage 2 compiler baseline). The release of **Velo 1.0 General Availability (GA)** represents a binding long-term stability and compatibility commitment to developers and production users.

### 3.1 The 1.0 Stability Guarantees

Upon releasing version 1.0.0, the Velo project commits to:

1. **Language Specification Freeze:** The syntax, grammar, keywords, and core semantics codified in `docs/SPECIFICATION.md` (`act`, `data`, `kind`, `aka`, `zone`, `defer`, `loop`, `on`, `pact`, `view`, `unsafe`) are frozen. No backward-incompatible language changes will occur within the 1.x major release lifecycle.
2. **Backward Compatibility Promise:** Any valid Velo program that compiles under Velo 1.0.0 will continue to compile and produce semantically identical runtime behavior on any subsequent 1.x release (e.g., 1.1, 1.2, 1.10).
3. **Cross-Platform Standard Library Tier 1:** The platform-model facade contract (`std.io`, `std.fs`, `std.mem`, `std.path`, `std.os`, `std.str`, `std.time`, `std.math`, `std.json`, `std.fmt`, `std.coll`) is fully functional, cross-platform, and verified across all Tier 1 operating systems (Windows, Linux, macOS).
4. **Deterministic Self-Hosting Guarantee:** The compiler self-hosts across all Tier 1 platforms with bit-for-bit identical multi-stage determinism (Gen2 $\equiv$ Gen3 SHA-256 verified via `check_determinism.py`).
5. **Tooling & Ecosystem Stability:** Official editor tooling (VS Code extension with LSP), package management (`velo pkg`), and canonical formatting (`velo fmt`) are production-grade and follow the same stability contract as the compiler.
6. **Zero Open P0/P1 Architectural Gaps:** All Priority 0 (Blocking) and Priority 1 (Correctness/Foundational) items recorded in `gaps.md` are marked `[COMPLETED] ✅`.

---

## 4. Deprecation Policy ("Minimum Two Minor Versions")

To protect developers, libraries, and downstream systems from sudden breakage, Velo enforces a strict deprecation timeline for any language syntax, compiler flag, or standard library public API slated for retirement.

### 4.1 The Two Minor Versions Rule

> [!IMPORTANT]
> **No feature, keyword, syntax construct, or public standard library API may be removed without being formally deprecated for a minimum of two consecutive minor releases.**

For example, a feature marked deprecated in **v1.2.0** must remain fully functional throughout **v1.2.x** and **v1.3.x**, and cannot be removed earlier than **v1.4.0** (or **v2.0.0** if across major versions).

```
v1.2.0: Deprecation Notice (Compiler Warning emitted; code compiles and runs)
  │
  ▼
v1.3.0: Active Deprecation (Compiler Warning continue; migration tooling active)
  │
  ▼
v1.4.0: Earliest Eligible Removal (Feature removed; clean actionable error emitted)
```

### 4.2 Deprecation Lifecycle Stages

1. **Stage 1: Deprecation Notice (`vX.Y.0`):**
   - The construct is annotated as deprecated in `docs/SPECIFICATION.md` and `CHANGELOG.md`.
   - The compiler emits a clear, actionable compile-time warning diagnostic (e.g. `[Velo Warning] 'old_feature' is deprecated since v1.2.0 and will be removed in v1.4.0; use 'new_feature' instead`).
   - The code continues to compile, run, and pass existing tests without degradation or behavioral change.
2. **Stage 2: Active Grace Period (`vX.Y+1.0`):**
   - The warning diagnostic continues to be emitted during compilation.
   - All official documentation, examples, and showcase applications are updated to the replacement construct.
   - Automated migration guidance or refactoring suggestions are provided where feasible.
3. **Stage 3: Removal (`vX.Y+2.0` or next Major version):**
   - After at least two full minor version cycles have elapsed, the construct may be removed.
   - Attempted usage produces a descriptive compiler error diagnostic explaining the replacement and pointing to migration documentation.

### 4.3 Emergency Security Exception

In rare instances where an existing feature or API contains a critical, unpatchable security vulnerability (such as remote code execution or sandbox escape under strict safety mode), the Core Maintainers may disable or restrict the vulnerable construct in a patch release (`vX.Y.Z`). Any such emergency exception requires immediate public disclosure in [`SECURITY.md`](SECURITY.md) and full remediation guidance.
