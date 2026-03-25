#!/usr/bin/env bash
# Create .lenses-local/ (gitignored) and .lenses-repo/<github-login>/ (tracked) at the
# parent/host git repo root — not inside forge-lenses/ when forge-lenses is a submodule.
# Standalone forge-lenses clone: data dirs stay at this repo root.
#
# Non-overwrite policy: never truncate user content. This script only:
#   - mkdir -p for .lenses-local and .lenses-repo/<login>/
#   - creates .gitkeep if absent
#   - appends one .gitignore line if missing (never replaces an existing .gitignore)
#   - creates README.txt under .lenses-repo/<login>/ only if absent
#
# Works when REPO_ROOT is a submodule ( .git may be a file, not a directory ).
#
# GitHub login: gh api user → else parse origin (github.com).
set -euo pipefail

resolve_repo_root() {
  if [[ -n "${REPO_ROOT:-}" ]]; then
    echo "$(cd "$REPO_ROOT" && pwd)"
    return
  fi
  if git rev-parse --show-toplevel >/dev/null 2>&1; then
    git rev-parse --show-toplevel
    return
  fi
  echo "Set REPO_ROOT to the git repository root or run inside a git repo." >&2
  exit 1
}

login_via_gh() {
  command -v gh >/dev/null 2>&1 || return 1
  gh api user -q .login 2>/dev/null || return 1
}

login_via_origin() {
  local url owner
  url=$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || true)
  [[ -z "$url" ]] && return 1
  if [[ "$url" =~ https://github\.com/([^/]+)/ ]]; then
    owner="${BASH_REMATCH[1]}"
  elif [[ "$url" =~ git@github\.com:([^/]+)/ ]]; then
    owner="${BASH_REMATCH[1]}"
  else
    return 1
  fi
  owner="${owner%.git}"
  printf '%s\n' "$owner"
}

sanitize_login() {
  local s="${1,,}"
  s="${s//[^a-z0-9_-]/}"
  if [[ -z "$s" || "$s" == *..* ]]; then
    return 1
  fi
  printf '%s\n' "$s"
}

# If cwd (or REPO_ROOT) is a submodule checkout, use superproject root for .lenses-* .
elevate_to_host_repo_if_submodule() {
  local initial="$1"
  local super
  super="$(git -C "$initial" rev-parse --show-superproject-working-tree 2>/dev/null || true)"
  super="${super//$'\r'/}"
  super="${super//$'\n'/}"
  if [[ -z "$super" ]]; then
    printf '%s\n' "$initial"
    return
  fi
  if git -C "$super" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    (cd "$super" && pwd)
    return
  fi
  printf '%s\n' "$initial"
}

INITIAL_ROOT="$(resolve_repo_root)"
REPO_ROOT="$(elevate_to_host_repo_if_submodule "$INITIAL_ROOT")"
if ! git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not a git repository: $REPO_ROOT" >&2
  exit 1
fi
if [[ "$REPO_ROOT" != "$INITIAL_ROOT" ]]; then
  echo "[lenses-startup] host repo: $REPO_ROOT  (submodule checkout was: $INITIAL_ROOT)" >&2
fi

RAW_LOGIN=""
if RAW_LOGIN="$(login_via_gh)"; then
  RAW_LOGIN="${RAW_LOGIN//$'\r'/}"
  RAW_LOGIN="${RAW_LOGIN//$'\n'/}"
fi
if [[ -z "${RAW_LOGIN:-}" ]]; then
  RAW_LOGIN="$(login_via_origin)" || true
  RAW_LOGIN="${RAW_LOGIN//$'\r'/}"
  RAW_LOGIN="${RAW_LOGIN//$'\n'/}"
fi

GITHUB_LOGIN=""
if out="$(sanitize_login "${RAW_LOGIN:-}")"; then
  GITHUB_LOGIN="$out"
fi

if [[ -z "$GITHUB_LOGIN" ]]; then
  echo "[lenses-startup] Could not resolve GitHub login." >&2
  echo "  Run: gh auth login" >&2
  echo "  Or set git remote origin to a github.com URL." >&2
  exit 1
fi

mkdir -p "$REPO_ROOT/.lenses-local"
mkdir -p "$REPO_ROOT/.lenses-repo/$GITHUB_LOGIN"
if [[ ! -f "$REPO_ROOT/.lenses-repo/$GITHUB_LOGIN/.gitkeep" ]]; then
  : >"$REPO_ROOT/.lenses-repo/$GITHUB_LOGIN/.gitkeep"
fi

README="$REPO_ROOT/.lenses-repo/$GITHUB_LOGIN/README.txt"
if [[ ! -f "$README" ]]; then
  cat >"$README" <<'EOF'
# This folder (.lenses-repo/<login>/)

Put files here that should be committed with the repository (team-visible).

The sibling .lenses-local/ at the repository root is gitignored for machine-only state.

See forge-lenses README (Host repo data directories) for details.
EOF
fi

GIGN="$REPO_ROOT/.gitignore"
LINE=".lenses-local/"
if [[ -f "$GIGN" ]]; then
  if ! grep -qxF "$LINE" "$GIGN" 2>/dev/null; then
    printf '\n# lenses — machine-local state (forge-lenses)\n%s\n' "$LINE" >>"$GIGN"
  fi
else
  printf '# lenses — machine-local state (forge-lenses)\n%s\n' "$LINE" >"$GIGN"
fi

echo "[lenses-startup] repo:    $REPO_ROOT"
echo "[lenses-startup] login:   $GITHUB_LOGIN"
echo "[lenses-startup] created: .lenses-local/"
echo "[lenses-startup] created: .lenses-repo/$GITHUB_LOGIN/ (.gitkeep, README.txt if absent)"
