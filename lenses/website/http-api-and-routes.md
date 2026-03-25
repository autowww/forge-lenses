# HTTP API and routes

The server binds to **127.0.0.1:8080** by default (`--host`, `--port` override).

## HTML dashboard

| Path | Purpose |
|------|---------|
| `/` | Overview: workspace root, child directories, quick stats. |
| `/projects` | Git-focused view of children (branch, dirty, `origin`). |
| `/toolset` | Shell scripts (`*.sh`) at workspace root and `.cursor` presence. |
| `/websites` | Repos under the workspace that contain `firebase.json`. |
| `/wbs` | Index of `docs/requirements/WBS.md` and `WBS.csv` files. |
| `/wbs/view` | Query `?p=<relative-path>` — read-only viewer for one WBS file (path must stay under workspace and include `requirements` segment; file name must be `WBS.md` or `WBS.csv`). |

Top navigation links to the published Handbook and Forge sites (URLs from registry defaults or overrides).

## Static documentation

| Path | Purpose |
|------|---------|
| `/docs`, `/docs/…` | Files under **`lenses-docs/`** in the forge-lenses repo (run `python3 generator/build-lenses-docs.py`). If docs are missing, some URLs return plain-text guidance. |

## JSON API

| Method | Path | Response |
|--------|------|----------|
| `GET` | `/api/workspace-state` | `application/json` — same object as produced by `scan_workspace` (see [Workspace scan contract](workspace-scan-contract.html)). |

## Security notes

- Paths are constrained: WBS viewer rejects `..` and paths outside `workspace_root`.
- The process only reads the filesystem; it does not execute workspace code.
