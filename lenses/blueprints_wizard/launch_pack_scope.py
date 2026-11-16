"""Resolve artifact keys for Cursor Launch Pack export from scope closure options (experimental)."""

from __future__ import annotations

from typing import Any

from lenses.blueprints_wizard.artifact_generation_dependencies import (
    ARTIFACT_UPSTREAM_AND,
    ARTIFACT_UPSTREAM_ONE_OF,
    upstream_keys_for_generation,
)
from lenses.blueprints_wizard.artifact_generation_normalize import ARTIFACT_SLICE_KEYS

# Keys treated as shared contracts / interfaces (subset of planning + engineering surfaces).
CONTRACT_LIKE_KEYS = frozenset(
    {
        "prd",
        "architecture_brief",
        "dependency_map",
        "adr_seeds",
        "nfr_checklist",
    }
)

VERIFICATION_KEYS = frozenset(
    {
        "acceptance_criteria",
        "qa_verification_checklist",
        "rollout_notes",
    })

_MAX_CLOSURE_KEYS = 48
_MAX_DOWNSTREAM_ROUNDS = 12


def _valid_keys(raw: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for x in raw:
        k = str(x).strip()
        if not k or k not in ARTIFACT_SLICE_KEYS or k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out


def _order_keys(keys: set[str]) -> list[str]:
    order = {k: i for i, k in enumerate(ARTIFACT_SLICE_KEYS)}
    return sorted(keys, key=lambda x: order.get(x, 999))


def _downstream_one_hop(working: set[str]) -> set[str]:
    """Artifacts that list any key in ``working`` as an upstream dependency."""
    out: set[str] = set()
    for ak, deps in ARTIFACT_UPSTREAM_AND.items():
        if ak in working:
            continue
        if any(d in working for d in deps):
            out.add(ak)
    for ak, groups in ARTIFACT_UPSTREAM_ONE_OF.items():
        if ak in working:
            continue
        for group in groups:
            if any(g in working for g in group):
                out.add(ak)
                break
    return out


def _expand_downstream(working: set[str]) -> tuple[set[str], list[str]]:
    """Transitive downstream (limited rounds) to avoid exporting the entire graph."""
    trace: list[str] = []
    cur = set(working)
    for round_i in range(_MAX_DOWNSTREAM_ROUNDS):
        nxt = _downstream_one_hop(cur)
        nxt -= cur
        if not nxt:
            break
        added = nxt & set(ARTIFACT_SLICE_KEYS)
        if not added:
            break
        trace.append(f"downstream_round_{round_i + 1}: +{sorted(added)}")
        cur |= added
        if len(cur) >= _MAX_CLOSURE_KEYS:
            trace.append(f"downstream_capped_at_{_MAX_CLOSURE_KEYS}_keys")
            break
    return cur, trace


def resolve_launch_pack_artifact_keys(
    base_keys: list[str],
    closure_options: list[str],
    arts: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """
    Returns (ordered_artifact_keys, human_readable_trace_lines).

    If ``exact_only`` is among ``closure_options``, only normalized ``base_keys`` are returned
    (other closure flags are ignored).
    """
    opts = frozenset(str(x).strip() for x in closure_options if str(x).strip())
    base = _valid_keys(base_keys)
    trace: list[str] = []

    if not base:
        return [], ["error: no valid base artifact keys"]

    if "exact_only" in opts:
        trace.append("exact_only: no expansion beyond selected keys")
        return _order_keys(set(base)), trace

    working = set(base)
    trace.append(f"base: {sorted(working)}")

    if "include_required_upstream" in opts:
        up = upstream_keys_for_generation(frozenset(working), arts)
        added = (up & set(ARTIFACT_SLICE_KEYS)) - working
        if added:
            trace.append(f"include_required_upstream: +{sorted(added)}")
        working |= up

    if "include_shared_contracts" in opts:
        bubble = set(working) | set(upstream_keys_for_generation(frozenset(base), arts))
        contracts = (CONTRACT_LIKE_KEYS & bubble) - working
        if contracts:
            trace.append(f"include_shared_contracts: +{sorted(contracts)}")
        working |= CONTRACT_LIKE_KEYS & bubble

    if "include_downstream_impacted" in opts:
        before = len(working)
        working, dtrace = _expand_downstream(working)
        trace.extend(dtrace)
        if len(working) == before and not dtrace:
            trace.append("include_downstream_impacted: no additional keys")

    if "include_verification_artifacts" in opts:
        ver = VERIFICATION_KEYS - working
        if ver:
            trace.append(f"include_verification_artifacts: +{sorted(ver)}")
        working |= VERIFICATION_KEYS

    if len(working) > _MAX_CLOSURE_KEYS:
        ordered = _order_keys(working)
        working = set(ordered[:_MAX_CLOSURE_KEYS])
        trace.append(f"warning: truncated to first {_MAX_CLOSURE_KEYS} keys in canonical order")

    return _order_keys(working), trace
