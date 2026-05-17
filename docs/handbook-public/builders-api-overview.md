---

nav_title: Builders — API overview
public_publish: true
audience: public
product_area: lenses
learning_level: reference
section: builders
description: Entry point for HTTP integration — links to generated catalog and safety
  notes.
status: shipped
tier: builder
handbook_area: builders
page_type: landing
---

# Builders — API overview

## What it is

Forge Lenses exposes a single **local HTTP surface** from `python3 -m lenses`. Studio and Classic browsers call the same **`/api/...`** routes documented for operators in the maintainer handbook and summarized here for **builders and integrators**.

```blueprint-diagram
key: network
alt: Browser, Forge Lenses process, repos, Fleet, and outbound LLMs as HTTP peers
caption: Builders reason about POST boundaries the same surfaces Studio trusts locally
```

## Where to read next

| Topic | Page |
|-------|------|
| Error envelopes, safe curl | [Schemas and API (builders)](16-schemas-and-api-for-builders.md) |
| Prefix families and counts | [Builders — route families](builders-route-families.md) |
| Generated flat + per-family tables | [Generated HTTP routes](../generated/api-routes.md) |
| Auth and secrets | [Builders — auth and safety](builders-auth-and-safety.md) |
| JSON schemas | [Builders — schemas](builders-schemas.md) |
| Versioning / stability | [Builders — stability policy](builders-stability-policy.md) |

## OpenAPI rollup (partial)

`generator/export_openapi.py` emits **`docs/generated/openapi.json`** whenever **`scripts/check-docs.sh`** runs. Pair it with **`docs/generated/api-routes.json`** and **[Schemas and API (builders)](16-schemas-and-api-for-builders.md)** — nuanced envelopes remain **code-first** until a fuller export exists.

## Verify

Pick one **`GET`** path from [Generated HTTP routes](../generated/api-routes.md) and confirm it returns on your loopback server with the same method shown in the table.

## What to do next

- [JSON examples hub](19-examples-hub.md)
