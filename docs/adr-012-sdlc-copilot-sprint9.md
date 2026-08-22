# ADR-012 — Grounded SDLC copilot (Sprint 9)

## Status

Accepted — implemented in forge-lenses.

## Context

Studio **Search** and **Chat** were useful but disconnected from the canonical orchestration graph, quality/DevSecOps/Ops fixtures, and local evidence. Operators need answers tied to **product data**, with **auditable** prompts and **permissioned** write paths—not silent mutations.

## Decision

1. **Retrieval** — Before each LLM call, assemble a numbered **source bundle** from: FTS **`search_db`** (scoped optional), **orchestration graph** entities (recent rows + optional BFS trace from `entity_id`), **`build_cross_team_release_overview`**, **`build_quality_overview_payload`**, **`build_devsecops_overview_payload`**, **`build_ops_delivery_overview`**, and **recent `llm-usage.json` events** (metadata only, not user prompts).
2. **Prompting** — Prepend sources to the user question in one message (existing `llm_chat.chat` transport); instruct the model to cite `[n]` for every factual claim.
3. **Tool modes** — **`read_only`**: answers only. **`propose_writes`**: same, plus heuristic **draft proposals** (risk exception scaffold, test plan scaffold, PR↔work-item stub, release readiness excerpt, rollback notes, postmortem stub). Proposals are **JSON files** under **`.lenses-local/copilot-proposals/`** with TTL; no automatic graph/file writes.
4. **Commit** — **`POST /api/sdlc-copilot/commit-proposal`** writes a Markdown export under **`.lenses-local/copilot-exports/`** after re-checking RBAC; staging file is deleted.
5. **Audit** — Append-only **`.lenses-local/sdlc-copilot-audit.jsonl`** records chat turns (`prompt_excerpt`, citation count, proposals count, operator login) and commits.
6. **Studio** — **`CopilotPanel`** on **Plan**, **Search**, **Project** detail, **Knowledge** (`/workspace-md`), and primary **Chat** route; legacy ungrounded chat remains behind a disclosure.

## Consequences

- **Positive** — Grounding is explainable via citations; writes are explicit, permissioned, and export-shaped for human review.
- **Negative** — Large workspaces may hit **`MAX_MESSAGE_CHARS`**; grounding may truncate (flagged in the response). Heuristic proposals may misfire; operators must confirm exports.
- **Follow-up** — Optional multi-message chat in `llm_completions`; stronger intent routing for drafts; project-scoped grounding filters on aggregates.
- **Follow-up (2026-06)** — **Map-reduce Copilot** for portfolio / broad workspace asks: intent router + scoped FTS subtasks + reduce synthesis (`lenses/sdlc_copilot/map_reduce.py`). Supplements deflect-retry for “describe each project” style questions; gated by `LENSES_COPILOT_MAP_REDUCE` (default on when git repo count > 8 on portfolio route). **Algorithm doc:** [copilot-map-reduce-retrieval.md](copilot-map-reduce-retrieval.md).
