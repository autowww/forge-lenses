# T02 — Autonomy H1 + Docs Management summary

**Executor:** Composer 2.5

**Backlog:** FLS2-003, FLS2-011

## Plan

Autonomy maturity route exposes a visible H1 after lazy load; Home shows a PM-friendly Doc Management summary beside documentation review.

## Do

1. Ensure [`AutonomyMaturityPage.tsx`](../../../lenses-enterprise/src/pages/AutonomyMaturityPage.tsx) has `PageHeader` with visible H1, or eager-load route wrapper in [`App.tsx`](../../../lenses-enterprise/src/App.tsx).
2. Add [`DocsManagementSummary.tsx`](../../../lenses-enterprise/src/components/doc-management/DocsManagementSummary.tsx) on [`HomePage.tsx`](../../../lenses-enterprise/src/pages/HomePage.tsx): active sessions, last promote, plain-language lead summary.

## Check

```bash
scripts/fl-studio-ux2-pdca/check-phase-gate.sh T02
cd lenses-enterprise && npm run build
```

## Act

Fix autonomy H1 shell or Docs Management summary until T02 gate is green; then proceed to T03.
