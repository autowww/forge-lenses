# Workspace scan contract

`scan_workspace(workspace_root, lenses_repo_root, registry, *, git_extended=False)` returns a **dict** suitable for JSON serialization and for HTML renderers.

## Top-level keys

| Key | Type | Description |
|-----|------|-------------|
| `workspace_root` | string | Absolute path of the directory being scanned (sibling repos live here). |
| `lenses_repo_root` | string | Absolute path of the **forge-lenses** checkout (for labels and static assets). |
| `resolved_at` | string | UTC ISO-8601 timestamp when the scan ran. |
| `standards_compliance_note` | string | Short disclaimer for heuristic **agentic / standards** scoring (not an audit). |
| `children` | list | One entry per **immediate** subdirectory of `workspace_root` (see below). |
| `toolset` | object | `root_scripts` (names of `*.sh` in workspace root), `script_cards` (list of `{ name, blurb }` from leading `#` comments), `cursor_dir` (path if `.cursor` exists). |
| `websites` | list | Firebase hosting candidates (see below). |
| `wbs` | list | WBS file index (see below). |
| `roadmaps` | list | `ROADMAP.md` file index under `docs/` (see below). |

## `toolset` object

- **`root_scripts`** — sorted basenames of `*.sh` files directly under `workspace_root` (stable list for counts and APIs).
- **`script_cards`** — same scripts as `{ "name", "blurb" }`; `blurb` is a short single-line summary from the script’s leading `#` comment block after the shebang (empty if none).
- **`cursor_dir`** — absolute path to `.cursor` when present, else empty string.

## `children[]` entries

Each child corresponds to a directory **one level** under `workspace_root`:

- Skipped: names starting with `.`, or names listed in `registry["ignore_paths"]`.
- Fields: `name`, `path`, `is_git`, `git` (empty object if not a git repo), **`standards_compliance`** (object — see below).

### `children[].standards_compliance`

Present after server-side enrichment (same shape for HTML and JSON). Heuristic proxy for [agentic coding standards](https://blueprints.forgesdlc.com/sdlc--methodologies-agentic-coding-standards.html) themes — **not** a compliance audit.

| Key | Type | Description |
|-----|------|-------------|
| `score` | int | 0–100 weighted score from applicable checks. |
| `tier` | string | `good` (≥85), `partial` (≥55), or `minimal`. |
| `summary` | string | One-line human summary. |
| `is_git` | bool | Whether the path is a git work tree. |
| `checks` | list | Objects: `id`, `label`, `theme`, `weight`, `status` (`pass` / `warn` / `na` / `skipped`), `detail`, `suggestion` (often empty), **`rationale`** (why the signal matters for agentic SDLC), **`cursor_fix_prompt`** (curated copy-paste prompt for Cursor; may be empty when not applicable). |
| `suggestions` | list of strings | Action hints from checks in **warn** state. |

When `is_git` is true, `git` includes at least: `top_level`, `branch`, `dirty`, `origin_url` (from `git_info` in `lenses/scan.py`).

If **`git_extended=True`** (used for HTML dashboards and for **`GET /api/workspace-state?git_extended=1`**), `git` also includes:

- `head_short`, `head_full` — from `git rev-parse`
- `commit_unix` — integer Unix time (seconds) for **HEAD** from `git log -1` (`%ct`), or **0** if missing
- `commit_subject`, `commit_date` — from the same `git log -1` line (ISO timestamp for `commit_date`)

When **`git_extended=False`**, `head_*` and `commit_*` string fields are **empty strings** and **`commit_unix`** is **0** for a stable JSON shape; consumers that need values should use `git_extended=1` or read the project dashboard HTML path.

## `websites[]` entries

For each child directory that contains a **`firebase.json`** file at its root:

- `name` — directory name  
- `path` — absolute path  
- `firebase_json` — path to `firebase.json`  
- `hosting_public` — string directory under the repo used for Firebase Hosting **`public`** (from `firebase.json`, default **`website`**)  
- `firebase_site_id` — optional Firebase **`site`** id from `firebase.json` (may be empty)  
- `preview_base` — URL prefix for the local static server, e.g. **`/local-site/<name>/`**  
- `pages` — bounded list of objects: `path` (posix relative to `hosting_public`), `title`, `h1`, `label` (best display string), from a shallow scan of HTML files  
- `html_total` — number of `*.html` files discovered under `hosting_public` (capped during discovery)  
- `html_indexed` — number of files represented in `pages`  
- `index_html_mtime` — last modified time of `hosting_public/index.html` as a Unix timestamp, or **`null`** if missing  
- `suggested_commands` — map of **`build`** / **`deploy`** shell one-liners for copy-paste (heuristic from generator layout)  

Optional display labels come from `registry["website_labels"]` (keyed by child name) in the UI.

## `wbs[]` entries

Recursive search under `workspace_root` for:

- `**/docs/requirements/WBS.md`
- `**/docs/requirements/WBS.csv`

Each entry: `repo_hint` (first path segment under workspace), `rel_path` (posix relative path from workspace root), `kind` (`md` or `csv`). Sorted by `rel_path`.

## `roadmaps[]` entries

Recursive search under `workspace_root` for:

- `**/ROADMAP.md` where every matching path includes a `docs` path segment (e.g. `forgesdlc/docs/product/ROADMAP.md`, `blueprints/docs/ROADMAP.md`).

Each entry: `repo_hint` (first path segment under workspace), `rel_path` (posix relative path from workspace root), `kind` (always `md`). Sorted by `rel_path`.

## `forge_hints[]` entries

For the workspace root and each top-level child directory, when **any** of the following exist, an entry is added:

- `forge/charge.md`
- `ember-logs/` (directory)
- `forge-logs/versona/` (directory)
- `forge/journal/` (directory)

Each entry: `repo_hint` (first path segment, or empty string when the match is at workspace root), `has_charge`, `has_ember_logs`, `has_versona`, `has_journal` (booleans).

## Workspace root resolution

Implemented in `resolve_workspace_root` (`lenses/scan.py`):

1. CLI `--workspace-root` if provided  
2. Else `LENSES_WORKSPACE_ROOT` if set and an existing directory  
3. Else the parent directory of the **forge-lenses** repository root (`lenses_repo_root.parent`)

For a multi-repo layout, set **`LENSES_WORKSPACE_ROOT`** (or use **`restart-lenses.sh`** at your workspace parent) so the scan targets the folder that contains sibling projects, not only the parent of `forge-lenses`.

## Path helper

`resolve_workspace_child_dir(workspace_root, name, registry)` returns the resolved **`Path`** for a single child **name** if it is allowed, else **`None`**. Used by **`/projects/<name>`** and project APIs.

## Overview metrics file (not part of `scan_workspace`)

The **Overview** page also reads **`lenses-docs/overview-metrics.json`** from the forge-lenses checkout (served under **`/docs/overview-metrics.json`**). That file is **generated** by **`generator/collect-lenses-overview-data.py`** after the docs build (see **`scripts/run-lenses.sh`**). It is **not** returned by **`scan_workspace`**; it combines Cursor filesystem signals with optional **`overview_metrics_manual`** from the merged registry. See [Dashboard pages — Overview](dashboard-pages.md) and [Registry configuration](registry-configuration.md).
