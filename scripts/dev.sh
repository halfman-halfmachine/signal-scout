#!/usr/bin/env bash
#
# Signal Scout local dev runner.
#
# Loads environment from .env, then runs the backend either directly with
# uvicorn (default) or via docker compose.
#
# Usage:
#   scripts/dev.sh                 # local uvicorn with --reload
#   scripts/dev.sh --docker        # build + run the full stack via docker compose
#   scripts/dev.sh --no-reload     # local uvicorn without autoreload
#   PORT=9000 scripts/dev.sh       # env overrides still win
#
set -euo pipefail

# --- Resolve repo root (this script lives in <root>/scripts) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

MODE="local"
RELOAD="--reload"
for arg in "$@"; do
  case "$arg" in
    --docker)    MODE="docker" ;;
    --no-reload) RELOAD="" ;;
    -h|--help)
      sed -n '3,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

# --- Load .env ---
ENV_FILE="$ROOT_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found. Copy .env.example to .env and edit it." >&2
  exit 1
fi
# Export every assignment in .env (ignores comments/blank lines).
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

PORT="${PORT:-8000}"

if [[ "$MODE" == "docker" ]]; then
  echo ">> docker compose up --build (reads .env automatically)"
  exec docker compose up --build
fi

# --- Local mode: ensure venv + deps, then run uvicorn ---
cd "$ROOT_DIR/backend"
if [[ ! -x ".venv/bin/uvicorn" ]]; then
  echo ">> Setting up backend venv..."
  python3 -m venv .venv
  ./.venv/bin/pip install --quiet --upgrade pip
  ./.venv/bin/pip install --quiet -e ".[dev]"
fi

# Layer 6 / parity logic assumes UTC; keep dev consistent.
export TZ="${TZ:-UTC}"
export DATA_DIR="${DATA_DIR:-./data}"
# Serve the built Next.js export from the same origin. Overridable via env.
export STATIC_DIR="${STATIC_DIR:-$ROOT_DIR/frontend/out}"

if [[ ! -f "$STATIC_DIR/index.html" ]]; then
  echo ">> WARNING: no built front-end at $STATIC_DIR" >&2
  echo "   The API will run but the UI won't be served. Build it with:" >&2
  echo "     (cd \"$ROOT_DIR/frontend\" && npm install && npm run build)" >&2
fi

AUTH_MODE="template (no key/token)"
if [[ -n "${ANTHROPIC_AUTH_TOKEN:-}" ]]; then
  AUTH_MODE="live via gateway: ${ANTHROPIC_BASE_URL:-https://api.anthropic.com}"
elif [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
  AUTH_MODE="live via api.anthropic.com"
fi

echo ">> Signal Scout backend"
echo "   port:  $PORT"
echo "   data:  $DATA_DIR"
echo "   ui:    $STATIC_DIR"
echo "   llm:   $AUTH_MODE"
echo "   url:   http://localhost:$PORT"

# shellcheck disable=SC2086
exec ./.venv/bin/uvicorn app.main:app --port "$PORT" $RELOAD
