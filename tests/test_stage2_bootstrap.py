import os
import hashlib
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
BIN_DIR = REPO_ROOT / "bin"
CACHE_DIR = REPO_ROOT / ".velo_cache"
GEN1_EXE = BIN_DIR / "velo_gen1.exe"
GEN2_EXE = BIN_DIR / "velo_gen2.exe"
GEN3_EXE = BIN_DIR / "velo_gen3.exe"
MAIN_VL = REPO_ROOT / "src" / "main.vl"

def get_env():
    env = os.environ.copy()
    if r"C:\msys64\ucrt64\bin" not in env.get("PATH", ""):
        env["PATH"] = r"C:\msys64\ucrt64\bin;" + env.get("PATH", "")
    return env

@pytest.fixture(scope="session", autouse=True)
def setup_bootstrap():
    """Ensure Generation 1, 2, and 3 are built for verification."""
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Gen 1 built from bootstrap.c using GCC (or Python compiler as fallback)
    if not GEN1_EXE.exists():
        bootstrap_c = REPO_ROOT / "bootstrap.c"
        if bootstrap_c.exists():
            env = get_env()
            gcc_cmd = [
                "gcc", "-O2", "-std=c99",
                "-I", str(REPO_ROOT / "runtime"),
                "-I", str(REPO_ROOT / "velo" / "runtime"),
                str(bootstrap_c),
                "-o", str(GEN1_EXE)
            ]
            res = subprocess.run(gcc_cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, env=env)
            assert res.returncode == 0, f"Gen1 build from bootstrap.c failed:\n{res.stderr}"
        else:
            res = subprocess.run(
                ["python", "velo.py", "build", str(MAIN_VL), "-o", str(GEN1_EXE)],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True
            )
            assert res.returncode == 0, f"Gen1 build failed:\n{res.stderr}"

    # 2. Gen 2 built from Gen 1
    if not GEN2_EXE.exists():
        res = subprocess.run(
            [str(GEN1_EXE), "build", str(MAIN_VL), "-o", str(GEN2_EXE)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=get_env()
        )
        assert res.returncode == 0, f"Gen2 build failed:\n{res.stdout}\n{res.stderr}"

    # 3. Gen 3 built from Gen 2
    if not GEN3_EXE.exists():
        res = subprocess.run(
            [str(GEN2_EXE), "build", str(MAIN_VL), "-o", str(GEN3_EXE)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=get_env()
        )
        assert res.returncode == 0, f"Gen3 build failed:\n{res.stdout}\n{res.stderr}"

def test_gen2_and_gen3_executables_exist():
    assert GEN1_EXE.exists(), "velo_gen1.exe must exist"
    assert GEN2_EXE.exists(), "velo_gen2.exe must exist"
    assert GEN3_EXE.exists(), "velo_gen3.exe must exist"

def test_triple_bootstrap_sha256_determinism():
    """Verify that Gen2 and Gen3 emit 100% bit-for-bit identical C code."""
    res2 = subprocess.run(
        [str(GEN2_EXE), "emit-c", str(MAIN_VL)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res2.returncode == 0, f"Gen2 emit-c failed:\n{res2.stderr}"

    res3 = subprocess.run(
        [str(GEN3_EXE), "emit-c", str(MAIN_VL)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res3.returncode == 0, f"Gen3 emit-c failed:\n{res3.stderr}"

    sha256_gen2 = hashlib.sha256(res2.stdout.encode("utf-8")).hexdigest()
    sha256_gen3 = hashlib.sha256(res3.stdout.encode("utf-8")).hexdigest()

    assert sha256_gen2 == sha256_gen3, (
        f"Bootstrap determinism failed!\n"
        f"Gen2 SHA256: {sha256_gen2}\n"
        f"Gen3 SHA256: {sha256_gen3}"
    )

def test_gen3_version_and_help():
    res_ver = subprocess.run(
        [str(GEN3_EXE), "version"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res_ver.returncode == 0
    assert "Velo v2.0 (Self-Hosted Native Compiler)" in res_ver.stdout

    res_help = subprocess.run(
        [str(GEN3_EXE), "help"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res_help.returncode == 0
    assert "Usage:" in res_help.stdout

def test_gen3_run_examples():
    hello_vl = REPO_ROOT / "examples" / "01_hello.vl"
    res = subprocess.run(
        [str(GEN3_EXE), "run", str(hello_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=get_env()
    )
    assert res.returncode == 0
    assert "Hello, world!!" in res.stdout
