# Blueprints Wizard — file map

Quick reference for routes, modules, tests, and environment variables. Paths are relative to the **forge-lenses** repo root unless noted.

**Docs:** [wizard-usage.md](wizard-usage.md) (operators), [wizard-architecture.md](wizard-architecture.md) (system view), [wizard-extending.md](wizard-extending.md) (developers).

## Environment variables

| Variable | Where | Purpose |
|----------|--------|---------|
| `LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD` | Python process | Default **on**; set to `0` / `false` / `no` / `off` to disable wizard HTTP APIs. |
| `LENSES_CURSOR_LAUNCH_STAGING_TTL_SEC` | Python process | Optional; minimum **60** when set. Staged zip files under `.lenses-local/blueprints-wizard/cursor-launch-staging/` older than this (mtime) are deleted on new staging writes, before each download GET, and by the background cleanup thread. Default **3600** (1 hour). |
| `LENSES_CURSOR_LAUNCH_STAGING_CLEANUP_INTERVAL_MIN` | Python process | Minutes between background TTL sweeps for staged zips (`serve.py` daemon thread). Default **15**; set to **0** / `off` to disable background sweeps only. |
| `VITE_EXPERIMENTAL_BLUEPRINTS_WIZARD` | Vite build / `lenses-enterprise` | Default **on** (see `.env.production`); set to `false` to omit client routes and sidebar link. |
| `LENSES_BLUEPRINTS_WIZARD_TELEMETRY` | Python process | Default **off**; set to `1` / `true` / `yes` / `on` to append JSONL telemetry (requires experimental wizard on). |
| `VITE_BLUEPRINTS_WIZARD_TELEMETRY` | Vite build | Default **off**; set to `true` / `1` / `yes` / `on` to allow client `step_view` POSTs (server telemetry must also persist). |
| `GITHUB_TOKEN` or `LENSES_GITHUB_TOKEN` | Python process | Optional: **Create GitHub repository** (`POST …/create-repo`). Not stored in session files. |

## HTTP API (wizard)

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/api/blueprints/wizard/enabled` | `{ ok, enabled }` — always (no slice gate). |
| `POST` | `/api/blueprints/wizard/telemetry` | Body: `event` (required), optional `session_id`, `step_index`, `mission_mode` — metadata only; requires server flag + telemetry env. |
| `GET` | `/api/blueprints/wizard/sessions` | `{ ok, sessions: [...] }` — summary list for hub UI; requires server flag. |
| `POST` | `/api/blueprints/wizard/session` | `{ ok, session_id }` — requires server flag. |
| `GET` | `/api/blueprints/wizard/session/<id>` | `{ ok, session }` — requires server flag. |
| `PUT` | `/api/blueprints/wizard/session/<id>` | Body: full session document — requires server flag; validates `scope` paths and `parent_session_id`. |
| `POST` | `/api/blueprints/wizard/session/<id>/refine` | Body: `provider`, optional `model`, optional `refine` (chain). Writes `payload.foundation_brief` — requires server flag + same access as `/api/llm/chat`. |
| `POST` | `/api/blueprints/wizard/session/<id>/create-repo` | Body: `{ confirm: true }`. Creates GitHub repo from `payload.new_product_draft`; requires server flag + loopback / `LENSES_ALLOW_ACTIONS` + token env. |
| `POST` | `/api/blueprints/wizard/session/<id>/generate-artifacts` | Body: `provider`, optional `model`/`refine`; optional `artifact` (single key), `artifact_keys` (list), or `artifact_bundle` (`planning` \| `engineering` \| `all` \| `full` = planning+engineering, `execution`, `complete` \| `full_stack` = all slices). Writes `wizard_domain.artifact_generation`; requires server flag + same access as LLM chat. |
| `POST` | `/api/blueprints/wizard/session/<id>/artifact-review` | Body: `action`, `artifact_key`, optional `feedback`; or `action: approve_bundle` with `artifact_keys` (list). |
| `POST` | `/api/blueprints/wizard/session/<id>/artifact-export` | Body: `artifact_keys` — returns `{ ok, markdown }`; requires server flag + same access as LLM chat. |
| `POST` | `/api/blueprints/wizard/session/<id>/cursor-launch-pack/preview` | Body: `artifact_keys`, optional `closure_options`, optional `strict_approval` — returns `{ ok, manifest, files[], warnings? }`; requires server flag only (read-only). |
| `POST` | `/api/blueprints/wizard/session/<id>/cursor-launch-pack/export` | Body: `artifact_keys`, optional `closure_options`, optional `strict_approval`, `destination`: `workspace` \| `download`, optional `relative_path`; for `download`, optional `stream`/`prefer_stream` to force staged file + GET instead of base64. Writes under `.lenses-local/blueprints-wizard/cursor-launch-packs/…` or returns inline zip as `content_base64`, or `{ download_mode: "stream", download_path, download_token, byte_length, filename }` for large packs or when `stream` is true; requires server flag + loopback / `LENSES_ALLOW_ACTIONS`. |
| `GET` | `/api/blueprints/wizard/session/<id>/cursor-launch-pack/download/<token>` | Streams staged zip (chunked read); single-use — file removed after send. Same auth gate as export POST. |
| `POST` | `/api/blueprints/wizard/session/<id>/artifact-recheck` | Body: optional `dry_run` (`true` / `1` / `"true"`). Default **persists** `recheck_summary` + pack sync. With `dry_run`, returns `{ ok, recheck_summary, dry_run: true }` and **does not** save. Requires server flag + LLM gate. |

Session JSON files: `.lenses-local/blueprints-wizard/sessions/<id>.json`. Typed domain data: `payload.wizard_domain` (see `docs/blueprints/wizard-domain-model.md`).

## Studio routes

| URL path (under `/studio`) | Page | Notes |
|----------------------------|------|--------|
| `/blueprints/wizard` | `BlueprintsWizardLayout` → hub (`BlueprintsWizardHub`) | Lazy-loaded; **omitted in the client build only if** `blueprintsWizardFeatureEnabled()` is false (explicit `VITE_EXPERIMENTAL_BLUEPRINTS_WIZARD=false`). |
| `/blueprints/wizard/session/:sessionId` | `BlueprintsWizardSessionPage` | Wizard steps + session setup + refine. Legacy **`?session=`** on the hub redirects here. |

## Navigation and meta

| File | Change |
|------|--------|
| `lenses-enterprise/src/App.tsx` | Nested routes under `blueprints/wizard`. |
| `lenses-enterprise/src/nav/navigationConfig.ts` | Knowledge sidebar: optional “Blueprints Wizard (experimental)” via `blueprintsWizardFeatureEnabled()`. |
| `lenses-enterprise/src/nav/routeMeta.ts` | Breadcrumbs for hub and session routes (Knowledge group). |

## Client modules

| Path | Role |
|------|------|
| `lenses-enterprise/src/util/experimentalFlags.ts` | `blueprintsWizardFeatureEnabled()`, `blueprintsWizardTelemetryClientEnabled()` — Vite env. |
| `lenses-enterprise/src/api/http.ts` | `apiGetJson`, `apiPostJson`, `apiPutJson`; static museum stubs for wizard. |
| `lenses-enterprise/src/api/blueprintsWizard.ts` | Wizard API wrappers including `listWizardSessions`, `postWizardCreateRepo`. |
| `lenses-enterprise/src/blueprints-wizard/wizardStepModel.ts` | Step count, titles, `clampStepIndex`, `applyStepNext` / `applyStepBack`, `stepNotes` in `payload`. |
| `lenses-enterprise/src/blueprints-wizard/WizardSetupPanel.tsx` | Scope, mode, new-product draft, create-repo entry. |
| `lenses-enterprise/src/blueprints-wizard/BlueprintsWizardHub.tsx` | Session list + new session. |
| `lenses-enterprise/src/pages/BlueprintsWizardLayout.tsx` | Server vs local (`BlueprintsWizardLocalMode`) gate + `Outlet`. |
| `lenses-enterprise/src/pages/BlueprintsWizardSessionPage.tsx` | Server-backed wizard shell + setup + refine. |
| `lenses-enterprise/src/pages/BlueprintsWizardLocalMode.tsx` | SessionStorage draft when the wizard API is off. |
| `lenses-enterprise/src/api/staticMuseum.ts` | Museum mapping for wizard API paths. |
| `lenses-enterprise/src/blueprints-wizard/wizardDomainTypes.ts` | String-literal unions + JSON shapes for `wizard_domain`. |
| `lenses-enterprise/src/blueprints-wizard/wizardDomainNormalize.ts` | `emptyWizardDomain`, `normalizeWizardDomain` (mirror Python). |
| `lenses-enterprise/src/blueprints-wizard/wizardSessionMapping.ts` | Server document ↔ shell state; preserves `payload` keys including `wizard_domain`. |
| `lenses-enterprise/src/blueprints-wizard/wizardPersistence.ts` | Local draft (`shell.v2`); optional `wizardDomain` on `WizardPersistedState`. |
| `lenses-enterprise/src/blueprints-wizard/ExperimentalBuildStepPanel.tsx` | Step 11 — preview / export Cursor Launch Pack. |
| `lenses-enterprise/src/blueprints-wizard/wizardAsyncUi.tsx` | Shared `WizardAlert` / `WizardRetryRow` for async errors. |

## Server modules

| Path | Role |
|------|------|
| `lenses/blueprints_wizard/feature_flag.py` | `experimental_blueprints_wizard_enabled()` from env. |
| `lenses/blueprints_wizard/wizard_telemetry.py` | Optional JSONL telemetry; `record_http_api_result` from `serve.py` for some POST handlers. |
| `lenses/blueprints_wizard/schemas.py` | `WizardSessionDocument`, `normalize_wizard_payload`, version **2** payload defaults; merges `wizard_domain`. |
| `lenses/blueprints_wizard/domain_enums.py` | Frozenset-backed enums + coerce helpers. |
| `lenses/blueprints_wizard/domain_models.py` | Dataclass views (`FoundationBrief`, `RunPlan`, …) aligned with JSON. |
| `lenses/blueprints_wizard/wizard_domain_normalize.py` | `empty_wizard_domain`, `normalize_wizard_domain`, nested normalizers. |
| `lenses/blueprints_wizard/wizard_session_state.py` | Pure selectors + immutable document actions. |
| `lenses/blueprints_wizard/recheck_provider.py` | `RecheckProvider` protocol + `NullRecheckProvider`. |
| `lenses/blueprints_wizard/session_store.py` | Create/load/save/list under `.lenses-local/`. |
| `lenses/blueprints_wizard/scope_paths.py` | `safe_wbs_file` / `safe_roadmap_file` for scope validation. |
| `lenses/blueprints_wizard/payload_validate.py` | `validate_wizard_payload_paths` (scope + parent session). |
| `lenses/blueprints_wizard/github_create.py` | GitHub REST create repo + session update. |
| `lenses/blueprints_wizard/api.py` | HTTP helpers: list, get/put session, refine, create-repo path parser. |
| `lenses/blueprints_wizard/refine.py` | Build prompt from `stepNotes` / `foundation_brief_raw`, call `llm_chat.chat`, persist `foundation_brief`. |
| `lenses/blueprints_wizard/artifact_generation_dependencies.py` | Upstream approval rules, bundle key resolution (`planning` / `engineering` / `all`), lineage helpers. |
| `lenses/blueprints_wizard/artifact_generation_recheck.py` | Recheck summary: quality floors + provenance lineage drift vs current upstream ids. |
| `lenses/blueprints_wizard/launch_pack_scope.py` | Closure options → expanded artifact keys for Cursor Launch Pack. |
| `lenses/blueprints_wizard/cursor_launch_pack.py` | Compile markdown tree + `manifest.json`; `preview_pack`, `build_launch_pack_zip_bytes`, `StrictApprovalError`. |
| `lenses/blueprints_wizard/launch_pack_staging.py` | Staged zip files for large / streaming download (`GET …/download/<token>`). |
| `lenses/blueprints_wizard/prompt_materializer.py` | `PromptMaterializer` protocol + `NullPromptMaterializer` for dynamic recipe placeholders. |
| `lenses/serve.py` | Wizard `GET`/`POST`/`PUT` routes including `GET …/sessions` and `POST …/create-repo`. |

## Static assets (museum)

| Path | Role |
|------|------|
| `lenses-enterprise/public/museum-data/blueprints-wizard-enabled.json` | `GET` enabled fixture. |
| `lenses-enterprise/public/museum-data/blueprints-wizard-sessions.json` | `GET` sessions list fixture. |
| `lenses-enterprise/public/museum-data/blueprints-wizard-session.json` | `GET` session-by-id fixture. |

## Design / Kitchen Sink

| Path | Role |
|------|------|
| `forgesdlc-kitchensink/css/wizard-flow.css` | Shared session list + setup panel primitives (`ks-wizard-flow__*`). |
| `forgesdlc-kitchensink/docs/design/wizard-flow-studio.md` | Short consumption note for Studio. |

## Domain model (reference)

| Path | Role |
|------|------|
| `docs/blueprints/wizard-domain-model.md` | Enums, composite shapes, persistence notes. |

## Tests

| Path | Role |
|------|------|
| `tests/test_blueprints_wizard_feature_flag.py` | Python: flag parsing. |
| `tests/test_blueprints_wizard_domain_normalize.py` | Python: `wizard_domain` normalization + payload merge. |
| `tests/test_blueprints_wizard_session_state.py` | Python: pure session state transitions. |
| `tests/test_blueprints_wizard_session_store.py` | Python: session round-trip + validation. |
| `tests/test_blueprints_wizard_api_extended.py` | Python: list, scope validation, GitHub helper, create-repo confirm. |
| `tests/test_blueprints_wizard_refine.py` | Python: refine path parsing, persist brief, mocked `llm_chat.chat`. |
| `lenses-enterprise/src/util/experimentalFlags.test.ts` | Client: flag helper. |
| `lenses-enterprise/src/api/staticMuseum.test.ts` | Museum path mapping. |
| `lenses-enterprise/src/blueprints-wizard/wizardStepModel.test.ts` | Vitest: step navigation + notes helpers. |
| `lenses-enterprise/src/pages/BlueprintsWizardPage.test.tsx` | Vitest: local wizard shell. |
| `lenses-enterprise/src/pages/BlueprintsWizardPage.server.test.tsx` | Vitest: session route + `putWizardSession` + resume by `step_index`. |
| `lenses-enterprise/src/pages/BlueprintsWizardFlows.server.test.tsx` | Vitest: mocked flows (idea, assess, recheck, launch-pack API). |
| `tests/test_wizard_telemetry.py` | Python: telemetry gate + JSONL ingest. |
| `tests/test_wizard_telemetry_http.py` | Python: `POST /api/blueprints/wizard/telemetry` via `LensesHandler`. |
| `lenses-enterprise/src/blueprints-wizard/wizardDomainNormalize.test.ts` | Vitest: domain normalization. |
| `tests/test_cursor_launch_pack.py` | Python: Cursor Launch Pack manifest, scope closure, export. |
| `tests/test_cursor_launch_pack_http.py` | Python: TTL cleanup for staging zips; HTTP POST→GET stream download integration. |

## Tooling

| Requirement | Notes |
|-------------|-------|
| Node.js | `lenses-enterprise/package.json` **`engines.node`: `>=20.12.0`** — Vitest 4 / Rolldown need `util.styleText` (older Node fails at startup). |

## Cursor / agent instructions

| Path | Role |
|------|------|
| `.cursor/rules/blueprints-wizard-experimental.mdc` | Repo-local rules for this feature. |
