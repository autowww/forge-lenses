# Wizard 201 — Mission modes and scenarios

The first step of the wizard asks you to pick a **mission mode**. The UI presents four options; each maps to a different **posture** so downstream steps (targets, scope, run plan) stay coherent.

## The four modes (with examples)

### Start from idea — “We have a concept, not a shape yet”

**Use when:** Greenfield or early discovery; you are exploring **value** and **constraints** before locking a stack or repo layout.

**Example — CI/CD pipeline visualizer:** You describe pain (opaque pipelines, hard to see failures across repos). Context intake captures existing CI systems; understanding + clarification nail **read-only** vs **trigger** scope. Target pack leans **planning** + **engineering** spikes. Run plan might start with **one pipeline’s** data model before any UI polish.

**Outcome:** A crisp brief, explicit assumptions, and artifacts you can take to a spike or RFC.

### Assess current project — “We have code; we need alignment”

**Use when:** A repository already exists but **Forge / Blueprints** practices are partial or inconsistent.

**Example — Adopt Forge SDLC for an existing Node.js API:** Context intake lists current folders, tests, and deployment. Clarification surfaces gaps (missing `WBS`, unclear charge). Scope selection defines an **adoption wave** (documentation + tracking first, refactors second). Run plan sequences **inventory → minimal WBS → charge updates**.

**Outcome:** A realistic adoption plan that respects legacy risk.

### Resume and advance — “We started; we need the next chapter”

**Use when:** Foundation work happened; you must **move the program** (e.g. from foundation to active delivery, or from MVP to scale).

**Example — Move from foundation to active development:** Mission references prior decisions (link in step notes). Context intake summarizes **what is already shipped**. Target pack adds **execution** and **full_stack** slices if you are cutting releases. Run plan emphasizes **milestones** and **evidence** (Ember / Versona hooks) for governance.

**Outcome:** Updated artifacts and a run plan that **continues** the story instead of re-litigating the beginning.

### Repair stage — “Something drifted or broke down”

**Use when:** Delivery pressure caused **process drift**, inconsistent artifacts, or a **blocked** stage (e.g. releases ad hoc though CI is green).

**Example — CI green but release process ad hoc:** Clarification lists symptoms (no release notes, manual handoffs). Autonomy & mutation defines what can change **this week** vs what needs steering committee. Recheck / repair emphasizes **closing gaps** in charge and roadmap narrative.

**Outcome:** A corrective run plan and recheck summary you can track to closure.

## Hub vs session (again)

- **One session per initiative** is easiest to reason about; clone the narrative in a **new session** if you pivot hard (e.g. from “idea” to “assess” on the same codebase after a spike).
- Name sessions on the hub so you can find **“Retro dashboard — Q2”** vs **“Retro dashboard — security review”**.

## Server mode vs local-only

| Mode | What you get | When it happens |
|------|----------------|-----------------|
| **Server-enabled** | Sessions saved under your workspace, full **PUT** autosave, LLM-backed steps as configured | Default when the wizard APIs respond healthy |
| **Local-only draft** | Browser **sessionStorage** snapshot; no durable server session | Server down, wizard disabled, or probe failure—Studio shows a **Retry** path when possible |

If you see a warning about **local draft only**, fix server/wizard flags and **retry** before relying on exports for governance.

## Next

- [Wizard 301 — Advanced usage](wizard-301-advanced-usage.md)
- [Wizard guides index](index.md)
