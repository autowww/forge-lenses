#!/usr/bin/env bash
# Run Studio UX crawl v4 against ephemeral Lenses + multi-repo fixture; assert green summary.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${E2E_LENSES_PORT:-17556}"
ORIGIN="http://127.0.0.1:${PORT}"
REPORT="${ROOT}/workbench/studio-ux-crawl-v4/report.json"
FIXTURE_SCRIPT="${ROOT}/lenses-enterprise/scripts/e2e-lenses-with-fixture.sh"
CRAWL="${ROOT}/workbench/studio-ux-crawl-v4.mjs"

[[ -f "${CRAWL}" ]] || { echo "missing ${CRAWL}" >&2; exit 1; }
[[ -x "${FIXTURE_SCRIPT}" ]] || chmod +x "${FIXTURE_SCRIPT}"

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "${SERVER_PID}" 2>/dev/null; then
    kill "${SERVER_PID}" 2>/dev/null || true
    wait "${SERVER_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

export E2E_LENSES_PORT="${PORT}"
export E2E_BUILD_STUDIO="${E2E_BUILD_STUDIO:-0}"
export LENSES_STICKERBOARD_PORT="${LENSES_STICKERBOARD_PORT:-0}"

"${FIXTURE_SCRIPT}" &
SERVER_PID=$!

for _ in $(seq 1 60); do
  if curl -fsS "${ORIGIN}/api/workspace-state" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
curl -fsS "${ORIGIN}/api/workspace-state" >/dev/null || {
  echo "Lenses fixture server failed to start on ${ORIGIN}" >&2
  exit 1
}

node "${CRAWL}" "${ORIGIN}/studio"

[[ -f "${REPORT}" ]] || { echo "missing report ${REPORT}" >&2; exit 1; }

if ! command -v jq >/dev/null 2>&1; then
  echo "jq required for studio-ux-crawl-gate.sh" >&2
  exit 1
fi

splash="$(jq -r '.splashCleared' "${REPORT}")"
jargon_len="$(jq '.jargonRoutes | length' "${REPORT}")"
splash_len="$(jq '.splashRoutes | length' "${REPORT}")"

[[ "${splash}" == "true" ]] || { echo "splashCleared not true" >&2; exit 1; }
[[ "${jargon_len}" -eq 0 ]] || { echo "jargon routes: $(jq -c '.jargonRoutes' "${REPORT}")" >&2; exit 1; }
[[ "${splash_len}" -eq 0 ]] || { echo "splash routes: $(jq -c '.splashRoutes' "${REPORT}")" >&2; exit 1; }

echo "studio-ux-crawl-gate: GREEN (${ORIGIN})"
