# Forge plan UI map (roadmap → evidence)

This page describes how **artifacts** in a Forge-style repo connect to **tabs and panes** on **`/plan`** (Forge plan lens). It complements [HTTP API and routes](http-api-and-routes.html).

## Flow

Artifact chain on the plan lens (left to right):

1. **`ROADMAP.md`** shapes horizon and narrative; feeds milestone and story context into **`docs/requirements/WBS.md`**.
2. **`WBS.md`** holds milestones → epics → stories → **tasks (Sparks)**.
3. **Tasks / Sparks** drive execution and roll into **`forge/charge.md`** (operational status).
4. **`forge/charge.md`** and discipline work connect to **Ember / Versona / journal** evidence.

| Artifact | Role | Where it appears in the UI |
|----------|------|----------------------------|
| **`ROADMAP.md`** (optional) | Horizon, narrative, tables for charts | **Source** tab (iframe preview), **Roadmap summary** strip, **story Source** tab (section hits + canonical link) |
| **`docs/requirements/WBS.md`** | Requirements, milestone → epic → story → **task (Spark)** | **Plan** tab tree and center; **Definition** / **Product** in story cockpit; **`/wbs/view`** links |
| **`forge/charge.md`** | Operational status for active sparks | **Today** tab; **Execution** tab and **Source** tab in story cockpit |
| **Ember / Versona / journal** | Decisions and discipline sessions | **Decisions** tab; **Today** (pending Versona); evidence lists in the work graph |

**APIs** (same query shape: `wbs_p`, `repo`, optional `roadmap_p`; story APIs add `id`):

- **`GET /api/plan-spine`** — Single payload: WBS plan tree, Charge rows, roadmap summary metrics, paths to forge files.
- **`GET /api/story-hub?id=…`** — Story cockpit: synthesized WBS slots, roadmap hits, execution (sparks + Charge rows), decisions, canonical source links.
- **`GET /api/today-charge`** — **Today** tab: sections (in progress, blocked, banked, Versona, done) with links back to **`/plan?id=`**.

## URL query contract (deep links)

Supported parameters (see `lenses/plan_query.py`, mirrored in client `qs()`):

| Parameter | Purpose |
|-----------|---------|
| `repo` | Repository hint under the workspace |
| `wbs_p` | Relative path to `WBS.md` |
| `roadmap_p` | Optional `ROADMAP.md` path |
| `id` | Selected work item id in the tree |
| `tab` | `plan` (default), `today`, or `source` |

## Responsive checks (manual)

After UI changes, verify in the browser:

1. Below **992px** width, **Detail** defaults hidden until **Show detail** (unless a previous session chose to show it); **Hide detail** restores a wider center column.
2. **Story** / **Spark** selection still expands the center (**story mode**) and hides the detail rail; exiting a story selection restores the saved rail preference.
3. **Plan / Today / Source** and story **cockpit** tabs are reachable by keyboard (Tab, Arrow keys in tab lists where implemented).
