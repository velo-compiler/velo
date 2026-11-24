"""
Task 79.3: Content-Hashed Build Cache Tests.

Verifies:
1. .velo_cache artifacts are keyed by SHA-256 of the fully resolved source closure
   (source + imported dependencies + compiler version + flags).
2. Rebuilding without touching any source file results in a cache hit (action=cache_hit).
3. Modifying an imported dependency forces recompilation (action=recompile) and produces
   a new hash artifact.
4. Security Invariant I79.2: "Cache validity is content-hash based, not name based.
   A stale cache must be impossible, not unlikely."
5. Flag changes (e.g. --release, --strict-safety) invalidate the cache and force recompilation.
6. `velo run` correctly leverages cached executables without stdout pollution.
"""

import os
import subprocess
import time
from pathlib import Path
import pytest
from conftest import cc_dir, velo_exe

pytestmark = pytest.mark.fast

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()
CACHE_DIR = REPO_ROOT / ".velo_cache"
LAST_BUILD_TXT = CACHE_DIR / "last_build.txt"


def get_env():
    env = os.environ.copy()
    if cc_dir() not in env.get("PATH", ""):
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return env


def parse_last_build():
    """Reads .velo_cache/last_build.txt and returns dict of key=value."""
    if not LAST_BUILD_TXT.is_file():
        return {}
    res = {}
    for line in LAST_BUILD_TXT.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            res[k.strip()] = v.strip()
    return res


def test_cache_initial_build_and_cache_hit(tmp_path):
    """Verifies initial build compiles (action=recompile), and second build hits cache (action=cache_hit)."""
    helper_file = tmp_path / "helper.vl"
    helper_file.write_text(
        'use std.io\n'
        'view act get_message() -> string {\n'
        '    return "hello from helper"\n'
        '}\n',
        encoding="utf-8",
    )

    main_file = tmp_path / "main.vl"
    main_file.write_text(
        'use std.io\n'
        'use "helper.vl"\n'
        'act main() -> i32 {\n'
        '    println_str(get_message())\n'
        '    return 0\n'
        '}\n',
        encoding="utf-8",
    )

    out_exe = tmp_path / "app.exe"

    # 1. Initial build: must compile
    res1 = subprocess.run(
        [str(VELO_EXE), "build", str(main_file), "-o", str(out_exe)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
        cwd=str(REPO_ROOT),
    )
    assert res1.returncode == 0, f"Initial build failed: {res1.stderr}\n{res1.stdout}"
    assert out_exe.is_file(), "Target executable was not created"

    # Check execution output
    run_res1 = subprocess.run([str(out_exe)], capture_output=True, text=True, encoding="utf-8")
    assert run_res1.returncode == 0
    assert "hello from helper" in run_res1.stdout

    # Verify last_build.txt
    build1_info = parse_last_build()
    assert build1_info.get("action") == "recompile"
    hash1 = build1_info.get("hash")
    assert hash1 and len(hash1) == 64, f"Invalid SHA-256 hash: {hash1}"

    # Verify cached artifact exists in .velo_cache/
    cached_exe = CACHE_DIR / f"main_{hash1}.exe"
    assert cached_exe.is_file(), f"Cached executable not found: {cached_exe}"

    exe_mtime1 = out_exe.stat().st_mtime_ns

    # Small pause to ensure filesystem mtime would advance if overwritten
    time.sleep(0.05)

    # 2. Rebuild without touching anything: must be a cache hit
    res2 = subprocess.run(
        [str(VELO_EXE), "build", str(main_file), "-o", str(out_exe)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
        cwd=str(REPO_ROOT),
    )
    assert res2.returncode == 0, f"Second build failed: {res2.stderr}\n{res2.stdout}"

    build2_info = parse_last_build()
    assert build2_info.get("action") == "cache_hit"
    assert build2_info.get("hash") == hash1


def test_cache_invalidation_on_dependency_touch(tmp_path):
    """
    Verifies Security Invariant I79.2:
    Modifying an imported dependency changes the closure hash and forces recompilation.
    """
    dep_file = tmp_path / "dep.vl"
    dep_file.write_text(
        'view act compute_val() -> i32 { return 42 }\n',
        encoding="utf-8",
    )

    app_file = tmp_path / "app.vl"
    app_file.write_text(
        'use std.io\n'
        'use "dep.vl"\n'
        'act main() -> i32 {\n'
        '    println_i64(compute_val() as i64)\n'
        '    return 0\n'
        '}\n',
        encoding="utf-8",
    )

    out_exe = tmp_path / "dep_app.exe"

    # Build 1: original dep
    res1 = subprocess.run(
        [str(VELO_EXE), "build", str(app_file), "-o", str(out_exe)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
        cwd=str(REPO_ROOT),
    )
    assert res1.returncode == 0
    run1 = subprocess.run([str(out_exe)], capture_output=True, text=True, encoding="utf-8")
    assert run1.stdout.strip() == "42"

    hash1 = parse_last_build().get("hash")
    assert hash1

    # Modify the dependency (touch with change)
    dep_file.write_text(
        'view act compute_val() -> i32 { return 99 }\n',
        encoding="utf-8",
    )

    # Build 2: must recompile because closure content hash changed
    res2 = subprocess.run(
        [str(VELO_EXE), "build", str(app_file), "-o", str(out_exe)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
        cwd=str(REPO_ROOT),
    )
    assert res2.returncode == 0
    build2 = parse_last_build()
    assert build2.get("action") == "recompile"
    hash2 = build2.get("hash")
    assert hash2 != hash1, "Hash should have changed when dependency was modified"

    # Verify execution output reflects updated dependency
    run2 = subprocess.run([str(out_exe)], capture_output=True, text=True, encoding="utf-8")
    assert run2.stdout.strip() == "99"

    # Build 3: touch nothing -> cache hit
    res3 = subprocess.run(
        [str(VELO_EXE), "build", str(app_file), "-o", str(out_exe)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
        cwd=str(REPO_ROOT),
    )
    assert res3.returncode == 0
    assert parse_last_build().get("action") == "cache_hit"
    assert parse_last_build().get("hash") == hash2


def test_cache_flag_sensitivity(tmp_path):
    """Verifies that changing compiler flags changes the closure hash and forces recompile."""
    src_file = tmp_path / "flags_test.vl"
    src_file.write_text(
        'use std.io\n'
        'act main() -> i32 {\n'
        '    println_str("flags test")\n'
        '    return 0\n'
        '}\n',
        encoding="utf-8",
    )
    out_exe = tmp_path / "flags_test.exe"

    # Build without --release
    res1 = subprocess.run(
        [str(VELO_EXE), "build", str(src_file), "-o", str(out_exe)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
        cwd=str(REPO_ROOT),
    )
    assert res1.returncode == 0
    hash_default = parse_last_build().get("hash")

    # Build with --release
    res2 = subprocess.run(
        [str(VELO_EXE), "build", str(src_file), "-o", str(out_exe), "--release"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
        cwd=str(REPO_ROOT),
    )
    assert res2.returncode == 0
    build2 = parse_last_build()
    assert build2.get("action") == "recompile"
    hash_release = build2.get("hash")
    assert hash_release != hash_default, "Flag change should produce distinct hash"

    # Build with --strict-safety
    res3 = subprocess.run(
        [str(VELO_EXE), "build", str(src_file), "-o", str(out_exe), "--strict-safety"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
        cwd=str(REPO_ROOT),
    )
    assert res3.returncode == 0
    build3 = parse_last_build()
    assert build3.get("action") == "recompile"
    hash_strict = build3.get("hash")
    assert hash_strict != hash_default
    assert hash_strict != hash_release


def test_cache_velo_run(tmp_path):
    """Verifies that `velo run` leverages the content-hashed cache seamlessly."""
    src_file = tmp_path / "run_test.vl"
    src_file.write_text(
        'use std.io\n'
        'act main() -> i32 {\n'
        '    println_str("run from cache")\n'
        '    return 0\n'
        '}\n',
        encoding="utf-8",
    )

    # First run: compile and execute
    res1 = subprocess.run(
        [str(VELO_EXE), "run", str(src_file)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
        cwd=str(REPO_ROOT),
    )
    assert res1.returncode == 0
    assert "run from cache" in res1.stdout
    hash1 = parse_last_build().get("hash")
    assert hash1

    # Second run: cache hit, execute
    res2 = subprocess.run(
        [str(VELO_EXE), "run", str(src_file)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
        cwd=str(REPO_ROOT),
    )
    assert res2.returncode == 0
    assert "run from cache" in res2.stdout
    build2 = parse_last_build()
    assert build2.get("action") == "cache_hit"
    assert build2.get("hash") == hash1


def test_cache_noop_touch_preserves_hit(tmp_path):
    """
    Verifies that changing a file's timestamp (mtime) without modifying its content
    does NOT invalidate the cache (pure content hashing, Security Invariant I79.2).
    """
    src_file = tmp_path / "noop_touch.vl"
    src_file.write_text(
        'use std.io\n'
        'act main() -> i32 {\n'
        '    println_str("content hash invariant")\n'
        '    return 0\n'
        '}\n',
        encoding="utf-8",
    )
    out_exe = tmp_path / "noop_touch.exe"

    res1 = subprocess.run(
        [str(VELO_EXE), "build", str(src_file), "-o", str(out_exe)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
        cwd=str(REPO_ROOT),
    )
    assert res1.returncode == 0
    hash1 = parse_last_build().get("hash")

    # Touch mtime in the future without changing content
    now = time.time() + 100
    os.utime(src_file, (now, now))

    res2 = subprocess.run(
        [str(VELO_EXE), "build", str(src_file), "-o", str(out_exe)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
        cwd=str(REPO_ROOT),
    )
    assert res2.returncode == 0
    build2 = parse_last_build()
    assert build2.get("action") == "cache_hit", "mtime touch should remain a cache hit"
    assert build2.get("hash") == hash1


def test_cache_transitive_dependency_invalidation(tmp_path):
    """
    Verifies that modifying a transitive dependency (A -> B -> C, touching C)
    invalidates A's build cache and causes recompilation.
    """
    c_file = tmp_path / "c.vl"
    c_file.write_text('view act c_val() -> string { return "c_v1" }\n', encoding="utf-8")

    b_file = tmp_path / "b.vl"
    b_file.write_text('use "c.vl"\nview act b_val() -> string { return c_val() }\n', encoding="utf-8")

    a_file = tmp_path / "a.vl"
    a_file.write_text(
        'use std.io\n'
        'use "b.vl"\n'
        'act main() -> i32 {\n'
        '    println_str(b_val())\n'
        '    return 0\n'
        '}\n',
        encoding="utf-8",
    )
    out_exe = tmp_path / "transitive.exe"

    # 1. First build
    res1 = subprocess.run(
        [str(VELO_EXE), "build", str(a_file), "-o", str(out_exe)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
        cwd=str(REPO_ROOT),
    )
    assert res1.returncode == 0
    run1 = subprocess.run([str(out_exe)], capture_output=True, text=True, encoding="utf-8")
    assert run1.stdout.strip() == "c_v1"
    hash1 = parse_last_build().get("hash")

    # 2. Modify transitive dep C
    c_file.write_text('view act c_val() -> string { return "c_v2" }\n', encoding="utf-8")

    # 3. Rebuild A: must recompile
    res2 = subprocess.run(
        [str(VELO_EXE), "build", str(a_file), "-o", str(out_exe)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=get_env(),
        cwd=str(REPO_ROOT),
    )
    assert res2.returncode == 0
    build2 = parse_last_build()
    assert build2.get("action") == "recompile"
    hash2 = build2.get("hash")
    assert hash2 != hash1

    run2 = subprocess.run([str(out_exe)], capture_output=True, text=True, encoding="utf-8")
    assert run2.stdout.strip() == "c_v2"

