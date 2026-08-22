# U07 — Publish health drill-down popover

**Executor:** Composer 2.5

**Backlog:** FLS3-006

## Plan

Publish nav badge opens an inline site-health preview without navigating away; full list remains on `/websites`.

## Do

1. Add `PublishHealthPopover` component (portal) — reuse [`publishHealthSummary.ts`](../../../lenses-enterprise/src/lib/publishHealthSummary.ts) and per-site rows from `state.websites` with `siteHealthSummary` logic from [`WebsitesPage.tsx`](../../../lenses-enterprise/src/pages/WebsitesPage.tsx).
2. Wire badge click in [`TopNavigation.tsx`](../../../lenses-enterprise/src/components/TopNavigation.tsx) — `aria-expanded`, Escape closes, focus trap; "View all sites" → `/websites`.
3. Add `le-top-nav__publish-health--*` styles in [`enterprise-shell.css`](../../../lenses-enterprise/src/enterprise-shell.css) if not already present from U06.

## Check

```bash
scripts/fl-studio-ux3-pdca/check-phase-gate.sh U07
cd lenses-enterprise && npm run build
```

## Act

Fix popover wiring or a11y until U07 gate is green; then proceed to U08.
