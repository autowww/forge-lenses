# Roadmap — Project Management (governance) capabilities (Lenses)

**Purpose:** Maintainer-facing **high-level** plan for **governance Project Management** features in **forge-lenses** — schedule, budget, scope, risk, and resource signals around Markdown-grounded delivery. This is **not** the product-management discovery corpus (vision, market sizing, prioritization frameworks); that lives in the blueprints body of knowledge. This roadmap states **intent** for Lenses-the-product; authoritative story status may later live in a product WBS if one is introduced.

**Discipline context:** [Project Management (Governance)](../blueprints/disciplines/governance/pm/PM-SDLC-PDLC-BRIDGE.md) vs [Product Management](../blueprints/disciplines/product/product-management/PRODUCT-MANAGEMENT.md) — see alignment below.

---

## Alignment with PRODUCT-MANAGEMENT.md

| Blueprint section | Use in this roadmap |
|-------------------|---------------------|
| **§2 Roadmap management** | Horizons labeled **NOW / NEXT / LATER**; hybrid committed vs aspirational; quarterly review; no stale rows without explicit kill or re-scope. |
| **§10 Stakeholder communication** | **Signals** for tooling: executive-style summaries, cross-functional status, risks and asks — informs themes for **reporting** and **portfolio visibility**, not a duplicate of §10 process. |
| **§11 Relationship — Project Management (Governance)** | Scope of features: **how** delivery runs within constraints (schedule, budget, scope, risk, resources), alongside existing Forge plan artifacts (WBS, Charge, roadmap tables). |

**Out of scope here:** Product-management discovery and strategy workstreams from PRODUCT-MANAGEMENT **§§1, 3–9** (vision, RICE/ICE, TAM/SAM/SOM, competitive matrices, pricing, PMF experiments, and so on). Lenses may surface **links** to product docs in a repo, but this roadmap does not plan those practices as product features.

---

## What exists today (baseline)

Lenses ships a **local delivery cockpit skeleton**: workspace and project dashboards, WBS index and paths into **`/plan`**, **Today** (`/api/today-charge`), parsed timeline/roadmap fragments, boards, search, websites preview, Studio shells, and documented Enterprise **targets** (Portfolio, Programs, Risk). Several routes are **exposed but incomplete** relative to the orchestrator vision—see [Observed gaps (capture evidence)](#observed-gaps-capture-evidence) and the [WBS](requirements/WBS.md) **T5** rows for traceable backlog. See [Dashboard pages](../lenses/website/dashboard-pages.md), [Forge plan UI map](../lenses/website/ui-map-workflow.md), and [Studio Flow shell MVP scope](studio-flow-shell-mvp-scope.md).

---

## Observed gaps (capture evidence)

**Evidence:** External **zip capture** of the running product (not hypothetical). Use this table to keep roadmap rows honest and to prioritize **surface completeness** before claiming portfolio/orchestrator maturity.

| Area | Symptom (as seen) | Desired outcome (product) | Horizon |
|------|-------------------|---------------------------|---------|
| **Project Overview** | Loading stats, raw API JSON, no live operational model | Overview reflects a coherent workspace/project model with stable loading and explainable metrics | NOW |
| **Project Strategy / Charts** | “Failed to load chart data” | Charts bind to real APIs or documented empty/error states; no silent permanent failure | NOW → NEXT |
| **Workspace / Delivery charts** | Placeholder loading, not reporting | Same as above; **Delivery** reads as its own reporting domain | NEXT |
| **Delivery IA** | Routes reuse planning/workspace pages | Distinct Delivery experience or explicit “same as plan” with honest nav | NEXT |
| **Story Cockpit vs Source Context** | Collapse to same planning screen | Differentiated workflows and panels per role of each surface | NOW → NEXT |
| **WBS Viewer** | Raw path input only | Object-driven selection (repo, canonical WBS) with safe deep links | NOW → NEXT |
| **Boards** | Create/templates work; load/editor fails on probe | End-to-end open/edit path for a board in the exercised route | NOW |
| **Search** | Flat keyword only | Roadmap toward cross-entity, evidence-aware search (phase 0 = contract + slice) | NEXT |
| **Blueprints Wizard** | Empty shell / session launcher | Progress [implementation plan](blueprints/wizard-implementation-plan.md) toward real provisioning steps | NEXT |
| **Workspace markdown / evidence** | File-path loader | Managed evidence model (index, provenance, not arbitrary paths only) | NEXT → LATER |
| **Tutorials** | Disconnected / empty in capture | Tutorials linked to built content and entry points (see `docs/index.md` tutorial pipeline) | NOW |
| **Auth / session / permissions** | “Not signed in,” open/legacy, read/write unclear | Tier-aware auth story: functional sign-in where promised, documented posture elsewhere | NOW → NEXT |

---

## Orchestrator capability backlog (not yet in UI)

**Scope:** Layers expected for a **best-in-class orchestrator**, largely **absent or implied** today. These are **product-strategy** outcomes; governance PM milestones **M2–M4** stay focused on delivery signals and control. A dedicated milestone **M5** (below) holds discovery/spec Sparks so M1 surface work does not silently subsume multi-quarter platform scope.

| Capability | Outcome | Horizon |
|------------|---------|---------|
| **Demand intake / business request funnel** | Work enters Lenses with intake metadata, triage, and traceability to WBS/Charge | LATER |
| **Requirements baseline & approval workflow** | Baselined scope with explicit approve/change semantics | LATER |
| **Decision records / ADR governance** | ADRs linked to work nodes, searchable, status-aware | LATER |
| **Unified evidence management** | Single evidence index across files, sessions, exports (not path-only) | LATER |
| **Workflow inbox, approvals, subscriptions, notifications** | Operator sees actionable queue; optional subscriptions | LATER |
| **Governed automation / runbooks** | Automation is policy-tagged, auditable, not ad hoc script launch only | LATER |
| **Transparent standards governance (“score”)** | Users can inspect *why* a score changed and which rules fired | NEXT → LATER |
| **Blueprint-based project bootstrapping** | Wizard or flow creates/aligns repo skeleton from blueprint templates | LATER |
| **Documentation / release publishing tied to delivery** | Release or doc publish events correlate to Charge/milestones | LATER |
| **Connector health, freshness, lineage, conflict handling** | External or multi-root connectors show health and conflict UX | LATER |

---

## Milestones

| Milestone | Status | Window | Notes |
|-----------|--------|--------|-------|
| **M1 — PM narrative and IA fit** | In progress | NOW | Document governance PM gaps vs shipped routes; **close T5 surface gaps** where routes are broken or misleading. Keep [Interface pages](../lenses/website/interface-pages.md) Enterprise mapping honest. |
| **M2 — Monitoring and portfolio signals** | Planned | NEXT | Stronger **delivery** health signals (beyond git/LoC): slip, throughput, blocked work rollup; workspace charts that are real reporting surfaces; optional portfolio strip / attention APIs. |
| **M3 — Control plane (risk, baseline, cost)** | Aspirational | LATER | Formal **risk register** or equivalent, scope/baseline story, budget or cost **signals** (even manual/registry-first), change-awareness — only after M2 learnings and demand. |
| **M4 — Reporting and integrations** | Aspirational | LATER | Stakeholder **export** or status pack, optional **external** system-of-record sync (e.g. work trackers); gated on product tier and privacy. |
| **M5 — Orchestrator foundations (discovery/spec)** | Planned | LATER | Spikes and §5-gated specs for intake, evidence unification, workflow, ADR linkage, connectors, and publish hooks—**no UI completeness claim** until M1/M2 stable. |

---

## Epics and themes (by governance area)

Themes are mapped to **NOW / NEXT / LATER** per PRODUCT-MANAGEMENT §2.

### Planning

| Theme | Horizon | Notes |
|-------|---------|-------|
| Timeline and roadmap tables (repo `ROADMAP.md`) integrated with `/plan` and `/timeline` | NOW | Shipped; continue parity (Classic / Studio) and docs. |
| Richer **dependency** and schedule narrative (beyond parsed Gantt tables) | NEXT | Heavier roadmap/WBS conventions or lightweight graph signals. |
| **Critical-path** or cross-milestone scheduling | LATER | Aspirational; may stay out of scope for file-first Lenses. |

### Monitoring

| Theme | Horizon | Notes |
|-------|---------|-------|
| Activity, contributors, standards compliance, optional manual hour bars | NOW | Shipped on Overview / project dashboard. |
| **Delivery** KPIs (cycle time, milestone slip, spark throughput) derived from WBS + Charge + git | NEXT | Distinct from pure engineering hygiene metrics. |
| **KPI history** trends aligned to delivery outcomes | NEXT | Extend append-only snapshots where useful. |

### Control

| Theme | Horizon | Notes |
|-------|---------|-------|
| Blockers in WBS + Charge + Today tab | NOW | Shipped. |
| Dedicated **risk** log (probability/impact) and mitigation owners | LATER | Not the same as task blockers alone. |
| **Baseline vs current** scope/schedule story | LATER | Requires product decision on storage (files vs registry vs DB). |

### Portfolio and programs

| Theme | Horizon | Notes |
|-------|---------|-------|
| Multi-repo Overview and project portal | NOW | Shipped. |
| **Portfolio** health and **programs** spanning repos (Enterprise IA target) | NEXT → LATER | Documentation and shell placeholders first; APIs second. |

### Reporting

| Theme | Horizon | Notes |
|-------|---------|-------|
| Deep links and Today / Plan for status narrative | NOW | Shipped. |
| One-place **summary** for sponsors (export Markdown/HTML/PDF) | LATER | Aligns with §10 communication formats as *signals*, not templates for slide decks. |

### Integrations

| Theme | Horizon | Notes |
|-------|---------|-------|
| File-first Forge artifacts as system of record | NOW | Default posture. |
| Optional sync with external trackers | LATER | High cost; privacy and tier gating. |

### Surface completeness (capture-backed)

| Theme | Horizon | Notes |
|-------|---------|-------|
| Charts and Overview **truthful** (data or explicit empty state) | NOW | Aligns with [Observed gaps](#observed-gaps-capture-evidence); blocks inflated PM claims. |
| Plan lens **differentiation** (cockpit vs source, WBS picker) | NOW → NEXT | User can answer *where am I in the workflow* without duplicate screens. |
| Boards **probe path** reliable | NOW | Creation without load/edit is not shippable for boards narrative. |
| Tutorials and Wizard **connected** to real content / plan milestones | NOW → NEXT | Empty shells erode trust; tie to `build-fa-tutorials.sh` and wizard implementation plan. |
| Auth/RBAC **documented and functional** per tier | NOW → NEXT | Resolves “open / legacy” confusion. |

### Orchestrator depth (M5)

| Theme | Horizon | Notes |
|-------|---------|-------|
| Intake, baseline, ADR, unified evidence, workflow inbox | LATER | WBS **M5** epics; §5 before locking storage and policy. |
| Runbooks, score transparency, blueprint bootstrap, publish + connectors | LATER | Depends on evidence and identity posture from M1/M2. |

---

## NOW / NEXT / LATER (summary)

| Horizon | Themes |
|---------|--------|
| **NOW** | Harden **M1**: PM narrative + **T5** surface truth (Overview, broken charts, boards path, tutorials link-up, auth clarity); **Planning** and **Monitoring** baselines where they are already honest. |
| **NEXT** | **M2**: delivery-oriented metrics, real workspace/Delivery reporting, portfolio/attention signals, Studio/Classic chart parity; **search** and **wizard** tranche toward orchestrator shape. |
| **LATER** | **M3–M4**: control plane and exports; **M5** orchestrator spikes (intake, evidence, workflow, ADR, connectors, publish) — evidence- and tier-gated. |

---

## Relationship to other forge-lenses artifacts

| Artifact | Role |
|----------|------|
| [Dashboard pages](../lenses/website/dashboard-pages.md) | Screen-level behavior for Overview, projects, `/plan`, WBS, boards. |
| [Forge plan UI map](../lenses/website/ui-map-workflow.md) | APIs: `plan-spine`, `story-hub`, `today-charge`, work model. |
| [Interface pages](../lenses/website/interface-pages.md) | Product tiers, Enterprise targets (Portfolio, Programs, Risk), Classic vs Studio. |
| [Studio Flow shell MVP scope](studio-flow-shell-mvp-scope.md) | What the enterprise shell includes vs defers (e.g. full portfolio automation). |

---

## Maintenance

**Review cadence:** At least **quarterly**, or when major plan-lens or Studio milestones ship. **Roadmap hygiene:** Items that do not move for several quarters should be **killed**, **re-scoped**, or moved to **LATER** with explicit rationale (per PRODUCT-MANAGEMENT §2 anti-pattern: feature graveyard). **Authoritative backlog:** [docs/requirements/WBS.md](requirements/WBS.md) for Lenses governance PM delivery (milestones M1–M4); sync story status there when themes shift — same discipline as [Blueprints ROADMAP](../blueprints/docs/ROADMAP.md) and its WBS.

---

## Related reading

| Doc | Why |
|-----|-----|
| [PRODUCT-MANAGEMENT.md](../blueprints/disciplines/product/product-management/PRODUCT-MANAGEMENT.md) | Product vs governance PM boundary (§11); roadmap and communication discipline (§2, §10). |
| [PM-SDLC-PDLC-BRIDGE.md](../blueprints/disciplines/governance/pm/PM-SDLC-PDLC-BRIDGE.md) | How governance PM relates to SDLC/PDLC. |
| [PM.md](../blueprints/disciplines/governance/pm/PM.md) | Generic PM roles and process groups (reference). |
