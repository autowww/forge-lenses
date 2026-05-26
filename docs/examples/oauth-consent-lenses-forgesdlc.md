# Google OAuth consent — lenses.forgesdlc.com + leo.forgedc.net

Use this checklist when configuring the **forge-lenses** GCP project OAuth consent screen and Web client for **Stickerboard** guest sign-in.

**Two hosts, one app:**

| Host | Role |
|------|------|
| **`lenses.forgesdlc.com`** | Static handbook + OAuth **branding** (home, privacy, terms) |
| **`leo.forgedc.net`** | **Live** Stickerboard guest app + OIDC redirect (share links today) |

You can use **both** without moving legal pages to `leo` — add **both** registrable domains under **Authorized domains**.

## Static pages (deploy first)

Build and deploy **forge-lenses-website** so these URLs return **200**:

| Purpose | URL |
|---------|-----|
| Application home (OAuth branding) | `https://lenses.forgesdlc.com/stickerboard.html` |
| Privacy policy | `https://lenses.forgesdlc.com/privacy.html` |
| Terms of service | `https://lenses.forgesdlc.com/terms.html` |
| Product handbook | `https://lenses.forgesdlc.com/` |

From **forge-lenses-website** repo root:

```bash
python3 generator/build-site.py
python3 generator/build_oauth_public_pages.py
# deploy: ./deploy-websites.sh --only forge-lenses-website
```

Source Markdown: `forge-lenses-website/oauth-public/content/*.md`.

## OAuth consent screen (Branding)

| Field | Value |
|-------|--------|
| **User type** | **Internal** (Workspace only) or **External** (any Google account — required for public guests; use **Testing** + test users until verified) |
| **App name** | `Forge Lenses Stickerboard` |
| **User support email** | `info@autowww.org` |
| **App logo** | Optional — square 120×120 PNG |
| **Application home page** | `https://lenses.forgesdlc.com/stickerboard.html` |
| **Application privacy policy link** | `https://lenses.forgesdlc.com/privacy.html` |
| **Application terms of service link** | `https://lenses.forgesdlc.com/terms.html` |
| **Authorized domains** | **`forgesdlc.com`** and **`forgedc.net`** — use **+ Add domain** for each (covers `lenses.forgesdlc.com` and `leo.forgedc.net`) |
| **Developer contact** | `info@autowww.org` |

**Save** is enabled only when every domain used in branding links **and** in redirect URIs is listed. With live guests on `leo.forgedc.net`, **`forgedc.net` is required** even when home/privacy/terms stay on `lenses.forgesdlc.com`.

Do **not** put `https://leo.forgedc.net/...` in **Application home page** unless you also add **`forgedc.net`**; prefer **`https://lenses.forgesdlc.com/stickerboard.html`** for home/privacy/terms and keep **`leo`** only on redirect URIs + `LENSES_STICKERBOARD_PUBLIC_BASE`.

## OAuth client — Authorized redirect URIs

Add every origin where Lenses serves Stickerboard APIs:

```
https://lenses.forgesdlc.com/stickerboard/api/auth/oidc/callback
https://leo.forgedc.net/stickerboard/api/auth/oidc/callback
http://127.0.0.1:8080/stickerboard/api/auth/oidc/callback
http://127.0.0.1:9999/api/auth/oidc/callback
```

Create a **new Web application** client (not the IAP locked client):

`https://console.cloud.google.com/apis/credentials/oauthclient?project=forge-lenses`

If the client page says *“automatically generated … can't be modified”* and the only redirect URI is `iap.googleapis.com/…:handleRedirect`, that client **cannot** be used for Stickerboard — create a separate **Web application** OAuth client and put its id/secret in `lenses-oidc.env`.

## Lenses environment (production)

**Current live host (`leo`):**

```bash
LENSES_PUBLIC_ORIGIN=https://leo.forgedc.net
LENSES_STICKERBOARD_PUBLIC_BASE=https://leo.forgedc.net/stickerboard
```

**Optional future** — same Lenses process proxied at `lenses.forgesdlc.com` (branding URLs unchanged):

```bash
LENSES_PUBLIC_ORIGIN=https://lenses.forgesdlc.com
LENSES_STICKERBOARD_PUBLIC_BASE=https://lenses.forgesdlc.com/stickerboard
```

OIDC redirect path defaults to `/stickerboard/api/auth/oidc/callback` when `LENSES_STICKERBOARD_PUBLIC_BASE` ends with `/stickerboard`. Register **every** redirect URI host on the OAuth client (see above).

## App logo (verification)

Google may reject a **generic initials** square (e.g. **“FS”** on black) as not uniquely identifying your brand.

| Option | Action |
|--------|--------|
| **Fastest (Testing)** | **Remove** the logo on the Branding page — logo is optional; text app name + links still work. |
| **Better** | Upload a **120×120** square PNG derived from `forge-lenses-website/oauth-public/assets/forge-lenses-oauth-logo.svg` (amber lens ring + **F** + **LENSES**). |
| **Re-verify** | After Remove or new logo → **Save** → dialog **“I have fixed the issues”** → **Proceed**. |

Branding verification is **separate** from **`redirect_uri_mismatch`** (fixed with a normal **Web application** OAuth client, not the IAP locked client).

## Verify

1. Open `https://lenses.forgesdlc.com/stickerboard.html`, `privacy.html`, `terms.html` in a browser.
2. Save OAuth branding — no “Missing domain” errors for `forgesdlc.com` or `forgedc.net`.
3. Facilitator starts sharing; guest opens share URL; **Sign in with Google** completes without `redirect_uri_mismatch`.
