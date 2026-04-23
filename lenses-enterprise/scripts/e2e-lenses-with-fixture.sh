#!/usr/bin/env bash
# Start Lenses on a disposable workspace (docs_health_sample_repo copy + git init) for Studio E2E.
# Repo root = forge-lenses (parent of lenses-enterprise).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PORT="${E2E_LENSES_PORT:-17555}"
WS="$(mktemp -d)"
export E2E_WORKSPACE_TMP="$WS"

cleanup() {
  rm -rf "$WS"
}
trap cleanup EXIT

mkdir -p "$WS/e2e_doc_proj"
cp -a "$ROOT/tests/fixtures/docs_health_sample_repo/." "$WS/e2e_doc_proj/"
(
  cd "$WS/e2e_doc_proj"
  git init
  git config user.email "e2e@example.invalid"
  git config user.name "e2e"
  git add -A
  git commit -m "init"
)

if [ "${E2E_BUILD_STUDIO:-1}" = "1" ]; then
  (cd "$ROOT/lenses-enterprise" && npm run build)
fi

cd "$ROOT"
# Foreground (not exec) so EXIT trap can remove the temp workspace when Playwright stops the server.
python3 -m lenses --host 127.0.0.1 --port "$PORT" --workspace-root "$WS"
