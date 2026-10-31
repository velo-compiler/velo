#!/usr/bin/env bash
# Velo Programming Language One-Liner POSIX Installer
# Usage: curl -fsSL http://localhost:5173/install.sh | bash

set -e

echo ""
echo "  ⚡ Velo Systems Language Installer (v2.0 Native)"
echo "  Code at high velocity."
echo ""

SERVER_URL="${VELO_INSTALL_URL:-http://localhost:5173}"
TARGET_DIR="$HOME/.velo/bin"
TARGET_BIN="$TARGET_DIR/velo"
DOWNLOAD_URL="$SERVER_URL/velo"

mkdir -p "$TARGET_DIR"

echo "--> Downloading standalone binary from $DOWNLOAD_URL..."
if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$DOWNLOAD_URL" -o "$TARGET_BIN"
elif command -v wget >/dev/null 2>&1; then
    wget -qO "$TARGET_BIN" "$DOWNLOAD_URL"
else
    echo "Error: curl or wget is required to install Velo." >&2
    exit 1
fi

chmod +x "$TARGET_BIN"
echo "--> Binary installed: $TARGET_BIN"

# Add to PATH in shell profile if not present
SHELL_PROFILE="$HOME/.bashrc"
if [ -f "$HOME/.zshrc" ]; then
    SHELL_PROFILE="$HOME/.zshrc"
fi

if ! grep -q '.velo/bin' "$SHELL_PROFILE" 2>/dev/null; then
    echo "export PATH=\"\$HOME/.velo/bin:\$PATH\"" >> "$SHELL_PROFILE"
    echo "--> Added ~/.velo/bin to $SHELL_PROFILE"
fi

export PATH="$TARGET_DIR:$PATH"

echo ""
echo "--> Verifying installation..."
"$TARGET_BIN" version || true

echo ""
echo "🎉 SUCCESS! Velo v2.0 is installed and ready to use."
echo "Run 'velo help' to get started."
echo ""
