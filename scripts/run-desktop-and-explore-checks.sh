#!/usr/bin/env bash
# Run desktop npm ci, Studio screenshot tour, Python tests, and Playwright Electron smoke.
# Starts Lenses on LENSES_PORT if /studio/ is not reachable; restarts it if the tour hits connection errors.
#
# Env: STUDIO_EXPLORE_MODE=full → capture all Studio routes (tours/full-studio-ui/tour.yaml).
# Screenshot output defaults to ../.workspace-screenshots/<repo>/studio-explore/<run-id>/ (see desktop/studio-explore/runner.mjs).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${LENSES_PORT:-8080}"
HOST="${LENSES_BIND:-127.0.0.1}"
BASE_URL="http://${HOST}:${PORT}"
STUDIO_URL="${BASE_URL}/studio/"

export FORGE_LENSES_ROOT="$ROOT"
export LENSES_WORKSPACE_ROOT="${LENSES_WORKSPACE_ROOT:-$ROOT}"
export PYTHONPATH="$ROOT"
export LENSES_BASE_URL="$BASE_URL"

PID_FILE="/tmp/lenses-checks-${PORT}.pid"
LOG_FILE="/tmp/lenses-checks-${PORT}.log"
OUR_SERVER=0

log() { echo "[checks] $*"; }

studio_ok() {
  curl -sf -o /dev/null --connect-timeout 2 --max-time 5 "$STUDIO_URL" 2>/dev/null
}

start_lenses() {
  if studio_ok; then
    log "Lenses already responding at $STUDIO_URL"
    return 0
  fi
  log "Starting Lenses: python3 -m lenses --host $HOST --port $PORT (log: $LOG_FILE)"
  nohup python3 -m lenses --host "$HOST" --port "$PORT" >>"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"
  OUR_SERVER=1
}

stop_our_lenses() {
  if [[ "$OUR_SERVER" -eq 1 && -f "$PID_FILE" ]]; then
    local p
    p="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "$p" ]] && kill -0 "$p" 2>/dev/null; then
      log "Stopping our Lenses pid $p"
      kill "$p" 2>/dev/null || true
      wait "$p" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
    OUR_SERVER=0
    sleep 2
  fi
}

wait_for_studio() {
  local i
  for i in $(seq 1 90); do
    if studio_ok; then
      log "Studio OK ($i s)"
      return 0
    fi
    sleep 1
  done
  log "Studio did not become ready at $STUDIO_URL"
  tail -40 "$LOG_FILE" 2>/dev/null || true
  return 1
}

ensure_lenses() {
  if studio_ok; then
    log "Using existing server at $STUDIO_URL"
    return 0
  fi
  start_lenses
  wait_for_studio
}

restart_lenses_if_ours() {
  if [[ "$OUR_SERVER" -ne 1 ]]; then
    log "Tour failed but Lenses was not started by this script — wait and retry once"
    sleep 4
    ensure_lenses || true
    return 0
  fi
  log "Restarting Lenses after failure"
  stop_our_lenses
  start_lenses
  wait_for_studio
}

run_studio_explore_with_retries() {
  local attempt max=3 a
  local explore_cmd="studio-explore"
  if [[ "${STUDIO_EXPLORE_MODE:-}" == "full" ]]; then
    explore_cmd="studio-explore:full"
  fi
  for attempt in $(seq 1 "$max"); do
    log "$explore_cmd attempt $attempt/$max"
    if (cd "$ROOT/desktop" && npm run "$explore_cmd"); then
      return 0
    fi
    a=$?
    log "studio-explore exited $a"
    if [[ "$attempt" -lt "$max" ]]; then
      restart_lenses_if_ours
    fi
  done
  return 1
}

run_e2e() {
  cd "$ROOT/desktop"
  export CI=true
  if command -v xvfb-run >/dev/null 2>&1; then
    log "Playwright E2E via xvfb-run"
    xvfb-run --auto-servernum -- npm run test:e2e
  elif [[ -n "${DISPLAY:-}" ]]; then
    log "Playwright E2E with DISPLAY=$DISPLAY"
    npm run test:e2e
  else
    log "No DISPLAY and no xvfb-run — install xvfb (apt install xvfb) or set DISPLAY; skipping E2E"
    return 0
  fi
}

main() {
  cd "$ROOT"
  ensure_lenses

  log "desktop: npm ci"
  (cd "$ROOT/desktop" && npm ci)

  log "Playwright: install chromium (for tour + tests)"
  (cd "$ROOT/desktop" && npx playwright install chromium) || (cd "$ROOT/desktop" && npx playwright install)

  run_studio_explore_with_retries

  log "pytest tests/"
  python3 -m pytest tests/ -q

  run_e2e

  log "All checks passed."
}

main "$@"
