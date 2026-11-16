#!/usr/bin/env bash
set -euo pipefail

BASE="${LENSES_BASE_URL:-http://127.0.0.1:8080}"

curl -sf "${BASE}/api/workspace-state" >/dev/null || {
  echo "smoke: workspace-state failed (is Lenses running on ${BASE}?)" >&2
  exit 1
}

curl -sf "${BASE}/api/sticker-board-registry" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'projects' in d" || {
  echo "smoke: sticker-board-registry failed" >&2
  exit 1
}

echo "smoke-boards-studio: ok (${BASE})"
