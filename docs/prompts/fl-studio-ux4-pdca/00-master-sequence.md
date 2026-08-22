# Forge Lenses Studio UX4 remediation PDCA — master sequence

Composer **2.5** implements repo phases **V00–V05** for all **4** Studio UX4 backlog items (**FLS4-001…004**) from the Playwright crawl v4 and [lenses-studio-ux-backlog-v4](https://github.com/autowww/forge-lenses) canvas.

Prerequisite: **fl-studio-ux3-pdca** U00–U08 complete (crawl v4 green, FLS3-001…006 resolved).

Executor model: **Composer 2.5** (standard variant, not `-fast`).

| Phase | Prompt | FLS4 IDs | Scope |
|-------|--------|----------|-------|
| V00 | [V00-scaffold.md](V00-scaffold.md) | — | SEQUENCE, gate scripts, master sequence (all 4 IDs listed below) |
| V01 | [V01-nested-roadmap-react.md](V01-nested-roadmap-react.md) | 001 | `GET /api/nested-roadmap-config` + `NestedRoadmapHorizon` React host |
| V02 | [V02-classic-embed-retirement.md](V02-classic-embed-retirement.md) | 002 | Sites browse via `/local-site/`; remove Classic board editor link from Studio hub |
| V03 | [V03-index-bundle-split.md](V03-index-bundle-split.md) | 003 | Lazy `HomePage` + index chunk target (&lt;700 KB) in Vite `manualChunks` |
| V04 | [V04-board-redirect-soak.md](V04-board-redirect-soak.md) | 004 | `_studio_redirect` for `/board`; handbook notes board/websites browse retirement |
| V05 | [V05-closeout.md](V05-closeout.md) | — | Crawl v5, backlog v5 canvas, full gate closeout |

## Full backlog registry (FLS4-001…004)

| ID | Phase | Title |
|----|-------|-------|
| FLS4-001 | V01 | Nested roadmap iframe → React |
| FLS4-002 | V02 | Classic `/board/:id` and `/websites/browse` embed retirement |
| FLS4-003 | V03 | Index bundle split (&lt;700 KB) |
| FLS4-004 | V04 | `render.py` page builder deletion soak |

Gate runner: `scripts/fl-studio-ux4-pdca/check-phase-gate.sh <V00|…|V05|all>`

Do not open **V0N+1** until `./scripts/fl-studio-ux4-pdca/check-phase-gate.sh V0N` is green.
