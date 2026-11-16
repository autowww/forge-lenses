#!/usr/bin/env bash
# Build docs (if markdown available) and start lenses on :8080.
# For “stop previous + rebuild + start”, use ./scripts/restart-lenses.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"

if [[ -z "${LENSES_WORKSPACE_ROOT:-}" ]]; then
  export LENSES_WORKSPACE_ROOT="$(cd "$ROOT/.." && pwd)"
fi

# Experimental Blueprints Wizard (/studio/blueprints/wizard). Override with LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD=0 to disable.
export LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD="${LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD:-1}"

if python3 -c "import markdown" 2>/dev/null; then
  python3 generator/build-lenses-docs.py
else
  echo "[lenses] markdown not installed — skipping docs build (pip install markdown)" >&2
fi

python3 generator/collect-lenses-overview-data.py || true

exec python3 -m lenses "$@"
