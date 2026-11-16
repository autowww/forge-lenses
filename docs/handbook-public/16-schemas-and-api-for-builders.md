---

nav_title: Builder contracts and schemas
public_publish: true
audience: public
product_area: lenses
tier: advanced
handbook_area: wizard
learning_level: '301'
section: builders
status: shipped
description: Builder contracts and schemas — Forge Lenses handbook entry (builders).
page_type: topic
---

# Blueprints schemas for automation authors

## What it is

Machine-readable drafts now live beside the repo Markdown:

- **`docs/schemas/README.md`** — stability labels + changelog expectations.
- **`docs/examples/`** — JSON snippets exercised by **`tests/test_docs_schemas.py`** (`pytest`).
- Companion HTTP tables remain canonical for runtime routes (**`http-api-and-routes.html`**).

Schemas currently cover:

| File | Matches |
|------|---------|
| `wizard-session.schema.json` | Session envelope persisted for Wizard |
| `wizard-stage-response.schema.json` | HTTP acknowledgements for `/api/blueprints/wizard/*` |
| `wizard-domain.schema.json` | `wizard_domain` object fragment |
| `workspace-scan-result.schema.json` | `GET /api/workspace-scan` + cached `_scan` payloads |
| `cursor-launch-pack-manifest.schema.json` | Cursor ZIP manifest |
| `api-error.schema.json` | Canonical `{ ok: false }` payloads |

## HTTP route inventory

- **Committed snapshot** — [`docs/generated/api-routes.md`](../generated/api-routes.md) (Markdown table + matching [`api-routes.json`](../generated/api-routes.json)).
- **Regenerate** after **`lenses/serve.py`** edits:

```bash
python3 generator/export_api_routes_docs.py
```

- **CI drift gate** — `scripts/check-generated-api-routes-fresh.py` (runs via **`scripts/check-docs.sh`**).
- **Quick dump** — `python3 generator/collect_lenses_api_routes.py --output build/lenses-api-routes.json` (prompt-pack artifact under **`build/`**).

Route families (representative):

| Family | Prefix / pattern | Doc anchor |
|--------|------------------|------------|
| Workspace + scan | `/api/workspace-state`, `/api/workspace-scan` | Maintainer HTTP tables + this page |
| Projects / git | `/api/project/*` | HTTP tables |
| Wizard | `/api/blueprints/wizard/*` | Wizard chapters + `wizard-session.schema.json` |
| Docs Health | `/api/docs-health/*` | [Docs Health](15-docs-health.md) |
| Governance | `/api/governance/*`, `/api/oidc/*` | [Security and local-first](17-security-and-local-first.md) |
| LLM / tools | `/api/llm/*`, tool runner endpoints | [LLM and AI setup](13-llm-and-ai-setup.md) |

## When to use schemas

1. Cursor/MCP tooling wants deterministic prompts — import JSON Schema Draft 2020-12 validators.
2. CI needs guardrails preventing silent shape drift (**`generator/collect_lenses_api_routes.py`** already mirrors HTTP inventory).

Do **not** treat schemas as exhaustive security proofs — permissive **`additionalProperties`** remain where backwards compatibility mandates unknown keys (`cursor-launch-pack` manifest deliberately allows forward-compatible fields).
