#!/usr/bin/env bash
# Rebuild docs (if markdown is available), free the lenses port, start the dashboard.
# Default workspace is the parent of this repo (sibling project folders), same as the Python resolver.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"

HOST="${LENSES_HOST:-127.0.0.1}"
PORT="${LENSES_PORT:-8080}"

if [[ -z "${LENSES_WORKSPACE_ROOT:-}" ]]; then
  export LENSES_WORKSPACE_ROOT="$(cd "$ROOT/.." && pwd)"
fi

if command -v fuser >/dev/null 2>&1; then
  fuser -k "${PORT}/tcp" >/dev/null 2>&1 || true
  sleep 0.2
else
  echo "[restart-lenses] tip: install fuser (package psmisc on Debian/Ubuntu) to auto-stop the old listener" >&2
fi

if python3 -c "import markdown" 2>/dev/null; then
  python3 generator/build-lenses-docs.py
else
  echo "[restart-lenses] markdown not installed — skipping docs build (pip install markdown)" >&2
fi

python3 generator/collect-lenses-overview-data.py || true

exec python3 -m lenses --host "$HOST" --port "$PORT" "$@"
