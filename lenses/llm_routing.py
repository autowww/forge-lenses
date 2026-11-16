"""Model tier resolution and adaptive adjustment (Situ8-aligned). Pure functions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

# Best-first (strongest / typically costliest first) — align with Situ8 LlmModels where overlapping.
OPENAI_QUALITY_ORDER: list[str] = [
    "o3",
    "o4-mini",
    "o1",
    "o1-mini",
    "gpt-4.1",
    "gpt-4o",
    "gpt-4-turbo",
    "o3-mini",
    "gpt-4.1-mini",
    "gpt-4o-mini",
    "gpt-4.1-nano",
    "gpt-3.5-turbo",
]

GEMINI_QUALITY_ORDER: list[str] = [
    "gemini-2.5-pro",
    "gemini-1.5-pro",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.5-flash-lite",
    "gemini-1.5-flash",
]

ANTHROPIC_QUALITY_ORDER: list[str] = [
    "claude-sonnet-4-20250514",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-3-haiku-20240307",
]


class ModelTier(str, Enum):
    NONE = "NONE"
    EXTRA_LOW = "EXTRA_LOW"
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"
    HIGHEST = "HIGHEST"
    TOP = "TOP"


# Slot 0 = TOP (best), slot 5 = EXTRA_LOW (cheapest in pool)
CLOUD_TIER_SLOTS: list[ModelTier] = [
    ModelTier.TOP,
    ModelTier.HIGHEST,
    ModelTier.HIGH,
    ModelTier.MED,
    ModelTier.LOW,
    ModelTier.EXTRA_LOW,
]


class TaskKind(str, Enum):
    CHAT = "CHAT"
    CODE = "CODE"
    REASONING = "REASONING"
    CREATIVE = "CREATIVE"
    SUMMARIZE = "SUMMARIZE"
    OTHER = "OTHER"


class Complexity(str, Enum):
    TRIVIAL = "TRIVIAL"
    MODERATE = "MODERATE"
    HEAVY = "HEAVY"


@dataclass(frozen=True)
class RequestClassification:
    task: TaskKind
    complexity: Complexity


def parse_tier(raw: str | None) -> ModelTier:
    if not raw or not str(raw).strip():
        return ModelTier.MED
    s = str(raw).strip().upper()
    try:
        return ModelTier(s)
    except ValueError:
        return ModelTier.MED


def quality_order_for_provider(provider: str) -> list[str]:
    p = provider.lower().strip()
    if p == "openai":
        return list(OPENAI_QUALITY_ORDER)
    if p == "gemini":
        return list(GEMINI_QUALITY_ORDER)
    if p == "anthropic":
        return list(ANTHROPIC_QUALITY_ORDER)
    return []


def order_for_catalog(provider: str, catalog: set[str]) -> list[str]:
    known = [m for m in quality_order_for_provider(provider) if m in catalog]
    rest = sorted(catalog - set(known))
    return known + rest


def tier_ladder_models(
    provider: str,
    pool: set[str],
    catalog: set[str],
) -> list[str]:
    """Ordered list of enabled models (best-first within pool)."""
    order = order_for_catalog(provider, catalog)
    return [m for m in order if m in pool]


def ordered_model_list(
    provider: str,
    pool: set[str],
    catalog: set[str],
    pool_order: list[str] | None,
) -> list[str]:
    """If ``pool_order`` is set, use that sequence (best-first). Else use quality order."""
    if pool_order:
        out = [x.strip() for x in pool_order if x.strip() and x.strip() in pool]
        return out
    return tier_ladder_models(provider, pool, catalog)


def pick_from_ordered(
    ordered: list[str],
    tier: ModelTier,
    fallback: str,
) -> str:
    if not ordered:
        return fallback
    n = len(ordered)
    if n == 1:
        return ordered[0]
    if tier == ModelTier.NONE:
        return fallback
    slot = CLOUD_TIER_SLOTS.index(tier) if tier in CLOUD_TIER_SLOTS else 5
    idx = (slot * (n - 1)) // 5
    idx = max(0, min(n - 1, idx))
    return ordered[idx]


def adaptive_adjust(
    ordered_best_first: list[str],
    tier: ModelTier,
    fallback: str,
    c: RequestClassification,
) -> str:
    """Situ8 AdaptiveModelMapper.adjust port."""
    if not ordered_best_first:
        return fallback
    n = len(ordered_best_first)
    if n == 1:
        return ordered_best_first[0]

    slot = CLOUD_TIER_SLOTS.index(tier) if tier in CLOUD_TIER_SLOTS else 5
    idx = ((slot * (n - 1)) // 5)
    idx = max(0, min(n - 1, idx))

    if c.complexity == Complexity.HEAVY:
        idx = max(0, idx - 2)
    elif c.complexity == Complexity.TRIVIAL:
        idx = min(n - 1, idx + 2)

    if c.task in (TaskKind.CODE, TaskKind.REASONING, TaskKind.CREATIVE):
        idx = max(0, idx - 1)
    elif c.task == TaskKind.SUMMARIZE:
        idx = min(n - 1, idx + 1)

    return ordered_best_first[idx]


def refinement_shift_toward_cheaper(
    ordered_best_first: list[str],
    current_model: str,
    steps: int,
) -> str:
    """Move index toward cheaper (higher index in best-first list)."""
    if not ordered_best_first or steps <= 0:
        return current_model
    try:
        i = ordered_best_first.index(current_model)
    except ValueError:
        return current_model
    n = len(ordered_best_first)
    j = min(n - 1, i + steps)
    return ordered_best_first[j]


def parse_classification(raw: dict[str, Any] | None) -> RequestClassification | None:
    if not raw or not isinstance(raw, dict):
        return None
    t = str(raw.get("task", "OTHER")).upper()
    x = str(raw.get("complexity", "MODERATE")).upper()
    try:
        task = TaskKind(t)
    except ValueError:
        task = TaskKind.OTHER
    try:
        comp = Complexity(x)
    except ValueError:
        comp = Complexity.MODERATE
    return RequestClassification(task=task, complexity=comp)
