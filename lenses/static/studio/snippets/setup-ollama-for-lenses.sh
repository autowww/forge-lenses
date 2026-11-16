#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Ollama one-shot setup for Forge Lenses (LLM chat → provider "ollama").
#
# Run as your normal user (NOT with sudo — root's PATH often hides `ollama`).
#
# From the forge-lenses repo root:
#   bash scripts/setup-ollama-for-lenses.sh
#
# Or from a copy in ~/Downloads:
#   bash ./setup-ollama-for-lenses.sh
#
# Environment:
#   OLLAMA_BASE_URL       optional for this script only (defaults to http://127.0.0.1:11434 for probes/pull).
#                         Lenses itself requires OLLAMA_BASE_URL to be set when using provider "ollama".
#   LENSES_OLLAMA_MODEL   default llama3.2 (must match AI Setup / override)
#   OLLAMA_AUTO_INSTALL=1 run https://ollama.com/install.sh if `ollama` is missing
#                         (the installer may prompt for sudo itself)
# -----------------------------------------------------------------------------
set -euo pipefail

BASE="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
BASE="${BASE%/}"
MODEL="${LENSES_OLLAMA_MODEL:-llama3.2}"

log() { printf '%s\n' "$*"; }

# Common install locations (helpful after manual install or when PATH is minimal)
for _d in /usr/local/bin /opt/homebrew/bin "${HOME}/.local/bin"; do
  if [[ -x "${_d}/ollama" ]]; then
    case ":${PATH}:" in *":${_d}:"*) ;; *) PATH="${_d}:${PATH}" ;; esac
  fi
done
export PATH

if [[ "${EUID:-0}" -eq 0 ]] && [[ "${OLLAMA_ALLOW_ROOT:-}" != "1" ]]; then
  log "[ollama-setup] You are running as root (e.g. sudo). That often breaks this script."
  log "  Run as your normal user instead, from the folder that contains this file:"
  log "    bash ./setup-ollama-for-lenses.sh"
  log "  If you really need root, set OLLAMA_ALLOW_ROOT=1 (not recommended)."
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  log "[ollama-setup] ERROR: curl is required."
  exit 1
fi

api_ok() {
  curl -fsS -m 3 "${BASE}/api/tags" >/dev/null 2>&1
}

if ! command -v ollama >/dev/null 2>&1; then
  log "[ollama-setup] Ollama CLI not found in PATH."
  if [[ "${OLLAMA_AUTO_INSTALL:-}" == "1" ]]; then
    log "[ollama-setup] Running official installer: https://ollama.com/install.sh"
    curl -fsSL https://ollama.com/install.sh | sh
    # Installer usually places ollama in /usr/local/bin; refresh PATH
    for _d in /usr/local/bin /opt/homebrew/bin "${HOME}/.local/bin"; do
      if [[ -x "${_d}/ollama" ]]; then
        case ":${PATH}:" in *":${_d}:"*) ;; *) PATH="${_d}:${PATH}" ;; esac
      fi
    done
    export PATH
  else
    log "Install Ollama first (official one-liner), then run this script again:"
    log "  curl -fsSL https://ollama.com/install.sh | sh"
    log ""
    log "Or install and finish setup in one go (runs the same installer when needed):"
    log "  OLLAMA_AUTO_INSTALL=1 bash ./setup-ollama-for-lenses.sh"
    log ""
    log "Do not use sudo on this helper script — only the Ollama installer may ask for your password."
    exit 1
  fi
fi

if ! command -v ollama >/dev/null 2>&1; then
  log "[ollama-setup] ERROR: ollama is still not on PATH after install. Open a new terminal and retry."
  exit 1
fi

if ! api_ok; then
  log "[ollama-setup] API not up at ${BASE}; starting \`ollama serve\` in background..."
  nohup ollama serve >>"${TMPDIR:-/tmp}/ollama-lenses.log" 2>&1 &
  _i=0
  while [ "$_i" -lt 20 ]; do
    _i=$((_i + 1))
    sleep 1
    if api_ok; then
      log "[ollama-setup] Ollama API is reachable at ${BASE}"
      break
    fi
  done
fi

if ! api_ok; then
  log "[ollama-setup] ERROR: Still cannot reach ${BASE}/api/tags"
  log "Start Ollama manually or set OLLAMA_BASE_URL to your API base."
  exit 1
fi

log "[ollama-setup] Pulling model: ${MODEL}"
ollama pull "${MODEL}"

log "[ollama-setup] Done."
log "Lenses requires this in the environment before you start the server (use your probe URL above):"
log "  export OLLAMA_BASE_URL='${BASE}'"
log "Then: Open Lenses → LLM chat → Provider: ollama. The status strip should show “Ollama reachable”."
