# ADR-017 — Ceremony bridge: methodology-neutral orchestration (Sprint B4)

## Status

Accepted — implemented in forge-lenses.

## Context

Ceremonies were implicit in Markdown, calendars, and product copy. There was no shared **orchestration record** tying **neutral intent** (C1–C6), **Forge ritual names**, **delivery mode** (human vs agent-assisted), **required outputs**, **sign-off**, and **downstream decisions / evidence / work items**.

## Decision

1. **Graph entity kinds** — Add **`ceremony_intent`**, **`ceremony_template`**, **`ceremony_mapping`**, **`ceremony_instance`**, **`delivery_mode`**, **`ceremony_output`**, **`participant_role`**, **`moderator_role`**, **`signoff_record`**, **`followup_action`**, **`required_artifact_ref`**, **`decision_binding_rule`** to **`ENTITY_KINDS`**.
2. **Edges** — Add **`instantiates`** (instance → template), **`realizes_intent`** (template → intent), **`yields_output`** (instance → output), **`requires_input`** (template → required artifact ref), **`follows_up_with`** (instance → follow-up). Reuse **`references`**, **`contains`**, **`constrains`**, **`approves`** for mappings, roles, binding rules, and sign-off.
3. **Registry** — Ship **`lenses/bridge/data/ceremony_bridge_registry.json`**: **delivery mode** rules (binding vs non-binding, human sign-off), **mappings** (C1–C6 ↔ Forge rituals and Studio route hints), **templates** (pre-reads, required outputs, sign-off roles, allowed modes). Merge neutral labels from **`registry.v1.json`** **`ceremony_intents`**.
4. **Validation** — **`validate_projection_label`** rejects **Forge** display names that do not match the **explicit mapping** for the intent (no silent relabeling).
5. **Delivery modes** — Support **`human_only`**, **`hybrid`**, **`versona_only_non_binding`**, **`versona_assisted_human_binding`**. **Binding** output types cannot be recorded under **`versona_only_non_binding`**. **Binding** outputs require **human sign-off** on the instance before **`POST …/outputs`** succeeds (unless the mode disallows binding entirely).
6. **Outputs** — Each **`ceremony_output`** payload records **`delivery_mode`**, **`output_type`**, and **`binding`**. Optional **`linked_*`** graph links via **`references`** edges to **decisions**, **evidence**, **review packs**, **assay packets**, **tasks**.
7. **APIs** — **`GET /api/ceremonies/*`** (enabled, intents, mappings, templates, instances, instance bundle, agenda, readiness, inspector) and **`POST`** instances, outputs, sign-off. Feature flag **`LENSES_EXPERIMENTAL_CEREMONY_BRIDGE_B4`** (default on when the orchestration graph is on).
8. **Migration v6** — Index **`(kind, created_at)`** on **`ogs_entity`** for ceremony lists.
9. **UI** — Studio **Plan** and **Today** embed **`CeremonyBridgePanel`**: mapping inspector + readiness gaps + trace link (no full page redesign).
10. **Demo** — **`orchestration-graph.demo.json`** adds two **instances** (hybrid non-binding synthesis vs human-signed binding gate), **outputs**, **sign-off**, **follow-ups** linked to **story** / **task** / **methodology** entities.

## Consequences

- **Positive** — Ceremonies become **auditable orchestration objects** with explicit **bridge semantics** and **traceability** into decisions and work.
- **Negative** — No **calendar** or **notification** integration; readiness heuristics are **registry- and template-driven**, not a full workflow engine.
- **Follow-up** — Calendar feeds, notification hooks, richer **participant** attendance model, and **multi-methodology** mappings beyond Forge.

## Deferred / non-goals

- Full **calendar** integration and **messaging** / **notifications** layer (explicitly out of scope for B4).
