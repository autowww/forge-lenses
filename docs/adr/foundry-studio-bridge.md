# ADR: Foundry Studio bridge to forge-dark-factory

**Status:** Accepted (2026-07-03)  
**Context:** Lenses Studio needs a bounded conversation surface for Dark Factory L1 runs with human promote gates.

## Decision

1. Add **`lenses/foundry/`** as the HTTP + launcher bridge; wire **`serve.py`** dispatch for **`/api/foundry/*`** only (no inline route sprawl).
2. Piggyback on **B3** feature flags (`LENSES_EXPERIMENTAL_AGENTIC_BRIDGE_B3`) with optional **`LENSES_EXPERIMENTAL_FOUNDRY=0`** kill switch.
3. Studio routes **`/studio/foundry`** (composer + plan) and **`/studio/foundry/runs/:runId`** (stage bar + assay + approval).
4. L1 only in MVP: **`POST /api/foundry/runs`** rejects **L2/L3** with **501**; **`GET /api/foundry/capabilities`** documents the ladder honestly.
5. Promote is **file-scoped** copy from DF worktree → live target; **no auto-commit** — branching policy remains human/PR.
6. Deterministic plan + intake fallback when no LLM; fake worker + fixture for CI and offline proof.

## Consequences

- Requires sibling **`forge-dark-factory`** (or **`FOUNDRY_DARK_FACTORY_ROOT`**) for live runs.
- Run registry is JSON under **`.lenses-local/foundry-runs/`** (not orchestration graph entities yet).
- Higher autonomy levels need future wiring to DF campaigns and multi-unit plans.
