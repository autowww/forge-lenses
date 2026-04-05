# Work breakdown structure — forge-lenses (governance PM capabilities)

<!--
  Milestones M1–M4 align with docs/roadmap-project-management.md.
  ID scheme: M{milestone}E{epic}S{story}T{task} (Spark = task).
-->

## 1. Overview

| Field | Detail |
|-------|--------|
| **Product / initiative** | **forge-lenses** — local workspace visualization; Project Management (governance) capability roadmap |
| **Product Spark / Milestone** | M1–M4 — see [Roadmap — PM governance](../roadmap-project-management.md) |
| **Delivery approach** | Phased (NOW → NEXT → LATER per roadmap) |
| **Owner** | Maintainers (TBD) |
| **Date** | 2026-04-02 |
| **Status** | Draft |

**Upstream traceability:** [docs/roadmap-project-management.md](../roadmap-project-management.md) (milestones, themes, Product Versona alignment).

---

## 1a. Sparks and Charge (discipline)

**Rule:** Any story that is **in progress** or **committed for the current increment** must have **Spark-level tasks** (`M*E*S*T*`) in the **Tasks** table below, with `discover:` / `specify:` / `build:` / `verify:` / `release:` phase prefixes where applicable. Backlog stories may omit Sparks until execution starts.

**Charge:** When using Forge execution, list Active Sparks in `forge/charge.md` with Spark IDs matching this WBS so **`/plan`**, **Today**, and **`forge/charge.md`** stay aligned.

---

## 1b. Product Versona checkpoints

Before **baselining** or **re-scoping** epics under M2–M4, run a **Product family** session using the blueprint skill [run-product-versona-session](../../blueprints/sdlc/templates/forge/cursor-skills/run-product-versona-session/SKILL.md): prefer **`versona-family-product`** or **`versona-product-management`**. Follow **§5** structured output in [VERSONA-CONTRACT.md](../../blueprints/sdlc/methodologies/forge/versona/VERSONA-CONTRACT.md).

**Stories requiring §5 before commitment:**

| Story ID | When |
|----------|------|
| **M2E1S1** | Before locking delivery KPI definitions |
| **M3E1S1** | Before locking risk-register design |
| **M4E1S1** | Before locking export scope |

**Acceptance:** Product Versona session completed; §5 recommendation recorded in `forge-logs/versona/<actor>/<session-id>/` or linked from the story notes. Optional: use [forge/README.template.md](../../blueprints/sdlc/templates/forge/README.template.md) team workflow.

---

## 2. Themes

| Theme ID | Theme | Strategic objective |
|----------|-------|---------------------|
| **T1** | **M1 — PM narrative and IA fit** | Governance PM story is documented; Enterprise IA claims match shipped routes |
| **T2** | **M2 — Monitoring and portfolio signals** | Delivery health beyond git/LoC; portfolio attention backed by spec or API |
| **T3** | **M3 — Control plane (aspirational)** | Risk and baseline/scope decisions documented before build |
| **T4** | **M4 — Reporting and integrations (aspirational)** | Sponsor-ready export spike; integration policy |

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

---

## 3a. Tasks (Sparks)

Add rows when stories move to **in progress**. Examples for near-term M1 work:

| Task ID | Task | Story | Phase prefix | Estimate (hrs) |
|---------|------|-------|--------------|----------------|
| M1E2S1T1 | Audit interface-pages Enterprise targets vs `/studio/`, `/plan`, `/` routes | M1E2S1 | `discover:` | 2 |
| M1E3S1T1 | Verify `/wbs` lists this file; open `/plan?repo=forge-lenses&wbs_p=docs/requirements/WBS.md` | M1E3S1 | `verify:` | 1 |

When **M2E1S1** starts, add Sparks such as `M2E1S1T1` (draft metric list), `M2E1S1T2` (Product Versona session + §5 capture).

---

## 4. Estimation summary

| Level | Count |
|-------|-------|
| Themes | 4 |
| Epics | 10 |
| Stories | 14 |
| Tasks (Sparks) | 2+ (expand as work starts) |

**Estimation approach:** S ≈ under half a day, M ≈ about one day for a single maintainer.

---

## 5. Dependencies

| # | Dependent item | Depends on | Type | Risk | Mitigation |
|---|----------------|------------|------|------|------------|
| 1 | M1E2S1 | M1E1S2 | Finish-to-Start | Low | Ordered in T1 |
| 2 | M2 themes | M1 narrative stable | Finish-to-Start | Medium | Exit M1 before heavy M2 build |
| 3 | M3 | M2 learnings | Finish-to-Start | Medium | Keep M3 aspirational until demand |
| 4 | M4 export | Privacy/tier strategy | External | High | Policy story M4E2S1 |

---

## 6. Sequencing and iteration mapping

| Phase | Items included | Focus |
|-------|----------------|-------|
| **NOW** | T1 stories | PM narrative, IA honesty, this WBS visible in `/plan` |
| **NEXT** | T2 stories | Delivery KPIs, portfolio signals, KPI history proposal |
| **LATER** | T3, T4 | Control plane, reporting, integrations |

**Product Versona cadence:** Run sessions at M2E1S1, M3E1S1, M4E1S1 per §1b.

---

## 7. Risks

| # | Risk | Likelihood | Impact | Mitigation | Owner |
|---|------|------------|--------|------------|-------|
| 1 | M2 metrics conflated with git/LoC vanity | Medium | Medium | Explicit definitions in M2E1S1 | Maintainers |
| 2 | File-first Lenses cannot satisfy enterprise PM expectations | Medium | High | Roadmap + IA honesty (M1); tier gating docs | Maintainers |
| 3 | WBS drifts stale | Medium | Low | Quarterly review per roadmap; status table below | Maintainers |

---

## 8. Traceability

| WBS item | Roadmap milestone | Source |
|----------|-------------------|--------|
| T1 | M1 | [roadmap-project-management.md](../roadmap-project-management.md) |
| T2 | M2 | Same — Monitoring + Portfolio rows |
| T3 | M3 | Same — Control plane |
| T4 | M4 | Same — Reporting + Integrations |

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

---

*Last updated: 2026-04-02 · Owner: Maintainers*
