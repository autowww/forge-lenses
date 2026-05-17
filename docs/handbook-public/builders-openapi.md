---

nav_title: Builders — OpenAPI stub
public_publish: true
audience: public
product_area: lenses
learning_level: reference
section: builders
tier: builder
handbook_area: builders
description: Derived OpenAPI 3.1 inventory from api-routes.json and how builders should use it.
status: shipped
page_type: topic
---

# Builders — OpenAPI rollup (derived)

Forge Lenses ships a **non-authoritative OpenAPI snapshot** regenerated from [`docs/generated/api-routes.json`](../generated/api-routes.json):

- **`docs/generated/openapi.json`** — emits one path bucket per discrete route signature in the collector (**method inventory**, not exhaustive request/response models).
- **Generator** — `generator/export_openapi.py` (`scripts/check-docs.sh` rewrites the file whenever `api-routes.json` changes).

Automation keeps this aligned with **`check-generated-openapi-fresh.py`**: stale committed JSON fails CI after `generator/export_openapi.py` tweaks.

Treat the OpenAPI artefact as a **navigator** alongside the handbook. Runtime truth remains `lenses/serve.py`, JSON Schemas under `docs/schemas/`, and the maintained HTTP appendix.

```blueprint-diagram
key: tree
alt: Builder docs tree linking HTTP tables, schemas, derived OpenAPI, and Fleet helpers
caption: Derived OpenAPI is a sibling to handbook tables and schemas, not a second server implementation
```

## Stable route families referenced in reviewer contracts

The API documentation contracts in **`docs/strategy/api-family-contracts.json`** anchor prose coverage for orchestration jobs. Mention these prefixes prominently when you cite HTTP behaviour anywhere in handbook + builder corpus:

| Family | Typical prefix | Companion docs |
|--------|----------------|----------------|
| Docs Health | **`/api/docs-health`** (`/api/docs-health/summary`, `/api/docs-health/work-items`, …) | [Docs Health Lenses](15-docs-health.md) |
| Wizard + blueprints sessions | **`/api/blueprints`** plus `/api/blueprints/wizard/*` (session persistence) | [Wizard overview](08-wizard-overview.md), **`wizard-session.schema.json`** |
| Repo + workspace overlays | **`/api/repo`** (status, branches, artefacts behind Studio overlays) | [Schemas and API (builders)](16-schemas-and-api-for-builders.md) |
| LLM tooling | **`/api/llm`** (`/api/llm/settings`, probes, diagnostics) | [LLM and AI setup](13-llm-and-ai-setup.md) (**Studio** consumes these routes.) |
| Forge Fleet mesh bridges | **`/api/fleet`** (pooling hooks that pair with Forge Fleet admins) | [LLM setup](13-llm-and-ai-setup.md) + enterprise fleet chapter |
| Local auth | **`/api/auth`** (`/api/auth/status`, GitHub PAT exchange, logout, OIDC callbacks) | [Builders — auth & safety](builders-auth-and-safety.md), [Security — local-first](17-security-and-local-first.md) |

When a tier is labelled **experimental** upstream and no schema exists yet, add the escape token documented in **`api-family-contracts.json`** (for example **`SCHEMA_EXEMPT_api_blueprints`** in Markdown) beside the handbook paragraph explaining why automation must skip assertions.

## Workflow

```bash
python3 generator/collect_lenses_api_routes.py --output docs/generated/api-routes.json
python3 generator/export_api_routes_docs.py      # snapshots Markdown + JSON
python3 generator/export_openapi.py              # derives openapi.json
python3 scripts/check-generated-openapi-fresh.py # drift gate vs committed file
```

## Verify

Follow [Builders — schemas](builders-schemas.md) for **`pytest tests/test_docs_schemas.py`** and keep JSON examples paired whenever you touch request/response bodies.
