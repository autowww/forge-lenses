#!/usr/bin/env bash
# Forge Lenses Studio UX4 remediation PDCA phase gate.
# Usage: ./scripts/fl-studio-ux4-pdca/check-phase-gate.sh <V00|…|V05|all>
#
# Cumulative gates V00–V05. Later phases assume earlier gates passed.
# V00 checks harness only; V01+ use grep patterns for post-implementation artifacts.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PHASE="${1:-}"
MASTER_SEQ="${REPO_ROOT}/docs/prompts/fl-studio-ux4-pdca/00-master-sequence.md"
PROMPTS_DIR="${REPO_ROOT}/docs/prompts/fl-studio-ux4-pdca"
LE="${REPO_ROOT}/lenses-enterprise"
SERVE_PY="${REPO_ROOT}/lenses/serve.py"
APP_TSX="${LE}/src/App.tsx"
VITE_CONFIG="${LE}/vite.config.ts"
NESTED_HORIZON="${LE}/src/components/plan/NestedRoadmapHorizon.tsx"
NESTED_FRAME="${LE}/src/components/plan/NestedRoadmapWorkspaceFrame.tsx"
WEBSITES_BROWSE="${LE}/src/pages/WebsitesBrowsePage.tsx"
BOARDS_HUB="${LE}/src/components/boards/BoardsArtifactsHub.tsx"
HANDBOOK_RETIREMENT="${REPO_ROOT}/docs/handbook-public/studio-classic-ui-retirement.md"
CRAWL_V5="${REPO_ROOT}/workbench/studio-ux-crawl-v5.mjs"
V05_PROMPT="${PROMPTS_DIR}/V05-closeout.md"

FLS4_IDS=(
  FLS4-001 FLS4-002 FLS4-003 FLS4-004
)

[[ -n "${PHASE}" ]] || { echo "usage: $0 <V00|…|V05|all>" >&2; exit 1; }

cd "${REPO_ROOT}"

info() { echo "==> gate ${1}: $2"; }
fail() { echo "FAIL: $*" >&2; exit 1; }
require_file() { [[ -f "$1" ]] || fail "missing: $1"; }

grep_file() {
  local pattern="$1"
  local file="$2"
  local label="$3"
  grep -qE "${pattern}" "${file}" || fail "${label}: pattern not found in ${file}: ${pattern}"
}

grep_file_absent() {
  local pattern="$1"
  local file="$2"
  local label="$3"
  if grep -qE "${pattern}" "${file}" 2>/dev/null; then
    fail "${label}: forbidden pattern found in ${file}: ${pattern}"
  fi
}

require_all_fls4_in_master() {
  local id
  for id in "${FLS4_IDS[@]}"; do
    grep -q "${id}" "${MASTER_SEQ}" || fail "master sequence missing ${id}"
  done
}

gate_v00() {
  require_file "${MASTER_SEQ}"
  require_file scripts/fl-studio-ux4-pdca/SEQUENCE.yaml
  require_file scripts/fl-studio-ux4-pdca/check-phase-gate.sh
  require_file scripts/fl-studio-ux4-pdca/pdca-run-phase.sh
  require_file scripts/fl-studio-ux4-pdca/cursor-agent-run-phase.sh
  require_file "${PROMPTS_DIR}/V00-scaffold.md"
  require_file "${PROMPTS_DIR}/V05-closeout.md"
  grep -q 'Composer 2.5' "${MASTER_SEQ}" || fail "master sequence must specify Composer 2.5"
  grep -q 'V05' scripts/fl-studio-ux4-pdca/SEQUENCE.yaml || fail "SEQUENCE missing V05"
  require_all_fls4_in_master
}

gate_v01() {
  gate_v00
  require_file "${SERVE_PY}"
  grep_file '/api/nested-roadmap-config' "${SERVE_PY}" 'V01 /api/nested-roadmap-config in serve.py'
  require_file "${NESTED_HORIZON}"
  require_file "${NESTED_FRAME}"
  grep_file 'NestedRoadmapHorizon' "${NESTED_FRAME}" \
    'V01 NestedRoadmapWorkspaceFrame imports NestedRoadmapHorizon'
  grep_file_absent 'nested-roadmap-view\.html' "${NESTED_FRAME}" \
    'V01 no nested-roadmap-view.html iframe src in NestedRoadmapWorkspaceFrame'
}

gate_v02() {
  gate_v01
  require_file "${WEBSITES_BROWSE}"
  grep_file '/local-site/' "${WEBSITES_BROWSE}" 'V02 WebsitesBrowsePage uses /local-site/'
  grep_file_absent '/websites/browse' "${WEBSITES_BROWSE}" \
    'V02 no /websites/browse in WebsitesBrowsePage'
  require_file "${BOARDS_HUB}"
  grep_file_absent 'FULL_WORKSPACE_UI\.openFullBoardEditor' "${BOARDS_HUB}" \
    'V02 no FULL_WORKSPACE_UI.openFullBoardEditor in BoardsArtifactsHub'
}

gate_v03() {
  gate_v02
  require_file "${APP_TSX}"
  grep_file 'lazy.*HomePage|HomePage.*lazy' "${APP_TSX}" 'V03 lazy HomePage in App.tsx'
  require_file "${VITE_CONFIG}"
  grep_file 'manualChunks' "${VITE_CONFIG}" 'V03 manualChunks in vite.config.ts'
}

gate_v04() {
  gate_v03
  require_file "${SERVE_PY}"
  grep_file '_studio_redirect' "${SERVE_PY}" 'V04 _studio_redirect in serve.py'
  grep_file '/board' "${SERVE_PY}" 'V04 /board handling in serve.py'
  require_file "${HANDBOOK_RETIREMENT}"
  grep_file 'board|websites browse' "${HANDBOOK_RETIREMENT}" \
    'V04 handbook mentions board/websites browse retirement'
}

gate_v05() {
  gate_v04
  require_file "${CRAWL_V5}"
  grep -q 'lenses-studio-ux-backlog-v5' "${V05_PROMPT}" \
    || fail "V05: V05-closeout.md must reference lenses-studio-ux-backlog-v5 canvas path"
}

run_phase() {
  local p="$1"
  case "${p}" in
    V00) gate_v00 ;;
    V01) gate_v01 ;;
    V02) gate_v02 ;;
    V03) gate_v03 ;;
    V04) gate_v04 ;;
    V05) gate_v05 ;;
    *) fail "unknown phase: ${p}" ;;
  esac
  info "${p}" "CHECK GREEN"
}

if [[ "${PHASE}" == "all" ]]; then
  for p in V00 V01 V02 V03 V04 V05; do
    run_phase "${p}"
  done
else
  run_phase "${PHASE}"
fi
