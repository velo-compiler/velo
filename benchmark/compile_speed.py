#!/usr/bin/env python3
"""
benchmark/compile_speed.py — Compiler Build Speed & Regression Monitor (Task 81.3)

Measures clean and incremental `velo build src/main.vl` time, tracks compilation
throughput (LOC/s) per git commit, records history in benchmark/compile_speed_history.json,
and fails CI when a compile-time regression exceeds a configurable threshold (default: >20%).
"""

import sys
import os
import time
import json
import shutil
import platform
import argparse
import datetime
import subprocess
from pathlib import Path

# Ensure MSYS2 UCRT64 toolchain is in PATH if present on Windows
if os.name == 'nt':
    ucrt64_path = r"C:\msys64\ucrt64\bin"
    if os.path.isdir(ucrt64_path) and ucrt64_path not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ucrt64_path + os.pathsep + os.environ.get("PATH", "")

def get_git_commit(repo_root: Path) -> dict:
    try:
        rev = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root, capture_output=True, text=True, encoding="utf-8", timeout=5
        ).stdout.strip()
        short_rev = rev[:8] if rev else "unknown"
        msg = subprocess.run(
            ["git", "log", "-1", "--pretty=%s"],
            cwd=repo_root, capture_output=True, text=True, encoding="utf-8", timeout=5
        ).stdout.strip()
        return {"commit": rev, "short_commit": short_rev, "summary": msg}
    except Exception:
        return {"commit": "unknown", "short_commit": "unknown", "summary": ""}

def count_source_loc(src_dir: Path) -> tuple:
    vl_files = list(src_dir.rglob("*.vl"))
    total_loc = 0
    for f in vl_files:
        try:
            total_loc += len(f.read_text(encoding="utf-8", errors="replace").splitlines())
        except Exception:
            pass
    return len(vl_files), total_loc

def locate_velo_compiler(repo_root: Path) -> Path:
    ext = ".exe" if os.name == 'nt' else ""
    default_bin = repo_root / "bin" / f"velo{ext}"
    if default_bin.exists():
        return default_bin
    gen3_bin = repo_root / "bin" / f"velo_gen3{ext}"
    if gen3_bin.exists():
        return gen3_bin
    return default_bin

def run_single_build(velo_bin: Path, source_file: Path, output_bin: Path, repo_root: Path) -> float:
    t0 = time.perf_counter()
    env = os.environ.copy()
    res = subprocess.run(
        [str(velo_bin), "build", str(source_file), "-o", str(output_bin)],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    t1 = time.perf_counter()
    if res.returncode != 0:
        raise RuntimeError(f"Build failed with exit code {res.returncode}:\n{res.stderr}\n{res.stdout}")
    return t1 - t0

def measure_builds(velo_bin: Path, source_file: Path, output_bin: Path, repo_root: Path, runs: int = 1) -> tuple:
    cache_dir = repo_root / ".velo_cache"

    # 1. Clean Build: purge cache beforehand
    clean_times = []
    for _ in range(runs):
        if cache_dir.exists():
            shutil.rmtree(cache_dir, ignore_errors=True)
        if output_bin.exists():
            try:
                output_bin.unlink()
            except Exception:
                pass
        t = run_single_build(velo_bin, source_file, output_bin, repo_root)
        clean_times.append(t)

    avg_clean = sum(clean_times) / len(clean_times)

    # 2. Incremental Build: run with populated cache
    incremental_times = []
    for _ in range(runs):
        t = run_single_build(velo_bin, source_file, output_bin, repo_root)
        incremental_times.append(t)

    avg_incremental = sum(incremental_times) / len(incremental_times)

    # Clean up test output binary
    if output_bin.exists():
        try:
            output_bin.unlink()
        except Exception:
            pass

    return avg_clean, avg_incremental

def load_history(history_file: Path) -> dict:
    if history_file.exists():
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"runs": []}

def save_history(history_file: Path, data: dict):
    history_file.parent.mkdir(parents=True, exist_ok=True)
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def evaluate_regression(current_clean_sec: float, baseline_sec: float, threshold_pct: float) -> tuple:
    """
    Returns (regressed: bool, pct_diff: float, message: str)
    pct_diff is positive when slower, negative when faster.
    """
    if baseline_sec <= 0:
        return False, 0.0, f"No baseline timing available (recorded {current_clean_sec:.2f}s as initial baseline)."

    pct_diff = ((current_clean_sec - baseline_sec) / baseline_sec) * 100.0

    if pct_diff > threshold_pct:
        msg = (
            f"[REGRESSION FAILURE] Compile time regressed by +{pct_diff:.1f}% "
            f"(current: {current_clean_sec:.2f}s, baseline: {baseline_sec:.2f}s, threshold: +{threshold_pct:.1f}%)"
        )
        return True, pct_diff, msg
    else:
        status_word = f"+{pct_diff:.1f}%" if pct_diff >= 0 else f"{pct_diff:.1f}%"
        msg = (
            f"[PASS] Compile time within threshold: {status_word} "
            f"(current: {current_clean_sec:.2f}s, baseline: {baseline_sec:.2f}s, threshold: +{threshold_pct:.1f}%)"
        )
        return False, pct_diff, msg

def main():
    parser = argparse.ArgumentParser(description="Velo Compile Speed & Regression Gate (Task 81.3)")
    parser.add_argument("--source", type=str, default="src/main.vl", help="Entry point to build (default: src/main.vl)")
    parser.add_argument("--history-file", type=str, default="benchmark/compile_speed_history.json", help="Path to history JSON file")
    parser.add_argument("--runs", type=int, default=1, help="Number of benchmark runs to average (default: 1)")
    parser.add_argument("--check-regression", action="store_true", help="Fail with exit 1 if clean build time regressed by > threshold")
    parser.add_argument("--threshold", type=float, default=20.0, help="Regression percentage threshold (default: 20.0%%)")
    parser.add_argument("--baseline-sec", type=float, default=None, help="Explicit baseline clean build time in seconds")
    parser.add_argument("--baseline-commit", type=str, default=None, help="Specific commit in history to compare against")
    parser.add_argument("--no-record", action="store_true", help="Do not persist results to history JSON file")
    parser.add_argument("--quick", action="store_true", help="Quick mode (single measurement run)")
    parser.add_argument("--mock-clean-sec", type=float, default=None, help="Mock clean build seconds for test verification")
    parser.add_argument("--mock-incremental-sec", type=float, default=None, help="Mock incremental build seconds for test verification")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    source_path = repo_root / args.source
    history_path = repo_root / args.history_file
    ext = ".exe" if os.name == 'nt' else ""
    output_bin = repo_root / "bin" / f"velo_compile_speed_tmp{ext}"

    velo_bin = locate_velo_compiler(repo_root)
    git_info = get_git_commit(repo_root)
    file_count, total_loc = count_source_loc(repo_root / "src")

    print("=" * 78)
    print(" ⏱️  Velo Compiler Speed Benchmark (Task 81.3)")
    print(f" Target: {args.source} ({file_count} source files, {total_loc:,} lines)")
    print(f" Commit: {git_info['short_commit']} - {git_info['summary']}")
    print(f" Platform: {platform.system()} {platform.machine()} ({os.cpu_count()} cores)")
    print("=" * 78)

    # Timing measurement
    if args.mock_clean_sec is not None:
        clean_sec = args.mock_clean_sec
        incr_sec = args.mock_incremental_sec if args.mock_incremental_sec is not None else 0.5
        print(f"\n[Mock Mode] clean={clean_sec:.2f}s, incremental={incr_sec:.2f}s")
    else:
        if not velo_bin.exists():
            print(f"[Error] Velo compiler binary not found at {velo_bin}.")
            sys.exit(1)
        runs = 1 if args.quick else args.runs
        print(f"\nMeasuring clean & incremental builds ({runs} run{'s' if runs > 1 else ''})...")
        clean_sec, incr_sec = measure_builds(velo_bin, source_path, output_bin, repo_root, runs=runs)

    clean_throughput = (total_loc / clean_sec) if clean_sec > 0 else 0
    incr_throughput = (total_loc / incr_sec) if incr_sec > 0 else 0

    print("\n--- Compile Speed Results ---")
    print(f" Clean Build Time:       {clean_sec:6.2f} s  ({clean_throughput:8.1f} LOC/s)")
    print(f" Incremental Build Time: {incr_sec:6.2f} s  ({incr_throughput:8.1f} LOC/s)")
    speedup = clean_sec / incr_sec if incr_sec > 0 else 1.0
    print(f" Cache Speedup Ratio:    {speedup:6.1f}x faster incremental build")

    # Load history and determine baseline
    history = load_history(history_path)
    baseline_sec = args.baseline_sec

    if baseline_sec is None:
        if args.baseline_commit:
            for entry in history.get("runs", []):
                if entry.get("commit", "").startswith(args.baseline_commit):
                    baseline_sec = entry.get("clean_sec")
                    break
        elif history.get("runs"):
            # Compare against the most recent historical run with a different commit or last entry
            for entry in reversed(history["runs"]):
                if entry.get("commit") != git_info["commit"]:
                    baseline_sec = entry.get("clean_sec")
                    break
            if baseline_sec is None and history["runs"]:
                baseline_sec = history["runs"][-1].get("clean_sec")

    # Evaluate regression
    regressed = False
    if baseline_sec is not None:
        regressed, pct_diff, eval_msg = evaluate_regression(clean_sec, baseline_sec, args.threshold)
        print(f"\n{eval_msg}")
    else:
        print(f"\n[Info] Establishing initial baseline compile time: {clean_sec:.2f}s")

    # Record history if not disabled
    if not args.no_record:
        entry = {
            "commit": git_info["commit"],
            "short_commit": git_info["short_commit"],
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "clean_sec": round(clean_sec, 2),
            "incremental_sec": round(incr_sec, 2),
            "total_loc": total_loc,
            "clean_loc_per_sec": round(clean_throughput, 1),
            "incremental_loc_per_sec": round(incr_throughput, 1),
            "platform": f"{platform.system()} {platform.machine()}"
        }
        # Update or append
        existing = [i for i, r in enumerate(history.get("runs", [])) if r.get("commit") == git_info["commit"]]
        if existing:
            history["runs"][existing[0]] = entry
        else:
            history.setdefault("runs", []).append(entry)
        save_history(history_path, history)
        print(f"[Record] Saved compile speed record to {args.history_file}")

    print("=" * 78)

    if args.check_regression and regressed:
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
