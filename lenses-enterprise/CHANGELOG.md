# Changelog

All notable changes to **Forge Studio** (the `lenses-enterprise` React SPA) are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) as described in [VERSIONING.md](./VERSIONING.md).

## [Unreleased]

### Changed

- **`npm run build` / `npm run build:museum`:** run **`scripts/bump-studio-patch-version.mjs`** first so **`package.json`** **PATCH** increases on every Studio production build (opt out with **`SKIP_STUDIO_VERSION_BUMP=1`**). **`npm run watch`** does not bump.

### Added

- **Docs health E2E:** `npm run test:e2e:docs-health` runs Playwright **scan** regression (`e2e/docs-health-scan.spec.ts`) and **session** UI coverage (`e2e/docs-health-session.spec.ts`) with mocked `session_get` for cancelled, awaiting-approval, post-apply verify, and completed states. Maintainer notes: **`../docs/maintainer/docs-health-mvp.md`**.
- **AI Setup — diagnostics & trust:** **`GET /api/llm/diagnostics`** (aggregated health, usage, probes, routing log); **`probe_log`** in **`llm-usage.json`** filled by **`POST /api/llm/provider-probe`**; chat events record **`fallback_from`** / **`studio_task_id`** when routing provides them; settings migration adds **`routing_mode`**, task-route privacy defaults, and **`first_run_wizard_dismissed`**. Studio: expanded **Usage & diagnostics** block (`#ai-setup-diagnostics`), first-run wizard with dismiss, contextual rail shows live setup status and doc/debug links. Museum sample **`llm-diagnostics.json`**.
- **Splash:** in-app loading panel shows **`v{semver} · {commit|no-git} · {ISO UTC}`** (virtual build meta). **Electron** frameless splash reads the same triple from **`lenses/static/studio/studio-build-meta.json`** after **`npm run build`**, with fallback to `package.json` + git only if that file is missing.
- **AI Setup — routing:** three modes (**Single model**, **Smart multi-model**, **Advanced routing**); smart **four-stop quality** preset; **routing preview** table with live **`POST /api/llm/routing-preview-draft`**; advanced **per-task matrix** (primary, fallback, privacy); single-mode **per-task overrides** with privacy. Museum **`routing-preview.json`** includes extended row fields.
- **AI Setup — Local (Ollama):** model-management panel — host line, catalog table (size, modified, **last used** from workspace analytics), **pull / update / remove** via **`POST /api/llm/ollama-action`**, quick **task role** mapping (Chat, Code, Vision, Embeddings → `task_routes`), first-time setup (numbered steps + bundled **`setup-ollama-for-lenses.sh`** copy/download). Static museum sample **`ollama-status.json`** includes **`model_catalog`**.

### Fixed

- **Plan → Story:** avoid a blank/black main area when opening a story — `story_view.slots` values are API objects (`{ text, sources }`), not strings; rendering them as React children threw. Slots now show markdown from `.text`, and the **Definition** block falls back to the top-level **`definition`** payload.

### Changed

- **AI Setup — Model sources swimlane:** each **cloud** vendor tile and **More providers** has its own **Tile / Hero / Advanced** control (no longer one density for the whole cloud row). Cloud **tile** mode is read-only with **Expand to configure**; **advanced** adds in-card usage/probe snippets. **Custom** advanced adds aggregated gateway diagnostics; **Ollama** tile mode is a read-only summary (roles/catalog use the section density control). Spec: `docs/AI_SETUP_BLOCK_CONTRACT.md`.
- **AI Setup — per-task model overrides:** free-text model ids are **stacked `<select>` rows** (saved priority in **`model_stack`** in `llm-settings.json`); options merge **Discover models** catalog, the source’s **main model**, and **task-category suggestions**. Routing still uses only the **first** id until failover exists. **Single-model** mode now applies a per-task model even when **Provider** is **(primary)** (previously ignored).
- **Shell:** removed the bottom **build footer** (version line + **Release notes** control). It overlapped the bottom of scrollable pages and blocked row clicks; **Release notes** remain under **Settings → About Forge Studio** (CHANGELOG modal).
- **AI Setup (`/settings/llm`):** dashboard layout — status strip with Save / Try Chat, grouped **Cloud / Custom / Local** source cards (collapsed credentials with Connect / Manage / Try out), first-time empty state, multi-source routing controls only when **two or more** sources are connected, collapsed **Usage & diagnostics** and **Technical details** (files and env vars). **Sprint 2:** **More providers** shortcuts, **Add custom provider** drawer (display name, compatibility/auth, base URL, discover & health), **`POST /api/llm/provider-probe`** for server-side model discovery, **Used for** chips from per-task routes, masked credential line, **Discover models** / **Health check** on cloud + custom + Ollama cards; `custom_provider` block in `llm-settings.json` for gateway metadata.
- **Boards hub (`/board`):** no longer opens on a **loading-only** screen. The hub always renders header, planning shortcuts, **KPI strip** (with pulse placeholders until data exists), templates, create form, and directory chrome. **`ResourceFetchStatus`** (shared page component) covers **initial fetch**, **background refresh**, **hard API failure**, and **stale localStorage fallback** (snapshot time + retry + Today / Plan / Workspace charts). Registry state is classified as **empty / loaded / partial** (validation issues or `access_enforced`). **Recent boards** (by preview mtime) restore quick open paths. Board registry cache is keyed by **`workspace_root`** to avoid cross-workspace bleed.
- **Shell & header:** the persistent build footer was removed later (see Unreleased) after it blocked bottom-row clicks. **Primary nav** is a **single bar**: section tabs share one row with **Back / trail / breadcrumbs** (tabs scroll horizontally if space is tight). **Flow / Artifacts** inline explainer line removed from chrome to save vertical space (glossary and onboarding elsewhere). **Release notes** open an **in-app** modal with the bundled `CHANGELOG.md` (no GitHub link). Header tool strip can **scroll horizontally** if the viewport is tight; window chrome and account cluster stay **non-shrinking**.
- **Planning cockpit:** friendlier **Work backlog** vs **Product roadmap** scope cards (titles from file names; paths as secondary detail), page header context line, milestone **cards** with roll-up counts, and **story detail modal** (tasks, definition, slots) instead of jumping straight to the Story tab. **Session history:** Back (parent route when known, else browser back), **Forward**, and a **recent pages** dropdown from `StudioNavigationTrailProvider`.
- **Plan scope bar:** four **clickable tiles** (backlog, roadmap, repository, work item) each open a **popover list**; changing **WBS** clears roadmap, repo hint (reset from row), and work item; changing **roadmap** or **repo** clears the work item. **Advanced** collapsible keeps raw inputs.

## [1.0.0] — 2026-04-10

### Added

- **Build metadata in the UI:** a bottom footer briefly showed **Forge Studio** semver and short **git** commit (later removed so it did not cover table rows); **Settings → About Forge Studio** shows version, commit, UTC build time, and links to this changelog and the version policy.
- **Versioning docs:** [VERSIONING.md](./VERSIONING.md) defines semver rules for Studio vs the **forge-lenses** Python server.

### Fixed

- **Navigation and embedded content:** same-origin link handling, markdown and relative `plan?…` href resolution, iframe bridge for in-preview navigation, and related routing so Studio stays in-shell when following internal links (docs, WBS, plans, embedded sites).

[Unreleased]: https://github.com/autowww/forge-lenses/compare/main...HEAD
[1.0.0]: https://github.com/autowww/forge-lenses/tree/main/lenses-enterprise
