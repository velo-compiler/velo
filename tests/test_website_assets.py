#!/usr/bin/env python3
"""Task 84.4: Test suite for website assets and distribution integrity.

Verifies:
  1. All brand and icon assets in website/public and website/src/components exist
     and are valid non-empty files.
  2. `website/public/bootstrap.c` exists and matches the root `bootstrap.c`
     SHA-256 hash bit-for-bit.
  3. Distribution archives (`velo-std.zip`, `velo-std.tar.gz`) exist in website/public.
  4. `git status --short website/` reports no untracked files.
"""

import hashlib
import shutil
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WEBSITE_DIR = REPO_ROOT / "website"
PUBLIC_DIR = WEBSITE_DIR / "public"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_website_brand_and_component_assets_exist():
    """Verify all website visual, logo, and component assets exist."""
    required_assets = [
        PUBLIC_DIR / "apple-touch-icon.png",
        PUBLIC_DIR / "favicon.ico",
        PUBLIC_DIR / "favicon.svg",
        PUBLIC_DIR / "velo-horizontal.svg",
        PUBLIC_DIR / "velo-logo.svg",
        WEBSITE_DIR / "src" / "components" / "VeloLogo.tsx",
    ]
    for asset in required_assets:
        assert asset.exists(), f"Required asset missing: {asset}"
        assert asset.stat().st_size > 0, f"Asset is empty: {asset}"


def test_website_bootstrap_c_matches_canonical_root():
    """Verify website/public/bootstrap.c matches root bootstrap.c bit-for-bit."""
    root_bootstrap = REPO_ROOT / "bootstrap.c"
    web_bootstrap = PUBLIC_DIR / "bootstrap.c"
    
    assert root_bootstrap.exists(), "Root bootstrap.c is missing"
    assert web_bootstrap.exists(), "website/public/bootstrap.c is missing"
    
    root_hash = file_sha256(root_bootstrap)
    web_hash = file_sha256(web_bootstrap)
    
    assert root_hash == web_hash, (
        f"Hash mismatch: root bootstrap.c ({root_hash}) != "
        f"website/public/bootstrap.c ({web_hash})"
    )


def test_website_distribution_archives():
    """Verify standard library distribution archives exist in website/public."""
    zip_archive = PUBLIC_DIR / "velo-std.zip"
    tar_archive = PUBLIC_DIR / "velo-std.tar.gz"
    
    assert zip_archive.exists(), "website/public/velo-std.zip is missing"
    assert zip_archive.stat().st_size > 10000, "velo-std.zip is unexpectedly small"
    
    assert tar_archive.exists(), "website/public/velo-std.tar.gz is missing"
    assert tar_archive.stat().st_size > 10000, "velo-std.tar.gz is unexpectedly small"


def test_website_clean_git_status():
    """Verify that git status for website/ contains no untracked files."""
    proc = subprocess.run(
        ["git", "status", "--short", "website/"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    assert proc.returncode == 0
    lines = proc.stdout.splitlines()
    untracked = [line for line in lines if line.startswith("??")]
    # Note: untracked files should be 0 once committed; if running before commit,
    # caller is expected to stage them.
    assert not untracked, f"Untracked files remain in website/: {untracked}"


def test_website_build():
    """Verify website passes TypeScript and Vite production build."""
    npm_exe = shutil.which("npm")
    if not npm_exe:
        pytest.skip("npm not available on PATH")
        
    proc = subprocess.run(
        ["npm.cmd" if subprocess.os.name == "nt" else "npm", "run", "build"],
        cwd=str(WEBSITE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=True if subprocess.os.name == "nt" else False
    )
    assert proc.returncode == 0, f"npm run build failed:\n{proc.stdout}\n{proc.stderr}"
    assert (WEBSITE_DIR / "dist" / "index.html").exists(), "dist/index.html not generated"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
