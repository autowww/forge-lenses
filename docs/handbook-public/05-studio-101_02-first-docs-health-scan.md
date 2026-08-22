---

nav_title: '101: First Docs Health scan'
public_publish: true
audience: public
product_area: lenses
tier: '101'
handbook_area: lenses
learning_level: '101'
section: tutorials-101
status: shipped
description: '101: First Docs Health scan — Forge Lenses handbook entry (tutorials-101).'
page_type: tutorial
---

# Docs Health 101 — First scan

## What it is

A **read-only** check of the **Docs Health** JSON feeds (or the Studio panel that consumes them) so you can see documentation hygiene signals without changing repos.

## When to use it

When branching or handbook policy changed, or right after your **[first Classic review](05-studio-101_01-first-classic-dashboard.md)**, before asking agents to fix docs drift.

## Outcome

You have looked at **summary** and **work-items** (or their Studio equivalent) once and understand what “clean vs in trouble” means for your workspace.

## Prerequisites

- Server from [Install and run](02-install-and-run.md).
- **GET-only** access on loopback — follow [Schemas and API for builders](16-schemas-and-api-for-builders.md) if you script calls; no mutating verbs in this tutorial.

## Scenario

You want a **2–5 minute** sanity check: counts on **`/api/docs-health/summary`** line up with **`/api/docs-health/work-items`** totals you see in Forge Studio.

## Steps

1. Read the reference table in [Docs Health in Studio](15-docs-health.md) so you know the three paths (`summary`, `work-items`, `live-sessions`).
2. From the same host the server binds to, request **`GET /api/docs-health/summary`** and **`GET /api/docs-health/work-items`** (browser, `curl`, or Studio cards — **GET only**).
3. Compare **roll-up counts** in `summary` with **`total`** or list length in `work-items` as described on the product-area page.
4. Optionally skim **`live-sessions`** if you run verification jobs — correlate `repo` fields with your checkout paths.
5. If Studio exposes a **Docs Health** panel, open it and confirm it shows the same signals you saw in JSON.

## How to verify success

- Both **summary** and **work-items** return **200** JSON (not HTML error pages).
- Totals **reconcile** the way [Docs Health in Studio](15-docs-health.md) describes; you can explain one **work-item** type in plain language.

## Recover

- **401/403** — your deployment may require auth; see [Security and local-first operations](17-security-and-local-first.md) and server operator docs — do not paste tokens into tickets.
- **Connection refused** — wrong host/port or server down; fix [Install and run](02-install-and-run.md) first.
- **Empty queues but you expect issues** — scan paths or branch policy may exclude repos; see maintainer **`docs-health-git-branch-policy`** references from [Docs Health in Studio](15-docs-health.md).

## What to do next

- [Studio 201](06-studio-201.md) for operational habits.
- [Schemas and API for builders](16-schemas-and-api-for-builders.md) for safe automation patterns.
