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
title: Lenses local HTTP surface
summary: One Lenses process exposes /api routes that Studio, builders, and local HTTP peers share on loopback.
node: What it is
detail: The local HTTP integration surface this builders overview introduces.
more: Forge Lenses serves documented /api/... routes from python3 -m lenses; Studio and Classic browsers call the same paths integrators use.
node: Root / intake
detail: The Lenses process entry where inbound API requests arrive.
more: Prefix families and methods are cataloged for operators; builders verify behavior against the generated route tables on loopback.
node: branch A
detail: A first HTTP peer path off the shared local API intake.
node: branch B
detail: A second peer class using the same documented route boundaries.
node: branch C
detail: A third peer path on the bounded local network diagram.
more: Outbound Fleet or LLM calls stay outside this surface unless a route explicitly brokers them.
caption: Builders reason about POST boundaries the same surfaces Studio trusts locally
fallback_ascii: |
  What it is

  Root / intake
      +-- branch A
      +-- branch B
      +-- branch C
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
