---

nav_title: Builders — route families
public_publish: true
audience: public
product_area: lenses
learning_level: reference
section: builders
description: How HTTP routes are grouped by URL prefix for scanning and docs coverage.
status: shipped
tier: builder
handbook_area: builders
page_type: landing
---

# Builders — route families

## What it is

Routes are grouped by the **first two path segments** (for example `/api/blueprints`, `/api/docs-health`) so coverage tables and CI stay readable. **Prefer this page plus the generated catalog’s family headings** over scrolling the raw route grid: open [`api-routes.md`](../generated/api-routes.md), jump to the family anchor you care about, then cross-check JSON bodies against [`builders-openapi.md`](builders-openapi.md) / [`builders-schemas.md`](builders-schemas.md).

The same grouping drives:

- **[HTTP API route catalog](../generated/api-routes.md)** — per-family sections with method counts ([JSON mirror](../generated/api-routes.json))
- Maintainer/strategy rollup on GitHub: [API route families](https://github.com/autowww/forge-lenses/blob/main/docs/strategy/api-route-families.md)
- `docs/generated/api-routes.json` — machine-readable `families` map

## When to use it

When you need a **stable mental model** before diving into the full table or [`lenses/serve.py`](https://github.com/autowww/forge-lenses/blob/main/lenses/serve.py).

## Verify

Open the generated page and confirm a family you care about (for example **`/api/blueprints`**) lists **non-zero** counts for the HTTP methods you expect.

## What to do next

- [Builders — API overview](builders-api-overview.md)
