# Wizard 101 — Getting started

This page is for your **first** run through the Blueprints Wizard: what it is, where to click, what the **twelve steps** are for, and one **worked example** using **Start from idea**.

## What is the Blueprints Wizard?

It is a **guided shell inside Forge Studio** that walks from **mission** through **contribution setup**, **context**, **understanding**, **clarification**, **targets and outputs**, **autonomy and change**, **scope**, **run plan**, **review and generate**, **recheck / repair**, and **experimental build** (including **Cursor Launch Pack** export). It is **aligned with Blueprints methodology** concepts but does **not** automatically change files in your `blueprints/` submodule—you stay in control of commits.

Use it when you want a **repeatable workshop** for a new initiative, a **sanity pass** on an existing repo, or a **structured handoff** to engineering and Cursor.

## Open the wizard

1. Start Lenses and open Forge Studio: **`http://127.0.0.1:<port>/studio/`** (or your configured host).
2. In the sidebar, open **Blueprints Wizard (experimental)** (wording may vary slightly by build).
3. You land on the **Hub**: **`/studio/blueprints/wizard`**. From here you **create a session** or resume one.

## Hub vs session

| Place | URL pattern | Purpose |
|-------|-------------|---------|
| **Hub** | `/studio/blueprints/wizard` | List sessions, create a **new session**, see last step and updated time |
| **Session** | `/studio/blueprints/wizard/session/<sessionId>` | Full wizard: stepper, notes, saves, exports |

Create a **new session** when you start a new thread of work; open an **existing session** to continue.

## The twelve steps (user-facing)

The UI shows short titles in a stepper. In order:

1. **Mission** — Choose **why** you are here (see Wizard 201 for the four mission modes) and capture the headline intent.
2. **Contribution Setup** — How this work fits contributors, repos, and expectations (roles, constraints).
3. **Context Intake** — What is already true: product, stack, team, deadlines.
4. **Understanding** — Synthesize a shared picture; often pairs with **Refine** to improve a foundation-style brief.
5. **Clarification** — Resolve ambiguities and explicit assumptions before you commit to a plan.
6. **Target & Output Pack** — What “done” looks like and which **artifact bundles** you need (introduced in detail in Wizard 301).
7. **Autonomy & Mutation** — How much change is allowed, and what must stay stable (governance, blast radius).
8. **Scope Selection** — Cut line for this increment vs later.
9. **Run Plan** — Ordered steps, owners, and checks to execute.
10. **Review & Generate** — Inspect generated **artifacts** (planning, engineering, execution, or broader packs depending on your choices).
11. **Recheck / Repair** — Validate consistency; optionally refresh checks after edits.
12. **Experimental Build** — Package a **Cursor Launch Pack** (and related exports) so you can continue in the IDE with context.

You can move in the shell step by step; your **session** remembers position and notes when the server is available.

## Worked example — “Start from idea”

**Scenario:** You want a small internal tool: **a team retrospective dashboard** that pulls action items from the last few sprints and shows trends.

1. **Hub** — **New session**. Pick a name you will recognize later (e.g. “Retro dashboard — Q2”).
2. **Mission** — Select **Start from idea** (maps to an exploratory posture—see Wizard 201). In free text, state the problem: scattered retro notes, no visibility on follow-through.
3. **Contribution Setup** — Note that one repo will hold the app, and that design + eng will pair weekly.
4. **Context Intake** — List stack preferences (e.g. existing org standard: TypeScript, existing auth). Note “must integrate with Slack or GitHub issues” if that is a constraint.
5. **Understanding** — Use **Refine** if offered: turn bullets into a short **foundation brief** with goals and non-goals.
6. **Clarification** — Answer open questions: single team vs multi-team, hosting region, PII boundaries.
7. **Target & Output Pack** — Choose bundles that match this stage—often **planning** + early **engineering** sketches first (Wizard 301).
8. **Autonomy & Mutation** — Mark whether prototypes may introduce new dependencies or must stay inside an approved template.
9. **Scope Selection** — Example: **MVP** = read-only dashboard + manual CSV import; **out of scope** = automated Jira sync.
10. **Run Plan** — Sequence: spike UI mock → define API contract → vertical slice → hardening.
11. **Review & Generate** — Read generated Markdown and checklists; adjust notes and regenerate if needed.
12. **Recheck / Repair** — Run the recheck step; fix gaps called out in the summary.
13. **Experimental Build** — Export a **Cursor Launch Pack** so your repo can start with the same structure and prompts.

**What you leave with:** A persisted session (on disk under your workspace when server mode works), **generated artifacts**, optional **Markdown** export paths depending on your build, and a **launch pack** you can open in Cursor to continue implementation.

## When to use the wizard vs manual Blueprints

| Use the wizard | Prefer manual Blueprints / docs |
|----------------|----------------------------------|
| You want a **facilitated** pass with prompts and artifact bundles | You are only **tweaking** existing `blueprints/` or SDLC files |
| Several people need a **shared narrative** before branching | You already have **ROADMAP / WBS / charge** in good shape |
| You are **bootstrapping** a new repo or initiative | You rely on **custom automation** outside Lenses |

## Next

- [Wizard 201 — Mission modes and scenarios](wizard-201-mission-modes.md)
- [Wizard guides index](index.md)
