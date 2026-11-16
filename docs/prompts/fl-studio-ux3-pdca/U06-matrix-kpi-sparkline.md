# U06 — Matrix KPI sparklines + health-tier CSS

**Executor:** Composer 2.5

**Backlog:** FLS3-005

## Plan

Wire matrix cell sparklines and health tiers to `kpi_trends` overview chart data; add missing matrix and publish-health CSS classes.

## Do

1. In [`PlanMatrixPage.tsx`](../../../lenses-enterprise/src/pages/PlanMatrixPage.tsx), parallel-fetch via `getOverviewChartPayload(timeHorizon)` from [`ShellChromeContext`](../../../lenses-enterprise/src/context/ShellChromeContext.tsx).
2. Map `rm.repo_hint` → `perRepoLinesByKey(payload)`; use `sparklinePeriodTotals` + `tierToClass` from [`kpiTrendUi.ts`](../../../lenses-enterprise/src/lib/kpiTrendUi.ts).
3. Blend orchestration red tier when `slip_preview.transitive_blocked_count > 0`.
4. Add CSS for `le-roadmap-matrix__healthTier--*` in [`enterprise-shell.css`](../../../lenses-enterprise/src/enterprise-shell.css).

## Check

```bash
scripts/fl-studio-ux3-pdca/check-phase-gate.sh U06
cd lenses-enterprise && npm test
```

## Act

Fix chart wiring or matrix CSS until U06 gate is green; then proceed to U07.
