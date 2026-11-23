"""
Showcase verification tests (Phase 83 / Task 83.3).

Validates that all real-world showcase games and applications in `games/` and `apps/`
remain fully compatible with the compiler, type checker, and C codegen pipeline:

1. games/flappy_bird (2D arcade game with Raylib 6.0 C-FFI)
2. games/survivors (2D horde survival game with swarming AI and zone memory)
3. games/velocraft (3D voxel engine with procedural generation)
4. apps/velokv (Redis-compatible in-memory KV database with RESP & AOF)
5. apps/velostudio (SQLite GUI database studio with Raylib)
"""

import subprocess
from pathlib import Path

import pytest
from conftest import cc_env, velo_exe

REPO_ROOT = Path(__file__).resolve().parent.parent

SHOWCASE_TARGETS = [
    ("games/flappy_bird/game.vl", "flappy_bird"),
    ("games/survivors/main.vl", "survivors"),
    ("games/velocraft/main.vl", "velocraft"),
    ("apps/velokv/main.vl", "velokv"),
    ("apps/velokv/test_velokv.vl", "velokv_test"),
    ("apps/velostudio/main.vl", "velostudio"),
    ("apps/velostudio/test_velostudio.vl", "velostudio_test"),
]


def _run_cmd(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
        env=cc_env(),
        timeout=25.0,
    )


@pytest.mark.parametrize("rel_path,label", SHOWCASE_TARGETS, ids=[t[1] for t in SHOWCASE_TARGETS])
def test_showcase_check(rel_path: str, label: str):
    exe = velo_exe()
    if not exe.exists():
        pytest.skip(f"Compiler binary {exe} not found")

    src = REPO_ROOT / rel_path
    assert src.exists(), f"Showcase source {src} not found on disk"

    proc = _run_cmd([str(exe), "check", str(src)], cwd=REPO_ROOT)
    assert proc.returncode == 0, f"Check failed for {rel_path}:\n{proc.stdout}\n{proc.stderr}"
    assert "[Velo] Check passed" in proc.stdout


@pytest.mark.parametrize("rel_path,label", SHOWCASE_TARGETS, ids=[f"{t[1]}_emit" for t in SHOWCASE_TARGETS])
def test_showcase_emit_c(rel_path: str, label: str, tmp_path: Path):
    exe = velo_exe()
    if not exe.exists():
        pytest.skip(f"Compiler binary {exe} not found")

    src = REPO_ROOT / rel_path
    assert src.exists(), f"Showcase source {src} not found on disk"

    out_c = tmp_path / f"{label}.c"
    proc = _run_cmd([str(exe), "emit-c", str(src), "-o", str(out_c)], cwd=REPO_ROOT)
    assert proc.returncode == 0, f"Emit-c failed for {rel_path}:\n{proc.stdout}\n{proc.stderr}"
    assert out_c.exists(), f"Output C file {out_c} was not created"
    assert out_c.stat().st_size > 0, f"Output C file {out_c} is empty"
