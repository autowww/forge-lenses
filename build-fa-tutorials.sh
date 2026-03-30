#!/usr/bin/env bash
# Build engineer tutorials into lenses/tutorials/ (forge-autodoc + Kitchensink),
# then sync to repo-root tutorial/. Lenses also serves lenses/tutorials/ and tutorials/
# under /local-site/<repo>/tutorials/… via tutorial_index.py when rsync is skipped.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

FA="$ROOT/kitchensink/forge-autodoc"
if [[ ! -f "$FA/forge_autodoc/__init__.py" ]]; then
  echo "[build-fa-tutorials] Missing kitchensink/forge-autodoc. Run:" >&2
  echo "  git submodule update --init --recursive kitchensink" >&2
  exit 1
fi

CONFIG="$ROOT/fa-handbook.yaml"
if [[ ! -f "$CONFIG" ]]; then
  echo "[build-fa-tutorials] Missing $CONFIG" >&2
  exit 1
fi

PYTHONPATH="$FA" python3 -m forge_autodoc build --config "$CONFIG" "$@"

SRC="$ROOT/lenses/tutorials"
DST="$ROOT/tutorial"
if [[ ! -f "$SRC/index.html" ]]; then
  echo "[build-fa-tutorials] Expected $SRC/index.html after build" >&2
  exit 1
fi

mkdir -p "$DST"
rsync -a --delete "$SRC/" "$DST/"
echo "[build-fa-tutorials] Synced $SRC/ → $DST/"
