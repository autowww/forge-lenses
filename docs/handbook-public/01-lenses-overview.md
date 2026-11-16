---
nav_title: Lenses overview
public_publish: true
audience: public
product_area: lenses
tier: overview
handbook_area: lenses
learning_level: overview
section: product
status: shipped
description: Lenses overview — Forge Lenses handbook entry (start).
page_type: landing
content_id: forge.docs.lenses.overview
canonical_owner: forge-lenses
primary_persona: engineering_leader
reader_stage: discover
maturity: demonstrated
evidence_level: canonical_doc
refresh_policy: on_claim_change
last_reviewed: '2026-07-03'
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
title: Three surfaces one server
summary: Classic, Forge Studio, and Blueprints Wizard share one local Python server at distinct URL paths.
node: What it is
detail: Entry framing for how Lenses products relate on one host.
more: The overview below maps each branch to a product surface you open in the browser after install.
node: Root / intake
detail: The local Lenses server that scans your workspace.
more: One process serves Classic at `/` and Studio at `/studio/`; no cloud deployment is required.
node: branch A
detail: Classic Lenses at `/` for daily repo and health scans.
more: Server-rendered dashboard for projects, overview, plan views, and knowledge links.
node: branch B
detail: Forge Studio at `/studio/` for newer, Studio-only UX flows.
more: React app on the same server; entry point for capabilities that Classic does not surface.
node: branch C
detail: Blueprints Wizard inside Studio for facilitated workshop sessions.
more: Guided flow at `/studio/blueprints/wizard/`; exports packs without auto-committing to your blueprints submodule.
node: Note: `/` |
detail: Classic occupies the site root path on the server.
more: Default URL is http://127.0.0.1:8080/; use it when the job is workspace visibility, not workshop facilitation.
node: | Newer UX, Studio-only flows |
detail: Studio paths carry flows that Classic does not expose.
more: Open `/studio/` when you need the Wizard, newer navigation, or other Studio-only capabilities described in the Studio overview.
fallback_ascii: |
  What it is

  Root / intake
      +-- branch A
      +-- branch B
      +-- branch C

  Note: `/` |
  | Newer UX, Studio-only flows |
```

### Which surface for which job

| Job | Start here |
|-----|------------|
| Daily scan of repos and health | **Classic** `/` |
| Newer UX, Studio-only flows | **Forge Studio** `/studio/` |
| Facilitated workshop or export pack | **Wizard** ([Wizard overview](08-wizard-overview.md)) |

### Product map — integrations and Docs Health

| Concern | Where it lives |
|---------|----------------|
| **Docs Health** scans & reports | [Docs Health](15-docs-health.md); Studio-focused UI notes in product pages. |
| **HTTP surfaces for automation** | [Builders overview](builders-api-overview.md), [Schemas and API (builders)](16-schemas-and-api-for-builders.md), generated [HTTP API route catalog](../generated/api-routes.md). |
| **Environment & knobs** | [Configuration reference](../reference/config-env.md) cross-linked from Enterprise pages. |
| **Fleet or LLM (optional)** | Configured deliberately — see [LLM and AI setup](13-llm-and-ai-setup.md) and enterprise guides. |

### Maintainer vs product documentation boundary

Everything under **`docs/handbook-public/`**, **`docs/reference/`** (entries listed in **`docs/nav.yml`**), **`docs/generated/`** mirrors, is **oriented toward readers adopting Lenses**.

**Contributor-only** drafts, ADRs, raw strategy inventories, and publishing workflows live under **`docs/maintainer/`**, **`docs/strategy/`**, and related trees in the **[GitHub repository](https://github.com/autowww/forge-lenses)**. They summarize into public pages instead of leaking as primary reader links.

When you finish this overview and install, **[Pick your path](role-based-paths.md)** helps choose Studio, Wizard (experimental), Enterprise, or builder tracks.

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

## Executive capsule

**Lenses** is a local workspace dashboard for Forge- and Blueprints-aligned repositories: you run a small Python server on your machine and use the browser (or an optional desktop shell) to inspect projects, plans, and knowledge in one place. Maturity: **demonstrated**.

## Who this is for

Engineering leaders at the **discover** stage. Skim the executive capsule first; agents should respect the page frontmatter contract.

## Evidence and maturity

Maturity: **demonstrated**. Statements here reflect the owning repo (`forge-lenses`) at `last_reviewed`; treat anything not explicitly marked as demonstrated as design direction rather than a shipped guarantee.

## Trust boundary

Forge keeps humans in charge of promotion, approval, and release decisions; automation proposes and executes only within approved boundaries described here.

## How to use this page

Read top-to-bottom at your depth: capsule for the decision, mechanism for design, links below for the next step in your journey.

## How it works

The sections above and below describe the mechanism in practice; read them top-to-bottom for the operating model, and follow the linked canonical references for contract-level detail.

## How it fits the Forge ecosystem

This page belongs to its owning repo's canonical documentation and links outward to the related Forge surfaces (methodology in Blueprints, product docs in each product handbook, adoption narrative on forgesdlc.com). Follow the related links to stay on the governed path.
