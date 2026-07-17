---

nav_title: Builders — JSON schemas
public_publish: true
audience: public
product_area: lenses
learning_level: reference
section: builders
description: Schema directory, samples, and pytest coverage for docs fixtures.
status: shipped
tier: builder
handbook_area: builders
page_type: topic
---

# Builders — JSON schemas

## What it is

`docs/schemas/` holds JSON Schema files checked by **`tests/test_docs_schemas.py`**. Companion samples live in `docs/examples/` and are indexed from [JSON examples hub](19-examples-hub.md).

```blueprint-diagram
key: tree
alt: Schema directory branching to samples, pytest contract, and generated OpenAPI mirrors
title: Schema directory contract tree
summary: How docs/schemas/ branches to samples, pytest contracts, and generated OpenAPI mirrors as versioned builder contracts.
node: What it is
detail: The schema directory and its role in the builders reference surface.
more: docs/schemas/ holds JSON Schema files that builders treat as versioned contracts alongside HTTP route catalogs.
node: Root / intake
detail: The docs/schemas/ directory where JSON Schema contract files live.
more: Change Python envelopes first, then update the matching schema file before refreshing samples and running pytest.
node: branch A
detail: Companion sample JSON files in docs/examples/ indexed from the examples hub.
more: Each sample-*.json fixture proves the schema against realistic payloads builders can copy.
node: branch B
detail: The pytest contract in tests/test_docs_schemas.py that validates schemas and samples.
more: CI fails on test_docs_schemas when schema edits drift from Python envelopes or companion samples.
node: branch C
detail: Generated schema-index and partial OpenAPI mirrors refreshed by check-docs.sh.
more: export_schema_index.py and export_openapi.py emit docs/generated artifacts for auditors; OpenAPI coverage is partial, not authoritative parity.
caption: Builders treat schemas as versioned contracts alongside HTTP route catalogs
fallback_ascii: |
  What it is

  Root / intake
      +-- branch A
      +-- branch B
      +-- branch C
```

## Workflow

1. Change Python envelopes first, then schema.
2. Update matching **`sample-*.json`**.
3. Run `pytest tests/test_docs_schemas.py`.

Additional machine-generated artifacts refreshed by **`scripts/check-docs.sh`** for auditors:

- **`docs/generated/schema-index.json`** — `generator/export_schema_index.py` indexes every `.schema.json` file.
- **`docs/generated/openapi.json`** — `generator/export_openapi.py` mirrors `docs/generated/api-routes.json` with **partial** path coverage (**not** authoritative OpenAPI parity yet — read **[Builders — OpenAPI](builders-openapi.md)**).

## Verify

CI passes on **`test_docs_schemas`** after your schema edit.

## What to do next

- [Schemas and API (builders)](16-schemas-and-api-for-builders.md)
