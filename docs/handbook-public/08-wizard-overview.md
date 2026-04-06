---
nav_title: Wizard overview
public_publish: true
audience: public
product_area: wizard
tier: overview
---

# Blueprints Wizard overview

## What it is

The **Blueprints Wizard** is a guided flow **inside Forge Studio** that walks a team through mission, context, clarification, targets, scope, run plan, review, recheck, and optional **Cursor Launch Pack** export. It aligns with Blueprints concepts; it does **not** automatically modify your **`blueprints/`** git submodule.

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
