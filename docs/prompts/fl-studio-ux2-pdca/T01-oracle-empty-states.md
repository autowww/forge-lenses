# T01 — Human-copy oracle + sparse workspace guides

**Executor:** Composer 2.5

**Backlog:** FLS2-001, FLS2-002

## Plan

Regression-proof human-readable Studio chrome with a Playwright oracle; sparse workspaces get progressive empty-state guidance instead of blank shells.

## Do

1. Add [`lenses-enterprise/e2e/studio-human-copy-oracle.spec.ts`](../../../lenses-enterprise/e2e/studio-human-copy-oracle.spec.ts): visit core routes, assert body text does **not** match `/(GET \/api|:8080|workspace-md|ogs:demo|Trace sample)/i`.
2. Add `test:e2e:human-copy` script in [`lenses-enterprise/package.json`](../../../lenses-enterprise/package.json).
3. Add [`WorkspaceSparseGuide.tsx`](../../../lenses-enterprise/src/components/onboarding/WorkspaceSparseGuide.tsx); wire on Home, Projects, Plan when workspace scan is sparse.
4. Optional wrapper: [`scripts/studio-human-copy-oracle.sh`](../../../scripts/studio-human-copy-oracle.sh).

## Check

```bash
scripts/fl-studio-ux2-pdca/check-phase-gate.sh T01
cd lenses-enterprise && npm run test:e2e:human-copy
```

## Act

Fix oracle spec, npm script, or sparse guides until T01 gate is green; then proceed to T02.
