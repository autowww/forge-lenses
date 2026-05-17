---

nav_title: LLM providers and Forge Fleet probes
public_publish: true
audience: public
product_area: lenses
tier: practitioner
handbook_area: lenses
learning_level: '201'
section: tutorials-201
status: shipped
description: LLM providers and Forge Fleet probes — Forge Lenses handbook entry (tutorials-201).
page_type: tutorial
---

# LLM providers and Forge Fleet probes

## What it is

The Studio **AI tray** consumes the same **`/api/llm/*`**, **`/api/fleet/*`**, **`/api/sdlc-copilot/*`**, and OAuth-like helper routes documented in **`http-api-and-routes.html`**. Think of Forge Fleet as discovery + pooling for Forge-hosted inference nodes, while the LLM stack tracks provider credentials, catalogs, telemetry, routing previews, and Ollama warm-up scripts.

```blueprint-diagram
key: network
alt: Loopback-only Studio pane calling Fleet and LLM routes without automatic cloud egress
caption: Optional providers stay opt-in; document every boundary before enabling WAN paths
```

## When to use this guide

- You flipped **`LENSES_EXPERIMENTAL_SDLC_COPILOT`** or Wizard flags but still cannot chat locally.
- You need to sanity-check Forge Fleet meshes before enrolling Studio clients.
- You want assurance about what stays on disk (**`.lenses-local`**) vs what never leaves **`127.0.0.1`**.

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Local Lenses checkout | `./scripts/run-lenses.sh` on loopback (**default `127.0.0.1:8080`**) |
| Optional Ollama | Set **`OLLAMA_BASE_URL`**; fall back to Forge Fleet / hosted models |
| Optional PAT / OIDC | Required when RBAC is enforced (**`lenses-access.json`**) |

## Configure providers (happy path)

1. Open Forge Studio (**`/studio/`**) → **Settings → AI**.
2. Pick **`/api/llm/providers`** entry that matches your transport (HTTP OpenAI-compat, Forge Fleet pooled node, mocked fixtures for offline demos).
3. Save via **`POST /api/llm/settings`** — response should echo merged JSON with sanitized secrets (tokens never echoed verbatim).
4. Run **`POST /api/llm/provider-probe`** for each profile you rely on nightly.
5. (Optional Fleet) Populate **`POST /api/fleet/settings`** with discovery subnets + bearer references, then hit **`POST /api/fleet/discover`** followed by **`POST /api/fleet/node-detail`** for each candidate.

Verify success by watching Studio banners fed from **`GET /api/llm/diagnostics`** and **`GET /api/llm/ollama-status`**.

Next steps: **`11-wizard-301_04-cursor-launch-pack.html`** for packaging outputs, or **`http-api-and-routes.html`** for full JSON tables.

## Data boundaries (local-first)

| Surface | Local-only? | Notes |
|---------|---------------|-------|
| Provider secrets | Yes | Stored under **`.lenses-local/`**; never mirrored to Git |
| Chat transcripts | Yes | SDLC copilot audit tail **`sdlc-copilot-audit.jsonl`** |
| Fleet discovery cache | Mostly | Stored alongside LLM blobs; prune via Studio reset |
| Hosted model traffic | Depends | Leaves loopback once you intentionally target cloud endpoints |

Treat **`LENSES_ALLOW_ACTIONS=1`** as “this host now trusts LAN clients equally with localhost” — do not combine with unsecured Wi-Fi.
