#!/usr/bin/env bash
# Forge Lenses Studio UX5 remediation PDCA phase gate.
# Usage: ./scripts/fl-studio-ux5-pdca/check-phase-gate.sh <W00|…|W05|all>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PHASE="${1:-}"
MASTER_SEQ="${REPO_ROOT}/docs/prompts/fl-studio-ux5-pdca/00-master-sequence.md"
PROMPTS_DIR="${REPO_ROOT}/docs/prompts/fl-studio-ux5-pdca"
LE="${REPO_ROOT}/lenses-enterprise"
RENDER_PY="${REPO_ROOT}/lenses/render.py"
APP_TSX="${LE}/src/App.tsx"
VITE_CONFIG="${LE}/vite.config.ts"
NESTED_HORIZON="${LE}/src/components/plan/NestedRoadmapHorizon.tsx"
SITE_SHELL="${LE}/src/components/sites/SitePreviewShell.tsx"
WEBSITES_BROWSE="${LE}/src/pages/WebsitesBrowsePage.tsx"
LOCAL_REDIRECT="${LE}/src/pages/LocalSiteRedirect.tsx"
CRAWL_V6="${REPO_ROOT}/workbench/studio-ux-crawl-v6.mjs"
W05_PROMPT="${PROMPTS_DIR}/W05-closeout.md"
STUDIO_ASSETS="${REPO_ROOT}/lenses/static/studio/assets"
INDEX_LIMIT_BYTES=600000

FLS5_IDS=(
  FLS5-001 FLS5-002 FLS5-003 FLS5-004
)

[[ -n "${PHASE}" ]] || { echo "usage: $0 <W00|…|W05|all>" >&2; exit 1; }

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

require_all_fls5_in_master() {
  local id
  for id in "${FLS5_IDS[@]}"; do
    grep -q "${id}" "${MASTER_SEQ}" || fail "master sequence missing ${id}"
  done
}

gate_w00() {
  require_file "${MASTER_SEQ}"
  require_file scripts/fl-studio-ux5-pdca/SEQUENCE.yaml
  require_file scripts/fl-studio-ux5-pdca/check-phase-gate.sh
  require_file scripts/fl-studio-ux5-pdca/pdca-run-phase.sh
  require_file scripts/fl-studio-ux5-pdca/cursor-agent-run-phase.sh
  require_file "${PROMPTS_DIR}/W00-scaffold.md"
  require_file "${PROMPTS_DIR}/W05-closeout.md"
  grep -q 'Composer 2.5' "${MASTER_SEQ}" || fail "master sequence must specify Composer 2.5"
  grep -q 'W05' scripts/fl-studio-ux5-pdca/SEQUENCE.yaml || fail "SEQUENCE missing W05"
  require_all_fls5_in_master
}

gate_w01() {
  gate_w00
  require_file "${NESTED_HORIZON}"
  grep_file 'modal-backdrop--open' "${NESTED_HORIZON}" 'W01 modal open animation class'
  grep_file 'nested-roadmap-tier-detail' "${NESTED_HORIZON}" 'W01 tier detail panel'
  grep_file 'Escape' "${NESTED_HORIZON}" 'W01 Escape closes modal'
}

gate_w02() {
  gate_w01
  require_file "${SITE_SHELL}"
  require_file "${WEBSITES_BROWSE}"
  require_file "${LOCAL_REDIRECT}"
  grep_file 'SitePreviewShell' "${WEBSITES_BROWSE}" 'W02 SitePreviewShell used in WebsitesBrowsePage'
  grep_file 'LocalSiteRedirect' "${APP_TSX}" 'W02 LocalSiteRedirect route in App'
  grep_file 'websites/browse/:site/\*' "${APP_TSX}" 'W02 splat route for site subpaths'
}

gate_w03() {
  gate_w02
  require_file "${APP_TSX}"
  grep_file 'lazy.*Layout|Layout.*lazy' "${APP_TSX}" 'W03 lazy Layout in App.tsx'
  require_file "${VITE_CONFIG}"
  grep_file "'copilot'" "${VITE_CONFIG}" 'W03 copilot manualChunk in vite.config.ts'
  grep_file "'layout'" "${VITE_CONFIG}" 'W03 layout manualChunk in vite.config.ts'
}

gate_w04() {
  gate_w03
  require_file "${RENDER_PY}"
  grep_file_absent '^def page_plan\(' "${RENDER_PY}" 'W04 page_plan removed from render.py'
  grep_file_absent '^def page_timeline\(' "${RENDER_PY}" 'W04 page_timeline removed from render.py'
  require_file tests/test_classic_pages_retired.py
  grep_file_absent 'test_plan_page_html' tests/test_classic_pages_retired.py \
    'W04 no legacy plan page html tests'
}

index_chunk_size_ok() {
  local idx
  idx="$(find "${STUDIO_ASSETS}" -maxdepth 1 -name 'index-*.js' -type f 2>/dev/null | head -1)"
  [[ -n "${idx}" ]] || fail "W05: no index-*.js under ${STUDIO_ASSETS} — run npm run build in lenses-enterprise"
  local size
  size="$(stat -c%s "${idx}")"
  if [[ "${size}" -ge "${INDEX_LIMIT_BYTES}" ]]; then
    fail "W05: index chunk ${idx} is ${size} bytes (limit ${INDEX_LIMIT_BYTES})"
  fi
  info W05 "index chunk ${size} bytes (< ${INDEX_LIMIT_BYTES})"
}

gate_w05() {
  gate_w04
  require_file "${CRAWL_V6}"
  grep -q 'lenses-studio-ux-backlog-v6' "${W05_PROMPT}" \
    || fail "W05: W05-closeout.md must reference lenses-studio-ux-backlog-v6 canvas path"
  index_chunk_size_ok
}

run_phase() {
  local p="$1"
  case "${p}" in
    W00) gate_w00 ;;
    W01) gate_w01 ;;
    W02) gate_w02 ;;
    W03) gate_w03 ;;
    W04) gate_w04 ;;
    W05) gate_w05 ;;
    *) fail "unknown phase: ${p}" ;;
  esac
  info "${p}" "CHECK GREEN"
}

if [[ "${PHASE}" == "all" ]]; then
  for p in W00 W01 W02 W03 W04 W05; do
    run_phase "${p}"
  done
else
  run_phase "${PHASE}"
fi
