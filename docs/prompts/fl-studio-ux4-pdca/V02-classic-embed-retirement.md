# V02 — Classic embed retirement (Sites browse + board link)

**Executor:** Composer 2.5

**Backlog:** FLS4-002

## Plan

Studio Sites browse should preview via `/local-site/<repo>/…` (same-origin static root) instead of classic `/websites/browse` iframe chrome. Remove Classic outbound board editor link from the Boards hub.

## Do

1. Update [`WebsitesBrowsePage.tsx`](../../../lenses-enterprise/src/pages/WebsitesBrowsePage.tsx) to embed `/local-site/<site>/…` (not `/websites/browse?site=…`).
2. Remove `FULL_WORKSPACE_UI.openFullBoardEditor` from [`BoardsArtifactsHub.tsx`](../../../lenses-enterprise/src/components/boards/BoardsArtifactsHub.tsx).

## Check

```bash
scripts/fl-studio-ux4-pdca/check-phase-gate.sh V02
cd lenses-enterprise && npm run build
```

## Act

Fix preview URL or hub copy until V02 gate is green; then proceed to V03.
