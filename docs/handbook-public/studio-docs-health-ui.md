---


nav_title: Studio Docs Health UI
public_publish: true
audience: public
product_area: studio
tier: practitioner
handbook_area: studio
learning_level: '201'
section: studio-wizard
description: Project-scoped Docs Health routes and feeds in Forge Studio.
status: shipped
page_type: topic
---

# Studio — Docs Health UI

## What it is

Forge Studio exposes **Docs Health** under each **project** (see **`projects/:name/docs-health`** tokens in the [route atlas](14-studio-route-map.md)). Cards and tables consume the **`GET`** feeds documented in [Docs Health overlays](15-docs-health.md).

## When to use it

After policy or branch changes, or when [First Docs Health scan](05-studio-101_02-first-docs-health-scan.md) shows queue growth — use the UI for **severity** scanning before opening `work-items` in raw JSON.

## API alignment

| Concern | Reference |
|---------|-----------|
| Summary vs work-items totals | [Docs Health overlays](15-docs-health.md) |
| Safe automation | [Schemas and API for builders](16-schemas-and-api-for-builders.md) |
| Session-scoped routes | Atlas **Home** row (`.../docs-health/session/:sessionId`) |

## Verify

Open **Docs Health** for a project that should have signal; the UI should list **issues** consistent with a **`GET /api/docs-health/work-items`** sample from the same server (counts may be filtered — compare trends, not literal clones).

## What to do next

- [Docs Health remediation scenario](examples-scenario-docs-health.md)
- [Studio route atlas](14-studio-route-map.md)
