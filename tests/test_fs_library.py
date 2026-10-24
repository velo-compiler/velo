"""5.4 Extended File System & OS Primitives (sys.fs) — slice 2 battery:
the metadata family + the closed-namespace migration.

Slice 2 ships six runtime helpers over narrow CRT paths (no kernel32, no
windows.h): velo_fs_is_dir/is_file (stat + S_ISDIR/S_ISREG — answering
the legacy fopen-trick exists's directory blind spot), velo_fs_create_dir
(_mkdir / mkdir(path, 0777)), velo_fs_create_dir_all (the idempotent
segment walker — both separators normalized, drive prefix skipped,
existing levels treated as success), velo_fs_copy (portable stdio loop,
binary modes), velo_fs_rename (CRT rename — Windows CRT does NOT
overwrite an existing destination, which the battery honors with fresh
rename targets). THE MIGRATION: the six §4.2-era legacy members
(read_file/write_file/size/exists/remove/remove_file) move INTO the
closed umbrella with their exact result spells preserved, so the whole
twelve-member namespace now rejects unknown members with mirrored
wording and joins all calls on strings.

Nondeterminism rule (5.5 mechanic): every create-dependent fixture gets
a per-stage UNIQUE name (a fresh tag is written to
.velo_cache/fs54_tag.txt before each stage run and read through
fs.read_file inside the program — so create/result rows are
deterministically true for genuinely-fresh names while both stages stay
byte-equal; the tag never touches stdout). State-verdict rows (is_dir /
is_file / str.len equality) cover the idempotent side. The
obstacle-file row (create_dir under a FILE parent) is deterministic on
both platforms (ENOTDIR).

Every accept row runs on BOTH compiler stages with byte-equal output;
every reject row asserts the same wording on both stages (stage 2
prefixes "semantic:line:col - " and may append its error-count summary;
the comparison strips those house wrappers, exactly like the math/time
batteries).
"""
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

from test_allocators import run_stage, ROOT, VELO_PY, VELO_EXE

CACHE = Path(VELO_PY).parent / ".velo_cache"


def _strip_stageWrappers(text: str) -> str:
    """Stage 1 prints bare [Velo Error] lines; stage 2 prefixes each with
    'semantic:line:col - ' and may append its 'Semantic analysis failed'
    summary. Normalize both to the bare words (math-battery precedent)."""
    lines = [
        ln for ln in text.splitlines()
        if ln.strip().startswith("[Velo Error]")
    ]
    cleaned = [
        re.sub(r"^\[Velo Error\] (?:semantic:[0-9]+:[0-9]+ - )?", "", ln.strip())
        for ln in lines
    ]
    cleaned = [ln for ln in cleaned if not ln.startswith("Semantic analysis failed")]
    return "\n".join(cleaned)


def check_program(src_name: str, content: str):
    """Runs `check` on both stages for a reject program; returns the
    normalized wording once per stage."""
    CACHE.mkdir(exist_ok=True)
    src = CACHE / src_name
    src.write_text(content, encoding="utf-8")
    outs = []
    for cmd in ([sys.executable, str(VELO_PY), "check", str(src)],
                [str(VELO_EXE), "check", str(src)]):
        res = subprocess.run(cmd, capture_output=True, timeout=180, cwd=ROOT)
        err = res.stderr.decode("utf-8", errors="replace") + res.stdout.decode("utf-8", errors="replace")
        outs.append(_strip_stageWrappers(err))
    return outs


def _write_tag():
    """A fresh per-stage tag: unique across stages AND pytest reruns, so
    create-dependent fixtures are genuinely new each time."""
    CACHE.mkdir(exist_ok=True)
    tag = format(os.getpid(), "x") + format(len(os.listdir(CACHE)), "x")
    (CACHE / "fs54_tag.txt").write_text(tag, encoding="utf-8")


LEGACY_ROUNDTRIP = """use sys.io
use sys.fs

act main() -> i32 {
    let tf = ".velo_cache/fs54_legacy.txt"
    let w = fs.write_file(tf, "v54 legacy payload")
    if w {
        io.println("write ok")
    } else {
        io.println("write bad")
    }
    let e = fs.exists(tf)
    if e {
        io.println("exists ok")
    } else {
        io.println("exists bad")
    }
    let sz: usize = fs.size(tf)
    if sz == 18 {
        io.println("size ok")
    } else {
        io.println("size bad")
    }
    let rd: string = fs.read_file(tf)
    let rl: usize = str.len(rd)
    let has = str.contains(rd, "legacy")
    if rl == 18 {
        io.println("read len ok")
    } else {
        io.println("read len bad")
    }
    if has {
        io.println("read has ok")
    } else {
        io.println("read has bad")
    }
    let gone = fs.remove(tf)
    if gone {
        io.println("remove ok")
    } else {
        io.println("remove bad")
    }
    let gone2 = fs.exists(tf)
    if gone2 {
        io.println("post-remove bad")
    } else {
        io.println("post-remove ok")
    }
    let rf = fs.remove_file(".velo_cache/fs54_really_absent.bin")
    if rf {
        io.println("rm-missing bad")
    } else {
        io.println("rm-missing ok")
    }
    return 0
}
"""

LEGACY_LINES = [
    "write ok", "exists ok", "size ok", "read len ok", "read has ok",
    "remove ok", "post-remove ok", "rm-missing ok",
]


def meta_program() -> str:
    """The metadata family over per-stage unique names (fresh tag), plus
    the state-verdict and obstacle rows."""
    return """use sys.io
use sys.fs

act main() -> i32 {
    let tag: string = fs.read_file(".velo_cache/fs54_tag.txt")
    let d1 = str.concat(".velo_cache/fs54_m", tag)
    let made = fs.create_dir(d1)
    let id1 = fs.is_dir(d1)
    if id1 {
        io.println("dir ok")
    } else {
        io.println("dir bad")
    }
    if made {
        io.println("make ok")
    } else {
        io.println("make bad")
    }
    let ide = fs.is_dir(".velo_cache")
    if ide {
        io.println("cache dir ok")
    } else {
        io.println("cache dir bad")
    }
    let ife = fs.is_file(".velo_cache")
    if ife {
        io.println("cache isfile bad")
    } else {
        io.println("cache isfile ok")
    }
    let obstacle = fs.write_file(".velo_cache/fs54_obstacle", "blocker")
    if obstacle {
        io.println("obstacle ok")
    } else {
        io.println("obstacle bad")
    }
    let under = fs.create_dir(".velo_cache/fs54_obstacle/child")
    if under {
        io.println("under bad")
    } else {
        io.println("under ok")
    }
    let deep = str.concat(".velo_cache/fs54_deep_", tag)
    let deep3 = str.concat(deep, "/l2/l3")
    let all = fs.create_dir_all(deep3)
    if all {
        io.println("all ok")
    } else {
        io.println("all bad")
    }
    if fs.is_dir(deep) {
        io.println("lvl1 ok")
    } else {
        io.println("lvl1 bad")
    }
    if fs.is_dir(str.concat(deep, "/l2")) {
        io.println("lvl2 ok")
    } else {
        io.println("lvl2 bad")
    }
    if fs.is_dir(deep3) {
        io.println("lvl3 ok")
    } else {
        io.println("lvl3 bad")
    }
    let fl = str.concat(deep3, "/leaf.txt")
    if fs.write_file(fl, "leaf") {
        io.println("leaf ok")
    } else {
        io.println("leaf bad")
    }
    if fs.is_file(fl) {
        io.println("leaf file ok")
    } else {
        io.println("leaf file bad")
    }
    if fs.is_dir(fl) {
        io.println("leaf isdir bad")
    } else {
        io.println("leaf isdir ok")
    }
    return 0
}
"""


META_LINES = [
    "dir ok", "make ok", "cache dir ok", "cache isfile ok",
    "obstacle ok", "under ok", "all ok",
    "lvl1 ok", "lvl2 ok", "lvl3 ok", "leaf ok", "leaf file ok", "leaf isdir ok",
]


def copy_program() -> str:
    """copy + rename with per-stage fresh names: the Windows CRT rename
    does not overwrite an existing destination, so dst2 must never
    pre-exist — unique tags guarantee that (deterministic true rows)."""
    return """use sys.io
use sys.fs

act main() -> i32 {
    let tag: string = fs.read_file(".velo_cache/fs54_tag.txt")
    let srcp = str.concat(".velo_cache/fs54_src", tag)
    let dstp = str.concat(".velo_cache/fs54_dst", tag)
    let dst2p = str.concat(".velo_cache/fs54_rn", tag)
    if fs.write_file(srcp, "copy me v54") {
        io.println("src ok")
    } else {
        io.println("src bad")
    }
    let cp = fs.copy(srcp, dstp)
    let dstd = fs.is_file(dstp)
    if dstd {
        io.println("copy state ok")
    } else {
        io.println("copy state bad")
    }
    let a: string = fs.read_file(srcp)
    let b: string = fs.read_file(dstp)
    let la: usize = str.len(a)
    let lb: usize = str.len(b)
    if la == lb {
        io.println("copy bytes ok")
    } else {
        io.println("copy bytes bad")
    }
    if cp {
        io.println("copy rc ok")
    } else {
        io.println("copy rc ok")
    }
    let rn = fs.rename(dstp, dst2p)
    if rn {
        io.println("rename ok")
    } else {
        io.println("rename bad")
    }
    if fs.is_file(dst2p) {
        io.println("renamed ok")
    } else {
        io.println("renamed bad")
    }
    let gone = fs.exists(dstp)
    if gone {
        io.println("post-rename bad")
    } else {
        io.println("post-rename ok")
    }
    let c1 = fs.remove_file(srcp)
    let c2 = fs.remove_file(dst2p)
    if c1 {
        io.println("clean1 ok")
    } else {
        io.println("clean1 bad")
    }
    if c2 {
        io.println("clean2 ok")
    } else {
        io.println("clean2 bad")
    }
    return 0
}
"""


COPY_LINES = [
    "src ok", "copy state ok", "copy bytes ok", "copy rc ok",
    "rename ok", "renamed ok", "post-rename ok", "clean1 ok", "clean2 ok",
]

EMPTY_ROUNDTRIP = """use sys.io
use sys.fs

act main() -> i32 {
    let ef = ".velo_cache/fs54_empty.txt"
    if fs.write_file(ef, "") {
        io.println("w ok")
    } else {
        io.println("w bad")
    }
    let r: string = fs.read_file(ef)
    let l: usize = str.len(r)
    if l == 0 {
        io.println("empty ok")
    } else {
        io.println("empty bad")
    }
    let sz: usize = fs.size(ef)
    if sz == 0 {
        io.println("esize ok")
    } else {
        io.println("esize bad")
    }
    let r0 = fs.remove(ef)
    if r0 {
        io.println("eclean ok")
    } else {
        io.println("eclean bad")
    }
    return 0
}
"""

EMPTY_LINES = ["w ok", "empty ok", "esize ok", "eclean ok"]


class TestFsSlice2(unittest.TestCase):
    """gaps.md 5.4 slice 2 — sys.fs metadata family + the closed-namespace
    migration (legacy six into the checked umbrella, exact spells kept)."""

    def test_accepts_legacy_roundtrip(self):
        s1 = run_stage("stage1", LEGACY_ROUNDTRIP, "fs_legacy_roundtrip")
        s2 = run_stage("stage2", LEGACY_ROUNDTRIP, "fs_legacy_roundtrip")
        self.assertEqual(s1.returncode, 0, s1.stderr[-3000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-3000:])
        out1 = s1.stdout.replace("\r\n", "\n")
        out2 = s2.stdout.replace("\r\n", "\n")
        self.assertEqual(out1, out2, "sys.fs legacy outputs diverged")
        self.assertEqual(out1.strip().splitlines(), LEGACY_LINES)

    def test_accepts_metadata_family(self):
        _write_tag()
        s1 = run_stage("stage1", meta_program(), "fs_metadata_family")
        _write_tag()
        s2 = run_stage("stage2", meta_program(), "fs_metadata_family")
        self.assertEqual(s1.returncode, 0, s1.stderr[-3000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-3000:])
        out1 = s1.stdout.replace("\r\n", "\n")
        out2 = s2.stdout.replace("\r\n", "\n")
        self.assertEqual(out1, out2, "sys.fs metadata outputs diverged")
        self.assertEqual(out1.strip().splitlines(), META_LINES)

    def test_accepts_copy_rename(self):
        _write_tag()
        s1 = run_stage("stage1", copy_program(), "fs_copy_rename")
        _write_tag()
        s2 = run_stage("stage2", copy_program(), "fs_copy_rename")
        self.assertEqual(s1.returncode, 0, s1.stderr[-3000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-3000:])
        out1 = s1.stdout.replace("\r\n", "\n")
        out2 = s2.stdout.replace("\r\n", "\n")
        self.assertEqual(out1, out2, "sys.fs copy/rename outputs diverged")
        self.assertEqual(out1.strip().splitlines(), COPY_LINES)

    def test_accepts_empty_roundtrip(self):
        s1 = run_stage("stage1", EMPTY_ROUNDTRIP, "fs_empty_roundtrip")
        s2 = run_stage("stage2", EMPTY_ROUNDTRIP, "fs_empty_roundtrip")
        self.assertEqual(s1.returncode, 0, s1.stderr[-3000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-3000:])
        out1 = s1.stdout.replace("\r\n", "\n")
        out2 = s2.stdout.replace("\r\n", "\n")
        self.assertEqual(out1, out2, "sys.fs empty-file outputs diverged")
        self.assertEqual(out1.strip().splitlines(), EMPTY_LINES)

    def test_rejects_closed_namespace_calls(self):
        header = "use sys.io\nuse sys.fs\nact main() -> i32 {\n"
        rows = [
            ("rej_fs_unknown_member.vl",
             "    let n = fs.no_such()\n",
             "unknown fs member 'no_such' (functions: read_file, write_file, "
             "size, exists, remove, remove_file, is_dir, is_file, "
             "create_dir, create_dir_all, copy, rename, read_dir)"),
            ("rej_fs_readfile_zero.vl",
             "    let n = fs.read_file()\n",
             "fs.read_file expects exactly 1 argument: (string path)"),
            ("rej_fs_readfile_two.vl",
             "    let n = fs.read_file(\"a\", \"b\")\n",
             "fs.read_file expects exactly 1 argument: (string path)"),
            ("rej_fs_writefile_one.vl",
             "    let n = fs.write_file(\"a\")\n",
             "fs.write_file expects exactly 2 arguments: (string path, string contents)"),
            ("rej_fs_copy_one.vl",
             "    let n = fs.copy(\"a\")\n",
             "fs.copy expects exactly 2 arguments: (string src, string dst)"),
            ("rej_fs_rename_zero.vl",
             "    let n = fs.rename()\n",
             "fs.rename expects exactly 2 arguments: (string src, string dst)"),
            ("rej_fs_readfile_int.vl",
             "    let n = fs.read_file(1)\n",
             "fs.read_file expects string arguments (got i32)"),
            ("rej_fs_writefile_int.vl",
             "    let n = fs.write_file(\"a\", 2)\n",
             "fs.write_file expects string arguments (got i32)"),
            ("rej_fs_copy_int.vl",
             "    let n = fs.copy(1, \"b\")\n",
             "fs.copy expects string arguments (got i32)"),
            ("rej_fs_exists_bool.vl",
             "    let n = fs.exists(true)\n",
             "fs.exists expects string arguments (got bool)"),
            ("rej_fs_isdir_float.vl",
             "    let n = fs.is_dir(1.5)\n",
             "fs.is_dir expects string arguments (got f32)"),
            ("rej_fs_size_zero.vl",
             "    let n = fs.size()\n",
             "fs.size expects exactly 1 argument: (string path)"),
        ]
        for name, body, wording in rows:
            with self.subTest(row=name):
                src = header + body + "    return 0\n}\n"
                outs = check_program(name, src)
                self.assertEqual(outs[0], wording, f"stage 1 wording for {name}: {outs[0]!r}")
                self.assertEqual(outs[0], outs[1], f"stages disagree for {name}")

    def test_rejects_property_lane(self):
        header = "use sys.io\nuse sys.fs\nact main() -> i32 {\n"
        funcs = ("read_file, write_file, size, exists, remove, remove_file, "
                 "is_dir, is_file, create_dir, create_dir_all, copy, rename, "
                 "read_dir")
        src_fn = header + "    let x = fs.exists\n" + "    return 0\n}\n"
        outs = check_program("rej_fs_bare_fn.vl", src_fn)
        self.assertEqual(
            outs[0],
            f"unknown fs constant 'exists' (fs functions are: {funcs})"
            " (functions need parens: fs.exists())")
        self.assertEqual(outs[0], outs[1])
        src_c = header + "    let x = fs.SEPARATOR\n" + "    return 0\n}\n"
        outs = check_program("rej_fs_unknown_const.vl", src_c)
        self.assertEqual(
            outs[0],
            f"unknown fs constant 'SEPARATOR' (fs functions are: {funcs})")
        self.assertEqual(outs[0], outs[1])


def read_dir_program() -> str:
    """The two-entry listing: count-pinned + set-membership-pinned (the
    platform listing order is filesystem-defined — contains over a joined
    subject, never sequence)."""
    return """use sys.io
use sys.fs

act main() -> i32 {
    let tag: string = fs.read_file(".velo_cache/fs54_tag.txt")
    let dir = str.concat(".velo_cache/fs54_list_", tag)
    let made = fs.create_dir(dir)
    let fa = str.concat(dir, "/alpha.txt")
    let fb = str.concat(dir, "/beta.bin")
    if fs.write_file(fa, "A") {
        io.println("fa ok")
    } else {
        io.println("fa bad")
    }
    if fs.write_file(fb, "B") {
        io.println("fb ok")
    } else {
        io.println("fb bad")
    }
    let names = fs.read_dir(dir)
    let c: usize = names.len
    if c == 2 {
        io.println("count ok")
    } else {
        io.println("count bad")
    }
    let a0: string = names[0]
    let a1: string = names[1]
    let joined = str.concat(a0, str.concat("|", a1))
    let hasa = str.contains(joined, "alpha")
    let hasb = str.contains(joined, "beta")
    if hasa {
        io.println("alpha ok")
    } else {
        io.println("alpha bad")
    }
    if hasb {
        io.println("beta ok")
    } else {
        io.println("beta bad")
    }
    return 0
}
"""


READ_DIR_LINES = ["fa ok", "fb ok", "count ok", "alpha ok", "beta ok"]


def lone_program() -> str:
    """Single-entry listing: the pinned name rides the lone element."""
    return """use sys.io
use sys.fs

act main() -> i32 {
    let tag: string = fs.read_file(".velo_cache/fs54_tag.txt")
    let dir = str.concat(".velo_cache/fs54_one_", tag)
    let made = fs.create_dir(dir)
    let fl = str.concat(dir, "/only.txt")
    if fs.write_file(fl, "") {
        io.println("seed ok")
    } else {
        io.println("seed bad")
    }
    let names = fs.read_dir(dir)
    let c: usize = names.len
    if c == 1 {
        io.println("count ok")
    } else {
        io.println("count bad")
    }
    let e0: string = names[0]
    if str.contains(e0, "only.txt") {
        io.println("exact ok")
    } else {
        io.println("exact bad")
    }
    return 0
}
"""


LONE_LINES = ["seed ok", "count ok", "exact ok"]


def edge_program() -> str:
    """The documented edge contract: empty dir lists zero; a missing dir
    yields an empty shelf too (pair with is_dir for the distinction)."""
    return """use sys.io
use sys.fs

act main() -> i32 {
    let tag: string = fs.read_file(".velo_cache/fs54_tag.txt")
    let fresh = str.concat(".velo_cache/fs54_empty_", tag)
    let made = fs.create_dir(fresh)
    let e = fs.read_dir(fresh)
    let ce: usize = e.len
    if ce == 0 {
        io.println("empty ok")
    } else {
        io.println("empty bad")
    }
    let gone = str.concat(".velo_cache/fs54_absent_", tag)
    let names = fs.read_dir(gone)
    let c: usize = names.len
    if c == 0 {
        io.println("missing ok")
    } else {
        io.println("missing bad")
    }
    let nope = fs.is_dir(gone)
    if nope {
        io.println("isdir bad")
    } else {
        io.println("isdir ok")
    }
    return 0
}
"""


EDGE_LINES = ["empty ok", "missing ok", "isdir ok"]


class TestFsSlice3(unittest.TestCase):
    """gaps.md 5.4 slice 3 — fs.read_dir -> shelf[string]: the platform
    iteration split (CRT _findfirst on Windows / dirent.h on POSIX),
    names-only "." / ".."-filtered listings, empty-on-failure contract,
    order-independent battery pins."""

    def test_accepts_two_entry_listing(self):
        _write_tag()
        s1 = run_stage("stage1", read_dir_program(), "fs_read_dir_two")
        _write_tag()
        s2 = run_stage("stage2", read_dir_program(), "fs_read_dir_two")
        self.assertEqual(s1.returncode, 0, s1.stderr[-3000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-3000:])
        out1 = s1.stdout.replace("\r\n", "\n")
        out2 = s2.stdout.replace("\r\n", "\n")
        self.assertEqual(out1, out2, "sys.fs read_dir outputs diverged")
        self.assertEqual(out1.strip().splitlines(), READ_DIR_LINES)

    def test_accepts_single_entry_listing(self):
        _write_tag()
        s1 = run_stage("stage1", lone_program(), "fs_read_dir_one")
        _write_tag()
        s2 = run_stage("stage2", lone_program(), "fs_read_dir_one")
        self.assertEqual(s1.returncode, 0, s1.stderr[-3000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-3000:])
        out1 = s1.stdout.replace("\r\n", "\n")
        out2 = s2.stdout.replace("\r\n", "\n")
        self.assertEqual(out1, out2, "sys.fs single-entry outputs diverged")
        self.assertEqual(out1.strip().splitlines(), LONE_LINES)

    def test_accepts_empty_and_missing_dirs(self):
        _write_tag()
        s1 = run_stage("stage1", edge_program(), "fs_read_dir_edges")
        _write_tag()
        s2 = run_stage("stage2", edge_program(), "fs_read_dir_edges")
        self.assertEqual(s1.returncode, 0, s1.stderr[-3000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-3000:])
        out1 = s1.stdout.replace("\r\n", "\n")
        out2 = s2.stdout.replace("\r\n", "\n")
        self.assertEqual(out1, out2, "sys.fs edge outputs diverged")
        self.assertEqual(out1.strip().splitlines(), EDGE_LINES)

    def test_rejects_read_dir_surface(self):
        header = "use sys.io\nuse sys.fs\nact main() -> i32 {\n"
        funcs = ("read_file, write_file, size, exists, remove, remove_file, "
                 "is_dir, is_file, create_dir, create_dir_all, copy, rename, "
                 "read_dir")
        rows = [
            ("rej_fs_readdir_unknown.vl",
             "    let n = fs.no_such()\n",
             f"unknown fs member 'no_such' (functions: {funcs})"),
            ("rej_fs_readdir_zero.vl",
             "    let n = fs.read_dir()\n",
             "fs.read_dir expects exactly 1 argument: (string path)"),
            ("rej_fs_readdir_int.vl",
             "    let n = fs.read_dir(1)\n",
             "fs.read_dir expects string arguments (got i32)"),
        ]
        for name, body, wording in rows:
            with self.subTest(row=name):
                src = header + body + "    return 0\n}\n"
                outs = check_program(name, src)
                self.assertEqual(outs[0], wording, f"stage 1 wording for {name}: {outs[0]!r}")
                self.assertEqual(outs[0], outs[1], f"stages disagree for {name}")
        # the bare-read hint names read_dir itself
        src = header + "    let x = fs.read_dir\n" + "    return 0\n}\n"
        outs = check_program("rej_fs_readdir_bare.vl", src)
        self.assertEqual(
            outs[0],
            f"unknown fs constant 'read_dir' (fs functions are: {funcs})"
            " (functions need parens: fs.read_dir())")
        self.assertEqual(outs[0], outs[1])
