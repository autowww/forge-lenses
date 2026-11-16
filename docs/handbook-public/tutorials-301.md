---

nav_title: Tutorial ladder — 301 overview
public_publish: true
audience: public
product_area: lenses
learning_level: '301'
section: tutorials-301
description: Advanced tutorials — deep Studio navigation and Wizard artifact loops.
status: shipped
tier: tutorial
handbook_area: tutorials-301
page_type: landing
---

# Tutorials — 301 (overview)

## Prerequisites

- Keep **Wizard 201 + Studio 201** habits fresh (reviews, checkpoints, reversible exports).
- Read **[Experimental surfaces](#experimental-surfaces)** so you recognize feature-flag divergence.

301 content assumes **201** habits are in place and you are comfortable losing a throwaway session.

| Guide | Time (typ.) | Outcome |
|-------|-------------|---------|
| [Studio 301](07-studio-301.md) | 25–35 min | Navigate advanced Studio surfaces without breaking context |
| [Wizard 301](11-wizard-301.md) | 20–30 min | Coordinate bundles, refine, and review passes |
| [Artifact bundles](11-wizard-301_01-artifact-bundles.md) | 15–20 min | Shape exports for downstream tooling |
| [Refine](11-wizard-301_02-refine.md) | 20–30 min | Tighten assumptions with structured prompts |
| [Review / recheck](11-wizard-301_03-review-recheck.md)| 15–25 min | Validate outputs before handoff |

## Studio subsite (301 depth)

Pair [Studio 301](07-studio-301.md) with the atlas and focused pages: [Studio route atlas](14-studio-route-map.md), [Navigation and shell](studio-navigation-and-shell.md), [Workspace and projects](studio-workspace-and-projects.md), [LLM and Fleet settings](studio-settings-llm-fleet.md), [Docs Health UI](studio-docs-health-ui.md).

## Experimental surfaces

Some 301 flows depend on **feature flags** or optional LLM gateways. Callouts in each chapter mark **experimental** behavior — treat those steps as best-effort until your build matches the documented flag matrix in [Configuration reference](../reference/config-env.md).

## When to escalate

If Studio is blank, assets 404, or Wizard sessions fail to persist, start at [Troubleshooting](12-troubleshooting.md) before assuming a methodology issue.

## Recover

Turn off experimental gateways, reconcile **`.lenses-local/`** checkpoints against [Security and local-first](17-security-and-local-first.md), then resume from **[Wizard 301](11-wizard-301.md)** once the workspace root matches your intent.
