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

# Minimal forge-df-test-project for Foundry integration E2E (fake worker fixture).
mkdir -p "$WS/forge-df-test-project/src/dfcalc" "$WS/forge-df-test-project/tests" "$WS/forge-df-test-project/fixtures"
cat > "$WS/forge-df-test-project/src/dfcalc/engine.py" <<'PY'
def multiply(a, b):
    return a + b
PY
cat > "$WS/forge-df-test-project/tests/test_engine.py" <<'PY'
from dfcalc.engine import multiply

def test_multiply():
    assert multiply(3, 4) == 12
PY
cp "$ROOT/../forge-df-test-project/fixtures/multiply_fix.json" "$WS/forge-df-test-project/fixtures/" 2>/dev/null || \
  echo '{"files":{"src/dfcalc/engine.py":"def multiply(a,b): return a*b\n"}}' > "$WS/forge-df-test-project/fixtures/multiply_fix.json"
(
  cd "$WS/forge-df-test-project"
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
