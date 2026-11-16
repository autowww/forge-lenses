# S07 — Home attention + docs readiness

**Executor:** Composer 2.5

**Backlog:** FLS-011, FLS-014

## Plan

Home ranks attention before the KPI wall; documentation review is visible as a human summary, not buried jargon.

## Do

1. Add portfolio attention strip above KPI wall on [`HomePage.tsx`](../../../lenses-enterprise/src/pages/HomePage.tsx).
2. Add documentation review summary card on Home + Project (counts + next fix) — reuse docs-health components under `lenses-enterprise/src/components/docs-health/`.
3. Use **Documentation review** label from `studioVisibleCopy` consistently.

## Check

```bash
scripts/fl-studio-ux-pdca/check-phase-gate.sh S07
```

## Act

Wire attention strip and docs summary until S07 gate is green; then proceed to S08.
