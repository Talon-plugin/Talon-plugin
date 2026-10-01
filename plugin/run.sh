#!/bin/bash
# Talons Media Extractor wrapper for Grabbit (macOS Apple Silicon)
# Uses `uv run` to manage the Python environment and yt-dlp dependency
# declared in pyproject.toml / uv.lock — no bundled source, no version hacks.

# ---------------------------------------------------------------------------
# Zero-Dependency Bootstrap
# If we don't have `uv` installed, download it standalone locally.
# ---------------------------------------------------------------------------
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

if ! command -v uv &> /dev/null; then
    # Download uv executable directly into ~/.local/bin without modifying shell profiles
    curl -LsSf https://astral.sh/uv/install.sh | env INSTALLER_NO_MODIFY_PATH=1 sh >/dev/null 2>&1
fi

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# ---------------------------------------------------------------------------
# All modes invoke extractor.py via `uv run`.
# uv reads pyproject.toml, syncs .venv (installing yt-dlp if needed),
# then runs the script with the correct Python version (silently downloading
# a portable Python if we don't have one) — fully automatic.
# ---------------------------------------------------------------------------

if [ "$1" == "--extract" ] || [ "$1" == "--dump-json" ]; then
    URL="$2"
    RESOLUTION="${3:-Best Quality}"
    uv run --project "$DIR" "$DIR/extractor.py" "$URL" "$RESOLUTION"
elif [ "$1" == "--raw" ]; then
    URL="$2"
    uv run --project "$DIR" -m yt_dlp --no-warnings -q --dump-json --yes-playlist -- "$URL"
else
    # Default: treat first argument as URL
    URL="$1"
    RESOLUTION="${2:-Best Quality}"
    uv run --project "$DIR" "$DIR/extractor.py" "$URL" "$RESOLUTION"
fi
