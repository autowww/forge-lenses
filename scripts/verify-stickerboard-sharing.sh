#!/usr/bin/env bash
# Stickerboard guest sharing — quick verification against a running Lenses server.
set -euo pipefail

BASE="${LENSES_BASE_URL:-http://127.0.0.1:8080}"
TOKEN="${LENSES_VERIFY_SHARE_TOKEN:-K8SmhwjbgshU95Jogy67ogHd0Fs9vBUA}"
BOARD="${LENSES_VERIFY_BOARD_ID:-XwsPN3GfCW2I30CH19Vs8M}"

fail() { echo "verify-stickerboard: $*" >&2; exit 1; }

code() { curl -sS -o /dev/null -w "%{http_code}" "$1"; }

echo "== stickerboard sharing verify (${BASE}) =="

c=$(code "${BASE}/api/workspace-state") || fail "workspace-state unreachable"
[[ "${c}" == "200" ]] || fail "workspace-state HTTP ${c}"

c=$(code "${BASE}/stickerboard/") || fail "stickerboard SPA unreachable"
[[ "${c}" == "200" ]] || fail "stickerboard SPA HTTP ${c}"

c=$(code "${BASE}/stickerboard/api/auth/status") || fail "prefixed auth unreachable"
[[ "${c}" == "200" ]] || fail "stickerboard/api/auth/status HTTP ${c}"

meta=$(curl -sf "${BASE}/stickerboard/api/sticker-board-share?token=${TOKEN}") \
  || fail "share metadata failed"
echo "${meta}" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('ok'), d; assert d.get('board_id'), d" \
  || fail "share metadata JSON invalid"

echo "share meta ok (token ${TOKEN:0:8}…)"

board=$(curl -sf -H "Cookie: lenses_share_scope=${TOKEN}" \
  "${BASE}/stickerboard/api/sticker-board?board_id=${BOARD}") \
  || fail "scoped board GET failed"
echo "${board}" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('board_id')=='${BOARD}', d; assert not d.get('board_not_found')" \
  || fail "scoped board payload"
echo "scoped board GET ok (share cookie)"

echo "verify-stickerboard: all checks passed"
