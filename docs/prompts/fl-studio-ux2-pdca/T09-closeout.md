# T09 — Rescan + backlog v3 + closeout

**Executor:** Composer 2.5

## Plan

Verify UX2 remediation with a fresh Playwright crawl, publish backlog v3 (new ideas only), run full gate suite.

## Do

1. Add `workbench/studio-ux-crawl-v3.mjs`; write crawl report under `workbench/`.
2. Produce canvas **lenses-studio-ux-backlog-v3** (path: `.cursor/projects/home-lzvyahin-Code/canvases/lenses-studio-ux-backlog-v3.canvas.tsx`) noting FLS2-001…012 resolved.
3. Run `./scripts/fl-studio-ux2-pdca/check-phase-gate.sh all`.
4. Run `pytest` (forge-lenses root) and `cd lenses-enterprise && npm run build` when publishing.

## Check

```bash
scripts/fl-studio-ux2-pdca/check-phase-gate.sh T09
scripts/fl-studio-ux2-pdca/check-phase-gate.sh all
pytest
cd lenses-enterprise && npm run build
```

## Act

Fix crawl regressions or gate failures until T09 and full suite are green.
