# S06 — Project maturity surfaces

**Executor:** Composer 2.5

**Backlog:** FLS-008, FLS-009, FLS-010

## Plan

Projects Flow and project dashboard answer health and next action without opening Artifacts or charts first.

## Do

1. Add Ready / Watch / At risk health tiers on Flow cards in [`ProjectsPage.tsx`](../../../lenses-enterprise/src/pages/ProjectsPage.tsx).
2. Promote **Suggested next step** as primary CTA on [`ProjectDetailPage.tsx`](../../../lenses-enterprise/src/pages/ProjectDetailPage.tsx) over Repository charts.
3. Add this-week narrative to [`ProjectAtAGlance.tsx`](../../../lenses-enterprise/src/components/projects/ProjectAtAGlance.tsx) (story, not commits/HEAD jargon).

## Check

```bash
scripts/fl-studio-ux-pdca/check-phase-gate.sh S06
```

## Act

Fix health tiers, CTA order, and narrative until S06 gate is green; then proceed to S07.
