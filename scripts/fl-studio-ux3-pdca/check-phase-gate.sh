#!/usr/bin/env bash
# Forge Lenses Studio UX3 remediation PDCA phase gate.
# Usage: ./scripts/fl-studio-ux3-pdca/check-phase-gate.sh <U00|…|U08|all>
#
# Cumulative gates U00–U08. Later phases assume earlier gates passed.
# U00 checks harness only; U01+ use grep patterns for post-implementation artifacts.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PHASE="${1:-}"
MASTER_SEQ="${REPO_ROOT}/docs/prompts/fl-studio-ux3-pdca/00-master-sequence.md"
PROMPTS_DIR="${REPO_ROOT}/docs/prompts/fl-studio-ux3-pdca"
LE="${REPO_ROOT}/lenses-enterprise"
LE_PAGES="${LE}/src/pages"
SERVE_PY="${REPO_ROOT}/lenses/serve.py"
TIMELINE_API="${REPO_ROOT}/lenses/timeline_api.py"
ROADMAP_PREVIEW="${LE}/src/components/plan/RoadmapSectionPreview.tsx"
ROADMAP_SECTION_PAGE="${LE_PAGES}/RoadmapSectionPage.tsx"
ROADMAP_DATE_EDITOR="${LE}/src/components/plan/RoadmapDateEditor.tsx"
TIMELINE_PAGE="${LE_PAGES}/TimelinePage.tsx"
PLAN_MATRIX="${LE_PAGES}/PlanMatrixPage.tsx"
ENTERPRISE_CSS="${LE}/src/enterprise-shell.css"
TOP_NAV="${LE}/src/components/TopNavigation.tsx"
E2E_MULTI_REPO="${REPO_ROOT}/tests/fixtures/e2e_multi_repo"
CRAWL_V4="${REPO_ROOT}/workbench/studio-ux-crawl-v4.mjs"
CRAWL_GATE="${REPO_ROOT}/scripts/studio-ux-crawl-gate.sh"
CI_YML="${REPO_ROOT}/.github/workflows/ci.yml"
U08_PROMPT="${PROMPTS_DIR}/U08-closeout.md"

FLS3_IDS=(
  FLS3-001 FLS3-002 FLS3-003 FLS3-004 FLS3-005 FLS3-006
)

[[ -n "${PHASE}" ]] || { echo "usage: $0 <U00|…|U08|all>" >&2; exit 1; }

cd "${REPO_ROOT}"

info() { echo "==> gate ${1}: $2"; }
fail() { echo "FAIL: $*" >&2; exit 1; }
require_file() { [[ -f "$1" ]] || fail "missing: $1"; }
require_dir() { [[ -d "$1" ]] || fail "missing directory: $1"; }

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

grep_tree_absent() {
  local pattern="$1"
  local dir="$2"
  local label="$3"
  if grep -rqE "${pattern}" "${dir}" 2>/dev/null; then
    fail "${label}: forbidden pattern found under ${dir}: ${pattern}"
  fi
}

require_all_fls3_in_master() {
  local id
  for id in "${FLS3_IDS[@]}"; do
    grep -q "${id}" "${MASTER_SEQ}" || fail "master sequence missing ${id}"
  done
}

gate_u00() {
  require_file "${MASTER_SEQ}"
  require_file scripts/fl-studio-ux3-pdca/SEQUENCE.yaml
  require_file scripts/fl-studio-ux3-pdca/check-phase-gate.sh
  require_file scripts/fl-studio-ux3-pdca/pdca-run-phase.sh
  require_file scripts/fl-studio-ux3-pdca/cursor-agent-run-phase.sh
  require_file "${PROMPTS_DIR}/U00-scaffold.md"
  require_file "${PROMPTS_DIR}/U08-closeout.md"
  grep -q 'Composer 2.5' "${MASTER_SEQ}" || fail "master sequence must specify Composer 2.5"
  grep -q 'U08' scripts/fl-studio-ux3-pdca/SEQUENCE.yaml || fail "SEQUENCE missing U08"
  require_all_fls3_in_master
}

gate_u01() {
  gate_u00
  require_dir "${E2E_MULTI_REPO}"
  require_file "${CRAWL_V4}"
  require_file "${CRAWL_GATE}"
  require_file "${CI_YML}"
  grep -q 'studio-ux-crawl-gate' "${CI_YML}" \
    || fail "U01: .github/workflows/ci.yml must reference studio-ux-crawl-gate"
}

gate_u02() {
  gate_u01
  grep_tree_absent 'FULL_WORKSPACE_UI' "${LE_PAGES}" 'U02 no FULL_WORKSPACE_UI in pages'
  grep_file_absent 'classicPlanHref' "${LE_PAGES}/PlanPage.tsx" 'U02 no classicPlanHref in PlanPage'
}

gate_u03() {
  gate_u02
  require_file "${SERVE_PY}"
  grep_file '_studio_redirect' "${SERVE_PY}" 'U03 _studio_redirect in serve.py'
  grep_file_absent 'page_plan|page_timeline|page_overview' "${SERVE_PY}" \
    'U03 no page_plan|page_timeline|page_overview in serve.py route branches'
}

gate_u04() {
  gate_u03
  require_file "${ROADMAP_PREVIEW}"
  require_file "${ROADMAP_SECTION_PAGE}"
  grep_file_absent 'dangerouslySetInnerHTML' "${ROADMAP_SECTION_PAGE}" \
    'U04 no dangerouslySetInnerHTML in RoadmapSectionPage'
}

gate_u05() {
  gate_u04
  require_file "${TIMELINE_API}"
  grep_file 'date_rows' "${TIMELINE_API}" 'U05 date_rows in timeline_api.py'
  require_file "${ROADMAP_DATE_EDITOR}"
  require_file "${TIMELINE_PAGE}"
  grep_file_absent 'ForgeRoadmapDates' "${TIMELINE_PAGE}" 'U05 no ForgeRoadmapDates in TimelinePage'
}

gate_u06() {
  gate_u05
  require_file "${PLAN_MATRIX}"
  grep_file 'getOverviewChartPayload|perRepoLinesByKey' "${PLAN_MATRIX}" \
    'U06 getOverviewChartPayload or perRepoLinesByKey in PlanMatrixPage'
  require_file "${ENTERPRISE_CSS}"
  grep_file 'healthTier' "${ENTERPRISE_CSS}" 'U06 healthTier CSS in enterprise-shell.css'
}

gate_u07() {
  gate_u06
  require_file "${TOP_NAV}"
  grep_file 'PublishHealthPopover' "${TOP_NAV}" 'U07 PublishHealthPopover in TopNavigation'
}

gate_u08() {
  gate_u07
  require_file "${CRAWL_V4}"
  grep -q 'lenses-studio-ux-backlog-v4' "${U08_PROMPT}" \
    || fail "U08: U08-closeout.md must reference lenses-studio-ux-backlog-v4 canvas path"
}

run_phase() {
  local p="$1"
  case "${p}" in
    U00) gate_u00 ;;
    U01) gate_u01 ;;
    U02) gate_u02 ;;
    U03) gate_u03 ;;
    U04) gate_u04 ;;
    U05) gate_u05 ;;
    U06) gate_u06 ;;
    U07) gate_u07 ;;
    U08) gate_u08 ;;
    *) fail "unknown phase: ${p}" ;;
  esac
  info "${p}" "CHECK GREEN"
}

if [[ "${PHASE}" == "all" ]]; then
  for p in U00 U01 U02 U03 U04 U05 U06 U07 U08; do
    run_phase "${p}"
  done
else
  run_phase "${PHASE}"
fi
