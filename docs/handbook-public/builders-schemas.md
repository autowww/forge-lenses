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
caption: Builders treat schemas as versioned contracts alongside HTTP route catalogs
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
