"""
Packaging script for Velo compiler and standard library distributions.
Generates website/public/velo.exe, website/public/bootstrap.c,
website/public/velo-std.zip, and website/public/velo-std.tar.gz.
"""

import os
import shutil
import zipfile
import tarfile
import hashlib

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    bin_exe = os.path.join(repo_root, "bin", "velo.exe")
    bootstrap_c = os.path.join(repo_root, "bootstrap.c")
    runtime_h = os.path.join(repo_root, "runtime", "velo_runtime.h")
    std_dir = os.path.join(repo_root, "std")
    pub_dir = os.path.join(repo_root, "website", "public")

    os.makedirs(pub_dir, exist_ok=True)

    if not os.path.isfile(bin_exe):
        raise FileNotFoundError(f"Compiler binary not found at {bin_exe}. Run bootstrap first.")
    if not os.path.isfile(bootstrap_c):
        raise FileNotFoundError(f"Bootstrap C snapshot not found at {bootstrap_c}")
    if not os.path.isfile(runtime_h):
        raise FileNotFoundError(f"Runtime header not found at {runtime_h}")

    print("=== Packaging Velo Distribution Assets ===")

    # 1. Copy velo.exe to website/public/velo.exe
    target_exe = os.path.join(pub_dir, "velo.exe")
    shutil.copy2(bin_exe, target_exe)
    print(f"--> [OK] Copied {bin_exe} -> {target_exe} ({os.path.getsize(target_exe):,} bytes)")
    print(f"    SHA-256: {sha256_file(target_exe)}")

    # 2. Copy bootstrap.c to website/public/bootstrap.c
    target_boot = os.path.join(pub_dir, "bootstrap.c")
    shutil.copy2(bootstrap_c, target_boot)
    print(f"--> [OK] Copied {bootstrap_c} -> {target_boot} ({os.path.getsize(target_boot):,} bytes)")
    print(f"    SHA-256: {sha256_file(target_boot)}")

    # 3. Create velo-std.zip
    target_zip = os.path.join(pub_dir, "velo-std.zip")
    with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add std/
        for root, _, files in os.walk(std_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, repo_root) # e.g. std/io.vl
                zf.write(full_path, rel_path.replace("\\", "/"))
        # Add runtime/velo_runtime.h and include/velo_runtime.h
        zf.write(runtime_h, "runtime/velo_runtime.h")
        zf.write(runtime_h, "include/velo_runtime.h")

    print(f"--> [OK] Created {target_zip} ({os.path.getsize(target_zip):,} bytes)")
    print(f"    SHA-256: {sha256_file(target_zip)}")

    # 4. Create velo-std.tar.gz
    target_tar = os.path.join(pub_dir, "velo-std.tar.gz")
    with tarfile.open(target_tar, "w:gz") as tf:
        tf.add(std_dir, arcname="std")
        tf.add(runtime_h, arcname="runtime/velo_runtime.h")
        tf.add(runtime_h, arcname="include/velo_runtime.h")

    print(f"--> [OK] Created {target_tar} ({os.path.getsize(target_tar):,} bytes)")
    print(f"    SHA-256: {sha256_file(target_tar)}")
    print("=== Packaging Complete ===")

if __name__ == "__main__":
    main()
