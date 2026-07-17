# HTTP API and routes

The server binds to **127.0.0.1:8080** by default (`--host`, `--port` override). The dashboard is intended for **loopback use only** so local previews and privileged APIs are not exposed on the LAN unless you explicitly opt in.

## Bind safety

- Default **`--host 127.0.0.1`** — use **`http://127.0.0.1:8080/`** (not `0.0.0.0`).
- Binding to **`0.0.0.0`**, **`::`**, or any **non-loopback** IP **exits with an error** unless you also pass **`--bind-all-interfaces`**, which prints a **security warning**.
- Environment **`LENSES_ALLOW_ACTIONS=1`** allows **POST** auth and allowlisted shell actions from **non-loopback** clients when you have bound beyond localhost (still requires GitHub session + allowlist for actions).

## Kitchensink assets (dynamic UI)

When the **`kitchensink/`** submodule is present, the server serves design-system files for the dashboard:

| Path | Purpose |
|------|---------|
| `/__ks/css/…` | CSS from `kitchensink/css/` (e.g. `forge-theme.css`, `forgesdlc-theme.css`). |
| `/__ks/js/…` | JS from `kitchensink/js/` (e.g. `forge-theme.js`). |
| `/__ks/assets/svg/…` | SVGs under `kitchensink/assets/svg/`. |

Requests are rejected if the resolved path leaves those subtrees or is not a regular file.

## Lenses-owned static (dashboard JS)

| Path | Purpose |
|------|---------|
| `/__lenses/js/…` | JavaScript under **`lenses/static/js/`** in the forge-lenses repo (e.g. sticker board UI). Only **`.js`** files under that subtree are served; path traversal is rejected. |

## Local site preview (built static output)

| Path | Purpose |
|------|---------|
| `/local-site/<repo>/…` | **Static root** per repo: **`firebase.json`** **`hosting.public`** if that directory exists; otherwise **`website/`**, **`public/`**, or **`dist/`** (first match). (1) **`tutorial`** / **`tutorial/…`** — from **`<repo>/tutorial/`** for any child (default **`index.html`** when the path is exactly **`tutorial`**). (2) **`tutorials`** / **`tutorials/…`** — **`tutorials/`** with **`index.html`**, else **`lenses/tutorials/`**, else **`website/tutorials/`**; then under the static root. (3) **Other paths** — files under the static root (default **`index.html`** when empty). Reject **`..`**. Same origin as the dashboard (`/websites/browse?site=<repo>`). |

### HTML responses (`*.html` / `*.htm`)

For **`text/html`** only, the server **rewrites** the UTF-8 body before returning it:

1. **Root-relative `href` / `src`** — Values starting with `/` (but not `//` and not already `/local-site/`) are prefixed with **`/local-site/<repo>/`** so `href="/assets/foo.css"` becomes `href="/local-site/<repo>/assets/foo.css"` and loads correctly under the preview prefix.
2. **`<base href="…">`** — If the document does not already define `<base href=…>`, one is inserted right after **`<head>`** (or after the first **`<meta charset=…>`** in the head, when present). The base URL is **`http` or `https`** (see `X-Forwarded-Proto`) plus the **`Host`** header plus the **directory** of the requested URL (e.g. `/local-site/forgesdlc/` for `…/forgesdlc/index.html`, or `…/forgesdlc/cases/showcase/` for a nested `index.html`). If `Host` is missing, **`127.0.0.1`** is assumed (you should still send `:8080` in the host when using a non-default port).

Non-HTML files (CSS, JS, fonts, images, etc.) are returned **unchanged**. **`Content-Type`** uses explicit mappings for common extensions (e.g. **`.woff2`** → `font/woff2`, **`.webmanifest`** → `application/manifest+json`) and falls back to `mimetypes.guess_type`.

### Styling looks “half broken” in the iframe

1. **DevTools (preview iframe)** — Open **Network**, filter **CSS** / **JS**, reload. Distinguish:
   - **404** on paths under **`/local-site/<repo>/`** → path or rewrite issue.
   - **Failed / blocked** requests to **cdn.jsdelivr.net**, **fonts.googleapis.com**, etc. → many generated pages load **Bootstrap** and **fonts** from the public internet; offline or strict blockers cause partial styling while local **`assets/*.css`** may still load. That is **not** a lenses static-file bug.
2. **Same-origin cookies** — Product **`forge-theme.js`** may set **`forge_color_scheme`** with **`Path=/`**, which is shared across the whole **`127.0.0.1:8080`** origin (dashboard + iframe). That can affect theme preference but not whether stylesheets load.

## HTML dashboard

Route catalog (maintainer): see **`docs/maintainer/website/interface-pages.md`** in the repository. Public users start from the [Studio overview](https://blueprints.forgesdlc.com/lenses/guides/04-studio-overview.html) guide.

| Path | Purpose |
|------|---------|
| `/` | Overview: workspace root, child directories, quick stats. |
| `/projects` | Portal: card grid with README previews, git badges, links to each project dashboard. |
| `/tutorials` | Index of every detected forge-autodoc handbook per workspace child (**`tutorial/index.html`**, **`tutorials/index.html`**, **`lenses/tutorials/index.html`**, or **`website/tutorials/index.html`** via **`list_child_handbooks`**), with **Open tutorial** / **Open engineer handbook** links under **`/local-site/<name>/…`** and **Project dashboard**. |
| `/projects/<name>` | Per-project dashboard: revision links, 90-day commit chart, contributors, file-type bars, optional git actions, JSON stats link. |
| `/projects/<name>/charts-api` | Same metrics as the project dashboard, rendered client-side via **`forge-data-charts.js`** and **`GET /api/project/<name>/chart-data`**. The classic HTML charts remain on **`/projects/<name>`**. |
| `/projects/<name>/strategy` | Repo layout and strategy: **`.gitmodules`** table, **`git submodule status`** (bounded), optional inline SVG + kitchensink template thumbnail, current branch / remote default, registry **`project_strategy`** text, optional **`LENSES-REPO-STRATEGY.md`**. |
| `/projects/<name>/branching` | Branch Steward review page: resolved policy source (`forge/branching.yml` fallback chain), lane/grouped branches, branch protection, PR structure, and recommended branch choices for Charge/backlog/ad-hoc/spike/hotfix flows. |
| `/overview/charts-api` | Workspace analytics (same kinds as **`/`** overview charts) via **`GET /api/chart-data/overview`**. |
| `/toolset` | Card grid of workspace-root **`*.sh`** scripts (blurbs from comments) and `.cursor` presence. |
| `/toolset/<name>` | Per-script run screen: confirm, then **`POST /api/toolset/run`** for console output. |
| `/websites` | Firebase site repos: hero cards, stats, search, local preview links, copyable build/deploy commands, GitHub PAT sign-in for allowlisted actions. |
| `/websites/browse?site=<name>` | Sticky dashboard chrome + sidebar page index + **iframe** preview (`/local-site/<name>/…`). |
| `/search` | Local full-text search. **GET** query: **`q`** (keywords), optional **`limit`** (default **25**, max **100**), **`offset`** (pagination), **`repo`** or **`site`** (workspace child name — boosts results under **`/local-site/<name>/`**). Optional **`reindex=`** after index rebuild redirects. The index is **SQLite FTS5** at **`<workspace>/.lenses-local/lenses-search.sqlite`**. Populate with **`POST /api/search/reindex`** or **GET** **`/api/search/reindex?redirect=…`**; optional **`POST /api/search/ingest`** for client-rendered page text. |
| `/wbs` | Index of `docs/requirements/WBS.md` files. |
| `/wbs/view` | Query `?p=<relative-path>` — read-only viewer for one WBS file (path must stay under workspace and include `requirements` segment; file name must be `WBS.md`). |
| `/plan` | **Forge plan** lens: pick repository, **WBS**, optional **ROADMAP.md**. **Plan** tab: **3-pane explorer** (work tree from **`/api/forge-work-model`**, center pane, detail rail). **Today** tab: compact operational tables from **`/api/today-charge`** (Charge + WBS + Versona), links to **`?id=`** on this page. **Story** and **Spark** selections use the center pane as the primary **story cockpit** (tabs: Definition, Product context, Execution, Decisions, Source) fed by **`/api/story-hub`**; the **Detail** rail stays minimal. Other nodes use a level-aware center and **`/api/forge-work-model?node_id=`** in the rail. Filter/search, URL `?id=` & `?tab=plan|today|source`, roadmap summary strip (collapsible). **Source** tab: iframe roadmap section preview (outline is not mixed into the work tree). |
| `/roadmaps` | **302 redirect** to **`/plan`** (same query string preserved for bookmarks). |
| `/workspace-md/view` | Query `?p=<relative-path>` — read-only viewer for allowlisted Forge markdown under the workspace (`forge/charge.md`, `forge/journal/*.md`, `ember-logs/*.md`, `forge-logs/**/*.md`). |
| `/roadmaps/summary` | Query `?p=<relative-path>` — HTML fragment only: charts + KS diagram thumbnails derived from tables in that roadmap (status, % complete, horizon). |
| `/roadmaps/preview` | Query `?p=<relative-path>&section=<id>` — full minimal HTML document for one section (for iframe `src`; links `/__ks/css/` for theming). |
| `/board` | **Sticker board** hub: flat list of boards with project filter, thumbnails, create / rename / delete / move between projects. Optional **`?project=<child-name>`** pre-selects the filter (same as the link from a project dashboard). |
| `/board/<board_id>` | **Sticker board editor** for one board: Kanban / freeform stickers; hover **edit** / **delete** on cards. **`?thumb=1`** — minimal chrome for PNG capture. **Local** board file: **`<workspace>/.lenses-local/sticker-boards/<board_id>.json`**. **Shared** board: **`<workspace>/.lenses-repo/<login>/sticker-boards/<board_id>.json`** + **`<workspace>/.lenses-local/sticker-boards/<board_id>-shared-local.json`** + marker **`<board_id>.marker.json`**. Registry: **`<workspace>/.lenses-local/sticker-board-registry.json`**. Legacy single-file **`sticker-board.json`** is migrated automatically on first access. |
| `/board-preview/<board_id>.png` | **PNG** thumbnail if present under **`.lenses-local/sticker-board-previews/`** and **`board_id`** is in the registry; **404** otherwise. **`Cache-Control: private, max-age=60`**. |

Top navigation and sidebar: workspace pages (including **Tutorials** → **`/tutorials`**), **Lenses docs** (**`/docs/`**), then **Handbook** and **Forge** (URLs from registry defaults or overrides).

## Static documentation

| Path | Purpose |
|------|---------|
| `/docs`, `/docs/…` | Files under **`lenses-docs/`** in the forge-lenses repo (run `python3 generator/build-lenses-docs.py`). If docs are missing, some URLs return plain-text guidance. |

## JSON API

Maintainer-facing JSON schemas (Wizard payloads, canonical HTTP errors) ship in **`docs/schemas/`** beside this repo (`README.md` explains stability tiers). Companion **`docs/examples/`** snippets are exercised by **`tests/test_docs_schemas.py`**.

| Method | Path | Response |
|--------|------|----------|
| `GET` | `/api/roadmap-outline?p=<relative-path>` | `application/json` — `{ "doc_title", "sections": [ { "id", "level", "title" } ] }` for one `ROADMAP.md`. **400** if `p` missing; **404** if path not allowed or missing. |
| `GET` | `/api/roadmaps-matrix` | JSON matrix summarizing roadmap coverage across tracked workspace repos (Forge Studio **`Plan`** views). Mirrors **`/plan`** explorers; honours the same roadmap allowlisting rules as **`/api/roadmap-outline`**. Typical query knobs: **`repo`** filter + pagination hints surfaced in **`ui-map-workflow.md`**. |
| `GET` | `/api/plan-spine?wbs_p=<rel>&repo=<repo_hint>&roadmap_p=<rel optional>` | JSON: joined **plan** tree (from WBS), optional roadmap metrics, Charge rows, Versona session count, forge path hints. When the orchestration graph is enabled and the DB is available, includes **`orchestration`**: graph completeness score, dependency pressure, critical path, and scenario ids (Studio readiness cards). **400** if `wbs_p` missing; **404** if WBS path not allowed. |
| `GET` | `/api/story-hub?id=<WBS_ID>&wbs_p=<rel>&repo=<repo_hint>&roadmap_p=<rel optional>` | JSON: story or task **definition**; **today_charge**, **decision_log_ember**, **discipline_sessions_versona**, **journal** (legacy fields); **`story_view`** when the work item resolves to a story (or a spark’s parent story): structured **slots** (WBS column → problem, acceptance, notes, etc.), **milestone_outcome**, **phase_affinity**, **roadmap_hits** (sections mentioning the story id), **product_context** (work-graph doc links), **execution** (WBS sparks + charge rows), **decisions** (Ember scans, graph-linked decisions/sessions, Versona list), **sources** (WBS / Charge / journal). When orchestration + repo-workflow features are on, includes **`code_execution`**: **`graph`** (branch / PR / commit links and merge readiness from **`implements`** / **`targets`** edges), **`repo`** (fixture-backed PR preview, **`project_href`** to Studio Projects), and when the graph DB is available **`cicd_trace`** (story → **build** → **artifact** → **release** → **environment** via **`tests`**, **`contains`**, **`deploys`** edges), **`quality_trace`** (**test_plan** / **test_suite** / **test_case** / **test_run** / **defect** / **release** via **`validates`**, **`raised_defect`**, **`affects`**), **`security_trace`** (**security_finding** → story via **`affects`**; **compliance_exception** via **`accepted_risk_for`**; **control** → **release** via **`satisfies`** when delivery trace yields releases). When test-quality is on and a fixture exists, **`quality_evidence`** (test cases, runs, defects, UAT, attachments for that story id). When DevSecOps is on and **`devsecops-compliance`** data exists, **`devsecops_evidence`** (findings, vulns, secrets, exceptions, controls tagged with **`story_ids`**). When Ops delivery is on and the graph DB is available, **`ops_trace`** (**incident** → story via **`affects`**, **`triggered_after`** **release**, **`impacts`** **service**, **postmortem** **`analyzes`** incident). When Ops delivery is on and **`ops-delivery`** data exists, **`ops_delivery_evidence`** (incidents, postmortems, SLOs tagged with **`story_ids`**). Optional **`roadmap_ctx`** (metrics) when **`roadmap_p`** is set. **400** if `id` or `wbs_p` missing. |
| `GET` | `/api/today-charge?wbs_p=<rel>&repo=<repo_hint>&roadmap_p=<rel optional>` | JSON: **Today (Charge)** operational view — **`spark_rows`** (full list with **`flags`**, **`breadcrumb`**, **`plan_href`**), **`sections`** ( **`active`**, **`blocked`**, **`banked`**, **`recently_resolved`**, **`pending_versona`** ), **`charge`** (frontmatter hat/date, **`view_href`**), **`phase_prefixes`**, **`notes`**. Joins **`forge/charge.md`** (Active Sparks + Blockers + Banking tables) with WBS and Versona session index. **400** if `wbs_p` missing; **404** if WBS path not allowed. |
| `GET` | `/api/workspace-state` | `application/json` — scan object from `scan_workspace` plus **`standards_compliance_note`** and per-child **`standards_compliance`** (heuristic agentic/standards score) after server enrichment (see [Workspace scan contract](workspace-scan-contract.html)). |
| `GET` | `/api/delivery/enabled` | JSON **`{ "ok", "enabled" }`** — whether delivery / pipeline signal overlays are on (`experimental_delivery_signals_enabled()`). **Off** when **`LENSES_EXPERIMENTAL_DELIVERY_SIGNALS`** is **`0`** / **`false`** / **`no`** / **`off`**; **on** by default (local scan + optional JSON only). |
| `GET` | `/api/delivery/overview` | JSON **schema v1** — **`feature_enabled`**, **`provider_kind`** (`disabled` \| `scan_only` \| `local_fixture`), **`workspace_summary`**, **`repos`** (per child: git hints, optional **`workflows`**, **`trace_links`**, **`environments`**, **`releases`** from **`.lenses-local/delivery-signals.json`**), **`hints`**. Uses the same workspace scan as **`/api/workspace-state`** (git extended). Read-only. Optional demo overlay: **`LENSES_DELIVERY_SIGNALS_SEED_DEMO=1`** merges **`lenses/fixtures/delivery-signals.demo.json`** when no local file exists. Studio surfaces this on **Plan → Today** as *Pipeline and traceability*. |
| `GET` | `/api/repo-workflow/enabled` | JSON **`{ "ok", "enabled" }`** — repo / PR / MR workflow feature flag (**`LENSES_EXPERIMENTAL_REPO_WORKFLOW`**; off when **`0`** / **`false`** / **`no`** / **`off`**; on by default). |
| `GET` | `/api/repo-workflow/overview` | JSON **schema v1** — same scan merge as delivery: per-repo **`workflow`** (normalized **branches**, **pull_requests**, **branch_protection**, **code_owners**, **commits_recent**), **`health`** (open/stale/blocked PR counts, review debt, optional **`unlinked_work_items_count`**), **`work_item_links`** (story id → branch / PR URLs). Data from **`.lenses-local/repo-workflow.json`** or **`LENSES_REPO_WORKFLOW_SEED_DEMO=1`** (**`lenses/fixtures/repo-workflow.demo.json`**). Provider-specific JSON is normalized via GitHub / GitLab / Azure Repos adapters. |
| `GET` | `/api/cicd/enabled` | JSON **`{ "ok", "enabled" }`** — CI/CD control tower feature flag (**`LENSES_EXPERIMENTAL_CICD_ORCHESTRATION`**; off when **`0`** / **`false`** / **`no`** / **`off`**; on by default). |
| `GET` | `/api/cicd/control-tower` | JSON **schema v1** — **`feature_enabled`**, **`provider_kind`** (`disabled` \| `scan_only` \| `local_fixture`), **`workspace_summary`**, **`pipeline_runs`** (canonical **`pipeline_run`** rows from GitHub Actions, GitLab CI, Azure Pipelines, Jenkins, Argo CD-style fixtures), **`environments`** (catalog: current version, last deploy, rollback target, approval status, history), **`release_train`**, **`promotions`** (checkpoints, blocked reasons), **`freeze_windows`**, **`blocked_promotions`**, **`what_is_live`**, **`rollback_targets`**, optional **`artifacts`**, optional **`security_release_gate`** (policy + risk summary for the train). Merges **`.lenses-local/cicd-orchestration.json`** with workspace scan (project filter); demo: **`LENSES_CICD_ORCHESTRATION_SEED_DEMO=1`** (**`lenses/fixtures/cicd-orchestration.demo.json`**). When **`LENSES_EXPERIMENTAL_TEST_QUALITY`** is on and **`test-quality`** data exists, appends **`quality_gate_failed:*`** rows to **`blocked_promotions`** and may add **`hints`**. When **`LENSES_EXPERIMENTAL_DEVSECOPS_COMPLIANCE`** is on and **`devsecops-compliance`** data exists, appends **`security_policy_failed:<policy_id>`** to **`blocked_promotions`** for failing security policies that block the train. Same git-extended scan as **`/api/workspace-state?git_extended=1`**. Read-only. |
| `GET` | `/api/quality/enabled` | JSON **`{ "ok", "enabled" }`** — test management / quality gates flag (**`LENSES_EXPERIMENTAL_TEST_QUALITY`**; off when **`0`** / **`false`** / **`no`** / **`off`**; on by default). |
| `GET` | `/api/quality/overview` | JSON **schema v1** — **`test_plans`**, **`test_suites`**, **`test_cases`**, **`test_runs`** (manual and automated **`execution_kind`**), **`defects`**, **`coverage_summaries`**, **`flaky_test_signals`**, **`quality_gates`**, evaluated **`gate_evaluations`**, **`uat_signoffs`**, **`regression_packs`**, **`release_readiness_checklists`**, **`evidence_attachments`**, **`release_quality`** (train readiness), **`run_comparisons`** (current vs **`compared_to_run_id`**). **`.lenses-local/test-quality.json`** or **`LENSES_TEST_QUALITY_SEED_DEMO=1`** (**`lenses/fixtures/test-quality.demo.json`**). Read-only. |
| `GET` | `/api/devsecops/enabled` | JSON **`{ "ok", "enabled" }`** — DevSecOps / compliance orchestration flag (**`LENSES_EXPERIMENTAL_DEVSECOPS_COMPLIANCE`**; off when **`0`** / **`false`** / **`no`** / **`off`**; on by default). |
| `GET` | `/api/devsecops/overview` | JSON **schema v1** — canonical rows (**`security_findings`**, **`vulnerabilities`**, **`secret_exposures`**, **`dependency_risks`**, **`sbom_components`**, **`provenance_attestations`**, **`controls`**, **`exceptions`**, **`policy_decisions`**, **`security_policies`** when present), **`policy_check_evaluations`**, **`rollups`** (**`by_repo`**, **`by_initiative`**, **`by_release`**, **`by_environment`**), computed **`risk_score`**, **`security_release_gate`**. **`.lenses-local/devsecops-compliance.json`** or **`LENSES_DEVSECOPS_COMPLIANCE_SEED_DEMO=1`** (**`lenses/fixtures/devsecops-compliance.demo.json`**). Ingestion adapters expand **`ingestions[]`** from CodeQL/Semgrep, Dependabot/Snyk, Gitleaks, Trivy, Syft/Cosign-shaped payloads. Read-only. |
| `GET` | `/api/cross-team-release/enabled` | JSON **`{ "ok", "enabled" }`** — cross-team release / change orchestration flag (**`LENSES_EXPERIMENTAL_CROSS_TEAM_RELEASE`**; off when **`0`** / **`false`** / **`no`** / **`off`**; on by default). |
| `GET` | `/api/cross-team-release/overview` | JSON **schema v1** — **`dependency_board`** (**`nodes`**, **`edges`**; workspace git children may add **`repo`** nodes), **`dependency_edges`** (typed cross-team links for packet text), **`release_calendar`** (**`events`**: milestones, **`freeze_window`** from live CI/CD, **`implementation_window`**, **`cab`**), **`change_requests`** (scope, risk, **`approvers`**, **`implementation_window`**, **`rollback_notes`**), **`cab_sessions`** (**`decisions`** CAB-lite), **`readiness_views`**, **`go_no_go_packet`** (**`sections`**, **`markdown`** assembled from fixture + live **`build_cicd_control_tower_payload`**, plus quality / DevSecOps summaries when those fixtures exist), **`communication_artifacts`** (**`release_notes_md`**, **`stakeholder_summary_md`**, **`blocker_summary_md`**), **`live_enrichment`** (train, **`blocked_promotions`**, **`rollback_targets`**, **`what_is_live`**, freezes, promotions). **`.lenses-local/cross-team-release.json`** or **`LENSES_CROSS_TEAM_RELEASE_SEED_DEMO=1`** (**`lenses/fixtures/cross-team-release.demo.json`**). Read-only. |
| `GET` | `/api/ops-delivery/enabled` | JSON **`{ "ok", "enabled" }`** — ops feedback / delivery metrics flag (**`LENSES_EXPERIMENTAL_OPS_DELIVERY`**; off when **`0`** / **`false`** / **`no`** / **`off`**; on by default). |
| `GET` | `/api/ops-delivery/overview` | JSON **schema v1** — **`services`**, **`slis`**, **`slos`**, **`incidents`** (with **`traceability`** block: release, environment, story ids, promotion), **`postmortems`**, **`error_budget_events`**, **`feature_flag_exposures`**, **`dora_metrics`** (deploy frequency, lead time, change failure rate, recovery / MTTR, rework from pipelines + quality), **`rollback_signals`**, **`postmortem_templates`**. Merges **`.lenses-local/ops-delivery.json`** (and **`ingestions[]`** for PagerDuty-style incidents) with live **`build_cicd_control_tower_payload`** and optional test-quality for rework. Demo: **`LENSES_OPS_DELIVERY_SEED_DEMO=1`** (**`lenses/fixtures/ops-delivery.demo.json`**). Read-only. |
| `GET` | `/api/orchestration/enabled` | JSON **`{ "ok", "enabled" }`** — orchestration graph feature flag (**`LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH`**; off when **`0`** / **`false`** / **`no`** / **`off`**). |
| `GET` | `/api/orchestration/status` | JSON **`ok`**, **`feature_disabled`**, **`schema_version`**, **`entity_count`**, **`edge_count`** — stats for **`<workspace>/.lenses-local/lenses-orchestration.sqlite`**. |
| `GET` | `/api/orchestration/entity?id=<entity_id>` | JSON **`entity`** (or **404** `entity_not_found`). Single node with **`payload`**, provenance fields. |
| `GET` | `/api/orchestration/trace?root=<id>&direction=out\|in\|both&max_depth=&max_nodes=` | JSON **trace payload**: **`root`**, **`nodes[]`**, **`edges[]`**, **`truncated`**, **`limits`**. BFS neighborhood for traceability UI. **400** if **`root`** missing. |
| `POST` | `/api/orchestration/seed-demo` | Reloads demo entities/edges from **`lenses/fixtures/orchestration-graph.demo.json`** (deletes prior **`ogs:demo:*`** rows). **403** unless loopback or **`LENSES_ALLOW_ACTIONS=1`**. **404** if feature disabled. |
| `GET` | `/api/orchestration/portfolio-context?scenario_a=&scenario_b=&slip_focus=` | JSON **`ok`**, **`rollups`** (dependency pressure, graph completeness, milestone confidence, critical path, risk heuristics), **`scenarios`**, optional **`scenario_compare`** when both scenario ids are set, **`slip_impact`** when **`slip_focus`** resolves to an entity, **`depends_on_edges`**, **`workstreams`** (capacity placeholders). **`200`** with **`feature_disabled`** when **`LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH`** is off; **503** if the DB file cannot be opened. |
| `GET` | `/api/tutorials-index` | JSON **`{ "ok", "rows" }`** — forge-autodoc handbook rows per workspace child (same discovery as **`/tutorials`**: **`list_child_handbooks`**). Each row: **`child_name`**, **`kind`**, **`label`**, **`local_site_rel`**, **`preview_url`**. |
| `GET` | `/api/timeline-context?repo=&wbs_p=&roadmap_p=` | JSON for **Timeline** (Classic **`/timeline`** and Lenses Studio): **`repo_hints`**, **`wbs_options`**, **`roadmap_options`**, **`selected`**, **`gantt_html`**, **`metrics_html`**, **`editor_html`**, **`roadmap_source_href`**, **`workspace_projects`**, **`current_project`**. When the orchestration graph is enabled, may include **`orchestration_portfolio`** (rollups, scenarios, slip demo, same schema as matrix overlay). |
| `GET` | `/api/wbs-file?p=<relative-path>` | JSON **`{ "ok", "text", "kind": "md", "rel_path" }`** for one `WBS.md` under the same rules as **`/wbs/view`**. |
| `GET` | `/api/workspace-md-file?p=<relative-path>` | JSON **`{ "ok", "text", "rel_path" }`** for allowlisted Forge markdown (same rules as **`/workspace-md/view`**). |
| `GET` | `/api/roadmap-section?p=<roadmap-rel>&section=<id>` | JSON **`{ "ok", "html", "rel_path", "section" }`** — HTML fragment for one roadmap section (Studio and other clients). |
| `GET` | `/api/search?q=<query>&limit=<n>&offset=<n>&site=<repo>&repo=<repo>` | JSON: **`ok`**, **`query`**, **`hits`**, **`total`** (match count for the query), **`limit`**, **`offset`**. Each hit: **`path_key`**, **`url`**, **`title`**, **`source`**, **`snippet`**, **`ref_count`** (inbound internal links from indexed HTML/Markdown), **`score`** (BM25-style rank with indegree adjustment; lower is better). **`site`** and **`repo`** are aliases: when set, matches under **`/local-site/<value>/`** are ranked ahead of others. Ranking uses **FTS5 BM25** with higher weight on **title** and **headings** than **body**. Empty **`q`** returns empty **`hits`** and **`total`: 0**. **`limit`** defaults to **25**, max **100**; **`offset`** defaults to **0**. |
| `GET` | `/api/search/reindex?redirect=/search` | Same side effect as **POST** (starts background reindex when allowed). With **`redirect`**, responds **303** to that path with **`reindex=started`** or **`reindex=busy`** in the query string (browser-friendly). Without **`redirect`**, JSON **202** / **409** / **403** like **POST**. |
| `POST` | `/api/search/reindex` | **202** when a background reindex starts: **`ok`**, **`status`**: `"started"`. Indexes HTML/Markdown under each workspace child’s **static output directory** (see **Local search index** — no Firebase CLI required) and under **`lenses-docs/`** in the forge-lenses checkout. **409** if a reindex is already running. **403** from non-loopback unless **`LENSES_ALLOW_ACTIONS=1`**. |
| `POST` | `/api/search/ingest` | Body: JSON **`{"url":"<canonical url>","title":"<short>","text":"<plain text>"}`** ( **`text`** max ~512 KiB). Upserts one **`ingested`** document for dynamic/client-rendered views. **400** if **`url`** or **`text`** missing. **403** same as reindex. |
| `GET` | `/api/workspace-state?git_extended=1` | Same shape, with `git` objects including `head_short`, `head_full`, `commit_subject`, `commit_date` for each git child. **`standards_compliance`** is included whenever the scan runs. |
| `GET` | `/api/project/<name>/context` | JSON: **`role`**, **`is_workspace_super_admin`**, **`can_read_project`**, **`can_write_project`**, **`effective_readonly`**, **`access_policy_enforced`**, **`scopes`** (named permission strings), **`scopes_source`** (`role_default` \| `member_override`), **`git_user_name`**, **`git_user_email`**, **`session_login`**, **`auth_provider`** — for aligning UI with per-repo RBAC and `git config` display names. |
| `GET` | `/api/project/<name>/stats` | Repo statistics: commits by week (90 days), contributors, extension counts, `tracked_files`, `commits_total`, and when available **`tracked_lines_approx`** (approximate newline count in tracked text files, capped — same heuristic as the Projects portal). **404** if the child is missing or not a git repo. **403** `project_forbidden` when access policy is enforced and the session lacks read access. |
| `GET` | `/api/project/<name>/forge-runs` | **Forge Platform Self-Host Alpha:** lists directories under **`<child>/.forge/runs/`** (`frun_*`). Response **`ok`**, **`runs`** (each with **`forge_run_id`** and optional embedded **`forge_run`** JSON), **`runs_root`**. With query **`run_id=<frun_…>`**, returns **`bundle`**: **`forge_run`**, **`approvals`**, **`evidence_packet`**, **`local_runner_result`**, **`follow_on_sparks`**, **`events_tail`**. **404** `run_not_found` when id missing. **403** `project_forbidden` when policy enforced without read. |
| `POST` | `/api/project/<name>/forge-run-decision` | Body: JSON **`forge_run_id`**, **`state`** (`draft` \| `proposed` \| `approved` \| `rejected` \| `deferred` \| `superseded`), optional **`human_owner`**. Patches **`forge_run.json`** under **`.forge/runs/<id>/`** locally. **400** on invalid state or missing run. **403** without loopback / **`LENSES_ALLOW_ACTIONS`** or without project write per policy (same gate class as other mutating POSTs). |
| `GET` | `/api/project/<name>/repo-workflow` | JSON: **`repo`** row for that project (same shape as **`/api/repo-workflow/overview`** repos entry) or **`repo`: null** if no fixture; **`hints`**. **403** `project_forbidden` when policy enforced and the session cannot read the project. Uses workspace scan + **`repo-workflow.json`** / demo seed. |
| `GET` | `/api/project/<name>/branching` | JSON: resolved Branch Steward policy (**source**, model, trunk, team profile, promotion guardrails), current local branch from scan, normalized branch + PR structure grouped by lane/category, branch protection rows, and Branch Steward recommendations for common task intents. **403** `project_forbidden` when policy enforced and the session cannot read the project. |
| `GET` | `/api/project/<name>/quality` | JSON: **`quality_summary`** (open defects, failed gates, latest suite runs, **`release_quality`**), **`gate_evaluations`**, scoped **`test_runs`**, **`defects`**, **`coverage_summaries`**, **`flaky_test_signals`**, **`run_comparisons`**. **403** `project_forbidden` when enforced. Same fixture as **`/api/quality/overview`**, filtered by project. |
| `GET` | `/api/project/<name>/devsecops` | JSON: **`security_summary`** (**`risk_score`**, **`security_release_gate`**, repo rollup), **`policy_check_evaluations`**, scoped findings / vulns / secrets / exceptions / controls / SBOM / provenance / **`rollups`**. **403** `project_forbidden` when enforced. Same source as **`/api/devsecops/overview`**, filtered by **`project`**. |
| `GET` | `/api/chart-data/overview` | JSON bundle for client-side charts on **`/overview/charts-api`**: daily commits, LoC bars, donut, compliance scores, extension heatmap (same inputs as the overview SSR charts). Requires a normal workspace scan. |
| `GET` | `/api/project/<name>/chart-data` | JSON bundle for **`/projects/<name>/charts-api`**: weekly/daily activity, contributors, extensions, compliance, submodule SVG fragment, etc. **404** if the child is missing or not a git repo. **403** when policy enforced and the session lacks read access. |
| `POST` | `/api/project/<name>/git` | Body: JSON `{"action":"fetch"\|"pull"\|"status"}`. Runs `git` in the resolved project directory with a fixed allowlist. Response JSON: `ok`, `stdout`, `stderr`, `exit_code`, optional `error`. When **`lenses-access.json`** is active (`bootstrap_completed`), requires a signed-in user with **write** access to the project and respects **read-only** checkouts (**403** `auth_required` or `project_forbidden`). |
| `POST` | `/api/toolset/run` | Body: JSON `{"script":"<basename>.sh"}`. Runs **`/bin/bash <workspace_root>/<script>`** with cwd set to **`workspace_root`** when the file exists and the basename is allowlisted. **400** if the name is invalid or missing. Response JSON: `ok`, `stdout`, `stderr`, `exit_code`, optional `error`. **403** from non-loopback unless **`LENSES_ALLOW_GIT_ACTIONS=1`** (same policy as project git actions). **Not** GitHub-session gated (unlike **`/api/actions/run`**). |
| `GET` | `/api/sticker-board?board_id=<id>` | Merged board JSON for one board: **`version`** (2), **`board_storage`** `local` \| `shared`, **`template`**, **`columns`**, **`stickers`** (optional **`owner_login`** per sticker; **`scope`** `local` \| `shared` when `board_storage` is `shared`). Includes **`board_acl`** (`owner_login`, `editors`, `viewers`) when the board exists in the registry. **`403`** `sticker_board_forbidden` when the session cannot view the board. **`400`** if `board_id` is missing or invalid. **`404`** if the id is not in the registry or data files are missing. Legacy **`version`: 1** payloads (after migration) are normalized. If shared but the server cannot resolve **expected GitHub login**, response may include **`shared_board_login_required`: true** and empty stickers (UI should warn). |
| `POST` | `/api/sticker-board?board_id=<id>` | Body: same merged shape as GET (board **version 3** adds optional sticker **`impact`** / **`effort`** (1–5), **`source_node_id`**, **`source_kind`**, plus **`session_template`**, **`workshop_phase`**, **`prefill_applied`**); omit **`board_acl`** on POST. **403** when the user cannot edit the board. **Local** boards: **`shared_sticker_on_local_board`** if any sticker has `scope: shared`. **Shared** boards: require resolved login or **`400`** `shared_board_login_required`. Split-save to per-board repo + overlay + marker paths under **`sticker-boards/<id>.*`**. Loopback / **`LENSES_ALLOW_GIT_ACTIONS=1`** (same as git POST). |
| `GET` | `/api/sticker-board-registry` | JSON: **`version`**, **`projects`** (map project slug → list of board rows with optional **`owner_login`**, **`editors`**, **`viewers`**, **`preview_mtime`**), **`validation_issues`**, **`shared_login_configured`**, **`workspace_projects`**. When access policy is enforced, boards the session may not view are omitted (**`access_enforced`: true**). |
| `POST` | `/api/sticker-board-registry` | Body: JSON **`{"action":"create"|"rename"|"delete"|"assign"|"acl"|"repair_registry", …}`** (or **`payload`** object). **create**: `project`, `label`, `storage`, optional **`session_template`** (`roadmap_session`, `product_map_workshop`, …), optional **`prefill`** (default true for product map), optional **`wbs_p`** / **`roadmap_p`**; returns **`board_id`**. **repair_registry**: drops orphan registry rows and fixes storage flags. **acl**: `board_id`, optional **`owner_login`**, **`editors`**, **`viewers`** (requires board ACL permission). **rename** / **delete** / **assign**: require sticker edit rights. Loopback / **`LENSES_ALLOW_GIT_ACTIONS=1`**. |
| `GET` | `/api/auth/status` | `expected_login`, `expected_configured`, `session_login`, `session_ok`, **`access_policy_enforced`**, **`workspace_super_admin`**, **`auth_provider`** (`github` \| `oidc`), **`oidc_configured`** (issuer/client present), `sites_with_allowlisted_actions`, `action_keys_by_site`. |
| `GET` | `/api/access/policy` | Full **`lenses-access.json`** for workspace **super admins** only (**403** otherwise). |
| `POST` | `/api/access/set-member` | Body: JSON **`project`**, **`login`**, **`role`** (`viewer` \| `member` \| `discipline_power_user`), optional **`disciplines`**, optional **`scopes`** (string array — overrides role-derived scopes when valid), or **`action":"remove"`** with **`project`** and **`login`**. Super admins may assign any role; discipline power users only **`viewer`** / **`member`** within their discipline scope. Appends a **`data_change`** row to **`.lenses-local/governance-audit.jsonl`** on success. Loopback / **`LENSES_ALLOW_ACTIONS=1`** (same as auth). |
| `POST` | `/api/auth/github` | Body: JSON `{"token":"<github_pat>"}`. Validates the token with GitHub. **First sign-in** creates **`<workspace>/.lenses-local/lenses-access.json`** with **`super_admins`** set to that login. Later sign-ins require membership in the policy (or super admin). Sets **HttpOnly** session cookie `lenses_session`. Still requires **expected GitHub login** to be configured (registry / single **`.lenses-repo/`** / `gh`) so shared assets have a canonical path. Loopback-only unless `LENSES_ALLOW_ACTIONS=1`. |
| `POST` | `/api/auth/logout` | Clears session cookie and server-side session record. |
| `POST` | `/api/actions/run` | Body: JSON `{"site":"<child_name>","action":"<key>"}`. Requires a valid session, **write** access to that workspace child per access policy, and allowlisted `registry["actions"][site][action]`. Loopback-only unless `LENSES_ALLOW_ACTIONS=1`. Returns `ok`, `stdout`, `stderr`, `exit_code`. |

### Git actions security

- By default, **POST** is allowed only from **loopback** (`127.0.0.1`, `::1`, and IPv4-mapped `::ffff:127.0.0.1`).
- To allow from other interfaces when the server is bound to a LAN IP, set **`LENSES_ALLOW_GIT_ACTIONS=1`** (understand the risk: anyone who can reach the port can trigger `git fetch` / `git pull` / `git status` in your workspace trees, and can trigger **workspace-root shell scripts** via **`POST /api/toolset/run`**).

The process uses **no shell** for git: arguments are fixed lists (`git -C <repo> …`).

### Local search index

- **Storage:** **`<workspace>/.lenses-local/lenses-search.sqlite`** (FTS5). Ignored by git via **`.lenses-local/`**.
- **Indexed by reindex:** static **`.html` / `.htm` / `.md`** under the same directory **`/local-site/`** uses: optional **`firebase.json` → `hosting.public`**, otherwise the first existing among **`website/`**, **`public/`**, **`dist/`**; plus **`lenses-docs/`** in the forge-lenses repo (served as **`/docs/…`**). No Firebase account or CLI.
- **Headings:** **`h1`–`h6`** plain text (HTML) and Markdown **`#`–`######`** lines are indexed in a dedicated FTS column (searchable with the body).
- **Inbound links:** after indexing, internal **`a[href]`** (and Markdown links) resolving to **`/local-site/…`** or **`/docs/…`** increment a per-document **reference count** used in ranking (pages linked from many indexed files sort earlier, all else equal).
- **Schema upgrades:** if the on-disk DB predates the headings / indegree schema, the server **drops and recreates** the FTS and indegree tables on connect (re-run reindex to refill).
- **Not indexed from disk:** text that exists only after JavaScript runs in the browser. Use **`POST /api/search/ingest`** from a bookmarklet or the site under preview to push **`document.body.innerText`** (or similar) for those views.
- **Env:** **`LENSES_SEARCH_MAX_MB`** — max file size per source file (default **8** MiB).

### Toolset runs

- **`POST /api/toolset/run`** uses **`/bin/bash`** with a **single resolved path** under **`workspace_root`**; only **`*.sh`** basenames matching a strict pattern are accepted (no directories, no `..`).

### GitHub session and allowlisted actions

- **Expected GitHub login** (for **shared sticker paths** under **`.lenses-repo/<login>/`**) is resolved at server startup: `registry["github_login"]`, else a **single** subdirectory under **`<workspace>/.lenses-repo/`**, else `gh api user` from the workspace (if available). If none match, **POST `/api/auth/github`** returns **`expected_github_login_not_configured`**.
- **Per-project RBAC** lives in **`<workspace>/.lenses-local/lenses-access.json`** (see [Registry configuration](registry-configuration.html#access-policy-rbac)). Until the first successful sign-in, that file is absent and the dashboard behaves in **legacy open** mode (no per-project enforcement). After bootstrap, users must be invited or be a **super admin**.
- Sessions are stored under **`<workspace>/.lenses-local/lenses-sessions.json`** (created as needed). The **PAT is never stored**; only a random session id in an HttpOnly cookie.
- **Allowlisted actions** come from **`registry["actions"]`** (see [Registry configuration](registry-configuration.html)). There is **no free-form shell**; each entry is `argv` + `cwd_relative` under the workspace root.
- **Git remote ACLs** (GitHub org / repo permissions) are separate: anyone who can clone a repo that contains **`.lenses-repo/`** data can read that JSON offline. Lenses enforces policy only in this HTTP server.

## Security notes

- Paths are constrained: WBS viewer rejects `..` and paths outside `workspace_root`. Roadmap routes reject `..`, require a `docs` segment in the resolved path, and allow only files named **`ROADMAP.md`**.
- `/local-site/` serves files from each repo’s static output directory (same resolution as search: **`firebase.json`** **`hosting.public`** if present and valid, else **`website/`**, **`public/`**, or **`dist/`**).
- `/projects/<name>` and project APIs resolve **only** immediate child directory names allowed by `scan_workspace` (respecting `ignore_paths`).
- Without `LENSES_ALLOW_GIT_ACTIONS`, the server only **reads** the filesystem on GET (except auth/actions POST and **session file** writes for sign-in as above). **Sticker board POST** and **sticker-board-registry POST** also require loopback or `LENSES_ALLOW_GIT_ACTIONS=1` and may write **`.lenses-local/`** and, in shared mode, **`.lenses-repo/<login>/`** (last-write-wins; no locking in v1).

## Roadmap date editor (Initial / Target)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/roadmap-dates` | JSON body: `{"rel_path": "<workspace-relative docs/.../ROADMAP.md>", "updates": [{"epic_id": "M1E1", "initial_start": "YYYY-MM-DD", ...}]}` — patches epic rows in the optional date table. Same network policy as sticker saves: loopback or `LENSES_ALLOW_GIT_ACTIONS=1`; when team RBAC is enforced, requires session + `can_write_project` for the workspace child that owns the file. |

`GET /api/timeline-context` includes **`editor_html`**: the kitchensink **roadmap date editor** fragment (without inline script); Lenses Studio loads `/__ks/js/roadmap-dates.js` and calls `ForgeRoadmapDates.init(container)`.

## SDLC Copilot (grounded orchestration assistant)

Feature flag **`LENSES_EXPERIMENTAL_SDLC_COPILOT`** — on by default; set to **`0`** / **`false`** / **`no`** / **`off`** to disable. Same network boundary as LLM chat: **loopback** or **`LENSES_ALLOW_ACTIONS=1`**.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/sdlc-copilot/enabled` | JSON **`{ "ok", "enabled" }`** — whether the copilot package is active. |
| `GET` | `/api/sdlc-copilot/chat-stream` | **SSE**/stream continuation for copilot chats (same policy as **`POST /api/sdlc-copilot/chat`**). Query parameters mirror the synchronous chat envelope Studio uses (`provider`, **`message`** / continuation token, **`model`** hints). Intended for Forge Studio. |
| `POST` | `/api/sdlc-copilot/chat-async` | Starts an asynchronous copilot chat job (returns **`202`** + **`job_id`** semantics) so Studio can poll or stream later. Shares audit + grounding rules with **`chat`**. Requires loopback or **`LENSES_ALLOW_ACTIONS=1`**. |
| `POST` | `/api/sdlc-copilot/chat` | Body: **`provider`**, **`message`**, optional **`model`**, **`refine`**, **`tool_mode`** (`read_only` \| `propose_writes`), **`route`** (Studio route name for audit), optional **`project_slug`**, **`entity_id`**, **`scope_site`** / **`repo`**, optional **`studio_chat_mode`** (`threads` \| `linear`) so the model knows when Chat is in Threads vs linear mode. Returns the same fields as **`/api/llm/chat`** plus **`citations`**, **`audit_id`**, **`grounding_truncated`**, **`write_proposals`**, and **`turn_reflection`** (answered / agent_note / suggested_follow_up / adjust_context; heuristic by default). Appends one line per turn to **`.lenses-local/sdlc-copilot-audit.jsonl`**. Optional second-pass JSON: set **`LENSES_COPILOT_LLM_TURN_REFLECTION=1`** to merge an LLM classifier (same provider; extra latency/tokens). **`propose_writes`** requires GitHub session with **`can_write_project`** for **`project_slug`** when RBAC is enforced (or workspace super_admin). |
| `POST` | `/api/sdlc-copilot/topic-archive` | Body: **`topic_id`**, **`started_at_iso`**, **`ended_at_iso`**, **`route`**, optional **`project_slug`**, **`turns`** (list of `{role, text_excerpt, usage?}`), **`tags`**, **`title`**, **`summary`**, optional **`totals`** (e.g. token sums, **`dwell_approx_sec`**). Appends **`.lenses-local/copilot-topics.jsonl`** and writes **`.lenses-local/copilot-discussions/<date>_<route>.md`** when possible. |
| `POST` | `/api/sdlc-copilot/commit-proposal` | Body: **`proposal_id`**, **`confirm`: true** — exports one persisted proposal to **`.lenses-local/copilot-exports/<timestamp>_<tool>_<id>.md`** and removes the staging file under **`.lenses-local/copilot-proposals/`**. Appends a **`commit_proposal`** row to the audit log. Same permission gate as propose-writes. **400** if not confirmed; **404** if proposal missing or expired (~48h); **403** if forbidden. |

## Governance, SSO (OIDC), and connector health (Sprint 10)

**RBAC scopes** — Named strings in **`lenses/governance/scopes.py`** (`workspace.*`, `project.*`, `environment.read`, `release.*`, `admin.*`). **`GET /api/governance/scopes`** returns the signed-in user’s effective scopes (requires session when policy is enforced).

**Governance audit** — Append-only **`.lenses-local/governance-audit.jsonl`**: kinds **`data_change`**, **`approval`**, **`ai_action`**, **`connector_sync`**. **`GET /api/governance/audit`** — **`events[]`**, optional **`limit`** — **workspace super admins only** (**403** otherwise).

**OIDC** — Optional env: **`LENSES_PUBLIC_ORIGIN`**, **`LENSES_OIDC_ISSUER`**, **`LENSES_OIDC_CLIENT_ID`**, optional **`LENSES_OIDC_CLIENT_SECRET`**, **`LENSES_OIDC_REDIRECT_PATH`** (default **`/api/auth/oidc/callback`**), **`LENSES_OIDC_SCOPES`**. Values may also live in **`<workspace>/.lenses-local/lenses-oidc.env`**. Login/callback are allowed from any client IP when issuer + client id are configured (HTTPS stickerboard guests); loopback-only otherwise.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/auth/oidc/status` | JSON **`configured`**, **`issuer`**, **`client_id_set`**, **`redirect_uri`** (absolute when origin known). |
| `GET` | `/api/auth/oidc/login` | **302** to provider authorize URL (PKCE). **503** if not configured. |
| `GET` | `/api/auth/oidc/callback` | Exchanges code, creates session with **`auth_provider`**: **`oidc`**, **302** to **`/studio/`**. |
| `GET` | `/api/governance/scopes` | JSON **`ok`**, **`scopes`**, **`login`**, **`access_policy_enforced`**. **401** if enforced and no session. |
| `GET` | `/api/governance/audit` | JSON **`ok`**, **`events`** (most recent first). Super admin only. |
| `GET` | `/api/connectors/health` | JSON **`ok`**, per-domain **`delivery`**, **`repo_workflow`**, **`cicd`**, **`quality`**, **`devsecops`**, **`cross_team_release`**, **`ops`** — each with **`enabled`**, **`provider_kind`**, **`hints`**, summary fields. When RBAC is enforced: requires session and (**super admin** or membership in **any** project in the policy). |

## Methodology bridge spine (Sprint B1)

**Single store** — The physical graph remains **`ogs_entity` / `ogs_edge`** in **`lenses-orchestration.sqlite`**. Canonical methodology-neutral kinds and Forge/SDLC/PDLC labels come from the **versioned registry** at **`lenses/bridge/data/registry.v1.json`** (loaded by **`lenses.bridge.registry`**).

**Overlay** — Schema v3 adds **`bridge_spine_overlay`** (optional owner, **`freshness_at`**, **`trust_level`**, **`provenance_json`**) per **`entity_id`**.

**Feature flags** — **`LENSES_EXPERIMENTAL_BRIDGE_SPINE`** (default **on** when **`LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH`** is on; set **`0`** to disable trace/impact/gaps/projections/links). **`GET /api/bridge/registry`** and **`GET /api/bridge/registry/terms/…`** work without the bridge flag.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/bridge/enabled` | JSON **`ok`**, **`enabled`**, **`orchestration_enabled`**. |
| `GET` | `/api/bridge/registry` | JSON **`ok`**, **`registry`** (full reference object), **`validation_issues`**. |
| `GET` | `/api/bridge/registry/terms/<term>` | JSON **`term_query`**, **`neutral_entry`**, **`reverse_hits`**, **`collisions`**. |
| `GET` | `/api/bridge/trace/<entity_id>` | Like **`/api/orchestration/trace`** but nodes include **`canonical_kind`**, **`spine_meta`** (**`created_at`**, **`updated_at`**, overlay owner/freshness/trust when present), **`projections`** (neutral/forge/sdlc/pdlc), optional **`overlay`**, and **`bridge.traceability_score`** / **`bridge.root_gaps`**. Query: **`max_depth`**, **`max_nodes`**. |
| `GET` | `/api/bridge/impact/<entity_id>` | Downstream-only trace (**`direction=out`**) plus **`bridge`** metadata. |
| `GET` | `/api/bridge/provenance/<entity_id>` | Upstream-only trace (**`direction=in`**) plus **`bridge.direction`**: **`upstream_provenance`**. |
| `GET` | `/api/bridge/neighbors/<entity_id>` | Single-hop **`outgoing_edges`**, **`incoming_edges`**, and resolved **`neighbor_entities`** (with **`spine_meta`**). Query: **`max_entities`** (default **200**, max **500**). **404** if entity missing. |
| `GET` | `/api/bridge/gaps/<entity_id>` | JSON **`gaps`** (from **`compute_gaps`**) and **`traceability_score`**. **404** if entity missing. |
| `GET` | `/api/bridge/projections/<entity_id>?lens=forge\|sdlc\|pdlc\|neutral` | JSON **`projection`**, **`all_lenses`**, and **`spine_meta`**. |
| `POST` | `/api/bridge/links` | Body: **`from_id`**, **`to_id`**, **`kind`** (must be in **`EDGE_KINDS`**, including bridge kinds such as **`deploys_to`**, **`evidenced_by`**, **`blocked_by`**), optional **`payload_json`**, **`source_system`**. Loopback or **`LENSES_ALLOW_ACTIONS=1`**. |

## Methodology artifacts, evidence, and decisions (Sprint B2)

**Store** — Same **`ogs_entity` / `ogs_edge`** database. Entity kinds include **`methodology_artifact`**, **`decision_record`**, **`review_pack`**, **`assay_packet`**. Migration **v4** adds **`bridge_evidence_doc_index`** (`rel_path` → ingested markdown entity, checksum, timestamp).

**Registry** — JSON at **`lenses/bridge/data/methodology_b2_registry.json`**: Forge artifact profiles (neutral category + evidence phase), decision-type profiles (binding defaults, allowed gates, human sign-off for binding), gating hints, markdown ingest defaults.

**Feature flag** — **`LENSES_EXPERIMENTAL_METHODOLOGY_BRIDGE_B2`**: default **on** when the orchestration graph is on; set **`0`** / **`false`** to disable these routes (returns **`feature_disabled`** on GET where applicable).

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/artifacts/enabled` | JSON **`ok`**, **`enabled`**, registry version and profile keys (does not require DB). |
| `GET` | `/api/artifacts` | List **`methodology_artifact`** rows ( **`limit`**, **`offset`** ). |
| `GET` | `/api/artifacts/<id>` | Entity bundle: **`entity`**, **`outgoing_edges`**, **`incoming_edges`**, optional **`source_document`** from doc index. |
| `POST` | `/api/artifacts/import` | Body: **`paths`** (relative `*.md` list) and/or **`scan_roots`**. Upserts entities from frontmatter / path heuristics; updates **`bridge_evidence_doc_index`**. Loopback or **`LENSES_ALLOW_ACTIONS=1`**. |
| `POST` | `/api/artifacts/<id>/link` | Body: **`to_id`**, optional **`kind`** (default **`references`**). **`400`** on bad edge kind or missing entity. |
| `GET` | `/api/decisions` | List **`decision_record`** rows. |
| `POST` | `/api/decisions` | Create decision (**`decision_type`**, **`title`**, optional fields). **`201`** / **`400`**. |
| `POST` | `/api/decisions/<id>/signoff` | Body: **`signed_by`**, and **`confirm_human_signoff`: true** when profile requires it for binding ADR/Directive. **`400`** if human confirmation missing. |
| `GET` | `/api/review-packs` | List **`review_pack`** summaries. |
| `GET` | `/api/review-packs/<id>` | Aggregated view: work units, linked code, evidence, decisions, **`source_inputs`**, payload sections. |
| `POST` | `/api/review-packs` | Create **`review_pack`**. **`201`**. |
| `GET` | `/api/doc-hydration/review-packs` | Read-only list of doc-hydration review packs (hydration briefs, claim inventories, reviewer decision manifests, workcell results) scanned from `forge-platform/docs/hydration-runs/` and `workbench/doc-hydration-runs/`. |
| `GET` | `/api/doc-hydration/review-packs/<id>` | Read-only detail for one doc-hydration review pack: brief Markdown, claim inventory, hydration plans, workcell result, and the reviewer decision manifest as an approval record. |
| `GET` | `/api/doc-management/catalog` | Personas and hydration target surfaces for Studio wizard (from forge-platform governance registries). |
| `GET` | `/api/doc-management/sessions` | List Doc Management sessions (`.lenses-local/doc-management/sessions/`). |
| `GET` | `/api/doc-management/session/<id>` | Doc Management session detail including pack artifacts and reviewer manifest. |
| `GET` | `/api/doc-management/session-events?session_id=` | SSE stream of session state (workflow stages, status). |
| `POST` | `/api/doc-management` | Doc Management ops: `create_session`, `session_intake`, `session_wizard`, `session_run`, `session_decisions`, `session_promote`, `session_rollback`, `session_cancel`. |
| `GET` | `/api/assay-packets` | List **`assay_packet`** summaries. |
| `GET` | `/api/assay-packets/<id>` | View plus **`readiness_gaps`** for **`primary_release_id`**. |
| `POST` | `/api/assay-packets` | Create **`assay_packet`**. **`201`**. |
| `GET` | `/api/evidence/search?q=&limit=` | Search / browse methodology-linked entities; empty **`q`** returns recent rows. |
| `GET` | `/api/methodology/readiness?release_id=` | Heuristic **`gaps`** for a **`release`** (e.g. missing **`assay_packet`** edge, signed binding directive). |
| `GET` | `/api/methodology/records/<id>` | Generic **`get_entity_bundle`** for any OGS id (artifacts, decisions, packs). |

## Agentic bridge (Sprint B3)

**Feature flag** — **`LENSES_EXPERIMENTAL_AGENTIC_BRIDGE_B3`**: default **on** when **`LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH`** is on; set **`0`** to disable (**`feature_disabled`** on GET where applicable).

**Discovery** — Reads **`forge/forge.config.yaml`**, **`.cursor/rules/*.mdc`**, **`agents/recipes/**`** (globs in **`lenses/bridge/data/agentic_bridge_registry.json`**). Compares active **versona** disciplines to **expected** rule filenames for **drift**.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/agents/enabled` | **`ok`**, **`enabled`**, **`registry_version`** (no DB required). |
| `GET` | `/api/agents/versonas` | Forge config slice + **`versona_family` / `versona_profile`** graph rows. |
| `GET` | `/api/agents/recipes` | Registry recipes + discovered files + **`recipe`** entities. |
| `GET` | `/api/agents/tasklets` | Registry tasklets + **`tasklet`** graph rows. |
| `GET` | `/api/agents/drift` | **aligned**, active families/disciplines, **missing_expected_rules**, **orphaned_or_unmatched_rules**. |
| `GET` | `/api/agents/policies` | Default policies from registry + **`policy_rule`** entities. |
| `GET` | `/api/agents/manifests` | Live **`build_rules_manifest`** + **`rules_manifest`** graph rows. |
| `GET` | `/api/agents/runs` | Recent **`agent_run`** rows + **`pending_approval_run_ids`**. |
| `GET` | `/api/agents/runs/<id>` | Run bundle (entity + edges). |
| `GET` | `/api/agents/approvals` | **`approval_request`** rows with **`status`: pending**. |
| `POST` | `/api/agents/launch-packs` | Create **`launch_pack`**. Loopback / **`LENSES_ALLOW_ACTIONS=1`**. |
| `POST` | `/api/agents/runs` | Create **`agent_run`**; **`approval_gated`** / **`write`** spawn **`approval_request`** + **`seeks_approval`**. |
| `POST` | `/api/agents/runs/<id>/approve` | Requires **`confirm_human_approval`: true** when run is write-capable. |
| `POST` | `/api/agents/outputs/<id>/link` | Body **`artifact_id`** — link **`agent_output`** → **`methodology_artifact`** or **`evidence`**. |

## Foundry (Dark Factory Studio bridge)

**Feature flag** — **`LENSES_EXPERIMENTAL_FOUNDRY`**: default **on** when **`LENSES_EXPERIMENTAL_AGENTIC_BRIDGE_B3`** is on; set **`0`** to disable (**`feature_disabled`** on GET/POST).

**Execution** — Launches **`forge-dark-factory`** from a sibling checkout (`../forge-dark-factory`) or **`FOUNDRY_DARK_FACTORY_ROOT`**. Run records live under **`<workspace>/.lenses-local/foundry-runs/`**. Studio routes: **`/studio/foundry`**, **`/studio/foundry/runs/:runId`**.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/foundry/enabled` | **`ok`**, **`enabled`**. |
| `GET` | `/api/foundry/capabilities` | Autonomy ladder (**L1** available; **L2/L3** stub; **L4+** not planned). |
| `GET` | `/api/foundry/runs` | Recent Foundry runs (normalized phase summaries). |
| `GET` | `/api/foundry/runs/<id>` | One run + assay/proof when **`foundry_run_dir`** is set; includes **`review`** (proof markdown + per-file unified diffs) for in-UI promote review. |
| `POST` | `/api/foundry/plan` | Deterministic L1 plan (**goal**, **`target`** or **`project`**, **`level`**). |
| `POST` | `/api/foundry/intake` | Chat/fallback parser → **`goal`**, **`target`**, **`project`**, **`level`**. |
| `POST` | `/api/foundry/runs` | Start L1 draft run (**`worker`**: **`fake`** \| **`local`**, optional **`fixture`**). Loopback / **`LENSES_ALLOW_ACTIONS=1`**. **L2/L3** → **501** **`dark_factory_level_not_wired`**. |
| `POST` | `/api/foundry/runs/<id>/approve` | Requires **`confirm_human_approval`: true**; promotes changed files from DF worktree (**`promote_scope: file`**). |
| `POST` | `/api/foundry/campaigns` | **501** stub — campaigns not wired in Studio. |

| `GET` | `/api/ceremonies/enabled` | **`ok`**, **`enabled`**, **`registry_version`** (Sprint B4 ceremony bridge; no DB required). |
| `GET` | `/api/ceremonies/intents` | Neutral **C1–C6** intents (from **`registry.v1.json`**) + **`delivery_modes`** catalog. |
| `GET` | `/api/ceremonies/mappings` | Explicit **intent ↔ methodology** mapping rows (Forge ritual names and route hints). |
| `GET` | `/api/ceremonies/templates` | Registry templates + **`ceremony_template`** graph rows. |
| `GET` | `/api/ceremonies/instances` | Recent **`ceremony_instance`** entities. |
| `GET` | `/api/ceremonies/instances/<id>` | Instance bundle (template, intent, mapping entity, outputs, sign-offs, follow-ups). |
| `GET` | `/api/ceremonies/agenda/<id>` | Structured agenda (neutral framing, mapped ritual, pre-reads, delivery-mode rules). |
| `GET` | `/api/ceremonies/readiness/<id>` | Required outputs/sign-offs/inputs vs actuals (**`complete`**, **`missing_*`**). |
| `GET` | `/api/ceremonies/inspector/<id>` | Bridge inspector row: neutral intent, Forge label, delivery mode, completeness gaps. |
| `POST` | `/api/ceremonies/instances` | Create **`ceremony_instance`** (**`template_id`**, **`delivery_mode`**, **`mapping_id`**, inputs). Forge labels must match an explicit mapping. Loopback / **`LENSES_ALLOW_ACTIONS=1`**. |
| `POST` | `/api/ceremonies/instances/<id>/outputs` | Add **`ceremony_output`**; binding types require allowed delivery mode and prior human sign-off. |
| `POST` | `/api/ceremonies/instances/<id>/signoff` | Create **`signoff_record`** + **`approves`** edge (**`confirm_human_signoff`**, **`signed_by`**). |
| `GET` | `/api/handoffs/enabled` | **`ok`**, **`enabled`**, **`registry_version`** (Sprint B5 Cursor / Claude handoff bridge; requires orchestration graph). |
| `GET` | `/api/handoffs/by-work-unit?work_item_id=` | **`package_ids`** linked to the work unit (**WBS id** or **`ogs:…`** story id). |
| `GET` | `/api/handoffs/<id>` | **`handoff_package`** bundle (targets, bundles, linked work, launch pack ref). |
| `GET` | `/api/handoffs/<id>/status` | Launch pack version, target, return summary, branch/PR hints, **`partial_return`**, **`stale`**. |
| `GET` | `/api/handoffs/<id>/gaps` | Missing acceptance, missing evidence, approval status, **`return_incomplete`**. |
| `GET` | `/api/execution-sessions/<id>` | **`execution_session`** bundle (returns, manifests, build/test rows). |
| `POST` | `/api/handoffs` | Create **`handoff_package`** + child rows from JSON body. Loopback / **`LENSES_ALLOW_ACTIONS=1`**. |
| `POST` | `/api/handoffs/<id>/export?target=cursor\|claude` | Render per-target exports (**markdown**, **task**, **summary**, **manifest** JSON). |
| `POST` | `/api/handoffs/<id>/returns` | Ingest **`execution_return`** (idempotent fingerprint); links PR/files/build/review refs. Loopback / **`LENSES_ALLOW_ACTIONS=1`**. |
| `POST` | `/api/execution-sessions/<id>/reconcile` | Recompute session ↔ package linkage and gap hints after returns. Loopback / **`LENSES_ALLOW_ACTIONS=1`**. |
| `GET` | `/api/outcomes/enabled` | **`ok`**, **`enabled`**, **`registry_version`** (Sprint B6 PDLC outcome bridge; requires orchestration graph). |
| `GET` | `/api/outcomes` | List **`launch_record`** rows with **`signal_count`** and explainable **`scores`** (launch confidence, completeness, follow-on demand hints). |
| `GET` | `/api/outcomes/by-work-unit?work_item_id=` | **`launch_ids`** for launches tied to the work item via traced **releases** (**WBS id** or **`ogs:…`** story id). |
| `GET` | `/api/outcomes/<id>` | Outcome-related **entity** row; **`scores`** when **`id`** is a **`launch_record`**. |
| `GET` | `/api/outcomes/<id>/trace` | **`trace_subgraph`** from the entity (**both** directions, capped). |
| `GET` | `/api/launches` | Same list payload as **`GET /api/outcomes`** (launch-centric alias). |
| `GET` | `/api/launches/<id>` | **`launch_record`** bundle: **release**, **signals**, learning / follow-on / demand ids, **`scores`**. |
| `GET` | `/api/pdlc/bridge/<id>` | Registry **projection** for an entity (**neutral → PDLC / Forge** hints). |
| `POST` | `/api/outcomes` | Create typed outcome entity (**`kind`**: **`outcome_signal`**, **`adoption_signal`**, **`metric_snapshot`**, …). Loopback / **`LENSES_ALLOW_ACTIONS=1`**. |
| `POST` | `/api/outcomes/<id>/create-followon-ore` | Create **`followon_ore_candidate`** + **`demand_signal`** + **`proposes_followon`** / **`bridges_to_demand`** (idempotent **`idempotency_key`**). Anchor: **`learning_summary`** or **`launch_record`**. |
| `POST` | `/api/launches` | Create **`launch_record`** + **`launch_for`** → **`release_id`**. Loopback / **`LENSES_ALLOW_ACTIONS=1`**. |
| `POST` | `/api/launches/<id>/link-outcome` | **`outcome_observed`** edge from outcome entity → launch. Loopback / **`LENSES_ALLOW_ACTIONS=1`**. |

## LLM providers, Forge Fleet helpers, and core chat transports

Companion design notes live in **`design-studio-ai-setup.html`** (Forge Studio → AI pane). **`403`** from these routes usually means the client IP is outside loopback **and** **`LENSES_ALLOW_ACTIONS` / `LENSES_ALLOW_GIT_ACTIONS`** are not set appropriately.

### LLM settings and diagnostics (`/api/llm/*`)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/llm/providers` | JSON catalog of selectable providers/schemas for Studio dropdowns (static + persisted overrides). Read-only. |
| `GET` | `/api/llm/settings` | JSON snapshot of persisted provider configuration (merged workspace + **`~/.lenses-local`**). |
| `GET` | `/api/llm/usage` | Rolling usage counters (calls, tokens where available) per coarse capability. Read-only audit aid. |
| `GET` | `/api/llm/diagnostics` | Last-good/bad states, warmup flags, remediation hints surfaced in Studio banners. Read-only. |
| `GET` | `/api/llm/ollama-status` | Connectivity JSON for **`OLLAMA_BASE_URL`** probing; never blocks silently if Ollama is down. Read-only. |
| `GET` | `/api/llm/model-catalog-notifications` | Lightweight feed of catalog refresh/import events for banners. Read-only. |
| `GET` | `/api/llm/routing-preview` | Expands hypothetical routing (**query/body**) without mutating persisted settings (**read-only analyzer** used by routing UI). |
| `POST` | `/api/llm/settings` | Merge + normalize provider payloads; persists to workspace-local store. Requires loopback or **`LENSES_ALLOW_ACTIONS=1`** (classic LLM privilege gate). |
| `POST` | `/api/llm/chat` | One-shot chat completions for Classic UI + scripted clients. Mirrors provider capabilities from **`/api/sdlc-copilot/chat`** without SDLC scaffolding. Protected like other LLM POSTs. |
| `POST` | `/api/llm/provider-probe` | Validates credentials / reachable HTTP / model id for **one provider profile** (POST JSON body identifies profile). |
| `POST` | `/api/llm/routing-preview-draft` | Persistable preview for routing tables (Studio advanced flows). Shares validation with **`GET /api/llm/routing-preview`** but allows draft persistence. |
| `POST` | `/api/llm/ollama-action` | Model lifecycle helpers (warm/pull) against Ollama with fixed argv allowlists. Requires loopback or actions flag. |

### Forge Fleet probes (`/api/fleet/*`)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/fleet/settings` | Mirrors persisted Fleet YAML/JSON overlays + discovery hints for Studio (**read-only envelope** aligned with Forge LLM nodes). |
| `POST` | `/api/fleet/settings` | Persists Fleet mesh configuration (discovery interval, subnets, bearer references). Shares LLM privilege gate (loopback or **`LENSES_ALLOW_ACTIONS=1`**). Writes **`.lenses-local`** state. |
| `POST` | `/api/fleet/probe` | **`probe_health`** — returns reachability summaries for configured nodes/token holders. Read/write audit only in memory. |
| `POST` | `/api/fleet/test-fleet` | Runs bounded synthetic checks across registered Fleet nodes (**`count`** knob in POST JSON body). |
| `POST` | `/api/fleet/discover` | Triggers **`run_discovery`** (quick/subnet scans, extra hosts hints, timeout tuning). Outputs candidate nodes + confidence. |
| `POST` | `/api/fleet/node-detail` | Hydrates richer metadata about a Fleet peer (versions, GPUs, workloads) when probes succeed. |
| `POST` | `/api/fleet/connect-forge-llm` | Validates + stores pairing metadata so Studio can advertise **Forge-hosted** LLMs via Fleet. Shares LLM gates. |

## Docs-health overlays

Used by Forge Studio Docs Health rail + maintainer overlays in **`docs/maintainer/docs-health-mvp.md`**.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/docs-health/summary` | Compact JSON status for dashboards (overall green/yellow/red, outstanding counts). Read-only. |
| `GET` | `/api/docs-health/work-items` | Paginated remediation queue (titles, repos, timestamps). Read-only. |
| `GET` | `/api/docs-health/live-sessions` | Telemetry for live verification sessions keyed by Lens job ids (who is validating which repo). Requires same auth posture as Docs Health viewer. |

## Autonomy maturity (experimental)

Backed by **`lenses/autonomy_maturity/`** — deterministic per-project scoring against the blueprint autonomy maturity framework. All endpoints are feature-flagged (**`LENSES_EXPERIMENTAL_AUTONOMY_MATURITY=1`**); with the flag off, the overview and project endpoints return **404** `feature_disabled`.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/autonomy-maturity/enabled` | JSON **`enabled`** boolean so the Studio UI can hide the panel when the flag is off. Read-only. |
| `GET` | `/api/autonomy-maturity/overview` | Workspace summary: per-project **observed** level+grade claim, 0–100 **score**, and top recommendation, sorted weakest-first. Read-only. |
| `GET` | `/api/project/<name>/autonomy-maturity` | Full per-project assessment: score components (gate definition, demonstrated evidence, repeatability, operational), gate signals, Dark Factory run evidence, and gap **recommendations**. **403** `project_forbidden` when access policy is enforced without read. |

## ForgeSDLC public blog mirror endpoints

Backed by **`lenses/forgesdlc_blog*`** ingestion helpers — safe to expose read-only summaries on LAN **only when** bindings allow it.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/forgesdlc-blog` | Lightweight feed metadata (titles, summaries, CDN pointers). Read-only GET. |
| `GET` | `/api/forgesdlc-blog/content` | Hydrated article payload for Studio previews (Markdown + sanitized HTML snippets). Query parameters select slug/id. Read-only GET. |
| `POST` | `/api/forgesdlc-blog/sync` | Forces a sync pass against the ForgeSDLC blog origin (downloads + rewrite cache). Shares privileged POST policy (**loopback** or **`LENSES_ALLOW_ACTIONS=1`**). Touches **`~/.lenses-local/forgesdlc-blog*`** caches. |

## Workspace Markdown FTS manifest

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/workspace-md-index` | Manifest JSON enumerating searchable Markdown/HTML targets that power Studio “Knowledge workspace” overlays (paired with **`GET /api/search`**). Honors workspace ignore rules identical to roadmap/WBS scanners. |

## Agent runtime façade

Requests whose path **`startswith("/api/agent-runtime")`** (both **`GET`** and **`POST`**) defer to **`lenses.agent_runtime.http`**. Typical consumers: Claude/Cursor bridging inside localhost sandboxes.

- **Purpose:** multiplex agent session CRUD (`/sessions`, SSE streams, action hooks) behind the same bearer/loopback policy as other **`LENSES_ALLOW_ACTIONS`** routes.
- **Security:** rejects non-loopback clients unless **`LENSES_ALLOW_ACTIONS=1`** (mirrors **`llm_chat_allowed_from_loopback…`** guards used by Wizard refinement routes).

Keep descriptions aligned with **`lenses/agent_runtime/http.py`** if response schemas change — the façade path prefix is intentional so Studio can statically allowlist upgrades.

## Plan / workflow JSON helpers

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/wbs-management` | JSON bundle listing every detected **`WBS.md`**, rollup stats, linkage into roadmap sections; powers Studio Workspace → Plans tables. Read-only snapshot. |
| `GET` | `/api/workflow-context` | Returns serialized workflow board context (lanes, sparks, forge hints) keyed by roadmap/WBS tuples for Studio overlays. Read-only helper for `/studio/plan`. |
| `POST` | `/api/wbs/create` | Creates a scaffold **`WBS.md`** + optional starter rows inside an allowlisted workspace child. Requires **`LENSES_ALLOW_GIT_ACTIONS=1`** or loopback shell policy + **`can_write_project`** when RBAC is active. Writes git-tracked Markdown. |

## Blueprints Wizard (experimental)

Requires **`LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD`**. Sensitive POST bodies (LLM + repo creation) reuse the **`llm_chat_allowed_from_loopback_or_lenses_allow_actions`** gate unless noted.

### Capability switches and session catalogs

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/blueprints/wizard/enabled` | JSON **`{ ok, enabled }`** — whether Wizard routes are active (**server + workspace flag** parity). Read-only. |
| `GET` | `/api/blueprints/wizard/sessions` | Paginated/registry JSON listing session ids, timestamps, statuses for Studio hubs. |

### Session fetch + Cursor launch-pack download

Everything under **`/api/blueprints/wizard/session/…`** (**`GET`**) shares **`parse_session_path`** normalization.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/blueprints/wizard/session/<id>` | Hydrates persisted session JSON (wizard payload envelope + metadata). **`405`** if callers wrongly hit refinement-only tails with GET. |
| `GET` | `/api/blueprints/wizard/session/<id>/cursor-launch-pack/download/<token>` | Streams **`cursor-launch-pack-<id-prefix>.zip`** when staging token validates; consumes entry from **`.lenses-local/blueprints-wizard/cursor-launch-staging`** (see Wizard 301 guide). Shares LLM/action gate before streaming bytes. |

### Session lifecycle writes

| Method | Path | Purpose |
|--------|------|---------|
| `PUT` | `/api/blueprints/wizard/session/<id>` | `put_session` — authoritative replace/merge (`body` validated + written to disk). Shares experimental flag + normalization with GET. Requires loopback/action guard equivalent to POST refine stack. |
| `POST` | `/api/blueprints/wizard/session` | **`post_create_session`** — allocates new session scaffolding (title/purpose stubs). **`404`** when feature disabled. |
| `POST` | `/api/blueprints/wizard/telemetry` | **`post_wizard_telemetry_event`** — lightweight analytics (`step`, `elapsed_ms`, `error_hint`). Bounded JSON body (**≤16 KiB**). |

### LLM-heavy session actions (POST tails)

Unless otherwise noted, each **`POST`** path below validates session id fragments via `parse_session_*`, enforces **`experimental_blueprints_wizard_enabled()`**, requires loopback **or **`LENSES_ALLOW_ACTIONS=1`**, accepts JSON payloads **≤ 256 KiB** (**export** **`≤ 512 KiB`**), and returns structured `{ ok, error, … }` envelopes inherited from **`lenses.blueprints_wizard.api`**.

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/blueprints/wizard/session/<id>/clarify-suggest` | Deterministic clarification question merge + optional LLM embellishments (`deterministic_questions`, `use_llm`, routing knobs). |
| `POST` | `/api/blueprints/wizard/session/<id>/refine` | `post_refine_session` — iterative refinement lane (notes backlog, approvals). Known errors: `missing_notes`, `empty_model_output`, `save_failed`. |
| `POST` | `/api/blueprints/wizard/session/<id>/interpret` | `post_interpret_session` — richer interpretation summarizer with provider validation gates. Adds errors like `interpretation_parse_error`. |
| `POST` | `/api/blueprints/wizard/session/<id>/generate-artifacts` | `post_generate_artifacts` — artifact generation v2 run graph; persists telemetry via `wizard_telemetry.record_http_api_result`. |
| `POST` | `/api/blueprints/wizard/session/<id>/artifact-review` | Binding review transitions (`approve`, `reject`, `bundle` semantics) with **`approve_bundle_blocked`** guardrails when strict approval tiers fail. |
| `POST` | `/api/blueprints/wizard/session/<id>/artifact-export` | Exports zipped/markdown payloads for integrations; rejects invalid **`artifact_keys`**. |
| `POST` | `/api/blueprints/wizard/session/<id>/cursor-launch-pack/preview` | `post_cursor_launch_pack_preview` — non-mutating dry-run describing manifest closures + guardrails (**no zip** emission). |
| `POST` | `/api/blueprints/wizard/session/<id>/cursor-launch-pack/export` | `post_cursor_launch_pack_export` — stages zip + manifests for download token path above. Validates **`destination`**, **`strict_approval_failed`**, TTL via **`LENSES_CURSOR_LAUNCH_STAGING_TTL_SEC`**. |
| `POST` | `/api/blueprints/wizard/session/<id>/artifact-recheck` | `post_artifact_recheck` — post-generation QA prompts; emits telemetry similar to **`generate-artifacts`**. |
| `POST` | `/api/blueprints/wizard/session/<id>/create-repo` | `post_create_repo` — GitHub repository bootstrap with explicit confirmation + PAT surfaces (`missing_github_token`, `confirmation_required`). |

See also **`docs/blueprints/wizard-domain-model.html`** and **`docs/handbook-public/`** Wizard chapters for end-user narration (this table is maintainer-contract focused).
