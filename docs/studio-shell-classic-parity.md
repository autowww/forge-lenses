# Classic Lenses parity — Studio enterprise shell

**Rule (product):** User-visible features added in **Lenses Studio** should be **ported to Classic** so both surfaces stay equivalent when feasible ([`interface-pages.md`](../lenses/website/interface-pages.md) — dual-surface architecture).

## This shell (Flow lens chrome)

| Studio (shipped) | Classic parity plan |
|------------------|---------------------|
| Context bar (scope, horizon, compare, saved view / filters stubs) | When compare and saved views are backed by real data, add a comparable strip to Classic **Overview** (`/`) and align query params or session defaults. Until then, Classic keeps existing overview layout; no stub-only duplication required. |
| Executive KPI strip + attention stream + evidence rail | Port as an optional **compact executive block** above the Classic workspace table on `/`, reusing `GET /api/workspace-state` and `GET /api/chart-data/overview`. Defer until stakeholders want Classic to match Studio’s leadership-first ordering. |
| Navigation labels (Workspace, Knowledge, side nav) | Update Classic **sidebar** and top nav labels in `lenses/render.py` (`lenses_sidebar_html` and related) to the same speakable strings so users switching between Classic and Studio do not remap vocabulary. **Do in the same release** when Studio labels ship. |

## Out of scope

Electron-only window chrome (frameless, drag strip) remains Studio-only; Classic does not need it.
