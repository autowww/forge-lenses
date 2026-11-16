# S11 — Narrative polish

**Executor:** Composer 2.5

**Backlog:** FLS-015, FLS-027, FLS-035, FLS-042, FLS-045, FLS-047

## Plan

Autonomy, Publish, milestones, and identity read as enterprise narrative — not score jargon or debug chrome.

## Do

1. Plain readiness story on [`AutonomyMaturityPage.tsx`](../../../lenses-enterprise/src/pages/AutonomyMaturityPage.tsx) / project maturity pages (FLS-015).
2. Single home for Release checklist in `navigationConfig` — remove Work/Knowledge duplicate (FLS-027).
3. Consistent [`PageHeader`](../../../lenses-enterprise/src/components/page/) on Boards / sparse hubs like [`BoardsArtifactsHub.tsx`](../../../lenses-enterprise/src/components/boards/BoardsArtifactsHub.tsx) (FLS-035).
4. Publish human site health on [`WebsitesPage.tsx`](../../../lenses-enterprise/src/pages/WebsitesPage.tsx) (FLS-042).
5. Milestone business outcome field in Plan spine (FLS-045).
6. Guided local identity when not signed in — header profile (FLS-047).

## Check

```bash
scripts/fl-studio-ux-pdca/check-phase-gate.sh S11
```

## Act

Polish narrative, headers, and identity until S11 gate is green; then proceed to S12.
