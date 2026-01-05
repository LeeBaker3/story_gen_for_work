#!/usr/bin/env bash
set -euo pipefail
# run-frontend-tests.sh
# One-shot convenience: bootstrap node (if needed) + install deps (if missing) + run frontend tests.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

bash scripts/bootstrap-node.sh >/dev/null 2>&1 || true
# Activate portable env for this process
if ! command -v node >/dev/null 2>&1; then
  eval "$(bash scripts/bootstrap-node.sh env)"
fi

if [[ ! -d node_modules ]]; then
  echo "Installing npm dependencies..." >&2
  npm install
fi

echo "Running frontend tests..." >&2
npm run test:frontend
