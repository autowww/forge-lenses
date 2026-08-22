# U08 — Rescan + backlog v4 + closeout

**Executor:** Composer 2.5

## Plan

Verify UX3 remediation with a fresh Playwright crawl v4, publish backlog v4 (new opportunities only), run full gate suite.

## Do

1. Ensure `workbench/studio-ux-crawl-v4.mjs` writes crawl report under `workbench/studio-ux-crawl-v4/`.
2. Produce canvas **lenses-studio-ux-backlog-v4** (path: `.cursor/projects/home-lzvyahin-Code/canvases/lenses-studio-ux-backlog-v4.canvas.tsx`) noting FLS3-001…006 resolved.
3. Run `./scripts/fl-studio-ux3-pdca/check-phase-gate.sh all`.
4. Run `pytest` (forge-lenses root) and `cd lenses-enterprise && npm test && npm run build`.

## Check

```bash
scripts/fl-studio-ux3-pdca/check-phase-gate.sh U08
scripts/fl-studio-ux3-pdca/check-phase-gate.sh all
./scripts/studio-ux-crawl-gate.sh
pytest
cd lenses-enterprise && npm test && npm run build
```

## Act

Fix crawl regressions or gate failures until U08 and full suite are green.
