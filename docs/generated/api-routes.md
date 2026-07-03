---
audience: public
section: builders
learning_level: reference
product_area: lenses
status: shipped
tier: builder
handbook_area: builders
public_publish: true
description: Machine-generated inventory of HTTP routes parsed from lenses/serve.py.
nav_title: HTTP API route catalog
---

# HTTP API route inventory

Auto-generated from `lenses/serve.py` via `generator/collect_lenses_api_routes.py`. Do not edit by hand — run `python3 generator/export_api_routes_docs.py`.

See also [Builders — route families](../handbook-public/builders-route-families.md), [Schemas and API (builders)](../handbook-public/16-schemas-and-api-for-builders.md), and historical maintainer narrative on GitHub: [lenses/website/http-api-and-routes.md](https://github.com/autowww/forge-lenses/blob/main/lenses/website/http-api-and-routes.md).

## Full catalog

| Method | Family | Audience | Signature |
|--------|--------|----------|-----------|
| GET | `/api/access` | general | `/api/access/policy` |
| GET | `/api/auth` | auth | `/api/auth/loopback-dev-login` |
| GET | `/api/auth` | auth | `/api/auth/oidc/callback` |
| GET | `/api/auth` | auth | `/api/auth/oidc/login` |
| GET | `/api/auth` | auth | `/api/auth/oidc/status` |
| GET | `/api/auth` | auth | `/api/auth/status` |
| GET | `/api/autonomy-maturity` | general | `/api/autonomy-maturity/enabled` |
| GET | `/api/autonomy-maturity` | general | `/api/autonomy-maturity/overview` |
| GET | `/api/blueprints` | wizard | `/api/blueprints/wizard/enabled` |
| GET | `/api/blueprints` | wizard | `/api/blueprints/wizard/sessions` |
| GET | `/api/chart-data` | general | `/api/chart-data/overview` |
| GET | `/api/cicd` | general | `/api/cicd/control-tower` |
| GET | `/api/cicd` | general | `/api/cicd/enabled` |
| GET | `/api/connectors` | general | `/api/connectors/health` |
| GET | `/api/cross-team-release` | general | `/api/cross-team-release/enabled` |
| GET | `/api/cross-team-release` | general | `/api/cross-team-release/overview` |
| GET | `/api/delivery` | general | `/api/delivery/enabled` |
| GET | `/api/delivery` | general | `/api/delivery/overview` |
| GET | `/api/devsecops` | general | `/api/devsecops/enabled` |
| GET | `/api/devsecops` | general | `/api/devsecops/overview` |
| GET | `/api/doc-hydration` | general | `/api/doc-hydration/review-packs` |
| GET | `/api/docs-health` | docs-health | `/api/docs-health/live-sessions` |
| GET | `/api/docs-health` | docs-health | `/api/docs-health/summary` |
| GET | `/api/docs-health` | docs-health | `/api/docs-health/work-items` |
| GET | `/api/fleet` | general | `/api/fleet/settings` |
| GET | `/api/forge-work-model` | general | `/api/forge-work-model` |
| GET | `/api/forgesdlc-blog` | general | `/api/forgesdlc-blog` |
| GET | `/api/forgesdlc-blog` | general | `/api/forgesdlc-blog/content` |
| GET | `/api/governance` | general | `/api/governance/audit` |
| GET | `/api/governance` | general | `/api/governance/scopes` |
| GET | `/api/llm` | general | `/api/llm/diagnostics` |
| GET | `/api/llm` | general | `/api/llm/model-catalog-notifications` |
| GET | `/api/llm` | general | `/api/llm/ollama-status` |
| GET | `/api/llm` | general | `/api/llm/providers` |
| GET | `/api/llm` | general | `/api/llm/routing-preview` |
| GET | `/api/llm` | general | `/api/llm/settings` |
| GET | `/api/llm` | general | `/api/llm/usage` |
| GET | `/api/ops-delivery` | general | `/api/ops-delivery/enabled` |
| GET | `/api/ops-delivery` | general | `/api/ops-delivery/overview` |
| GET | `/api/orchestration` | general | `/api/orchestration/enabled` |
| GET | `/api/orchestration` | general | `/api/orchestration/entity` |
| GET | `/api/orchestration` | general | `/api/orchestration/portfolio-context` |
| GET | `/api/orchestration` | general | `/api/orchestration/status` |
| GET | `/api/orchestration` | general | `/api/orchestration/trace` |
| GET | `/api/plan-spine` | general | `/api/plan-spine` |
| GET | `/api/quality` | general | `/api/quality/enabled` |
| GET | `/api/quality` | general | `/api/quality/overview` |
| GET | `/api/repo-workflow` | general | `/api/repo-workflow/enabled` |
| GET | `/api/repo-workflow` | general | `/api/repo-workflow/overview` |
| GET | `/api/roadmap-outline` | general | `/api/roadmap-outline` |
| GET | `/api/roadmap-section` | general | `/api/roadmap-section` |
| GET | `/api/roadmaps-matrix` | general | `/api/roadmaps-matrix` |
| GET | `/api/sdlc-copilot` | general | `/api/sdlc-copilot/chat-stream` |
| GET | `/api/sdlc-copilot` | general | `/api/sdlc-copilot/enabled` |
| GET | `/api/search` | general | `/api/search` |
| GET | `/api/search` | general | `/api/search/reindex` |
| GET | `/api/sticker-board` | general | `/api/sticker-board` |
| GET | `/api/sticker-board-registry` | general | `/api/sticker-board-registry` |
| GET | `/api/sticker-board-share` | general | `/api/sticker-board-share` |
| GET | `/api/sticker-board-share` | general | `/api/sticker-board-share/config` |
| GET | `/api/story-hub` | general | `/api/story-hub` |
| GET | `/api/timeline-context` | general | `/api/timeline-context` |
| GET | `/api/today-charge` | general | `/api/today-charge` |
| GET | `/api/tutorials-index` | general | `/api/tutorials-index` |
| GET | `/api/wbs-file` | general | `/api/wbs-file` |
| GET | `/api/wbs-management` | general | `/api/wbs-management` |
| GET | `/api/workflow-context` | general | `/api/workflow-context` |
| GET | `/api/workspace-md-file` | general | `/api/workspace-md-file` |
| GET | `/api/workspace-md-index` | general | `/api/workspace-md-index` |
| GET | `/api/workspace-state` | general | `/api/workspace-state` |
| GET | `/api/agent-runtime` | general | `PREFIX:/api/agent-runtime` |
| GET | `/api/agents` | general | `PREFIX:/api/agents` |
| GET | `/api/artifacts` | general | `PREFIX:/api/artifacts` |
| GET | `/api/assay-packets` | general | `PREFIX:/api/assay-packets` |
| GET | `/api/blueprints` | wizard | `PREFIX:/api/blueprints/wizard/session` |
| GET | `/api/bridge` | general | `PREFIX:/api/bridge` |
| GET | `/api/ceremonies` | general | `PREFIX:/api/ceremonies` |
| GET | `/api/decisions` | general | `PREFIX:/api/decisions` |
| GET | `/api/doc-hydration` | general | `PREFIX:/api/doc-hydration/review-packs` |
| GET | `/api/evidence` | general | `PREFIX:/api/evidence` |
| GET | `/api/execution-sessions` | general | `PREFIX:/api/execution-sessions` |
| GET | `/api/foundry` | general | `PREFIX:/api/foundry` |
| GET | `/api/handoffs` | general | `PREFIX:/api/handoffs` |
| GET | `/api/launches` | general | `PREFIX:/api/launches` |
| GET | `/api/methodology` | general | `PREFIX:/api/methodology` |
| GET | `/api/outcomes` | general | `PREFIX:/api/outcomes` |
| GET | `/api/pdlc` | general | `PREFIX:/api/pdlc/bridge` |
| GET | `/api/review-packs` | general | `PREFIX:/api/review-packs` |
| POST | `/api/access` | general | `/api/access/set-member` |
| POST | `/api/actions` | general | `/api/actions/run` |
| POST | `/api/assay-packets` | general | `/api/assay-packets` |
| POST | `/api/auth` | auth | `/api/auth/github` |
| POST | `/api/auth` | auth | `/api/auth/logout` |
| POST | `/api/auth` | auth | `/api/auth/loopback-dev-login` |
| POST | `/api/blueprints` | wizard | `/api/blueprints/wizard/session` |
| POST | `/api/blueprints` | wizard | `/api/blueprints/wizard/session/<id>/artifact-export` |
| POST | `/api/blueprints` | wizard | `/api/blueprints/wizard/session/<id>/artifact-recheck` |
| POST | `/api/blueprints` | wizard | `/api/blueprints/wizard/session/<id>/artifact-review` |
| POST | `/api/blueprints` | wizard | `/api/blueprints/wizard/session/<id>/clarify-suggest` |
| POST | `/api/blueprints` | wizard | `/api/blueprints/wizard/session/<id>/create-repo` |
| POST | `/api/blueprints` | wizard | `/api/blueprints/wizard/session/<id>/cursor-launch-pack/export` |
| POST | `/api/blueprints` | wizard | `/api/blueprints/wizard/session/<id>/cursor-launch-pack/preview` |
| POST | `/api/blueprints` | wizard | `/api/blueprints/wizard/session/<id>/generate-artifacts` |
| POST | `/api/blueprints` | wizard | `/api/blueprints/wizard/session/<id>/interpret` |
| POST | `/api/blueprints` | wizard | `/api/blueprints/wizard/session/<id>/refine` |
| POST | `/api/blueprints` | wizard | `/api/blueprints/wizard/telemetry` |
| POST | `/api/bridge` | general | `/api/bridge/links` |
| POST | `/api/fleet` | general | `/api/fleet/connect-forge-llm` |
| POST | `/api/fleet` | general | `/api/fleet/discover` |
| POST | `/api/fleet` | general | `/api/fleet/node-detail` |
| POST | `/api/fleet` | general | `/api/fleet/probe` |
| POST | `/api/fleet` | general | `/api/fleet/settings` |
| POST | `/api/fleet` | general | `/api/fleet/test-fleet` |
| POST | `/api/forgesdlc-blog` | general | `/api/forgesdlc-blog/sync` |
| POST | `/api/llm` | general | `/api/llm/chat` |
| POST | `/api/llm` | general | `/api/llm/ollama-action` |
| POST | `/api/llm` | general | `/api/llm/provider-probe` |
| POST | `/api/llm` | general | `/api/llm/routing-preview-draft` |
| POST | `/api/llm` | general | `/api/llm/settings` |
| POST | `/api/orchestration` | general | `/api/orchestration/seed-demo` |
| POST | `/api/review-packs` | general | `/api/review-packs` |
| POST | `/api/sdlc-copilot` | general | `/api/sdlc-copilot/chat` |
| POST | `/api/sdlc-copilot` | general | `/api/sdlc-copilot/chat-async` |
| POST | `/api/sdlc-copilot` | general | `/api/sdlc-copilot/commit-proposal` |
| POST | `/api/sdlc-copilot` | general | `/api/sdlc-copilot/topic-archive` |
| POST | `/api/search` | general | `/api/search/ingest` |
| POST | `/api/search` | general | `/api/search/reindex` |
| POST | `/api/sticker-board` | general | `/api/sticker-board` |
| POST | `/api/sticker-board-registry` | general | `/api/sticker-board-registry` |
| POST | `/api/sticker-board-share` | general | `/api/sticker-board-share` |
| POST | `/api/sticker-board-share` | general | `/api/sticker-board-share/join` |
| POST | `/api/toolset` | general | `/api/toolset/run` |
| POST | `/api/wbs` | general | `/api/wbs/create` |
| POST | `/api/agent-runtime` | general | `PREFIX:/api/agent-runtime` |
| POST | `/api/agents` | general | `PREFIX:/api/agents` |
| POST | `/api/artifacts` | general | `PREFIX:/api/artifacts` |
| POST | `/api/blueprints` | wizard | `PREFIX:/api/blueprints/wizard/session` |
| POST | `/api/ceremonies` | general | `PREFIX:/api/ceremonies` |
| POST | `/api/decisions` | general | `PREFIX:/api/decisions` |
| POST | `/api/execution-sessions` | general | `PREFIX:/api/execution-sessions` |
| POST | `/api/foundry` | general | `PREFIX:/api/foundry` |
| POST | `/api/handoffs` | general | `PREFIX:/api/handoffs` |
| POST | `/api/launches` | general | `PREFIX:/api/launches` |
| POST | `/api/outcomes` | general | `PREFIX:/api/outcomes` |
| PUT | `/api/blueprints` | wizard | `PREFIX:/api/blueprints/wizard/session` |

## By family

### `/api/access` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/access/policy` |
| POST | general | `/api/access/set-member` |

### `/api/actions` — 1 route(s)

| Method | Count |
|--------|-------|
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| POST | general | `/api/actions/run` |

### `/api/agent-runtime` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `PREFIX:/api/agent-runtime` |
| POST | general | `PREFIX:/api/agent-runtime` |

### `/api/agents` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `PREFIX:/api/agents` |
| POST | general | `PREFIX:/api/agents` |

### `/api/artifacts` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `PREFIX:/api/artifacts` |
| POST | general | `PREFIX:/api/artifacts` |

### `/api/assay-packets` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `PREFIX:/api/assay-packets` |
| POST | general | `/api/assay-packets` |

### `/api/auth` — 8 route(s)

| Method | Count |
|--------|-------|
| GET | 5 |
| POST | 3 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | auth | `/api/auth/loopback-dev-login` |
| GET | auth | `/api/auth/oidc/callback` |
| GET | auth | `/api/auth/oidc/login` |
| GET | auth | `/api/auth/oidc/status` |
| GET | auth | `/api/auth/status` |
| POST | auth | `/api/auth/github` |
| POST | auth | `/api/auth/logout` |
| POST | auth | `/api/auth/loopback-dev-login` |

### `/api/autonomy-maturity` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 2 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/autonomy-maturity/enabled` |
| GET | general | `/api/autonomy-maturity/overview` |

### `/api/blueprints` — 17 route(s)

| Method | Count |
|--------|-------|
| GET | 3 |
| POST | 13 |
| PUT | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | wizard | `/api/blueprints/wizard/enabled` |
| GET | wizard | `/api/blueprints/wizard/sessions` |
| GET | wizard | `PREFIX:/api/blueprints/wizard/session` |
| POST | wizard | `/api/blueprints/wizard/session` |
| POST | wizard | `/api/blueprints/wizard/session/<id>/artifact-export` |
| POST | wizard | `/api/blueprints/wizard/session/<id>/artifact-recheck` |
| POST | wizard | `/api/blueprints/wizard/session/<id>/artifact-review` |
| POST | wizard | `/api/blueprints/wizard/session/<id>/clarify-suggest` |
| POST | wizard | `/api/blueprints/wizard/session/<id>/create-repo` |
| POST | wizard | `/api/blueprints/wizard/session/<id>/cursor-launch-pack/export` |
| POST | wizard | `/api/blueprints/wizard/session/<id>/cursor-launch-pack/preview` |
| POST | wizard | `/api/blueprints/wizard/session/<id>/generate-artifacts` |
| POST | wizard | `/api/blueprints/wizard/session/<id>/interpret` |
| POST | wizard | `/api/blueprints/wizard/session/<id>/refine` |
| POST | wizard | `/api/blueprints/wizard/telemetry` |
| POST | wizard | `PREFIX:/api/blueprints/wizard/session` |
| PUT | wizard | `PREFIX:/api/blueprints/wizard/session` |

### `/api/bridge` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `PREFIX:/api/bridge` |
| POST | general | `/api/bridge/links` |

### `/api/ceremonies` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `PREFIX:/api/ceremonies` |
| POST | general | `PREFIX:/api/ceremonies` |

### `/api/chart-data` — 1 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/chart-data/overview` |

### `/api/cicd` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 2 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/cicd/control-tower` |
| GET | general | `/api/cicd/enabled` |

### `/api/connectors` — 1 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/connectors/health` |

### `/api/cross-team-release` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 2 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/cross-team-release/enabled` |
| GET | general | `/api/cross-team-release/overview` |

### `/api/decisions` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `PREFIX:/api/decisions` |
| POST | general | `PREFIX:/api/decisions` |

### `/api/delivery` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 2 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/delivery/enabled` |
| GET | general | `/api/delivery/overview` |

### `/api/devsecops` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 2 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/devsecops/enabled` |
| GET | general | `/api/devsecops/overview` |

### `/api/doc-hydration` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 2 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/doc-hydration/review-packs` |
| GET | general | `PREFIX:/api/doc-hydration/review-packs` |

### `/api/docs-health` — 3 route(s)

| Method | Count |
|--------|-------|
| GET | 3 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | docs-health | `/api/docs-health/live-sessions` |
| GET | docs-health | `/api/docs-health/summary` |
| GET | docs-health | `/api/docs-health/work-items` |

### `/api/evidence` — 1 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `PREFIX:/api/evidence` |

### `/api/execution-sessions` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `PREFIX:/api/execution-sessions` |
| POST | general | `PREFIX:/api/execution-sessions` |

### `/api/fleet` — 7 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |
| POST | 6 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/fleet/settings` |
| POST | general | `/api/fleet/connect-forge-llm` |
| POST | general | `/api/fleet/discover` |
| POST | general | `/api/fleet/node-detail` |
| POST | general | `/api/fleet/probe` |
| POST | general | `/api/fleet/settings` |
| POST | general | `/api/fleet/test-fleet` |

### `/api/forge-work-model` — 1 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/forge-work-model` |

### `/api/forgesdlc-blog` — 3 route(s)

| Method | Count |
|--------|-------|
| GET | 2 |
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/forgesdlc-blog` |
| GET | general | `/api/forgesdlc-blog/content` |
| POST | general | `/api/forgesdlc-blog/sync` |

### `/api/foundry` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `PREFIX:/api/foundry` |
| POST | general | `PREFIX:/api/foundry` |

### `/api/governance` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 2 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/governance/audit` |
| GET | general | `/api/governance/scopes` |

### `/api/handoffs` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `PREFIX:/api/handoffs` |
| POST | general | `PREFIX:/api/handoffs` |

### `/api/launches` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `PREFIX:/api/launches` |
| POST | general | `PREFIX:/api/launches` |

### `/api/llm` — 12 route(s)

| Method | Count |
|--------|-------|
| GET | 7 |
| POST | 5 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/llm/diagnostics` |
| GET | general | `/api/llm/model-catalog-notifications` |
| GET | general | `/api/llm/ollama-status` |
| GET | general | `/api/llm/providers` |
| GET | general | `/api/llm/routing-preview` |
| GET | general | `/api/llm/settings` |
| GET | general | `/api/llm/usage` |
| POST | general | `/api/llm/chat` |
| POST | general | `/api/llm/ollama-action` |
| POST | general | `/api/llm/provider-probe` |
| POST | general | `/api/llm/routing-preview-draft` |
| POST | general | `/api/llm/settings` |

### `/api/methodology` — 1 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `PREFIX:/api/methodology` |

### `/api/ops-delivery` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 2 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/ops-delivery/enabled` |
| GET | general | `/api/ops-delivery/overview` |

### `/api/orchestration` — 6 route(s)

| Method | Count |
|--------|-------|
| GET | 5 |
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/orchestration/enabled` |
| GET | general | `/api/orchestration/entity` |
| GET | general | `/api/orchestration/portfolio-context` |
| GET | general | `/api/orchestration/status` |
| GET | general | `/api/orchestration/trace` |
| POST | general | `/api/orchestration/seed-demo` |

### `/api/outcomes` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `PREFIX:/api/outcomes` |
| POST | general | `PREFIX:/api/outcomes` |

### `/api/pdlc` — 1 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `PREFIX:/api/pdlc/bridge` |

### `/api/plan-spine` — 1 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/plan-spine` |

### `/api/quality` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 2 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/quality/enabled` |
| GET | general | `/api/quality/overview` |

### `/api/repo-workflow` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 2 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/repo-workflow/enabled` |
| GET | general | `/api/repo-workflow/overview` |

### `/api/review-packs` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `PREFIX:/api/review-packs` |
| POST | general | `/api/review-packs` |

### `/api/roadmap-outline` — 1 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/roadmap-outline` |

### `/api/roadmap-section` — 1 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/roadmap-section` |

### `/api/roadmaps-matrix` — 1 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/roadmaps-matrix` |

### `/api/sdlc-copilot` — 6 route(s)

| Method | Count |
|--------|-------|
| GET | 2 |
| POST | 4 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/sdlc-copilot/chat-stream` |
| GET | general | `/api/sdlc-copilot/enabled` |
| POST | general | `/api/sdlc-copilot/chat` |
| POST | general | `/api/sdlc-copilot/chat-async` |
| POST | general | `/api/sdlc-copilot/commit-proposal` |
| POST | general | `/api/sdlc-copilot/topic-archive` |

### `/api/search` — 4 route(s)

| Method | Count |
|--------|-------|
| GET | 2 |
| POST | 2 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/search` |
| GET | general | `/api/search/reindex` |
| POST | general | `/api/search/ingest` |
| POST | general | `/api/search/reindex` |

### `/api/sticker-board` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/sticker-board` |
| POST | general | `/api/sticker-board` |

### `/api/sticker-board-registry` — 2 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/sticker-board-registry` |
| POST | general | `/api/sticker-board-registry` |

### `/api/sticker-board-share` — 4 route(s)

| Method | Count |
|--------|-------|
| GET | 2 |
| POST | 2 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/sticker-board-share` |
| GET | general | `/api/sticker-board-share/config` |
| POST | general | `/api/sticker-board-share` |
| POST | general | `/api/sticker-board-share/join` |

### `/api/story-hub` — 1 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/story-hub` |

### `/api/timeline-context` — 1 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/timeline-context` |

### `/api/today-charge` — 1 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/today-charge` |

### `/api/toolset` — 1 route(s)

| Method | Count |
|--------|-------|
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| POST | general | `/api/toolset/run` |

### `/api/tutorials-index` — 1 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/tutorials-index` |

### `/api/wbs` — 1 route(s)

| Method | Count |
|--------|-------|
| POST | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| POST | general | `/api/wbs/create` |

### `/api/wbs-file` — 1 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/wbs-file` |

### `/api/wbs-management` — 1 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/wbs-management` |

### `/api/workflow-context` — 1 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/workflow-context` |

### `/api/workspace-md-file` — 1 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/workspace-md-file` |

### `/api/workspace-md-index` — 1 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/workspace-md-index` |

### `/api/workspace-state` — 1 route(s)

| Method | Count |
|--------|-------|
| GET | 1 |

| Method | Audience | Signature |
|--------|----------|-----------|
| GET | general | `/api/workspace-state` |
