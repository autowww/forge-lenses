---

nav_title: Docs Health in Studio
public_publish: true
audience: public
product_area: lenses
tier: practitioner
handbook_area: lenses
learning_level: '201'
section: studio-wizard
status: shipped
description: Docs Health in Studio — Forge Lenses handbook entry (product-areas).
page_type: topic
---

# Docs Health overlays

## What it is

Forge Studio exposes three JSON feeds for documentation hygiene:

```blueprint-diagram
key: linear
alt: Summary feed to work items to live sessions with GET-only verification first
title: Docs Health overlay flow
summary: How operators inspect documentation hygiene through read-only JSON feeds before opening mutation tooling.
node: What it is
detail: Studio exposes three GET feeds for documentation hygiene signals.
more: The summary, work-items, and live-sessions endpoints roll up counts, remediation queues, and active verification jobs.
node: Start
detail: Operators open Docs Health when policy or handbook drift is suspected.
more: Typical triggers include branching policy changes or agents reporting divergent handbook copies across submodules.
node: Core steps (see walkthrough below)
detail: Verify each endpoint with GET-only checks from localhost.
more: Hit summary, work-items, and live-sessions; reconcile counts and correlate live-sessions repos with Fleet nodes when proxies run.
node: Outcome
detail: Confirmed hygiene state without invoking mutation tooling.
more: Docs Health stays read-only until operators explicitly choose remediation paths linked from Troubleshooting.
caption: Docs Health stays read-only until operators explicitly open mutation tooling
fallback_ascii: |
  What it is

  Start
      |
      v
  Core steps (see walkthrough below)
      |
      v
  Outcome
```

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/docs-health/summary` | Roll-up signal for dashboards (counts, repos in trouble). |
| `GET` | `/api/docs-health/work-items` | Queue of remediation issues with stable ids for agents. |
| `GET` | `/api/docs-health/live-sessions` | Who currently runs verification jobs vs which repo/checkout. |

## When to open the panel

- After branching policy changes (**`docs-health-git-branch-policy.html`** in maintainer handbook).
- When Cursor agents report divergent handbook copies — cross-check **`work-items`** payload before editing submodules blindly.

## How to verify

1. Hit each endpoint curl-style from **`127.0.0.1`** (matching server bind).
2. Ensure summary counts reconcile with **`work-items` → `total`** (Studio cards already do this; duplicate check when customizing).
3. For live audits, correlate **`live-sessions[].repo`** entries with Forge Fleet nodes if proxies are enabled.

## Steps

Execute the numbered checks under **[How to verify](#how-to-verify)** above whenever you change branching policy or suspect stale caches.

Remediation tips live primarily in **`12-troubleshooting.html`**; operator deep dives stay in the **`forge-lenses`** GitHub tree under **`docs/maintainer/`** (not mirrored to the lightweight public handbook build).

## Recover

If summaries disagree with **`work-items`**, restart Lenses after clearing stale caches — see **[Troubleshooting](12-troubleshooting.md)** for Docs Health remediation loops.

## What to do next

- **[Troubleshooting](12-troubleshooting.md)** — when CI agents disagree with Studio counts.
- **[Schemas and API (builders)](16-schemas-and-api-for-builders.md)** — payload shapes behind **`/api/docs-health/*`** when extending automation.
