# Package architecture

The **lenses** Python package lives under the **forge-lenses** repository. It is a small, synchronous stack: one HTTP server, a workspace scanner, HTML renderers, and an optional JSON registry.

## Layout

| Path | Role |
|------|------|
| `lenses/serve.py` | CLI entry (`python3 -m lenses`): `ThreadingHTTPServer`, route dispatch, static `/docs`, **`/__ks/`** kitchensink assets, **`/__lenses/js/`** dashboard JS, project APIs, sticker board API, POST git, **`/toolset/…`** and **`POST /api/toolset/run`**, **`/roadmaps`**, **`/roadmaps/preview`**, **`/roadmaps/summary`**, **`GET /api/roadmap-outline`**. |
| `lenses/scan.py` | `resolve_workspace_root`, `resolve_workspace_child_dir`, `scan_workspace`, `workspace_state_json`; subprocess calls to `git`; toolset **`script_cards`** / comment blurbs for root **`*.sh`**; indexes **`roadmaps`** (`**/docs/**/ROADMAP.md`) alongside WBS. |
| `lenses/toolset_actions.py` | Allowlisted workspace-root shell script execution for **`POST /api/toolset/run`** (bash, fixed path, no user shell). |
| `lenses/render.py` | HTML for dashboard pages; **`showcase_page`** shell when kitchensink is present, else fallback layout. Roadmaps UI: **`page_roadmaps`**, preview document builder, summary fragment. |
| `lenses/roadmap_outline.py` | Parse `ROADMAP.md` into sections, GFM tables → HTML, **`extract_chart_metrics`** for summaries. |
| `lenses/roadmap_charts.py` | Inline SVG bars / status donut / horizon badges; optional KS **`/__ks/assets/svg/`** template thumbnails. |
| `lenses/ks_layout.py` | Kitchensink path checks and `lenses_showcase_page` wrapper. |
| `lenses/git_urls.py` | Map `origin` to HTTPS repo / commit URLs (GitHub, GitLab-style hosts). |
| `lenses/project_stats.py` | Git log / `ls-files` aggregations and SVG chart helpers for project dashboards. |
| `lenses/standards_compliance.py` | Heuristic **agentic / coding-standards compliance** per repo (filesystem + optional git message sample); **`enrich_workspace_with_standards`** mutates scan state; SVG score bars for Overview. |
| `lenses/git_actions.py` | Allowlisted `git` subprocess actions for the POST API; shared loopback policy helper for sticker board writes. |
| `lenses/sticker_board.py` | Load/save/validate sticker boards: **local** file under **`.lenses-local/`**; **shared** split across **`.lenses-repo/<login>/`** and a local overlay + marker. |
| `lenses/registry.py` | Loads `workspace-registry.json` from the **forge-lenses** repo root and merges with defaults. |
| `lenses/tutorial_index.py` | **`list_child_handbooks`**, **`tutorial/`** and **`tutorials/`** URL resolution for **`/local-site/<repo>/…`**. |
| `lenses/website/*.md` | Source for **reference** handbook pages (this section); consumed by `generator/build-lenses-docs.py` with `docs/index.md` as the `/docs/` hub. |
| `lenses/fa-tutorial-md/*.md` | Source for **tutorial** handbook pages; built by **forge-autodoc** (`./build-fa-tutorials.sh`) into **`lenses/tutorials/`**, optionally synced to repo-root **`tutorial/`**. **`tutorial_index.py`** also discovers **`tutorials/`**, **`lenses/tutorials/`**, and **`website/tutorials/`** (e.g. forgesdlc) so **`/tutorials`** (global index) and **`/local-site/<repo>/tutorials/…`** work without rsync. |

## Data flow

1. **Startup** — Resolve `workspace_root` (CLI, `LENSES_WORKSPACE_ROOT`, or heuristic). Load registry from **forge-lenses** checkout.
2. **Each GET** (except static `/docs`, `/__ks/…`, and project stats JSON) — Run `scan_workspace` then **`enrich_workspace_with_standards`** so each child includes **`standards_compliance`** (score, tier, checks, suggestions). HTML uses `git_extended=True`; **`GET /api/workspace-state`** uses `git_extended` only when `?git_extended=1` is passed (compliance is always attached when the scan runs).
3. **JSON API** — `GET /api/workspace-state` returns the scan dict; `GET /api/roadmap-outline?p=…` returns section metadata for one roadmap file; `GET /api/project/<name>/stats` returns repo statistics; `POST /api/project/<name>/git` runs allowlisted git commands (loopback-gated by default); `POST /api/toolset/run` runs an allowlisted workspace-root **`*.sh`** (same loopback gate as git by default); `GET`/`POST /api/sticker-board?board_id=…` reads/writes one board (local or shared split under **`sticker-boards/<id>.*`**); `GET`/`POST /api/sticker-board-registry` lists and mutates the board registry (POST loopback-gated like git by default).

There is no server-side cache in v1: reloading a page re-runs the scan.

## Extending the dashboard (SSR-first)

The dashboard is **server-rendered**: each relevant `GET` builds HTML in Python (mainly `render.py`) and returns a document. Prefer that model for new screens.

- **New routes** — Dispatch in `serve.py` (`do_GET` / `do_POST`); implement the page body as a `page_*` helper (or split module) next to existing dashboard pages; wrap with the kitchensink `showcase_page` shell when present (`ks_layout.py`).
- **JSON** — Use `/api/…` when a feature needs async updates (sticker board, git, toolset). That complements SSR; it does not mean turning the whole UI into a client-rendered SPA.
- **Client JS** — Keep interactive snippets in `lenses/static/js/`; avoid moving the entire page shell to client-only rendering unless there is a strong reason.
- **Privileged actions** — New `POST` handlers should follow the same session, allowlist, and loopback patterns as `git_actions` / sticker board.

Edits to `lenses/**/*.py` require **restarting** the `python3 -m lenses` process to load new code; a browser reload alone is not enough for handler or render changes.

## Related docs

- [HTTP API and routes](http-api-and-routes.html)
- [Workspace scan contract](workspace-scan-contract.html)
- [Registry configuration](registry-configuration.html)
- [Dashboard pages](dashboard-pages.html)
