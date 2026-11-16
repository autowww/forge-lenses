#!/usr/bin/env bash
# Forge Lenses Studio UX2 remediation PDCA phase gate.
# Usage: ./scripts/fl-studio-ux2-pdca/check-phase-gate.sh <T00|…|T09|all>
#
# Cumulative gates T00–T09. Later phases assume earlier gates passed.
# T00 checks harness only; T01+ use grep patterns for post-implementation artifacts.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PHASE="${1:-}"
MASTER_SEQ="${REPO_ROOT}/docs/prompts/fl-studio-ux2-pdca/00-master-sequence.md"
PROMPTS_DIR="${REPO_ROOT}/docs/prompts/fl-studio-ux2-pdca"
LE="${REPO_ROOT}/lenses-enterprise"
LE_SRC="${LE}/src"
PACKAGE_JSON="${LE}/package.json"
ORACLE_SPEC="${LE}/e2e/studio-human-copy-oracle.spec.ts"
ORACLE_SCRIPT="${REPO_ROOT}/scripts/studio-human-copy-oracle.sh"
SPARSE_GUIDE="${LE_SRC}/components/onboarding/WorkspaceSparseGuide.tsx"
DOCS_MGMT_SUMMARY="${LE_SRC}/components/doc-management/DocsManagementSummary.tsx"
AUTONOMY_PAGE="${LE_SRC}/pages/AutonomyMaturityPage.tsx"
APP_TSX="${LE_SRC}/App.tsx"
VITE_CONFIG="${LE}/vite.config.ts"
TOP_NAV="${LE_SRC}/components/TopNavigation.tsx"
PLAN_CLUSTER="${LE_SRC}/components/plan/PlanningClusterPageHeader.tsx"
SERVE_PY="${REPO_ROOT}/lenses/serve.py"
TIMELINE_GANTT="${LE_SRC}/components/plan/TimelineGantt.tsx"
TIMELINE_PAGE="${LE_SRC}/pages/TimelinePage.tsx"
PLAN_MATRIX="${LE_SRC}/pages/PlanMatrixPage.tsx"
HEADER_MENU="${LE_SRC}/components/HeaderSettingsMenu.tsx"
TELEMETRY="${LE_SRC}/telemetry/studioTelemetry.ts"
CLASSIC_RETIREMENT_DOC="${REPO_ROOT}/docs/handbook-public/studio-classic-ui-retirement.md"
CRAWL_V3="${REPO_ROOT}/workbench/studio-ux-crawl-v3.mjs"
T09_PROMPT="${PROMPTS_DIR}/T09-closeout.md"

FLS2_IDS=(
  FLS2-001 FLS2-002 FLS2-003 FLS2-004 FLS2-005 FLS2-006
  FLS2-007 FLS2-008 FLS2-009 FLS2-010 FLS2-011 FLS2-012
)

[[ -n "${PHASE}" ]] || { echo "usage: $0 <T00|…|T09|all>" >&2; exit 1; }

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

grep_any() {
  local pattern="$1"
  local label="$2"
  shift 2
  local f
  for f in "$@"; do
    if [[ -f "${f}" ]] && grep -qE "${pattern}" "${f}"; then
      return 0
    fi
  done
  fail "${label}: pattern not found in any of: $*"
}

require_all_fls2_in_master() {
  local id
  for id in "${FLS2_IDS[@]}"; do
    grep -q "${id}" "${MASTER_SEQ}" || fail "master sequence missing ${id}"
  done
}

gate_t00() {
  require_file "${MASTER_SEQ}"
  require_file scripts/fl-studio-ux2-pdca/SEQUENCE.yaml
  require_file scripts/fl-studio-ux2-pdca/check-phase-gate.sh
  require_file scripts/fl-studio-ux2-pdca/pdca-run-phase.sh
  require_file scripts/fl-studio-ux2-pdca/cursor-agent-run-phase.sh
  require_file "${PROMPTS_DIR}/T00-scaffold.md"
  require_file "${PROMPTS_DIR}/T09-closeout.md"
  grep -q 'Composer 2.5' "${MASTER_SEQ}" || fail "master sequence must specify Composer 2.5"
  grep -q 'T09' scripts/fl-studio-ux2-pdca/SEQUENCE.yaml || fail "SEQUENCE missing T09"
  require_all_fls2_in_master
}

gate_t01() {
  gate_t00
  require_file "${ORACLE_SPEC}"
  require_file "${PACKAGE_JSON}"
  grep_file 'test:e2e:human-copy|human-copy-oracle' "${PACKAGE_JSON}" 'T01 human-copy npm script'
  require_file "${SPARSE_GUIDE}"
}

gate_t02() {
  gate_t01
  require_file "${DOCS_MGMT_SUMMARY}"
  if grep -qE 'PageHeader' "${AUTONOMY_PAGE}" 2>/dev/null; then
    return 0
  fi
  grep_file 'AutonomyMaturityPage' "${APP_TSX}" 'T02 autonomy route in App.tsx'
  grep_file 'import.*AutonomyMaturityPage|AutonomyMaturityPage' "${APP_TSX}" 'T02 autonomy eager import in App.tsx'
}

gate_t03() {
  gate_t02
  require_file "${VITE_CONFIG}"
  grep_file 'manualChunks' "${VITE_CONFIG}" 'T03 vite manualChunks'
}

gate_t04() {
  gate_t03
  require_file "${TOP_NAV}"
  grep_file 'publishHealth' "${TOP_NAV}" 'T04 publishHealth in TopNavigation'
  grep_file 'ExecutiveSummaryStrip' "${PLAN_CLUSTER}" 'T04 ExecutiveSummaryStrip in plan cluster'
  grep_any 'ExecutiveSummaryStrip' 'T04 ExecutiveSummaryStrip in knowledge' \
    "${LE_SRC}/pages"/*Knowledge*.tsx \
    "${LE_SRC}/pages/SearchPage.tsx" \
    "${LE_SRC}/components/knowledge"/*.tsx
}

gate_t05() {
  gate_t04
  require_file "${SERVE_PY}"
  grep_file 'gantt_bars' "${SERVE_PY}" 'T05 gantt_bars in timeline API'
  require_file "${TIMELINE_GANTT}"
  require_file "${TIMELINE_PAGE}"
  grep_file_absent 'dangerouslySetInnerHTML.*gantt_html|gantt_html.*dangerouslySetInnerHTML' "${TIMELINE_PAGE}" \
    'T05 no dangerouslySetInnerHTML for gantt_html in TimelinePage'
}

gate_t06() {
  gate_t05
  require_file "${PLAN_MATRIX}"
  grep_file 'healthTier|milestoneSparkline' "${PLAN_MATRIX}" 'T06 matrix healthTier or milestoneSparkline'
}

gate_t07() {
  gate_t06
  require_file "${HEADER_MENU}"
  grep_file 'workspaceProfile|guidedSignIn' "${HEADER_MENU}" 'T07 workspaceProfile or guidedSignIn in HeaderSettingsMenu'
}

gate_t08() {
  gate_t07
  require_file "${TELEMETRY}"
  grep_file 'recordTourStep' "${TELEMETRY}" 'T08 recordTourStep in studioTelemetry'
  grep_file 'recordFirstRunWizardStep' "${TELEMETRY}" 'T08 recordFirstRunWizardStep in studioTelemetry'
  require_file "${CLASSIC_RETIREMENT_DOC}"
}

gate_t09() {
  gate_t08
  require_file "${CRAWL_V3}"
  grep -q 'lenses-studio-ux-backlog-v3' "${T09_PROMPT}" \
    || fail "T09: T09-closeout.md must reference lenses-studio-ux-backlog-v3 canvas path"
}

run_phase() {
  local p="$1"
  case "${p}" in
    T00) gate_t00 ;;
    T01) gate_t01 ;;
    T02) gate_t02 ;;
    T03) gate_t03 ;;
    T04) gate_t04 ;;
    T05) gate_t05 ;;
    T06) gate_t06 ;;
    T07) gate_t07 ;;
    T08) gate_t08 ;;
    T09) gate_t09 ;;
    *) fail "unknown phase: ${p}" ;;
  esac
  info "${p}" "CHECK GREEN"
}

if [[ "${PHASE}" == "all" ]]; then
  for p in T00 T01 T02 T03 T04 T05 T06 T07 T08 T09; do
    run_phase "${p}"
  done
else
  run_phase "${PHASE}"
fi
