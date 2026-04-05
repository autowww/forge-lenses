# Lenses Studio shell — API mapping and gaps

Maps **shell modules** to **existing** Lenses JSON APIs and lists **missing signals** for future phases (dependency graph, confidence scores, publish parity records, curated decision log).

## Current wiring (MVP)

| Shell module | Data source | Notes |
|--------------|-------------|--------|
| **Context bar — workspace label** | `GET /api/workspace-state` (`workspace_root`, `resolved_at`) | Same payload as `WorkspaceContext`. |
| **Executive KPI strip — counts** | `GET /api/workspace-state?git_extended=1` | Children (git repos), `websites`, `wbs`, `roadmaps` arrays; standards compliance per child when present. |
| **Executive KPI strip — delivery pulse (7d commits)** | `GET /api/chart-data/overview` | Sums `charts.commit_daily.series[].count`; failure degrades gracefully (hide or “—”). |
| **Attention stream** | Derived client-side from workspace-state | Dirty working trees, weak/absent standards scores, missing roadmaps/WBS, optional site coverage hints. Not a separate API. |
| **Evidence rail** | Static routes + `GET /api/workspace-state` | Links to `/docs/`, `/tutorials`, `/workspace-md`, `/search`; “API” row points at `/api/workspace-state` for traceability. |

## Gaps (next / later)

| Desired signal | Needed for | Suggested direction |
|----------------|-------------|---------------------|
| **Cross-repo dependency graph** | Dependency risk KPI, ranked dependency news | New read model or scan of `ROADMAP.md` / WBS + git submodule graph; API e.g. `/api/workspace-dependencies`. |
| **Roadmap / WBS confidence** | Outcome confidence KPI | Authoring convention + parser or manual field in plan spine. |
| **Publish parity / stale deploy** | Publish parity KPI, site news | Workspace-level `publish-record.json` or CI artifact pointers; optional parity script integration. |
| **Decision log with owners** | Executive news “decision needed” | Structured `forge/charge.md` or registry entries with owner + due date. |
| **Compare period truth** | True trend vs previous period | Persisted snapshots or git-timestamped extracts; not just UI dropdown. |
| **Role-based ownership** | Owner on KPIs/news | RBAC from `lenses-access.json` + mapping to GitHub or directory owners. |

## Confidence labels (honest MVP)

KPIs and news items use **Medium** confidence where data is live workspace scan (**`resolved_at`**) without independent audit. **Low** when chart API fails or data is partial. **High** reserved for future signed or CI-backed signals.
