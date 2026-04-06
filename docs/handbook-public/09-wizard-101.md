---
nav_title: Wizard 101
public_publish: true
audience: public
product_area: wizard
tier: "101"
---

# Wizard 101 — First session

## What it is

Your **first** run through the Blueprints Wizard: open the hub, create a session, understand the **twelve steps**, and complete one short **worked example**.

## When to use it

After [Wizard overview](08-wizard-overview.md) and [Studio 101](05-studio-101.md).

## Prerequisites

- Wizard enabled ([Wizard overview](08-wizard-overview.md)).
- Browser on **`/studio/`**.

## Steps

### Open the wizard

1. Start Lenses and open **`/studio/`**.
2. In the sidebar, choose **Blueprints Wizard** (wording may vary).
3. Land on the **Hub** — create a **new session** or resume one.

### Hub vs session

| Place | URL pattern | Purpose |
|-------|-------------|---------|
| **Hub** | `/studio/blueprints/wizard` | List sessions, create new, see last step |
| **Session** | `/studio/blueprints/wizard/session/<sessionId>` | Full stepper, notes, saves, exports |

### The twelve steps (what you see in the UI)

1. **Mission** — Why you are here (see [Wizard 201](10-wizard-201.md) for modes).
2. **Contribution setup** — Roles, repos, expectations.
3. **Context intake** — What is already true.
4. **Understanding** — Shared picture; **Refine** may appear.
5. **Clarification** — Resolve ambiguities.
6. **Target & output pack** — Done shape and artifact bundles ([Wizard 301](11-wizard-301.md)).
7. **Autonomy & mutation** — Allowed change vs stability.
8. **Scope selection** — This increment vs later.
9. **Run plan** — Ordered steps and checks.
10. **Review & generate** — Inspect generated artifacts.
11. **Recheck / repair** — Consistency checks.
12. **Experimental build** — **Cursor Launch Pack** and related exports.

### Worked example — “Start from idea”

**Scenario:** A small internal tool — a **team retrospective dashboard** (action items and trends).

1. **Hub** — New session; name it (e.g. “Retro dashboard — Q2”).
2. **Mission** — **Start from idea**; describe scattered retro notes and lack of follow-through visibility.
3. Continue through steps with short, honest notes; use **Refine** where offered.
4. **Experimental build** — Export a **Cursor Launch Pack** if your build offers it.

## How to verify success

- Session persists when the server supports it (otherwise you may see a **local draft** warning — see [Troubleshooting](12-troubleshooting.md)).
- You finish with generated artifacts or exports you can take to engineering.

## What to do next

- [Wizard 201 — Mission modes](10-wizard-201.md)
- [Wizard 301 — Advanced](11-wizard-301.md)
