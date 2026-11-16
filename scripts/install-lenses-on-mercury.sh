#!/usr/bin/env bash
# Operator script: bind Lenses on Mercury loopback and document tunnel origin.
# Does not SSH; prints Fleet API rollout steps when MERCURY_FLEET_URL is set.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${FORGE_LENSES_LOOPBACK_PORT:-8080}"
echo "Lenses workspace root should parent the persistent forge-agents checkout."
echo "Bind: 127.0.0.1:${PORT} · public: https://lenses.forgedc.net"
echo "Health: curl -fsS https://lenses.forgedc.net/api/ready"
echo "Spec board: curl -fsS 'https://lenses.forgedc.net/api/epic-spec-board?repo=forge-agents'"
if [[ -n "${MERCURY_FLEET_URL:-}" ]]; then
  echo "Fleet: POST ${MERCURY_FLEET_URL}/v1/admin/forge-lenses-studio-rollout (when available)"
fi