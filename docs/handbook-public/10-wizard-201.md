---

nav_title: Wizard 201
public_publish: true
audience: public
product_area: wizard
tier: '201'
handbook_area: wizard
learning_level: '201'
section: tutorials-201
status: experimental
description: Wizard 201 — Forge Lenses handbook entry (tutorials-201).
page_type: tutorial
---

# Wizard 201 — Mission modes

## What it is

The **first wizard step** asks for a **mission mode**. Four options set the **posture** for the rest of the session so targets, scope, and run plan stay coherent.

## When to use it

When you pick **Mission** in a new or resumed session ([Wizard 101](09-wizard-101.md)).

## Prerequisites

- [Wizard 101](09-wizard-101.md) concepts understood.

## Mission modes at a glance

| Mode | Choose it when… | Deep dive |
|------|-----------------|----------|
| **Start from idea** | Discovery is open; problem and constraints are still fuzzy | [Start from idea](10-wizard-201_01-start-from-idea.md) |
| **Assess current project** | Code exists but Forge / Blueprints practices are uneven | [Assess current project](10-wizard-201_02-assess-current-project.md) |
| **Resume and advance** | Foundation work exists; you need the **next chapter** (for example MVP to scale) | [Resume and advance](10-wizard-201_03-resume-and-advance.md) |
| **Repair stage** | Process drift, inconsistent artifacts, or a blocked stage | [Repair stage](10-wizard-201_04-repair-stage.md) |

### Decision prompts (plain language)

| Question | If “yes” → |
|----------|------------|
| Are we still proving the problem and value? | **Start from idea** |
| Do we have shipping code but messy process or docs? | **Assess current project** |
| Do we already have a plan and need the *next* increment? | **Resume and advance** |
| Are we stuck, inconsistent, or blocked on a stage? | **Repair stage** |

### Mission modes (visual)

The four modes differ by how much is unknown vs how much is already shipping; use the table above to pick a child page.

```blueprint-diagram
key: quadrant
alt: Wizard 201 mission modes — idea vs assess vs resume vs repair
title: Wizard mission session flow
summary: How choosing a mission mode frames the wizard steps that follow for one bounded initiative.
node: Mission modes at a glance
detail: The overview that frames the four posture options above.
more: Use the decision table to match unknowns and shipping state before you start.
node: Start
detail: You open or resume a wizard session and pick mission mode.
more: Mission is the first step; it sets targets, scope, and run plan coherence for everything after.
node: Core steps (see walkthrough below)
detail: Child pages walk through mode-specific wizard steps.
more: Each of the four modes links to a deep dive; downstream steps should not fight the posture you chose.
node: Outcome
detail: A session result aligned with the mission you selected.
more: Verify success by confirming the mode matches team posture and downstream steps stay coherent.
node: Note: one session per initiative
detail: Keep one wizard session scoped to a single initiative.
more: Start a new session on a hard pivot; name sessions on the hub for later retrieval.
fallback_ascii: |
  Mission modes at a glance

  Start
      |
      v
  Core steps (see walkthrough below)
      |
      v
  Outcome

  Note: one session per initiative
```

### Sessions

- Prefer **one session per initiative**; start a **new session** on a hard pivot.
- Name sessions on the hub so you can find them later.

### Server vs local-only

| Mode | What you get |
|------|----------------|
| **Server-enabled** | Durable sessions, autosave when APIs are healthy |
| **Local-only draft** | Browser storage if the server or wizard is unavailable — retry when fixed |

## How to verify success

- The mode you picked matches the team’s actual posture.
- Downstream steps do not fight the mission (e.g. “idea” vs “repair”).

## What to do next

- [Wizard 301 — Advanced](11-wizard-301.md)
- [Troubleshooting](12-troubleshooting.md)