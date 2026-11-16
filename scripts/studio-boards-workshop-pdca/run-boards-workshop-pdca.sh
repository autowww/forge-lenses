#!/usr/bin/env bash
# PDCA loop for Studio boards workshop feature (forge-lenses).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${BOARDS_PDCA_REPO:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
MAX_ITER="${BOARDS_PDCA_MAX_ITERATIONS:-12}"
ONLY_PROMPT="${BOARDS_PDCA_ONLY:-}"
BASE="${LENSES_BASE_URL:-http://127.0.0.1:8080}"

PROMPTS=(
  "01-plan-registry-health.md"
  "02-do-session-templates-api.md"
  "03-do-ks-sticker-primitives.md"
  "04-do-studio-hub-templates.md"
  "10-do-product-map-prefill.md"
  "05-do-studio-workshop-editor.md"
  "06-do-impact-effort-scoring.md"
  "07-do-workshop-phases-ux.md"
)

run_checks() {
  (cd "${REPO_ROOT}" && python3 -m pytest tests/test_sticker_board_session.py tests/test_board_product_map.py -q)
  LENSES_BASE_URL="${BASE}" "${SCRIPT_DIR}/checks/smoke-boards-studio.sh" || true
}

cd "${REPO_ROOT}"

if [[ "${SKIP_CURSOR_AGENT:-0}" == "1" ]]; then
  run_checks
  exit 0
fi

if [[ -n "${ONLY_PROMPT}" ]]; then
  run_checks || true
  "${SCRIPT_DIR}/cursor-agent-run-board-prompt.sh" "${REPO_ROOT}" "${SCRIPT_DIR}/prompts/${ONLY_PROMPT}"
  run_checks
  exit 0
fi

iter=0
while [[ "${iter}" -lt "${MAX_ITER}" ]]; do
  iter=$((iter + 1))
  echo "[boards-pdca] iteration ${iter}/${MAX_ITER}" >&2
  if run_checks; then
    echo "[boards-pdca] checks passed" >&2
    exit 0
  fi
  p="${PROMPTS[$(( (iter - 1) % ${#PROMPTS[@]} ))]}"
  echo "[boards-pdca] agent prompt: ${p}" >&2
  "${SCRIPT_DIR}/cursor-agent-run-board-prompt.sh" "${REPO_ROOT}" "${SCRIPT_DIR}/prompts/${p}" || true
done

echo "[boards-pdca] max iterations reached; run checks manually" >&2
exit 1
