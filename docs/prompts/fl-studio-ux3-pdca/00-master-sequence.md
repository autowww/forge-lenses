# Forge Lenses Studio UX3 remediation PDCA — master sequence

Composer **2.5** implements repo phases **U00–U08** for all **6** Studio UX3 backlog items (**FLS3-001…006**) from the Playwright crawl v3 and [lenses-studio-ux-backlog-v3](https://github.com/autowww/forge-lenses) canvas.

Prerequisite: **fl-studio-ux2-pdca** T00–T09 complete (Studio **1.0.55+**, crawl v3 green, FLS2-001…012 resolved).

Executor model: **Composer 2.5** (standard variant, not `-fast`).

| Phase | Prompt | FLS3 IDs | Scope |
|-------|--------|----------|-------|
| U00 | [U00-scaffold.md](U00-scaffold.md) | — | SEQUENCE, gate scripts, master sequence (all 6 IDs listed below) |
| U01 | [U01-multi-repo-ci.md](U01-multi-repo-ci.md) | 004 | Multi-repo E2E fixture + crawl v4 script + CI crawl gate |
| U02 | [U02-classic-studio-strip.md](U02-classic-studio-strip.md) | 001 (A) | Remove Classic outbound links from Studio default UI |
| U03 | [U03-classic-server-removal.md](U03-classic-server-removal.md) | 001 (B) | `_studio_redirect` stubs; delete classic `page_*` handlers in `serve.py` |
| U04 | [U04-roadmap-section-react.md](U04-roadmap-section-react.md) | 002 | Structured roadmap section API + `RoadmapSectionPreview` React |
| U05 | [U05-timeline-editor-metrics.md](U05-timeline-editor-metrics.md) | 003 | `date_rows` timeline API + `RoadmapDateEditor`; retire `ForgeRoadmapDates` |
| U06 | [U06-matrix-kpi-sparkline.md](U06-matrix-kpi-sparkline.md) | 005 | Matrix sparklines from `kpi_trends` + health-tier CSS |
| U07 | [U07-publish-drilldown.md](U07-publish-drilldown.md) | 006 | `PublishHealthPopover` drill-down from Publish nav badge |
| U08 | [U08-closeout.md](U08-closeout.md) | — | Crawl v4, backlog v4 canvas, full gate closeout |

## Full backlog registry (FLS3-001…006)

| ID | Phase | Title |
|----|-------|-------|
| FLS3-001 | U02, U03 | Full Classic UI code removal |
| FLS3-002 | U04 | RoadmapSection HTML injection → React |
| FLS3-003 | U05 | Timeline editor React host |
| FLS3-004 | U01 | Multi-repo crawl fixture in CI |
| FLS3-005 | U06 | Matrix sparkline from kpi_trends API |
| FLS3-006 | U07 | Publish badge drill-down modal |

Gate runner: `scripts/fl-studio-ux3-pdca/check-phase-gate.sh <U00|…|U08|all>`

Do not open **U0N+1** until `./scripts/fl-studio-ux3-pdca/check-phase-gate.sh U0N` is green.
