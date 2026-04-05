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

Lenses already provides a **local delivery cockpit**: workspace and project dashboards, WBS index and viewer, **Forge plan** (`/plan`) with work tree and story cockpit, **Today** (`/api/today-charge`), timeline and roadmap fragments from `ROADMAP.md`, sticker boards, search, websites preview, optional team RBAC, and Lenses Studio shells with documented Enterprise **targets** (Portfolio, Programs, Risk). See [Dashboard pages](../lenses/website/dashboard-pages.md), [Forge plan UI map](../lenses/website/ui-map-workflow.md), and [Studio Flow shell MVP scope](studio-flow-shell-mvp-scope.md).

---

## Milestones

| Milestone | Status | Window | Notes |
|-----------|--------|--------|-------|
| **M1 — PM narrative and IA fit** | In progress | NOW | Document governance PM gaps vs shipped routes; keep [Interface pages](../lenses/website/interface-pages.md) Enterprise mapping honest (documentation-first where APIs are missing). |
| **M2 — Monitoring and portfolio signals** | Planned | NEXT | Stronger **delivery** health signals (beyond git/LoC): slip, throughput, blocked work rollup; optional workspace-level portfolio strip / attention items backed by existing or new APIs. |
| **M3 — Control plane (risk, baseline, cost)** | Aspirational | LATER | Formal **risk register** or equivalent, scope/baseline story, budget or cost **signals** (even manual/registry-first), change-awareness — only after M2 learnings and demand. |
| **M4 — Reporting and integrations** | Aspirational | LATER | Stakeholder **export** or status pack, optional **external** system-of-record sync (e.g. work trackers); gated on product tier and privacy. |

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

---

## NOW / NEXT / LATER (summary)

| Horizon | Themes |
|---------|--------|
| **NOW** | Harden **M1**: clarity on PM governance scope; ship and document **Planning** and **Monitoring** baselines (plan lens, Today, dashboards, boards, Studio shell MVP). |
| **NEXT** | **M2**: delivery-oriented metrics, portfolio/attention signals, Studio/Classic parity for chart and plan surfaces; start **Control** prototypes if backlog allows. |
| **LATER** | **M3–M4**: risk/baseline/cost **signals**, stakeholder exports, integrations — only with evidence and tier strategy. |

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
