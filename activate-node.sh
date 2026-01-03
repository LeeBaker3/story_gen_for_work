#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORTABLE_DIR="$ROOT_DIR/.node-runtime"

# Prefer portable Node if present.
if [[ -d "$PORTABLE_DIR" ]]; then
  # Pick the latest extracted portable version (lexicographic sort is fine for vX.Y.Z here).
  NODE_BIN_DIR=$(ls -1d "$PORTABLE_DIR"/node-v*-*/bin 2>/dev/null | sort | tail -n 1 || true)
  if [[ -n "${NODE_BIN_DIR:-}" && -d "$NODE_BIN_DIR" ]]; then
    export PATH="$NODE_BIN_DIR:$PATH"
  fi
fi

# Fall back to nvm if installed.
if [[ -s "$HOME/.nvm/nvm.sh" && -f "$ROOT_DIR/.nvmrc" ]]; then
  # shellcheck source=/dev/null
  . "$HOME/.nvm/nvm.sh" >/dev/null 2>&1 || true
  nvm use >/dev/null 2>&1 || true
fi

echo "Activated Node environment; node version: $(command -v node >/dev/null 2>&1 && node -v || echo 'not found')"
