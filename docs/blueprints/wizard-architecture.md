# Blueprints Wizard — architecture

The wizard is implemented in **forge-lenses** only (experimental). This document complements the file map in [wizard-file-map.md](wizard-file-map.md) and the domain overview in [wizard-domain-model.md](wizard-domain-model.md).

## Request flow

1. **Studio** (`lenses-enterprise`) issues JSON requests via `api/http.ts` helpers (`apiGetJson`, `apiPostJson`, `apiPutJson`) to paths under `/api/blueprints/wizard/…`.
2. **`lenses/serve.py`** routes HTTP methods to thin handlers that import **`lenses.blueprints_wizard.api`** and related modules.
3. **Session state** is loaded and saved with **`session_store.py`** (JSON on disk under `.lenses-local/blueprints-wizard/sessions/`).
4. **Typed domain** data lives in `payload.wizard_domain`, normalized on both sides (`wizard_domain_normalize.py` / `wizardDomainNormalize.ts`).

## Key modules

| Area | Location | Role |
|------|----------|------|
| Feature gate | `lenses/blueprints_wizard/feature_flag.py` | Server APIs respect `LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD`. |
| Session document | `lenses/blueprints_wizard/schemas.py` | `WizardSessionDocument`, versioned payload. |
| HTTP JSON surface | `lenses/blueprints_wizard/api.py` | Session CRUD, refine, interpret, artifacts, recheck, launch pack, telemetry. |
| Telemetry | `lenses/blueprints_wizard/wizard_telemetry.py` | Optional JSONL append; `record_http_api_result` used from `serve.py` for selected POST handlers. |
| Client API | `lenses-enterprise/src/api/blueprintsWizard.ts` | Typed wrappers; includes `postWizardTelemetry` for opt-in client events. |
| Session UI | `lenses-enterprise/src/pages/BlueprintsWizardSessionPage.tsx` | Orchestrates shell state, persistence, LLM calls, and async error banners. |
| Step UI | `lenses-enterprise/src/blueprints-wizard/WizardStepBody.tsx`, `BlueprintsWizardShell.tsx` | Step panels and navigation. |
| Async UX helpers | `lenses-enterprise/src/blueprints-wizard/wizardAsyncUi.tsx` | Shared alert / retry row styling. |

## Telemetry

When `LENSES_BLUEPRINTS_WIZARD_TELEMETRY` is enabled, events are appended to:

`<workspace_root>/.lenses-local/blueprints-wizard/telemetry.jsonl`

Each line is a compact JSON object: `kind` (`api` or `client`), timestamps, optional `session_id`, `step_index`, `api` name, `ok`, `duration_ms`, `error_code`, and `dry_run` for recheck previews. No prompt text or file contents are logged.

Client `step_view` events require `VITE_BLUEPRINTS_WIZARD_TELEMETRY` and a successful `POST /api/blueprints/wizard/telemetry` (same experimental gate as other wizard routes).

**Operators:** for rotating or deleting `telemetry.jsonl` and cap behavior, see [Telemetry review](wizard-usage.md#telemetry-review) in the usage guide.

## Related docs

- [wizard-extending.md](wizard-extending.md) — how to add steps and artifact slices.
- [ADR: trust boundaries for GitHub](../adr-002-blueprints-wizard-trust-github.md).

## Static museum

Studio builds with `VITE_STATIC_MUSEUM=true` map wizard API paths to canned JSON (`api/staticMuseum.ts` and `lenses/static/studio/museum-data/`). Session writes and LLM calls are intentionally blocked or stubbed; see usage guide.
