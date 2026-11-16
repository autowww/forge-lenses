# Copilot map-reduce retrieval and synthesis

How Forge Lenses **SDLC Copilot** answers broad workspace questions (for example “describe each project in one sentence”) without stuffing the entire portfolio into a single LLM prompt.

**Related:** [ADR-012 — Grounded SDLC copilot](adr-012-sdlc-copilot-sprint9.md) (original single-shot grounding design).

---

## Problem

The default Copilot path builds **one large grounding bundle** (FTS hits, workspace roster, graph rollups, aggregates) and sends it in a **single** `llm_chat.chat` call, capped at `MAX_MESSAGE_CHARS` (32 000).

That works for focused questions. It fails for **enumerate-the-whole-workspace** asks:

- Too much context → truncation or weak answers
- Slow custom gateways time out on one giant prompt
- Models deflect or hallucinate when asked to cover 20+ repos at once

**Map-reduce** decomposes the ask: **plan → map (many small calls) → reduce (one synthesis call)**.

---

## When map-reduce runs

Entry point: `run_copilot_chat` and `run_copilot_chat_multi` in [`lenses/sdlc_copilot/chat.py`](../lenses/sdlc_copilot/chat.py). Before the legacy deflect-retry loop, Copilot classifies the turn and may delegate to [`run_copilot_map_reduce`](../lenses/sdlc_copilot/map_reduce.py).

### 1. Intent classification

Module: [`lenses/sdlc_copilot/intent.py`](../lenses/sdlc_copilot/intent.py)

| Strategy | Meaning |
|----------|---------|
| `single_shot` | Normal Copilot — one grounding bundle, one LLM call |
| `portfolio_map_reduce` | One subtask per git repo (or batched repos) from workspace scan |
| `search_map_reduce` | Subtasks from top FTS hits grouped by `local-site` repo |

**Heuristic triggers (no extra LLM call):**

- **Projects route** + phrasing like “each/every/all … project/repo” → `portfolio_map_reduce`
- **Projects route** + “list/describe/summarize … project/portfolio” → `portfolio_map_reduce`
- Message mentions **across / whole workspace / all repos** + many workspace children → `search_map_reduce`
- Otherwise → `single_shot`

### 2. Feature gate

Function: `map_reduce_enabled()` in `intent.py`

| Environment variable | Effect |
|---------------------|--------|
| `LENSES_COPILOT_MAP_REDUCE=0` | Force off |
| `LENSES_COPILOT_MAP_REDUCE=1` | Force on (when strategy ≠ `single_shot`) |
| *(unset)* | **Default on** for `portfolio_map_reduce` / `search_map_reduce` when **git repo count > 8** |

---

## Algorithm (high level)

```
User message + Studio route + workspace scan
        │
        ▼
 classify_copilot_strategy()
        │
        ├─ single_shot ──► build_grounding_bundle() ──► one llm_chat.chat()
        │
        └─ portfolio_map_reduce | search_map_reduce
                │
                ▼
           build_plan()          ← planner.py
                │
                ▼
     For each subtask (map phase):
       build_scoped_grounding_for_subtask()   ← slim FTS + charge.md
       llm_chat.chat(MAP TASK prompt)        ← small context / small answer
       collect map_results[], citations[]
                │
                ▼
     llm_chat.chat(REDUCE prompt)             ← map summaries only
                │
                ▼
     Final answer + merged citations + copilot_trace
```

---

## Planning (subtasks)

Module: [`lenses/sdlc_copilot/planner.py`](../lenses/sdlc_copilot/planner.py)

Each **subtask** includes:

| Field | Purpose |
|-------|---------|
| `subtask_id` | Stable id (`portfolio-1`, `search-3`, …) |
| `label` | UI progress label (repo name or batch) |
| `scope_site` | Workspace child name — boosts FTS under `/local-site/<site>/` |
| `related_md_rel_paths` | Allowlisted paths (e.g. `<repo>/forge/charge.md` when present) |
| `fts_query` | Repo-scoped FTS query string |
| `user_sub_prompt` | Instruction for the map-phase LLM call |
| `max_citations` | Small cap (default 8) per slice |

**Portfolio plan:** git repos from `scan_state.children` (optional folders if message mentions “folder”).  
**Search plan:** top FTS hits grouped by site; falls back to portfolio plan if no hits.

**Limits:**

| Variable | Default | Meaning |
|----------|---------|---------|
| `LENSES_COPILOT_MAP_MAX_SUBTASKS` | 30 | Max map calls per turn |
| `LENSES_COPILOT_MAP_BATCH_SIZE` | 1 | Repos per map call (increase to 4 on slow gateways) |

If the workspace exceeds the cap, the plan sets `truncated` and the reduce step carries an honest note.

---

## Scoped grounding (map phase)

Module: [`lenses/sdlc_copilot/grounding.py`](../lenses/sdlc_copilot/grounding.py)

`build_scoped_grounding_for_subtask()` calls `build_grounding_bundle()` with:

- `skip_sections`: page context, roster, orchestration, rollups (no workspace-wide noise)
- `fts_query_override`: per-subtask query
- `scope_site`: repo-scoped search boost
- `related_md_rel_paths`: repo `forge/charge.md` when the file exists
- `max_citations`: 4–12 (typically 8)

Target size: ~2–4 k characters of context per map call, not the full 32 k bundle.

Retrieval is **SQLite FTS5** ([`lenses/search_db.py`](../lenses/search_db.py)), not a vector index. Hybrid embeddings are a documented follow-up (see ADR-012).

---

## Map phase

Module: [`lenses/sdlc_copilot/map_reduce.py`](../lenses/sdlc_copilot/map_reduce.py)

For each subtask, sequentially:

1. Build scoped grounding block + citations (renumbered globally across slices).
2. Compose prompt: `{grounding}\n\n--- MAP TASK ---\n{user_sub_prompt}`.
3. Call `llm_chat.chat()` — same provider/model as the Copilot rail.
4. Append `{label, text, ok, repo_names}` to `map_results`.
5. Emit SSE events (async Studio path): `subtask_start`, `subtask_end`, `usage`.

Map prompts instruct the model to answer **only from attached sources**, one line per entry, and to say when context is missing.

If a map step fails (`ok: false`), execution **continues** with remaining subtasks; the reduce step synthesizes from whatever succeeded.

---

## Reduce phase

One final `llm_chat.chat()` with:

- Original user question
- **Map summaries only** (no raw file bodies)
- Instructions: preserve numbering/names, do not invent repos, carry forward “unknown” gaps

Output becomes the operator-facing reply. Citations from all map slices are merged into the response `citations` array.

---

## Studio / API surface

| Surface | Behavior |
|---------|----------|
| `POST /api/sdlc-copilot/chat-async` + SSE | Map-reduce emits `plan`, `subtask_start`, `subtask_end`, `thought`, `usage`, then `final` |
| `POST /api/sdlc-copilot/chat` | Same orchestration via `run_copilot_chat` |
| **Projects** Copilot rail | Prefill: `PROJECT_PORTFOLIO_COPILOT_DEFAULT` in [`studioVisibleCopy.ts`](../lenses-enterprise/src/nav/studioVisibleCopy.ts) |
| Thinking blade | Shows “Summarizing 3/26: forge-lenses…” during map phase |
| Response metadata | `copilot_trace.strategy`, `subtask_count`, `map_results_count`, `stopped_reason: map_reduce` |

---

## Comparison: single-shot vs map-reduce

| | Single-shot | Map-reduce |
|---|-------------|------------|
| Grounding | One bundle (up to ~48 citations) | Many slim bundles (~8 citations each) |
| LLM calls | 1 (+ up to 3 deflect retries) | N map + 1 reduce |
| Best for | One repo, docs-health, narrow facts | “Each project…”, portfolio summaries |
| Retrieval | FTS + graph + rollups | FTS scoped per repo + charge.md |
| Failure mode | Deflect / truncate | Per-slice failure + partial reduce |

Legacy **deflect-retry** (`run_copilot_chat_multi` widening citations) still runs when strategy is `single_shot` or map-reduce is disabled.

---

## Source files (implementation map)

| File | Role |
|------|------|
| [`lenses/sdlc_copilot/intent.py`](../lenses/sdlc_copilot/intent.py) | Strategy classification + feature gate |
| [`lenses/sdlc_copilot/planner.py`](../lenses/sdlc_copilot/planner.py) | Subtask plan generation |
| [`lenses/sdlc_copilot/grounding.py`](../lenses/sdlc_copilot/grounding.py) | Full + scoped grounding bundles |
| [`lenses/sdlc_copilot/map_reduce.py`](../lenses/sdlc_copilot/map_reduce.py) | Map + reduce executor |
| [`lenses/sdlc_copilot/chat.py`](../lenses/sdlc_copilot/chat.py) | Wiring into sync/async Copilot |
| [`lenses-enterprise/src/components/LensesCopilotRail.tsx`](../lenses-enterprise/src/components/LensesCopilotRail.tsx) | SSE progress UI |

---

## Tests

| Test file | Covers |
|-----------|--------|
| [`tests/test_sdlc_copilot_intent.py`](../tests/test_sdlc_copilot_intent.py) | Strategy + env gate |
| [`tests/test_sdlc_copilot_planner.py`](../tests/test_sdlc_copilot_planner.py) | Subtask plans |
| [`tests/test_sdlc_copilot_map_reduce.py`](../tests/test_sdlc_copilot_map_reduce.py) | Map + reduce with mocked LLM |
| [`tests/test_copilot_multi.py`](../tests/test_copilot_multi.py) | `run_copilot_chat_multi` routing |

Run: `python3 -m pytest tests/test_sdlc_copilot_intent.py tests/test_sdlc_copilot_planner.py tests/test_sdlc_copilot_map_reduce.py tests/test_copilot_multi.py -q`

---

## Future work (not implemented)

- **Hybrid vector retrieval** — sqlite-vec or sidecar embeddings; FTS shortlist → vector rerank per subtask (`embeddings_indexing` task route in LLM settings).
- **Optional LLM intent classifier** — `LENSES_COPILOT_INTENT_LLM=1` for ambiguous turns (planned, not shipped in phase 1).
- **Parallel map batches** — sequential today; optional concurrency when gateway is stable.
