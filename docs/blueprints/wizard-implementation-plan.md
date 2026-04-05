# Blueprints Wizard — implementation plan (Lenses Studio)

This document expands the high-level blueprint for the **experimental** Blueprints Wizard inside **Lenses Studio** (`/studio/`). Implementation must follow [blueprints-wizard-experimental.mdc](../../.cursor/rules/blueprints-wizard-experimental.mdc) and align with existing forge-lenses patterns (React Router, `serve.py` JSON APIs, `llm_chat`, `.lenses-local` persistence, Vitest + pytest).

## Goals (v1)

- Guided flow from rough intent → **Foundation Brief**, **clarifications**, **target / autonomy / scope**, **run-plan preview**, **artifacts**, **recheck/repair**, and an experimental **build pack export**.
- **Session continuity**: save and resume wizard state per workspace (server-backed JSON under `.lenses-local/blueprints-wizard/sessions/` via slice 2 APIs).
- **No new frameworks**: reuse existing LLM stack (`lenses.llm_chat`), HTTP handler style, and Studio UI conventions (`le-*` classes, Context where appropriate).

## Non-goals (v1)

- Editing the **blueprints** git submodule from the wizard.
- Full parity with **Classic** HTML UI until the feature exits experimental (see ADR / parity rule exception).

## Expansion (session hub, scope, optional GitHub)

- **Session hub** at `/studio/blueprints/wizard` lists saved sessions; **session editor** at `/studio/blueprints/wizard/session/:id`.
- **Payload v2** adds `title`, `purpose`, `state`, `mode`, `scope` (WBS / roadmap paths), `new_product_draft`, `created_repo_url`, optional `parent_session_id`.
- **GitHub create** is explicit `POST …/create-repo` with env token; see [adr-002-blueprints-wizard-trust-github.md](../adr-002-blueprints-wizard-trust-github.md).

## User stories (v1)

1. **As a** workspace lead **I want** to turn on an experimental Blueprints Wizard **so that** I can draft methodology-aligned packs without leaving Lenses.
2. **As a** user **I want** the server to expose whether the feature is enabled **so that** the UI matches deployment policy (`LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD`).
3. **As a** user **I want** to paste rough notes and get a structured Foundation Brief **so that** I can iterate with LLM assistance (slice 4 refine → `payload.foundation_brief`; further loops later).
4. **As a** user **I want** clarification questions **so that** gaps are surfaced before committing to a run plan (later slices).
5. **As a** user **I want** to pick target outcome, autonomy, and scope **so that** generated artifacts match how the team works (later slices).
6. **As a** user **I want** a run-plan preview and generated markdown artifacts **so that** I can review before export (later slices).
7. **As a** user **I want** a recheck/repair pass **so that** I can fix inconsistencies (later slices).
8. **As a** user **I want** a one-click build pack export **so that** I can take files into another repo or tool (experimental; may start as JSON download only).

## Current architecture (reference)

| Area | Pattern | Location |
|------|---------|----------|
| Router | React Router v6, `basename="/studio"` | `lenses-enterprise/src/App.tsx` |
| Navigation | `navigationConfig.ts`, `routeMeta.ts` | `lenses-enterprise/src/nav/` |
| UI | `le-*`, `Layout`, side nav | `lenses-enterprise/src/components/` |
| State | Page `useState` + React Context | `lenses-enterprise/src/context/` |
| API | `apiGetJson` / `apiPostJson` | `lenses-enterprise/src/api/http.ts` |
| Server | `LensesHandler` in `serve.py` | `lenses/serve.py` |
| LLM | `POST /api/llm/chat` → `llm_chat.chat` | `lenses/llm_chat.py` |
| Persistence | `.lenses-local/*.json` | e.g. `llm_settings_store.py` |

## Feature flags

| Layer | Variable | When true |
|-------|----------|-----------|
| Server | `LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD` | `1` (or documented truthy) — enables wizard APIs and behavior. |
| Client (Vite) | `VITE_EXPERIMENTAL_BLUEPRINTS_WIZARD` | `true` — registers `/blueprints/wizard`, shows Knowledge sidebar link, loads wizard chunk. |

Both should be set during development of the wizard. Production/studio museum builds typically leave them unset.

## API contract sketch (incremental)

Slice 1:

- `GET /api/blueprints/wizard/enabled` → `{ "ok": true, "enabled": boolean }`

Slice 2:

- `POST /api/blueprints/wizard/session` → `{ "ok": true, "session_id": string }`
- `GET /api/blueprints/wizard/session/<id>` → `{ "ok": true, "session": { version, updated_at, step_index, payload } }`
- `PUT /api/blueprints/wizard/session/<id>` — body: session document JSON → `{ "ok": true }`

Slice 4:

- `POST /api/blueprints/wizard/session/<id>/refine` — body: `{ "provider", "model"?, "refine"? }` → merges LLM output into `session.payload.foundation_brief` (same trust boundary as `POST /api/llm/chat`: loopback / `LENSES_ALLOW_ACTIONS`). JSON: `{ "ok": true, "text", "session", … }` on success; LLM failures often return HTTP 200 with `{ "ok": false, "error", … }` (mirrors chat).

Later slices (illustrative — finalize in PRs):

- Clarification loop, target/autonomy, artifacts — separate endpoints or payload fields.

All mutating/LLM routes must check `LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD` and reject with `feature_disabled` or `404` when off.

Slice 3 (Studio UI):

- `/studio/blueprints/wizard` — multi-step shell (Intent / Scope / Plan / Review), `step_index` and per-step notes in `session.payload.stepNotes`.
- Resume: query param **`?session=<session_id>`** after first load (or open a bookmarked URL).

## Implementation slices (checklist)

- [x] **Slice 1:** Feature flags, `GET /api/blueprints/wizard/enabled`, Studio route `/blueprints/wizard` (client flag), `routeMeta`, Knowledge sidebar link, Vitest + pytest.
- [x] **Slice 2:** Session store on disk + `GET`/`POST`/`PUT` session API + pytest.
- [x] **Slice 3:** Wizard shell (steps, no LLM) + persistence round-trip + Vitest.
- [x] **Slice 4:** LLM-backed **Foundation Brief** refine (`POST …/session/<id>/refine` → `llm_chat.chat`), `payload.foundation_brief`, Studio controls + pytest (mocked `llm_chat`). *Clarification loop remains a later slice.*
- [ ] **Slice 5:** Target / autonomy / scope + run-plan preview UI.
- [ ] **Slice 6:** Artifact generation + recheck/repair.
- [ ] **Slice 7:** Build pack export + static museum wiring + README env notes.

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| LLM returns invalid JSON | Retry/repair prompt; mock adapters in tests; strict server-side parsing with clear errors. |
| Remote access to LLM-backed routes | Mirror `client_may_run_shell_actions` / `LENSES_ALLOW_ACTIONS` patterns used by `/api/llm/chat`. |
| Static museum build | Map `/api/blueprints/wizard/enabled` in `staticMuseum.ts` + JSON fixture under `museum-data/`. |

## Related docs

- [wizard-file-map.md](./wizard-file-map.md) — file and route inventory.
- [../studio-shell-api-map.md](../studio-shell-api-map.md) — Studio API overview.
- [../adr-001-lenses-studio-shell.md](../adr-001-lenses-studio-shell.md) — Studio shell ADR.
