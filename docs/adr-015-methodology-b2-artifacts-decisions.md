# ADR-015 — Artifact, evidence, and decision bridge (Sprint B2)

## Status

Accepted — implemented in forge-lenses.

## Context

Sprint B1 added a **methodology bridge registry** and trace projections over the existing orchestration graph, but **Forge/Blueprints outputs** (Ore through release records, ADRs, review/assay packs) were still primarily **files** or ad-hoc payloads. Lenses needed **durable graph objects** with **lineage**, **governance** (sign-off), and **readiness gaps** without a second database or duplicated storage.

## Decision

1. **Neutral + Forge mapping** — Reuse **`ogs_entity`**. Methodology-specific rows use kinds **`methodology_artifact`**, **`decision_record`**, **`review_pack`**, **`assay_packet`**. Forge-facing names and neutral categories are defined in **`lenses/bridge/data/methodology_b2_registry.json`** (artifact profiles, decision profiles, gating hints, ingest defaults).
2. **Decisions** — **`decision_record`** payload carries **`decision_type`** (e.g. **`adr`**, **`directive`**, **`ember_log`**), problem/summary/alternatives/rationale/impact, **`binding`**, **`signoff_state`**, **`gates_allowed`**. Binding ADR/Directive sign-off requires **`confirm_human_signoff`** in the API when the profile marks **`human_signoff_required_for_binding`**.
3. **Review Pack / Assay Packet** — Dedicated entity kinds; aggregation views follow **`aggregates`** / **`references`** edges from the pack/packet to work, code, evidence, decisions, release, build, exceptions. Views expose **`source_inputs`** from **`bridge_evidence_doc_index`** when the row was ingested from markdown.
4. **Evidence ingestion** — **`POST /api/artifacts/import`** scans paths or roots, parses simple YAML frontmatter (flat keys such as **`lenses_forge_profile`**, **`lenses_decision_type`**) and path heuristics, upserts entities, and records **`bridge_evidence_doc_index`** (checksum, **`rel_path`**).
5. **Readiness** — **`GET /api/methodology/readiness`** returns explicit **`gaps`** (e.g. no **`assay_packet`** referencing the release, no signed binding directive) for Studio/delivery surfaces.
6. **APIs** — See **`lenses/website/http-api-and-routes.md`** § Methodology artifacts, evidence, and decisions (Sprint B2).
7. **UI** — Forge Studio **Knowledge** adds evidence and decision registries and a generic graph record view; **Delivery** sidebar links **Release readiness**. No full redesign of Plan/Project pages in this sprint.
8. **Demo** — **`orchestration-graph.demo.json`** extended with a **Product Spark Plan**, implementation evidence, ADR/Directive, Review Pack, Assay Packet, launch record, and edges for lineage and aggregation.

## Consequences

- **Positive** — One graph for traceability and methodology governance; local-first markdown ingest; explicit missing-artifact signals.
- **Negative** — Frontmatter parser is intentionally minimal (no nested YAML blocks); external connector ingestion and publishing workflows remain out of scope.
- **Follow-up** — Deeper Plan/Project/Delivery integration (linked artifacts per WBS id), Traceability drawer gap sync, static museum fixtures for new GET paths, richer **`gating_rules`** evaluation beyond current heuristics.
