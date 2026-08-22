# S09 — Guided journeys

**Executor:** Composer 2.5

**Backlog:** FLS-019, FLS-020, FLS-021, FLS-048

## Plan

Studio teaches first value in-app: tour, Monday ritual, agentic start-here, and humane empty Knowledge states.

## Do

1. Add 5-stop in-app tour component (Home → Project → Today → Evidence → Publish) in shell/onboarding.
2. Add Monday checklist band on Home (attention → blockers → readiness).
3. Add Start-here journey on [`AgenticBridgePage.tsx`](../../../lenses-enterprise/src/pages/AgenticBridgePage.tsx) (not empty catalogs + JSON).
4. Knowledge empty states: sample cards + how to populate on Evidence/Decisions (no SQLite/API in main copy).

## Check

```bash
scripts/fl-studio-ux-pdca/check-phase-gate.sh S09
```

## Act

Wire tour, checklist, agentic journey, and empty guidance until S09 gate is green; then proceed to S10.
