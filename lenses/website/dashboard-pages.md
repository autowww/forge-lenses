# Dashboard pages

The UI is server-generated HTML from `lenses/render.py` (Bootstrap-style markup consistent with kitchensink themes used in the static handbook).

## Overview (`/`)

Shows the resolved workspace root, a summary of discovered children, and entry points into other views. Links to external Handbook and Forge sites use the registry.

## Projects (`/projects`)

Emphasizes git metadata: current branch, dirty working tree, `origin` URL when available. Useful for a multi-repo folder (e.g. `forgesdlc`, `blueprints-website`).

## Toolset (`/toolset`)

Lists executable-oriented cues at the **workspace root**: `*.sh` scripts and whether **`.cursor`** exists (rules/skills live there in many setups).

## Websites (`/websites`)

Lists repositories that contain **`firebase.json`** at the repo root — treated as Firebase Hosting projects. Labels can be overridden via `website_labels` in **`workspace-registry.json`**.

## WBS (`/wbs` and `/wbs/view`)

- **`/wbs`** — Table (or list) of all `docs/requirements/WBS.md` and `WBS.csv` files found under the workspace.  
- **`/wbs/view?p=…`** — Read-only preview of a single file; path validated so only workspace-local requirement trees are accessible.

## Docs link

The top bar **Docs** target is **`/docs/`**, which serves pre-built HTML from **`lenses-docs/`** (build with `generator/build-lenses-docs.py`).
