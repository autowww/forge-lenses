# ADR 007: CI/CD control tower and release orchestration (Sprint 4)

## Status

Accepted (local-first fixtures + graph trace; remote HTTP optional later).

## Context

Delivery views had **pipeline traceability** and **repo workflow** overlays but no single **deployment control layer**: normalized **pipeline runs** and **stage** shapes across CI vendors, an **environment catalog** with promotion / rollback / freeze semantics, or a **story → build → artifact → release → environment** chain for operational traceability.

## Decision

1. **Package** — **`lenses/cicd_orchestration/`**: **`feature_flag`** (`LENSES_EXPERIMENTAL_CICD_ORCHESTRATION`, default on), **`normalized`** control-tower v1 shell, **`local_store`** (`.lenses-local/cicd-orchestration.json` + demo **`lenses/fixtures/cicd-orchestration.demo.json`**), **`aggregate.build_cicd_control_tower_payload`**, **`adapters/`** normalizing **GitHub Actions**, **GitLab CI**, **Azure Pipelines**, **Jenkins**, and **Argo CD**-style payloads to **`pipeline_run`** (+ optional deployment sync metadata).
2. **Graph trace** — **`lenses/orchestration_graph/cicd_trace.py`**: **`story_cicd_trace_from_graph`** walks **`tests`** → **build**, **`contains`** → **artifact**, **`contains`** ← **release**, **`deploys`** → **environment**.
3. **Story hub** — **`forge_spine`** adds **`code_execution.cicd_trace`** when the orchestration graph is enabled and the DB is available.
4. **API** — **`GET /api/cicd/enabled`**, **`GET /api/cicd/control-tower`** (git-extended workspace scan + fixture merge).
5. **Studio** — **Plan → Today**: **`DeliveryControlTowerCard`**; **`WhatChangedSincePrior`** links and a compact posture strip; **Story hub**: build/deploy trace section from **`cicd_trace`**. **Museum** static JSON: **`cicd-enabled.json`**, **`cicd-control-tower.json`**.

## Consequences

- **No outbound network** in Sprint 4 for CI/CD; adapters are contracts + normalizers over fixture JSON.
- **Operational source of truth** for release status is the **local fixture** until importers attach live systems; graph trace requires seeded orchestration entities/edges.

## Related

- **`lenses/website/http-api-and-routes.md`**
- **`tests/test_cicd_orchestration.py`**, **`tests/test_cicd_trace_graph.py`**
