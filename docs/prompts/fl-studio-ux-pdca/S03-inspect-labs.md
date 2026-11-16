# S03 — Inspect gate + Labs IA

**Executor:** Composer 2.5

**Backlog:** FLS-023, FLS-025, FLS-029, FLS-030

## Plan

Raw JSON, operator tooling, and demo traces are not default enterprise chrome. Advanced routes explain who they are for.

## Do

1. Gate [`TechnicalDetails`](../../../lenses-enterprise/src/components/page/TechnicalDetails.tsx) behind Inspect/admin role (session or RBAC helper).
2. Move UX insights, Agent runtime, Toolset to **Labs** in [`navigationConfig.ts`](../../../lenses-enterprise/src/nav/navigationConfig.ts) / [`HeaderSettingsMenu.tsx`](../../../lenses-enterprise/src/components/HeaderSettingsMenu.tsx).
3. Apply `ADVANCED_SURFACE_FRAMES` from `studioVisibleCopy` on Fleet, Agent runtime, Toolset, Matrix routes.
4. Remove **Trace sample story** / **Trace repo (demo)** from default primary actions on [`HomePage.tsx`](../../../lenses-enterprise/src/pages/HomePage.tsx), [`PlanPage.tsx`](../../../lenses-enterprise/src/pages/PlanPage.tsx), [`ProjectDetailPage.tsx`](../../../lenses-enterprise/src/pages/ProjectDetailPage.tsx).

## Check

```bash
scripts/fl-studio-ux-pdca/check-phase-gate.sh S03
```

## Act

Fix inspect gating, Labs menu, advanced framing, or demo trace removal until S03 gate is green; then proceed to S04.
