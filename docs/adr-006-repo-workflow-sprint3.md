# ADR 006: Repo and code workflow integration (Sprint 3)

## Status

Accepted (local-first fixtures + graph links; remote HTTP optional later).

## Context

Planning and delivery UIs had **metadata** (WBS, charge, delivery-signals CI rows) but no shared, provider-agnostic model for **branches, PRs/MRs, reviews, merge readiness, branch protection, and CODEOWNERS**, nor a first-class link from **work items** to **in-repo activity**.

## Decision

1. **Package** — **`lenses/repo_workflow/`**: **`feature_flag`** (`LENSES_EXPERIMENTAL_REPO_WORKFLOW`, default on), **`protocol.RepoWorkflowAdapter`**, **`normalized`** workflow v1 shape and **`compute_health`**, **`adapters/`** for **GitHub**, **GitLab**, and **Azure Repos** (pure **`dict` → `dict`** normalizers for REST-shaped fixtures).
2. **Storage** — **`.lenses-local/repo-workflow.json`** (`repos` map: workspace child name → **`provider`**, **`snapshot`**, optional **`work_item_links`**, **`health_hints`**). Demo: **`lenses/fixtures/repo-workflow.demo.json`** when **`LENSES_REPO_WORKFLOW_SEED_DEMO=1`**.
3. **API** — **`GET /api/repo-workflow/enabled`**, **`GET /api/repo-workflow/overview`**; **`GET /api/project/<name>/repo-workflow`** (RBAC same as stats).
4. **Story hub** — **`build_story_hub_payload`** adds **`code_execution`**: **`graph`** from **`lenses/orchestration_graph/code_links.py`** (`implements`, `contains`, `targets` edges) and **`repo`** from **`get_repo_workflow_row_for_project`** (fixture PR preview + **`project_href`**).
5. **Studio** — **Plan → Today**: **`RepoWorkflowOpsCard`**; **Projects / `:name`**: operational PR table + planning ↔ code links + **Open in Plan**; **Story hub**: code & merge section; **Plan** header: link to project dashboard when **`repo`** scope is set.

## Consequences

- **No outbound network** in Sprint 3; adapters are contracts + normalizers. Importers map vendor APIs into each adapter’s **input** shape.
- **Unlinked work** counts are **hint** fields from fixtures until planning back-links are automated.

## Related

- **`lenses/website/http-api-and-routes.md`**
- **`tests/test_repo_workflow.py`**, **`tests/test_orchestration_code_links.py`**
