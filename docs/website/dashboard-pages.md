# Dashboard pages

The UI is server-generated HTML from `lenses/render.py`. When the **kitchensink** submodule is present, pages use **`showcase_page`** from the design system (Bootstrap + `forge-theme.css` + `forgesdlc-theme.css`) with assets served from **`/__ks/`**. If the submodule is missing, the UI falls back to a compact inline-styled shell.

**Workspace switcher** — On every dashboard page, a **Workspace** `<select>` (top of the left sidebar when kitchensink is present; beside the brand row in the fallback shell) jumps to **Overview** (`/`), **All projects** (`/projects`), or a **repository** (`/projects/<name>`). On **Overview** and the **Projects** portal, the matching option is selected; on a **project** route, that project is selected. Other sections (Plan, WBS, etc.) show the neutral **— Workspace —** row until you pick a destination. Implemented by **`project_switcher_html`**, **`switcher_selected_href`**, and **`workspace_project_names_sorted`** in `lenses/render.py`.

## Overview (`/`)

**Hero** — When kitchensink is present, the top of the page uses **`render_product_landing_hero`**: workspace path and scan time sit in the clarification line; **Browse projects** and **Lenses docs** CTAs link to **`/projects`** and **`/docs/index.html`**; a muted **Tutorials** link below the buttons goes to **`/tutorials`**. Without kitchensink, the fallback title block includes inline links: Browse projects · Lenses docs · Tutorials.

**KPI row** — Counts for top-level folders, Firebase sites, WBS files, **Roadmaps** (`ROADMAP.md` under `docs/`), root **`*.sh`** scripts, plus **Approx. lines (sum)** — the sum of per-repo approximate tracked newlines (same caps as project stats). Layout uses six tiles on extra-wide breakpoints.

**Main column** — **Repositories:** each top-level child is a **repository card**:

- **Badges** — clean/dirty, branch, Firebase, published site (**Web**), and **Submodules: N** when a **`.gitmodules`** file exists at the repo root (section count only).
- **Facts line** — For git repos: **HEAD** short hash (linked when `origin` parses to a known host), **Updated** (relative time from **`commit_unix` / `commit_date`**), one-line **Latest** subject, **commits (7d)** (sum of **`commits_by_day_dict`**), **+additions / −deletions (7d)** from **`git_numstat_since`**, and **~LoC** (**`approx_tracked_lines`**).
- **Quick links** — **Project** (`/projects/<name>`), **Live** when **`project_urls`** lists a URL, **Preview** (`/local-site/<name>/…`) when that folder is a detected Firebase site, and **one link per detected handbook** (new tab) when the child has **`tutorial/index.html`**, **`tutorials/index.html`**, **`lenses/tutorials/index.html`**, or **`website/tutorials/index.html`** (`list_child_handbooks` in `tutorial_index.py`).
- **File mix** — Top **five** extensions from **`file_extension_counts`** for that repo (percent of that repo’s tracked files, with full counts in the pill **`title`**).
- **Description** — Registry **`project_summaries`** override the README source when set. Long text (**> ~400 characters**, **> 4** non-empty lines, or ASCII-tree markers such as **`├──` / `└──`**) shows a short **lede** plus a **`<details>`** block (“Full description” or “Architecture & full notes”) so large blurbs stay collapsible without JavaScript. Shorter text stays a single paragraph (truncated to ~720 characters when below the threshold).

**Workspace analytics** (below the cards, 2×2 grid on large screens):

- **Commits by day (7 days)** — Vertical bar chart: **`commits_by_day_dict`** per repo, merged and aligned to the last seven **UTC calendar days** (`workspace_commits_daily_series` in `lenses/project_stats.py`). Each bar shows the **commit count as visible text** above the bar (not only in the hover tooltip).
- **Lines added by repository (7 days)** — Horizontal bars from **`git log --numstat`** (additions only).
- **Repository size (approx. LoC)** — Horizontal bars of per-repo **`approx_tracked_lines`**, plus a **donut** of share of workspace lines (**top 8 repos + Other**).
- **File types (workspace)** — Merged extension histogram (**`file_extension_counts`**, top 120 extensions per repo) shown as horizontal share bars (`extension_heatmap_html`); denominator is the sum of each repo’s tracked-file count. Captions on the page spell out limitations (sampling, truncation, not `cloc`).

**Standards and agentic hygiene** (below **Workspace analytics**, same main column) — Heuristic **0–100 compliance score** per top-level repo from [`standards_compliance.compliance_report`](../standards_compliance.py): CI config, CONTRIBUTING/docs entry, **`sdlc/`** or **`blueprints/`**, **`.cursor`** rules or skills, Forge-related paths, dependency lockfiles, **`firebase.json`**, and (optional) recent commit-message markers for AI/co-author attribution when **`LENSES_STANDARDS_SCAN_COMMITS=1`**. Horizontal SVG bars (**`svg_compliance_score_bars`**); link to the blueprint handbook **Agentic coding standards**. Each check includes **`rationale`** and **`cursor_fix_prompt`** in JSON; the **project dashboard** table adds a **Guide** column with **Why & fix** modals (rationale, scan detail, copy-paste Cursor prompt). Same data appears under each child as **`standards_compliance`** in **`GET /api/workspace-state`** (see [Workspace scan contract](https://github.com/autowww/forge-lenses/blob/main/lenses/website/workspace-scan-contract.md)).

**Right column** — **Recent commits by repository**: for each git child, up to **five** commits with **subject**, **short hash** (link to host when `origin` parses), **relative time**, and the **commit body** excerpt as context (“explanation”). The column is **sticky** on wide viewports (scrollable if tall).

**Workspace metrics** — Reads **`lenses-docs/overview-metrics.json`**, produced by **`generator/collect-lenses-overview-data.py`** (run automatically after **`generator/build-lenses-docs.py`** from **`scripts/run-lenses.sh`** and **`scripts/restart-lenses.sh`**). That file merges:

- **Cursor** — Under **`~/.cursor/projects/`**, directories matching the workspace path slug (`exact` or **`prefix`** mode via **`LENSES_CURSOR_PROJECTS_MODE`**, default **`prefix`** for meta-repos). Counts **agent transcript** **`.jsonl`** files touched in the last **7 days** (by file mtime; not wall-clock session time). Also summarizes workspace **`.cursor/`** (rule count, **`SKILL.md`** count, **`mcp.json`** presence).
- **Manual** — Optional **`overview_metrics_manual`** in **`lenses-workspace-registry.json`**: e.g. **`human_hours_week`**, **`estimated_hours_without_genai`**, **`estimated_hours_genai_potential`** (aliases: **`hours_without_genai`**, **`hours_genai_potential`**), plus **`methodology_note`**. Shown as comparison bars with an explicit note that values are **not** inferred from git/Cursor.

**Environment** — **`LENSES_SKIP_CURSOR_METRICS=1`** skips reading **`~/.cursor`** (CI/privacy). **`LENSES_WORKSPACE_ROOT`** must match the dashboard scan root so slug matching aligns.

**Publishing / Requirements** — Compact **Publishing** and **WBS** blocks remain at the bottom of the page.

Git work on Overview uses parallel subprocess calls per repo; very large workspaces may take a few seconds on first load.

**Forge-autodoc handbooks** — Per workspace child, **`list_child_handbooks`** detects **`<repo>/tutorial/index.html`** (optional rsync target after **`build-fa-tutorials.sh`**), **`<repo>/tutorials/index.html`** (typical **`output_dir`** e.g. aw3), **`<repo>/lenses/tutorials/index.html`** (forge-lenses build without rsync), and **`<repo>/website/tutorials/index.html`** (e.g. forgesdlc **`build-site.py`**). If multiple **`tutorials/`** trees exist, the URL prefix **`tutorials/`** maps to the first match: root, then **`lenses/tutorials/`**, then **`website/tutorials/`**. Served as **`/local-site/<name>/tutorial/…`** and **`/local-site/<name>/tutorials/…`** (not part of **`/websites`** indexing). For Firebase sites, page titles from the scan may override default labels (**Tutorial** / **Engineer handbook**). The nav **Tutorials** item opens **`/tutorials`**, which lists **each** handbook (a repo can appear more than once if it has both **`tutorial/`** and **`tutorials/`**).

## Navigation (sidebar and compact top bar)

Workspace band: **Overview**, **Projects**, **Tutorials**, **Toolset**, **Websites**, **Sticker board**, **WBS**, **Roadmaps**. **Reference** band: **Lenses docs** (**`/docs/index.html`** — product reference handbook). **Published** band: **Handbook** and **Forge** (external).

**Target IA (product):** Charts are not top-level nav destinations (embed or tab). **Strategy** stays under **Repo & strategy** on the project dashboard, not a global nav item. **Knowledge** (Tutorials, Lenses docs, WBS, Workspace Markdown) groups as one cluster in the plan-aware shells—Classic still lists Tutorials, WBS, etc. separately today. See [Interface pages](interface-pages.md) for four plan shells, **Lenses Studio** vs Classic, and **Studio first / Classic in sync**.

## Tutorials (`/tutorials`)

Lists **each** handbook found under top-level workspace children (**`tutorial/`**, **`tutorials/`**, **`lenses/tutorials/`**, or **`website/tutorials/`**), with **Open tutorial** or **Open engineer handbook** and **Project dashboard** links. Empty state lists the path patterns and points to **Lenses docs**.

## Projects (`/projects`)

**Vertical stack** of full-width panels (same hero chrome as **`/websites`**: `lenses-site-hero-section`, `_lenses_vertical_hero_styles` in `lenses/render.py`), sorted by **last commit** (**`commit_unix`**, newest git repos first; non-git folders last, by name). **`_prefetch_portal_repo_metrics`** runs **`approx_tracked_lines`** and **`git_numstat_since(..., 7)`** in parallel across repos so the portal stays responsive.

Each panel highlights **high-level** context (not branch/SHA/origin on this page):

- **Kicker** — **`website_labels`** for Firebase hosting children when set; otherwise *Project*.
- **Blurb** — **`project_summaries`** from the registry when present; else a longer **README** excerpt (~360 chars).
- **Role row** — **Firebase site**, **Published site** (from **`project_urls`**), **WBS** file count with link to **`/wbs`** when this repo roots requirement files.
- **Stat strip** — approximate **LoC**, relative **updated** time, **+add / −del (7d)** when there was churn (hidden when both zero).
- **Last change** — latest **commit subject** (truncated) plus optional **Open commit** link; a short note when the tree has **uncommitted changes**.
- **Actions** — **Open dashboard** → **`/projects/<name>`**; **Repo & strategy** → **`/projects/<name>/strategy`**; when kitchensink is present, a compact **`fs-topic-preview-card`** (class **`lenses-portal-preview-trigger`**) opens the dashboard URL in an **in-page modal** (`?fs-embed=1`). Without kitchensink, only the dashboard and strategy buttons are shown.

## Repo & strategy (`/projects/<name>/strategy`)

Single page per workspace child: **How code is stored** (parse **`.gitmodules`**, show **`git submodule status`** with timeout/line cap, workspace sibling hints when a submodule folder name matches another top-level repo, optional **inline SVG** sketch plus a kitchensink **SVG template** thumbnail from **`/__ks/assets/svg/`** when submodules exist or **`ks_diagram_asset`** is set in **`project_strategy`**), **Branching** (current branch, clean/dirty, best-effort **`origin/HEAD`**, optional **`branching`** / **`branching_notes`** from the registry), and **Maintenance rules** (registry **`maintenance`** / **`maintenance_notes`** or defaults, plus optional repo-root **`LENSES-REPO-STRATEGY.md`** rendered as HTML when **`markdown`** is available). Breadcrumb: Overview · Projects · project · **Repo & strategy**.

## Project dashboard (`/projects/<name>`)

Stacked **vertical hero sections** (same chrome as **`/websites`**: `_lenses_vertical_hero_styles` / `lenses-site-hero-section` in `lenses/render.py`):

- **Identity hero** — Kicker (*Git repository* vs *Workspace folder*), title, absolute **path**, optional blurb from **`project_summaries`** in the workspace registry (when set); otherwise a **README preview** appears in its **own** panel below (not duplicated in the hero). **Quick links** (button row directly under the blurb when any apply): **one button per detected handbook** (`list_child_handbooks`), then **Preview in lenses** and **Open local site** for Firebase children, **Project site** when **`project_urls`** has a URL, **Docs site** when **`docs/index.html`** exists at the repo root. **What’s here** (between quick links and stat strip): a small grid summarizing **Documentation** (links for each handbook under **`/local-site/<name>/tutorial/…`** or **`…/tutorials/…`**, else a muted note with path hints; optional **Docs site** line to **`/local-site/<name>/docs/index.html`** when that file exists), **Website** (Firebase Hosting child with inline **Preview in lenses** / **Open local site root** links, or a muted line if not a Firebase child), **Planning** (WBS file count + **View WBS** link, or muted when none), **Sticker boards** (count from **`.lenses-local/sticker-board-registry.json`** for that project name, plus **Sticker board hub** → **`/board?project=<name>`**). **Pill badges**: clean/dirty, branch, short revision; **Firebase site** / **WBS ×N** when applicable. **Stat strip**: approximate **LoC**, relative **last update**, **+additions / −deletions (7d)** from **`git log --numstat`**, **total commits**, **tracked files** (same payload as the API). **Last commit** line with host link when `origin` parses. **CTAs** are grouped under labels **Source**, **Ship / preview**, **Learn & plan**, and **Navigate** (repository, commit; project site, preview/local/Firebase list when applicable; **Learn & plan** includes every handbook link plus WBS and sticker board; **Repo & strategy** → **`/projects/<name>/strategy`**; **← All projects**). Expandable **Technical** block: commit date and raw **origin** URL.
- **Standards and agentic hygiene** — Panel below README preview: **tier** badge (**good** / **partial** / **minimal**) and **score**, **summary** line, link to the blueprint **Agentic coding standards** handbook page, **checklist table** (icon, check name, scan detail, **Guide** → **Why & fix** opens a Bootstrap modal with **rationale**, current detail, and **Try in Cursor** copy-paste prompt), and **Suggestions** bullets for **warn** rows. Data from **`standards_compliance`** on the workspace child (same object as JSON API, including **`rationale`** and **`cursor_fix_prompt`** per check).
- **Activity (90 days)** — SVG commits-by-ISO-week bars from **`svg_commit_bar_chart`**: **numeric count on each bar**, light horizontal grid lines, and **Y-axis tick labels** at 0, half-max, and max.
- **Activity (7 days)** — Commits per calendar day: **`commits_by_day_dict`** aligned with **`workspace_commits_daily_series`**, rendered with **`svg_commit_daily_bar_chart`** (**visible count above each bar**).
- **Contributors** — Table from project stats.
- **File types** — Extension share bars, tracked file count, total commits.
- **Git actions** (Status, Fetch, Pull `--ff-only`): POST to **`/api/project/<name>/git`** via in-page `fetch` (loopback-only unless **`LENSES_ALLOW_GIT_ACTIONS=1`**), plus link to **`/api/project/<name>/stats`** for the same stats as JSON.

## Toolset (`/toolset` and `/toolset/<script>.sh`)

**`/toolset`** — Card grid (**forge-card** / column layout): each workspace-root **`*.sh`** file gets a card with a **Shell** badge, a short **blurb** parsed from the script’s leading `#` comments (after the shebang), and **Open run screen →** linking to **`/toolset/<url-encoded-name>`**. The **Cursor / IDE** section still shows whether **`.cursor`** exists at the workspace root.

**`/toolset/<name>`** — Run screen for one script: full comment header (up to a length cap), warning about local execution, **Run script…** (browser **confirm** first), then **`POST /api/toolset/run`**; combined **stdout** / **stderr** appear in a tall console `<pre>` (same loopback policy as project git actions unless **`LENSES_ALLOW_GIT_ACTIONS=1`**). Only basenames of **`*.sh`** files directly under the workspace root are accepted.

## Sticker board (`/board` and `/board/<id>`)

**Hub (`/board`)** — Single list of all boards (flat), each row shows **storage** badge, **label**, **project** pill, optional **PNG thumbnail**, and actions: **Open**, **Rename**, **Delete**, **Move to project** (any source project). Filter dropdown: all projects, **Unassigned** only, or one workspace child. **Create board** still picks project + local/shared up front. Optional **`?project=<name>`** pre-selects the filter (same as the link from each **project dashboard**). Script: **`/__lenses/js/sticker-board-hub.js`**.

**Thumbnails** — After a successful **`POST /api/sticker-board`**, the server may (debounced) run **html2image** + Chromium against **`/board/<id>?thumb=1`** and write **`<workspace>/.lenses-local/sticker-board-previews/<id>.png`**. Disable with **`LENSES_BOARD_PREVIEWS=0`**. Hub loads images from **`GET /board-preview/<id>.png`**. Requires **`pip install html2image`** and a Chromium/Chrome the library can find (same idea as handbook reference previews).

**Editor (`/board/<board_id>`)** — **Kanban** (three columns, HTML5 drag-and-drop) or **freeform** (pointer drag on a canvas). Each sticker has **title** + **details**; the card shows a preview. **Hover** shows **edit** (pencil) and **delete** (×); double-click still opens the editor. Toolbar shows **Local only** vs **Shared board**, board label, and opaque **board id** (for sharing the URL or the tracked file). Query **`?thumb=1`** serves a minimal-chrome layout for automated screenshots only.

**Board storage:** Registry **`sticker-board-registry.json`**. Per board: **`sticker-boards/<board_id>.json`** (local), or shared repo file + **`…-shared-local.json`** overlay + **`.marker.json`**. Legacy single **`sticker-board.json`** / **`sticker-board-shared-local.json`** is migrated on first access. Shared mode needs the same **expected GitHub login** resolution as PAT actions. **Local boards cannot contain shared-scope stickers** (validated on POST).

**Saving:** **`POST /api/sticker-board?board_id=…`**; loopback unless **`LENSES_ALLOW_GIT_ACTIONS=1`**. **Last write wins** across tabs. Editor script: **`/__lenses/js/sticker-board.js`**.

## Websites (`/websites` and `/websites/browse`)

**`/websites`** — **Full-width vertical hero sections** (stacked one per Firebase Hosting repo): git badges, README excerpt, stat chips (HTML counts, indexed vs total when capped, `index.html` mtime, **`hosting.public`**, Firebase **site** id), last-commit line with link when `origin` parses, an always-visible **Key pages** grid (links to **`/local-site/<repo>/…`**; **top-level HTML only** — nested paths under **`hosting.public`** are not listed here), **Preview in lenses** (iframe shell), copyable **build** / **deploy** one-liners, optional **Published site** from **`project_urls`**, and **global search** across site names, README text, and indexed page titles. There is **no** separate **Tutorial** subsection on this page; **forge-autodoc** handbooks (**`/local-site/<repo>/tutorial/…`** or **`/local-site/<repo>/tutorials/…`**) are opened from **Overview** / **project** / **`/tutorials`**, not as part of the Firebase **Key pages** grid.

**GitHub PAT sign-in** (when expected login is configured) enables **Run …** buttons for allowlisted actions from **`registry["actions"]`** (see [Registry configuration](registry-configuration.md)).

**`/websites/browse?site=<name>`** — Sidebar of indexed pages (with filter) plus an **iframe** pointed at **`/local-site/<name>/…`** so in-app navigation stays on **127.0.0.1** and the lenses chrome remains visible.

## WBS (`/wbs` and `/wbs/view`)

- **`/wbs`** — Table (or list) of all `docs/requirements/WBS.md` and `WBS.csv` files found under the workspace.  
- **`/wbs/view?p=…`** — Read-only preview of a single file; path validated so only workspace-local requirement trees are accessible.

## Forge plan (`/plan`)

- **Conceptual map** — [How the UI maps roadmap → WBS → execution → evidence](ui-map-workflow.md) (artifacts, tabs, APIs).
- **`/plan`** — **Forge planning and execution lens**: select **repository**, **`docs/requirements/WBS.md`**, optional **`ROADMAP.md`**. The **Plan** tab is a **3-pane explorer**: left **Milestone → Epic → Story → Spark** tree from **`/api/forge-work-model`** (plus optional groups for roadmap summary, product docs, operational evidence). For **Story** and **Spark**, the **center** pane is the primary **story cockpit** with tabs (**Definition**, **Product context**, **Execution**, **Decisions**, **Source**) populated from **`/api/story-hub`** (`story_view`: structured WBS slots, roadmap section hits, product links, execution, decisions, sources); the **Detail** rail is minimal. For milestones, epics, and reference nodes, the center stays level-aware and the rail uses **`/api/forge-work-model?node_id=`** where applicable. **`/api/plan-spine`** still loads alongside for context. Query **`?id=`** restores selection; **`?tab=today`** opens the **Today** tab: compact tables from **`/api/today-charge`** (in progress, blocked, banked, pending Versona sessions, recently done) with links back to **`?id=`** sparks. The **Source** tab (top-level) loads **`/roadmaps/preview`** only there — roadmap outline headings are not shown as work hierarchy.
- **`/roadmaps`** — Redirects to **`/plan`** (legacy bookmarks).

## Roadmap fragments (iframes / charts)

- **`/roadmaps/summary`**, **`/roadmaps/preview`**, **`/roadmaps/timeline`** — Unchanged; used by the Forge plan **Source** tab and summary strip.

## Lenses docs link

The sidebar **Lenses docs** target is **`/docs/`**, which serves pre-built HTML from **`lenses-docs/`** (build with `generator/build-lenses-docs.py`). Workspace forge-autodoc handbooks are **not** here; use **Tutorials** in the nav or per-repo links under **`/local-site/<name>/tutorial/…`** or **`/local-site/<name>/tutorials/…`**. When the handbook is built with **`--previews`** or **`LENSES_BUILD_DOC_PREVIEWS=1`** (and **html2image** + Chromium are available), **`docs/index.html`** can include a **Reference page previews** grid: PNG thumbnails for the top-level reference pages linked from **`docs/index.md`**, stored under **`lenses-docs/previews/`**.
