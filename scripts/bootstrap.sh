#!/usr/bin/env bash
set -euo pipefail

echo "[Velo] Bootstrapping Velo Native Compiler from bootstrap.c..."
mkdir -p bin

CC_BIN=""
if command -v gcc >/dev/null 2>&1; then
    CC_BIN="gcc"
elif command -v clang >/dev/null 2>&1; then
    CC_BIN="clang"
elif command -v cc >/dev/null 2>&1; then
    CC_BIN="cc"
else
    echo "[Velo Error] No C compiler (gcc, clang, cc) found in PATH." >&2
    exit 1
fi

echo "[Velo] Using $CC_BIN to compile bootstrap.c..."
$CC_BIN -O2 -std=c99 -I runtime -I velo/runtime bootstrap.c -o bin/velo -lm
echo "[Velo] Successfully bootstrapped bin/velo from bootstrap.c!"
./bin/velo version

