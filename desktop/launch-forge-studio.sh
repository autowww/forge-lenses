#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
export LENSES_STUDIO_UI=1
exec ./node_modules/.bin/electron . --no-sandbox
