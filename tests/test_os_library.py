"""5.4 Extended File System & OS Primitives (sys.os) — slice 1 battery:
args/exit/get_env/set_env + the closed namespace.

Slice 1 ships the os scaffold and the runtime helpers (velo_os_args /
velo_os_get_env / velo_os_set_env — exit lowers directly onto C's):
`os.args()` returns the full argv as shelf[string] (argv[0] INCLUDED),
`os.get_env(key)` reads the environment (unset ⇒ owned empty string),
`os.set_env(key, val)` writes it (_putenv_s on Windows / setenv on POSIX,
bool result), and `os.exit(code)` terminates with a process code (1 int
arg, void, direct C exit — prior stdout stays intact because exit()
flushes stdio).

The nondeterminism rule (5.5 mechanic): env keys are unique to the test
and argv[0] differs per stage, so accept rows print the ROUND-TRIP value
(set then read the same key — both stages print "hello") and verdict
strings for counts; the DEEP argv coverage rides DIRECT exe invocation in
the battery (`velo run` cannot pass program args — fs.md), pinning count
and tokens byte-exactly per stage.

Every accept row runs on BOTH compiler stages; the direct-invocation and
exit rows assert per-stage behavior (the exe paths differ per stage but
the assertions are identical). Every reject row asserts the same wording
on both stages (stage 2 prefixes "semantic:line:col - " and appends its
error-count summary; the comparison strips those house wrappers, exactly
like the math/time batteries).
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

from test_allocators import run_stage, ROOT, VELO_PY, VELO_EXE


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
    normalized stderr wording once per stage."""
    tmp = Path(VELO_PY).parent / ".velo_cache"
    tmp.mkdir(exist_ok=True)
    src = tmp / src_name
    src.write_text(content, encoding="utf-8")
    outs = []
    for cmd in ([sys.executable, str(VELO_PY), "check", str(src)],
                [str(VELO_EXE), "check", str(src)]):
        res = subprocess.run(cmd, capture_output=True, timeout=180, cwd=ROOT)
        err = res.stderr.decode("utf-8", errors="replace") + res.stdout.decode("utf-8", errors="replace")
        outs.append(_strip_stageWrappers(err))
    return outs


def _build_exe(stage: str, content: str, name: str) -> Path:
    """Compiles `content` on the given stage and returns the exe path
    (test_allocators's run_stage layout: .velo_cache/<tag>/<name>.exe)."""
    tmp = Path(__file__).parent.parent / ".velo_cache" / f"os_test_{name}"
    tmp.mkdir(parents=True, exist_ok=True)
    src = tmp / f"{name}.vl"
    src.write_text(content, encoding="utf-8")
    exe = tmp / f"{name}_{stage}.exe"
    if stage == "stage1":
        cmd = [sys.executable, str(VELO_PY), "build", str(src), "-o", str(exe)]
    else:
        cmd = [str(VELO_EXE), "build", str(src), "-o", str(exe)]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT, timeout=300)
    if res.returncode != 0:
        raise AssertionError(f"{stage} build failed: {res.stderr[-2000:]}")
    if not exe.exists():
        raise AssertionError(f"{stage} build produced no exe at {exe}")
    return exe


ENV_ROUNDTRIP = """use sys.io
use sys.os

act main() -> i32 {
    let ok = os.set_env("VELO_BATTERY_S1", "hello")
    if ok {
        io.println("set ok")
    } else {
        io.println("set bad")
    }
    let back = os.get_env("VELO_BATTERY_S1")
    io.println("{back}")
    let missing = os.get_env("VELO_BATTERY_S1_ABSENT")
    io.println("missing:[{missing}]")
    return 0
}
"""

ENV_LINES = ["set ok", "hello", "missing:[]"]

ARGS_MAIN = """use sys.io
use sys.os

act main() -> i32 {
    let n = os.args()
    let c: usize = n.len
    if c >= 1 {
        io.println("args ok")
    } else {
        io.println("args bad")
    }
    let a: string = n[0]
    let alen: usize = str.len(a)
    if alen > 0 {
        io.println("first ok")
    } else {
        io.println("first bad")
    }
    return 0
}
"""

ARGS_LINES = ["args ok", "first ok"]

EXE_ARGS_MAIN = """use sys.io
use sys.os

act main() -> i32 {
    let n = os.args()
    let c: usize = n.len
    io.println("count {c}")
    let t1: string = n[1]
    let t2: string = n[2]
    io.println("tok {t1} {t2}")
    return 0
}
"""

EXIT_MAIN = """use sys.io
use sys.os

act main() -> i32 {
    io.println("before")
    os.exit(7)
    return 0
}
"""


class TestOsSlice1(unittest.TestCase):
    """gaps.md 5.4 slice 1 — sys.os scaffold: args/exit/get_env/set_env,
    closed namespace, argv plumbing on both stages."""

    def test_accepts_env_roundtrip(self):
        s1 = run_stage("stage1", ENV_ROUNDTRIP, "os_env_roundtrip")
        s2 = run_stage("stage2", ENV_ROUNDTRIP, "os_env_roundtrip")
        self.assertEqual(s1.returncode, 0, s1.stderr[-3000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-3000:])
        out1 = s1.stdout.replace("\r\n", "\n")
        out2 = s2.stdout.replace("\r\n", "\n")
        self.assertEqual(out1, out2, "sys.os env outputs diverged between stages")
        self.assertEqual(out1.strip().splitlines(), ENV_LINES)

    def test_accepts_args_verdict(self):
        s1 = run_stage("stage1", ARGS_MAIN, "os_args_main")
        s2 = run_stage("stage2", ARGS_MAIN, "os_args_main")
        self.assertEqual(s1.returncode, 0, s1.stderr[-3000:])
        self.assertEqual(s2.returncode, 0, s2.stderr[-3000:])
        out1 = s1.stdout.replace("\r\n", "\n")
        out2 = s2.stdout.replace("\r\n", "\n")
        self.assertEqual(out1, out2, "sys.os args outputs diverged")
        self.assertEqual(out1.strip().splitlines(), ARGS_LINES)

    def test_direct_invocation_custom_argv(self):
        """The deep argv rows: build the exe per stage, invoke it DIRECTLY
        with custom args, and pin the count + token bytes (`velo run`
        cannot pass program args — fs.md documents this split)."""
        exe1 = _build_exe("stage1", EXE_ARGS_MAIN, "os_exe_args")
        exe2 = _build_exe("stage2", EXE_ARGS_MAIN, "os_exe_args")
        want = "count 3\ntok alpha beta\n"
        for exe in (exe1, exe2):
            res = subprocess.run(
                [str(exe), "alpha", "beta"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120, cwd=ROOT)
            out = res.stdout.replace("\r\n", "\n")
            self.assertEqual(res.returncode, 0, res.stderr[-2000:])
            self.assertEqual(out.strip().splitlines(), want.strip().splitlines(),
                             f"argv row diverged for {exe}")

    def test_exit_code7_with_prior_output(self):
        src = EXIT_MAIN
        s1 = run_stage("stage1", src, "os_exit7")
        s2 = run_stage("stage2", src, "os_exit7")
        self.assertEqual(s1.returncode, 7, s1.stderr[-3000:])
        self.assertEqual(s2.returncode, 7, s2.stderr[-3000:])
        out1 = s1.stdout.replace("\r\n", "\n")
        out2 = s2.stdout.replace("\r\n", "\n")
        self.assertEqual(out1.strip().splitlines(), ["before"])
        self.assertEqual(out1, out2)

    def test_rejects_closed_namespace_calls(self):
        header = "use sys.io\nuse sys.os\nact main() -> i32 {\n"
        rows = [
            ("rej_os_unknown_member.vl",
             "    let n = os.nano()\n",
             "unknown os member 'nano' (functions: args, exit, get_env, set_env)"),
            ("rej_os_args_one.vl",
             "    let n = os.args(1)\n",
             "os.args expects exactly 0 arguments"),
            ("rej_os_getenv_zero.vl",
             "    let n = os.get_env()\n",
             "os.get_env expects exactly 1 argument: (string key)"),
            ("rej_os_getenv_int.vl",
             "    let n = os.get_env(1)\n",
             "os.get_env expects string arguments (got i32)"),
            ("rej_os_getenv_bool.vl",
             "    let n = os.get_env(true)\n",
             "os.get_env expects string arguments (got bool)"),
            ("rej_os_setenv_one.vl",
             "    let n = os.set_env(\"K\")\n",
             "os.set_env expects exactly 2 arguments: (string key, string val)"),
            ("rej_os_setenv_intval.vl",
             "    let n = os.set_env(\"K\", 2)\n",
             "os.set_env expects string arguments (got i32)"),
            ("rej_os_setenv_keyint.vl",
             "    let n = os.set_env(1, \"V\")\n",
             "os.set_env expects string arguments (got i32)"),
            ("rej_os_exit_zero.vl",
             "    os.exit()\n",
             "os.exit expects exactly 1 argument: (i64 code)"),
            ("rej_os_exit_string.vl",
             "    os.exit(\"x\")\n",
             "os.exit expects int arguments (got string)"),
            ("rej_os_exit_float.vl",
             "    os.exit(1.5)\n",
             "os.exit expects int arguments (got f32)"),
        ]
        for name, body, wording in rows:
            with self.subTest(row=name):
                src = header + body + "    return 0\n}\n"
                outs = check_program(name, src)
                self.assertEqual(outs[0], wording, f"stage 1 wording for {name}: {outs[0]!r}")
                self.assertEqual(outs[0], outs[1], f"stages disagree for {name}")

    def test_rejects_property_lane(self):
        header = "use sys.io\nuse sys.os\nact main() -> i32 {\n"
        src_fn = header + "    let x = os.exit\n" + "    return 0\n}\n"
        outs = check_program("rej_os_bare_fn.vl", src_fn)
        self.assertEqual(
            outs[0],
            "unknown os constant 'exit' (os functions are: args, exit, get_env, set_env)"
            " (functions need parens: os.exit())")
        self.assertEqual(outs[0], outs[1])
        src_c = header + "    let x = os.PI\n" + "    return 0\n}\n"
        outs = check_program("rej_os_unknown_const.vl", src_c)
        self.assertEqual(
            outs[0],
            "unknown os constant 'PI' (os functions are: args, exit, get_env, set_env)")
        self.assertEqual(outs[0], outs[1])
