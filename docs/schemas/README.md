# Contract JSON Schemas (Forge Lenses)

Authoritative schemas live beside this README as **`*.schema.json`**.

- **`$id` namespace** — `https://lenses.forgesdlc.com/schemas/*.schema.json`.
- Companion samples **`docs/examples/sample-<stem>.json`** mirror each stem (`tests/test_docs_schemas.py`).
- **`generator/export_schema_index.py`** writes **`docs/generated/schema-index.json`** for auditors/scorecards.
- Operational notes + diagrams — **`docs/handbook-public/builders-schemas.md`** and **`docs/handbook-public/builders-openapi.md`**.

Coverage (**14 bundles** — expand schemas + samples together):

| Schema | Stability | Notes |
| ------ | --------- | ----- |
| `api-error.schema.json` | stable | `{ "ok": false, … }` envelope surfaced by HTTP handlers |
| `oauth-oidc-endpoint.schema.json` | stable | Issuer hints for OIDC narratives |
| `docs-health-work-item.schema.json` | stable | Work items rendered by Docs Health |
| `workspace-mount-descriptor.schema.json` | stable | Studio workspace root rationales |
| `workspace-scan-result.schema.json` | stable | Cached workspace scan payloads + enrichment keys |
| `audit-notification.schema.json` | stable | Evidence-friendly notifications |
| `wizard-domain.schema.json` | experimental | `payload.wizard_domain` blobs |
| `wizard-session.schema.json` | experimental | `.lenses-local/blueprints-wizard` envelopes |
| `wizard-stage-response.schema.json` | beta | Typical `/api/blueprints/wizard/*` acknowledgements |
| `cursor-launch-pack-manifest.schema.json` | experimental | Cursor Launch Pack metadata |
| `fleet-job-descriptor.schema.json` | experimental | Forge Fleet automation narration |
| `studio-project-summary.schema.json` | experimental | Studio project row summaries |
| `rbac-scope-set.schema.json` | experimental | Scoped automation tokens |
| `webhook-envelope-meta.schema.json` | experimental | Outbound webhook metadata |
