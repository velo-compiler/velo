import subprocess
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_PY = REPO_ROOT / "velo.py"

def run_velo_cli(args, cwd=REPO_ROOT):
    cmd = [sys.executable, str(VELO_PY)] + args
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)

def test_native_test_runner_all_pass(tmp_path):
    source = """
    test "math addition" {
        let x = 10 + 20
        assert(x == 30)
    }

    test "boolean logic" {
        assert(true)
        assert(not false)
    }
    """
    vl_file = tmp_path / "simple_test.vl"
    vl_file.write_text(source, encoding="utf-8")

    res = run_velo_cli(["test", str(vl_file)])
    assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "running 2 tests" in res.stdout
    assert 'test "math addition" ... ok' in res.stdout
    assert 'test "boolean logic" ... ok' in res.stdout
    assert "test result: ok. 2 passed; 0 failed" in res.stdout

def test_native_test_runner_assertion_failure(tmp_path):
    source = """
    test "passes first" {
        assert(1 == 1)
    }

    test "fails with message" {
        let a = 5
        let b = 10
        assert(a == b, "expected a and b to be equal")
    }

    test "runs after failure" {
        assert(2 + 2 == 4)
    }
    """
    vl_file = tmp_path / "failure_test.vl"
    vl_file.write_text(source, encoding="utf-8")

    res = run_velo_cli(["test", str(vl_file)])
    assert res.returncode != 0
    assert "running 3 tests" in res.stdout
    assert 'test "passes first" ... ok' in res.stdout
    assert 'test "fails with message" ... FAILED' in res.stdout
    assert "expected a and b to be equal" in res.stdout
    assert 'test "runs after failure" ... ok' in res.stdout
    assert "test result: FAILED. 2 passed; 1 failed" in res.stdout

def test_native_test_runner_filtering(tmp_path):
    source = """
    test "apple pie" {
        assert(true)
    }

    test "banana split" {
        assert(true)
    }

    test "apple crumble" {
        assert(true)
    }
    """
    vl_file = tmp_path / "filter_test.vl"
    vl_file.write_text(source, encoding="utf-8")

    res = run_velo_cli(["test", str(vl_file), "--filter", "apple"])
    assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "running 2 tests (1 filtered out)" in res.stdout
    assert 'test "apple pie" ... ok' in res.stdout
    assert 'test "apple crumble" ... ok' in res.stdout
    assert "banana split" not in res.stdout
    assert "test result: ok. 2 passed; 0 failed" in res.stdout

def test_native_test_runner_memory_isolation(tmp_path):
    source = """
    use sys.mem

    test "allocates in arena" {
        let p = mem.alloc(@i32, 100)
        assert(p != null)
    }

    test "arena reset verifies clean state" {
        // Memory offset was reset between tests
        let p2 = mem.alloc(@i32, 50)
        assert(p2 != null)
    }
    """
    vl_file = tmp_path / "mem_test.vl"
    vl_file.write_text(source, encoding="utf-8")

    res = run_velo_cli(["test", str(vl_file)])
    assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "test result: ok. 2 passed; 0 failed" in res.stdout

def test_production_build_strips_test_blocks(tmp_path):
    source = """
    use sys.io

    test "unit test that fails if run" {
        assert(false, "should never run in production build")
    }

    act main() -> i32 {
        io.println("production hello")
        return 0
    }
    """
    vl_file = tmp_path / "prod.vl"
    vl_file.write_text(source, encoding="utf-8")

    # Regular 'run' mode must ignore the test block and run main()
    res = run_velo_cli(["run", str(vl_file)])
    assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "production hello" in res.stdout
    assert "running" not in res.stdout

def test_assert_in_regular_code_fatal_on_failure(tmp_path):
    source = """
    act main() -> i32 {
        let x = 42
        assert(x == 99, "x is not 99")
        return 0
    }
    """
    vl_file = tmp_path / "assert_fail.vl"
    vl_file.write_text(source, encoding="utf-8")

    res = run_velo_cli(["run", str(vl_file)])
    assert res.returncode != 0
    assert "[Velo Fatal] Assertion failed" in res.stderr
    assert "x is not 99" in res.stderr
