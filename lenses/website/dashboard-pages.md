# Dashboard pages

The UI is server-generated HTML from `lenses/render.py`. When the **kitchensink** submodule is present, pages use **`showcase_page`** from the design system (Bootstrap + `forge-theme.css` + `forgesdlc-theme.css`) with assets served from **`/__ks/`**. If the submodule is missing, the UI falls back to a compact inline-styled shell.

## Overview (`/`)

**Hero** — When kitchensink is present, the top of the page uses **`render_product_landing_hero`**: workspace path and scan time sit in the clarification line; **Browse projects** and **Lenses docs** CTAs link to **`/projects`** and **`/docs/index.html`**. Without kitchensink, a compact fallback title block is used.

**KPI row** — Counts for top-level folders, Firebase sites, WBS files, root **`*.sh`** scripts, plus a fifth tile **Approx. lines (sum)** — the sum of per-repo approximate tracked newlines (same caps as project stats).

**Main column** — **Repositories:** each top-level child is a **repository card**:

- **Badges** — clean/dirty, branch, Firebase, published site (**Web**), and **Submodules: N** when a **`.gitmodules`** file exists at the repo root (section count only).
- **Facts line** — For git repos: **HEAD** short hash (linked when `origin` parses to a known host), **Updated** (relative time from **`commit_unix` / `commit_date`**), one-line **Latest** subject, **commits (7d)** (sum of **`commits_by_day_dict`**), **+additions / −deletions (7d)** from **`git_numstat_since`**, and **~LoC** (**`approx_tracked_lines`**).
- **Quick links** — **Project** (`/projects/<name>`), **Live** when **`project_urls`** lists a URL, **Preview** (`/local-site/<name>/…`) when that folder is a detected Firebase site.
- **File mix** — Top **five** extensions from **`file_extension_counts`** for that repo (percent of that repo’s tracked files, with full counts in the pill **`title`**).
- **Description** — Registry **`project_summaries`** override the README source when set. Long text (**> ~400 characters**, **> 4** non-empty lines, or ASCII-tree markers such as **`├──` / `└──`**) shows a short **lede** plus a **`<details>`** block (“Full description” or “Architecture & full notes”) so large blurbs stay collapsible without JavaScript. Shorter text stays a single paragraph (truncated to ~720 characters when below the threshold).

**Workspace analytics** (below the cards, 2×2 grid on large screens):

- **Commits by day (7 days)** — Vertical bar chart: **`commits_by_day_dict`** per repo, merged and aligned to the last seven **UTC calendar days** (`workspace_commits_daily_series` in `lenses/project_stats.py`).
- **Lines added by repository (7 days)** — Horizontal bars from **`git log --numstat`** (additions only).
- **Repository size (approx. LoC)** — Horizontal bars of per-repo **`approx_tracked_lines`**, plus a **donut** of share of workspace lines (**top 8 repos + Other**).
- **File types (workspace)** — Merged extension histogram (**`file_extension_counts`**, top 120 extensions per repo) shown as horizontal share bars (`extension_heatmap_html`); denominator is the sum of each repo’s tracked-file count. Captions on the page spell out limitations (sampling, truncation, not `cloc`).

**Right column** — **Recent commits by repository**: for each git child, up to **five** commits with **subject**, **short hash** (link to host when `origin` parses), **relative time**, and the **commit body** excerpt as context (“explanation”). The column is **sticky** on wide viewports (scrollable if tall).

**Workspace metrics** — Reads **`lenses-docs/overview-metrics.json`**, produced by **`generator/collect-lenses-overview-data.py`** (run automatically after **`generator/build-lenses-docs.py`** from **`scripts/run-lenses.sh`** and **`scripts/restart-lenses.sh`**). That file merges:

- **Cursor** — Under **`~/.cursor/projects/`**, directories matching the workspace path slug (`exact` or **`prefix`** mode via **`LENSES_CURSOR_PROJECTS_MODE`**, default **`prefix`** for meta-repos). Counts **agent transcript** **`.jsonl`** files touched in the last **7 days** (by file mtime; not wall-clock session time). Also summarizes workspace **`.cursor/`** (rule count, **`SKILL.md`** count, **`mcp.json`** presence).
- **Manual** — Optional **`overview_metrics_manual`** in **`lenses-workspace-registry.json`**: e.g. **`human_hours_week`**, **`estimated_hours_without_genai`**, **`estimated_hours_genai_potential`** (aliases: **`hours_without_genai`**, **`hours_genai_potential`**), plus **`methodology_note`**. Shown as comparison bars with an explicit note that values are **not** inferred from git/Cursor.

**Environment** — **`LENSES_SKIP_CURSOR_METRICS=1`** skips reading **`~/.cursor`** (CI/privacy). **`LENSES_WORKSPACE_ROOT`** must match the dashboard scan root so slug matching aligns.

**Publishing / Requirements** — Compact **Publishing** and **WBS** blocks remain at the bottom of the page.

Git work on Overview uses parallel subprocess calls per repo; very large workspaces may take a few seconds on first load.

## Projects (`/projects`)

**Vertical stack** of full-width panels (same hero chrome as **`/websites`**: `lenses-site-hero-section`, `_lenses_vertical_hero_styles` in `lenses/render.py`), sorted by **last commit** (**`commit_unix`**, newest git repos first; non-git folders last, by name). **`_prefetch_portal_repo_metrics`** runs **`approx_tracked_lines`** and **`git_numstat_since(..., 7)`** in parallel across repos so the portal stays responsive.

Each panel highlights **high-level** context (not branch/SHA/origin on this page):

- **Kicker** — **`website_labels`** for Firebase hosting children when set; otherwise *Project*.
- **Blurb** — **`project_summaries`** from the registry when present; else a longer **README** excerpt (~360 chars).
- **Role row** — **Firebase site**, **Published site** (from **`project_urls`**), **WBS** file count with link to **`/wbs`** when this repo roots requirement files.
- **Stat strip** — approximate **LoC**, relative **updated** time, **+add / −del (7d)** when there was churn (hidden when both zero).
- **Last change** — latest **commit subject** (truncated) plus optional **Open commit** link; a short note when the tree has **uncommitted changes**.
- **Actions** — **Open dashboard** → **`/projects/<name>`**; when kitchensink is present, a compact **`fs-topic-preview-card`** (class **`lenses-portal-preview-trigger`**) opens the same URL in an **in-page modal** (`?fs-embed=1`). Without kitchensink, only the dashboard button is shown.

## Project dashboard (`/projects/<name>`)

Stacked **vertical hero sections** (same chrome as **`/websites`**: `_lenses_vertical_hero_styles` / `lenses-site-hero-section` in `lenses/render.py`):

- **Identity hero** — Kicker (*Git repository* vs *Workspace folder*), title, absolute **path**, optional blurb from **`project_summaries`** in the workspace registry (when set); otherwise a **README preview** appears in its **own** panel below (not duplicated in the hero). **Pill badges**: clean/dirty, branch, short revision; **Firebase site** / **WBS ×N** when applicable. **Stat strip**: approximate **LoC**, relative **last update**, **+additions / −deletions (7d)** from **`git log --numstat`**, **total commits**, **tracked files** (from the same stats payload as the API). **Last commit** line with host link when `origin` parses. **CTAs**: repository, commit, **project site** (`project_urls`), **Preview in lenses** / **Open local site root** / **Firebase sites list** when this child is a Firebase hosting repo, **WBS** when requirement files are rooted under this folder, **← All projects**. Expandable **Technical** block: commit date and raw **origin** URL.
- **Activity (90 days)** — SVG commits-by-ISO-week bars (unchanged data).
- **Activity (7 days)** — Commits per calendar day: **`commits_by_day_dict`** aligned with **`workspace_commits_daily_series`**, rendered with **`svg_commit_daily_bar_chart`**.
- **Contributors** — Table from project stats.
- **File types** — Extension share bars, tracked file count, total commits.
- **Git actions** (Status, Fetch, Pull `--ff-only`): POST to **`/api/project/<name>/git`** via in-page `fetch` (loopback-only unless **`LENSES_ALLOW_GIT_ACTIONS=1`**), plus link to **`/api/project/<name>/stats`** for the same stats as JSON.

## Toolset (`/toolset` and `/toolset/<script>.sh`)

**`/toolset`** — Card grid (**forge-card** / column layout): each workspace-root **`*.sh`** file gets a card with a **Shell** badge, a short **blurb** parsed from the script’s leading `#` comments (after the shebang), and **Open run screen →** linking to **`/toolset/<url-encoded-name>`**. The **Cursor / IDE** section still shows whether **`.cursor`** exists at the workspace root.

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
