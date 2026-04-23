# Docs Health MVP (maintainer)

Docs Health is a **markdown-first** documentation scanner and remediation loop integrated into **Projects**, **Work** (follow-up items), **Home** (rollup), and **AI Setup** (routing via new `studio_task_id` values).

## Sprint DOCS-1 — contract, inventory, entry point

- **Contract (canonical):** `forge/docs-contract.yaml` in the repository root (folder `forge/`). If missing, **convention defaults** apply (same shape, `_meta.source` = `convention`). Legacy `lenses-docs-contract.yaml` is still read when present and `forge/docs-contract.yaml` does not exist.
- **Normalized contract** includes `required_doc_types`, `ownership`, `scope`, and legacy keys used by the quality scanner (`require_adr`, `readme_required_sections`, …). See `lenses/docs_health/contract.py` (`resolve_project_docs_contract`).
- **Inventory:** `POST` with `op: "inventory"` walks scoped `.md` files, extracts title, headings, front matter, internal links, `doc_type`, and `knowledge_category` (`docs` | `evidence` | `decisions` | `diagrams`) for later Knowledge links. Snapshots persist under `.lenses-local/docs-health/<project>/inventories/` with `latest_inventory.json` pointer.
- **Domain types:** `lenses/docs_health/models.py` documents `ProjectDocsContract`, `DocsDocumentRecord`, `DocsInventorySnapshot`, and `DocsScanRun` stub shape.
- **Demo fixture:** `tests/fixtures/docs_health_sample_repo/` — partial docs, checklist file, nested markdown and links (used by `tests/test_docs_health_contract.py`).

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/docs-health/summary` | Workspace rollup: scores, contract file flags, last inventory timestamps |
| GET | `/api/docs-health/work-items` | Open KTLO-style items across projects |
| GET | `/api/project/<name>/docs-health` | Contract, contract_status, inventory_summary, docs_scan_run, latest quality run, … |
| GET | `/api/project/<name>/docs-health?full_inventory=1` | Same + embedded `latest_inventory` (documents truncated server-side) |
| POST | `/api/project/<name>/docs-health` | JSON body `{ "op": ... }` — see `lenses/docs_health/api_handlers.py` |

### POST operations

- `inventory` — rebuild markdown index + link graph for the project
- `scan` — deterministic quality scan, persists run under `.lenses-local/docs-health/<project>/runs/`
- `create_session` — `{ cluster_id, run_id }` starts a remediation session (persists `display_name` and full hex `id`). Also creates a **TaskletRun** under `.lenses-local/tasklet-runs/` and returns `tasklet_run_id`, `tasklet`, and `execution.step_backend` (from `LENSES_DOCS_HEALTH_STEP_BACKEND`).
- `session_get` — `{ session_id }`
- `session_cancel` — `{ session_id }` sets status `cancelled`, writes a cancel flag, **SIGKILL**s an in-flight **process** or **Docker** worker when `LENSES_DOCS_HEALTH_STEP_BACKEND` is `process` or `docker`, and marks the linked TaskletRun cancelled. Idempotent when already cancelled. Inline (`inline`) steps still run in the server process until the HTTP handler returns (same as before).
- `session_reply` — `{ session_id, … }` for `awaiting_input` / `awaiting_approval` prompts
- `session_step` — `{ session_id, step }` where `step` is `enrich` | `cluster_brief` | `diagram_draft` | `decision_stub` | `draft` | `review` | `apply` | `verify` (execution may be **inline**, **process**, or **docker** — see Tasklet + sandbox section below).
- `work_complete` — `{ work_item_id }` marks a tracked item done

## Model routing

Three Studio tasks are registered for routing previews and privacy: `docs_health_enricher`, `docs_health_writer`, `docs_health_reviewer`. Smart routing prefers **Ollama** then **openai_compatible**. Optional JSON in LLM settings: `docs_health_slots` maps logical slots (`local_writer`, …) to a provider id — see `lenses/docs_health/agents.py`.

## Feature flag

Set `LENSES_DOCS_HEALTH=0` to disable all Docs Health HTTP surfaces.

## Troubleshooting: Studio shows “Failed to fetch” on scan

That message is raised by the **browser** when the `POST /api/project/<name>/docs-health` call does not complete (connection refused, proxy reset, wrong host, CORS/preflight in dev, etc.). It is **not** the markdown scanner returning an error payload — if the server handled the request you would get JSON with `ok: false` and an `error` code instead.

1. **Confirm the API is reachable** (instant, no scan work): `POST` body `{ "op": "ping" }` — response `{"ok":true,"op":"ping",...}`.
2. **Same origin for `/api`**: either open Studio from the Lenses server (one host serves `/studio/` + `/api`), run Vite dev with `/api` proxied to that process, or set `VITE_LENSES_API_BASE` to the Lenses URL when the SPA is hosted separately. Studio UI and curl hints use that resolved API origin (not a fixed port).
3. **`npm run dev`**: Vite proxies `/api` to the target in `lenses-enterprise/vite.config.ts` (often `127.0.0.1:8080` by default — change if your Python app listens elsewhere). The Python app must be running. Long `op: "scan"` runs can exceed short proxy timeouts — the repo sets a long `/api` timeout; restart dev after changes.
4. **Non-loopback clients**: set `LENSES_ALLOW_ACTIONS=1` (see product README) when required by your deployment.

**Dynamic port / new URL each run:** `python3 -m lenses` (or wrappers) may bind `127.0.0.1:<port>` where `<port>` changes per invocation. Studio and the diagnostics bundle always use **this tab’s** `location.origin` or `VITE_LENSES_API_BASE` — never assume `:8080` in bug reports.

### Playwright E2E (Docs health)

From `forge-lenses/lenses-enterprise/` after `npm install` and `npx playwright install chromium`:

```bash
npm run test:e2e:docs-health
```

The script [`lenses-enterprise/scripts/e2e-lenses-with-fixture.sh`](../../lenses-enterprise/scripts/e2e-lenses-with-fixture.sh) (wired in [`lenses-enterprise/playwright.config.ts`](../../lenses-enterprise/playwright.config.ts)) starts a **throwaway workspace** (copies `tests/fixtures/docs_health_sample_repo/` into `e2e_doc_proj` + `git init`), runs `python3 -m lenses` on **127.0.0.1:17555** (override with `E2E_LENSES_PORT`), and builds Studio unless `E2E_BUILD_STUDIO=0`.

**Scan regression** — [`lenses-enterprise/e2e/docs-health-scan.spec.ts`](../../lenses-enterprise/e2e/docs-health-scan.spec.ts): opens `/studio/projects/e2e_doc_proj/docs-health`, waits for **Run markdown scan**, asserts the real **scan** `POST` to `/api/project/e2e_doc_proj/docs-health` returns `ok: true`, and the UI shows **Scan finished**. Covers the store regression where the first scan must create `.lenses-local/.../runs/` (missing `runs/` previously caused an empty HTTP response / “Failed to fetch”).

**Session UI (mocked `session_get`)** — [`lenses-enterprise/e2e/docs-health-session.spec.ts`](../../lenses-enterprise/e2e/docs-health-session.spec.ts): registers `page.route` on `POST` `**/api/project/e2e_doc_proj/docs-health` and **fulfills** JSON only when the body is `{ op: "session_get", session_id: "<fixed id>" }`; all other requests **continue** to the real server so the scan spec and normal API traffic are unchanged. Navigates to `/studio/projects/e2e_doc_proj/docs-health/session/<id>` and asserts:

| Mock scenario | UI checks |
|---------------|-----------|
| `status: "cancelled"` (no apply in metrics) | **Run cancelled** copy and **Resume run** |
| `status: "awaiting_approval"` with `proposed_patch` + `suggested_git_branch` | **Review before apply**; **Approve and apply to branch** scoped to the **`Primary run actions`** toolbar (role `toolbar`, `aria-label` matches) so it does not collide with **ForgeWorkflowStageBar** stage nodes that reuse similar labels |
| `status: "running"` with `step_metrics` containing `apply` but not `verify` | **Apply completed — verify next** and **Re-scan and verify** in the primary toolbar |
| `status: "completed"` with `completion_summary.verification_pipeline_ok: true` | **View results** link in the primary toolbar |

### Manual disposable workspace (same pattern as E2E)

For safe Docs Health experiments without touching your main clones, mirror what Playwright does:

1. `WS=$(mktemp -d)` and `mkdir -p "$WS/e2e_doc_proj"`.
2. Copy the sample repo into the child folder: `cp -a <forge-lenses>/tests/fixtures/docs_health_sample_repo/. "$WS/e2e_doc_proj/"` (replace `<forge-lenses>` with your checkout path).
3. `cd "$WS/e2e_doc_proj"`, `git init`, `git add -A`, `git commit -m init` (set `user.name` / `user.email` if needed).
4. From the **forge-lenses** repo root: `python3 -m lenses --host 127.0.0.1 --port 8080 --workspace-root "$WS"` (pick a free port; align Vite `vite.config` proxy or `VITE_LENSES_API_BASE` if Studio is separate).
5. In Studio, open project **`e2e_doc_proj`** → Docs health. When finished, stop Lenses and `rm -rf "$WS"`.

All `.lenses-local` data stays under `$WS`; nothing is written to the forge-lenses source tree unless you point `--workspace-root` there.

### Bug report bundle (from Studio)

On **Projects → … → Docs health → Score formula and API**, expand **Diagnostics bundle (if scan fails again)** and click **Copy report to clipboard**. Paste that Markdown into the issue or chat, plus a short note from **DevTools → Network** for the `docs-health` POST (HTTP status or `(failed)` / stuck pending). The report includes `json_api_origin`, `page_origin`, build flags, `userAgent`, an optional **last scan UI message**, and a ready-made `curl` `{ "op": "ping" }` line with the project slug encoded.

## Studio routes

- `/projects/:name/docs-health`
- `/projects/:name/docs-health/session/:sessionId` (probe: `docs_health_session`)

## Sprint DOCS-3 — agent runtime (dispatch, ledger, sessions)

- **Package:** `lenses/agent_runtime/` — `types`, `capabilities`, `dispatch` (local-first chain), `invoke` (calls `lenses.llm_chat.chat` + ledger), `ledger` (`.lenses-local/agent-runtime/token-ledger.jsonl`), `sessions` (`.lenses-local/agent-runtime/sessions/*.json`), `http` (GET/POST + SSE stream stub).
- **HTTP (loopback / `LENSES_ALLOW_GIT_ACTIONS` same as LLM):** `/api/agent-runtime/overview`, `/providers`, `/slots`, `/policy`, `/token-usage`, `/sessions`, `/sessions/<id>`, `/sessions/<id>/events`, `/sessions/<id>/stream` (SSE polling).
- **Docs Health:** remediation sessions get `agent_runtime_session_id`; each enrich/draft/review step records ledger rows and agent session events.
- **Studio:** **Settings → Agent runtime** (`/settings/agent-runtime`) under Admin & inspect for provider health, slots, policy summary, and ledger tail.

## Tasklet + sandbox (remediation execution)

- **Tasklet** — `lenses/tasklet/`: versioned workload definitions (`registry.py`), persistent **TaskletRun** JSON under `.lenses-local/tasklet-runs/<id>.json` (`store.py`). Docs Health remediation uses `docs_health_remediation` v1; each `create_session` creates a TaskletRun linked by `tasklet_run_id` on the session payload.
- **Run state machine** — `lenses/tasklet/state_machine.py`: explicit lifecycle states (`created`, `preparing`, `running`, `awaiting_input`, `awaiting_approval`, `paused`, `stopping`, `stopped`, `verifying`, `completed`, `failed`) with validated transitions. The persisted run record uses **`state`** (legacy **`status`** on the same file is mirrored for older readers). API responses include **`run_state`** (and **`tasklet_run`** summary) while **`status`** stays Studio-compatible via `run_state_to_docs_session_status`.
- **Durable events** — `lenses/tasklet/run_events.py`: append-only **`events.jsonl`** per run under `.lenses-local/tasklet-runs/<id>/events.jsonl`. `GET session` / merged views reconstruct the timeline from JSONL when present (seeded on `create_session`, extended on each step / reply).
- **Checkpoints** — after each successful `session_step` (and related sync), a checkpoint row is appended to the TaskletRun (coarse, resumable markers).
- **Draft vs apply** — proposed patches are persisted as `sessions/<sessionId>/artifacts/proposed_patch.json` (in addition to the session JSON). Optional **scratch git worktree** under `.lenses-local/docs-health/<project>/scratch/<sessionId>/wt` materializes the draft for preview without modifying the main checkout until **Apply** (which still writes the live repo only when policy allows).
- **Sandbox / isolation** — `lenses/sandbox/active.py` tracks in-flight **subprocess** (and future Docker) handles per session id; **session_cancel** sets a cancel flag, **SIGKILL**s the worker, and marks the TaskletRun cancelled. Step execution is dispatched from `lenses/docs_health/isolation.py`:
  - **`LENSES_DOCS_HEALTH_STEP_BACKEND` unset or `inline`** — same-process execution (`session_steps.py`).
  - **`process`** — `python -m lenses.docs_health.step_cli` subprocess on the host (paths unchanged).
  - **`docker`** — `docker run` with `/workspace` and `/lenses-src` mounts (`lenses/sandbox/backends.py`). Requires an image that includes Lenses dependencies (see `LENSES_SANDBOX_IMAGE`); stock `python:3.12-slim` is a placeholder.
- **Apply subprocess env** — worker sets `LENSES_STEP_BUNDLE_WRITE=1` only for the **apply** step when the HTTP bundle allows writes.

### Forge Fleet + suggested branch (P1)

- **Suggested branch** — resolved per project checkout via `lenses.docs_health.git_branch_policy` (see [Git branch policy](../docs-health-git-branch-policy.md)); session JSON may include `git_branch_policy` (`source`, `trunk`, `style`).
- **Fleet** — optional **`LENSES_FLEET_URL`** + **`LENSES_FLEET_TOKEN`** (or Studio **Settings → Fleet**) so `session_step` can dispatch **Docker argv** jobs to the **forge-fleet** orchestrator (sibling repo; see its `README.md`) instead of in-process `docker` CLI. Fallback: `LENSES_DOCS_HEALTH_STEP_BACKEND` / inline / process as today.
- **Port back** — see [docs-health-port-back.md](docs-health-port-back.md).

## Sprint DOCS-2 — deterministic findings, score, history, Work sync

- **Scanner pack** (`lenses/docs_health/scanner.py`): required files + `required_doc_types` patterns, README sections, empty stub headings, broken `.md` / docs links (from files and optional **inventory** link graph), placeholders, ADR/release/diagram rules, `scope.module_paths` drift vs checkout, architecture doc section hint.
- **Findings / clusters:** each finding exposes `plain_language_summary`, `scope`, `expected_score_impact`, `affected_files`, `fixability` (`safe_auto_fix` reserved; not emitted yet), `score_area`. Clusters group by **severity + category** with `expected_score_gain_if_cleared`.
- **Score:** weighted headline from sub-scores (`required_files`, `sections`, `links`, `traceability`, `diagrams`, `quality`) plus `sum_based_score`, `potential_delta_if_resolved`, and an explicit `formula` string on the score object.
- **History:** each run stores `finding_diff` (`resolved_from_prior_scan`, `new_since_prior_scan`, `reopened_findings`) using `finding_lifecycle.json` per project. GET `/api/project/.../docs-health` includes `run_compare` vs the prior run when available.
- **Work:** stable ids `docs-debt-<finding_id>` upserted on each scan for major/critical, `ticket_only`, `manual`, or `suppressed` findings; items include `project_docs_health_href`, `finding_anchor`, severity, optional `due` / `owner` placeholders.
- **Workspace summary rollup:** `rollup.average_last_score`, `projects_with_critical_open_findings`, `open_docs_work_items_total`, and per-project `critical_open_findings` / `open_docs_work_items` when runs exist.

## Deferred / follow-ups

- Published or documented **sandbox image** (Dockerfile) with `lenses` + LLM client deps preinstalled for reliable `LENSES_DOCS_HEALTH_STEP_BACKEND=docker`.
- Durable event log (append-only) replacing file rewrite hot paths for very large sessions.
- WebSocket or SSE for token streaming (MVP uses polling on session page when status is live).
- Richer drift detection (git-based doc/code coupling).
- Separate “Admin” surface for dispatch policy beyond AI Setup task rows.
