---

nav_title: JSON examples for builders
public_publish: true
audience: public
product_area: lenses
learning_level: overview
section: builders
description: Hand-edited JSON samples that track docs/schemas — use with CI and automation
  tests.
status: shipped
tier: builder
handbook_area: builders
page_type: landing
---

# JSON examples (builders)

These files live in [`docs/examples/`](../examples/) beside [`docs/schemas/`](../schemas/). They are **not** runtime fixtures — they track the same shapes `tests/test_docs_schemas.py` validates.

```blueprint-diagram
key: heatmap
alt: Rows of schemas versus CI pytest cells showing validation coverage intensity
title: Builder JSON sample flow
summary: How hand-edited samples stay aligned with schemas and pytest validation in CI.
node: Start
detail: A schema or envelope change signals that samples may be stale.
more: Tracked JSON lives beside docs/schemas/; samples are not runtime fixtures.
node: Core steps (see walkthrough below)
detail: Edit the schema, update matching sample-*.json files, then run pytest.
more: tests/test_docs_schemas.py validates the same shapes the server and builders rely on.
node: Outcome
detail: CI keeps scrubbed, deterministic examples builders can cite safely.
more: Mention behavioral shifts in Schemas and API when HTTP tables move.
caption: Samples stay scrubbed; extend the matrix whenever route families stabilize
fallback_ascii: |
  Process flow

  Start
      |
      v
  Core steps (see walkthrough below)
      |
      v
  Outcome
```

| Example | Schema | Use |
|---------|--------|-----|
| [`sample-wizard-session.json`](../examples/sample-wizard-session.json) | `wizard-session.schema.json` | Session envelope persisted for Wizard |
| [`sample-cursor-launch-pack-manifest.json`](../examples/sample-cursor-launch-pack-manifest.json) | `cursor-launch-pack-manifest.schema.json` | ZIP manifest fragment |
| [`sample-api-error.json`](../examples/sample-api-error.json) | `api-error.schema.json` | Canonical `{ ok: false }` error shape |

## Refresh workflow

1. Edit schema under `docs/schemas/` when the Python server changes envelopes.
2. Update matching `sample-*.json` and run:

   ```bash
   pytest tests/test_docs_schemas.py
   ```

3. Mention behavioral changes in [Schemas and API (builders)](16-schemas-and-api-for-builders.md) if HTTP tables move.

## Classic vs Studio coverage

| Area | Primary doc |
|------|-------------|
| HTTP inventory | **[HTTP API route catalog](../generated/api-routes.md)** + [Schemas and API (builders)](16-schemas-and-api-for-builders.md) ([GitHub narrative](https://github.com/autowww/forge-lenses/blob/main/lenses/website/http-api-and-routes.md))
| Wizard contracts | [Builders schemas](builders-schemas.md) + Wizard chapters ([schema sources on GitHub](https://github.com/autowww/forge-lenses/tree/main/docs/schemas)) |

More narrative context for example authors: **[examples README (GitHub)](https://github.com/autowww/forge-lenses/blob/main/docs/examples/README.md)** — machine-oriented one-liner beside the tracked JSON corpus.

## Scenario stubs (safe, no secrets)

| Product area | What to walk through |
|--------------|----------------------|
| **Classic** | Open `/` dashboard after install; confirm workspace scan ran ([Install](02-install-and-run.md)). |
| **Studio** | Complete [Studio 101](05-studio-101.md) path on `/studio/`. |
| **Wizard** | Throwaway session on hub + session URL ([Wizard 101](09-wizard-101.md)) — **experimental**. |
| **Docs Health** | Run a scan from [Docs Health](15-docs-health.md); inspect severity labels only. |
| **LLM / Fleet** | Local provider probe without pasting API keys ([LLM setup](13-llm-and-ai-setup.md)). |
| **API / schema** | Validate `sample-api-error.json` with `pytest tests/test_docs_schemas.py`. |

Full worked narratives live in tutorials; this hub stays anchored to **checked-in JSON** so CI stays deterministic.
