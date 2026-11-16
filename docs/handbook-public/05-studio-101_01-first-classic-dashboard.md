---

nav_title: '101: First Classic dashboard review'
public_publish: true
audience: public
product_area: studio
tier: '101'
handbook_area: studio
learning_level: '101'
section: tutorials-101
status: shipped
description: '101: First Classic dashboard review — Forge Lenses handbook entry (tutorials-101).'
page_type: tutorial
---

# Studio 101 — First Classic dashboard review

## What it is

A **short pass** over the **Classic** HTML UI at **`/`** (same server as Studio) so you know what still lives outside **`/studio/`** and how to spot a healthy landing view.

## When to use it

After [Studio 101 — First session](05-studio-101.md) or in parallel — when you need to **compare Classic vs Studio** ([Studio overview](04-studio-overview.md)) before changing bookmarks or teaching a teammate.

## Outcome

You can name **one** Classic route you trust for daily use and confirm the dashboard is not error-styled or empty due to bind/scan issues.

## Prerequisites

- [Install and run](02-install-and-run.md) completed; server answers on loopback.
- Browser; no API secrets required.

## Scenario

You already opened **`/studio/`** successfully and want **five minutes** on **`/`** to see portfolio or workspace summaries the way long-time users still open them.

## Steps

1. Open **`http://127.0.0.1:8080/`** (adjust host/port). Prefer the same origin you used for Studio.
2. Scan the **header and primary navigation** — note links that still point at Classic-only reports vs redirects toward Studio.
3. Open **one** list or index (for example workspace or portfolio) and confirm **at least one row** of real content.
4. If the page shows **errors or empty state**, note the exact message, then use [Troubleshooting](12-troubleshooting.md) before changing config.

## How to verify success

- **`/`** returns **200** and shows recognizable Lenses chrome (not a blank document).
- You can return to **`/studio/`** and the Classic view you opened still matches your server URL.

## Recover

- **Blank Classic but Studio works** — hard refresh; confirm static assets and `PYTHONPATH` per install docs; see [Troubleshooting](12-troubleshooting.md).
- **NeitherClassic nor Studio** — server not listening on the port you used; restart the Lenses process and recheck logs.

## What to do next

- [Studio 201](06-studio-201.md) for daily review habits.
- [Docs Health 101 — First scan](05-studio-101_02-first-docs-health-scan.md) when you are ready to read documentation hygiene signals.
