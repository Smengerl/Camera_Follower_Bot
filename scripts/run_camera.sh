#!/usr/bin/env bash
# Run the camera processor using the repository's virtualenv Python and forward all args
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "Virtualenv python not found at $VENV_PYTHON"
  echo "Activate your venv or adjust the path in this script."
  exit 1
fi

# Ensure we run from repo root so relative imports behave the same as during normal runs
cd "$ROOT_DIR"

# If the package is under src, set PYTHONPATH so the module can be found, then run it
PYTHONPATH="$ROOT_DIR/src"
exec env PYTHONPATH="$PYTHONPATH" "$VENV_PYTHON" -m camera_follower_bot.run_camera "$@"
