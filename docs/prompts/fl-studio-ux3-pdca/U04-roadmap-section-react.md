# U04 — Roadmap section React preview

**Executor:** Composer 2.5

**Backlog:** FLS3-002

## Plan

Replace roadmap section HTML injection with structured API data and a React preview component. Keep `NestedRoadmapWorkspaceFrame` iframe horizon unchanged (deferred to FLS4).

## Do

1. Extend roadmap-section handler in [`lenses/serve.py`](../../../lenses/serve.py) to return `{ title, body_lines, section_id }` alongside optional legacy `html`.
2. Reuse [`lenses/roadmap_outline.py`](../../../lenses/roadmap_outline.py) `find_section` / `ParsedRoadmap`.
3. Add [`RoadmapSectionPreview.tsx`](../../../lenses-enterprise/src/components/plan/RoadmapSectionPreview.tsx) — prose + lists; no raw HTML injection.
4. Update [`RoadmapSectionPage.tsx`](../../../lenses-enterprise/src/pages/RoadmapSectionPage.tsx) to use structured payload; remove `dangerouslySetInnerHTML`.

## Check

```bash
scripts/fl-studio-ux3-pdca/check-phase-gate.sh U04
cd lenses-enterprise && npm test
```

## Act

Fix roadmap API or React preview until U04 gate is green; then proceed to U05.
