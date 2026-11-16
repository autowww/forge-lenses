---
nav_title: Stickerboard sharing
public_publish: true
audience: public
product_area: lenses
tier: practitioner
handbook_area: lenses
learning_level: '201'
section: enterprise
status: shipped
description: Guest share links, Google OIDC, and view/edit workshop access for Stickerboard.
page_type: how-to
---

# Forge Lenses Stickerboard — guest sharing

**Forge Lenses Stickerboard** lets workshop participants join a sticker board via a **random share link**, sign in with **Google (OIDC)**, and collaborate under **view** or **edit** access chosen by the facilitator.

## Roles

| Role | Access |
|------|--------|
| **Facilitator** | Full **Studio** at `http://127.0.0.1:8080/studio/` — create boards, start/revoke sharing, copy links |
| **Guest** | **Stickerboard-only** app — local `http://127.0.0.1:9999/#/<token>`; public `https://leo.forgedc.net/stickerboard/#/<token>` |

## Local setup

1. Run Lenses (port **8080** by default). A secondary listener starts on **`127.0.0.1:9999`** when `LENSES_STICKERBOARD_PORT` is not `0` (default **9999**).
2. Build the guest SPA: `cd lenses-enterprise && npm run build:stickerboard`
3. Set env (server and Studio `.env`):

```bash
# Production guest links (authoritative — Studio reads this from GET /api/sticker-board-share/config):
LENSES_STICKERBOARD_PUBLIC_BASE=https://leo.forgedc.net/stickerboard

# Local dedicated listener (optional when not proxying guests on :443 only):
LENSES_STICKERBOARD_PORT=9999

# Optional Vite build hint only; server env wins at runtime:
# VITE_STICKERBOARD_PUBLIC_BASE=https://leo.forgedc.net/stickerboard
```

4. Configure Google OAuth with redirect URI `http://127.0.0.1:9999/api/auth/oidc/callback` (and your production host when deployed).

## Facilitator workflow

1. Open `/studio/board/<boardId>`.
2. In **Forge Lenses Stickerboard — sharing**, choose **Guests can view** or **Guests can edit**.
3. **Start sharing**, then **Copy Forge Lenses Stickerboard URL**.
4. Guests sign in with Google; names appear in the participant list.
5. **Revoke sharing** when the session ends.

## Guest workflow

1. Open the copied link (local `/#/<token>` on port 9999; production `/stickerboard/#/<token>` on the public host).
2. **Sign in with Google**.
3. Use the same workshop phase strip (Discover → Score → Prioritize → Capture).
4. **View** links: read-only board. **Edit** links: add/edit/delete stickers and set qualitative **Impact** / **Effort** tiers.

## Security

- Share-scope sessions receive **401** on all routes outside the allowlist (no Studio, workspace scan, or other boards).
- Port **9999** denies `/studio/` and other non-Stickerboard paths.
- Share links require Google sign-in (no anonymous access).

## OAuth branding (`lenses.forgesdlc.com`)

Static pages for the **Google OAuth consent screen** (deploy via **forge-lenses-website**):

| Purpose | URL |
|---------|-----|
| Application home | `https://lenses.forgesdlc.com/stickerboard.html` |
| Privacy | `https://lenses.forgesdlc.com/privacy.html` |
| Terms | `https://lenses.forgesdlc.com/terms.html` |

Add **`forgesdlc.com`** and **`forgedc.net`** under **Authorized domains** (legal pages on **lenses**; live share links on **leo**). Checklist: [oauth-consent-lenses-forgesdlc.md](../examples/oauth-consent-lenses-forgesdlc.md).

## Production (`leo.forgedc.net`)

| Setting | Value |
|---------|--------|
| Public base | `https://leo.forgedc.net/stickerboard` |
| Reverse proxy | `/stickerboard/` → Lenses backend |
| OAuth redirect | `https://leo.forgedc.net/stickerboard/api/auth/oidc/callback` (path-only proxy) or `/api/auth/oidc/callback` if `/api` is exposed |

Copy [docs/examples/lenses-oidc.env.example](../examples/lenses-oidc.env.example) to **`<workspace>/.lenses-local/lenses-oidc.env`** (or export the same keys in systemd / Docker):

```bash
LENSES_PUBLIC_ORIGIN=https://leo.forgedc.net
LENSES_STICKERBOARD_PUBLIC_BASE=https://leo.forgedc.net/stickerboard
LENSES_STICKERBOARD_PORT=0
LENSES_OIDC_ISSUER=https://accounts.google.com
LENSES_OIDC_CLIENT_ID=…
LENSES_OIDC_CLIENT_SECRET=…
```

Register the Google OAuth client redirect URI **`https://leo.forgedc.net/stickerboard/api/auth/oidc/callback`** (auto-selected when `LENSES_STICKERBOARD_PUBLIC_BASE` ends with `/stickerboard`). Add **`https://leo.forgedc.net/api/auth/oidc/callback`** too if your tunnel exposes `/api` at the site root.

Set `LENSES_STICKERBOARD_PORT=0` when only the reverse proxy serves guest URLs on port 443.

### Reverse proxy (required)

Guests need **both** the Stickerboard SPA and auth APIs on the **same public origin**:

| Path | Backend |
|------|---------|
| `/stickerboard/*` | Lenses (main `:8080` **or** dedicated `:9999` with `/stickerboard` prefix) |
| `/api/auth/*` | Lenses main port (`:8080`) — **not** optional |
| `/api/sticker-board-share/*`, `/api/sticker-board` | Same Lenses process as the board workspace |

If `/api/auth/status` returns **404** on the public host, fix the proxy before testing Google sign-in.

### Cloudflare Tunnel (blank white page)

A **healthy tunnel** can still show a **blank page** when only `/stickerboard` is published:

1. **JavaScript 404** — older builds referenced `/assets/…` instead of `/stickerboard/assets/…`. Rebuild `npm run build:stickerboard` and redeploy `lenses/static/stickerboard/`, or run current Lenses (it rewrites index HTML to `./assets/…` on serve).
2. **API 404** — the guest app calls **`/api/sticker-board-share`**, **`/api/auth/*`**, etc. on the **same hostname**. Add ingress rules (or one catch-all) to the Lenses process on **`127.0.0.1:8080`** (recommended: `LENSES_STICKERBOARD_PORT=0`, single listener):

| Public path | Backend |
|-------------|---------|
| `leo.forgedc.net` → `http://127.0.0.1:8080` | Full Lenses (Studio + `/stickerboard` + `/api`) |

Verify: `curl -sS -o /dev/null -w "%{http_code}" https://leo.forgedc.net/stickerboard/assets/index-*.js` → **200**; `curl … https://leo.forgedc.net/api/auth/status` → **200** (not 404).
