# T03 — Bundle code-splitting

**Executor:** Composer 2.5

**Backlog:** FLS2-004

## Plan

Reduce main Studio bundle size by splitting heavy vendor and route chunks in Vite.

## Do

1. Add `build.rollupOptions.output.manualChunks` in [`vite.config.ts`](../../../lenses-enterprise/vite.config.ts) — split `react`, `react-dom`, `jspdf`, `html2canvas`, wizard/foundry route groups.
2. Ensure heavy routes remain lazy in [`App.tsx`](../../../lenses-enterprise/src/App.tsx) (export menu, Foundry, Wizard, matrix).
3. Verify `npm run build` completes without regressions.

## Check

```bash
scripts/fl-studio-ux2-pdca/check-phase-gate.sh T03
cd lenses-enterprise && npm run build
```

## Act

Fix chunk config or lazy routes until T03 gate is green; then proceed to T04.
