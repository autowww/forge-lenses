# Lenses Studio — AI Setup page (design)

This note complements the normative blueprint [`llm-app-settings-and-routing.md`](../../blueprints/sdlc/methodologies/forge/llm-app-settings-and-routing.md) (§6) with **implementation-facing** detail for **forge-lenses** only.

## Route and shell

- **URL:** `/studio/settings/llm` (unchanged for bookmarks).
- **Product name:** **AI Setup** (replaces the legacy label “LLM preferences” in navigation and headers).
- **Shell:** Same three-column Studio layout — left nav, center setup dashboard, right contextual rail (help, evidence, next steps).

## Center panel — section order

1. **Summary row** — chips: count of connected providers, routing mode label, Ollama reachability (from `GET /api/llm/ollama-status`). Actions: **Add provider** (scroll to cloud keys), **Test setup** (link to `/studio/chat`), **Open chat test** (same).
2. **Setup sources** — grouped by type:
   - **Cloud:** OpenAI, Anthropic, Google — each card: connection status, masked key hint, optional “last successful chat” from usage.
   - **Custom:** OpenAI-compatible gateway (single base URL via server env today); surfaced as its own subsection.
   - **Local (Ollama):** `OLLAMA_BASE_URL`, reachability, **installed model names** when `GET /api/llm/ollama-status` returns a `models` array from Ollama’s tags API.
3. **Routing** — radio: Single model / Smart multi-model / Advanced routing (maps to `advanced_ui`, `auto_model`, `adaptive_autoselection`). **Quality** slider with Speed → Max labels (maps to discrete `tier`). **Routing preview** table from `GET /api/llm/routing-preview` (server-side resolution; refresh after **Save**).
4. **Per–task-category routes** — shown when **two or more** providers are connected (`GET /api/llm/providers`). Each row: task label, provider select, optional model id; persisted as `task_routes` in `llm-settings.json`.
5. **Diagnostics** — token usage block (existing), links to technical details.

## Progressive disclosure (enforced in UI)

- **0 providers:** Empty-state copy points to README and env vars; primary CTA to connect keys or Ollama.
- **1 provider:** Routing mode locked to **Single** (other modes disabled with short explanation).
- **2+ providers:** Smart and Advanced routing enabled; per-task table visible.

## APIs (trust boundary)

Privileged like other LLM endpoints: **loopback by default**; `LENSES_ALLOW_ACTIONS=1` relaxes client IP checks (document in README).

| Endpoint | Role |
|----------|------|
| `GET /api/llm/providers` | Booleans per provider (env + settings file keys). |
| `GET /api/llm/ollama-status` | Reachability + `models[]` when tags JSON parses. |
| `GET /api/llm/settings` | Masked settings including `task_routes`, `routing_mode`, `version`. |
| `POST /api/llm/settings` | Merge save (same trust boundary). |
| `GET /api/llm/routing-preview` | Resolved provider/model per `studio_task_id` for the table. |
| `POST /api/llm/chat` | Optional `studio_task_id` for task-based routing. |
| `POST /api/sdlc-copilot/chat` | Optional `studio_task_id` (default grounded path uses `search_knowledge`). |

## Deferred (explicitly not this page)

- Multiple named custom gateways (single `openai_compatible` + env today).
- Ollama pull/remove via Studio API (script + host shell remain the supported path).
- Same-prompt multi-model fan-out, compare, judge, consensus.

## See also

- [`../../README.md`](../../README.md) — operator setup for providers and env vars.
- `lenses/llm_studio_tasks.py` — stable `studio_task_id` constants and labels.
