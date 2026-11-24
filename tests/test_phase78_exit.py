"""
Phase 78 Exit Criteria Verification Suite.

Validates:
1. End-to-end integration test program (`std/tests/phase78_exit_test.vl`):
   - Sort a shelf (std.coll.sort)
   - Resolve a hostname (std.net.dns)
   - Connect to it via TCP (std.net.tcp)
   - Parse a regex over the response (std.patt / std.text.regex)
   - Decompress a gzip body (std.compress.gzip)
   - Decode JSON into a strongly typed struct (std.json.codec)
   - Format a local timestamp with timezone offset (std.time.tz)
2. Fuzz corpus checked into tests/fuzz/corpus/ for all 5 new parsers introduced in Phase 78:
   - Regex parser (std.patt)
   - JSON parser / codec (std.json)
   - Streaming CSV reader (std.csv)
   - Gzip / Deflate decompressor (std.compress.gzip)
   - TZif timezone parser (std.time.tz_tzif)
3. Direct execution of all fuzz corpora through native Velo parsers (`std/tests/phase78_fuzz_test.vl`).
"""

import os
import subprocess
from pathlib import Path
import pytest
from conftest import cc_dir, velo_exe

REPO_ROOT = Path(__file__).parent.parent.resolve()
VELO_EXE = velo_exe()
CORPUS_DIR = REPO_ROOT / "tests" / "fuzz" / "corpus"


def get_env():
    env = os.environ.copy()
    if cc_dir() not in env.get("PATH", ""):
        env["PATH"] = cc_dir() + ";" + env.get("PATH", "")
    return env


def test_phase78_e2e_integration_pipeline():
    """Runs the full Phase 78 E2E pipeline program exercising all 7 components."""
    test_vl = REPO_ROOT / "std" / "tests" / "phase78_exit_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"E2E test failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: Phase 78 exit criteria fully verified" in res.stdout


def test_phase78_fuzz_corpora_execution():
    """Runs the pure-Velo fuzz runner validating all 5 parser corpora."""
    test_vl = REPO_ROOT / "std" / "tests" / "phase78_fuzz_test.vl"
    res = subprocess.run(
        [str(VELO_EXE), "run", str(test_vl)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=get_env()
    )
    assert res.returncode == 0, f"Fuzz test failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "PASS: Phase 78 fuzz corpora all verified" in res.stdout


def test_phase78_fuzz_corpus_inventory():
    """Verifies that all 5 parser corpora exist and contain valid and malformed seeds."""
    expected_parsers = {
        "regex": (10, [".txt"]),
        "json": (10, [".json"]),
        "csv": (7, [".csv"]),
        "gzip": (7, [".gz"]),
        "tzif": (5, [".tzif"]),
    }
    for parser, (min_files, exts) in expected_parsers.items():
        pdir = CORPUS_DIR / parser
        assert pdir.is_dir(), f"Missing fuzz corpus directory for {parser}: {pdir}"
        files = [f for f in pdir.iterdir() if f.is_file() and any(f.name.endswith(ext) for ext in exts)]
        assert len(files) >= min_files, f"Expected at least {min_files} corpus files for {parser}, found {len(files)}"
        # Verify both valid and malformed/corrupted files exist
        has_valid = any("valid" in f.name for f in files)
        has_malformed = any("malformed" in f.name or "corrupted" in f.name or "bad" in f.name for f in files)
        assert has_valid, f"Corpus for {parser} must contain valid seed files"
        assert has_malformed, f"Corpus for {parser} must contain malformed/corrupted seed files"


def test_phase78_step_coverage_matrix():
    """Validates that each of the 7 exit criteria steps has dedicated test coverage."""
    steps = [
        ("Step 1: std.coll.sort", REPO_ROOT / "std" / "tests" / "coll" / "sort_test.vl"),
        ("Step 2: std.net.dns", REPO_ROOT / "std" / "tests" / "net" / "dns_test.vl"),
        ("Step 3: std.net.tcp", REPO_ROOT / "std" / "tests" / "net" / "tcp_test.vl"),
        ("Step 4: std.patt", REPO_ROOT / "std" / "tests" / "patt" / "regex_test.vl"),
        ("Step 5: std.compress", REPO_ROOT / "std" / "tests" / "compress" / "compress_test.vl"),
        ("Step 6: std.json.codec", REPO_ROOT / "std" / "tests" / "json" / "codec_test.vl"),
        ("Step 7: std.time.tz", REPO_ROOT / "std" / "tests" / "time" / "tz_test.vl"),
    ]
    for step_name, test_path in steps:
        assert test_path.is_file(), f"Missing dedicated unit test for {step_name}: {test_path}"
