"""
Documentation claims and code block verification test (Phase 83 / Task 83.5).

Enforces Security Invariant I83.5 / Documentation Drift Prevention:
"Every code block in README.md and docs/SPECIFICATION.md must compile
or be explicitly marked <!-- not-compiled -->."

Ensures that documentation examples never drift from canonical compiler syntax,
semantics, or standard library APIs.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import NamedTuple

import pytest
from conftest import cc_env, velo_exe

REPO_ROOT = Path(__file__).resolve().parent.parent


class DocBlock(NamedTuple):
    file_rel: str
    line_number: int
    lang: str
    is_not_compiled: bool
    code: str


def parse_doc_blocks(doc_path: Path) -> list[DocBlock]:
    """Parses all fenced code blocks from a Markdown document and extracts their metadata."""
    text = doc_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    blocks: list[DocBlock] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            fence = stripped
            lang = stripped[3:].strip()

            # Check preceding non-empty line for `<!-- not-compiled -->`
            is_not_compiled = False
            j = i - 1
            while j >= 0 and lines[j].strip() == "":
                j -= 1
            if j >= 0 and "not-compiled" in lines[j]:
                is_not_compiled = True
            if "not-compiled" in fence:
                is_not_compiled = True

            fence_line = i + 1
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1

            code = "\n".join(code_lines)
            blocks.append(
                DocBlock(
                    file_rel=str(doc_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                    line_number=fence_line,
                    lang=lang,
                    is_not_compiled=is_not_compiled,
                    code=code,
                )
            )
        i += 1

    return blocks


def get_all_blocks() -> list[DocBlock]:
    targets = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "docs" / "SPECIFICATION.md",
    ]
    all_b: list[DocBlock] = []
    for t in targets:
        if t.exists():
            all_b.extend(parse_doc_blocks(t))
    return all_b


ALL_BLOCKS = get_all_blocks()
COMPILED_BLOCKS = [b for b in ALL_BLOCKS if not b.is_not_compiled]


def _check_snippet(exe: Path, code_str: str) -> subprocess.CompletedProcess:
    """Attempts to check a code snippet as-is, and falls back to wrapping in act main() if needed."""
    s = code_str.strip()
    with tempfile.NamedTemporaryFile(suffix=".vl", delete=False, mode="w", encoding="utf-8") as f:
        f.write(s + "\n")
        tmp_name = f.name

    try:
        proc = subprocess.run(
            [str(exe), "check", tmp_name],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=cc_env(),
            timeout=5.0,
        )
        if proc.returncode == 0:
            return proc

        # Fallback: if snippet is statement-level code, wrap inside act main() { ... }
        wrapped = f"act main() {{\n{s}\n}}\n"
        with open(tmp_name, "w", encoding="utf-8") as f2:
            f2.write(wrapped)

        proc_wrapped = subprocess.run(
            [str(exe), "check", tmp_name],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=cc_env(),
            timeout=5.0,
        )
        if proc_wrapped.returncode == 0:
            return proc_wrapped

        # Return original failure for accurate diagnostics
        return proc
    finally:
        Path(tmp_name).unlink(missing_ok=True)


def test_markdown_blocks_discovery():
    """Asserts that both README.md and SPECIFICATION.md have code blocks discovered."""
    readme_blocks = [b for b in ALL_BLOCKS if b.file_rel == "README.md"]
    spec_blocks = [b for b in ALL_BLOCKS if b.file_rel == "docs/SPECIFICATION.md"]

    assert len(readme_blocks) >= 4, f"Expected at least 4 blocks in README.md, got {len(readme_blocks)}"
    assert len(spec_blocks) >= 50, f"Expected at least 50 blocks in SPECIFICATION.md, got {len(spec_blocks)}"

    # README quick-look must be in the compiled set
    readme_compiled = [b for b in readme_blocks if not b.is_not_compiled]
    assert len(readme_compiled) >= 1, "README.md quick-look block must be compiled"
    assert "Particle" in readme_compiled[0].code


@pytest.mark.parametrize(
    "block",
    COMPILED_BLOCKS,
    ids=[f"{b.file_rel}:L{b.line_number}" for b in COMPILED_BLOCKS],
)
def test_doc_code_block_compiles(block: DocBlock):
    """Asserts that every code block not marked <!-- not-compiled --> compiles cleanly."""
    exe = velo_exe()
    if not exe.exists():
        pytest.skip(f"Compiler binary {exe} not found")

    proc = _check_snippet(exe, block.code)
    assert proc.returncode == 0, (
        f"Code block at {block.file_rel}:{block.line_number} failed to compile!\n"
        f"Mark with <!-- not-compiled --> if this is non-compiling prose, pseudocode, or a syntax fragment.\n\n"
        f"--- Snippet ---\n{block.code}\n\n"
        f"--- Compiler Output ---\n{proc.stdout}\n{proc.stderr}"
    )
