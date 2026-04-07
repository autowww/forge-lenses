---
nav_title: Studio overview
public_publish: true
audience: public
product_area: studio
tier: overview
handbook_area: studio
learning_level: overview
---

# Forge Studio overview

## What it is

**Forge Studio** (also called Lenses Studio) is the **React** UI served at **`/studio/`** on your local Lenses server. It is the default place for **new** product surfaces (with Classic HTML catching up over time). **Blueprints Wizard** is a Studio feature under **`/studio/blueprints/wizard/`**.

## When to use it

Any time you want the newer navigation, Studio-only flows, or the Wizard — after the server from [Install and run](02-install-and-run.md) is up.

## Prerequisites

- Lenses running; browser available.
- If **`/studio/`** looks empty, confirm the server is running, try a hard refresh, then follow [Studio 101](05-studio-101.md) or [Troubleshooting](12-troubleshooting.md).

## First-value path (landing to useful work)

| Step | Action | You should see |
|------|--------|------------------|
| 1 | Open **`/studio/`** | Shell with header + sidebar |
| 2 | Open **workspace** or **projects** from the sidebar | Content for your scanned repos |
| 3 | Pick **one** project | Detail or plan entry points |
| 4 | Optional — **Blueprints Wizard** | Hub at `/studio/blueprints/wizard` ([Wizard overview](08-wizard-overview.md)) |

## Classic vs Studio (task-level)

| Task | Start in… |
|------|-----------|
| Legacy report or route you already use daily | **Classic** `/` |
| Newer flows, Wizard, or Studio-only views | **Forge Studio** `/studio/` |

## Steps

1. Open **`http://127.0.0.1:<port>/studio/`** (same host/port as Classic).
2. Use the **header** and **sidebar** to move between workspace areas (Flows, projects, knowledge — labels vary by plan and version).
3. To try the Wizard, open **Blueprints Wizard** in the sidebar (experimental label in some builds).

## How to verify success

- **`/studio/`** loads a shell with navigation — not a blank page.
- You can reach **Wizard** from the sidebar when the feature is enabled (see [Wizard overview](08-wizard-overview.md)).

## What to do next

- [Studio 101 — First session](05-studio-101.md)
- [Wizard overview](08-wizard-overview.md)