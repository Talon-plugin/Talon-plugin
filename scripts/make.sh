#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$SCRIPT_DIR/.."
PLUGIN_DIR="$REPO_ROOT/plugin"
OUT_FILE="$REPO_ROOT/build/talons.gda"

echo "🦅 [Talons] Building Grabbit Plugin package..."

# Ensure uv.lock is valid and up to date before packaging
cd "$PLUGIN_DIR"
# Remove corrupt/empty lockfile so uv can regenerate cleanly
if [ ! -s "uv.lock" ]; then
    rm -f "uv.lock"
fi
if ! uv lock; then
    echo "❌ uv lock failed — is uv installed? (brew install uv)" >&2
    exit 1
fi

# Ensure executable permissions
chmod +x "$PLUGIN_DIR/run.sh" "$PLUGIN_DIR/extractor.py"

# Remove previous build if exists
rm -f "$OUT_FILE"

# Package plugin directory contents into .gda archive
# Exclude venv, caches, and OS noise.
(
    cd "$PLUGIN_DIR"
    zip -r -q "$OUT_FILE" . \
        -x "*.DS_Store" \
        -x "__pycache__/*" \
        -x "*.pyc" \
        -x ".venv/*"
)

echo "✅ Created Grabbit plugin package: $OUT_FILE ($(du -sh "$OUT_FILE" | cut -f1))"
