#!/usr/bin/env sh
# Copy canonical Ollama helper from forge-lenses/scripts into Studio assets + static download.
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$ROOT/scripts/setup-ollama-for-lenses.sh"
if [ ! -f "$SRC" ]; then
  echo "[sync-ollama-setup] missing $SRC" >&2
  exit 1
fi
mkdir -p "$ROOT/lenses-enterprise/src/assets" "$ROOT/lenses-enterprise/public/snippets" "$ROOT/lenses/static/studio/snippets"
cp "$SRC" "$ROOT/lenses-enterprise/src/assets/setup-ollama-for-lenses.sh"
cp "$SRC" "$ROOT/lenses-enterprise/public/snippets/setup-ollama-for-lenses.sh"
cp "$SRC" "$ROOT/lenses/static/studio/snippets/setup-ollama-for-lenses.sh"
