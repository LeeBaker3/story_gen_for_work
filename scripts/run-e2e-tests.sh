#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Python executable not found at $PYTHON_BIN" >&2
    exit 1
fi

cd "$ROOT_DIR"

"$PYTHON_BIN" -m playwright install chromium
PYTHONPATH="$ROOT_DIR" RUN_UI_E2E=true "$PYTHON_BIN" -m pytest -q backend/tests/e2e --browser chromium "$@"