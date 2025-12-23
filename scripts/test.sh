#!/usr/bin/env bash
# Run pytest using the repository's virtualenv Python
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "Virtualenv python not found at $VENV_PYTHON"
  echo "Activate your venv or adjust the path in this script."
  exit 1
fi

# forward all args to pytest
cd "$ROOT_DIR"
exec "$VENV_PYTHON" -m pytest -v "$@"
