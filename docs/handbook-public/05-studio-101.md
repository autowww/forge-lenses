---

nav_title: Studio 101
public_publish: true
audience: public
product_area: studio
tier: '101'
handbook_area: studio
learning_level: '101'
section: tutorials-101
status: shipped
description: Studio 101 — Forge Lenses handbook entry (tutorials-101).
page_type: tutorial
---

# Studio 101 — First session

## What it is

Your **first successful visit** to Forge Studio: confirm **`/studio/`** loads, then complete one simple navigation path (for example open a project or workspace view).

## When to use it

Right after [Install and run](02-install-and-run.md), before deeper Studio or Wizard work.

## Time and checks

| | |
|-|--|
| **Time** | **5–10 minutes** once the server is up. |
| **Check** | `/studio/` returns **200** and the shell renders without a blank white screen. |
| **Scenario** | You just finished install and need proof Studio is viable before inviting a teammate. |
| **Next** | [Studio 201](06-studio-201.md) for daily review habits. |

## Prerequisites

- Server running.
- Modern browser.

## Glossary (labels you may see)

| Label | Meaning in practice |
|-------|---------------------|
| **Workspace** | The lens across your scanned repos |
| **Projects** | A single product/repo focus |
| **Plans / Flow** | Delivery-oriented views (names vary) |

Exact wording changes between builds; use this table only to orient, not as an API.

```blueprint-diagram
key: linear
alt: Studio first session flow
caption: Open Studio, confirm workspace, open one project
fallback_ascii: |
  +-------------+     +------------------+     +----------------+
  | Open /studio| --> | Confirm workspace | --> | Open a project |
  +-------------+     +------------------+     +----------------+
```

## Expected outcome

You leave this tutorial with **`/studio/`** returning HTTP **200**, visible chrome (navigation + content panels), and confidence that one workspace/project surface renders live data—matching the baseline captured in [Install and run](02-install-and-run.md).

## First session flow

| # | Action | Expected result |
|---|--------|-----------------|
| 1 | Confirm Classic loads at `/` | Server healthy ([Install and run](02-install-and-run.md)) |
| 2 | Open `/studio/` | Chrome appears — not a blank document |
| 3 | Use sidebar once | One area shows real content |

## Steps

1. Open **`http://127.0.0.1:8080/studio/`** (adjust host/port if yours differs).

2. If you see a **blank page** or missing assets, treat it as an environment issue: confirm the server started cleanly, then follow [Troubleshooting](12-troubleshooting.md).

3. Use the **sidebar** to open **one** primary area (for example **Projects** or **Workspace**) and confirm content appears.

## Verify

- **`/studio/`** shows chrome and at least one content area without errors.
- You can repeat the navigation without reading source files.

## Recover

If you still see a **blank `/studio/` page**, restart the server, confirm asset URLs resolve, then walk through [Troubleshooting](12-troubleshooting.md) starting with **Fast triage**.

## What to do next

- [Studio 201](06-studio-201.md)
- [Wizard overview](08-wizard-overview.md)