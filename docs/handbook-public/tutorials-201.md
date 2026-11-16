---

nav_title: Tutorial ladder — 201 overview
public_publish: true
audience: public
product_area: lenses
learning_level: '201'
section: tutorials-201
description: Intermediate tutorials — Studio habits, Wizard stages, LLM setup, Cursor
  launch pack.
status: shipped
tier: tutorial
handbook_area: tutorials-201
page_type: landing
---

# Tutorials — 201 (overview)

## Prerequisites

- Finish **[Tutorials — 101](tutorials-101.md)** milestones or demonstrate equivalent familiarity with **`/studio/`** URLs and Wizard hubs.
- Skim **[Configuration reference](../reference/config-env.md)** when you widen network binds, Fleet integrations, or LLM gateways referenced in deeper chapters.

201 chapters assume you finished **[Tutorials — 101](tutorials-101.md)** or have equivalent comfort with `/studio/` and the Wizard hub.

| Guide | Time (typ.) | Outcome |
|-------|-------------|---------|
| [Studio 201](06-studio-201.md) | 15–20 min | Repeatable review habits in Studio |
| [Wizard 201](10-wizard-201.md) | 30–45 min | Move a session through assess → refine stages |
| [Wizard 201 — start from idea](10-wizard-201_01-start-from-idea.md) | 15–20 min | Green-field session bootstrap |
| [Wizard 201 — assess project](10-wizard-201_02-assess-current-project.md) | 15–25 min | Brown-field assessment pass |
| [Wizard 201 — resume](10-wizard-201_03-resume-and-advance.md) | 10–15 min | Pick up a session after idle time |
| [Wizard 201 — repair](10-wizard-201_04-repair-stage.md) | 15–20 min | Recover from a stuck or failed stage |
| [LLM and AI setup](13-llm-and-ai-setup.md) | 20–40 min | Optional gateways for AI-assisted features |
| [Cursor Launch Pack](11-wizard-301_04-cursor-launch-pack.md) | 15–25 min | Export/preview a Cursor-oriented pack |

## Studio reference (URLs and settings)

| Page | Use when |
|------|----------|
| [Studio route atlas](14-studio-route-map.md) | You need the full **token × API** table |
| [Navigation and shell](studio-navigation-and-shell.md) | Explaining the shell to a teammate |
| [Workspace and projects](studio-workspace-and-projects.md) | Project hub / embedded viewers |
| [Docs Health UI](studio-docs-health-ui.md) | Project-scoped hygiene panels |
| [LLM and Fleet settings](studio-settings-llm-fleet.md) | Settings panes after [LLM setup](13-llm-and-ai-setup.md) |

## Verification pattern

For every 201 chapter: finish the **Time / Verify / Scenario** table at the top of the page (where present), then capture one screenshot or note your session id **locally** if you are debugging — do not post identifiers publicly.

## Recover

Rollback experimental flags (`LENSES_ALLOW_*`), restore loopback binds, then follow **[Studio troubleshooting](studio-troubleshooting.md)** before escalating to **[Troubleshooting](12-troubleshooting.md)** when HTTP surfaces fail entirely.

## Next ladder

Advanced Studio/Wizard mechanics live under **[Tutorials — 301](tutorials-301.md)**.
