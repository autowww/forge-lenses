# U03 — Classic server handler removal

**Executor:** Composer 2.5

**Backlog:** FLS3-001 (server)

## Plan

Delete classic HTML page handlers where Studio parity exists; replace with `_studio_redirect` 302 stubs. Keep API routes and iframe parity blockers documented in the retirement checklist.

## Do

1. Add `_studio_redirect` helper in [`lenses/serve.py`](../../../lenses/serve.py) for `/`, `/plan`, `/timeline`, `/wbs`, `/projects`, `/websites`, `/search`, `/tutorials`.
2. Remove `page_plan`, `page_timeline`, `page_overview` branches from active route dispatch in `serve.py`.
3. Trim unused classic page builders in `render.py` where redirects replace them.
4. Update [`docs/handbook-public/studio-classic-ui-retirement.md`](../../../docs/handbook-public/studio-classic-ui-retirement.md) — mark removed routes and surviving API/iframe surfaces.
5. Add pytest redirect smoke tests under `tests/`.

## Check

```bash
scripts/fl-studio-ux3-pdca/check-phase-gate.sh U03
pytest tests/ -k redirect -q
```

## Act

Fix redirect stubs or accidental handler deletion until U03 gate is green; then proceed to U04.
