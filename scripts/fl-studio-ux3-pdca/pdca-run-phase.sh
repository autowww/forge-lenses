#!/usr/bin/env bash
# FL Studio UX3 PDCA runner — check or note phase.
# Usage: ./scripts/fl-studio-ux3-pdca/pdca-run-phase.sh <U00|…|U08> [check]

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PHASE="${1:-}"
MODE="${2:-check}"
[[ -n "${PHASE}" ]] || { echo "usage: $0 <U00|…|U08> [check]" >&2; exit 1; }
if [[ "${MODE}" == "check" ]]; then
  exec "${SCRIPT_DIR}/check-phase-gate.sh" "${PHASE}"
fi
echo "See docs/prompts/fl-studio-ux3-pdca/${PHASE}*.md for DO steps" >&2
exit 0
