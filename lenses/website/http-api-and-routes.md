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
| `/local-site/<repo>/…` | (1) Paths **`tutorial`** or **`tutorial/…`** are served from **`<workspace>/<repo>/tutorial/`** for **any** workspace child (Firebase or not): default **`index.html`** when the path is exactly **`tutorial`**, reject `..`, only regular files. (2) Paths **`tutorials`** or **`tutorials/…`** are served from **`<repo>/tutorials/`** when that directory exists with **`index.html`**, else **`<repo>/lenses/tutorials/`**, else **`<repo>/website/tutorials/`** (e.g. forgesdlc). If still not found, the same path is tried under **`<hosting.public>`** when **`firebase.json`** exists. Same **`..`** rules. (3) All other paths are served from **`<workspace>/<repo>/<hosting.public>/`** only when **`firebase.json`** exists (default **`index.html`** when the path is empty, reject `..`). Same origin as the dashboard so pages can be shown in an iframe under the lenses chrome (`/websites/browse?site=<repo>`). |

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
| `/wbs` | Index of `docs/requirements/WBS.md` and `WBS.csv` files. |
| `/wbs/view` | Query `?p=<relative-path>` — read-only viewer for one WBS file (path must stay under workspace and include `requirements` segment; file name must be `WBS.md` or `WBS.csv`). |
| `/plan` | **Forge plan** lens: pick repository, **WBS** (`docs/requirements/WBS.md`), optional **ROADMAP.md**; default **Plan** view (milestones/epics/stories + story hub with Today / Charge, Ember, Versona). **Source** tab: iframe roadmap section preview. Query `?repo=&wbs_p=&roadmap_p=&id=` hydrates selection. |
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
| `GET` | `/api/story-hub?id=<WBS_ID>&wbs_p=<rel>&repo=<repo_hint>&roadmap_p=<rel optional>` | JSON: story or task **definition**, Today (Charge), Ember excerpts, Versona sessions, journal hits, provenance links. **400** if `id` or `wbs_p` missing. |
| `GET` | `/api/workspace-state` | `application/json` — scan object from `scan_workspace` plus **`standards_compliance_note`** and per-child **`standards_compliance`** (heuristic agentic/standards score) after server enrichment (see [Workspace scan contract](workspace-scan-contract.html)). |
| `GET` | `/api/workspace-state?git_extended=1` | Same shape, with `git` objects including `head_short`, `head_full`, `commit_subject`, `commit_date` for each git child. **`standards_compliance`** is included whenever the scan runs. |
| `GET` | `/api/project/<name>/stats` | Repo statistics: commits by week (90 days), contributors, extension counts, `tracked_files`, `commits_total`, and when available **`tracked_lines_approx`** (approximate newline count in tracked text files, capped — same heuristic as the Projects portal). **404** if the child is missing or not a git repo. |
| `GET` | `/api/chart-data/overview` | JSON bundle for client-side charts on **`/overview/charts-api`**: daily commits, LoC bars, donut, compliance scores, extension heatmap (same inputs as the overview SSR charts). Requires a normal workspace scan. |
| `GET` | `/api/project/<name>/chart-data` | JSON bundle for **`/projects/<name>/charts-api`**: weekly/daily activity, contributors, extensions, compliance, submodule SVG fragment, etc. **404** if the child is missing or not a git repo. |
| `POST` | `/api/project/<name>/git` | Body: JSON `{"action":"fetch"\|"pull"\|"status"}`. Runs `git` in the resolved project directory with a fixed allowlist. Response JSON: `ok`, `stdout`, `stderr`, `exit_code`, optional `error`. |
| `POST` | `/api/toolset/run` | Body: JSON `{"script":"<basename>.sh"}`. Runs **`/bin/bash <workspace_root>/<script>`** with cwd set to **`workspace_root`** when the file exists and the basename is allowlisted. **400** if the name is invalid or missing. Response JSON: `ok`, `stdout`, `stderr`, `exit_code`, optional `error`. **403** from non-loopback unless **`LENSES_ALLOW_GIT_ACTIONS=1`** (same policy as project git actions). **Not** GitHub-session gated (unlike **`/api/actions/run`**). |
| `GET` | `/api/sticker-board?board_id=<id>` | Merged board JSON for one board: **`version`** (2), **`board_storage`** `local` \| `shared`, **`template`**, **`columns`**, **`stickers`** (each sticker may include **`scope`** `local` \| `shared` when `board_storage` is `shared`). **`400`** if `board_id` is missing or invalid. **`404`** if the id is not in the registry or data files are missing. Legacy **`version`: 1** payloads (after migration) are normalized. If shared but the server cannot resolve **expected GitHub login**, response may include **`shared_board_login_required`: true** and empty stickers (UI should warn). |
| `POST` | `/api/sticker-board?board_id=<id>` | Body: same merged shape as GET (do not rely on `board_id` in the body). **Local** boards: **`shared_sticker_on_local_board`** if any sticker has `scope: shared`. **Shared** boards: require resolved login or **`400`** `shared_board_login_required`. Split-save to per-board repo + overlay + marker paths under **`sticker-boards/<id>.*`**. Loopback / **`LENSES_ALLOW_GIT_ACTIONS=1`** (same as git POST). |
| `GET` | `/api/sticker-board-registry` | JSON: **`version`**, **`projects`** (map project slug → list of `{id, label, storage}`; entries may include **`preview_mtime`** when a hub thumbnail PNG exists), **`validation_issues`**, **`shared_login_configured`**, **`workspace_projects`** (child folder names). |
| `POST` | `/api/sticker-board-registry` | Body: JSON **`{"action":"create"|"rename"|"delete"|"assign", "payload":{…}}`** (or flat fields with **`action`**). **create**: `project` (child name or **`_unassigned`**), `label`, `storage` `local`\|`shared`. **rename**: `board_id`, `label`. **delete**: `board_id` (removes registry entry and local files; **does not** delete shared JSON under **`.lenses-repo/`**). **assign**: `board_id`, `project`. Loopback / **`LENSES_ALLOW_GIT_ACTIONS=1`**. |
| `GET` | `/api/auth/status` | `expected_login`, `expected_configured`, `session_login`, `session_ok`, `sites_with_allowlisted_actions`, `action_keys_by_site` (map of site → action name list). |
| `POST` | `/api/auth/github` | Body: JSON `{"token":"<github_pat>"}`. Validates the token with GitHub; if `login` matches **expected** workspace login, sets **HttpOnly** session cookie `lenses_session`. Loopback-only unless `LENSES_ALLOW_ACTIONS=1`. |
| `POST` | `/api/auth/logout` | Clears session cookie and server-side session record. |
| `POST` | `/api/actions/run` | Body: JSON `{"site":"<child_name>","action":"<key>"}`. Requires valid session and allowlisted `registry["actions"][site][action]` (`argv` + `cwd_relative`). Loopback-only unless `LENSES_ALLOW_ACTIONS=1`. Returns `ok`, `stdout`, `stderr`, `exit_code`. |

### Git actions security

- By default, **POST** is allowed only from **loopback** (`127.0.0.1`, `::1`, and IPv4-mapped `::ffff:127.0.0.1`).
- To allow from other interfaces when the server is bound to a LAN IP, set **`LENSES_ALLOW_GIT_ACTIONS=1`** (understand the risk: anyone who can reach the port can trigger `git fetch` / `git pull` / `git status` in your workspace trees, and can trigger **workspace-root shell scripts** via **`POST /api/toolset/run`**).

The process uses **no shell** for git: arguments are fixed lists (`git -C <repo> …`).

### Toolset runs

- **`POST /api/toolset/run`** uses **`/bin/bash`** with a **single resolved path** under **`workspace_root`**; only **`*.sh`** basenames matching a strict pattern are accepted (no directories, no `..`).

### GitHub session and allowlisted actions

- **Expected GitHub login** is resolved at server startup: `registry["github_login"]`, else a **single** subdirectory under **`<workspace>/.lenses-repo/`**, else `gh api user` from the workspace (if available). If none match, **POST `/api/auth/github`** returns an error and **POST `/api/actions/run`** stays disabled for lack of expected user.
- Sessions are stored under **`<workspace>/.lenses-local/lenses-sessions.json`** (created as needed). The **PAT is never stored**; only a random session id in an HttpOnly cookie.
- **Allowlisted actions** come from **`registry["actions"]`** (see [Registry configuration](registry-configuration.html)). There is **no free-form shell**; each entry is `argv` + `cwd_relative` under the workspace root.

## Security notes

- Paths are constrained: WBS viewer rejects `..` and paths outside `workspace_root`. Roadmap routes reject `..`, require a `docs` segment in the resolved path, and allow only files named **`ROADMAP.md`**.
- `/local-site/` only serves under each Firebase repo’s configured **`hosting.public`** directory.
- `/projects/<name>` and project APIs resolve **only** immediate child directory names allowed by `scan_workspace` (respecting `ignore_paths`).
- Without `LENSES_ALLOW_GIT_ACTIONS`, the server only **reads** the filesystem on GET (except auth/actions POST and **session file** writes for sign-in as above). **Sticker board POST** and **sticker-board-registry POST** also require loopback or `LENSES_ALLOW_GIT_ACTIONS=1` and may write **`.lenses-local/`** and, in shared mode, **`.lenses-repo/<login>/`** (last-write-wins; no locking in v1).
