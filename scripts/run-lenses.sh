#!/usr/bin/env bash
# Build docs (if markdown available) and start lenses on :8080.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"

if python3 -c "import markdown" 2>/dev/null; then
  python3 generator/build-lenses-docs.py
else
  echo "[lenses] markdown not installed — skipping docs build (pip install markdown)" >&2
fi

exec python3 -m lenses.serve "$@"
