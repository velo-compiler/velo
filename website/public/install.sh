#!/usr/bin/env bash
# Velo Programming Language One-Liner POSIX Installer
# Usage: curl -fsSL http://localhost:5173/install.sh | bash

set -e

echo ""
echo "  ⚡ Velo Systems Language Installer (v2.0 Native)"
echo "  Code at high velocity."
echo ""

SERVER_URL="${VELO_INSTALL_URL:-http://localhost:5173}"
VELO_HOME="$HOME/.velo"
TARGET_DIR="$VELO_HOME/bin"
TARGET_BIN="$TARGET_DIR/velo"
TARGET_STD="$VELO_HOME/std"
TARGET_INC="$VELO_HOME/include"
TARGET_RUNTIME="$VELO_HOME/runtime"
DOWNLOAD_BIN_URL="$SERVER_URL/velo"
DOWNLOAD_BOOTSTRAP_URL="$SERVER_URL/bootstrap.c"
DOWNLOAD_STD_URL="$SERVER_URL/velo-std.tar.gz"

mkdir -p "$TARGET_DIR" "$TARGET_STD" "$TARGET_INC" "$TARGET_RUNTIME"

echo "--> Installing standalone compiler..."
DOWNLOADED_BIN=0
if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$DOWNLOAD_BIN_URL" -o "$TARGET_BIN" 2>/dev/null && DOWNLOADED_BIN=1 || true
elif command -v wget >/dev/null 2>&1; then
    wget -qO "$TARGET_BIN" "$DOWNLOAD_BIN_URL" 2>/dev/null && DOWNLOADED_BIN=1 || true
fi

# If remote binary is not present or failed, compile from bootstrap.c
if [ "$DOWNLOADED_BIN" -ne 1 ] || [ ! -s "$TARGET_BIN" ]; then
    echo "--> Pre-compiled binary not found on server. Checking bootstrap.c..."
    BOOTSTRAP_SRC=""
    if [ -f "./bootstrap.c" ]; then
        BOOTSTRAP_SRC="./bootstrap.c"
    elif [ -f "../bootstrap.c" ]; then
        BOOTSTRAP_SRC="../bootstrap.c"
    elif command -v curl >/dev/null 2>&1; then
        echo "--> Downloading bootstrap.c from $DOWNLOAD_BOOTSTRAP_URL..."
        curl -fsSL "$DOWNLOAD_BOOTSTRAP_URL" -o "$VELO_HOME/bootstrap.c" && BOOTSTRAP_SRC="$VELO_HOME/bootstrap.c" || true
    fi

    if [ -n "$BOOTSTRAP_SRC" ] && [ -f "$BOOTSTRAP_SRC" ]; then
        if command -v gcc >/dev/null 2>&1; then
            echo "--> Compiling standalone compiler from bootstrap.c using gcc..."
            gcc -std=c99 -O2 "$BOOTSTRAP_SRC" -o "$TARGET_BIN"
        elif command -v clang >/dev/null 2>&1; then
            echo "--> Compiling standalone compiler from bootstrap.c using clang..."
            clang -std=c99 -O2 "$BOOTSTRAP_SRC" -o "$TARGET_BIN"
        else
            echo "Error: C compiler (gcc or clang) required to build from bootstrap.c" >&2
            exit 1
        fi
    elif [ -f "./bin/velo" ]; then
        cp -f "./bin/velo" "$TARGET_BIN"
    else
        echo "Error: Could not obtain velo compiler binary." >&2
        exit 1
    fi
fi

chmod +x "$TARGET_BIN"
echo "--> Binary installed: $TARGET_BIN"

echo "--> Installing Standard Library & Runtime headers..."
TMP_TAR="$(mktemp /tmp/velo-std.XXXXXX.tar.gz 2>/dev/null || echo "$VELO_HOME/tmp-std.tar.gz")"
DOWNLOADED_TAR=0
if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$DOWNLOAD_STD_URL" -o "$TMP_TAR" 2>/dev/null && DOWNLOADED_TAR=1 || true
elif command -v wget >/dev/null 2>&1; then
    wget -qO "$TMP_TAR" "$DOWNLOAD_STD_URL" 2>/dev/null && DOWNLOADED_TAR=1 || true
fi

if [ "$DOWNLOADED_TAR" -eq 1 ] && [ -f "$TMP_TAR" ] && [ -s "$TMP_TAR" ]; then
    tar -xzf "$TMP_TAR" -C "$VELO_HOME"
    rm -f "$TMP_TAR"
else
    # Fallback to local repo directories
    if [ -d "./std" ]; then
        echo "--> Copying standard library from ./std..."
        cp -rf ./std/* "$TARGET_STD/"
    fi
    if [ -d "./runtime" ]; then
        cp -rf ./runtime/* "$TARGET_RUNTIME/"
    fi
fi

if [ -f "$TARGET_RUNTIME/velo_runtime.h" ]; then
    cp -f "$TARGET_RUNTIME/velo_runtime.h" "$TARGET_INC/velo_runtime.h"
elif [ -f "$VELO_HOME/runtime/velo_runtime.h" ]; then
    cp -f "$VELO_HOME/runtime/velo_runtime.h" "$TARGET_INC/velo_runtime.h"
elif [ -f "./runtime/velo_runtime.h" ]; then
    cp -f "./runtime/velo_runtime.h" "$TARGET_INC/velo_runtime.h"
    cp -f "./runtime/velo_runtime.h" "$TARGET_RUNTIME/velo_runtime.h"
fi
echo "--> Standard library installed: $TARGET_STD"

# Configure shell profile
SHELL_PROFILE="$HOME/.bashrc"
if [ -f "$HOME/.zshrc" ]; then
    SHELL_PROFILE="$HOME/.zshrc"
fi

if ! grep -q 'VELO_HOME' "$SHELL_PROFILE" 2>/dev/null; then
    echo "export VELO_HOME=\"\$HOME/.velo\"" >> "$SHELL_PROFILE"
    echo "export VELO_STD=\"\$HOME/.velo/std\"" >> "$SHELL_PROFILE"
    echo "export PATH=\"\$HOME/.velo/bin:\$PATH\"" >> "$SHELL_PROFILE"
    echo "--> Added ~/.velo/bin to $SHELL_PROFILE"
fi

export VELO_HOME="$VELO_HOME"
export VELO_STD="$TARGET_STD"
export PATH="$TARGET_DIR:$PATH"

echo ""
echo "--> Verifying installation..."
"$TARGET_BIN" version || true

echo ""
echo "🎉 SUCCESS! Velo v2.0 is installed and ready to use."
echo "Run 'velo help' to get started."
echo ""
