# ADR-016 — Agentic bridge: governed agent execution (Sprint B3)

## Status

Accepted — implemented in forge-lenses.

## Context

Lenses exposed **LLM chat**, **SDLC copilot**, and **export** flows, but **agent execution** was largely **opaque**: little structured record of **which Versona scope**, **which recipe/tasklet**, **what policy mode**, or **what outputs** tied back to **work items** and **evidence**. Uncontrolled **write** paths risk autonomous mutation without auditability.

## Decision

1. **First-class graph kinds** — Extend **`ENTITY_KINDS`** with **`versona_family`**, **`versona_profile`**, **`tasklet`**, **`recipe`**, **`launch_pack`**, **`agent_run`**, **`agent_step`**, **`agent_output`**, **`approval_request`**, **`policy_rule`**, **`execution_target`**, **`drift_report`**, **`rules_manifest`**, **`prompt_template`**. Payloads carry **provenance**, **owner**, **status**, **timestamps**, **read-only vs write-capable**, and **approval** metadata.
2. **Edges** — Add **`executes`**, **`invokes`**, **`emits`**, **`seeks_approval`**, **`constrains`** to link runs → recipes/tasklets/outputs/approvals/policies.
3. **Registry** — Ship **`lenses/bridge/data/agentic_bridge_registry.json`**: **tasklet** categories (cognition, execution, review, packaging, governance), **recipe** definitions (vendor-neutral ids), **default policies**, **expected Cursor rule files per discipline** for drift.
4. **Discovery** — Scan **`forge/forge.config.yaml`** (PyYAML), **`.cursor/rules/*`**, and **`agents/recipes/**`** (configurable globs). Build a **rules manifest** and **drift** view: active families/disciplines, **missing expected** rule files, **orphan heuristics** for `versona-*` / `forge-*` files.
5. **Runs and approvals** — **`POST /api/agents/runs`** creates **`agent_run`** rows; **`write`** / **`approval_gated`** modes create **`approval_request`** and **`seeks_approval`** edges. **`POST …/approve`** requires **`confirm_human_approval`** for write-capable runs.
6. **Evidence** — **`POST /api/agents/outputs/<id>/link`** adds a **`references`** edge from **`agent_output`** to **`methodology_artifact`** or **`evidence`** and annotates the output payload.
7. **APIs** — **`GET /api/agents/enabled`**, **`versonas`**, **`recipes`**, **`tasklets`**, **`drift`**, **`policies`**, **`manifests`**, **`runs`**, **`runs/<id>`**, **`approvals`**; **`POST` launch-packs**, **runs**, **runs/approve**, **outputs/link** (loopback / allow-actions).
8. **Feature flag** — **`LENSES_EXPERIMENTAL_AGENTIC_BRIDGE_B3`** (default **on** when orchestration graph is on; **`0`** disables).
9. **Migration v5** — Composite index **`(kind, updated_at)`** on **`ogs_entity`** for agentic list queries.
10. **UI** — Studio **Knowledge → Agentic bridge** surfaces config, drift, catalog, runs, approvals, policies; **Plan → Story** linked as the recommended work context (no full Plan redesign).
11. **Demo seed** — **`orchestration-graph.demo.json`** includes a **read-only** run with **output → methodology artifact** edge, and an **approval-gated** run with **pending approval**.

## Consequences

- **Positive** — Observable agent configuration, explicit policy/approval gates, graph-linked outputs for traceability.
- **Negative** — Drift expectations are **registry-driven heuristics**, not a full parser of every Cursor rule frontmatter; deep vendor integrations remain **non-goals**.
- **Follow-up** — Inline **Plan** rail for recommended tasklets; **static museum** fixtures for **`/api/agents/*`**; richer **rules_manifest** persistence; automated **run** ingestion from copilot audit logs.
