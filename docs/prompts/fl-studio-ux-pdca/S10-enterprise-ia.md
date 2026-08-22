# S10 — Enterprise IA + shell polish

**Executor:** Composer 2.5

**Backlog:** FLS-006, FLS-007, FLS-024, FLS-026, FLS-028, FLS-033, FLS-034, FLS-036, FLS-038, FLS-039, FLS-040, FLS-041, FLS-043, FLS-044, FLS-046

## Plan

Stable Setup / Governance / Labs IA; unified evidence naming; Foundry demoted; trust and narrative polish across Work surfaces.

## Do

1. Unify Evidence naming in [`studioVisibleCopy.ts`](../../../lenses-enterprise/src/nav/studioVisibleCopy.ts) + sidebars (FLS-006).
2. Demote Foundry/Dark Factory behind Labs in [`navigationConfig.ts`](../../../lenses-enterprise/src/nav/navigationConfig.ts) (FLS-007).
3. Split gear menu: Setup / Governance / Labs via `getSettingsGearMenuSections` (FLS-024).
4. Simplify Flow vs Artifacts onboarding; reduce Classic / Full workspace escapes (FLS-026, FLS-028).
5. Extend ExecutiveSummaryStrip beyond Home; soften matrix density; ban internal status tokens (FLS-033, FLS-034, FLS-036).
6. Fleet runner story, Copilot sources default-open, Agent runtime approval summary (FLS-038–040).
7. Risk destinations, Boards card face, collapse workspace directory listing, breadcrumb workspace name (FLS-041, FLS-043, FLS-044, FLS-046).

## Check

```bash
scripts/fl-studio-ux-pdca/check-phase-gate.sh S10
cd lenses-enterprise && npm run build
```

## Act

Fix IA splits, naming, and shell polish until S10 gate is green; then proceed to S11.
