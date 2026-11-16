# ADR-019 — PDLC outcome bridge: launch → learning → demand (Sprint B6)

## Status

Accepted — implemented in forge-lenses.

## Context

Delivery-focused views (CI/CD, PRs, releases) stopped short of **product outcomes**: adoption, support load, retention, experiments, and customer feedback were not first-class orchestration objects linked back to **releases**, **work**, and **new Ore**. “Lessons learned” risked living outside the planning spine.

## Decision

1. **Graph entity kinds** — Add **`launch_record`**, **`outcome_signal`**, **`metric_snapshot`**, **`experiment_result`**, **`customer_feedback_ref`**, **`support_signal`**, **`adoption_signal`**, **`retention_signal`**, **`satisfaction_signal`**, **`revenue_proxy_signal`**, **`learning_summary`**, **`followon_ore_candidate`** (reuse existing **`demand_signal`** for bridged demand).
2. **Edges** — **`launch_for`** (launch → release), **`outcome_observed`** (signal or snapshot → launch), **`proposes_followon`** (learning_summary → followon_ore_candidate), **`bridges_to_demand`** (followon → demand_signal). Reuse **`aggregates`**, **`references`**, **`originates_from`** for evidence and objective linkage.
3. **Registry** — **`lenses/bridge/data/pdlc_outcome_bridge_registry.json`**: neutral → PDLC / Forge **labels**, expected signal categories for completeness heuristics, and **follow-on generation rule** metadata (explainable, not ML).
4. **Scoring** — **`explain_scores_for_launch`** returns **launch_confidence**, **evidence_completeness**, **signal_freshness_notes**, **outcome_ambiguity**, **followon_demand** counts, plus a human-readable **`explanations`** list (transparent heuristics).
5. **APIs** — **`GET/POST /api/outcomes*`**, **`GET/POST /api/launches*`**, **`GET /api/pdlc/bridge/<id>`** as documented in **`lenses/website/http-api-and-routes.md`**. Feature flag **`LENSES_EXPERIMENTAL_OUTCOME_BRIDGE_B6`** (default on when the orchestration graph is on).
6. **Migration v8** — Partial index on **`ogs_entity(kind, updated_at)`** for outcome-related kinds.
7. **UI** — **`OutcomeLoopPanel`** on Studio **Plan**, **Today**, and **project** dashboard; **`outcome_loop`** on **`/api/story-hub`**; **Knowledge / Evidence registry** hint when B6 is enabled.
8. **Demo** — **`orchestration-graph.demo.json`** adds a **launch_record** for **v1.4.0**, multiple **signals**, **`learning_summary`** aggregating them and referencing a **review_pack**, **`followon_ore_candidate`**, **`demand_signal`** with **originates_from** objective and **references** story **S-1842**.

## Consequences

- **Positive** — Closed loop **plan → ship → observe → learn → Ore** is traceable in one graph; follow-on demand is not orphaned from the originating launch.
- **Negative** — No **analytics warehouse** or BI dashboards; signals are **structured graph rows** plus optional external refs in payload.
- **Follow-up** — Adapters for product analytics / support tools; richer **prioritization** scoring; optional automation from rules in registry.

## Deferred / non-goals

- Full **data warehouse** or **custom BI** (explicitly out of scope).
- Opaque **ML** scoring — heuristics must stay **explainable** in API responses.
