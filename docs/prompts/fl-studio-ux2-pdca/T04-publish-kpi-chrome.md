# T04 — Publish health + executive KPI chrome

**Executor:** Composer 2.5

**Backlog:** FLS2-005, FLS2-012

## Plan

Top nav Publish badge conveys site health readiness; Work and Knowledge clusters get compact ExecutiveSummaryStrip.

## Do

1. Add `publishHealth` summary in [`TopNavigation.tsx`](../../../lenses-enterprise/src/components/TopNavigation.tsx) linking to [`WebsitesPage.tsx`](../../../lenses-enterprise/src/pages/WebsitesPage.tsx).
2. Extend [`ExecutiveSummaryStrip.tsx`](../../../lenses-enterprise/src/components/shell/ExecutiveSummaryStrip.tsx) to [`PlanningClusterPageHeader`](../../../lenses-enterprise/src/components/plan/PlanningClusterPageHeader.tsx) and Knowledge section layouts.

## Check

```bash
scripts/fl-studio-ux2-pdca/check-phase-gate.sh T04
cd lenses-enterprise && npm run build
```

## Act

Fix Publish health badge or executive strip placement until T04 gate is green; then proceed to T05.
