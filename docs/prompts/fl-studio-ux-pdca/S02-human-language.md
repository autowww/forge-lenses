# S02 — Human language layer

**Executor:** Composer 2.5

**Backlog:** FLS-001, FLS-002, FLS-003, FLS-004

## Plan

Default Studio copy is human-readable. Technical codes, paths, and API methods live behind Advanced/Inspect surfaces.

## Do

1. Rename nav nouns in [`lenses-enterprise/src/nav/studioVisibleCopy.ts`](../../../lenses-enterprise/src/nav/studioVisibleCopy.ts): **Backlog files**, **Documentation review**, **AI agents** (and related WBS/Docs health/Agentic bridge labels).
2. Expand `STUDIO_GLOSSARY` and wire [`GlossaryHint`](../../../lenses-enterprise/src/components/page/GlossaryHint.tsx) on Plan scope bar and Knowledge H1s.
3. Ban `:8080`, `workspace-md`, `ogs:demo:` from default chrome in errors, breadcrumbs, readiness helpers — use [`resolveUxFailure`](../../../lenses-enterprise/src/lib/uxPageState.ts).
4. Humanize empty states on Evidence, Agentic bridge, Decisions pages (no `GET /api/...` in main column).

## Check

```bash
scripts/fl-studio-ux-pdca/check-phase-gate.sh S02
```

## Act

Extend label maps, glossary, and empty-state copy until S02 gate is green; then proceed to S03.
