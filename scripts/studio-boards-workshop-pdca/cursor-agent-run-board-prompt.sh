#!/usr/bin/env bash
# Run a Studio boards workshop PDCA prompt via Cursor CLI (`agent`).
set -euo pipefail

REPO_ROOT="${1:-.}"
PROMPT_ARG="${2:-}"
cd "$REPO_ROOT"

if [[ -z "$PROMPT_ARG" || ! -f "$PROMPT_ARG" ]]; then
  echo "Usage: $0 [REPO_ROOT] prompts/NN-name.md" >&2
  exit 1
fi

if ! command -v agent >/dev/null 2>&1; then
  echo "Cursor CLI (agent) not found. Install: https://cursor.com/docs/cli/overview" >&2
  exit 1
fi

ABS_PROMPT="$(cd "$(dirname "$PROMPT_ARG")" && pwd)/$(basename "$PROMPT_ARG")"
ROOT="$(pwd)"

AGENT_PROMPT="Repository root: ${ROOT}

Read and execute the PDCA prompt at: ${ABS_PROMPT}

Follow Plan → Do → Check → Adjust. Run pytest for sticker boards and product map when the prompt says Check. Rebuild Studio with: cd lenses-enterprise && npm run build

Do not use Classic /board as the primary workshop UI unless the prompt explicitly allows it."

EXTRA_FLAGS=()
if [[ -n "${BOARDS_CURSOR_AGENT_EXTRA:-}" ]]; then
  read -r -a EXTRA_FLAGS <<< "${BOARDS_CURSOR_AGENT_EXTRA}"
fi

exec agent -p --trust "${EXTRA_FLAGS[@]}" "${AGENT_PROMPT}"
