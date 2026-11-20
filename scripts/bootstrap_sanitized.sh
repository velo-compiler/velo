#!/usr/bin/env bash
set -euo pipefail

# Scripts directory and repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

FULL_BOOTSTRAP=1
RUN_TESTS=1

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --quick|-q)
            FULL_BOOTSTRAP=0
            shift
            ;;
        --full|-f)
            FULL_BOOTSTRAP=1
            shift
            ;;
        --no-test)
            RUN_TESTS=0
            shift
            ;;
        *)
            break
            ;;
    esac
done

echo "[Velo Sanitizer] Bootstrapping Velo Native Compiler under ASan + UBSan..."
mkdir -p bin

CC_BIN="${CC:-}"
if [[ -z "${CC_BIN}" ]]; then
    if command -v clang >/dev/null 2>&1; then
        CC_BIN="clang"
    elif command -v gcc >/dev/null 2>&1; then
        CC_BIN="gcc"
    elif command -v cc >/dev/null 2>&1; then
        CC_BIN="cc"
    else
        echo "[Velo Error] No C compiler (clang, gcc, cc) found in PATH." >&2
        exit 1
    fi
fi

# Sanitizer compiler and linker flags (Task 74.6)
SANITIZER_FLAGS="-fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer -g"
SANITIZER_LDFLAGS="-fsanitize=address,undefined"

# Export sanitizer flags so all down-chain compilations invoke the sanitizers
export VELO_CFLAGS="${SANITIZER_FLAGS}"
export VELO_LDFLAGS="${SANITIZER_LDFLAGS}"
export ASAN_OPTIONS="detect_leaks=1:halt_on_error=1:abort_on_error=1"
export UBSAN_OPTIONS="halt_on_error=1:abort_on_error=1"

echo "[Velo Sanitizer] Using ${CC_BIN} with ${SANITIZER_FLAGS} to compile bootstrap.c..."
${CC_BIN} -O1 ${SANITIZER_FLAGS} -fwrapv -std=c99 -I runtime -I velo/runtime bootstrap.c -o bin/velo ${SANITIZER_LDFLAGS} -lm -lpthread
chmod +x bin/velo
ln -sf velo bin/velo.exe 2>/dev/null || cp bin/velo bin/velo.exe 2>/dev/null || true

echo "[Velo Sanitizer] Successfully bootstrapped sanitized bin/velo from bootstrap.c!"
./bin/velo version

if [[ "${FULL_BOOTSTRAP}" -eq 1 ]]; then
    echo ""
    echo "[Velo Sanitizer] Commencing 3-stage self-hosting verification (Gen1 -> Gen2 -> Gen3)..."

    # Stage 1 -> Gen2
    echo "[Velo Sanitizer] Building Gen2 compiler (bin/velo build src/main.vl -o bin/velo_gen2)..."
    ./bin/velo build src/main.vl -o bin/velo_gen2
    chmod +x bin/velo_gen2

    # Gen2 -> Gen3
    echo "[Velo Sanitizer] Building Gen3 compiler (bin/velo_gen2 build src/main.vl -o bin/velo_gen3)..."
    ./bin/velo_gen2 build src/main.vl -o bin/velo_gen3
    chmod +x bin/velo_gen3

    # Verify determinism between Gen2 and Gen3
    echo "[Velo Sanitizer] Verifying SHA-256 fixed-point determinism..."
    if command -v python3 >/dev/null 2>&1; then
        python3 scripts/check_determinism.py
    else
        python scripts/check_determinism.py
    fi

    # Canonical binary update
    cp bin/velo_gen3 bin/velo
    ln -sf velo bin/velo.exe 2>/dev/null || cp bin/velo bin/velo.exe 2>/dev/null || true
    echo "[Velo Sanitizer] Bootstrap complete! Canonical bin/velo is verified deterministic Gen3."
fi

if [[ "${RUN_TESTS}" -eq 1 ]]; then
    echo ""
    echo "[Velo Sanitizer] Running test suite under ASan + UBSan..."
    PYTHON_CMD="python3"
    if ! command -v python3 >/dev/null 2>&1; then
        PYTHON_CMD="python"
    fi

    if [[ $# -gt 0 ]]; then
        ${PYTHON_CMD} -m pytest "$@"
    else
        ${PYTHON_CMD} -m pytest tests -q
    fi
fi
