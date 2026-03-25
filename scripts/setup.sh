#!/usr/bin/env bash
# Initialize nested submodules and check Python 3.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "[lenses setup] repo root: $ROOT"

if ! command -v git >/dev/null 2>&1; then
  echo "git is required." >&2
  exit 1
fi

git -c protocol.file.allow=always submodule update --init --recursive

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found; install Python 3." >&2
  exit 1
fi

echo "[lenses setup] python3: $(command -v python3)"

if ! python3 -c "import markdown" 2>/dev/null; then
  echo "[lenses setup] Tip: pip install markdown  (needed for generator/build-lenses-docs.py)"
fi

echo "[lenses setup] Done."
if [[ -x "$ROOT/scripts/lenses-startup.sh" ]]; then
  REPO_ROOT="$ROOT" "$ROOT/scripts/lenses-startup.sh" || true
fi
echo "  Build docs:  python3 generator/build-lenses-docs.py"
echo "  Run server:  ./scripts/run-lenses.sh"
echo "  Workspace:   export LENSES_WORKSPACE_ROOT=/path/to/workspace   (optional)"
