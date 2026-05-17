---

nav_title: Builders — stability policy
public_publish: true
audience: public
product_area: lenses
learning_level: reference
section: builders
description: semver expectations for HTTP routes and generated docs artifacts.
status: shipped
tier: builder
handbook_area: builders
page_type: topic
---

# Builders — stability policy

## What it is

- **Patch** releases may add **`GET`** diagnostics or extend existing **`POST`** bodies in backward-compatible ways.
- **Minor** releases may introduce new `/api/...` families — regenerate **`docs/generated/api-routes.json`** and review **`families`** diffs.
- **Major** or breaking path changes should arrive with release notes ([Release notes](24-release-notes.md)) and handbook updates.

## Generated artifacts

`docs/generated/api-routes.json` and `api-routes.md` are **regenerated** with `python3 generator/export_api_routes_docs.py` whenever `lenses/serve.py` routing changes; CI fails if the committed JSON drifts (`scripts/check-generated-api-routes-fresh.py`).

## OpenAPI

Public OpenAPI export remains **out of scope** until the maintainer team declares the `/api` surface stable enough to freeze (see [Builders — API overview](builders-api-overview.md)).

## Verify

After upgrading Lenses, re-run `bash scripts/check-docs.sh` locally before relying on automation tied to specific paths.

## What to do next

- [Docs versioning](25-docs-versioning.md)
