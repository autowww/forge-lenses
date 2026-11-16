# T06 — Matrix visual density

**Executor:** Composer 2.5

**Backlog:** FLS2-007

## Plan

Matrix cells show health tier color and optional milestone sparklines instead of count-only density.

## Do

1. Add per-cell `healthTier` and optional `milestoneSparkline` in [`PlanMatrixPage.tsx`](../../../lenses-enterprise/src/pages/PlanMatrixPage.tsx).
2. Reuse tier colors from KPI trends (`green` / `amber` / `red`).

## Check

```bash
scripts/fl-studio-ux2-pdca/check-phase-gate.sh T06
cd lenses-enterprise && npm test
```

## Act

Fix matrix health/sparkline rendering until T06 gate is green; then proceed to T07.
