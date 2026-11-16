---

nav_title: Scenario — sibling repos
public_publish: true
audience: public
product_area: lenses
learning_level: overview
section: builders
description: Layout pattern — multiple product repos beside each other under one workspace
  root.
status: shipped
tier: builder
handbook_area: builders
page_type: topic
---

# Scenario — sibling repos under one workspace

## Outcome

One workspace root lists **multiple checkouts** (siblings) so Lenses scans them together without nesting one repo inside another.

## Canonical path

Follow [Workspace setup — layouts](03-workspace-setup_01-layouts.md) and align your directory tree before tuning scan settings in [Scan host](03-workspace-setup_03-scan-host.md).

## Fixtures

No JSON envelope is standardized for this layout — it is **filesystem structure** only.

## Avoid

- Checking a **single** repo subtree when you meant the **parent** folder that holds all siblings (you will miss cross-repo signals).
