#!/usr/bin/env bash
set -euo pipefail

# Scripts directory and repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

FULL_BOOTSTRAP=1
if [[ "${1:-}" == "--quick" || "${1:-}" == "-q" ]]; then
    FULL_BOOTSTRAP=0
elif [[ "${1:-}" == "--full" || "${1:-}" == "-f" ]]; then
    FULL_BOOTSTRAP=1
fi

echo "[Velo] Bootstrapping Velo Native Compiler from bootstrap.c..."
mkdir -p bin

CC_BIN="${CC:-}"
if [[ -z "${CC_BIN}" ]]; then
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
fi

echo "[Velo] Using ${CC_BIN} to compile bootstrap.c..."
${CC_BIN} -O2 -std=c99 -I runtime -I velo/runtime bootstrap.c -o bin/velo -lm -lpthread
chmod +x bin/velo
ln -sf velo bin/velo.exe 2>/dev/null || cp bin/velo bin/velo.exe 2>/dev/null || true

echo "[Velo] Successfully bootstrapped bin/velo from bootstrap.c!"
./bin/velo version

if [[ "${FULL_BOOTSTRAP}" -eq 1 ]]; then
    echo ""
    echo "[Velo] Commencing 3-stage self-hosting verification (Gen1 -> Gen2 -> Gen3)..."

    # Stage 1 -> Gen2
    echo "[Velo] Building Gen2 compiler (bin/velo build src/main.vl -o bin/velo_gen2)..."
    ./bin/velo build src/main.vl -o bin/velo_gen2
    chmod +x bin/velo_gen2

    # Gen2 -> Gen3
    echo "[Velo] Building Gen3 compiler (bin/velo_gen2 build src/main.vl -o bin/velo_gen3)..."
    ./bin/velo_gen2 build src/main.vl -o bin/velo_gen3
    chmod +x bin/velo_gen3

    # Verify determinism between Gen2 and Gen3
    echo "[Velo] Verifying SHA-256 fixed-point determinism..."
    if command -v python3 >/dev/null 2>&1; then
        python3 scripts/check_determinism.py
    else
        python scripts/check_determinism.py
    fi

    # Canonical binary update
    cp bin/velo_gen3 bin/velo
    ln -sf velo bin/velo.exe 2>/dev/null || cp bin/velo bin/velo.exe 2>/dev/null || true
    echo "[Velo] Bootstrap complete! Canonical bin/velo is verified deterministic Gen3."
fi
