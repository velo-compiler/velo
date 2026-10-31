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
DOWNLOAD_BIN_URL="$SERVER_URL/velo"
DOWNLOAD_STD_URL="$SERVER_URL/velo-std.tar.gz"

mkdir -p "$TARGET_DIR" "$TARGET_STD" "$TARGET_INC"

echo "--> Downloading standalone compiler from $DOWNLOAD_BIN_URL..."
if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$DOWNLOAD_BIN_URL" -o "$TARGET_BIN"
elif command -v wget >/dev/null 2>&1; then
    wget -qO "$TARGET_BIN" "$DOWNLOAD_BIN_URL"
else
    echo "Error: curl or wget is required to install Velo." >&2
    exit 1
fi

chmod +x "$TARGET_BIN"
echo "--> Binary installed: $TARGET_BIN"

echo "--> Installing Standard Library & Runtime headers..."
TMP_TAR="$(mktemp /tmp/velo-std.XXXXXX.tar.gz)"
if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$DOWNLOAD_STD_URL" -o "$TMP_TAR" || true
elif command -v wget >/dev/null 2>&1; then
    wget -qO "$TMP_TAR" "$DOWNLOAD_STD_URL" || true
fi

if [ -f "$TMP_TAR" ] && [ -s "$TMP_TAR" ]; then
    tar -xzf "$TMP_TAR" -C "$VELO_HOME"
    rm -f "$TMP_TAR"
fi

if [ -f "$VELO_HOME/runtime/velo_runtime.h" ]; then
    cp -f "$VELO_HOME/runtime/velo_runtime.h" "$TARGET_INC/velo_runtime.h"
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
