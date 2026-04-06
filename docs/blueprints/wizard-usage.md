# Blueprints Wizard — internal usage

**Browser vs app routes:** Forge Studio is served at **`/studio/`** on your Lenses server. The Wizard’s client routes are **`/blueprints/wizard/...`** (hub and session) **inside** that app, so the paths you open in the browser are **`/studio/blueprints/wizard`** and **`/studio/blueprints/wizard/session/<sessionId>`** — the same as the [public Wizard overview](../handbook-public/08-wizard-overview.md). Shorter paths below (`/blueprints/wizard`, `session/:sessionId`) name the same screens in the React router.

The Blueprints Wizard is **experimental**. Enable it on both the Python server and the Studio client before relying on session APIs or the `/blueprints/wizard` routes.

## Feature flags

| Layer | Variable | Default | Effect |
|-------|----------|---------|--------|
| Server | `LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD` | on | When set to `0`, `false`, `no`, or `off`, wizard JSON APIs (except `GET /api/blueprints/wizard/enabled`) return disabled / 404. |
| Client | `VITE_EXPERIMENTAL_BLUEPRINTS_WIZARD` | on | When `false` / `0`, the wizard routes and sidebar entry are omitted from the Studio build. |
| Telemetry (server file) | `LENSES_BLUEPRINTS_WIZARD_TELEMETRY` | off | When `1` / `true` / `yes` / `on`, records metadata-only events under `.lenses-local/blueprints-wizard/telemetry.jsonl` (requires experimental wizard on). |
| Telemetry (client POST) | `VITE_BLUEPRINTS_WIZARD_TELEMETRY` | off | When `true` / `1` / `yes` / `on`, the session page may send debounced `step_view` events to `POST /api/blueprints/wizard/telemetry` (server telemetry must also be enabled to persist). |

### Telemetry review

The server appends one JSON object per line to `<workspace_root>/.lenses-local/blueprints-wizard/telemetry.jsonl`. The file is **capped** (when it grows past a size limit, new lines are skipped until you make room). For **long-running internal deployments**:

1. **Rotate / archive:** Stop the Lenses process (or pause writes), copy or move the file to a dated name (for example `telemetry.jsonl.bak-20260405`), then restart. Inspect or archive the copy under your org’s retention rules.
2. **Delete to reset:** Remove `telemetry.jsonl` (or the whole `blueprints-wizard` directory under `.lenses-local/` if you intend to clear wizard-local state). A new file is created on the next event. Ensure backups are not required before deleting.
3. **Permissions:** The directory is created with restrictive permissions; keep `.lenses-local/` on encrypted disk if the workspace path is sensitive.

Content is metadata only (event names, session ids, step indices, API result codes)—not prompts or file paths. Treat the file like other operational logs.

## Hub vs session

- **Hub** (`/blueprints/wizard`): lists saved sessions (newest first), creates a new session id, and links to `session/:sessionId`.
- **Session** (`/blueprints/wizard/session/:sessionId`): full 12-step shell, session setup (scope, product mode, optional GitHub create), LLM refine/interpret panels, and artifact flows.

If the server probe for `GET /api/blueprints/wizard/enabled` fails (network error), Studio falls back to **local-only** draft mode (`sessionStorage`). Use **Retry server connection** to probe again.

## Where data lives

- **Server-enabled mode:** Session documents are JSON files under `<workspace>/.lenses-local/blueprints-wizard/sessions/<id>.json`. Saving uses `PUT` with the full document; navigation and many edits trigger autosave (including silent paths that surface a **Retry save** banner on failure).
- **Local fallback:** A compact shell snapshot lives in `sessionStorage` (see `wizardPersistence.ts`). It does not include full server-only artifact state.

## LLM and trust

Refine, interpret, clarify-suggest, artifact generation, and recheck follow the same **loopback / `LENSES_ALLOW_ACTIONS`** rules as `/api/llm/chat`. GitHub repository creation uses env tokens only (`GITHUB_TOKEN` or `LENSES_GITHUB_TOKEN`); tokens are not stored in session JSON.

## Recheck and experimental build

- **Recheck / Repair (step 10):** **Refresh recheck** persists a new `recheck_summary` on the session. **Preview recheck (no save)** updates the dashboard only. If the persist call fails, an error appears and you can retry.
- **Experimental Build (step 11):** Preview and export Cursor Launch Packs. Respect **strict approval** when your policy requires approved/locked slices. Large downloads may use a staged zip and `GET` download. Workspace export writes under the workspace root (or a validated relative path). Warnings from the compiler are shown inline (preview, last export).

## Operational tips

- Use **Retry** on hub load errors, session boot errors, and failed saves.
- If saves fail in a **static museum** build, run Studio against the live Lenses server; museum builds cannot persist session `PUT`s.
- Concurrent edits to the same session id are last-write-wins; avoid two tabs on one session for critical work.
