# forge-lenses GCP project — OAuth via gcloud

Project **`forge-lenses`** (`886172952932`) hosts Stickerboard guest Google sign-in.

## What `gcloud` can do

| Step | Command | Notes |
|------|---------|--------|
| Create project | `gcloud projects create forge-lenses --name="Forge Lenses"` | Done |
| OAuth brand | `gcloud alpha iap oauth-brands create …` | Deprecated API; still works on new projects today |
| OAuth client (Web) | `gcloud alpha iap oauth-clients create BRAND_ID --display_name=…` | **Do not use for Stickerboard guests** — IAP clients are locked; redirect URI is only `…iap.googleapis.com/…:handleRedirect` |
| IAM `oauth-clients` | `gcloud iam oauth-clients create` | **Wrong** for Google Sign-In (`invalid_client` at accounts.google.com) |

**Stickerboard needs a normal Web client** created in the Console: **APIs & Services → Credentials → Create credentials → OAuth client ID → Web application**. IAP auto-generated clients show *“can't be modified”* and cause **`redirect_uri_mismatch`** for `leo.forgedc.net`.

## Redirect URIs to register

```
https://leo.forgedc.net/stickerboard/api/auth/oidc/callback
http://127.0.0.1:8080/stickerboard/api/auth/oidc/callback
http://127.0.0.1:9999/api/auth/oidc/callback
```

## Consent screen

The IAP brand defaults to **Internal**. For guests outside your Google Workspace, open [OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent?project=forge-lenses) and set **User type** to **External** (and add test users while in Testing).

## Lenses env

Copy client id/secret into `<workspace>/.lenses-local/lenses-oidc.env` or run:

```bash
./scripts/setup-lenses-google-oidc.sh --write
```

Restart Lenses; verify:

```bash
curl -sS http://127.0.0.1:8080/stickerboard/api/auth/oidc/status
```

Expect `"configured": true`.
