# T08 — Telemetry + Classic UI retirement doc

**Executor:** Composer 2.5

**Backlog:** FLS2-009, FLS2-010

## Plan

Tour and first-run wizard emit step telemetry; maintainer doc captures Classic UI retirement checklist.

## Do

1. Extend [`studioTelemetry.ts`](../../../lenses-enterprise/src/telemetry/studioTelemetry.ts) with `recordTourStep` and `recordFirstRunWizardStep`.
2. Wire [`StudioInAppTour.tsx`](../../../lenses-enterprise/src/components/onboarding/StudioInAppTour.tsx) and [`StudioFirstRunWizard.tsx`](../../../lenses-enterprise/src/components/onboarding/StudioFirstRunWizard.tsx).
3. Add [`docs/handbook-public/studio-classic-ui-retirement.md`](../../../docs/handbook-public/studio-classic-ui-retirement.md): per-surface migration table and sunset criteria.

## Check

```bash
scripts/fl-studio-ux2-pdca/check-phase-gate.sh T08
```

## Act

Fix telemetry wiring or retirement doc until T08 gate is green; then proceed to T09.
