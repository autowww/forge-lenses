---

nav_title: 'Wizard 301: Cursor Launch Pack'
public_publish: true
audience: public
product_area: wizard
tier: '301'
handbook_area: wizard
learning_level: '301'
section: tutorials-201
status: experimental
description: 'Wizard 301: Cursor Launch Pack — Forge Lenses handbook entry (tutorials-201).'
page_type: tutorial
---

# Wizard 301 — Cursor Launch Pack

## What it is

The last step can package context for **Cursor** (or another editor). Read warnings; strict modes may block export until slices are locked.

**Parent:** [Wizard 301 — Advanced usage](11-wizard-301.md).

## Step-by-step usage (typical)

1. Complete **Review & generate** and **Recheck** so the pack reflects a **passed** or **explicitly accepted** state ([Review and recheck](11-wizard-301_03-review-recheck.md)).
2. Open the **Experimental** or **handoff** step (wording varies by build). If **Cursor Launch Pack** (or similar) is offered, read warnings about **strict** modes — they may block export until required slices are complete.
3. Download or copy the bundle into your editor workspace; treat it as **context**, not automatic execution.
4. If export is blocked, note the UI message and fix the listed step, or export a smaller slice manually.

### UI affordances (plain language)

- **Launch pack** packages **prompt and file context** for your editor — it does not run commands on your machine by itself.
- **Strict** modes exist so teams do not ship half-finished bundles.

## Optional integrations

Some environments offer extra steps (for example creating a remote repository after confirmation). Whether those appear depends on **server policy and configuration** where you run Lenses — not on fields in your session file. If your organization restricts that flow, complete exports manually and place artifacts in your own repo.

If your team maintains the server, advanced setup lives with the **forge-lenses** project; everyday users should rely on this handbook and [Troubleshooting](12-troubleshooting.md).

**Tie-in:** The **worked example session** on [Wizard 301 — Advanced usage](11-wizard-301.md) ends with a **Launch Pack** that carries summary, tasks, and constraints into an editor — the same handoff shape this page describes step by step.

## Verify

You can export or copy the **Launch Pack** without bypassing **strict** mode unintentionally. The bundle includes the slices you expect (summary, tasks, constraints); if export was blocked earlier, the UI listed cause is resolved or you chose a smaller slice on purpose.

## What to do next

- [Wizard 301 — Advanced usage](11-wizard-301.md)
- [Troubleshooting](12-troubleshooting.md)