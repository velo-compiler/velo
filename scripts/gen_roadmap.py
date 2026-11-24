#!/usr/bin/env python3
"""scripts/gen_roadmap.py — Generates docs/ROADMAP.md deterministically from gaps.md.

Task 84.5 & Phase 84 Exit Criteria:
  "docs/ROADMAP.md is generated from gaps.md and fails CI when stale."

Usage:
  python scripts/gen_roadmap.py          # Generate or update docs/ROADMAP.md
  python scripts/gen_roadmap.py --check  # Verify docs/ROADMAP.md is fresh (exits 1 on drift)
  python scripts/gen_roadmap.py --stdout # Print generated roadmap to stdout
"""

import argparse
import difflib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
GAPS_MD = REPO_ROOT / "gaps.md"
TARGET_ROADMAP = REPO_ROOT / "docs" / "ROADMAP.md"


@dataclass
class TaskItem:
    task_id: str
    is_completed: bool
    summary: str


@dataclass
class PhaseData:
    number: int
    title: str
    severity: str
    raw_status: str
    status_kind: str  # COMPLETED, CLOSED, PARTIAL, OPEN
    defect_summary: str = ""
    invariants: List[str] = field(default_factory=list)
    tasks: List[TaskItem] = field(default_factory=list)
    exit_criteria: List[str] = field(default_factory=list)
    residual_table: List[str] = field(default_factory=list)


def parse_backlog_summary_table(text: str) -> List[dict]:
    """Parse table from ## 3. Backlog Summary."""
    m = re.search(r"## 3\. Backlog Summary\s*\n\n(.*?)(?=\n## 4|\Z)", text, re.DOTALL)
    if not m:
        return []
    lines = [l.strip() for l in m.group(1).splitlines() if l.strip().startswith("|")]
    if len(lines) < 3:
        return []
    
    rows = []
    for line in lines[2:]:  # skip header and separator
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) >= 5:
            phase_num = re.sub(r"[^\d]", "", cols[0])
            rows.append({
                "phase": int(phase_num) if phase_num else 0,
                "title": cols[1],
                "severity": cols[2],
                "verified": cols[3],
                "tasks": cols[4],
                "commits": cols[5] if len(cols) > 5 else "",
            })
    return rows


def parse_waves(text: str) -> List[dict]:
    """Parse wave definitions from ## 4. Recommended Execution Waves."""
    m = re.search(r"## 4\. Recommended Execution Waves\s*\n\n(.*?)(?=\n## 5|\Z)", text, re.DOTALL)
    if not m:
        return []
    wave_items = re.findall(r"- \*\*Wave\s+([A-Z])\s*\(([^)]+)\):\*\*\s*(.*?)(?=(?:\n- \*\*Wave|\Z))", m.group(1), re.DOTALL)
    waves = []
    for w, name, desc in wave_items:
        clean_desc = " ".join(desc.split())
        waves.append({
            "wave": w.strip(),
            "name": name.strip(),
            "desc": clean_desc,
        })
    return waves


def normalize_status(raw: str) -> str:
    upper = raw.upper()
    if "COMPLETED" in upper or "CLOSED" in upper:
        return "COMPLETED"
    if "PARTIAL" in upper:
        return "PARTIAL"
    return "OPEN"


def parse_gaps_md(text: str) -> List[PhaseData]:
    """Extract structured phase data from gaps.md."""
    sections = re.split(r"\n(?=# Phase \d+:)", text)
    phases: List[PhaseData] = []

    for sec in sections:
        header_m = re.match(r"# Phase (\d+):\s*([^(]+)\s*\((P\d)\)\s*-\s*([^\n]+)", sec)
        if not header_m:
            continue
        num_str, title, sev, status_raw = header_m.groups()
        num = int(num_str)
        norm_status = normalize_status(status_raw)

        phase = PhaseData(
            number=num,
            title=title.strip(),
            severity=sev.strip(),
            raw_status=status_raw.strip(),
            status_kind=norm_status,
        )

        # Defect summary
        defect_m = re.search(r"## Defect\s*\n\n(.*?)(?=\n## |\n---\Z|\Z)", sec, re.DOTALL)
        if defect_m:
            phase.defect_summary = defect_m.group(1).strip()
        else:
            para_m = re.search(r"\n\n([^\n#][^\n]+(?:\n[^\n#][^\n]+)*)", sec)
            if para_m:
                phase.defect_summary = para_m.group(1).strip()

        # Invariants
        inv_m = re.search(r"## (?:Security )?Invariants\s*\n\n(.*?)(?=\n## |\Z)", sec, re.DOTALL)
        if inv_m:
            items = re.findall(r"- (\*\*I\d+\.\d+\*\*.*?)(?=(?:\n- \*\*I|\n###|\n##|\Z))", inv_m.group(1), re.DOTALL)
            for it in items:
                clean_it = " ".join(it.split())
                phase.invariants.append(f"- {clean_it}")

        # Tasks
        task_matches = re.finditer(r"\*\*(\d+\.\d+)(?:\s*\[COMPLETED\]\s*✅)?\*\*\s*([\s\S]*?)(?=\n\n\*\*|\n\n##|\n\n---\Z|\Z)", sec)
        for tm in task_matches:
            tid = tm.group(1)
            raw_task = tm.group(0)
            is_done = "[COMPLETED]" in raw_task or "✅" in raw_task or norm_status == "COMPLETED"
            body = tm.group(2).strip()
            clean_body = " ".join(body.split())
            m_sent = re.split(r"(?<=[.!?])\s+", clean_body)
            first_sentence = m_sent[0] if m_sent else clean_body
            phase.tasks.append(TaskItem(task_id=tid, is_completed=is_done, summary=first_sentence))

        # Exit criteria
        exit_m = re.search(r"## Phase Exit Criteria\s*\n\n(.*?)(?=\n## |\n---\Z|\Z)", sec, re.DOTALL)
        if exit_m:
            raw_exit = exit_m.group(1).strip()
            if raw_exit.startswith("|"):
                phase.exit_criteria = [l.strip() for l in raw_exit.splitlines() if l.strip().startswith("|")]
            else:
                items = re.findall(r"- (.*?)(?=(?:\n- |\n##|\n---\Z|\Z))", raw_exit, re.DOTALL)
                for it in items:
                    clean_it = " ".join(it.split())
                    phase.exit_criteria.append(clean_it)

        # Residual table (Phase 85)
        if num == 85:
            table_m = re.search(r"(\| Item \| Evidence \|.*?\n\n)", sec, re.DOTALL)
            if table_m:
                phase.residual_table = [l.strip() for l in table_m.group(1).splitlines() if l.strip().startswith("|")]

        phases.append(phase)

    return sorted(phases, key=lambda p: p.number)


def generate_roadmap_markdown(gaps_text: str) -> str:
    """Generate the complete markdown document for docs/ROADMAP.md."""
    backlog_summary = parse_backlog_summary_table(gaps_text)
    waves = parse_waves(gaps_text)
    phases = parse_gaps_md(gaps_text)

    # Compute progress stats
    total_tasks = sum(len(p.tasks) for p in phases)
    completed_tasks = sum(sum(1 for t in p.tasks if t.is_completed) for p in phases)
    completed_phases = sum(1 for p in phases if p.status_kind == "COMPLETED")
    open_phases = [p for p in phases if p.status_kind != "COMPLETED"]

    lines = [
        "<!-- ===================================================================== -->",
        "<!-- AUTO-GENERATED FILE -- DO NOT EDIT DIRECTLY                           -->",
        "<!-- Generated by scripts/gen_roadmap.py from gaps.md                     -->",
        "<!-- To check freshness: python scripts/gen_roadmap.py --check             -->",
        "<!-- To regenerate:      python scripts/gen_roadmap.py                     -->",
        "<!-- ===================================================================== -->",
        "",
        "# 🗺️ Velo Engineering Roadmap & Release Registry",
        "",
        "> **Living Engineering Roadmap**: This document is generated deterministically from [`gaps.md`](../gaps.md) (the project's authoritative release gate and audit registry).",
        "> In accordance with the **Task Execution Contract (Section 5 of `gaps.md`)**, the public roadmap cannot drift from the registry. Every completed milestone is backed by regression tests and an architectural audit entry.",
        "",
        "---",
        "",
        "## 📊 High-Level Release Status",
        "",
        f"- **Current Baseline:** Self-hosted native compiler (`2.0.0-pre`, Stage 2 canonical).",
        f"- **Phase Completion:** **{completed_phases}/{len(phases)} Phases Closed** ({round(completed_phases / max(1, len(phases)) * 100)}%).",
        f"- **Task Execution:** **{completed_tasks}/{total_tasks} Tasks Delivered** ({round(completed_tasks / max(1, total_tasks) * 100)}%).",
        f"- **Open / Active Phases:** {len(open_phases)} ({', '.join(f'Phase {p.number}' for p in open_phases) if open_phases else 'None'}).",
        "",
        "---",
        "",
        "## 🌊 Strategic Execution Waves",
        "",
    ]

    for w in waves:
        lines.append(f"### Wave {w['wave']}: {w['name'].title()}")
        lines.append(f"{w['desc']}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 📋 Phase Progress Matrix",
        "",
        "| Phase | Milestone Title | Tier | Status | Tasks | Progress |",
        "| :---: | :--- | :---: | :---: | :---: | :---: |",
    ])

    for p in phases:
        t_total = len(p.tasks)
        t_done = sum(1 for t in p.tasks if t.is_completed)
        pct = round((t_done / t_total) * 100) if t_total > 0 else (100 if p.status_kind == "COMPLETED" else 0)
        
        status_badge = {
            "COMPLETED": "✅ **Closed**",
            "PARTIAL": "⚠️ **Partial**",
            "OPEN": "⏳ **Open**",
        }.get(p.status_kind, p.status_kind)

        lines.append(f"| **{p.number}** | {p.title} | `{p.severity}` | {status_badge} | {t_done}/{t_total} | {pct}% |")

    lines.extend([
        "",
        "---",
        "",
        "## 🚀 Active & Open Milestone Phases",
        "",
    ])

    for p in open_phases:
        lines.append(f"### Phase {p.number}: {p.title} (`{p.severity}`)")
        lines.append(f"**Current Status:** `{p.raw_status}`")
        lines.append("")
        if p.defect_summary:
            lines.append(f"**Goal & Scope:**\n> {' '.join(p.defect_summary.splitlines()[:2])}")
            lines.append("")
        
        if p.invariants:
            lines.append("**Governing Invariants:**")
            for inv in p.invariants:
                lines.append(f"{inv}")
            lines.append("")

        if p.tasks:
            lines.append("**Deliverable Tasks:**")
            for t in p.tasks:
                check = "x" if t.is_completed else " "
                tag = "✅ (Delivered)" if t.is_completed else "⏳ (Scheduled / In Progress)"
                lines.append(f"- [{check}] **Task {t.task_id}:** {t.summary} {tag}")
            lines.append("")

        if p.exit_criteria:
            lines.append("**Phase Exit Criteria:**")
            if p.exit_criteria[0].startswith("|"):
                for row in p.exit_criteria:
                    lines.append(row)
            else:
                for crit in p.exit_criteria:
                    lines.append(f"- [ ] {crit}")
            lines.append("")

        if p.residual_table:
            lines.append("**Recorded Residual Limitations:**")
            for row in p.residual_table:
                lines.append(row)
            lines.append("")

        lines.append("---")
        lines.append("")

    lines.extend([
        "## 📦 Completed Milestone Archives",
        "",
        "The following foundational phases have completed their audit contracts and shipped with full regression verification:",
        "",
    ])

    completed_list = [p for p in phases if p.status_kind == "COMPLETED"]
    for p in completed_list:
        lines.append(f"- **Phase {p.number} ({p.title} — `{p.severity}`):** Delivered {len(p.tasks)} tasks verified in-tree. Audit trail documented in [`gaps.md`](../gaps.md).")

    lines.extend([
        "",
        "---",
        "",
        "## 🛠️ Contributing to the Roadmap",
        "",
        "To propose an enhancement, report a limitation, or contribute to an open phase:",
        "1. **Propose:** Open an issue using [`.github/ISSUE_TEMPLATE/feature.md`](../.github/ISSUE_TEMPLATE/feature.md) or [`.github/ISSUE_TEMPLATE/bug.md`](../.github/ISSUE_TEMPLATE/bug.md).",
        "2. **Govern:** Review the stability guarantees and 5-stage approval pipeline in [`GOVERNANCE.md`](../GOVERNANCE.md).",
        "3. **Execute:** Follow the Task Execution Contract (Section 5 of `gaps.md`) and submit a PR conforming to [`.github/PULL_REQUEST_TEMPLATE.md`](../.github/PULL_REQUEST_TEMPLATE.md).",
        "4. **Verify Freshness:** CI enforces roadmap consistency via `python scripts/gen_roadmap.py --check`.",
        "",
    ])

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate docs/ROADMAP.md from gaps.md")
    parser.add_argument("--check", action="store_true", help="Check if docs/ROADMAP.md is fresh (exit 1 on drift)")
    parser.add_argument("--stdout", action="store_true", help="Print generated markdown to stdout")
    args = parser.parse_args()

    if not GAPS_MD.exists():
        print(f"Error: gaps.md not found at {GAPS_MD}", file=sys.stderr)
        return 1

    gaps_content = GAPS_MD.read_text(encoding="utf-8")
    generated = generate_roadmap_markdown(gaps_content)

    if args.stdout:
        sys.stdout.write(generated)
        return 0

    if args.check:
        if not TARGET_ROADMAP.exists():
            print(f"FAIL: {TARGET_ROADMAP} does not exist. Run 'python scripts/gen_roadmap.py' to generate.", file=sys.stderr)
            return 1

        existing = TARGET_ROADMAP.read_text(encoding="utf-8")
        if existing != generated:
            print("FAIL: docs/ROADMAP.md is stale or has drifted from gaps.md!", file=sys.stderr)
            diff = difflib.unified_diff(
                existing.splitlines(keepends=True),
                generated.splitlines(keepends=True),
                fromfile="docs/ROADMAP.md",
                tofile="generated from gaps.md",
                n=3
            )
            sys.stderr.writelines(diff)
            print("\nRun 'python scripts/gen_roadmap.py' to synchronize.", file=sys.stderr)
            return 1

        print("PASS: docs/ROADMAP.md is up to date with gaps.md.")
        return 0

    # Default: write to docs/ROADMAP.md
    TARGET_ROADMAP.parent.mkdir(parents=True, exist_ok=True)
    if TARGET_ROADMAP.exists() and TARGET_ROADMAP.read_text(encoding="utf-8") == generated:
        print(f"OK: {TARGET_ROADMAP} is already up to date.")
    else:
        TARGET_ROADMAP.write_text(generated, encoding="utf-8")
        print(f"Generated {TARGET_ROADMAP} ({len(generated):,} bytes).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
