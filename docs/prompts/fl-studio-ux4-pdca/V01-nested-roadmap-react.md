# V01 — Nested roadmap iframe → React

**Executor:** Composer 2.5

**Backlog:** FLS4-001

## Plan

Replace `NestedRoadmapWorkspaceFrame` iframe embed (`/nested-roadmap-view.html`) with a React `NestedRoadmapHorizon` host backed by structured JSON from the Python server.

## Do

1. Add `GET /api/nested-roadmap-config` in [`lenses/serve.py`](../../../lenses/serve.py) (reuse workspace matrix data from `nested_roadmap_workspace.py`).
2. Ensure [`NestedRoadmapHorizon.tsx`](../../../lenses-enterprise/src/components/plan/NestedRoadmapHorizon.tsx) fetches the API and renders KS drill-down.
3. Update [`NestedRoadmapWorkspaceFrame.tsx`](../../../lenses-enterprise/src/components/plan/NestedRoadmapWorkspaceFrame.tsx) to import and render `NestedRoadmapHorizon` — remove `nested-roadmap-view.html` iframe `src`.

## Check

```bash
scripts/fl-studio-ux4-pdca/check-phase-gate.sh V01
cd lenses-enterprise && npm run build
```

## Act

Fix API wiring or React host until V01 gate is green; then proceed to V02.
