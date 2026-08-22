#!/usr/bin/env bash
# Forge Lenses Studio UX remediation PDCA phase gate.
# Usage: ./scripts/fl-studio-ux-pdca/check-phase-gate.sh <S00|…|S12|all>
#
# Cumulative gates S00–S12. Later phases assume earlier gates passed.
# S00 checks harness only; S01+ use grep patterns for post-implementation artifacts.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PHASE="${1:-}"
MASTER_SEQ="${REPO_ROOT}/docs/prompts/fl-studio-ux-pdca/00-master-sequence.md"
PROMPTS_DIR="${REPO_ROOT}/docs/prompts/fl-studio-ux-pdca"
LE="${REPO_ROOT}/lenses-enterprise/src"
SPLASH="${LE}/components/Splash.tsx"
WORKSPACE_CTX="${LE}/context/WorkspaceContext.tsx"
WORKSPACE_API="${LE}/api/workspace.ts"
SERVE_PY="${REPO_ROOT}/lenses/serve.py"
STUDIO_COPY="${LE}/nav/studioVisibleCopy.ts"
NAV_CFG="${LE}/nav/navigationConfig.ts"
TECH_DETAILS="${LE}/components/page/TechnicalDetails.tsx"
HEADER_MENU="${LE}/components/HeaderSettingsMenu.tsx"
LLM_FORM="${LE}/components/LlmSettingsForm.tsx"
PLAN_SCOPE="${LE}/components/plan/PlanScopeBar.tsx"
PROJECTS_PAGE="${LE}/pages/ProjectsPage.tsx"
PROJECT_DETAIL="${LE}/pages/ProjectDetailPage.tsx"
HOME_PAGE="${LE}/pages/HomePage.tsx"
PLAN_MATRIX="${LE}/pages/PlanMatrixPage.tsx"
PLAN_PAGE="${LE}/pages/PlanPage.tsx"
TIMELINE_PAGE="${LE}/pages/TimelinePage.tsx"
AGENTIC_PAGE="${LE}/pages/AgenticBridgePage.tsx"
BOARDS_HUB="${LE}/components/boards/BoardsArtifactsHub.tsx"
AUTONOMY_PAGE="${LE}/pages/AutonomyMaturityPage.tsx"
CRAWL_V2="${REPO_ROOT}/workbench/studio-ux-crawl-v2.mjs"
S12_PROMPT="${PROMPTS_DIR}/S12-closeout.md"

FLS_IDS=(
  FLS-001 FLS-002 FLS-003 FLS-004 FLS-005 FLS-006 FLS-007 FLS-008 FLS-009 FLS-010
  FLS-011 FLS-012 FLS-013 FLS-014 FLS-015 FLS-016 FLS-017 FLS-018 FLS-019 FLS-020
  FLS-021 FLS-022 FLS-023 FLS-024 FLS-025 FLS-026 FLS-027 FLS-028 FLS-029 FLS-030
  FLS-031 FLS-032 FLS-033 FLS-034 FLS-035 FLS-036 FLS-037 FLS-038 FLS-039 FLS-040
  FLS-041 FLS-042 FLS-043 FLS-044 FLS-045 FLS-046 FLS-047 FLS-048
)

[[ -n "${PHASE}" ]] || { echo "usage: $0 <S00|…|S12|all>" >&2; exit 1; }

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

require_all_fls_in_master() {
  local id
  for id in "${FLS_IDS[@]}"; do
    grep -q "${id}" "${MASTER_SEQ}" || fail "master sequence missing ${id}"
  done
}

gate_s00() {
  require_file "${MASTER_SEQ}"
  require_file scripts/fl-studio-ux-pdca/SEQUENCE.yaml
  require_file scripts/fl-studio-ux-pdca/check-phase-gate.sh
  require_file scripts/fl-studio-ux-pdca/pdca-run-phase.sh
  require_file scripts/fl-studio-ux-pdca/cursor-agent-run-phase.sh
  require_file "${PROMPTS_DIR}/S00-scaffold.md"
  require_file "${PROMPTS_DIR}/S12-closeout.md"
  grep -q 'Composer 2.5' "${MASTER_SEQ}" || fail "master sequence must specify Composer 2.5"
  grep -q 'S12' scripts/fl-studio-ux-pdca/SEQUENCE.yaml || fail "SEQUENCE missing S12"
  require_all_fls_in_master
}

gate_s01() {
  gate_s00
  require_file "${SPLASH}"
  grep_file 'progress|le-splash__progress|splashProgress|progressStage' "${SPLASH}" 'S01 splash progress'
  grep_any 'timeout|TIMEOUT|AbortSignal' 'S01 workspace client timeout' "${WORKSPACE_CTX}" "${WORKSPACE_API}"
  require_file "${SERVE_PY}"
  grep_file 'workspace-state|workspace_state' "${SERVE_PY}" 'S01 serve workspace-state route'
  grep_file 'timeout|TIMEOUT' "${SERVE_PY}" 'S01 serve timeout'
}

gate_s02() {
  gate_s01
  require_file "${STUDIO_COPY}"
  grep_file 'Backlog files' "${STUDIO_COPY}" 'S02 Backlog files rename'
  grep_file 'Documentation review' "${STUDIO_COPY}" 'S02 Documentation review rename'
  grep_file 'AI agents' "${STUDIO_COPY}" 'S02 AI agents rename'
  grep_file 'STUDIO_GLOSSARY' "${STUDIO_COPY}" 'S02 glossary'
  grep_file 'backlog:' "${STUDIO_COPY}" 'S02 glossary backlog entry'
}

gate_s03() {
  gate_s02
  require_file "${TECH_DETAILS}"
  grep_file 'inspect|canInspect|INSPECT|showTechnical' "${TECH_DETAILS}" 'S03 TechnicalDetails inspect gate'
  grep_any 'Labs' 'S03 Labs section in gear menu' "${NAV_CFG}" "${HEADER_MENU}"
  grep_file_absent 'Trace sample story' "${HOME_PAGE}" 'S03 no demo trace on Home'
  grep_file_absent 'Trace sample story' "${PLAN_PAGE}" 'S03 no demo trace on Plan'
  grep_file_absent 'Trace repo \\(demo\\)' "${PROJECT_DETAIL}" 'S03 no demo trace on Project'
}

gate_s04() {
  gate_s03
  require_file "${LLM_FORM}"
  grep_file 'trust|keys stay local|trustBanner|trustBoundary' "${LLM_FORM}" 'S04 AI Setup trust banner'
}

gate_s05() {
  gate_s04
  local wizard_found=0
  while IFS= read -r -d '' f; do
    if grep -qE 'FirstRun|first-run|StudioFirstRun|FirstRunWizard' "${f}"; then
      wizard_found=1
      break
    fi
  done < <(find "${LE}/components" -type f \( -name '*.tsx' -o -name '*.ts' \) -print0 2>/dev/null)
  [[ "${wizard_found}" -eq 1 ]] || fail 'S05: first-run wizard component not found under lenses-enterprise/src/components'
  require_file "${PLAN_SCOPE}"
  grep_file 'friendlyTitle|displayTitle|backlogLabel|humanLabel' "${PLAN_SCOPE}" 'S05 PlanScopeBar friendly titles'
  grep_any 'ReleaseChecklist|readinessPicker|discoveredRelease|releasePicker' 'S05 release checklist picker' \
    "${LE}/pages/MethodologyBridgePages.tsx"
}

gate_s06() {
  gate_s05
  grep_file 'healthTier|Ready|Watch|At risk' "${PROJECTS_PAGE}" 'S06 Projects Flow health tiers'
  grep_file 'suggestedNextStep|Suggested next step' "${PROJECT_DETAIL}" 'S06 suggested next step primary'
}

gate_s07() {
  gate_s06
  grep_file 'AttentionStrip|attentionStrip|PortfolioAttention|attention strip' "${HOME_PAGE}" 'S07 Home attention strip'
  grep_any 'DocsHealthSummary|documentationReviewSummary|Documentation review' 'S07 docs health summary' \
    "${HOME_PAGE}" "${LE}/components/docs-health"/*.tsx
}

gate_s08() {
  gate_s07
  grep_file 'milestoneTitle|outcomeTitle|milestone title' "${PLAN_MATRIX}" 'S08 matrix milestone titles'
  grep_any 'FreshnessChip|freshnessChip|freshnessLabel|confidence chip' 'S08 freshness chips' \
    "${PLAN_PAGE}" "${LE}/components/delivery"/*.tsx
  grep_file 'rememberScope|lastScope|scopeMemory|persistedScope' "${TIMELINE_PAGE}" 'S08 timeline scope memory'
}

gate_s09() {
  gate_s08
  grep_any 'StudioTour|OnboardingTour|tourSteps|inAppTour' 'S09 tour component' \
    "${LE}/components/onboarding"/*.tsx "${LE}/components"/*.tsx
  grep_any 'MondayChecklist|mondayChecklist|Monday checklist' 'S09 Monday checklist' "${HOME_PAGE}" "${LE}/components/home"/*.tsx
  grep_file 'StartHere|start-here|Start here|AgenticStartHere' "${AGENTIC_PAGE}" 'S09 agentic start-here'
  grep_any 'emptyGuidance|sampleCards|how to populate|How to populate' 'S09 knowledge empty guidance' \
    "${LE}/pages"/*Evidence*.tsx "${LE}/pages/SearchPage.tsx" "${LE}/pages"/*.tsx
}

gate_s10() {
  gate_s09
  grep_file 'unifiedEvidence|evidenceNoun|proofAndEvidence|evidenceBrowse' "${STUDIO_COPY}" 'S10 unified evidence naming'
  grep_file 'Labs' "${NAV_CFG}" 'S10 Labs IA'
  grep_file 'Foundry' "${NAV_CFG}" 'S10 Foundry demoted (still referenced under Labs)'
  grep_any 'Setup|Governance|Labs' 'S10 setup/governance/labs split' "${NAV_CFG}" "${HEADER_MENU}"
  grep_any 'ExecutiveSummaryStrip' 'S10 executive strip beyond Home' \
    "${LE}/components"/*.tsx "${LE}/pages/ProjectsPage.tsx"
  grep_any 'sticky|empty illustration|emptyIllustration' 'S10 matrix density' "${PLAN_MATRIX}"
  if grep -rE 'scan_only|local_fixture|feature_disabled' "${LE}" \
    --include='*.tsx' --include='*.ts' 2>/dev/null | grep -vE '\.test\.|\.work\.test\.'; then
    fail 'S10: internal status tokens still present in lenses-enterprise/src'
  fi
  grep_any 'When Studio uses|runner story|Docs review example' 'S10 Fleet trust story' \
    "${LE}/pages/FleetSettingsPage.tsx"
  grep_any 'sources.*default|defaultOpen.*sources|sourcesExpanded' 'S10 Copilot sources default' \
    "${LE}/components/CopilotPanel.tsx" "${LE}/components/LensesCopilotRail.tsx"
  grep_any 'Needs approval|Automatic vs|approvalSummary' 'S10 agent runtime summary' \
    "${LE}/pages/AgentRuntimeInspectPage.tsx"
  grep_any 'concreteNext|riskDestination|resolveRisk' 'S10 risk destinations' \
    "${LE}/components/projects/ProjectAtAGlance.tsx"
  grep_any 'owner.*lastUpdated|lastUpdated.*owner' 'S10 boards card face' "${BOARDS_HUB}"
  grep_file_absent 'All workspace entries' "${HOME_PAGE}" 'S10 collapse workspace directory on Home'
  grep_any 'workspaceName|workspaceLabel|basename.*workspace' 'S10 breadcrumb workspace identity' \
    "${LE}/components/Layout.tsx" "${LE}/components"/*.tsx
}

gate_s11() {
  gate_s10
  grep_file 'readinessStory|plainReadiness|readiness narrative|Ready to delegate' "${AUTONOMY_PAGE}" 'S11 autonomy narrative'
  grep_file 'PageHeader' "${BOARDS_HUB}" 'S11 PageHeader on Boards hub'
  grep_any 'siteHealth|healthSummary|readinessScore' 'S11 Publish site health' \
    "${LE}/pages/WebsitesPage.tsx"
  grep_any 'businessOutcome|outcomeField' 'S11 milestone outcome field' "${LE}/components/plan"/*.tsx
  grep_any 'localIdentity|guidedSignIn|workspaceProfile' 'S11 guided local identity' \
    "${HEADER_MENU}" "${LE}/components"/*.tsx
}

gate_s12() {
  gate_s11
  require_file "${CRAWL_V2}"
  grep -q 'lenses-studio-ux-backlog-v2' "${S12_PROMPT}" \
    || fail "S12: S12-closeout.md must reference lenses-studio-ux-backlog-v2 canvas path"
}

run_phase() {
  local p="$1"
  case "${p}" in
    S00) gate_s00 ;;
    S01) gate_s01 ;;
    S02) gate_s02 ;;
    S03) gate_s03 ;;
    S04) gate_s04 ;;
    S05) gate_s05 ;;
    S06) gate_s06 ;;
    S07) gate_s07 ;;
    S08) gate_s08 ;;
    S09) gate_s09 ;;
    S10) gate_s10 ;;
    S11) gate_s11 ;;
    S12) gate_s12 ;;
    *) fail "unknown phase: ${p}" ;;
  esac
  info "${p}" "CHECK GREEN"
}

if [[ "${PHASE}" == "all" ]]; then
  for p in S00 S01 S02 S03 S04 S05 S06 S07 S08 S09 S10 S11 S12; do
    run_phase "${p}"
  done
else
  run_phase "${PHASE}"
fi
