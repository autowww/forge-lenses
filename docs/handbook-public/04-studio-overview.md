---
nav_title: Studio overview
public_publish: true
audience: public
product_area: studio
tier: overview
---

# Forge Studio overview

## What it is

**Forge Studio** (also called Lenses Studio) is the **React** UI served at **`/studio/`** on your local Lenses server. It is the default place for **new** product surfaces (with Classic HTML catching up over time). **Blueprints Wizard** is a Studio feature under **`/studio/blueprints/wizard/`**.

## When to use it

Any time you want the newer navigation, Studio-only flows, or the Wizard — after the server from [Install and run](02-install-and-run.md) is up.

## Prerequisites

- Lenses running; browser available.
- If the Studio page is empty, you may need to build the Studio bundle once (see [Studio 101](05-studio-101.md)).

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
