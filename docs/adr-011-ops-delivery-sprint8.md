# ADR 011: Ops feedback loop and delivery metrics (Sprint 8)

## Status

Accepted (local-first ops fixture merged with live CI/CD and quality; graph trace for incident → release → work).

## Context

Delivery tooling covered pipelines, security, and release management, but **operational outcomes** (SLOs, incidents, postmortems, error budget, flags) were not folded back into the same traceability spine. Release and program leads need **DORA-style signals** derived from real deploy and incident timestamps, not slides.

## Decision

1. **Package** — **`lenses/ops_delivery/`**: **`feature_flag`** (`LENSES_EXPERIMENTAL_OPS_DELIVERY`, default on), **`local_store`** (`.lenses-local/ops-delivery.json` + **`lenses/fixtures/ops-delivery.demo.json`** via **`LENSES_OPS_DELIVERY_SEED_DEMO=1`**), **`ingest.expand_ingestions`** (PagerDuty / generic incident adapters), **`dora.compute_dora_metrics`**, **`rollback_signals.build_rollback_signals`**, **`postmortem_templates.merged_templates`**, **`aggregate.build_ops_delivery_overview`** (calls **`build_cicd_control_tower_payload`** and optional **`build_quality_overview_payload`**), **`story_evidence.story_ops_delivery_evidence_from_doc`**.
2. **Graph** — Entity kinds **`service`**, **`postmortem`**; edge kinds **`triggered_after`** (incident → release), **`impacts`** (incident → service), **`analyzes`** (postmortem → incident). Demo extended in **`lenses/fixtures/orchestration-graph.demo.json`**. **`lenses/orchestration_graph/ops_trace.py`**: **`story_ops_trace_from_graph`**.
3. **Story hub** — **`forge_spine`** adds **`code_execution.ops_trace`** and **`ops_delivery_evidence`** when flags and data allow.
4. **API** — **`GET /api/ops-delivery/enabled`**, **`GET /api/ops-delivery/overview`**.
5. **Studio** — **Plan → Today**: **`OpsDeliveryCard`**.

## Consequences

- **DORA metrics** are **heuristic** (e.g. lead time = main-branch pipeline finish → prod deploy) but always **sourced** from normalized **`pipeline_runs`** and **`environments[].deployment_history`**, not badges.
- **Change failure rate** uses production incidents in the window with **`classification: change_related`** and a linked release version, over successful prod deploy count.
- **Rollback signals** surface open high-severity production incidents and optional **`health_degradations`** rows with **`suggest_rollback`**.

## Related

- **`lenses/website/http-api-and-routes.md`**
- **`tests/test_ops_delivery.py`**, **`tests/test_ops_trace_graph.py`**
