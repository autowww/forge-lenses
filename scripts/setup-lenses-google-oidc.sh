#!/usr/bin/env bash
# Prepare Google Sign-In (OIDC) for Forge Lenses Stickerboard guests.
#
# Google Cloud CLI cannot create "OAuth 2.0 Client IDs" (Web application) from
# APIs & Services → Credentials — those are Console-only. gcloud alpha iap
# oauth-clients and gcloud iam oauth-clients are different products (IAP /
# Workforce Identity) and do not replace them for accounts.google.com guests.
#
# This script: checks gcloud auth, opens the Credentials page, prints redirect
# URIs, and optionally writes lenses-oidc.env after you create the client.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE="${LENSES_WORKSPACE_ROOT:-$(cd "${REPO_ROOT}/.." && pwd)}"
ENV_FILE="${WORKSPACE}/.lenses-local/lenses-oidc.env"
PROJECT="${LENSES_OIDC_GCP_PROJECT:-$(gcloud config get-value project 2>/dev/null || true)}"
PUBLIC_ORIGIN="${LENSES_PUBLIC_ORIGIN:-https://leo.forgedc.net}"
STICKER_BASE="${LENSES_STICKERBOARD_PUBLIC_BASE:-${PUBLIC_ORIGIN}/stickerboard}"

REDIRECT_PATH="/stickerboard/api/auth/oidc/callback"
if [[ "${STICKER_BASE}" != */stickerboard ]]; then
  REDIRECT_PATH="/api/auth/oidc/callback"
fi
CALLBACK_URI="${PUBLIC_ORIGIN%/}${REDIRECT_PATH}"

echo "== Forge Lenses Google OIDC setup =="
echo "Workspace: ${WORKSPACE}"
echo "Env file:  ${ENV_FILE}"
echo ""

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud not found. Install Google Cloud SDK, then re-run." >&2
  exit 1
fi

if ! gcloud auth print-access-token >/dev/null 2>&1; then
  echo "gcloud is not logged in (token refresh failed)."
  echo "Run interactively in your terminal:"
  echo "  gcloud auth login"
  echo "  gcloud config set project ${PROJECT:-YOUR_PROJECT_ID}"
  exit 1
fi

echo "gcloud account: $(gcloud config get-value account 2>/dev/null)"
echo "gcloud project: ${PROJECT:-<unset>}"
echo ""
echo "Create a Web application OAuth client in the Console (CLI cannot do this):"
echo "  https://console.cloud.google.com/apis/credentials/oauthclient?project=${PROJECT}"
echo ""
echo "Authorized redirect URIs (add all you use):"
echo "  ${CALLBACK_URI}"
echo "  http://127.0.0.1:8080/stickerboard/api/auth/oidc/callback"
echo "  http://127.0.0.1:8080/api/auth/oidc/callback"
echo "  http://127.0.0.1:9999/api/auth/oidc/callback"
echo ""

if command -v xdg-open >/dev/null 2>&1 && [[ -n "${PROJECT}" ]]; then
  xdg-open "https://console.cloud.google.com/apis/credentials/oauthclient?project=${PROJECT}" 2>/dev/null || true
fi

mkdir -p "$(dirname "${ENV_FILE}")"
if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${REPO_ROOT}/docs/examples/lenses-oidc.env.example" "${ENV_FILE}"
fi

if [[ "${1:-}" == "--write" ]]; then
  read -r -p "Paste LENSES_OIDC_CLIENT_ID: " CID
  read -r -s -p "Paste LENSES_OIDC_CLIENT_SECRET: " SECRET
  echo ""
  export CID SECRET PUBLIC_ORIGIN ENV_FILE
  python3 - <<'PY'
import os
from pathlib import Path

p = Path(os.environ["ENV_FILE"])
public_origin = os.environ["PUBLIC_ORIGIN"]
cid = os.environ["CID"].strip()
secret = os.environ["SECRET"].strip()
lines = p.read_text(encoding="utf-8").splitlines() if p.is_file() else []
out = []
seen = set()
for line in lines:
    if line.startswith("LENSES_PUBLIC_ORIGIN="):
        out.append(f"LENSES_PUBLIC_ORIGIN={public_origin}")
        seen.add("LENSES_PUBLIC_ORIGIN")
    elif line.startswith("LENSES_OIDC_ISSUER="):
        out.append("LENSES_OIDC_ISSUER=https://accounts.google.com")
        seen.add("LENSES_OIDC_ISSUER")
    elif line.startswith("LENSES_OIDC_CLIENT_ID="):
        out.append(f"LENSES_OIDC_CLIENT_ID={cid}")
        seen.add("LENSES_OIDC_CLIENT_ID")
    elif line.startswith("LENSES_OIDC_CLIENT_SECRET="):
        out.append(f"LENSES_OIDC_CLIENT_SECRET={secret}")
        seen.add("LENSES_OIDC_CLIENT_SECRET")
    else:
        out.append(line)
for key, val in [
    ("LENSES_PUBLIC_ORIGIN", public_origin),
    ("LENSES_OIDC_ISSUER", "https://accounts.google.com"),
    ("LENSES_OIDC_CLIENT_ID", cid),
    ("LENSES_OIDC_CLIENT_SECRET", secret),
]:
    if key not in seen:
        out.append(f"{key}={val}")
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
print(f"Updated {p}")
PY
  echo "Restart Lenses / Forge Studio, then verify:"
  echo "  curl -sS http://127.0.0.1:8080/stickerboard/api/auth/oidc/status | python3 -m json.tool"
else
  echo "After creating the client in the Console, run:"
  echo "  ${REPO_ROOT}/scripts/setup-lenses-google-oidc.sh --write"
  echo ""
  echo "Or edit ${ENV_FILE} manually, then restart Lenses."
fi
