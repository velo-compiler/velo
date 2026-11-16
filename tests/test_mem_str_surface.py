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

# The four `mem` members the legacy checker validated before Task 64.2. The
# closed-set rewrite must keep validating all of them.
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
    let parts: shelf[string] = str.split(s, "B")
    let h_str: string = str.heap_concat(s, "!")
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


# ---------------------------------------------------------------------------
# Task 64.2: the mem closed set and its per-member walls.
# ---------------------------------------------------------------------------

MEM_REJECT_ROWS = [
    # Unknown members: closed-set wording plus the valid list.
    ("unknown_member", "mem.does_not_exist()", "unknown mem member 'does_not_exist'"),
    ("unknown_member_arg", "mem.also_missing(1)", "unknown mem member 'also_missing'"),
    ("unknown_member_typo", "mem.freee(zone_buf)", "unknown mem member 'freee'"),
    # Arity: zero-argument queries.
    ("used_arg", "mem.used(1)", "mem.used expects exactly 0 arguments"),
    ("heap_used_arg", "mem.heap_used(1)", "mem.heap_used expects exactly 0 arguments"),
    ("current_arg", "mem.current(1)", "mem.current expects exactly 0 arguments"),
    # Arity: one-argument members.
    ("free_none", "mem.free()", "mem.free expects exactly 1 argument: (pointer)"),
    ("free_two", "mem.free(zone_buf, heap_buf)", "mem.free expects exactly 1 argument: (pointer)"),
    ("create_arena_none", "mem.create_arena()", "mem.create_arena expects exactly 1 argument: (capacity)"),
    ("destroy_arena_none", "mem.destroy_arena()", "mem.destroy_arena expects exactly 1 argument: (arena)"),
    # Arity: alloc family.
    ("alloc_none", "mem.alloc()", "mem.alloc expects 1 or 2 arguments: (count) or (@Type, count)"),
    ("alloc_three", "mem.alloc(@i32, 8, 9)", "mem.alloc expects 1 or 2 arguments"),
    ("heap_alloc_none", "mem.heap_alloc()", "mem.heap_alloc expects 1 or 2 arguments"),
    ("heap_alloc_three", "mem.heap_alloc(@i32, 8, 9)", "mem.heap_alloc expects 1 or 2 arguments"),
    (
        "alloc_with_none",
        "mem.alloc_with()",
        "mem.alloc_with expects exactly 3 arguments: (allocator, @Type, count)",
    ),
    ("alloc_with_two", "mem.alloc_with(active, @u8)", "mem.alloc_with expects exactly 3 arguments"),
    ("alloc_with_four", "mem.alloc_with(active, @u8, 8, 9)", "mem.alloc_with expects exactly 3 arguments"),
    # Types.
    ("free_int", "mem.free(1)", "mem.free expects a pointer argument (got i32)"),
    ("free_shelf", "mem.free(parts)", "mem.free expects a pointer argument (got shelf[string])"),
    ("destroy_arena_int", "mem.destroy_arena(1)", "mem.destroy_arena expects a pointer argument (got i32)"),
    ("create_arena_string", 'mem.create_arena("x")', "mem.create_arena expects an integer capacity (got string)"),
    ("alloc_string", 'mem.alloc("abc")', "mem.alloc expects an integer count (got string)"),
    ("alloc_ptr_count", 'mem.alloc(@i32, "x")', "mem.alloc expects an integer count (got string)"),
    ("alloc_void_count", "mem.alloc(io.println(1))", "mem.alloc expects an integer count (got void)"),
    ("heap_alloc_string", 'mem.heap_alloc("abc")', "mem.heap_alloc expects an integer count (got string)"),
    ("alloc_with_int_ty", "mem.alloc_with(active, 1, 8)", "mem.alloc_with expects a @Type argument (got i32)"),
    ("alloc_with_string_count", 'mem.alloc_with(active, @u8, "x")', "mem.alloc_with expects an integer count (got string)"),
]


@pytest.mark.parametrize(
    "ident,call,message",
    MEM_REJECT_ROWS,
    ids=[row[0] for row in MEM_REJECT_ROWS],
)
def test_mem_rejects_closed_set_violations(tmp_path, ident, call, message):
    """Every invalid mem call must fail at `velo check`, never at GCC."""
    _require_native()
    source = PROBE_HEADER + f"    {call}\n}}\n"
    res = run_check(source, tmp_path, f"mem_reject_{ident}.vl")
    blob = res.stdout + res.stderr
    assert res.returncode != 0, f"velo check accepted {call}:\n{blob}"
    assert message in blob, f"expected {message!r} for {call}:\n{blob}"
    assert "gcc" not in blob.lower(), f"{call} reached the C lane:\n{blob}"


def test_mem_unknown_member_diagnostic_lists_the_closed_set(tmp_path):
    _require_native()
    source = PROBE_HEADER + "    mem.does_not_exist()\n}\n"
    res = run_check(source, tmp_path, "mem_unknown_list.vl")
    blob = res.stdout + res.stderr
    assert res.returncode != 0, blob
    listed_match = re.search(r"\(functions: (.*)\)", blob)
    assert listed_match is not None, f"diagnostic has no member list:\n{blob}"
    listed = [name.strip() for name in listed_match.group(1).split(",")]
    assert len(listed) == len(set(listed)), f"duplicate names in diagnostic:\n{blob}"
    assert set(listed) == set(MEM_INVENTORY), (
        "diagnostic list does not match the accepted set:\n"
        f"missing: {sorted(set(MEM_INVENTORY) - set(listed))}\n"
        f"extra: {sorted(set(listed) - set(MEM_INVENTORY))}"
    )


def test_mem_rejection_never_emits_c(tmp_path):
    """The checker owns the rule: emit-c must not produce a translation unit."""
    _require_native()
    source = PROBE_HEADER + "    mem.does_not_exist()\n}\n"
    probe = tmp_path / "mem_unknown_emitc.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")
    out_c = tmp_path / "mem_unknown_emitc.c"
    res = subprocess.run(
        [str(VELO_EXE), "emit-c", str(probe), "-o", str(out_c)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
    )
    blob = res.stdout + res.stderr
    assert res.returncode != 0, f"emit-c accepted an unknown mem member:\n{blob}"
    assert "unknown mem member" in blob, blob


def test_mem_zero_arg_alloc_reports_instead_of_crashing(tmp_path):
    """Regression: `mem.alloc()` used to abort the compiler (0xC0000005)."""
    _require_native()
    source = PROBE_HEADER + "    mem.alloc()\n}\n"
    res = run_check(source, tmp_path, "mem_alloc_zero.vl")
    blob = res.stdout + res.stderr
    assert res.returncode not in (-1073741819, -1073741571), (
        f"velo check crashed instead of reporting:\n{blob}"
    )
    assert res.returncode != 0, blob
    assert "mem.alloc expects 1 or 2 arguments" in blob, blob


# ---------------------------------------------------------------------------
# Task 64.3: the str closed set.
# ---------------------------------------------------------------------------

STR_REJECT_ROWS = [
    # Unknown members: closed-set wording plus the valid list.
    ("unknown_member", "str.does_not_exist()", "unknown str member 'does_not_exist'"),
    ("unknown_member_arg", 'str.also_missing("x")', "unknown str member 'also_missing'"),
    ("typo_contains", 'str.contain(s, "b")', "unknown str member 'contain'"),
    # Internal runtime helpers are NOT members: reaching them used to cost a
    # GCC failure ("unknown type name 'unknown'").
    ("internal_eq", "str.eq(s, s)", "unknown str member 'eq'"),
    ("internal_neq", "str.neq(s, s)", "unknown str member 'neq'"),
    ("internal_nonnull", "str.nonnull(s)", "unknown str member 'nonnull'"),
    ("internal_copy_heap", "str.copy_heap(s)", "unknown str member 'copy_heap'"),
    ("internal_trim_impl", "str.trim_impl(s)", "unknown str member 'trim_impl'"),
    # Arity walls stay intact after the rewrite.
    ("len_none", "str.len()", "str.len expects exactly 1 argument: (string s)"),
    ("len_two", 'str.len(s, s)', "str.len expects exactly 1 argument"),
    ("trim_none", "str.trim()", "str.trim expects exactly 1 argument: (string s)"),
    ("concat_one", "str.concat(s)", "str.concat expects exactly 2 arguments: (string a, string b)"),
    ("replace_two", 'str.replace(s, "a")', "str.replace expects exactly 3 arguments"),
    ("format_none", "str.format()", "str.format expects at least 1 argument"),
    # Type walls.
    ("len_int", "str.len(1)", "str.len expects string arguments (got i32)"),
    ("trim_int", "str.trim(1)", "str.trim expects string arguments (got i32)"),
    ("concat_int", "str.concat(s, 1)", "str.concat expects string arguments (got i32)"),
    ("format_int", "str.format(1)", "str.format expects string arguments (got i32)"),
]


@pytest.mark.parametrize(
    "ident,call,message",
    STR_REJECT_ROWS,
    ids=[row[0] for row in STR_REJECT_ROWS],
)
def test_str_rejects_closed_set_violations(tmp_path, ident, call, message):
    """Every invalid str call must fail at `velo check`, never at GCC."""
    _require_native()
    source = PROBE_HEADER + f"    {call}\n}}\n"
    res = run_check(source, tmp_path, f"str_reject_{ident}.vl")
    blob = res.stdout + res.stderr
    assert res.returncode != 0, f"velo check accepted {call}:\n{blob}"
    assert message in blob, f"expected {message!r} for {call}:\n{blob}"
    assert "gcc" not in blob.lower(), f"{call} reached the C lane:\n{blob}"


def test_str_unknown_member_diagnostic_lists_the_closed_set(tmp_path):
    _require_native()
    source = PROBE_HEADER + "    str.does_not_exist()\n}\n"
    res = run_check(source, tmp_path, "str_unknown_list.vl")
    blob = res.stdout + res.stderr
    assert res.returncode != 0, blob
    listed_match = re.search(r"\(functions: (.*)\)", blob)
    assert listed_match is not None, f"diagnostic has no member list:\n{blob}"
    listed = [name.strip() for name in listed_match.group(1).split(",")]
    assert len(listed) == len(set(listed)), f"duplicate names in diagnostic:\n{blob}"
    assert set(listed) == set(STR_INVENTORY), (
        "diagnostic list does not match the accepted set:\n"
        f"missing: {sorted(set(STR_INVENTORY) - set(listed))}\n"
        f"extra: {sorted(set(listed) - set(STR_INVENTORY))}"
    )


def test_str_rejection_never_emits_c(tmp_path):
    """The checker owns the rule: emit-c must not produce a translation unit."""
    _require_native()
    source = PROBE_HEADER + "    str.does_not_exist()\n}\n"
    probe = tmp_path / "str_unknown_emitc.vl"
    probe.write_text(source, encoding="utf-8", newline="\n")
    out_c = tmp_path / "str_unknown_emitc.c"
    res = subprocess.run(
        [str(VELO_EXE), "emit-c", str(probe), "-o", str(out_c)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
    )
    blob = res.stdout + res.stderr
    assert res.returncode != 0, f"emit-c accepted an unknown str member:\n{blob}"
    assert "unknown str member" in blob, blob


def test_str_internal_helper_no_longer_reaches_gcc(tmp_path):
    """Regression: str.eq used to pass check and die with 'unknown' at GCC."""
    _require_native()
    source = PROBE_HEADER + "    let same: bool = str.eq(s, s)\n}\n"
    res = run_check(source, tmp_path, "str_eq_regression.vl")
    blob = res.stdout + res.stderr
    assert res.returncode != 0, blob
    assert "unknown str member 'eq'" in blob, blob
    assert "unknown type name" not in blob, blob


# ---------------------------------------------------------------------------
# Task 64.4: codegen defense in depth.
#
# The checker owns both rules, so the defensive branches are unreachable from
# source. These tests assert the guards exist in the backend (so a future
# lowering path cannot silently emit an unresolved symbol) and that no
# source-reachable program ever reports the internal wording.
# ---------------------------------------------------------------------------

CODEGEN_INTERNAL = "internal compiler error: unknown {} member"


def test_codegen_defends_the_mem_ladder():
    text = CODEGEN_CALL.read_text(encoding="utf-8")
    assert "unknown mem member reached codegen" in text, (
        "codegen_call.vl no longer fails on an unknown mem member reaching the ladder"
    )
    start = text.index('if target.str_val == "mem" {')
    end = text.index('if target.str_val == "thread"', start)
    ladder = text[start:end]
    assert 'report_error("internal"' in ladder, (
        "the mem ladder must report an internal error, not a backend/user one"
    )


def test_codegen_defends_the_str_dispatch():
    text = CODEGEN_IO.read_text(encoding="utf-8")
    assert "unknown str member '" in text, (
        "emit_str_call no longer guards the generic velo_str_<member> emission"
    )
    assert 'report_error("internal"' in text, (
        "the str dispatch must report an internal error"
    )
    assert "str_is_known_member" in text, (
        "emit_str_call must consult the checker's closed set, not a duplicate list"
    )


@pytest.mark.parametrize(
    "ident,call",
    [
        ("mem", "mem.does_not_exist()"),
        ("str", "str.does_not_exist()"),
        ("str_internal", "str.eq(s, s)"),
    ],
    ids=["mem", "str", "str_internal"],
)
def test_source_never_reaches_the_codegen_defense(tmp_path, ident, call):
    """The semantic lane must own the diagnostic; the internal lane is a net."""
    _require_native()
    source = PROBE_HEADER + f"    {call}\n}}\n"
    res = run_check(source, tmp_path, f"defense_{ident}.vl")
    blob = res.stdout + res.stderr
    assert res.returncode != 0, blob
    assert CODEGEN_INTERNAL.format(ident.split("_")[0]) not in blob, (
        f"the codegen defense fired for {call}; the checker must reject it first:\n{blob}"
    )
    assert "reached codegen" not in blob, blob
