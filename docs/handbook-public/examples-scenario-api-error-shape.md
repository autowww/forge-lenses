---

nav_title: Scenario — API errors
public_publish: true
audience: public
product_area: lenses
learning_level: overview
section: builders
description: Canonical HTTP error envelope for integrations and tests.
status: shipped
tier: builder
handbook_area: builders
page_type: topic
---

# Scenario — HTTP error envelopes for builders

## Outcome

Your client parses **`{ "ok": false, ... }`** consistently and matches CI fixtures.

## Canonical path

[Schemas and API for builders](16-schemas-and-api-for-builders.md) — safe **GET** examples only in tutorials; error shape is for **documentation and tests**.

## Fixtures

[`sample-api-error.json`](../examples/sample-api-error.json) — `api-error.schema.json`; run `pytest tests/test_docs_schemas.py`.

## Avoid

- Logging full error bodies that contain **PII** or tokens — scrub in operational pipelines.
