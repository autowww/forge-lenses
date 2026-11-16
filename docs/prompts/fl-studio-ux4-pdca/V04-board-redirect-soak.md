# V04 — Board redirect soak + handbook update

**Executor:** Composer 2.5

**Backlog:** FLS4-004

## Plan

Add `_studio_redirect` for classic `/board/:id` routes and document board/websites browse retirement in the handbook soak checklist.

## Do

1. Extend [`lenses/serve.py`](../../../lenses/serve.py) — `_studio_redirect` for `/board` paths to `/studio/board/…`.
2. Update [`docs/handbook-public/studio-classic-ui-retirement.md`](../../handbook-public/studio-classic-ui-retirement.md) — note `/board` and `/websites/browse` embed retirement status under soak criteria.

## Check

```bash
scripts/fl-studio-ux4-pdca/check-phase-gate.sh V04
pytest tests/ -q -k serve 2>/dev/null || pytest tests/ -q --maxfail=1
```

## Act

Fix redirect mapping or handbook until V04 gate is green; then proceed to V05.
