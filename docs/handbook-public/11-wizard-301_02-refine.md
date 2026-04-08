---
nav_title: "Wizard 301: Refine"
public_publish: true
audience: public
product_area: wizard
tier: '301'
handbook_area: wizard
learning_level: '301'
---

# Wizard 301 — Refine

## What it is

Steps like **Understanding** may offer **Refine**: LLM-assisted iteration while you stay in control.

**Parent:** [Wizard 301 — Advanced usage](11-wizard-301.md).

## How to use it

Read output, edit notes, refine again. Paste **constraints** and **non-goals** explicitly.

**Tie-in:** In the **worked example session** on [Wizard 301 — Advanced usage](11-wizard-301.md), Refine almost drops an **SLO** until the team edits notes and runs Refine again — same pattern you should use when the model smooths away facts you need.

## Step-by-step usage (typical)

1. When **Understanding** (or a similar step) offers **Refine**, run it on a **short** paragraph you already agree is directionally right — not on empty text.
2. Read the model output; **edit the notes field** with facts the team insists on (dates, names, boundaries).
3. Refine again only when the delta is worth the cycle; otherwise move forward and fix detail in **Review & generate**.
4. If Refine errors appear, see [Troubleshooting](12-troubleshooting.md) — often policy or local API loopback.

### UI affordances (plain language)

- **Refine** is **assistive**: you remain the editor of record; nothing ships without your **Review** step.
- **Constraints** and **non-goals** belong in your notes so Refine does not “invent” organization policy.

## Recheck loop

After Refine-heavy steps, expect **Recheck / repair** to matter more — see [Review and recheck](11-wizard-301_03-review-recheck.md).

## What to do next

- [Wizard 301 — Advanced usage](11-wizard-301.md)
- [Review and recheck](11-wizard-301_03-review-recheck.md)
