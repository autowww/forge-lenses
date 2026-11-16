---

nav_title: Choose Wizard artifact bundles for planning, engineering, or execution
public_publish: true
audience: public
product_area: wizard
tier: '301'
handbook_area: wizard
learning_level: '301'
section: tutorials-301
status: experimental
description: Choose Wizard artifact bundles for planning, engineering, or execution
  — Forge Lenses handbook entry (tutorials-301).
page_type: tutorial
---

# Choose Wizard artifact bundles for planning, engineering, or execution

## What it is

How **Target & output pack** emphasizes planning, engineering, execution, or full-stack slices (labels vary by build).

**Parent:** [Wizard 301 — Advanced usage](11-wizard-301.md).

## Emphasis matrix

| Emphasis (labels vary by build) | Best when you need… |
|----------------------------------|---------------------|
| **Planning** | Roadmaps, milestones, decision log |
| **Engineering** | Tasks, risks, technical guardrails |
| **Execution** | Near-term steps and owners |
| **Full stack** | End-to-end slice across roles |

Treat emphasis as **what the generator highlights**, not as automatic commits to your repo.

**Tie-in:** The **worked example session** on [Wizard 301 — Advanced usage](11-wizard-301.md) starts with choosing the **Engineering** bundle for an API reliability initiative — see that story for how emphasis connects to Refine and Recheck.

## Step-by-step usage (typical)

1. Reach **Target & output pack** in the stepper after you have a shared picture in earlier steps ([Wizard 101](09-wizard-101.md) order).
2. Choose an emphasis that matches the **decision or handoff** you need (planning vs engineering vs execution vs full stack). Labels in the UI may vary by build.
3. Scan the generated outline: if the wrong slice is highlighted, adjust emphasis and regenerate rather than editing only surface text.
4. Proceed to **Review & generate**, then **Recheck** ([Review and recheck](11-wizard-301_03-review-recheck.md)) before you export.

### UI affordances (plain language)

- **Emphasis** controls what the session **foregrounds** in artifacts — it does not replace your repo’s branching or CI.
- If your build shows **pack** or **bundle** wording, treat it as the same idea: **what this session optimizes for**.

## Verify

The generated outline foregrounds the **emphasis** you chose (planning, engineering, execution, or full stack). If the wrong slice dominates, change emphasis and regenerate before **Review & generate**.

## What to do next

- [Wizard 301 — Advanced usage](11-wizard-301.md)
- [Refine](11-wizard-301_02-refine.md)