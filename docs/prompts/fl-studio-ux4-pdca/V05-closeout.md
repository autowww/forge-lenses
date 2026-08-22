# V05 — Rescan + backlog v5 + closeout

**Executor:** Composer 2.5

## Plan

Verify UX4 remediation with a fresh Playwright crawl v5, publish backlog v5 (new opportunities only), run full gate suite.

## Do

1. Add `workbench/studio-ux-crawl-v5.mjs` — copy v4; assert nested roadmap React host, `/local-site/` Sites preview, and no Classic embed regressions.
2. Produce canvas **lenses-studio-ux-backlog-v5** (path: `.cursor/projects/home-lzvyahin-Code/canvases/lenses-studio-ux-backlog-v5.canvas.tsx`) noting FLS4-001…004 resolved.
3. Run `./scripts/fl-studio-ux4-pdca/check-phase-gate.sh all`.
4. Run `pytest` (forge-lenses root) and `cd lenses-enterprise && npm test && npm run build`.

## Check

```bash
scripts/fl-studio-ux4-pdca/check-phase-gate.sh V05
scripts/fl-studio-ux4-pdca/check-phase-gate.sh all
pytest
cd lenses-enterprise && npm test && npm run build
```

## Act

Fix crawl regressions or gate failures until V05 and full suite are green.
