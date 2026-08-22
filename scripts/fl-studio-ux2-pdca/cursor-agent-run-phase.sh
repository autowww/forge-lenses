#!/usr/bin/env bash
# Run an FL Studio UX2 PDCA phase via Cursor CLI (`agent`).
set -euo pipefail

REPO_ROOT="${1:-.}"
PHASE="${2:-}"
cd "$REPO_ROOT"

if [[ -z "$PHASE" ]]; then
  echo "Usage: $0 [REPO_ROOT] <T00|…|T09>" >&2
  exit 1
fi

PROMPT_GLOB="docs/prompts/fl-studio-ux2-pdca/${PHASE}*.md"
shopt -s nullglob
matches=( ${PROMPT_GLOB} )
shopt -u nullglob
if [[ ${#matches[@]} -eq 0 ]]; then
  echo "No prompt file matching ${PROMPT_GLOB}" >&2
  exit 1
fi
PROMPT_ARG="${matches[0]}"

if ! command -v agent >/dev/null 2>&1; then
  echo "Cursor CLI (agent) not found. Install: https://cursor.com/docs/cli/overview" >&2
  exit 1
fi

ABS_PROMPT="$(cd "$(dirname "$PROMPT_ARG")" && pwd)/$(basename "$PROMPT_ARG")"
ROOT="$(pwd)"
MODEL="${FL_STUDIO_UX2_PDCA_MODEL:-composer-2.5}"

AGENT_PROMPT="Repository root: ${ROOT}

Read and execute the PDCA prompt at: ${ABS_PROMPT}

Executor model: Composer 2.5 (standard, not -fast).

Follow Plan → Do → Check → Act. Run the phase gate when the prompt says Check:
  scripts/fl-studio-ux2-pdca/check-phase-gate.sh ${PHASE}

Rebuild Studio when UI changes: cd lenses-enterprise && npm run build

Do not skip cumulative gates — fix until ${PHASE} gate is green before closing the phase."

EXTRA_FLAGS=(--model "${MODEL}")
if [[ -n "${FL_STUDIO_UX2_CURSOR_AGENT_EXTRA:-}" ]]; then
  read -r -a USER_FLAGS <<< "${FL_STUDIO_UX2_CURSOR_AGENT_EXTRA}"
  EXTRA_FLAGS+=("${USER_FLAGS[@]}")
fi

exec agent -p --trust "${EXTRA_FLAGS[@]}" "${AGENT_PROMPT}"
