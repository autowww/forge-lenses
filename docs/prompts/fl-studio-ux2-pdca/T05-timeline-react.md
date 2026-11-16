# T05 — Timeline React Gantt

**Executor:** Composer 2.5

**Backlog:** FLS2-006

## Plan

Replace default Gantt HTML injection with structured API data and a React chart component.

## Do

1. Extend timeline handler in [`lenses/serve.py`](../../../lenses/serve.py) to emit `gantt_bars: [{id, label, start, end, status}]` alongside existing HTML.
2. Add [`TimelineGantt.tsx`](../../../lenses-enterprise/src/components/plan/TimelineGantt.tsx) — CSS grid bars with human labels.
3. Update [`TimelinePage.tsx`](../../../lenses-enterprise/src/pages/TimelinePage.tsx): default to React Gantt; remove `dangerouslySetInnerHTML` for `gantt_html`.

## Check

```bash
scripts/fl-studio-ux2-pdca/check-phase-gate.sh T05
cd lenses-enterprise && npm test
```

## Act

Fix timeline API, React Gantt, or page wiring until T05 gate is green; then proceed to T06.
