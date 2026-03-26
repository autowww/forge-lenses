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
| `/local-site/<repo>/…` | Read-only files under **`<workspace>/<repo>/<hosting.public>/`**, only for repos that have **`firebase.json`** at the repo root. Default document **`index.html`** when the path has no file segment. Path traversal (`..`) is rejected. Same origin as the dashboard so pages can be shown in an iframe under the lenses chrome (`/websites/browse?site=<repo>`). |

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
| `/projects/<name>` | Per-project dashboard: revision links, 90-day commit chart, contributors, file-type bars, optional git actions, JSON stats link. |
| `/toolset` | Card grid of workspace-root **`*.sh`** scripts (blurbs from comments) and `.cursor` presence. |
| `/toolset/<name>` | Per-script run screen: confirm, then **`POST /api/toolset/run`** for console output. |
| `/websites` | Firebase site repos: hero cards, stats, search, local preview links, copyable build/deploy commands, GitHub PAT sign-in for allowlisted actions. |
| `/websites/browse?site=<name>` | Sticky dashboard chrome + sidebar page index + **iframe** preview (`/local-site/<name>/…`). |
| `/wbs` | Index of `docs/requirements/WBS.md` and `WBS.csv` files. |
| `/wbs/view` | Query `?p=<relative-path>` — read-only viewer for one WBS file (path must stay under workspace and include `requirements` segment; file name must be `WBS.md` or `WBS.csv`). |
| `/board` | **Sticker board**: Kanban / freeform stickers; hover **edit** / **delete** on cards. **Local** mode: **`<workspace>/.lenses-local/sticker-board.json`**. **Shared** mode: **`<workspace>/.lenses-repo/<expected-login>/sticker-board.json`** (shared stickers) + **`<workspace>/.lenses-local/sticker-board-shared-local.json`** (local-only stickers on that board) + a small marker in the first file (`board_storage: shared`). |

Top navigation links to the published Handbook and Forge sites (URLs from registry defaults or overrides).

## Static documentation

| Path | Purpose |
|------|---------|
| `/docs`, `/docs/…` | Files under **`lenses-docs/`** in the forge-lenses repo (run `python3 generator/build-lenses-docs.py`). If docs are missing, some URLs return plain-text guidance. |

## JSON API

| Method | Path | Response |
|--------|------|----------|
| `GET` | `/api/workspace-state` | `application/json` — same object as produced by `scan_workspace` (see [Workspace scan contract](workspace-scan-contract.html)). |
| `GET` | `/api/workspace-state?git_extended=1` | Same shape, with `git` objects including `head_short`, `head_full`, `commit_subject`, `commit_date` for each git child. |
| `GET` | `/api/project/<name>/stats` | Repo statistics: commits by week (90 days), contributors, extension counts, `tracked_files`, `commits_total`, and when available **`tracked_lines_approx`** (approximate newline count in tracked text files, capped — same heuristic as the Projects portal). **404** if the child is missing or not a git repo. |
| `POST` | `/api/project/<name>/git` | Body: JSON `{"action":"fetch"\|"pull"\|"status"}`. Runs `git` in the resolved project directory with a fixed allowlist. Response JSON: `ok`, `stdout`, `stderr`, `exit_code`, optional `error`. |
| `POST` | `/api/toolset/run` | Body: JSON `{"script":"<basename>.sh"}`. Runs **`/bin/bash <workspace_root>/<script>`** with cwd set to **`workspace_root`** when the file exists and the basename is allowlisted. **400** if the name is invalid or missing. Response JSON: `ok`, `stdout`, `stderr`, `exit_code`, optional `error`. **403** from non-loopback unless **`LENSES_ALLOW_GIT_ACTIONS=1`** (same policy as project git actions). **Not** GitHub-session gated (unlike **`/api/actions/run`**). |
| `GET` | `/api/sticker-board` | Merged board JSON: **`version`** (2), **`board_storage`** `local` \| `shared`, **`template`**, **`columns`**, **`stickers`** (each sticker may include **`scope`** `local` \| `shared` when `board_storage` is `shared`). Legacy **`version`: 1** files are treated as local boards. If the marker says shared but the server cannot resolve **expected GitHub login**, response may include **`shared_board_login_required`: true** and empty stickers (UI should warn). |
| `POST` | `/api/sticker-board` | Body: same merged shape as GET. **Local** boards: **`shared_sticker_on_local_board`** if any sticker has `scope: shared`. **Shared** boards: require resolved login or **`400`** `shared_board_login_required`. Split-save to repo + overlay + marker. Loopback / **`LENSES_ALLOW_GIT_ACTIONS=1`** (same as git POST). |
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

- Paths are constrained: WBS viewer rejects `..` and paths outside `workspace_root`.
- `/local-site/` only serves under each Firebase repo’s configured **`hosting.public`** directory.
- `/projects/<name>` and project APIs resolve **only** immediate child directory names allowed by `scan_workspace` (respecting `ignore_paths`).
- Without `LENSES_ALLOW_GIT_ACTIONS`, the server only **reads** the filesystem on GET (except auth/actions POST and **session file** writes for sign-in as above). **Sticker board POST** also requires loopback or `LENSES_ALLOW_GIT_ACTIONS=1` and may write **`.lenses-local/`** and, in shared mode, **`.lenses-repo/<login>/`** (last-write-wins; no locking in v1).
