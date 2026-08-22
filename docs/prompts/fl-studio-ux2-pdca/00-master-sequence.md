# Forge Lenses Studio UX2 remediation PDCA — master sequence

Composer **2.5** implements repo phases **T00–T09** for all **12** Studio UX2 backlog items (**FLS2-001…012**) from the Playwright crawl v2 and [lenses-studio-ux-backlog-v2](https://github.com/autowww/forge-lenses) canvas.

Prerequisite: **fl-studio-ux-pdca** S00–S12 complete (Studio shell on `:8080`, crawl v2 green, FLS-001…048 resolved).

Executor model: **Composer 2.5** (standard variant, not `-fast`).

| Phase | Prompt | FLS2 IDs | Scope |
|-------|--------|----------|-------|
| T00 | [T00-scaffold.md](T00-scaffold.md) | — | SEQUENCE, gate scripts, master sequence (all 12 IDs listed below) |
| T01 | [T01-oracle-empty-states.md](T01-oracle-empty-states.md) | 001, 002 | Playwright human-copy oracle + progressive empty states for sparse workspaces |
| T02 | [T02-surfaces-polish.md](T02-surfaces-polish.md) | 003, 011 | Autonomy maturity H1/loading shell; Doc Management PM summary on Home |
| T03 | [T03-bundle-splitting.md](T03-bundle-splitting.md) | 004 | Vite manual chunks + lazy heavy routes |
| T04 | [T04-publish-kpi-chrome.md](T04-publish-kpi-chrome.md) | 005, 012 | Publish nav health badge; ExecutiveSummaryStrip on Work + Knowledge |
| T05 | [T05-timeline-react.md](T05-timeline-react.md) | 006 | Structured timeline API + React Gantt (retire default HTML injection) |
| T06 | [T06-matrix-visual.md](T06-matrix-visual.md) | 007 | Matrix cell health color + mini sparkline |
| T07 | [T07-workspace-identity.md](T07-workspace-identity.md) | 008 | Guided local identity / workspace profile cue |
| T08 | [T08-telemetry-classic-docs.md](T08-telemetry-classic-docs.md) | 009, 010 | Tour/wizard step telemetry; Classic UI retirement maintainer doc |
| T09 | [T09-closeout.md](T09-closeout.md) | — | Crawl v3, backlog v3 canvas, full gate closeout |

## Full backlog registry (FLS2-001…012)

| ID | Phase | Title |
|----|-------|-------|
| FLS2-001 | T01 | CI Playwright human-copy oracle |
| FLS2-002 | T01 | Progressive empty states for small workspaces |
| FLS2-003 | T02 | Autonomy maturity page H1 + narrative shell |
| FLS2-004 | T03 | Studio bundle code-splitting |
| FLS2-005 | T04 | Publish health drill-down from badge |
| FLS2-006 | T05 | Timeline Gantt as React (retire HTML injection) |
| FLS2-007 | T06 | Matrix visual density pass |
| FLS2-008 | T07 | Guided local sign-in / workspace profile |
| FLS2-009 | T08 | Classic UI retirement checklist |
| FLS2-010 | T08 | Tour completion + first-run wizard analytics |
| FLS2-011 | T02 | Docs Management PM summary on Home |
| FLS2-012 | T04 | Executive strip on Work + Knowledge |

Gate runner: `scripts/fl-studio-ux2-pdca/check-phase-gate.sh <T00|…|T09|all>`

Do not open **T0N+1** until `./scripts/fl-studio-ux2-pdca/check-phase-gate.sh T0N` is green.
