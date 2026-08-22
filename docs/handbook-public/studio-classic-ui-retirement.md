# Classic UI retirement checklist (Forge Lenses Studio)

Forge Lenses **Studio** is the default experience. As of UX3 PDCA (FLS3-001), primary Classic **HTML page routes** respond with **302 redirects** to `/studio/…` equivalents. API routes, roadmap fragments, and iframe embeds listed below remain for parity.

## Redirected Classic HTML routes (302 → Studio)

| Classic route | Studio target |
|---------------|---------------|
| `/`, `/projects`, `/projects/:name` | `/studio/`, `/studio/projects`, `/studio/projects/:name` |
| `/plan`, `/timeline`, `/wbs` | `/studio/plan`, `/studio/timeline`, `/studio/wbs` |
| `/roadmaps` | `/studio/plan` (query preserved) |
| `/websites` (list) | `/studio/websites` |
| `/websites/browse?site=` | `/studio/websites/browse/:site` (static `/local-site/` preview) |
| `/board`, `/board/:id` | `/studio/board`, `/studio/board/:id` |
| `/search`, `/tutorials` | `/studio/search`, `/studio/tutorials` |

**Kept (parity blockers — do not delete without Studio replacement):**

- `/api/*` JSON and action endpoints
- `/roadmaps/summary`, `/roadmaps/timeline`, `/roadmaps/preview`
- `/websites/browse` (Studio iframe embed for Sites preview)
- `/board/:id` (classic sticker board editor — **thumb capture only**; normal visits redirect to `/studio/board/:id`)
- `/wbs/view`, `/workspace-md/view`, `/overview/charts-api`, `/projects/:name/charts-api`

## Per-surface migration

| Classic surface | Studio replacement | Sunset criteria |
|-----------------|------------------|-----------------|
| Project dashboard (`/project/…`) | `/studio/projects/:name` | Feature parity on health, risks, docs health bands |
| Plan / WBS (`/plan`, `/wbs`) | `/studio/plan`, `/studio/plan/matrix` | Scope memory, matrix, timeline React Gantt default |
| Timeline (`/timeline`) | `/studio/timeline` | React Gantt + metrics + `RoadmapDateEditor` default |
| Roadmaps summary (`/roadmaps`) | `/studio/plan` + matrix | Orchestration overlay parity |
| Websites list (`/websites`) | `/studio/websites` | Publish health badge + site readiness drill-down |
| Workspace markdown (`/workspace-md`) | `/studio/workspace-md` | Browse + copilot assist parity |

## Operator guidance

1. **Default link** — Open `http://127.0.0.1:8080/studio/` for day-to-day work.
2. **Bookmarks** — Classic paths above redirect automatically; update bookmarks to `/studio/…` when convenient.
3. **Removal gate** — Remaining Classic builders in `render.py` may be deleted after FLS4 soak (see backlog v4 canvas).

## Related

- [Studio troubleshooting](./studio-troubleshooting.md) — workspace root and sparse scan guidance.
- [Studio navigation and shell](./studio-navigation-and-shell.md) — Publish badge and KPI chrome.
