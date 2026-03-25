#!/usr/bin/env bash
# Create .lenses-local/ (gitignored) and .lenses-repo/<github-login>/ (tracked) at a host repo root.
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

REPO_ROOT="$(resolve_repo_root)"
if [[ ! -d "$REPO_ROOT/.git" ]]; then
  echo "Not a git repository: $REPO_ROOT" >&2
  exit 1
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
echo "[lenses-startup] created: .lenses-repo/$GITHUB_LOGIN/ (.gitkeep)"
