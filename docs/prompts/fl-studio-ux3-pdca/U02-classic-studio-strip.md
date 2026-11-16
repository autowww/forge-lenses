# U02 — Classic UI strip from Studio chrome

**Executor:** Composer 2.5

**Backlog:** FLS3-001 (Studio)

## Plan

Remove default Classic UI escape hatches from Studio pages and components so operators stay in `/studio/` unless inspect-only technical details are enabled.

## Do

1. Remove `FULL_WORKSPACE_UI` imports and Classic outbound links from all files under [`lenses-enterprise/src/pages/`](../../../lenses-enterprise/src/pages/).
2. Remove `classicPlanHref` fallbacks from [`PlanPage.tsx`](../../../lenses-enterprise/src/pages/PlanPage.tsx).
3. Demote or remove Classic pills in plan/delivery/sites components; update [`navigationConfig.ts`](../../../lenses-enterprise/src/nav/navigationConfig.ts) sidebar classic `href` entries to Studio routes.
4. Keep inspect-only technical surfaces behind `canShowTechnicalDetails()` where parity blockers remain.

## Check

```bash
scripts/fl-studio-ux3-pdca/check-phase-gate.sh U02
cd lenses-enterprise && npm run build
```

## Act

Fix remaining Classic link surfaces until U02 gate is green; then proceed to U03.
