#!/usr/bin/env sh
# Local Forge Lenses: Studio on :8080, Stickerboard guest app on :9999.
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export LENSES_STICKERBOARD_PUBLIC_BASE="${LENSES_STICKERBOARD_PUBLIC_BASE:-http://127.0.0.1:9999}"
export LENSES_STICKERBOARD_PORT="${LENSES_STICKERBOARD_PORT:-9999}"
echo "[stickerboard] public base: $LENSES_STICKERBOARD_PUBLIC_BASE"
echo "[stickerboard] guest port: $LENSES_STICKERBOARD_PORT"
echo "[stickerboard] Build guest SPA: cd lenses-enterprise && npm run build:stickerboard"
cd "$ROOT"
exec python3 -m lenses "$@"
