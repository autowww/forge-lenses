# V03 — Index bundle split (&lt;700 KB)

**Executor:** Composer 2.5

**Backlog:** FLS4-003

## Plan

Reduce the main Studio index chunk below **700 KB** by lazy-loading `HomePage` and extending Vite `manualChunks` for plan-depth and wizard surfaces.

## Do

1. Lazy-load `HomePage` in [`App.tsx`](../../../lenses-enterprise/src/App.tsx) via `React.lazy` + `Suspense`.
2. Extend [`vite.config.ts`](../../../lenses-enterprise/vite.config.ts) `manualChunks` — document index chunk target (&lt;700 KB) in gate comments or this prompt.
3. Verify `npm run build` completes; inspect emitted `index-*.js` size under `lenses/static/studio/assets/`.

## Check

```bash
scripts/fl-studio-ux4-pdca/check-phase-gate.sh V03
cd lenses-enterprise && npm run build
```

## Act

Fix lazy routes or chunk config until V03 gate is green; then proceed to V04.
