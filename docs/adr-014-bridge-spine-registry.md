# ADR-014 — Methodology bridge spine and registry (Sprint B1)

## Status

Accepted — implemented in forge-lenses.

## Context

Lenses already persists a **single orchestration graph** (OGS entities/edges in SQLite) for planning-through-delivery traceability. Methodology vocabulary (Forge SDLC, generic SDLC, PDLC) risked **parallel silos** if each lens introduced its own tracking store.

## Decision

1. **Neutral spine** — Reuse **OGS** as the physical store. **Canonical kinds** (`work_unit`, `artifact_ref`, `release_ref`, …) are derived via **`ogs_kind_to_canonical`** in a **versioned JSON registry** (`lenses/bridge/data/registry.v1.json`), not a second entity table per methodology.
2. **Bridge registry** — Ships with the package: lifecycle rows (neutral ↔ PDLC ↔ SDLC ↔ Forge), ceremony intents **C1–C6**, terminology rows (with explicit **conflict notes**), artifact and status mappings, **term collision registry**, and **canonical trace rules** for graph-completeness scoring.
3. **Overlay table** — Migration **v3** adds **`bridge_spine_overlay`** (optional per-entity owner, freshness, trust, provenance JSON) keyed by `entity_id` → `ogs_entity`, for fields not carried in OGS rows.
4. **Trace service** — **`bridge_trace_payload`** wraps `trace_subgraph`, enriches nodes with **canonical_kind**, **four-lens projections**, optional overlay, **root traceability score** (matched ÷ registry rules), and **root gaps** (missing recommended edge kinds).
5. **APIs** — **`GET /api/bridge/enabled`**, **`GET /api/bridge/registry`**, **`GET /api/bridge/registry/terms/<term>`**, **`GET /api/bridge/trace/<id>`**, **`GET /api/bridge/impact/<id>`**, **`GET /api/bridge/provenance/<id>`** (upstream), **`GET /api/bridge/neighbors/<id>`** (single hop), **`GET /api/bridge/gaps/<id>`**, **`GET /api/bridge/projections/<id>?lens=`**, **`POST /api/bridge/links`** (loopback / `LENSES_ALLOW_ACTIONS` only). Trace and projection responses include **`spine_meta`** (OGS timestamps + optional overlay).
6. **Feature flag** — **`LENSES_EXPERIMENTAL_BRIDGE_SPINE`** (default on when orchestration graph is on; set `0` to disable graph-using bridge routes). **Registry GET remains available** without the flag so docs/clients can read mappings offline.
7. **UI** — Existing **Traceability** drawer prefers **`/api/bridge/trace/…`** when enabled; shows lens tabs, completeness score, and gap hints. **Knowledge (workspace markdown)** gains demo launchers for **Ore** and **story** roots.
8. **Demo data** — **`orchestration-graph.demo.json`** extended with **`demand_signal`**, **`scoped_commitment`**, **`contributor`**, **`gate`** and bridge edges (**`originates_from`**, **`decomposes_to`**, **`reviewed_by`**, **`evidenced_by`**, **`gated_by`**) plus new **ENTITY_KINDS** / **EDGE_KINDS** in **`orchestration_graph/constants.py`**.

## Consequences

- **Positive** — One graph, many lenses; explicit conflict handling; scoring tied to declared rules, not ad-hoc UI.
- **Negative** — Canonical mapping is **heuristic** for some OGS kinds (e.g. branch → `work_unit`); overlays or future payload conventions may refine disambiguation.
- **Follow-up** — Human **sign-off** objects, connector-driven **freshness** writers into overlay, richer **PDLC outcome** projections, finer **meeting_ref** / **Versona** typing on OGS kinds.
