# forge-lenses — user guide

Welcome to **forge-lenses**: local workspace visualization for Forge and Blueprints-aligned repos. This guide covers how to **use** the dashboard, **Forge Studio** (Lenses Studio), and the **Blueprints Wizard** from your browser or desktop shell.

**Technical and maintainer documentation** (architecture, APIs, ADRs, implementation notes) is kept in the forge-lenses repository for contributors and is not published on the Blueprints handbook site.

## Start here

| Topic | Description |
|-------|----------------|
| [Interface pages](interface-pages.md) | Classic Lenses vs Forge Studio, plan-aware shells, and where to find major features |
| [Dashboard pages](dashboard-pages.md) | What each major screen does (Overview, Projects, Plan, Websites, …) |
| [Registry configuration](registry-configuration.md) | Optional `workspace-registry.json`, Handbook/Forge links, RBAC overview |
| [Forge plan UI map](ui-map-workflow.md) | How roadmap, WBS, Charge, and evidence connect on **`/plan`** |

## Forge Studio

Open **`/studio/`** on your local lenses server (same host and port as Classic). Forge Studio is the React UI for new features first; many flows also exist in Classic HTML. See [Interface pages](interface-pages.md) for navigation and [Dashboard pages](dashboard-pages.md) for route-level behavior.

## Blueprints Wizard (experimental)

A guided, Blueprints-aligned flow inside Forge Studio at **`/studio/blueprints/wizard/`**. It does **not** modify the `blueprints/` git submodule in your workspace.

- [Blueprints Wizard — guides](wizard/index.md) — progressive help: getting started (101), mission modes (201), advanced usage (301)

## Learn more

- **Repository:** [github.com/autowww/forge-lenses](https://github.com/autowww/forge-lenses)
- **Forge Studio quickstart (Blueprints):** [Forge Studio quickstart](https://blueprints.forgesdlc.com/sdlc--quickstarts-forge-studio.html)
