---

nav_title: Studio 201
public_publish: true
audience: public
product_area: studio
tier: '201'
handbook_area: studio
learning_level: '201'
section: tutorials-201
status: shipped
description: Studio 201 — Forge Lenses handbook entry (tutorials-201).
page_type: tutorial
---

# Studio 201 — Day-to-day use

## What it is

Using Forge Studio for **regular** work: switching between **workspace lenses** (for example Flow vs Artifacts), moving between **Plans**, **Projects**, and **Knowledge**, and keeping context while you work.

```blueprint-diagram
key: swimlane
alt: Daily operator lane switching Flow and Artifacts lenses without losing project context
caption: Studio 201 assumes you already trust the local loopback surface from 101
```

## When to use it

After [Studio 101](05-studio-101.md), when Studio is your default surface.

## Prerequisites

- Studio loads reliably at **`/studio/`**.

## Flow vs Artifacts (decision guide)

| Lens | Prefer when… | You usually leave with… |
|------|----------------|-------------------------|
| **Flow** | You are tracking delivery steps, handoffs, or “what happens next” | A clear next action on the plan or board |
| **Artifacts** | You need roadmaps, boards, or document-shaped views your build exposes | A stable view of scope and status artifacts |

If you are unsure, start in **Flow** for execution days and **Artifacts** for planning or review meetings.

## Recurring jobs (examples)

| Job | A simple Studio path |
|-----|----------------------|
| Daily stand-in | Workspace → one project → latest plan or board note |
| Prep for refinement | **Artifacts** (if available) → scope slice for the increment |
| Cross-team alignment | Same project in Studio, then confirm the same project in **Classic** at `/` if a report only exists there |

## Do / avoid

| Do | Avoid |
|----|-------|
| Pick **one** project per short session and finish one loop | Switching workspace roots mid-session without reason |
| Name sessions and plans the way your team already searches | Treating chart views as canonical if Classic disagrees |

## Steps

1. **Pick a lens** — Use the workspace lens switcher when present (names vary by build). **Flow** emphasizes delivery flow; **Artifacts** emphasizes roadmaps and boards where your build exposes them.

2. **Stay oriented** — Use the top navigation and project pickers the way your team agrees (same concepts exist in Classic under different chrome).

3. **Typical half-hour** — Open the workspace, drill into **one project**, open **one plan or document** linked from that project, then return to the workspace home. Adjust to your methodology.

4. **Charts and embeds** — Some builds expose chart views under Studio; treat them as **secondary** unless your team standardized on them.

## How to verify success

- You can repeat the path without memorizing URLs or repo paths.
- You know when to switch back to **Classic** at `/` if a flow is not in Studio yet.

## What to do next

- [Studio 301](07-studio-301.md)
- [Wizard 101](09-wizard-101.md)