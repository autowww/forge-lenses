#!/usr/bin/env bash
# Test Ollama (11434) and Caddy OpenAI-shim (11435) from another machine on the same LAN.
#
# Run this ON THE REMOTE CLIENT (not on the server hosting Ollama), after the server
# listens on the LAN interface:
#   - Ollama: set OLLAMA_HOST=0.0.0.0:11434 (e.g. in systemd override) and restart ollama.
#   - Caddy: bind :11435 on 0.0.0.0 and forward to 127.0.0.1:11434 (or your upstream).
#
# Usage:
#   export LENSES_LAN_HOST=192.168.1.50      # IP of the machine running Ollama/Caddy
#   export LENSES_CADDY_API_KEY='your-key' # if Caddy checks auth
#   export LENSES_CADDY_USE_X_API_KEY=1   # optional: send X-API-Key instead of Authorization: Bearer
#   bash scripts/test-ollama-lan.sh
#
# Optional:
#   OLLAMA_PORT=11434 CADDY_PORT=11435 OLLAMA_TEST_MODEL=ibm/granite4:tiny-h

set -euo pipefail

HOST="${LENSES_LAN_HOST:?Set LENSES_LAN_HOST to the server IP (e.g. 192.168.1.50)}"
O_PORT="${OLLAMA_PORT:-11434}"
C_PORT="${CADDY_PORT:-11435}"
KEY="${LENSES_CADDY_API_KEY:-}"

echo "== Ollama direct: GET http://${HOST}:${O_PORT}/api/tags =="
if curl -sS --connect-timeout 5 "http://${HOST}:${O_PORT}/api/tags" | head -c 400; then
  echo ""
  echo "OK (direct Ollama reachable)"
else
  echo ""
  echo "FAIL — check server OLLAMA_HOST, firewall (ufw/nftables), and that port ${O_PORT} is open."
  exit 1
fi

echo ""
echo "== Caddy shim: POST http://${HOST}:${C_PORT}/v1/chat/completions =="
AUTH_HEADER=()
if [[ -n "${KEY}" ]]; then
  if [[ "${LENSES_CADDY_USE_X_API_KEY:-}" == "1" ]]; then
    AUTH_HEADER=(-H "X-API-Key: ${KEY}")
  else
    AUTH_HEADER=(-H "Authorization: Bearer ${KEY}")
  fi
fi

BODY='{"model":"'"${OLLAMA_TEST_MODEL:-ibm/granite4:tiny-h}"'","messages":[{"role":"user","content":"Say OK in one word."}],"stream":false}'

HTTP=$(curl -sS -o /tmp/ollama-caddy-test.body -w "%{http_code}" --connect-timeout 8 \
  "${AUTH_HEADER[@]}" \
  -H "Content-Type: application/json" \
  -d "${BODY}" \
  "http://${HOST}:${C_PORT}/v1/chat/completions" || true)

echo "HTTP ${HTTP}"
head -c 600 /tmp/ollama-caddy-test.body || true
echo ""

if [[ "${HTTP}" != "200" ]]; then
  echo "FAIL — Caddy or upstream rejected the request. Verify API key header name/value and Caddy route."
  exit 1
fi

echo "OK (Caddy OpenAI-compatible path reachable)"
exit 0
