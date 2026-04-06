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

Single-page route catalog (surfaces and access modes): [Interface pages](interface-pages.html).

| Path | Purpose |
|------|---------|
| `/` | Overview: workspace root, child directories, quick stats. |
| `/projects` | Portal: card grid with README previews, git badges, links to each project dashboard. |
| `/tutorials` | Index of every detected forge-autodoc handbook per workspace child (**`tutorial/index.html`**, **`tutorials/index.html`**, **`lenses/tutorials/index.html`**, or **`website/tutorials/index.html`** via **`list_child_handbooks`**), with **Open tutorial** / **Open engineer handbook** links under **`/local-site/<name>/…`** and **Project dashboard**. |
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

| Method | Path | Response |
|--------|------|----------|
| `GET` | `/api/roadmap-outline?p=<relative-path>` | `application/json` — `{ "doc_title", "sections": [ { "id", "level", "title" } ] }` for one `ROADMAP.md`. **400** if `p` missing; **404** if path not allowed or missing. |
| `GET` | `/api/plan-spine?wbs_p=<rel>&repo=<repo_hint>&roadmap_p=<rel optional>` | JSON: joined **plan** tree (from WBS), optional roadmap metrics, Charge rows, Versona session count, forge path hints. **400** if `wbs_p` missing; **404** if WBS path not allowed. |
| `GET` | `/api/story-hub?id=<WBS_ID>&wbs_p=<rel>&repo=<repo_hint>&roadmap_p=<rel optional>` | JSON: story or task **definition**; **today_charge**, **decision_log_ember**, **discipline_sessions_versona**, **journal** (legacy fields); **`story_view`** when the work item resolves to a story (or a spark’s parent story): structured **slots** (WBS column → problem, acceptance, notes, etc.), **milestone_outcome**, **phase_affinity**, **roadmap_hits** (sections mentioning the story id), **product_context** (work-graph doc links), **execution** (WBS sparks + charge rows), **decisions** (Ember scans, graph-linked decisions/sessions, Versona list), **sources** (WBS / Charge / journal). Optional **`roadmap_ctx`** (metrics) when **`roadmap_p`** is set. **400** if `id` or `wbs_p` missing. |
| `GET` | `/api/today-charge?wbs_p=<rel>&repo=<repo_hint>&roadmap_p=<rel optional>` | JSON: **Today (Charge)** operational view — **`spark_rows`** (full list with **`flags`**, **`breadcrumb`**, **`plan_href`**), **`sections`** ( **`active`**, **`blocked`**, **`banked`**, **`recently_resolved`**, **`pending_versona`** ), **`charge`** (frontmatter hat/date, **`view_href`**), **`phase_prefixes`**, **`notes`**. Joins **`forge/charge.md`** (Active Sparks + Blockers + Banking tables) with WBS and Versona session index. **400** if `wbs_p` missing; **404** if WBS path not allowed. |
| `GET` | `/api/workspace-state` | `application/json` — scan object from `scan_workspace` plus **`standards_compliance_note`** and per-child **`standards_compliance`** (heuristic agentic/standards score) after server enrichment (see [Workspace scan contract](workspace-scan-contract.html)). |
| `GET` | `/api/tutorials-index` | JSON **`{ "ok", "rows" }`** — forge-autodoc handbook rows per workspace child (same discovery as **`/tutorials`**: **`list_child_handbooks`**). Each row: **`child_name`**, **`kind`**, **`label`**, **`local_site_rel`**, **`preview_url`**. |
| `GET` | `/api/timeline-context?repo=&wbs_p=&roadmap_p=` | JSON for **Timeline** (Classic **`/timeline`** and Lenses Studio): **`repo_hints`**, **`wbs_options`**, **`roadmap_options`**, **`selected`**, **`gantt_html`**, **`metrics_html`**, **`roadmap_source_href`**, **`workspace_projects`**, **`current_project`**. |
| `GET` | `/api/wbs-file?p=<relative-path>` | JSON **`{ "ok", "text", "kind": "md"|"csv", "rel_path" }`** for one WBS file under the same rules as **`/wbs/view`**. |
| `GET` | `/api/workspace-md-file?p=<relative-path>` | JSON **`{ "ok", "text", "rel_path" }`** for allowlisted Forge markdown (same rules as **`/workspace-md/view`**). |
| `GET` | `/api/roadmap-section?p=<roadmap-rel>&section=<id>` | JSON **`{ "ok", "html", "rel_path", "section" }`** — HTML fragment for one roadmap section (Studio and other clients). |
| `GET` | `/api/search?q=<query>&limit=<n>&offset=<n>&site=<repo>&repo=<repo>` | JSON: **`ok`**, **`query`**, **`hits`**, **`total`** (match count for the query), **`limit`**, **`offset`**. Each hit: **`path_key`**, **`url`**, **`title`**, **`source`**, **`snippet`**, **`ref_count`** (inbound internal links from indexed HTML/Markdown), **`score`** (BM25-style rank with indegree adjustment; lower is better). **`site`** and **`repo`** are aliases: when set, matches under **`/local-site/<value>/`** are ranked ahead of others. Ranking uses **FTS5 BM25** with higher weight on **title** and **headings** than **body**. Empty **`q`** returns empty **`hits`** and **`total`: 0**. **`limit`** defaults to **25**, max **100**; **`offset`** defaults to **0**. |
| `GET` | `/api/search/reindex?redirect=/search` | Same side effect as **POST** (starts background reindex when allowed). With **`redirect`**, responds **303** to that path with **`reindex=started`** or **`reindex=busy`** in the query string (browser-friendly). Without **`redirect`**, JSON **202** / **409** / **403** like **POST**. |
| `POST` | `/api/search/reindex` | **202** when a background reindex starts: **`ok`**, **`status`**: `"started"`. Indexes HTML/Markdown under each workspace child’s **static output directory** (see **Local search index** — no Firebase CLI required) and under **`lenses-docs/`** in the forge-lenses checkout. **409** if a reindex is already running. **403** from non-loopback unless **`LENSES_ALLOW_ACTIONS=1`**. |
| `POST` | `/api/search/ingest` | Body: JSON **`{"url":"<canonical url>","title":"<short>","text":"<plain text>"}`** ( **`text`** max ~512 KiB). Upserts one **`ingested`** document for dynamic/client-rendered views. **400** if **`url`** or **`text`** missing. **403** same as reindex. |
| `GET` | `/api/workspace-state?git_extended=1` | Same shape, with `git` objects including `head_short`, `head_full`, `commit_subject`, `commit_date` for each git child. **`standards_compliance`** is included whenever the scan runs. |
| `GET` | `/api/project/<name>/context` | JSON: **`role`**, **`is_workspace_super_admin`**, **`can_read_project`**, **`can_write_project`**, **`effective_readonly`**, **`access_policy_enforced`**, **`git_user_name`**, **`git_user_email`**, **`session_login`** — for aligning UI with per-repo RBAC and `git config` display names. |
| `GET` | `/api/project/<name>/stats` | Repo statistics: commits by week (90 days), contributors, extension counts, `tracked_files`, `commits_total`, and when available **`tracked_lines_approx`** (approximate newline count in tracked text files, capped — same heuristic as the Projects portal). **404** if the child is missing or not a git repo. **403** `project_forbidden` when access policy is enforced and the session lacks read access. |
| `GET` | `/api/chart-data/overview` | JSON bundle for client-side charts on **`/overview/charts-api`**: daily commits, LoC bars, donut, compliance scores, extension heatmap (same inputs as the overview SSR charts). Requires a normal workspace scan. |
| `GET` | `/api/project/<name>/chart-data` | JSON bundle for **`/projects/<name>/charts-api`**: weekly/daily activity, contributors, extensions, compliance, submodule SVG fragment, etc. **404** if the child is missing or not a git repo. **403** when policy enforced and the session lacks read access. |
| `POST` | `/api/project/<name>/git` | Body: JSON `{"action":"fetch"\|"pull"\|"status"}`. Runs `git` in the resolved project directory with a fixed allowlist. Response JSON: `ok`, `stdout`, `stderr`, `exit_code`, optional `error`. When **`lenses-access.json`** is active (`bootstrap_completed`), requires a signed-in user with **write** access to the project and respects **read-only** checkouts (**403** `auth_required` or `project_forbidden`). |
| `POST` | `/api/toolset/run` | Body: JSON `{"script":"<basename>.sh"}`. Runs **`/bin/bash <workspace_root>/<script>`** with cwd set to **`workspace_root`** when the file exists and the basename is allowlisted. **400** if the name is invalid or missing. Response JSON: `ok`, `stdout`, `stderr`, `exit_code`, optional `error`. **403** from non-loopback unless **`LENSES_ALLOW_GIT_ACTIONS=1`** (same policy as project git actions). **Not** GitHub-session gated (unlike **`/api/actions/run`**). |
| `GET` | `/api/sticker-board?board_id=<id>` | Merged board JSON for one board: **`version`** (2), **`board_storage`** `local` \| `shared`, **`template`**, **`columns`**, **`stickers`** (optional **`owner_login`** per sticker; **`scope`** `local` \| `shared` when `board_storage` is `shared`). Includes **`board_acl`** (`owner_login`, `editors`, `viewers`) when the board exists in the registry. **`403`** `sticker_board_forbidden` when the session cannot view the board. **`400`** if `board_id` is missing or invalid. **`404`** if the id is not in the registry or data files are missing. Legacy **`version`: 1** payloads (after migration) are normalized. If shared but the server cannot resolve **expected GitHub login**, response may include **`shared_board_login_required`: true** and empty stickers (UI should warn). |
| `POST` | `/api/sticker-board?board_id=<id>` | Body: same merged shape as GET (do not rely on `board_id` in the body); omit **`board_acl`** on POST. **403** when the user cannot edit the board. **Local** boards: **`shared_sticker_on_local_board`** if any sticker has `scope: shared`. **Shared** boards: require resolved login or **`400`** `shared_board_login_required`. Split-save to per-board repo + overlay + marker paths under **`sticker-boards/<id>.*`**. Loopback / **`LENSES_ALLOW_GIT_ACTIONS=1`** (same as git POST). |
| `GET` | `/api/sticker-board-registry` | JSON: **`version`**, **`projects`** (map project slug → list of board rows with optional **`owner_login`**, **`editors`**, **`viewers`**, **`preview_mtime`**), **`validation_issues`**, **`shared_login_configured`**, **`workspace_projects`**. When access policy is enforced, boards the session may not view are omitted (**`access_enforced`: true**). |
| `POST` | `/api/sticker-board-registry` | Body: JSON **`{"action":"create"|"rename"|"delete"|"assign"|"acl", …}`** (or **`payload`** object). **create**: `project`, `label`, `storage`, optional **`editors`**, **`viewers`**; server sets **`owner_login`** from the signed-in user. **acl**: `board_id`, optional **`owner_login`**, **`editors`**, **`viewers`** (requires board ACL permission). **rename** / **delete** / **assign**: require sticker edit rights. Loopback / **`LENSES_ALLOW_GIT_ACTIONS=1`**. |
| `GET` | `/api/auth/status` | `expected_login`, `expected_configured`, `session_login`, `session_ok`, **`access_policy_enforced`**, **`workspace_super_admin`**, `sites_with_allowlisted_actions`, `action_keys_by_site`. |
| `GET` | `/api/access/policy` | Full **`lenses-access.json`** for workspace **super admins** only (**403** otherwise). |
| `POST` | `/api/access/set-member` | Body: JSON **`project`**, **`login`**, **`role`** (`viewer` \| `member` \| `discipline_power_user`), optional **`disciplines`**, or **`action":"remove"`** with **`project`** and **`login`**. Super admins may assign any role; discipline power users only **`viewer`** / **`member`** within their discipline scope. Loopback / **`LENSES_ALLOW_ACTIONS=1`** (same as auth). |
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

## Blueprints Wizard (experimental)

Requires **`LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD`**. LLM routes also require loopback or **`LENSES_ALLOW_ACTIONS=1`** (same policy as Chat).

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/blueprints/wizard/session/<id>/clarify-suggest` | JSON: `deterministic_questions`, `use_llm`, optional `provider` / `model` / `refine` — returns merged clarification question list (optional LLM extras). |
