#!/usr/bin/env bash
set -euo pipefail
# bootstrap-node.sh
# Lightweight helper to ensure a usable Node.js runtime when nvm or system node is absent.
# Strategy:
# 1. If `node` exists and satisfies engines in package.json, exit.
# 2. If .nvmrc present and nvm available, auto use it.
# 3. Otherwise download a portable Node tarball into .node-runtime/ and prepend its bin to PATH.
# 4. Print instructions for adding eval "$(./scripts/bootstrap-node.sh env)" to your shell for convenience.

#!/usr/bin/env bash
# Idempotent Node bootstrapper.
# Guarantees: creates .node-runtime/, downloads portable Node if needed (or forced), and writes activate-node.sh.
# Environment overrides:
#   DEBUG=1            Verbose logging
#   PORTABLE_INSTALL=1 Force portable download even if a system/nvm Node is acceptable
#   NODE_VERSION=22.10.0  Pin a specific full version (overrides .nvmrc)
# Exit codes:
#   0 success
#   2 download failure
#   3 extraction failure

# Optional DEBUG mode: set DEBUG=1 to see verbose output
DEBUG=${DEBUG:-0}
PORTABLE_INSTALL=${PORTABLE_INSTALL:-0}
NODE_VERSION_OVERRIDE=${NODE_VERSION:-}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ENGINES_RANGE=">=20 <23"
NODE_VERSION_FILE="$ROOT_DIR/.nvmrc"
PORTABLE_DIR="$ROOT_DIR/.node-runtime"
PLATFORM="$(uname -s)" # Darwin or Linux
ARCH="$(uname -m)"     # arm64 or x86_64

function have_node() {
  command -v node >/dev/null 2>&1 || return 1
  local ver
  ver=$(node -v 2>/dev/null | sed 's/^v//') || return 1
  local major=${ver%%.*}
  if [[ $major -ge 20 && $major -lt 23 ]]; then
    return 0
  fi
  return 1
}

function have_npm() {
  command -v npm >/dev/null 2>&1
}

ORIGINAL_NODE_PATH=""
if have_node && [[ $PORTABLE_INSTALL -ne 1 ]]; then
  ORIGINAL_NODE_PATH="$(command -v node)"
  [[ $DEBUG == 1 ]] && echo "[bootstrap-node] Detected existing Node $(node -v) at $ORIGINAL_NODE_PATH" >&2
fi

# Always ensure portable directory exists as early as possible (even if we later early-exit)
mkdir -p "$PORTABLE_DIR"

# Try nvm if available and .nvmrc exists (unless forcing portable install)
NVM_USED=0
if [[ $PORTABLE_INSTALL -eq 1 ]]; then
  [[ $DEBUG == 1 ]] && echo "[bootstrap-node] Skipping nvm logic due to PORTABLE_INSTALL=1" >&2
else
  if [[ -z "$ORIGINAL_NODE_PATH" ]]; then
    if [[ -f $NODE_VERSION_FILE && -s "$HOME/.nvm/nvm.sh" ]]; then
      [[ $DEBUG == 1 ]] && echo "[bootstrap-node] Sourcing nvm from $HOME/.nvm/nvm.sh" >&2
      # shellcheck source=/dev/null
      set +e
      . "$HOME/.nvm/nvm.sh"
      NVM_SOURCE_STATUS=$?
      set -e
      if [[ $NVM_SOURCE_STATUS -ne 0 ]]; then
        [[ $DEBUG == 1 ]] && echo "[bootstrap-node] Warning: sourcing nvm returned exit code $NVM_SOURCE_STATUS (ignored)" >&2
      fi
      if command -v nvm >/dev/null 2>&1; then
        [[ $DEBUG == 1 ]] && echo "[bootstrap-node] Attempting nvm install/use based on $NODE_VERSION_FILE" >&2
        # nvm can return non-zero in some environments (e.g. missing aliases).
        # We don't want that to break installs; portable Node is the fallback.
        set +e
        nvm install >/dev/null 2>&1
        nvm use >/dev/null 2>&1
        set -e
        if have_node; then
          NVM_USED=1
          [[ $DEBUG == 1 ]] && echo "[bootstrap-node] nvm supplied Node $(node -v)" >&2
        else
          [[ $DEBUG == 1 ]] && echo "[bootstrap-node] nvm did not yield a usable Node version" >&2
        fi
      else
        [[ $DEBUG == 1 ]] && echo "[bootstrap-node] nvm not available after sourcing script" >&2
      fi
    else
      [[ $DEBUG == 1 ]] && echo "[bootstrap-node] No .nvmrc or nvm script missing; skipping nvm" >&2
    fi
  fi
fi

cd "$PORTABLE_DIR"

# Determine filename mapping for Node distribution
case "$PLATFORM" in
  Darwin) PLATFORM_LOWER=darwin ;;
  Linux)  PLATFORM_LOWER=linux ;;
  *) echo "Unsupported platform: $PLATFORM" >&2; exit 1;;
esac

case "$ARCH" in
  arm64|aarch64) ARCH_LOWER=arm64 ;;
  x86_64|amd64) ARCH_LOWER=x64 ;;
  *) echo "Unsupported architecture: $ARCH" >&2; exit 1;;
esac

# Determine desired version (can be major, full, or v-prefixed)
if [[ -n "$NODE_VERSION_OVERRIDE" ]]; then
  RAW_DESIRED="${NODE_VERSION_OVERRIDE#v}"
elif [[ -f "$NODE_VERSION_FILE" ]]; then
  RAW_DESIRED=$(tr -d 'v' < "$NODE_VERSION_FILE")
else
  RAW_DESIRED="22"
fi

FULL_TAG=""
SKIP_INDEX_FETCH=0

# Detect if RAW_DESIRED already looks like full semver (x.y.z)
if [[ "$RAW_DESIRED" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  FULL_TAG="$RAW_DESIRED"
  SKIP_INDEX_FETCH=1
fi

if [[ $SKIP_INDEX_FETCH -eq 0 ]]; then
  if [[ "$RAW_DESIRED" =~ ^[0-9]+$ ]]; then
    echo "Resolving latest Node ${RAW_DESIRED}.x version..." >&2
    if ! INDEX_JSON=$(curl -fsSL https://nodejs.org/dist/index.json | head -c 200000); then
      echo "Warning: Could not fetch index.json (network issue?). Falling back to major .0.0" >&2
      INDEX_JSON=""
    fi
    FULL_TAG=$(printf '%s' "$INDEX_JSON" | grep -m1 "\"version\": \"v${RAW_DESIRED}\." | sed -E 's/.*"version": "v([^\"]+)".*/\1/') || true
    if [[ -z "$FULL_TAG" ]]; then
      echo "Failed to resolve full version for major ${RAW_DESIRED}, falling back to ${RAW_DESIRED}.0.0" >&2
      FULL_TAG="${RAW_DESIRED}.0.0"
    fi
  else
    # Something else like snapshot or partial; treat as explicit
    FULL_TAG="$RAW_DESIRED"
  fi
fi

DESIRED="$FULL_TAG"
TARBALL="node-v${DESIRED}-${PLATFORM_LOWER}-${ARCH_LOWER}.tar.gz"
BASE_URL="https://nodejs.org/dist/v${DESIRED}"

PORTABLE_NODE_DIR="node-v${DESIRED}-${PLATFORM_LOWER}-${ARCH_LOWER}"
if [[ $PORTABLE_INSTALL -eq 1 || ( $NVM_USED -eq 0 && -z "$ORIGINAL_NODE_PATH" ) ]]; then
  if [[ ! -d "$PORTABLE_NODE_DIR" ]]; then
    echo "Downloading Node v${DESIRED} portable binary..." >&2
    if ! curl -fsSLO "${BASE_URL}/${TARBALL}"; then
      echo "Primary download failed. Trying HTTP fallback..." >&2
      if ! curl -fSL "http://nodejs.org/dist/v${DESIRED}/${TARBALL}" -o "$TARBALL"; then
        echo "ERROR: Could not download Node v${DESIRED}. Check network or pin a full version in .nvmrc." >&2
        exit 2
      fi
    fi
    tar -xzf "$TARBALL" || { echo "ERROR: Failed to extract Node tarball." >&2; exit 3; }
  fi
fi

NODE_DIR="$(pwd)/$PORTABLE_NODE_DIR"
NODE_BIN_DIR="${NODE_DIR}/bin"

# Decide activation strategy
ACTIVATE_BODY=""
if [[ $PORTABLE_INSTALL -eq 1 || ( $NVM_USED -eq 0 && -z "$ORIGINAL_NODE_PATH" ) ]]; then
  # Portable install path
  ACTIVATE_BODY="export PATH=\"${NODE_BIN_DIR}:\"\$PATH"
else
  # Use whichever node is currently discovered when sourcing nvm (if nvm used), otherwise no-op
  if [[ $NVM_USED -eq 1 ]]; then
    ACTIVATE_BODY="[ -s \"$HOME/.nvm/nvm.sh\" ] && . \"$HOME/.nvm/nvm.sh\" >/dev/null 2>&1 && nvm use >/dev/null 2>&1"
  else
    # Existing system node; just ensure it remains (no PATH modification needed)
    ACTIVATE_BODY="# System Node already satisfies constraints. No PATH change needed."
  fi
fi

# Write an activation helper for convenience.
# IMPORTANT: keep this deterministic and portable (no machine-specific absolute paths).
cat > "$ROOT_DIR/activate-node.sh" <<'EOF'
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
EOF
chmod +x "$ROOT_DIR/activate-node.sh" || true

# Output export lines for eval usage
if [[ "${1:-}" == "env" ]]; then
  echo "export PATH=$NODE_BIN_DIR:$PATH"
  exit 0
fi

echo "Node environment prepared. Next steps:" >&2
echo "  source ./activate-node.sh" >&2
echo "Then (first time) install deps: npm install" >&2
echo "Force portable install example: PORTABLE_INSTALL=1 bash scripts/bootstrap-node.sh" >&2
echo "Debug verbose run: DEBUG=1 bash scripts/bootstrap-node.sh" >&2

# Final diagnostic if npm still absent
if ! have_npm; then
  echo "WARNING: npm still not found after bootstrap. If you relied on nvm, you MUST 'source ./activate-node.sh' in your interactive shell." >&2
fi
echo "(If script lacked execute bit, run: chmod +x scripts/bootstrap-node.sh)" >&2
