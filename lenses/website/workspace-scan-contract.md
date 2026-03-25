# Workspace scan contract

`scan_workspace(workspace_root, lenses_repo_root, registry)` returns a **dict** suitable for JSON serialization and for HTML renderers.

## Top-level keys

| Key | Type | Description |
|-----|------|-------------|
| `workspace_root` | string | Absolute path of the directory being scanned (sibling repos live here). |
| `lenses_repo_root` | string | Absolute path of the **forge-lenses** checkout (for labels and static assets). |
| `resolved_at` | string | UTC ISO-8601 timestamp when the scan ran. |
| `children` | list | One entry per **immediate** subdirectory of `workspace_root` (see below). |
| `toolset` | object | `root_scripts` (names of `*.sh` in workspace root), `cursor_dir` (path if `.cursor` exists). |
| `websites` | list | Firebase hosting candidates (see below). |
| `wbs` | list | WBS file index (see below). |

## `children[]` entries

Each child corresponds to a directory **one level** under `workspace_root`:

- Skipped: names starting with `.`, or names listed in `registry["ignore_paths"]`.
- Fields: `name`, `path`, `is_git`, `git` (empty object if not a git repo).

When `is_git` is true, `git` typically includes: `top_level`, `branch`, `dirty`, `origin_url` (from `git_info` in `lenses/scan.py`).

## `websites[]` entries

For each child directory that contains a **`firebase.json`** file at its root:

- `name` — directory name  
- `path` — absolute path  
- `firebase_json` — path to `firebase.json`  

Optional display labels come from `registry["website_labels"]` (keyed by child name) in the UI.

## `wbs[]` entries

Recursive search under `workspace_root` for:

- `**/docs/requirements/WBS.md`
- `**/docs/requirements/WBS.csv`

Each entry: `repo_hint` (first path segment under workspace), `rel_path` (posix relative path from workspace root), `kind` (`md` or `csv`). Sorted by `rel_path`.

## Workspace root resolution

Implemented in `resolve_workspace_root` (`lenses/scan.py`):

1. CLI `--workspace-root` if provided  
2. Else `LENSES_WORKSPACE_ROOT` if set and an existing directory  
3. Else the parent directory of the **forge-lenses** repository root (`lenses_repo_root.parent`)

For a multi-repo layout, set **`LENSES_WORKSPACE_ROOT`** (or use **`restart-lenses.sh`** at your workspace parent) so the scan targets the folder that contains sibling projects, not only the parent of `forge-lenses`.
