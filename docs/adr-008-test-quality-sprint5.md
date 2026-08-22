# ADR 008: Test management and quality gates (Sprint 5)

## Status

Accepted (local-first fixtures + graph trace; live test systems optional later).

## Context

CI/CD control tower covered **pipelines and promotions**, but releases lacked a governed **quality evidence layer**: normalized **test plans**, **suites**, **cases**, **runs** (manual and automated), **defects**, **coverage**, **flaky** signals, **UAT**, **regression packs**, **readiness checklists**, and **gates** that can block promotion or the release train.

## Decision

1. **Package** — **`lenses/test_quality/`**: **`feature_flag`** (`LENSES_EXPERIMENTAL_TEST_QUALITY`, default on), **`normalized`** overview v1 shell, **`local_store`** (`.lenses-local/test-quality.json` + **`lenses/fixtures/test-quality.demo.json`** via **`LENSES_TEST_QUALITY_SEED_DEMO=1`**), **`gates.evaluate_quality_gates`**, **`gates.quality_gate_promotion_blockers`**, **`gates.build_run_comparisons`**, **`aggregate.build_quality_overview_payload`**, **`aggregate.build_project_quality_payload`**, **`story_evidence.story_quality_evidence_from_doc`**, **`cicd_merge.extend_blocked_promotions_with_quality_gates`**.
2. **CI/CD merge** — **`build_cicd_control_tower_payload`** appends **`blocked_promotions`** with **`reason`** `quality_gate_failed:<gate_id>` when a gate fails and **`applies_to_environments`** includes the promotion target.
3. **Graph** — New entity kinds **`test_plan`**, **`test_suite`**, **`test_case`**, **`defect`**; edge kinds **`validates`**, **`raised_defect`**. Demo bundle extended in **`lenses/fixtures/orchestration-graph.demo.json`**. **`lenses/orchestration_graph/quality_trace.py`**: **`story_quality_trace_from_graph`**.
4. **Story hub** — **`forge_spine`** adds **`code_execution.quality_trace`** and **`quality_evidence`** when flags and data allow.
5. **API** — **`GET /api/quality/enabled`**, **`GET /api/quality/overview`**, **`GET /api/project/<name>/quality`**.
6. **Studio** — **Plan → Today**: **`QualityGatesCard`**; **Pipeline** table adds **Quality (workspace)** column; **Projects / :name**: quality summary beside health stats. **Story hub**: trace + fixture evidence sections.

## Consequences

- **No outbound network** in Sprint 5; importers map vendor test and defect systems into the fixture shapes.
- **Gate rule** types are intentionally small (**`last_suite_run_status`**, **`no_open_defects_min_severity`**, **`coverage_line_minimum`**, **`uat_signoff_required`**) and can grow without breaking the overview shell.

## Related

- **`lenses/website/http-api-and-routes.md`**
- **`tests/test_test_quality.py`**, **`tests/test_quality_trace_graph.py`**
