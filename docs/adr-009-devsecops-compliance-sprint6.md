# ADR 009: DevSecOps and compliance orchestration (Sprint 6)

## Status

Accepted (local-first fixtures + graph trace + policy merge into CI/CD; live scanners optional later).

## Context

Quality gates and CI/CD promotions covered tests and pipelines, but **security and compliance** were not first-class workflow objects: findings, exceptions, SBOM, provenance, and controls were invisible next to the release train, and risk was not derived from normalized evidence.

## Decision

1. **Package** — **`lenses/devsecops_compliance/`**: **`feature_flag`** (`LENSES_EXPERIMENTAL_DEVSECOPS_COMPLIANCE`, default on), **`normalized`** overview shell, **`local_store`** (`.lenses-local/devsecops-compliance.json` + **`lenses/fixtures/devsecops-compliance.demo.json`** via **`LENSES_DEVSECOPS_COMPLIANCE_SEED_DEMO=1`**), **`ingest.expand_ingestions`** and **`adapters/`** (code, dependency, secret, container/IaC, SBOM/provenance), **`rollups.build_rollups`**, **`risk_engine.compute_risk_score`**, **`policy_engine.evaluate_security_policy_checks`** / **`security_policy_promotion_blockers`**, **`aggregate.build_devsecops_overview_payload`** / **`build_project_devsecops_payload`**, **`story_evidence.story_devsecops_evidence_from_doc`**, **`cicd_integration.merge_devsecops_into_control_tower_payload`**.
2. **CI/CD merge** — Control tower payload gains **`security_release_gate`**; **`blocked_promotions`** may include **`reason`** `security_policy_failed:<policy_id>` when a blocking policy fails.
3. **Graph** — Entity kinds **`security_finding`**, **`compliance_exception`**, **`control`**; edges **`affects`**, **`accepted_risk_for`**, **`satisfies`**. Demo in **`lenses/fixtures/orchestration-graph.demo.json`**. **`lenses/orchestration_graph/security_trace.py`**: **`story_security_trace_from_graph`**.
4. **Story hub** — **`forge_spine`** adds **`code_execution.security_trace`** and **`devsecops_evidence`** when flags and data allow.
5. **API** — **`GET /api/devsecops/enabled`**, **`GET /api/devsecops/overview`**, **`GET /api/project/<name>/devsecops`**.
6. **Studio** — **Plan → Today**: **`DevSecOpsCard`**, **Delivery control tower**: security/compliance gate panel; **Projects / :name**: security summary beside quality. **Story hub**: security trace + fixture evidence sections.

## Consequences

- **Risk score** is computed from open findings, vulns, secrets, and dependency rows, minus control mitigation, with **exceptions** excluding covered finding ids — not a static badge.
- **Exceptions** carry **owner**, **expiration**, and **`audit_trail`** in the canonical doc shape; policy decisions reference them.
- **No outbound network** in Sprint 6; adapters normalize vendor JSON into the shared schema.

## Related

- **`lenses/website/http-api-and-routes.md`**
- **`tests/test_devsecops_compliance.py`**, **`tests/test_security_trace_graph.py`**
