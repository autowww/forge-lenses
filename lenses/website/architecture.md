# Package architecture

The **lenses** Python package lives under the **forge-lenses** repository. It is a small, synchronous stack: one HTTP server, a workspace scanner, HTML renderers, and an optional JSON registry.

## Layout

| Path | Role |
|------|------|
| `lenses/serve.py` | CLI entry (`python3 -m lenses.serve`): `ThreadingHTTPServer`, route dispatch, static `/docs` from `lenses-docs/`. |
| `lenses/scan.py` | `resolve_workspace_root`, `scan_workspace`, `workspace_state_json`; subprocess calls to `git`. |
| `lenses/render.py` | Builds HTML for dashboard pages (nav bar, overview, projects, toolset, websites, WBS list and viewer). |
| `lenses/registry.py` | Loads `workspace-registry.json` from the **forge-lenses** repo root and merges with defaults. |
| `lenses/website/*.md` | Source for **reference** handbook pages (this section); consumed by `generator/build-lenses-docs.py`. |

## Data flow

1. **Startup** — Resolve `workspace_root` (CLI, `LENSES_WORKSPACE_ROOT`, or heuristic). Load registry from **forge-lenses** checkout.
2. **Each GET** (except static `/docs`) — Run `scan_workspace(workspace_root, lenses_repo_root, registry)` and pass the resulting dict into a render function.
3. **JSON API** — `GET /api/workspace-state` returns the same structure as JSON (pretty-printed, sorted keys).

There is no server-side cache in v1: reloading a page re-runs the scan.

## Related docs

- [HTTP API and routes](http-api-and-routes.html)
- [Workspace scan contract](workspace-scan-contract.html)
- [Registry configuration](registry-configuration.html)
- [Dashboard pages](dashboard-pages.html)
