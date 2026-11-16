# ADR-018 — Closed-loop Cursor / Claude handoff bridge (Sprint B5)

## Status

Accepted — implemented in forge-lenses.

## Context

Agent-assisted execution (Cursor, Claude Code, similar) was disconnected from the **orchestration spine**: launch packs and prompts were ad hoc, and **returns** (branches, PRs, builds, tests, evidence) did not reconcile back into the same graph as work items, review packs, and release readiness.

## Decision

1. **Graph entity kinds** — Add **`handoff_package`**, **`handoff_target`**, **`prompt_bundle`**, **`context_bundle`**, **`execution_session`**, **`execution_return`**, **`sync_checkpoint`**, **`output_manifest`**, **`file_change_summary`**, **`code_review_ref`**, **`build_test_return`** to **`ENTITY_KINDS`**.
2. **Edges** — Add **`scopes_handoff`** (package → work unit) and **`session_for`** (session → package). Reuse existing edges to link launch packs, recipes, evidence, review/assay artifacts where the fixture and services attach them.
3. **Registry** — Ship **`lenses/bridge/data/handoff_bridge_registry.json`**: per-**target** (**`cursor`**, **`claude`**) export templates (**markdown**, **task**, **summary**); **no** hardcoded agent instructions in code — formatting only.
4. **Services** — **`handoff_service`**: create package, **export** (target-specific render), **ingest return** with **content fingerprint** idempotency, **gaps** / **status**, **reconcile** session. Partial returns and stale/incomplete signals are explicit in API payloads.
5. **APIs** — **`GET/POST /api/handoffs/*`** and **`GET/POST /api/execution-sessions/*`** as documented in **`lenses/website/http-api-and-routes.md`**. Feature flag **`LENSES_EXPERIMENTAL_HANDOFF_BRIDGE_B5`** (default on when the orchestration graph is on).
6. **Migration v7** — Partial index on **`ogs_entity(kind, updated_at)`** for handoff-related kinds (list/status queries).
7. **UI** — **`HandoffLoopPanel`** on Studio **Plan**, **Today** (delivery), **project** dashboard, and **`story-hub`** **`handoff_loop`** block when enabled (no full redesign).
8. **Demo** — **`orchestration-graph.demo.json`** includes a scoped story handoff, Cursor-style exports, simulated return (files, PR, build/test, review ref), checkpoint, and **gaps** before assay/release.

## Consequences

- **Positive** — Handoff and return are **first-class orchestration objects** with traceability into work, evidence, and readiness views.
- **Negative** — No **real-time IDE** or vendor-specific plugins; export is **file/API** shaped, not live editor sync.
- **Follow-up** — Optional **webhook** or **CLI** ingest, richer **human approval** workflow, and additional **targets** via registry only.

## Deferred / non-goals

- Full **real-time IDE plugin** integration unless added later as a separate track.
- **Vendor lock-in** to a single model or tool — targets remain **registry-driven** formatters.
