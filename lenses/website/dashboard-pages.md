# Dashboard pages

The UI is server-generated HTML from `lenses/render.py`. When the **kitchensink** submodule is present, pages use **`showcase_page`** from the design system (Bootstrap + `forge-theme.css` + `forgesdlc-theme.css`) with assets served from **`/__ks/`**. If the submodule is missing, the UI falls back to a compact inline-styled shell.

## Overview (`/`)

**Hero** — When kitchensink is present, the top of the page uses **`render_product_landing_hero`**: workspace path and scan time sit in the clarification line; **Browse projects** and **Lenses docs** CTAs link to **`/projects`** and **`/docs/index.html`**. Without kitchensink, a compact fallback title block is used.

**KPI row** — Same as before: counts for top-level folders, Firebase sites, WBS files, and root **`*.sh`** scripts, linking to **Projects**, **Websites**, **WBS**, and **Toolset**.

**Main column** — Each top-level child is a **repository card**: badges (clean/dirty, branch, Firebase, published site), optional long description from **`project_summaries`** in the workspace registry (else a longer **README** excerpt than on the Projects portal), approximate tracked **LoC**, and **git numstat** totals for the **last 7 days** (+additions / −deletions). Below that, an **SVG horizontal bar chart** compares **lines added (7d)** across git repos (from **`git log --numstat`**; binary/merge lines excluded).

**Right column** — **Recent commits by repository**: for each git child, up to **five** commits with **subject**, **short hash** (link to host when `origin` parses), **relative time**, and the **commit body** excerpt as context (“explanation”). The column is **sticky** on wide viewports (scrollable if tall).

**Workspace metrics** — Reads **`lenses-docs/overview-metrics.json`**, produced by **`generator/collect-lenses-overview-data.py`** (run automatically after **`generator/build-lenses-docs.py`** from **`scripts/run-lenses.sh`** and **`scripts/restart-lenses.sh`**). That file merges:

- **Cursor** — Under **`~/.cursor/projects/`**, directories matching the workspace path slug (`exact` or **`prefix`** mode via **`LENSES_CURSOR_PROJECTS_MODE`**, default **`prefix`** for meta-repos). Counts **agent transcript** **`.jsonl`** files touched in the last **7 days** (by file mtime; not wall-clock session time). Also summarizes workspace **`.cursor/`** (rule count, **`SKILL.md`** count, **`mcp.json`** presence).
- **Manual** — Optional **`overview_metrics_manual`** in **`lenses-workspace-registry.json`**: e.g. **`human_hours_week`**, **`estimated_hours_without_genai`**, **`estimated_hours_genai_potential`** (aliases: **`hours_without_genai`**, **`hours_genai_potential`**), plus **`methodology_note`**. Shown as comparison bars with an explicit note that values are **not** inferred from git/Cursor.

**Environment** — **`LENSES_SKIP_CURSOR_METRICS=1`** skips reading **`~/.cursor`** (CI/privacy). **`LENSES_WORKSPACE_ROOT`** must match the dashboard scan root so slug matching aligns.

**Publishing / Requirements** — Compact **Publishing** and **WBS** blocks remain at the bottom of the page.

Git work on Overview uses parallel subprocess calls per repo; very large workspaces may take a few seconds on first load.

## Projects (`/projects`)

Portal-style **card grid**: each top-level workspace folder is sorted by **last commit** (**`commit_unix`**, newest git repos first; non-git folders last, by name). When kitchensink is present, each card is a **topic preview trigger** (`fs-topic-preview-card`): clicking opens the project dashboard in an **in-page modal** (iframe with **`?fs-embed=1`**). Use **Open full page** in the modal toolbar to open **`/projects/<name>`** in a normal tab. Without kitchensink, cards fall back to **forge-card** links (full navigation).

Each card summarizes:

- **Clean / Dirty**, **branch**, **short revision** (git), plus **Firebase** / **Web** hints in the description line
- **Approximate LoC** (newline count in tracked text files, with per-repo caps — same idea as **`tracked_lines_approx`** on **`GET /api/project/<name>/stats`**)
- **Last update** (relative time from **HEAD** commit, same source as **`commit_unix`** / **`commit_date`**)
- A short **README.md** excerpt when available

## Project dashboard (`/projects/<name>`)

Per-repo view with:

- Links to **HTTPS repository** and **commit on host** (GitHub / GitLab) when `origin` parses cleanly
- Optional **project site** button from **`project_urls`**
- Table: tree state, branch, revision, last commit message and date, raw `origin` URL
- **README preview**
- **Stats**: SVG bar chart of commits by ISO week (90 days), contributor table, file-type share bars, total commit count
- **Git actions** (Status, Fetch, Pull `--ff-only`): POST to **`/api/project/<name>/git`** via in-page `fetch` (loopback-only unless **`LENSES_ALLOW_GIT_ACTIONS=1`**)
- Link to **`/api/project/<name>/stats`** for the same stats as JSON

## Toolset (`/toolset` and `/toolset/<script>.sh`)

**`/toolset`** — Card grid (same **forge-card** / column layout as Projects): each workspace-root **`*.sh`** file gets a card with a **Shell** badge, a short **blurb** parsed from the script’s leading `#` comments (after the shebang), and **Open run screen →** linking to **`/toolset/<url-encoded-name>`**. The **Cursor / IDE** section still shows whether **`.cursor`** exists at the workspace root.

**`/toolset/<name>`** — Run screen for one script: full comment header (up to a length cap), warning about local execution, **Run script…** (browser **confirm** first), then **`POST /api/toolset/run`**; combined **stdout** / **stderr** appear in a tall console `<pre>` (same loopback policy as project git actions unless **`LENSES_ALLOW_GIT_ACTIONS=1`**). Only basenames of **`*.sh`** files directly under the workspace root are accepted.

## Sticker board (`/board`)

**Kanban** (three columns, HTML5 drag-and-drop) or **freeform** (pointer drag on a canvas). Each sticker has **title** + **details**; the card shows a preview. **Hover** shows **edit** (pencil) and **delete** (×); double-click still opens the editor.

**Board storage:** **Local** — everything in **`<workspace_root>/.lenses-local/sticker-board.json`**. **Shared** — shared stickers and layout in **`<workspace_root>/.lenses-repo/<expected-login>/sticker-board.json`**, private stickers for that board in **`<workspace_root>/.lenses-local/sticker-board-shared-local.json`**, and a small marker file under `.lenses-local`. Shared mode needs the same **expected GitHub login** resolution as PAT actions (registry, single **`.lenses-repo/<login>/`**, or **`gh`**). **Local boards cannot contain shared-scope stickers** (validated on POST).

**Saving:** **`POST /api/sticker-board`**; loopback unless **`LENSES_ALLOW_GIT_ACTIONS=1`**. **Last write wins** across tabs. Script: **`/__lenses/js/sticker-board.js`**; the page sets **`data-shared-available`** when a login is configured.

## Websites (`/websites` and `/websites/browse`)

**`/websites`** — **Full-width vertical hero sections** (stacked one per Firebase Hosting repo): git badges, README excerpt, stat chips (HTML counts, indexed vs total when capped, `index.html` mtime, **`hosting.public`**, Firebase **site** id), last-commit line with link when `origin` parses, an always-visible **Key pages** grid (links to **`/local-site/<repo>/…`**), **Preview in lenses** (iframe shell), copyable **build** / **deploy** one-liners, optional **Published site** from **`project_urls`**, and **global search** across site names, README text, and indexed page titles.

**GitHub PAT sign-in** (when expected login is configured) enables **Run …** buttons for allowlisted actions from **`registry["actions"]`** (see [Registry configuration](registry-configuration.html)).

**`/websites/browse?site=<name>`** — Sidebar of indexed pages (with filter) plus an **iframe** pointed at **`/local-site/<name>/…`** so in-app navigation stays on **127.0.0.1** and the lenses chrome remains visible.

## WBS (`/wbs` and `/wbs/view`)

- **`/wbs`** — Table (or list) of all `docs/requirements/WBS.md` and `WBS.csv` files found under the workspace.  
- **`/wbs/view?p=…`** — Read-only preview of a single file; path validated so only workspace-local requirement trees are accessible.

## Docs link

The sidebar **Docs** target is **`/docs/`**, which serves pre-built HTML from **`lenses-docs/`** (build with `generator/build-lenses-docs.py`).
