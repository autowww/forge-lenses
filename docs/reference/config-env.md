---

audience: public
section: builders
learning_level: reference
product_area: configuration
status: shipped
tier: builder
handbook_area: builders
public_publish: true
nav_title: Configuration reference
description: Configuration reference — Forge Lenses handbook entry (builders).
page_type: reference
---

# Reference — environment variables and Studio feature flags

Audience: **operators + power users** configuring local Forge Lenses / Studio. `build-lenses-docs` publishes this page as **`reference-config-env.html`**. Handbook chapters link here with relative Markdown paths (`../../docs/reference/config-env.md`).

| Variable | Default | Purpose | Surfaces / risks |
|----------|---------|---------|------------------|
| **`LENSES_WORKSPACE_ROOT`** | auto-detected cwd | Forces the workspace root scanned by `scan_workspace`. | Incorrect paths → empty `/api/workspace-state`. |
| **`LENSES_PORT`** | `8080` | HTTP listener port for `lenses/serve.py`. | Conflicts with other services. |
| **`LENSES_STUDIO_UI`** | `1` enabled | Toggles availability of Studio shell assets. | Studio 404 if disabled. |
| **`VITE_LENSES_API_BASE`** | same origin | Build-time override where the Studio bundle posts `/api`. | Mis-set → CORS noise in dev server. |
| **`LENSES_ALLOW_ACTIONS`** | `0` | Permits privileged POST surfaces from non-loopback clients. | **High** — exposes LLM + governance writes. |
| **`LENSES_ALLOW_GIT_ACTIONS`** | `0` | Permits `git` + tool runner POSTs remotely. | Effectively remote shell access to git + script allowlists. |
| **`LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD`** | `1` locally | Gates `/api/blueprints/wizard/*`. | Off → Wizard 404 + Studio banner. |
| **`VITE_EXPERIMENTAL_BLUEPRINTS_WIZARD`** | mirrors server | Studio dev server flag for Wizard nav. | Must match server flag to avoid dead links. |
| **`LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH`** | `1` | Enables graph DB + readiness cards. | SQLite file under **`.lenses-local`**. |
| **`OLLAMA_BASE_URL`** | `http://127.0.0.1:11434` | Targets for `/api/llm/ollama-*`. | WAN exposure if pointed off-box without auth. |
| **`LENSES_OPENAI_COMPAT_BASE_URL`** | unset | Global override for OpenAI-compatible transports. | Bearer tokens live in settings JSON. |
| **`LENSES_ARTIFACT_GENERATION_MOCK`** | `0` | Enables deterministic wizard artifact fixtures. | Keep off in production writes. |
| **`LENSES_CURSOR_LAUNCH_STAGING_TTL_SEC`** | server default | TTL for Cursor launch zip staging tokens. | Larger values → more disk in **`.lenses-local`**. |
| **`LENSES_PUBLIC_ORIGIN`** | unset | Canonical HTTPS origin (`https://leo.forgedc.net`) for OAuth redirect URIs behind a proxy. | Wrong value → Google redirect mismatch. |
| **`LENSES_OIDC_ISSUER`** | unset | OIDC discovery root (Google: `https://accounts.google.com`). | Also loadable from **`.lenses-local/lenses-oidc.env`**. |
| **`LENSES_OIDC_CLIENT_ID`** / **`SECRET`** | unset | OAuth confidential client. | Store via env or `lenses-oidc.env`, not git. |
| **`LENSES_OIDC_REDIRECT_PATH`** | `/api/auth/oidc/callback` | Must match reverse proxy paths. | Wrong value → login loops. |
| **`LENSES_OIDC_SCOPES`** | `openid profile email` | Space-delimited scopes. | Omit sensitive scopes when possible. |

## Blueprints publish scope

Blueprint Hosting only ingests **`docs/handbook-public/*.md`** entries allow-listed under **`forge_lenses.include_globs`** in **`blueprints-website/generator/handbook-publish-manifest.yaml`**. Reference pages such as **`docs/reference/config-env.md`** are intentionally outside that bundle; expect them via **lenses-docs** / **`forge-lenses-website`** and GitHub until the ingestion tooling learns non–`handbook-public` Lens paths.


