"""Phase 64.1: authoritative inventory of the `mem.*` and `str.*` surfaces.

The phase closes two open surfaces. `check_mem_call` returns `true` for every
member outside `copy`/`move`/`set`/`realloc` (`src/analysis/mem_checks.vl:43`),
and `check_str_call` returns `"unknown"` for an unknown member with the legacy
fallthrough intact (`src/analysis/str_checks.vl:109`). Both surfaces therefore
accept a typo at `velo check` and fail later at GCC:

    mem.does_not_exist()   // check passes -> unknown type name 'unknown'
    str.does_not_exist()   // check passes -> unresolved velo_str_does_not_exist

This module pins the INVENTORY the closing tasks consume. It is deliberately
behaviour-neutral: it records which members each surface owns today, derived
from the codegen ladders and from the runtime helpers the codegen can emit, and
asserts that the documented table matches those sources. The rejection walls
land in Tasks 64.2-64.5.

Sources of truth encoded here:

* `mem` — the dispatch ladder in `src/backend/codegen_call.vl` under
  `target.str_val == "mem"`. Every member the backend can lower is a member.
* `str` — `velo_str_*` helper definitions in `runtime/velo_runtime.h` minus the
  internal helpers (`nonnull`, `copy_heap`, `copy_zone`, `eq`, `neq`, and the
  shared `*_impl` implementations) plus `len`, which lowers inline to `strlen`.
"""
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = REPO_ROOT / "bin" / "velo.exe"
CODEGEN_CALL = REPO_ROOT / "src" / "backend" / "codegen_call.vl"
CODEGEN_IO = REPO_ROOT / "src" / "backend" / "codegen_io.vl"
MEM_CHECKS = REPO_ROOT / "src" / "analysis" / "mem_checks.vl"
STR_CHECKS = REPO_ROOT / "src" / "analysis" / "str_checks.vl"
RUNTIME = REPO_ROOT / "runtime" / "velo_runtime.h"

# The closed set `mem.*` must enforce. Member -> canonical argument list for the
# acceptance probe. Every entry is lowered by codegen_call.vl's mem ladder.
MEM_INVENTORY = {
    "alloc": "@u8, 8",
    "heap_alloc": "@u8, 8",
    "free": "heap_buf",
    "realloc": "null, @u8, 8",
    "copy": "zone_buf, heap_buf, 8",
    "move": "zone_buf, heap_buf, 8",
    "set": "zone_buf, 0, 8",
    "used": "",
    "heap_used": "",
    "current": "",
    "alloc_with": "active, @u8, 8",
    "create_arena": "65536",
    "destroy_arena": "arena",
}

# The closed set `str.*` must enforce. `len` is the legacy member (inline
# strlen); the other seventeen are velo_str_* runtime helpers.
STR_INVENTORY = {
    "len": "s",
    "contains": 's, "b"',
    "starts_with": 's, "A"',
    "ends_with": 's, "C"',
    "index_of": 's, "b"',
    "trim": "s",
    "heap_trim": "s",
    "to_upper": "s",
    "heap_to_upper": "s",
    "to_lower": "s",
    "heap_to_lower": "s",
    "replace": 's, "A", "z"',
    "heap_replace": 's, "A", "z"',
    "concat": 's, "!"',
    "heap_concat": 's, "!"',
    "split": 's, ","',
    "format": '"plain %d", 1',
    "heap_format": '"plain %d", 1',
}

# Runtime helpers that exist but are NOT public `str.*` members: they are the
# shared implementations and the NUL-guard/copy primitives behind the members
# above. Reaching them from source is a defect, not a feature.
STR_INTERNAL_HELPERS = {
    "nonnull",
    "copy_heap",
    "copy_zone",
    "eq",
    "neq",
    "trim_impl",
    "replace_impl",
    "to_upper_impl",
    "to_lower_impl",
    "concat_impl",
    "format_impl",
}

# The four `mem` members the checker validates today. Task 64.2 extends this to
# the full inventory; the row exists so the rewrite cannot silently drop them.
MEM_CHECKED_TODAY = {"copy", "move", "set", "realloc"}

PROBE_HEADER = """use std.io
use std.mem
use std.str

act main() {
    let s = "AbC"
    let zone_buf: @u8 = mem.alloc(@u8, 8)
    let heap_buf: @u8 = mem.heap_alloc(@u8, 8)
    let arena: @Allocator = mem.create_arena(65536)
    let active: @Allocator = mem.current()
"""


def get_env():
    import os

    env = os.environ.copy()
    if r"C:\msys64\ucrt64\bin" not in env.get("PATH", ""):
        env["PATH"] = r"C:\msys64\ucrt64\bin;" + env.get("PATH", "")
    return env


def run_check(source, tmp_path, name):
    probe = tmp_path / name
    probe.write_text(source, encoding="utf-8", newline="\n")
    return subprocess.run(
        [str(VELO_EXE), "check", str(probe)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
    )


def _require_native():
    if not VELO_EXE.exists():
        pytest.skip("bin/velo not built")


def _codegen_mem_members():
    """Every `member == "<name>"` in the codegen `mem` ladder."""
    text = CODEGEN_CALL.read_text(encoding="utf-8")
    start = text.index('if target.str_val == "mem" {')
    end = text.index('if target.str_val == "thread"', start)
    return set(re.findall(r'member == "([a-z0-9_]+)"', text[start:end]))


def _runtime_str_helpers():
    """Every `velo_str_<name>` runtime helper, split into members vs internal."""
    text = RUNTIME.read_text(encoding="utf-8")
    found = set(re.findall(r"\bvelo_str_([a-z0-9_]+)\s*\(", text))
    return found - STR_INTERNAL_HELPERS, found & STR_INTERNAL_HELPERS


# ---------------------------------------------------------------------------
# Static inventory: the tables above must match the compiler and the runtime.
# ---------------------------------------------------------------------------


def test_mem_inventory_matches_the_codegen_ladder():
    ladder = _codegen_mem_members()
    assert ladder == set(MEM_INVENTORY), (
        "the mem inventory drifted from codegen_call.vl:\n"
        f"only in codegen: {sorted(ladder - set(MEM_INVENTORY))}\n"
        f"only in inventory: {sorted(set(MEM_INVENTORY) - ladder)}"
    )


def test_str_inventory_matches_the_runtime_helpers():
    members, _ = _runtime_str_helpers()
    expected = set(STR_INVENTORY) - {"len"}
    assert members == expected, (
        "the str inventory drifted from runtime/velo_runtime.h:\n"
        f"public helpers without an inventory row: {sorted(members - expected)}\n"
        f"inventory rows without a public helper: {sorted(expected - members)}"
    )


def test_str_internal_helpers_are_not_published_as_members():
    _, internal = _runtime_str_helpers()
    leaked = internal & set(STR_INVENTORY)
    assert not leaked, f"internal helpers leaked into the public set: {sorted(leaked)}"


def test_mem_checked_members_are_a_subset_of_the_inventory():
    assert MEM_CHECKED_TODAY <= set(MEM_INVENTORY)


def test_mem_checks_still_validate_the_legacy_four():
    text = MEM_CHECKS.read_text(encoding="utf-8")
    for member in MEM_CHECKED_TODAY:
        assert f'member != "{member}"' in text or f'member == "{member}"' in text, (
            f"mem_checks.vl no longer mentions {member}"
        )


def test_str_checks_cover_every_non_legacy_member():
    text = STR_CHECKS.read_text(encoding="utf-8")
    missing = [m for m in STR_INVENTORY if f'"{m}"' not in text]
    assert not missing, f"str_checks.vl has no rule for: {missing}"


def test_codegen_str_dispatch_is_generic():
    """Documents the open `velo_str_<member>` fallback Task 64.4 must close."""
    text = CODEGEN_IO.read_text(encoding="utf-8")
    assert 'sb_append_str(sb, "velo_str_")' in text, (
        "emit_str_call no longer concatenates the member name onto velo_str_ — "
        "the Task 64.4 defense must be re-derived"
    )


# ---------------------------------------------------------------------------
# Runtime inventory: every documented member is accepted by `velo check`.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("member,args", sorted(MEM_INVENTORY.items()))
def test_mem_member_is_accepted(tmp_path, member, args):
    _require_native()
    source = PROBE_HEADER + f"    mem.{member}({args})\n}}\n"
    res = run_check(source, tmp_path, f"mem_{member}.vl")
    assert res.returncode == 0, (
        f"velo check rejected the documented member mem.{member}:\n"
        f"stdout: {res.stdout}\nstderr: {res.stderr}"
    )


@pytest.mark.parametrize("member,args", sorted(STR_INVENTORY.items()))
def test_str_member_is_accepted(tmp_path, member, args):
    _require_native()
    source = PROBE_HEADER + f"    str.{member}({args})\n}}\n"
    res = run_check(source, tmp_path, f"str_{member}.vl")
    assert res.returncode == 0, (
        f"velo check rejected the documented member str.{member}:\n"
        f"stdout: {res.stdout}\nstderr: {res.stderr}"
    )


def test_whole_mem_surface_checks_together(tmp_path):
    """One program touching every mem member: no cross-member interference."""
    _require_native()
    lines = [PROBE_HEADER]
    for member, args in MEM_INVENTORY.items():
        lines.append(f"    mem.{member}({args})\n")
    lines.append("}\n")
    res = run_check("".join(lines), tmp_path, "mem_surface_all.vl")
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"


def test_whole_str_surface_checks_together(tmp_path):
    """One program touching every str member: no cross-member interference."""
    _require_native()
    lines = [PROBE_HEADER]
    for member, args in STR_INVENTORY.items():
        lines.append(f"    str.{member}({args})\n")
    lines.append("}\n")
    res = run_check("".join(lines), tmp_path, "str_surface_all.vl")
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
