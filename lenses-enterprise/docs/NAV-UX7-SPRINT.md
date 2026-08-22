# Sprint UX7 — Advanced / admin surface isolation

## Goal

Keep everyday task flow (Home, Work, Projects, Knowledge, Publish + header utilities) free of admin, governance, diagnostics, and workspace-wide automation entry points that belonged in **Settings (gear)**.

## Route map (logical)

| Area | Route | Breadcrumb parent (Studio) | Primary entry |
|------|--------|-----------------------------|---------------|
| Advanced reporting | `/overview/charts` | Admin & inspect | Settings → Inspect & advanced → Advanced reporting; contextual rail; deep links |
| Connector health | `/governance/connectors` | Admin & inspect | Settings → Inspect & advanced; governance cross-links |
| Audit log | `/governance/audit` | Admin & inspect | Settings → Inspect & advanced; super-admin API |
| Toolset index / run | `/toolset`, `/toolset/:name` | Admin & inspect | Settings → Inspect & advanced; command bar; bookmarks |
| UX diagnostics | `/settings/ux-insights` | Admin & inspect | Settings → Inspect & advanced; AI Setup modal footnote |
| Feature lab | `/feature-showcase` | Admin & inspect | Settings → **Labs & probes** (bookmark / QA only) |
| Site preview (empty lab) | `/view/local-site/` | Publish-adjacent embed | Settings → Labs & probes |
| Flow vs Artifacts deep link | `/?studioHelp=lens` | Home | Settings → Labs & probes |
| Blueprints Wizard session (probe) | `/blueprints/wizard/session/:id` | Knowledge (when wizard flag on) | Settings → Labs & probes (flagged) |
| Agentic bridge | `/knowledge/agentic-bridge` | Knowledge | **Knowledge** sidebar (govern) — not duplicated under gear admin |

Sidebars under **Home** and **Work** do not list Advanced reporting (`/overview/charts`), toolset, governance, labs, or diagnostics.

## Role / policy visibility (unchanged server behavior)

- **Connector health** — may return 403 when workspace access policy is enforced; copy states operator/admin intent.
- **Audit log** — API remains **super_admin** gated; page framing calls out sensitive history.
- **Toolset** — dangerous actions remain explicit on run page; workspace scan defines available scripts.
- **UX diagnostics** — browser-local only; no upload by default.

## AI helpers (admin / inspect context)

Embedded **`CopilotPanel`** defaults (read-only prompts) on: connector health (includes auth/403 plain-language ask), audit log, advanced reporting, toolset (+ run), UX diagnostics, **AI Setup** — aligned with `ADMIN_INSPECT_COPY` in `studioVisibleCopy.ts`.

Advanced pages share **`AdvancedSurfaceFraming`** (who / what / when / safety / where next) from `ADVANCED_SURFACE_FRAMES` in `studioVisibleCopy.ts`.

## QA checklist (manual)

1. **Normal nav** — Confirm Home / Work sidebars do not surface `/overview/charts`, `/toolset`, labs, or governance.
2. **Gear menu** — Preferences (intro + AI Setup modal titled “advanced workspace”) → Workspace admin (docs links) → Inspect & advanced → **Labs & probes** (feature showcase, empty site preview, Flow/Artifacts deep link, optional wizard session).
3. **Breadcrumbs** — `/overview/charts`, `/toolset`, `/governance/*`, `/settings/ux-insights`, `/feature-showcase` show **Admin & inspect** as parent (unchanged registry).
4. **Bookmarks** — Direct URLs to advanced and lab routes still render; Home overflow menu no longer promotes advanced reporting (use gear or collapsed Inspect on What changed).
5. **Copilot** — Panels on governance, reporting, toolset, UX diagnostics, and **AI Setup**; connector prompt extended for auth/SSO/403 translation.
6. **Accessibility** — Gear: section headings + collapsible “Layout lens (inspect)” `<details>`; advanced pages use `<details>` TechnicalDetails and shared framing list semantics.

## Automated checks run (agent)

- `npm run build` — **pass** (`tsc -b` + `vite build`).
- `npx vitest run src/nav/` — **pass** (103 tests in nav + related batch).

Full `npm test` may still surface unrelated pre-existing failures (e.g. Blueprints wizard server tests); scope UX7 validation with the commands above when bisecting.
