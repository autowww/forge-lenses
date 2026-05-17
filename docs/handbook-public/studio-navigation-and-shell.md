---


nav_title: Studio navigation and shell
public_publish: true
audience: public
product_area: studio
tier: practitioner
handbook_area: studio
learning_level: '201'
section: studio-wizard
description: Header, sidebar, and route families for Forge Studio — companion to the route atlas.
status: shipped
page_type: topic
---

# Studio — navigation and shell

## What it is

How the **Forge Studio** SPA structures **top navigation**, **section sidebars**, and **client routes** under **`/studio/`**, grounded in [`lenses-enterprise/src/App.tsx`](https://github.com/autowww/forge-lenses/blob/main/lenses-enterprise/src/App.tsx). For the exhaustive route checklist, bookmark the **[Studio route atlas](14-studio-route-map.md)**.

## When to use it

- Onboarding operators who need **screen labels** tied to **URL tokens**.
- Before filing bugs about “missing sidebar” — confirm which **route family** you are in.

## Route families (summary)

The **canonical path checklist** (every `projects/...` token, Settings, Governance, and embedded viewers) lives in the **[Studio route atlas](14-studio-route-map.md)**. Use this page for **shell behavior**; use the atlas when you need the **full table**.

| Concern | Read |
|---------|------|
| Project hub, charts, strategy | [Workspace and projects](studio-workspace-and-projects.md) |
| Per-project Docs Health UI | [Docs Health in Studio UI](studio-docs-health-ui.md) |
| LLM, Fleet, experiments settings | [Studio LLM and Fleet settings](studio-settings-llm-fleet.md) |
| Blank shell, assets, API origin | [Studio troubleshooting](studio-troubleshooting.md) |

## Governance and productivity (quick pointer)

**Governance** (`governance/connectors`, `governance/audit`) and **Productivity** (`toolset`, `toolset/:name`) share the same shell: sidebar entries map to nested `<Route>` blocks in `App.tsx`. Deep API notes remain in **[Schemas and API for builders](16-schemas-and-api-for-builders.md)**.

## Verify

Open **`/studio/`** and switch **two** top-level areas; the URL should change under **`/studio/...`** and the sidebar should list the same families described in the atlas table.

## What to do next

- [Studio route atlas](14-studio-route-map.md)
- [Studio overview](04-studio-overview.md)
