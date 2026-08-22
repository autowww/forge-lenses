# S08 — Work depth without jargon

**Executor:** Composer 2.5

**Backlog:** FLS-012, FLS-013, FLS-022

## Plan

Plan and Timeline surfaces show milestone outcomes, interpreted freshness, and remembered scope.

## Do

1. Show milestone titles in matrix cells on [`PlanMatrixPage.tsx`](../../../lenses-enterprise/src/pages/PlanMatrixPage.tsx) (not only story/WBS counts).
2. Add freshness/confidence chips on Plan and Today headers ([`PlanPage.tsx`](../../../lenses-enterprise/src/pages/PlanPage.tsx), delivery headers).
3. Persist last scope + human labels on [`TimelinePage.tsx`](../../../lenses-enterprise/src/pages/TimelinePage.tsx).

## Check

```bash
scripts/fl-studio-ux-pdca/check-phase-gate.sh S08
```

## Act

Fix matrix titles, freshness chips, and timeline scope memory until S08 gate is green; then proceed to S09.
