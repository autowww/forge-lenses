---
nav_title: Lenses overview
public_publish: true
audience: public
product_area: lenses
tier: overview
handbook_area: lenses
learning_level: overview
---

# Lenses overview

## What it is

**Lenses** is a local workspace dashboard for Forge- and Blueprints-aligned repositories: you run a small Python server on your machine and use the browser (or an optional desktop shell) to inspect projects, plans, and knowledge in one place.

### Terms (quick read)

| Term | Plain language |
|------|----------------|
| **Lenses** | **Local engineering workspace dashboard** — Python server + browser UI for repo visibility. |
| **Forge Studio** | **Local workspace UI** at `/studio/` on that server — newer flows and the Wizard. |
| **Wizard** | **Guided project planning workflow** inside Studio — sessions and exports. |

Three **products** sit on top of the same server:

| Product | What you use it for |
|---------|---------------------|
| **Lenses (Classic)** | Server-rendered dashboard at the site root — projects, overview, plan views, and knowledge links. |
| **Forge Studio** | React app at **`/studio/`** — newer UI for the same workspace; where **Blueprints Wizard** lives. |
| **Blueprints Wizard** | Guided session flow inside Studio at **`/studio/blueprints/wizard/`** — structured workshops and exports; it does **not** auto-commit to your `blueprints/` submodule. |

### Three surfaces (visual)

Classic, Forge Studio, and the Blueprints Wizard share one local server; pick the surface by job (see table below).

```blueprint-diagram
key: tree
alt: Lenses server — Classic at /, Forge Studio at /studio/, Wizard inside Studio
```

### Which surface for which job

| Job | Start here |
|-----|------------|
| Daily scan of repos and health | **Classic** `/` |
| Newer UX, Studio-only flows | **Forge Studio** `/studio/` |
| Facilitated workshop or export pack | **Wizard** ([Wizard overview](08-wizard-overview.md)) |

## When to use it

Use Lenses when you want **visibility across sibling repos** (optional multi-root workspace), **Forge plan** surfaces, and **Studio + Wizard** without deploying anything to the cloud.

## Prerequisites

- **Git**, **Python 3**, and dependencies from the forge-lenses repo (`pip install -r requirements.txt` in a venv).
- A directory layout you are allowed to scan (your clones).

## Steps

1. Install and run the server — see [Install and run](02-install-and-run.md).
2. Point Lenses at your workspace — see [Workspace setup](03-workspace-setup.md).
3. Open **Classic** at `/` or **Forge Studio** at `/studio/` — see [Studio overview](04-studio-overview.md).

## How to verify success

- The home page loads at your chosen host and port (default **http://127.0.0.1:8080/**).
- **`/api/workspace-state`** returns JSON when the server is healthy.

## What to do next

- [Install and run](02-install-and-run.md)
- [Workspace setup](03-workspace-setup.md)
- [Studio overview](04-studio-overview.md)

**Contributors:** deeper architecture and API references stay in the [forge-lenses](https://github.com/autowww/forge-lenses) repository on GitHub — not on this public handbook site.