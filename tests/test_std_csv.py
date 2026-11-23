import os
import subprocess
import pytest
import sys
from pathlib import Path
from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()

def get_env():
    env = os.environ.copy()
    if cc_dir() not in env.get("PATH", ""):
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return env

def test_std_csv_reader():
    test_vl = REPO_ROOT / "std" / "tests" / "csv" / "reader_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "OK: std.csv reader tests passed" in res.stdout

def test_std_csv_writer():
    test_vl = REPO_ROOT / "std" / "tests" / "csv" / "writer_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "OK: std.csv writer tests passed" in res.stdout

def test_std_csv_module_import():
    test_vl = REPO_ROOT / "std" / "tests" / "csv_module_import_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: std.csv umbrella import all tests passed" in res.stdout

def test_std_csv_stream_reader():
    test_vl = REPO_ROOT / "std" / "tests" / "csv" / "stream_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"run failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "OK: std.csv stream reader tests passed" in res.stdout

def test_std_csv_streaming_1m_rows_bounded_memory(tmp_path):
    csv_file = REPO_ROOT / "scratch_1m_rows.csv"
    exe_file = tmp_path / "csv_1m.exe"

    # Generate 1,000,000 rows in chunks (~30 MB CSV)
    with open(csv_file, "w", newline="") as f:
        chunk = "".join(f"{i},alpha_{i%100},\"quoted,val_{i}\"\n" for i in range(10000))
        for _ in range(100):
            f.write(chunk)

    try:
        # Build standalone binary to measure memory exclusively of compiler
        src_vl = REPO_ROOT / "std" / "tests" / "csv" / "million_rows_test.vl"
        build_res = subprocess.run(
            [str(VELO_EXE), "build", str(src_vl), "-o", str(exe_file)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            env=get_env()
        )
        assert build_res.returncode == 0, f"build failed:\n{build_res.stderr}\n{build_res.stdout}"

        # Run binary and measure peak RSS
        proc = subprocess.Popen(
            [str(exe_file)],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace"
        )

        peak_rss_bytes = 0
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ('cb', wintypes.DWORD),
                    ('PageFaultCount', wintypes.DWORD),
                    ('PeakWorkingSetSize', ctypes.c_size_t),
                    ('WorkingSetSize', ctypes.c_size_t),
                    ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                    ('PagefileUsage', ctypes.c_size_t),
                    ('PeakPagefileUsage', ctypes.c_size_t),
                ]
            handle = int(proc._handle)
            pmc = PROCESS_MEMORY_COUNTERS()
            pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            stdout, stderr = proc.communicate()
            if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(pmc), ctypes.sizeof(pmc)):
                peak_rss_bytes = pmc.PeakWorkingSetSize
        else:
            import resource
            stdout, stderr = proc.communicate()
            usage = resource.getrusage(resource.RUSAGE_CHILDREN)
            peak_rss_bytes = usage.ru_maxrss * 1024

        assert proc.returncode == 0, f"execution failed (code {proc.returncode}):\n{stderr}\n{stdout}"
        assert "OK: processed 1000000 rows" in stdout

        # Peak RSS must be strictly below 25 MB ceiling
        peak_rss_mb = peak_rss_bytes / (1024 * 1024)
        print(f"\n[1M Rows Bounded Memory] Peak RSS: {peak_rss_mb:.2f} MB")
        if peak_rss_bytes > 0:
            assert peak_rss_mb < 25.0, f"Peak RSS exceeded 25MB: {peak_rss_mb:.2f} MB"
    finally:
        if csv_file.exists():
            csv_file.unlink()
