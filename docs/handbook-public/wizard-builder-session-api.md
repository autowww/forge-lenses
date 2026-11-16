---


nav_title: Wizard session HTTP API
public_publish: true
audience: public
product_area: wizard
tier: practitioner
handbook_area: wizard
learning_level: reference
section: studio-wizard
status: experimental
description: Curated GET/POST families for Wizard sessions — complements generated route inventory.
page_type: topic
---

# Wizard — builder session HTTP API

## What it is

**Curated** HTTP families for **Blueprints Wizard** automation. Authoritative route parsing lives in **`lenses/serve.py`**; the full machine-generated table is the **[HTTP API route catalog](../generated/api-routes.md)**. Maintainer narrative prose that predates automated inventory remains on GitHub: [HTTP API and routes source](https://github.com/autowww/forge-lenses/blob/main/lenses/website/http-api-and-routes.md).

## JSON envelope

Session shape is validated by **`wizard-session.schema.json`** with a worked sample at [`sample-wizard-session.json`](../examples/sample-wizard-session.json) ([JSON examples](19-examples-hub.md)).

## Read models (safe automation)

| Family | Representative `GET` | Purpose |
|--------|------------------------|---------|
| Feature gate | `/api/blueprints/wizard/enabled` | Whether Wizard surfaces should appear |
| Session list | `/api/blueprints/wizard/sessions` | Hub inventory |
| Session body | `/api/blueprints/wizard/session/<id>` | Current envelope for builders *read-only* |

Use **[Schemas and API for builders](16-schemas-and-api-for-builders.md)** for error envelopes and safe **`curl`** habits (**GET** listings only in shared examples).

## Write / assist paths (POST)

These **mutate** session state or trigger outbound work — **never** paste live tokens or customer data into docs.

| Step | Pattern (representative) | Notes |
|------|--------------------------|-------|
| Create / replace session | `POST /api/blueprints/wizard/session` | Allocates id used in deep links |
| Telemetry | `POST /api/blueprints/wizard/telemetry` | Step/navigation observations |
| Refine | `POST /api/blueprints/wizard/session/<id>/refine` | LLM assist |
| Interpret | `POST /api/blueprints/wizard/session/<id>/interpret` | LLM assist |
| Artifacts | `…/generate-artifacts`, `…/artifact-review`, `…/artifact-export`, `…/artifact-recheck` | Review gate before export |
| Launch pack | `…/cursor-launch-pack/<action>` | Editor handoff |
| Clarify | `…/clarify-suggest` | Suggested prompts |

Exact suffix sets can grow per release — diff **`docs/generated/api-routes.json`** when upgrading.

## Verify

A **`GET /api/blueprints/wizard/enabled`** from loopback matches what operators expect **before** you script deeper calls.

## What to do next

- [Wizard operator trust boundaries](wizard-operator-trust-boundaries.md)
- [Blueprints Wizard overview](08-wizard-overview.md)
