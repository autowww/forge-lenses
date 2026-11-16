#!/usr/bin/env bash
# Rebuild local handbook HTML for declared dual-wiki surfaces (no Firebase, no commit).
# Usage: ./scripts/refresh-dual-wiki.sh --repo <hint> --change <slug> [--dry-run]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

REPO_HINT=""
CHANGE_SLUG=""
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO_HINT="${2:-}"; shift 2 ;;
    --change) CHANGE_SLUG="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

[[ -n "${REPO_HINT}" && -n "${CHANGE_SLUG}" ]] || {
  echo "usage: $0 --repo <hint> --change <slug> [--dry-run]" >&2
  exit 2
}

_repo_base() {
  if [[ -z "${REPO_HINT}" ]]; then
    echo "${ROOT}"
  else
    echo "${ROOT}/${REPO_HINT}"
  fi
}

pick_dir() {
  local name="$1"
  shift
  local d
  for d in "$@"; do
    [[ -d "${d}" ]] && { echo "${d}"; return 0; }
  done
  return 1
}

REPO_BASE="$(_repo_base)"
PROPOSAL="${REPO_BASE}/openspec/changes/${CHANGE_SLUG}/proposal.md"
[[ -f "${PROPOSAL}" ]] || { echo "missing proposal: ${PROPOSAL}" >&2; exit 1; }

BPW="$(pick_dir bpw \
  "${ROOT}/blueprints-website" \
  "${HOME}/Code/blueprints-website" || true)"
FLSW="$(pick_dir flsw \
  "${ROOT}/forge-lenses-website" \
  "${HOME}/Code/forge-lenses-website" || true)"
FORGE="$(pick_dir forgesdlc \
  "${ROOT}/forgesdlc" \
  "${HOME}/Code/forgesdlc" || true)"

# Parse handbook shells from proposal (python helper in forge-lenses when present)
SHELLS=""
FL_ROOT="${ROOT}"
if [[ -d "${ROOT}/forge-lenses" ]]; then
  FL_ROOT="${ROOT}/forge-lenses"
fi
if [[ -f "${FL_ROOT}/lenses/dual_wiki.py" ]]; then
  SHELLS="$(cd "${FL_ROOT}" && python3 -c "
from pathlib import Path
from lenses.dual_wiki import parse_dual_wiki_surfaces
text = Path('${PROPOSAL}').read_text(encoding='utf-8')
for s in parse_dual_wiki_surfaces(text, repo_hint='${REPO_HINT}'):
    print(s.get('handbook_shell',''))
" 2>/dev/null | sort -u | grep -v '^none$' || true)"
fi
if [[ -z "${SHELLS}" ]]; then
  if [[ "${REPO_HINT}" == *lenses* ]]; then
    SHELLS="flsw"
  else
    SHELLS="bpw"
  fi
fi

run_build() {
  local label="$1"
  local dir="$2"
  local cmd="$3"
  if [[ -z "${dir}" || ! -d "${dir}" ]]; then
    echo "skip ${label}: directory absent"
    return 0
  fi
  echo "==> ${label}: ${dir}"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "    dry-run: cd ${dir} && ${cmd}"
    return 0
  fi
  (cd "${dir}" && eval "${cmd}")
}

while IFS= read -r shell; do
  [[ -z "${shell}" ]] && continue
  case "${shell}" in
    bpw|blueprints-website)
      run_build "blueprints-website" "${BPW}" \
        "python3 generator/build-handbook.py --all && python3 generator/inject-portal-nav.py"
      ;;
    flsw|forge-lenses-website)
      run_build "forge-lenses-website" "${FLSW}" \
        "python3 generator/build-site.py"
      ;;
    forgesdlc)
      run_build "forgesdlc" "${FORGE}" \
        "python3 generator/build-site.py"
      ;;
    *)
      echo "skip unknown shell: ${shell}"
      ;;
  esac
done <<< "${SHELLS}"

echo "refresh-dual-wiki: done (local HTML only; no Firebase publish)"
