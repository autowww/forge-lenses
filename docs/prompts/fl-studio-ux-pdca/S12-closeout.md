# S12 — Rescan + backlog v2 + closeout

**Executor:** Composer 2.5

## Plan

Verify remediation with a fresh Playwright crawl, publish backlog v2 (new ideas only), run full gate suite.

## Do

1. Add `workbench/studio-ux-crawl-v2.mjs`; write crawl report under `workbench/` or `lenses-enterprise/`.
2. Produce canvas **lenses-studio-ux-backlog-v2** (path: `.cursor/projects/home-lzvyahin-Code/canvases/lenses-studio-ux-backlog-v2.canvas.tsx`) noting FLS-001…048 resolved.
3. Run `./scripts/fl-studio-ux-pdca/check-phase-gate.sh all`.
4. Run `pytest` (forge-lenses root) and `cd lenses-enterprise && npm run build` when publishing.

## Check

```bash
scripts/fl-studio-ux-pdca/check-phase-gate.sh S12
scripts/fl-studio-ux-pdca/check-phase-gate.sh all
pytest
```

## Act

Fix crawl regressions or gate failures until S12 and full suite are green.
