#!/usr/bin/env bash
# Dedicated Electron shell for Virtual Camera Studio (minimal chrome, not full Forge Studio).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
export LENSES_STUDIO_UI=1
export LENSES_VIRTUAL_CAMERA_STUDIO=1
export LENSES_EXPERIMENTAL_VIRTUAL_CAMERA=1
export LENSES_PORT="${LENSES_PORT:-8096}"
exec ./node_modules/.bin/electron . --no-sandbox
