# U05 — Timeline editor + metrics React host

**Executor:** Composer 2.5

**Backlog:** FLS3-003

## Plan

Retire default `editor_html` / `ForgeRoadmapDates` injection on Timeline; serve structured `date_rows` and metrics from the timeline API.

## Do

1. Extend [`lenses/timeline_api.py`](../../../lenses/timeline_api.py) — add `date_rows` from `extract_date_shift_model` and structured `metrics` from `extract_chart_metrics`.
2. Add [`RoadmapDateEditor.tsx`](../../../lenses-enterprise/src/components/plan/RoadmapDateEditor.tsx) — controlled inputs, `POST /api/roadmap-dates` (existing KS contract).
3. Add [`TimelineMetrics.tsx`](../../../lenses-enterprise/src/components/plan/TimelineMetrics.tsx) for horizon badges and progress bars.
4. Update [`TimelinePage.tsx`](../../../lenses-enterprise/src/pages/TimelinePage.tsx) — default React components; remove `ForgeRoadmapDates.init()`.
5. Update [`lenses/website/http-api-and-routes.md`](../../../lenses/website/http-api-and-routes.md) for `date_rows` and structured `metrics`.

## Check

```bash
scripts/fl-studio-ux3-pdca/check-phase-gate.sh U05
pytest tests/test_timeline_api_roadmap_link.py -q
cd lenses-enterprise && npm test
```

## Act

Fix timeline API, editor, or page wiring until U05 gate is green; then proceed to U06.
