---
nav_title: Wizard 201
public_publish: true
audience: public
product_area: wizard
tier: '201'
handbook_area: wizard
learning_level: '201'
---

# Wizard 201 — Mission modes

## What it is

The **first wizard step** asks for a **mission mode**. Four options set the **posture** for the rest of the session so targets, scope, and run plan stay coherent.

## When to use it

When you pick **Mission** in a new or resumed session ([Wizard 101](09-wizard-101.md)).

## Prerequisites

- [Wizard 101](09-wizard-101.md) concepts understood.

## Mission modes at a glance

| Mode | Choose it when… | Primary outcome |
|------|-----------------|-----------------|
| **Start from idea** | Discovery is open; problem and constraints are still fuzzy | A crisp brief, explicit assumptions, artifacts for a spike or RFC |
| **Assess current project** | Code exists but Forge / Blueprints practices are uneven | An adoption plan that respects legacy risk |
| **Resume and advance** | Foundation work exists; you need the **next chapter** (for example MVP to scale) | Updated artifacts and a run plan that continues the story |
| **Repair stage** | Process drift, inconsistent artifacts, or a blocked stage | A corrective run plan and recheck you can track to closure |

### Decision prompts (plain language)

Answer these before locking **Mission**; the first row that matches is usually enough:

| Question | If “yes” → |
|----------|------------|
| Are we still proving the problem and value? | **Start from idea** |
| Do we have shipping code but messy process or docs? | **Assess current project** |
| Do we already have a plan and need the *next* increment? | **Resume and advance** |
| Are we stuck, inconsistent, or blocked on a stage? | **Repair stage** |

### Short examples (generic)

| Mode | Starting situation | What “good” looks like after the session |
|------|--------------------|------------------------------------------|
| **Start from idea** | Notes in three tools; no shared brief | One agreed problem statement and a spike-sized next step |
| **Assess current project** | Mixed ADRs and no ceremony rhythm | Adoption plan with owners and a first ceremony to standardize |
| **Resume and advance** | MVP shipped; scale and SRE need a plan | Run plan for the next increment with explicit risks |
| **Repair stage** | Recheck keeps failing on the same gap | Fewer open inconsistencies; recheck passes or gaps are explicitly accepted |

## Steps

### Start from idea

**Use when:** Early discovery; value and constraints are still open.

**Outcome:** A crisp brief, explicit assumptions, artifacts for a spike or RFC.

### Assess current project

**Use when:** Code exists but Forge / Blueprints practices are uneven.

**Outcome:** An adoption plan that respects legacy risk.

### Resume and advance

**Use when:** Foundation work exists; you need the **next chapter** (e.g. MVP to scale).

**Outcome:** Updated artifacts and a run plan that continues the story.

### Repair stage

**Use when:** Process drift, inconsistent artifacts, or a blocked stage.

**Outcome:** A corrective run plan and recheck you can track to closure.

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