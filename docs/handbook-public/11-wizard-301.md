---

nav_title: Wizard 301
public_publish: true
audience: public
product_area: wizard
tier: '301'
handbook_area: wizard
learning_level: '301'
section: tutorials-301
status: experimental
description: Wizard 301 — Forge Lenses handbook entry (tutorials-301).
page_type: tutorial
---

# Wizard 301 — Advanced usage

## What it is

Deeper use of the Wizard: **artifact bundles**, **Refine** and LLM-assisted steps, **review and recheck**, and **Cursor Launch Pack** packaging. This hub links to focused pages; read the **worked example session** below once so the advanced topics read as **one workflow**, not isolated toggles.

```blueprint-diagram
key: sequence
alt: Refine prompts call guarded POST routes before review/recheck publishes bundles
title: Advanced Wizard session flow
summary: How artifact emphasis, Refine, review gates, and exports chain through one governed Session shell.
node: What it is
detail: Frames the advanced Wizard topics as one coordinated workflow.
more: Artifact bundles, Refine, review/recheck, and Cursor Launch Pack share the same Session shell as Wizard 101/201.
node: Actor / trigger
detail: A squad starts or resumes a server-enabled Wizard session.
more: Prerequisites assume stable server-enabled sessions from Wizard 201; the team picks bundle emphasis and enters stage content.
node: System step
detail: Optional LLM steps run behind guarded POST routes in-session.
more: Refine rewrites Understanding notes; Review and Recheck validate artifacts before publish, using the same bounded session API as earlier tiers.
node: Outcome / handoff
detail: Reviewed bundles and Launch Pack export for bounded editor handoff.
more: Exports match team policy; Recheck passes or gaps are knowingly accepted before the pack leaves the session.
caption: Wizard 301 coordinates LLM optional steps behind the same Session shell as 101/201
fallback_ascii: |
  What it is

  Actor / trigger
      |
      v
  System step
      |
      v
  Outcome / handoff
```

## When to use it

After [Wizard 201](10-wizard-201.md), when you are tuning outputs or exports.

## Prerequisites

- Stable **server-enabled** sessions when possible ([Wizard 201](10-wizard-201.md)).

## Topics

| Topic | Page |
|-------|------|
| **Artifact bundles** | [Artifact bundles](11-wizard-301_01-artifact-bundles.md) |
| **Refine** | [Refine](11-wizard-301_02-refine.md) |
| **Review and recheck** | [Review and recheck](11-wizard-301_03-review-recheck.md) |
| **Cursor Launch Pack** | [Cursor Launch Pack](11-wizard-301_04-cursor-launch-pack.md) |

## Worked example session (generic)

**Scenario:** A squad runs a Wizard session for an **internal API reliability** initiative — not greenfield, but enough discovery that Mission and Understanding still matter.

**1. Bundle choice ([Artifact bundles](11-wizard-301_01-artifact-bundles.md))** — At **Target & output pack**, the team picks **Engineering** emphasis (labels may say “engineering” or similar in your build). **Why:** they need tasks, risks, and guardrails for the next increment more than a marketing-style roadmap slice.

**2. Refine ([Refine](11-wizard-301_02-refine.md))** — In **Understanding**, they run **Refine** on a short paragraph about current outages. The first pass smooths wording but drops an explicit **SLO** mention. The product lead **edits the notes** to put the SLO back, adds a **non-goal** (“no new datastore”), and Refines once more. The second pass keeps both.

**3. Review and Recheck ([Review and recheck](11-wizard-301_03-review-recheck.md))** — **Review & generate** surfaces an artifact set that lists **two owners** for the same risk class. **Recheck** flags an inconsistency between the run plan and the risk table. The team fixes the **session** (single owner per risk class, dates aligned), regenerates, and Recheck **passes**.

**4. Cursor Launch Pack ([Cursor Launch Pack](11-wizard-301_04-cursor-launch-pack.md))** — At **Experimental build** / handoff, they export a **Launch Pack** (wording varies). At a high level it includes: a **session summary** slice, **near-term tasks** with owners, and **constraints** copied from notes — enough for an editor session without pasting private chat. They treat it as **context for humans**, not auto-execution.

**Outcome:** One coherent story from **emphasis → Refine → gate → export**; child pages below unpack each lever.

## How to verify success

- Exports match your policy; recheck passes or you knowingly accept gaps.

## What to do next

- [Artifact bundles](11-wizard-301_01-artifact-bundles.md) — emphasis and packs
- [Troubleshooting](12-troubleshooting.md)