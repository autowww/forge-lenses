# S05 — First value + scope

**Executor:** Composer 2.5

**Backlog:** FLS-016, FLS-017, FLS-018

## Plan

A lead reaches scoped Today/Plan in five minutes without configuring raw file paths or graph ids.

## Do

1. Add first-run wizard component under `lenses-enterprise/src/components/onboarding/` (pick project → backlog → confirm).
2. Friendly backlog titles in [`PlanScopeBar.tsx`](../../../lenses-enterprise/src/components/plan/PlanScopeBar.tsx) and Timeline selects (never raw paths).
3. Release checklist picker on methodology readiness (discovered releases, not `ogs:…` free text) — see [`MethodologyBridgePages.tsx`](../../../lenses-enterprise/src/pages/MethodologyBridgePages.tsx).

## Check

```bash
scripts/fl-studio-ux-pdca/check-phase-gate.sh S05
```

## Act

Wire wizard, scope labels, and readiness picker until S05 gate is green; then proceed to S06.
