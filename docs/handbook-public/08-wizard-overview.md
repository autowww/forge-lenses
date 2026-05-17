---

nav_title: Wizard overview
public_publish: true
audience: public
product_area: wizard
tier: overview
handbook_area: wizard
learning_level: overview
section: studio-wizard
status: experimental
description: Wizard overview — Forge Lenses handbook entry (product-areas).
page_type: concept
---

# Blueprints Wizard overview

## What it is

The **Blueprints Wizard** is a guided flow **inside Forge Studio** that walks a team through mission, context, clarification, targets, scope, run plan, review, recheck, and optional **Cursor Launch Pack** export. It aligns with Blueprints concepts; it does **not** automatically modify your **`blueprints/`** git submodule.

### Terms (quick read)

| Term | Plain language |
|------|----------------|
| **Wizard** | **Guided planning / assessment workflow** — structured steps and artifacts, not auto-edits to your repo. |
| **Forge Studio** | **Local workspace UI** where the Wizard runs (`/studio/`). |
| **Artifact bundle / pack** | Emphasis the session gives to planning vs engineering vs execution outputs (labels vary by build). |

## Good for / not for

| Good for | Not the best tool when… |
|----------|-------------------------|
| Facilitated workshops with a shared narrative | You only need a one-line edit in existing Markdown |
| Aligning before branching or a new initiative | You want unattended automation to bump git submodules |
| Producing exports and packs for the next engineering step | Your team will not read or update session notes |

## Inputs and outputs (conceptual)

| Phase | You bring | You leave with |
|-------|-----------|----------------|
| **Mission through scope** | Context, constraints, disagreements | Shared targets and an explicit increment |
| **Run plan through review** | Owners, risks, dependencies | Ordered steps and generated artifacts |
| **Recheck / experimental** | Policy for exports | Packaged handoff (for example Cursor Launch Pack) when enabled |

## Trust boundaries (Studio ↔ Lenses ↔ outbound)

```blueprint-diagram
key: sequence
alt: Trust boundaries for Wizard sessions vs repo and outbound services
caption: Wizard stores session JSON locally; LLM and Fleet calls are explicit POST surfaces
```

| Boundary | Shipped today | Your responsibility |
|----------|---------------|---------------------|
| **Git working tree** | Wizard does **not** auto-commit Blueprints submodule bumps | Review exports before `git add` |
| **`.lenses-local/`** | Session envelope + telemetry land here | Back up or wipe per policy ([Security and local-first](17-security-and-local-first.md)) |
| **LLM vendor** | Optional refine/interpret calls via server-side POST routes | Redact prompts; use corporate gateways when required |
| **Forge Fleet** | Optional job orchestration when enabled | Treat bearer tokens like production secrets |

Deep dives: [Wizard — operator trust boundaries](wizard-operator-trust-boundaries.md) and [Wizard — builder session HTTP API](wizard-builder-session-api.md).

## Session lifecycle (happy path)

```blueprint-diagram
key: linear
alt: Wizard session lifecycle from hub create through export
caption: Hub creates id; session route loads stepper; exports are explicit actions
```

```blueprint-diagram
key: state
alt: Wizard session states from hub through review and optional export
caption: Happy path advances; recheck or repair can loop until consistency passes
```

## When to use it

When you want a **facilitated workshop**, a **shared narrative** before branching, or a **bootstrap** for a new initiative — not when you only need a one-line edit in existing Blueprints files.

## Prerequisites

- [Studio overview](04-studio-overview.md) — server and **`/studio/`** work.
- Wizard routes visible in the sidebar (see **Enable** below).

## Steps

### Enable (if the Wizard is hidden)

Visibility depends on **how your Lenses build and server are configured**. If the Wizard does not appear in the Studio sidebar, confirm you are on a build that includes it, or ask whoever maintains your Lenses installation. Operator-level configuration is documented in the **forge-lenses** repository on GitHub.

### Open the Wizard

1. Go to **`/studio/`**.
2. Open **Blueprints Wizard (experimental)** in the sidebar.
3. You land on the **Hub** at **`/studio/blueprints/wizard`** — create or resume a **session**.

## How to verify success

- Hub loads and lets you **create a session**.
- A session URL matches **`/studio/blueprints/wizard/session/<id>`**.

## What to do next

- [Wizard 101 — First session](09-wizard-101.md)
- [Wizard 201 — Mission modes](10-wizard-201.md)