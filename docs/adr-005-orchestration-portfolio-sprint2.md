# ADR 005: Orchestration portfolio planning (Sprint 2)

## Status

Accepted (extends ADR 004).

## Context

ADR 004 introduced the canonical SQLite graph and trace APIs. Planning screens (plan spine, roadmap matrix, timeline) still treated portfolio questions—scenarios, cross-item dependencies, capacity placeholders, and readiness versus the graph—as separate concerns.

## Decision

1. **Schema v2** — Additional indexes on **`ogs_edge`** (`kind`, `to_id`) and (`kind`, `from_id`) for portfolio queries (`lenses/orchestration_graph/migrate.py`, **`_LATEST` = 2**).
2. **Kinds and edges** — Entity kinds **`scenario`**, **`workstream`**. Edge kinds **`depends_on`** (from blocked until to completes), **`allocated_to`** (story or work item → workstream).
3. **Python module** — **`lenses/orchestration_graph/portfolio.py`**: dependency pressure, critical path on **`depends_on`**, graph completeness score, scenario comparison, workstream capacity placeholders, milestone/matrix enrichment, timeline and matrix overlays, **`plan_spine_orchestration_summary`** for the plan-spine API.
4. **HTTP** — **`GET /api/orchestration/portfolio-context`** (query: **`scenario_a`**, **`scenario_b`**, **`slip_focus`**). Existing **`GET /api/plan-spine`**, **`GET /api/roadmaps-matrix`**, and **`GET /api/timeline-context`** gain optional graph-backed fields when **`LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH`** is on and the DB is available.
5. **Studio** — Plan cockpit: **`PortfolioPlanningPanel`**, graph-aware **`PlanReadiness`**, URL params **`scenario_a`** / **`scenario_b`**. Matrix and timeline: **`GraphPortfolioSummary`** reading **`orchestration_portfolio`**.
6. **Demo fixture** — **`lenses/fixtures/orchestration-graph.demo.json`** includes baseline/stretch scenarios, **`depends_on`** between demo stories, **`allocated_to`** into workstreams, and optional **`duration_days`** on stories for critical-path demos.

## Consequences

- Slip / “what blocks” traversal semantics remain subject to refinement; the UI labels chain-style **`depends_on`** effects for the selected focus entity.
- Consumers should treat **`orchestration`** / **`orchestration_portfolio`** as optional keys when the feature flag or DB is absent.

## Related

- ADR 004: **`docs/adr-004-canonical-orchestration-graph.md`**
- HTTP: **`lenses/website/http-api-and-routes.md`**
- Tests: **`tests/test_portfolio_planning.py`**, **`tests/test_orchestration_graph.py`**
