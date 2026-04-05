# Lenses interface (plan-aware model)

Lenses is **one Python backend** (`python3 -m lenses`) serving JSON APIs and HTML. The **commercial product** is described as **four plan-aware shells** (Free, Personal, Team, Enterprise) over that backend—not as a flat list of routes. Screen-level detail lives in [Dashboard pages](dashboard-pages.html). APIs and bind rules are in [HTTP API and routes](http-api-and-routes.html). Forge plan artifacts and tabs are in [Forge plan UI map (roadmap → evidence)](ui-map-workflow.html).

## Dual-surface architecture: Studio first, Classic in sync

Two **UI surfaces** share the same server and APIs:

- **Classic Lenses** — Server-rendered HTML from `lenses/render.py` (routes under `/`). Default for many flows and **`./scripts/run-lenses.sh`**. Not deprecated.
- **Lenses Studio** — React SPA under **`/studio/`** (Vite build in `lenses/static/studio/`). Preferred for **new UI** first (Electron-first).

**Intentional duplication:** User-visible features added in Studio should be **ported to Classic** so both surfaces stay equivalent (same capabilities; presentation may differ). Implement **Studio first**, then **duplicate in Classic** in the same release when feasible, unless explicitly scoped as a Studio-only experiment with a note or ADR.

## Shared information architecture

These rules apply across plans and surfaces:

- **Search** evolves toward a **global omnibox / assistant** on every plan. Today: **`/search`** and the search APIs.
- **Knowledge cluster** — Tutorials, Lenses reference docs (**`/docs`**), WBS, Workspace Markdown viewers are one mental group (not necessarily one URL yet).
- **Charts-only pages** — **`/overview/charts-api`**, **`/projects/<name>/charts-api`**, and Studio **`/studio/overview/charts`**, **`/studio/projects/<name>/charts`**: target **tabs or embedded views**, not primary nav destinations.
- **Roadmap** — **`/roadmaps/summary`**, **`/roadmaps/preview`**, **`/roadmaps/timeline`**: **share/embed surfaces** (iframes, deep links), not the main app chrome.
- **Strategy** — **`/projects/<name>/strategy`** stays a **project sub-view**, not top-level nav in the target IA.

### Lenses Studio (Enterprise) — unified IA (Flow / Artifacts)

The Studio SPA (**`/studio/`**) uses the **same routes** for both lenses; only grouping and labels change. **Flow** is the default **workspace lens** (cookie **`workspace_lens`**, with legacy **`nav_mode`** read on first visit). **Header row:** brand, **Search**, **Workspace Lens** switcher, stubs for **Notifications** and **Workspace** switcher until backends exist, and **Auth**. **Top row:** primary areas (Flow: **Workspace** → Plans → Delivery → Projects → Sites → **Knowledge**; Artifacts: adds **Roadmaps** and **Boards** as top-level tabs). **Below the top nav:** enterprise **context bar** (scope, time horizon, compare, saved view / filters placeholders), **executive KPI strip**, **attention stream** (exception-style items from workspace scan), then main content + **evidence rail** — see [`docs/studio-flow-shell-mvp-scope.md`](../../docs/studio-flow-shell-mvp-scope.md). **Left column:** section-specific destinations (including classic **`/roadmaps/*`** links where the SPA has no page). **Discovery** and a real activity/inbox are **out of scope** for this v1 chrome refresh.

## Four plan shells — primary nav, landing, notes

Product IA for hosted SKUs; the open-source server may expose all routes—**entitlements** are in [Product tiers](#product-tiers-commercial-packaging).

| App | Primary nav | Default landing page | Notes |
|-----|-------------|----------------------|-------|
| **Free** | Home, Projects, Knowledge | Setup + workspace health + first insights | Optimize for first 3 minutes and first “aha” |
| **Personal** | Home, Projects, Plan, Release, Knowledge | “My work today” | **Release** = Websites + Toolset (publish/run tooling) |
| **Team** | Home, Work, Plan, Sites, Knowledge, Admin | Team health + at-risk work + recent changes | **Work** = boards, activity, assignments |
| **Enterprise** | Portfolio, Programs, Projects, Releases, Knowledge, Risk, Admin | Executive summary + portfolio risk | Governance and cross-workspace visibility first-class |

**Mapping notes**

- **Knowledge** appears on every tier and aligns with the Knowledge cluster above.
- **Release** (Personal) vs **Releases** (Enterprise): singular = combined Websites + Toolset; plural = portfolio-level surface—different scope, same word family.
- **Sites** (Team) maps to today’s **`/websites`** (including browse).
- **Portfolio**, **Programs**, **Risk** (Enterprise) are **target surfaces** for portfolio governance—may be documentation-first until dedicated views and APIs exist.

### Route / feature mapping (today’s URLs)

| Product concept | Typical routes today |
|-----------------|---------------------|
| Home | `/` |
| Projects | `/projects`, `/projects/<name>` |
| Plan | `/plan`, `/timeline` |
| Release (Personal) | `/websites`, `/websites/browse`, `/toolset`, `/toolset/<name>` |
| Work (Team) | `/board`, `/board/<id>` (boards; activity/assignments evolve with product) |
| Knowledge | `/tutorials`, `/docs`, `/wbs`, `/wbs/view`, `/workspace-md/view` |
| Sites (Team) | `/websites`, `/websites/browse` |
| Admin | Team workspace RBAC and policy (see [Registry configuration](registry-configuration.html)); not a single URL yet |

## Product tiers (commercial packaging)

These tiers describe **what to ship and where to gate** in a hosted or licensed Lenses product. They are **orthogonal** to [UI surfaces](#ui-surfaces-classic-lenses-vs-lenses-studio): **Lenses Studio** (**`/studio/`**) is a **technical shell**, not the same as the **Enterprise** subscription tier in this table.

Rough alignment with [workspace access](#workspace-access-personal-vs-team): **Free** and **Personal** map to solo / open or personal workspaces; **Team** and **Enterprise** assume **team workspace** (RBAC, shared boards, collaboration) as the default posture.

### Free

| | |
|--|--|
| **Core promise** | “Understand this workspace locally.” |
| **Best fit** | Evaluator, OSS maintainer, student |
| **Include by default** | Overview, Projects, Project Dashboard, Strategy, Tutorials, Search, Docs, Websites browse, basic Plan, 1 personal board, limited AI Q&A |
| **Gate / monetize here** | No shared workspace or RBAC, no advanced automations, no shared boards, no org analytics, limited AI credits |

### Personal

| | |
|--|--|
| **Core promise** | “Run your own delivery cockpit.” |
| **Best fit** | Solo builder, consultant, founder |
| **Include by default** | Everything in Free, plus full Plan, Boards, Toolset, personal Websites actions, custom home, exports, richer AI summaries and workflows |
| **Gate / monetize here** | No multi-user collaboration, no team admin, no org analytics, no SSO, SCIM, or audit |

### Team

| | |
|--|--|
| **Core promise** | “Coordinate delivery in one shared workspace.” |
| **Best fit** | Startup, product, or engineering team |
| **Include by default** | Everything in Personal, plus team workspace bootstrap and RBAC, shared boards, activity and comments, shared roadmaps, team analytics, integrations, viewer and commenter seats, shared automations |
| **Gate / monetize here** | No multi-workspace portfolio, no enterprise governance pack, no isolated hosting |

### Enterprise

| | |
|--|--|
| **Core promise** | “Govern portfolio delivery at scale.” |
| **Best fit** | Large org, regulated org, multi-team org |
| **Include by default** | Everything in Team, plus portfolio views, cross-workspace timeline, SSO and SAML, SCIM, audit logs, policy controls, data residency, advanced approvals, isolated hosting and networking, SLA, onboarding |
| **Gate / monetize here** | Optional pooled AI credits and professional services |

## UI surfaces (Classic Lenses vs Lenses Studio)

Independent from workspace RBAC (below). The same Python server serves both. Which surface is default in a hosted SKU is a **packaging** decision across [product tiers](#product-tiers-commercial-packaging).

| Surface | What it is |
|---------|------------|
| **Classic Lenses** | Server-rendered HTML from `lenses/render.py` — full dashboard (nav, Overview, Projects, Plan, Websites, docs, and routes in the [backend URL map](#backend-url-map-reference)). Default when you open the server in a browser or use **`./scripts/run-lenses.sh`**. |
| **Lenses Studio** | React SPA under **`/studio/`** (Vite build in `lenses/static/studio/`): client-side routing to native views (Overview, Projects, Plan, Timeline, boards, search, etc.) backed by the **same JSON API** as Classic. Charts on **`/studio/overview/charts`** and **`/studio/projects/<name>/charts`** use **`forge-data-charts.js`** (same contract as Classic charts-api pages). Unknown paths under **`/studio/…`** fall back to **`index.html`**. See [ADR 001: Lenses Studio shell](adr-001-lenses-studio-shell.html) and the repo **README** § *Lenses Studio*. |

**Electron:** set **`LENSES_STUDIO_UI=1`** (or legacy **`LENSES_ENTERPRISE_UI=1`**) when launching the desktop app to open **`http://127.0.0.1:<port>/studio/`** instead of **`/`** (`desktop/main.js`).

**Legacy URLs:** **`/enterprise`** and **`/enterprise/…`** respond with **302** to **`/studio/`** and **`/studio/…`** respectively.

## Workspace access (personal vs team)

This axis is about **who may read or write** which projects — not Classic vs Studio. **Team** and **Enterprise** [product tiers](#product-tiers-commercial-packaging) assume this mode for collaboration features; **Free** and **Personal** tiers typically stay in open or solo use unless upgraded.

| Mode | When it applies | Effect |
|------|-----------------|--------|
| **Open workspace** | No **`lenses-access.json`**, or policy exists but **`bootstrap_completed`** is not set. | RBAC is not enforced; the server behaves in **legacy open** mode for access checks. |
| **Team workspace** | After the first successful **`POST /api/auth/github`**, **`bootstrap_completed`** is true in **`<workspace>/.lenses-local/lenses-access.json`**. | Per-project **viewer / member / discipline_power_user** roles, super admins, sticker board ACL, gated project APIs, and allowlisted **Websites** actions apply. |

Details: [Registry configuration](registry-configuration.html) § Access policy (RBAC).

## Environment toggles (UI-relevant)

| Variable | Role |
|----------|------|
| **`LENSES_STUDIO_UI`** | **`1`** / **`true`**: Electron opens **`/studio/`** instead of **`/`**. |
| **`LENSES_ENTERPRISE_UI`** | Legacy alias for **`LENSES_STUDIO_UI`** (same behavior). |
| **`LENSES_WORKSPACE_ROOT`** | Directory whose **children** are scanned as workspace repos (overrides default parent-of-checkout behavior). |
| **`LENSES_ALLOW_GIT_ACTIONS`** | **`1`**: allow **`POST`** for project git actions and toolset script runs from **non-loopback** clients when the server is bound beyond localhost (security-sensitive). |
| **`LENSES_ALLOW_ACTIONS`** | **`1`**: allow GitHub auth and related **POST** from non-loopback when bound beyond localhost. |
| **`LENSES_SKIP_CURSOR_METRICS`** | **`1`**: skip reading **`~/.cursor`** on Overview (privacy / CI). |

For bind address, kitchensink assets, and search indexing, see [HTTP API and routes](http-api-and-routes.html).

### Assets and previews (supporting URLs)

Not separate “products,” but used by the UI: **`/__ks/…`** (kitchensink CSS/JS/assets), **`/__lenses/js/…`** (dashboard JS), **`/local-site/<repo>/…`** (static preview of each workspace child), **`/board-preview/<id>.png`** (sticker board thumbnails). See [HTTP API and routes](http-api-and-routes.html) § Kitchensink assets and § Local site preview.

## Backend URL map (reference)

Exact paths for engineering and deep links. Product story: [Four plan shells](#four-plan-shells--primary-nav-landing-notes) and [shared IA](#shared-information-architecture).

| Path | Purpose |
|------|---------|
| `/` | Overview: workspace root, child directories, quick stats. |
| `/enterprise` | **302** redirect to **`/studio/`** (legacy). |
| `/enterprise/…` | **302** redirect to **`/studio/…`** (legacy). |
| `/studio` | **302** redirect to **`/studio/`**. |
| `/studio/…` | Lenses Studio **React SPA** (hashed **`assets/*.js`**, **`assets/*.css`**, **`index.html`**); unknown paths serve **`index.html`** for client-side routes. Data via JSON APIs (e.g. **`GET /api/workspace-state`**). |
| `/projects` | Portal: card grid with README previews, git badges, links to each project dashboard. |
| `/tutorials` | Index of every detected forge-autodoc handbook per workspace child (**`tutorial/index.html`**, **`tutorials/index.html`**, **`lenses/tutorials/index.html`**, or **`website/tutorials/index.html`** via **`list_child_handbooks`**), with **Open tutorial** / **Open engineer handbook** links under **`/local-site/<name>/…`** and **Project dashboard**. |
| `/feature-showcase` | **Classic** scrollytelling feature showcase (split list + sticky layered visuals; vanilla JS). Complements **Lenses Studio** **`/studio/feature-showcase`**. |
| `/projects/<name>` | Per-project dashboard: revision links, 90-day commit chart, contributors, file-type bars, optional git actions, JSON stats link. |
| `/projects/<name>/charts-api` | Same metrics as the project dashboard, rendered client-side via **`forge-data-charts.js`** and **`GET /api/project/<name>/chart-data`**. The classic HTML charts remain on **`/projects/<name>`**. |
| `/projects/<name>/strategy` | Repo layout and branching: **`.gitmodules`** table, **`git submodule status`** (bounded), optional inline SVG + kitchensink template thumbnail, current branch / remote default, registry **`project_strategy`** text, optional **`LENSES-REPO-STRATEGY.md`**. Unknown second path segments under **`/projects/…`** (other than **`charts-api`**) return **404**. |
| `/overview/charts-api` | Workspace analytics (same kinds as **`/`** overview charts) via **`GET /api/chart-data/overview`**. |
| `/toolset` | Card grid of workspace-root **`*.sh`** scripts (blurbs from comments) and `.cursor` presence. |
| `/toolset/<name>` | Per-script run screen: confirm, then **`POST /api/toolset/run`** for console output. |
| `/websites` | Firebase site repos: hero cards, stats, search, local preview links, copyable build/deploy commands, GitHub PAT sign-in for allowlisted actions. |
| `/websites/browse?site=<name>` | Sticky dashboard chrome + sidebar page index + **iframe** preview (`/local-site/<name>/…`). |
| `/search` | Local full-text search. **GET** query: **`q`** (keywords), optional **`limit`** (default **25**, max **100**), **`offset`** (pagination), **`repo`** or **`site`** (workspace child name — boosts results under **`/local-site/<name>/`**). Optional **`reindex=`** after index rebuild redirects. The index is **SQLite FTS5** at **`<workspace>/.lenses-local/lenses-search.sqlite`**. Populate with **`POST /api/search/reindex`** or **GET** **`/api/search/reindex?redirect=…`**; optional **`POST /api/search/ingest`** for client-rendered page text. |
| `/wbs` | Index of `docs/requirements/WBS.md` and `WBS.csv` files. |
| `/wbs/view` | Query `?p=<relative-path>` — read-only viewer for one WBS file (path must stay under workspace and include `requirements` segment; file name must be `WBS.md` or `WBS.csv`). |
| `/plan` | **Forge plan** lens: pick repository, **WBS**, optional **ROADMAP.md**. **Plan** tab: **3-pane explorer** (work tree from **`/api/forge-work-model`**, center pane, detail rail). **Today** tab: compact operational tables from **`/api/today-charge`** (Charge + WBS + Versona), links to **`?id=`** on this page. **Story** and **Spark** selections use the center pane as the primary **story cockpit** (tabs: Definition, Product context, Execution, Decisions, Source) fed by **`/api/story-hub`**; the **Detail** rail stays minimal. Other nodes use a level-aware center and **`/api/forge-work-model?node_id=`** in the rail. Filter/search, URL `?id=` & `?tab=plan|today|source`, roadmap summary strip (collapsible). **Source** tab: iframe roadmap section preview (outline is not mixed into the work tree). |
| `/timeline` | Full-width milestone / epic **timeline** page with Plan-compatible **`repo`**, **`wbs_p`**, **`roadmap_p`** query parameters. |
| `/roadmaps` | **302 redirect** to **`/plan`** (same query string preserved for bookmarks). |
| `/roadmaps/summary` | Query `?p=<relative-path>` — HTML fragment only: charts + KS diagram thumbnails derived from tables in that roadmap (status, % complete, horizon). |
| `/roadmaps/preview` | Query `?p=<relative-path>&section=<id>` — full minimal HTML document for one section (for iframe `src`; links `/__ks/css/` for theming). |
| `/roadmaps/timeline` | Query `?p=<relative-path>` — full HTML document: **timeline** view for one **`ROADMAP.md`** (embeddable / standalone; not the same as **`/timeline`**, which is the full dashboard timeline page). |
| `/workspace-md/view` | Query `?p=<relative-path>` — read-only viewer for allowlisted Forge markdown under the workspace (`forge/charge.md`, `forge/journal/*.md`, `ember-logs/*.md`, `forge-logs/**/*.md`). |
| `/board` | **Sticker board** hub: flat list of boards with project filter, thumbnails, create / rename / delete / move between projects. Optional **`?project=<child-name>`** pre-selects the filter (same as the link from a project dashboard). |
| `/board/<board_id>` | **Sticker board editor** for one board: Kanban / freeform stickers; hover **edit** / **delete** on cards. **`?thumb=1`** — minimal chrome for PNG capture. **Local** board file: **`<workspace>/.lenses-local/sticker-boards/<board_id>.json`**. **Shared** board: **`<workspace>/.lenses-repo/<login>/sticker-boards/<board_id>.json`** + **`<workspace>/.lenses-local/sticker-boards/<board_id>-shared-local.json`** + marker **`<board_id>.marker.json`**. Registry: **`<workspace>/.lenses-local/sticker-board-registry.json`**. Legacy single-file **`sticker-board.json`** is migrated automatically on first access. |
| `/board-preview/<board_id>.png` | **PNG** thumbnail if present under **`.lenses-local/sticker-board-previews/`** and **`board_id`** is in the registry; **404** otherwise. **`Cache-Control: private, max-age=60`**. |
| `/docs`, `/docs/…` | Built reference handbook under **`lenses-docs/`** (run `python3 generator/build-lenses-docs.py`). If docs are missing, some URLs return plain-text guidance. |

Top navigation and sidebar (Classic): workspace pages (including **Tutorials** → **`/tutorials`**), **Lenses docs** (**`/docs/`**), then **Handbook** and **Forge** (URLs from registry defaults or overrides).

## See also

- [Dashboard pages](dashboard-pages.html) — narrative description of each major screen.
- [Forge plan UI map (roadmap → evidence)](ui-map-workflow.html) — artifacts, tabs, and APIs for **`/plan`**.
- [HTTP API and routes](http-api-and-routes.html) — bind safety, assets, JSON API, and POST contracts.
- **Kitchen Sink — Lenses Studio shell** (engineering guideline, source repo): `forgesdlc-kitchensink/docs/design/lenses-studio-shell.md` — Electron **`BrowserWindow`**, preload **`window.lensesElectron`**, **`/__ks/`** theme and shared CSS/JS, React **`WorkspaceLensControl`** sync; complements [ADR 001: Lenses Studio shell](adr-001-lenses-studio-shell.html) and [Forge Enterprise UI](https://github.com/autowww/forgesdlc-kitchensink/blob/main/docs/design/forge-enterprise-ui.md) on GitHub.
