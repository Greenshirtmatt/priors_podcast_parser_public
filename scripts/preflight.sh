#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if command -v brew >/dev/null 2>&1; then
  if brew list ffmpeg >/dev/null 2>&1; then
    brew upgrade ffmpeg
  else
    brew install ffmpeg
  fi
else
  echo "Homebrew not found. Please install ffmpeg manually."
fi

if ! command -v whisper >/dev/null 2>&1; then
  echo "whisper CLI not found on PATH. Ensure .venv is activated and re-run."
else
  echo "whisper CLI installed at: $(command -v whisper)"
fi
