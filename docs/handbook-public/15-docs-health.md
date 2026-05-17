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
caption: Docs Health stays read-only until operators explicitly open mutation tooling
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
