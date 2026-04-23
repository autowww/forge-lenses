# Work breakdown structure — forge-lenses (governance PM capabilities)

<!--
  Milestones M1–M5 align with docs/roadmap-project-management.md.
  ID scheme: M{milestone}E{epic}S{story}T{task} (Spark = task).
-->

## 1. Overview

| Field | Detail |
|-------|--------|
| **Product / initiative** | **forge-lenses** — local workspace visualization; Project Management (governance) capability roadmap |
| **Product Spark / Milestone** | M1–M5 — see [Roadmap — PM governance](../roadmap-project-management.md) |
| **Delivery approach** | Phased (NOW → NEXT → LATER per roadmap) |
| **Owner** | Maintainers (TBD) |
| **Date** | 2026-04-11 |
| **Status** | Draft |

**Upstream traceability:** [docs/roadmap-project-management.md](../roadmap-project-management.md) (milestones, themes, Product Versona alignment).

---

## 1a. Sparks and Charge (discipline)

**Rule:** Any story that is **in progress** or **committed for the current increment** must have **Spark-level tasks** (`M*E*S*T*`) in the **Tasks** table below, with `discover:` / `specify:` / `build:` / `verify:` / `release:` phase prefixes where applicable. Backlog stories may omit Sparks until execution starts.

**Charge:** When using Forge execution, list Active Sparks in `forge/charge.md` with Spark IDs matching this WBS so **`/plan`**, **Today**, and **`forge/charge.md`** stay aligned.

---

## 1b. Product Versona checkpoints

Before **baselining** or **re-scoping** epics under M2–M5, run a **Product family** session using the blueprint skill [run-product-versona-session](../../blueprints/sdlc/templates/forge/cursor-skills/run-product-versona-session/SKILL.md): prefer **`versona-family-product`** or **`versona-product-management`**. Follow **§5** structured output in [VERSONA-CONTRACT.md](../../blueprints/sdlc/methodologies/forge/versona/VERSONA-CONTRACT.md).

**Stories requiring §5 before commitment:**

| Story ID | When |
|----------|------|
| **M2E1S1** | Before locking delivery KPI definitions |
| **M3E1S1** | Before locking risk-register design |
| **M4E1S1** | Before locking export scope |
| **M5E1S1** | Before locking demand intake / funnel scope and storage |
| **M5E2S2** | Before locking unified evidence storage and index model |
| **M5E3S1** | Before locking inbox / approvals / notifications architecture |

**Acceptance:** Product Versona session completed; §5 recommendation recorded in `forge-logs/versona/<actor>/<session-id>/` or linked from the story notes. Optional: use [forge/README.template.md](../../blueprints/sdlc/templates/forge/README.template.md) team workflow.

---

## 2. Themes

| Theme ID | Theme | Strategic objective |
|----------|-------|---------------------|
| **T1** | **M1 — PM narrative and IA fit** | Governance PM story is documented; Enterprise IA claims match shipped routes |
| **T2** | **M2 — Monitoring and portfolio signals** | Delivery health beyond git/LoC; portfolio attention backed by spec or API |
| **T3** | **M3 — Control plane (aspirational)** | Risk and baseline/scope decisions documented before build |
| **T4** | **M4 — Reporting and integrations (aspirational)** | Sponsor-ready export spike; integration policy |
| **T5** | **Surface completeness (capture-backed)** | Exposed routes are truthful: working data, honest empty states, or documented deferral—aligned with roadmap gap table |
| **T6** | **M5 — Orchestrator foundations** | Discovery/spec for intake, evidence, workflow, ADR, automation governance, bootstrap, publish, connectors |

---

## 3. WBS hierarchy

### Theme: T1 — M1 (PM narrative and IA fit)

#### Epic: M1E1 — Governance docs

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M1E1S1** | Roadmap + handbook | [roadmap-project-management.md](../roadmap-project-management.md) exists; `python3 generator/build-lenses-docs.py` produces `lenses-docs/roadmap-project-management.html`; linked from [docs/index.md](../index.md) | High | S | — |
| **M1E1S2** | Cross-links valid | Roadmap links to [dashboard-pages](../../lenses/website/dashboard-pages.md), [interface-pages](../../lenses/website/interface-pages.md), [studio-flow-shell-mvp-scope](../studio-flow-shell-mvp-scope.md) resolve from `docs/` | Medium | S | M1E1S1 |

#### Epic: M1E2 — IA honesty

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M1E2S1** | Enterprise gap list | Gap list: Portfolio, Programs, Risk targets in [interface-pages](../../lenses/website/interface-pages.md) vs routes today; recorded in roadmap Notes or short ADR under `docs/` | High | M | M1E1S2 |
| **M1E2S2** | Studio MVP scope clarity | [studio-flow-shell-mvp-scope.md](../studio-flow-shell-mvp-scope.md) deferred items are not claimed as shipped in interface docs | Medium | S | — |

#### Epic: M1E3 — Plan lens

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M1E3S1** | WBS in Lenses | This file appears on `/wbs` and loads in `/plan` with `repo` + `wbs_p` (e.g. `docs/requirements/WBS.md` under forge-lenses child) | High | S | — |
| **M1E3S2** | Charge optional | (Optional) `forge/charge.md` Active Sparks use IDs matching Sparks below | Low | S | M1E3S1 |

### Theme: T5 — Surface completeness (capture-backed)

#### Epic: M1E4 — Dashboards and chart integrity

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M1E4S1** | Overview and project charts reliable | Project Overview presents a coherent operational summary (no raw JSON as primary UX); Strategy and project charts load data or show **documented** empty/error states (no persistent “Failed to load chart data” without tracking link); workspace chart placeholders replaced by working surfaces **or** explicit “not implemented” copy + roadmap link | High | M | M1E2S1 optional |

#### Epic: M1E5 — Delivery domain IA

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M1E5S1** | Delivery distinct from planning/workspace reuse | Delivery routes either implement a **distinct** Delivery reporting/planning surface or intentionally alias another surface with clear nav/labels; route map updated in [dashboard-pages](../../lenses/website/dashboard-pages.md) or ADR | High | M | M1E4S1 |

#### Epic: M1E6 — Plan lens differentiation

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M1E6S1** | Cockpit vs Source Context + WBS viewer | Story Cockpit and Source Context expose **different** primary panels/workflows (not both collapsing to the same planning screen); WBS viewer supports **object-driven** selection (e.g. repo + canonical WBS path) with safe deep links, not raw path input alone | High | M | M1E3S1 |

#### Epic: M1E7 — Boards and search

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M1E7S1** | Board load/editor + search roadmap | Board **probe** route: create → open → edit path works or defect filed with severity; **Search:** documented phase-0 contract (keyword baseline) and **NEXT** criteria for cross-entity / evidence-aware query | High | M | — |

#### Epic: M1E8 — Wizard and tutorials

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M1E8S1** | Wizard and tutorials connected | [Wizard implementation plan](../blueprints/wizard-implementation-plan.md) updated with next provisioning milestone; tutorials entry points resolve to **built** content where the pipeline applies (see [docs/index.md](../index.md) tutorial build); no empty tutorial shell in default capture path | Medium | M | M1E1S1 |

#### Epic: M1E9 — Evidence and identity

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M1E9S1** | Managed evidence (slice) | Workspace markdown / evidence: spike or slice toward **managed** evidence (index, provenance, repo-relative safety)—not file-path loader only; design note under `docs/` | Medium | M | M1E6S1 optional |
| **M1E9S2** | Auth, session, permissions | Read/write posture **documented** per tier; where sign-in is promised, flow is **functional**; “open / legacy” states are explicit in UI or docs | High | M | M1E2S1 |

### Theme: T2 — M2 (Monitoring and portfolio signals)

#### Epic: M2E1 — Delivery KPIs

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M2E1S1** | Metric definitions | Written definitions (e.g. slip, spark throughput, blocked rollup) aligned to roadmap Monitoring theme; **Product Versona §5** before baseline | High | M | M1 complete or explicit overlap |
| **M2E1S2** | Data-source design | Design note: fields from WBS vs Charge vs git vs new API | High | M | M2E1S1 |

#### Epic: M2E2 — Portfolio / attention

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M2E2S1** | Attention / portfolio spec | Spec or tracked issue for workspace attention stream / portfolio strip (shell + data) | High | M | M2E1S2 |

#### Epic: M2E3 — KPI history

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M2E3S1** | KPI history extension | Proposal to extend [kpi_history.py](../../lenses/kpi_history.py) (or successor) for delivery-relevant snapshots | Medium | S | M2E1S1 |

### Theme: T3 — M3 (Control plane — aspirational)

#### Epic: M3E1 — Risk

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M3E1S1** | Risk model design | Design: risk register vs blockers-only; storage (files vs `.lenses-local` vs DB); **Product Versona §5** before baseline | Medium | M | M2 exit agreed |

#### Epic: M3E2 — Baseline / scope

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M3E2S1** | Baseline decision | Decision record: baseline vs current schedule/scope; explicit out-of-scope allowed | Medium | M | M3E1S1 |

### Theme: T4 — M4 (Reporting and integrations — aspirational)

#### Epic: M4E1 — Reporting

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M4E1S1** | Export spike | Spike: Markdown/HTML export path for sponsor summary from workspace + plan; **Product Versona §5** for scope | Medium | M | M3 optional |

#### Epic: M4E2 — Integrations

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M4E2S1** | Integration policy | Policy doc: external SoR sync, privacy, tier gating | Low | S | M4E1S1 optional |

### Theme: T6 — M5 (Orchestrator foundations — discovery/spec)

#### Epic: M5E1 — Intake and requirements governance

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M5E1S1** | Demand intake funnel | Spec: how business/demand items enter Lenses, map to WBS/Charge, and show status; **§5** before baseline | Low | M | M2 exit or overlap agreed |
| **M5E1S2** | Requirements baseline & approval | Spec: baseline vs current requirements, approval/change semantics (file-first vs registry); links to M3 baseline epic | Low | M | M5E1S1 |

#### Epic: M5E2 — Decisions and unified evidence

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M5E2S1** | ADR governance surface | Spec: ADR discovery, linkage to work nodes, search/filter; storage options | Low | M | M5E1S1 optional |
| **M5E2S2** | Unified evidence model | Spec: single evidence index across artifacts; **§5** before storage lock | Low | M | M1E9S1 |

#### Epic: M5E3 — Workflow operator experience

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M5E3S1** | Inbox, approvals, subscriptions, notifications | Spec: operator queue, approval steps, notification channels; privacy/tier; **§5** before architecture lock | Low | M | M5E2S2 optional |

#### Epic: M5E4 — Standards transparency and bootstrap

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M5E4S1** | Score / standards transparency | Spec: user-visible explanation of compliance score (rules fired, deltas); may overlap M2 KPI narrative | Low | S | M2E1S1 optional |
| **M5E4S2** | Blueprint project bootstrap | Spec: blueprint-driven repo/project skeleton from Wizard or CLI; ties to [wizard plan](../blueprints/wizard-implementation-plan.md) | Low | M | M1E8S1 |

#### Epic: M5E5 — Connectors and publish hooks

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|--------------|
| **M5E5S1** | Connector health, lineage, conflicts | Spec: freshness, lineage display, conflict handling for multi-root or external connectors | Low | M | M5E2S2 optional |
| **M5E5S2** | Documentation and release publishing | Spec: tying doc/site publish events to Charge/milestones or delivery events | Low | M | M4E1S1 optional |

---

## 3a. Tasks (Sparks)

Add rows when stories move to **in progress**. Examples for near-term M1 work:

| Task ID | Task | Story | Phase prefix | Estimate (hrs) |
|---------|------|-------|--------------|----------------|
| M1E2S1T1 | Audit interface-pages Enterprise targets vs `/studio/`, `/plan`, `/` routes | M1E2S1 | `discover:` | 2 |
| M1E3S1T1 | Verify `/wbs` lists this file; open `/plan?repo=forge-lenses&wbs_p=docs/requirements/WBS.md` | M1E3S1 | `verify:` | 1 |
| M1E4S1T1 | Reproduce zip capture chart/Overview failures; file defects or fix API binding | M1E4S1 | `discover:` | 2 |
| M1E7S1T1 | Exercise board create → open → edit on probe route; capture gap vs WBS | M1E7S1 | `verify:` | 2 |

When **M2E1S1** starts, add Sparks such as `M2E1S1T1` (draft metric list), `M2E1S1T2` (Product Versona session + §5 capture).

---

## 4. Estimation summary

| Level | Count |
|-------|-------|
| Themes | 6 |
| Epics | 21 |
| Stories | 31 |
| Tasks (Sparks) | 4+ (expand as work starts) |

**Estimation approach:** S ≈ under half a day, M ≈ about one day for a single maintainer.

---

## 5. Dependencies

| # | Dependent item | Depends on | Type | Risk | Mitigation |
|---|----------------|------------|------|------|------------|
| 1 | M1E2S1 | M1E1S2 | Finish-to-Start | Low | Ordered in T1 |
| 2 | M2 themes | M1 narrative stable | Finish-to-Start | Medium | Exit M1 before heavy M2 build |
| 3 | M3 | M2 learnings | Finish-to-Start | Medium | Keep M3 aspirational until demand |
| 4 | M4 export | Privacy/tier strategy | External | High | Policy story M4E2S1 |
| 5 | T5 (M1E4–M1E9) | M1 IA honesty (M1E2) | Finish-to-Start | Medium | Surface truth before portfolio claims |
| 6 | T6 (M5) | T5 stable + M2 signal definitions | Finish-to-Start | High | Orchestrator specs follow honest baselines |

---

## 6. Sequencing and iteration mapping

| Phase | Items included | Focus |
|-------|----------------|-------|
| **NOW** | T1 + T5 (M1E4–M1E9) | PM narrative, IA honesty, charts/boards/auth/tutorials truth |
| **NEXT** | T2 stories | Delivery KPIs, portfolio signals, KPI history proposal |
| **LATER** | T3, T4, T6 | Control plane, reporting, integrations, M5 orchestrator specs |

**Product Versona cadence:** Run sessions at M2E1S1, M3E1S1, M4E1S1, M5E1S1, M5E2S2, M5E3S1 per §1b.

---

## 7. Risks

| # | Risk | Likelihood | Impact | Mitigation | Owner |
|---|------|------------|--------|------------|-------|
| 1 | M2 metrics conflated with git/LoC vanity | Medium | Medium | Explicit definitions in M2E1S1 | Maintainers |
| 2 | File-first Lenses cannot satisfy enterprise PM expectations | Medium | High | Roadmap + IA honesty (M1); tier gating docs | Maintainers |
| 3 | WBS drifts stale | Medium | Low | Quarterly review per roadmap; status table below | Maintainers |
| 4 | Orchestrator (M5) scope swallows M1 surface work | Medium | High | Keep M5 spec-only until T5 exit criteria met; dependency row #6 | Maintainers |

---

## 8. Traceability

| WBS item | Roadmap milestone | Source |
|----------|-------------------|--------|
| T1 | M1 | [roadmap-project-management.md](../roadmap-project-management.md) |
| T2 | M2 | Same — Monitoring + Portfolio rows |
| T3 | M3 | Same — Control plane |
| T4 | M4 | Same — Reporting + Integrations |
| T5 | M1 (surface) | Same — Observed gaps + Surface completeness themes |
| T6 | M5 | Same — Orchestrator foundations |

---

## 9. Status legend

| Status | Meaning |
|--------|---------|
| done | Merged / satisfied |
| in progress | Active |
| not started | Backlog |

| Story ID | Status |
|----------|--------|
| M1E1S1 | done |
| M1E1S2 | not started |
| M1E2S1 | not started |
| M1E2S2 | not started |
| M1E3S1 | not started |
| M1E3S2 | not started |
| M2E1S1 | not started |
| M2E1S2 | not started |
| M2E2S1 | not started |
| M2E3S1 | not started |
| M3E1S1 | not started |
| M3E2S1 | not started |
| M4E1S1 | not started |
| M4E2S1 | not started |
| M1E4S1 | not started |
| M1E5S1 | not started |
| M1E6S1 | not started |
| M1E7S1 | not started |
| M1E8S1 | not started |
| M1E9S1 | not started |
| M1E9S2 | not started |
| M5E1S1 | not started |
| M5E1S2 | not started |
| M5E2S1 | not started |
| M5E2S2 | not started |
| M5E3S1 | not started |
| M5E4S1 | not started |
| M5E4S2 | not started |
| M5E5S1 | not started |
| M5E5S2 | not started |

---

*Last updated: 2026-04-11 · Owner: Maintainers*
