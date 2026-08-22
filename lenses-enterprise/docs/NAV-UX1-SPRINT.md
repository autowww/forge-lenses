# Sprint UX1 — Navigation simplification (Forge Studio / `lenses-enterprise`)

## Before → after (information architecture)

| Before (conceptual) | After |
|----|----|
| Flow vs Artifacts as a primary header split | Single primary tab row: Home, Work, Projects, Knowledge, Publish |
| Many top-level section names (plans, delivery, documentation, sites, blog, …) | Five task-based sections; registry `groupId` values aligned to those ids |
| Agentic bridge, governance, etc. mixed into everyday side nav | Advanced/admin items live under **Settings** (gear) → Admin / Studio |
| Search + chat only in header | **Find / Ask / Do** quick links + search + Copilot + **Go** quick-nav menu |

URLs are largely unchanged; IA is driven by `navigationConfig`, `studioRouteRegistry` `groupId`, and chrome components.

## Top-level jobs (target)

1. **Home** — Overview, attention, charts hub, project index entry points.
2. **Work** — Plan surfaces, WBS, timeline, matrix, boards, readiness.
3. **Projects** — Project-scoped dashboard, strategy, notes/evidence entry.
4. **Knowledge** — Tutorials, embedded docs, workspace markdown, methodology evidence/decisions, optional blueprints wizard.
5. **Publish** — Websites, blog, shipped outputs.

## Route inventory (classification summary)

| Class | Examples | Nav exposure |
|----|----|----|
| Primary work | `/plan`, `/plan?tab=…`, boards under work, timeline, matrix | **Work** sidebar |
| Primary projects | `/projects`, `/projects/:name/…` | **Projects** sidebar |
| Primary knowledge | `/tutorials`, `/view/docs`, `/workspace-md`, methodology registries | **Knowledge** sidebar |
| Primary publish | `/websites`, `/blog` | **Publish** sidebar |
| Utility | `/search`, `/chat`, `/toolset`, LLM settings | Header + **Go** menu; optional sidebar utilities group |
| Advanced | Flow/Artifacts lens preference | **Settings → Studio** (lens control + onboarding link) |
| Admin | Governance, audit, connectors, agentic bridge, preferences | **Settings → Admin** |
| Legacy / classic | Full Lenses workspace `href` links | Marked “classic” in sidebar semantics; not duplicated in top tabs |

Duplicates (e.g. same search/chat URLs) are not repeated as extra top-level tabs; shortcuts may still appear in sidebar “utilities” with semantics labels.

## Compatibility

- Deep links: same paths; `resolveNavSection` / `groupId` updates adjust active tab and breadcrumbs.
- Flow/Artifacts **mode** remains in `useNavigationMode` for lens-specific titles/sidebars where the registry still branches.

## QA summary (automated + manual notes)

Automated (this sprint):

- `npm test` — all Vitest suites green (`354` tests at last run).
- `npm run build` — `tsc -b` + `vite build` succeed.

Manual (recommended on a dev session):

1. Desktop: click each of the five top tabs; confirm sidebars and active states.
2. Narrow viewport: confirm header panel scrolls (`le-header-chrome-panel`); Find/Ask/Do and **Go** remain usable.
3. Open **Settings**: confirm Admin links, lens dropdown, UX insights, About.
4. Deep link samples: `/plan?tab=today`, `/workspace-md`, `/websites`, `/knowledge/agentic-bridge` (admin), `/search?q=test`.
5. Five-click clarity: project health (Projects → pick project → dashboard/charts as applicable), plan/timeline (Work), evidence/docs (Knowledge), publish (Publish), settings/admin (gear).

## Files touched (reference)

- `src/nav/navigationConfig.ts`, `studioRouteRegistry.ts`, `navPlacementTypes.ts`, `resolveNavSection.ts`, `studioVisibleCopy.ts`
- `src/components/TopNavigation.tsx`, `Layout.tsx`, `HeaderUtilities.tsx`, `HeaderSettingsMenu.tsx`, `SectionSidebar.tsx`, `StudioQuickNav.tsx`, `WorkspaceLensControl.tsx`
- `src/index.css` — header FAD, quick nav, settings lens block
