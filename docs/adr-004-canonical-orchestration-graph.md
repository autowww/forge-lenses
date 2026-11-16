# ADR 004: Canonical orchestration graph (Sprint 1)

## Status

Accepted (v1 SQLite schema, trace API, Studio drawer, demo seed).

## Context

Forge Studio needs a **single reconcilable model** for SDLC objects and relationships so work can be traced from planning through delivery without duplicating ad-hoc JSON shapes per screen. Prior slices (delivery signals, WBS, charge) remain sources of truth for their domains; the orchestration graph **indexes and links** stable projections.

## Decision

1. **Storage** — Dedicated SQLite file **`<workspace>/.lenses-local/lenses-orchestration.sqlite`** (ignored by git), distinct from search FTS. Schema version in **`_ogs_schema`**; migrations in **`lenses/orchestration_graph/migrate.py`**. Portfolio indexes and Sprint 2 kinds/edges are in **schema v2** (see **ADR 005**).
2. **Entities** — Rows in **`ogs_entity`**: `id` (stable string, e.g. `ogs:demo:story:…`), `kind`, `display_name`, `summary`, `payload_json`, `external_ref`, `source_system`, `source_record_id`, timestamps. Canonical kinds: objective, initiative, epic, story, task, repo, branch, change_request, commit, build, artifact, release, environment, test_run, vulnerability, incident, evidence.
3. **Edges** — Rows in **`ogs_edge`**: `id`, `from_id`, `to_id`, `kind`, `payload_json`, provenance fields, **`UNIQUE(from_id, to_id, kind)`** for reconciliation. Canonical edge kinds: **contains**, **blocks**, **implements**, **tests**, **deploys**, **affects**, **caused_by**, **mitigates**, **documented_by**, **targets** (navigation / scope).
4. **Provenance** — Every row carries **`source_system`** and **`source_record_id`** (and optional **`external_ref`**) so GitHub/GitLab/Jenkins importers can upsert without clobbering unrelated rows.
5. **Demo seed** — **`lenses/fixtures/orchestration-graph.demo.json`** loaded when the DB is empty and **`LENSES_ORCHESTRATION_AUTO_SEED`** is on (default). **`POST /api/orchestration/seed-demo`** force-reloads the demo slice (loopback / **`LENSES_ALLOW_ACTIONS`** policy).
6. **API** — Read **`GET /api/orchestration/trace`**, **`GET /api/orchestration/entity`**, **`GET /api/orchestration/status`**, **`GET /api/orchestration/enabled`**. BFS trace with **`max_depth`** / **`max_nodes`** caps.
7. **UI** — **`TraceabilityDrawer`** (portal) + **`TraceabilityLaunchButton`** on Workspace (Home), Plans (summary + Today band), Delivery (pipeline card), Projects (dashboard).
8. **Feature flag** — **`LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH`** (default on; explicit off disables APIs and UI data).

## Consequences

- **Importers** should map vendor objects to `ogs_entity` / `ogs_edge` via adapters; domain logic stays in Python services, not in React.
- **Scale** — Large workspaces need paging or scoped traces (future); v1 is optimized for hundreds of nodes per workspace.
- **Classic parity** — Not required for Sprint 1; Studio is the primary consumer.

## Related

- Walkthrough: **`docs/orchestration-graph-sprint1-walkthrough.md`**
- HTTP: **`lenses/website/http-api-and-routes.md`**
