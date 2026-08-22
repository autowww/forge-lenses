"""Cross-provider picks for ``routing_mode: smart`` (Studio multi-model routing)."""

from __future__ import annotations

from typing import Final

from lenses.llm_routing import ModelTier, parse_tier

_CLOUD: Final[frozenset[str]] = frozenset({"anthropic", "openai", "gemini"})
_LOCALISH: Final[frozenset[str]] = frozenset({"ollama", "openai_compatible"})


def tier_quality_bucket(tier: ModelTier) -> str:
    """Map internal tier enum to four UX stops: speed / balanced / quality / max."""
    if tier in (ModelTier.TOP, ModelTier.HIGHEST):
        return "max"
    if tier == ModelTier.HIGH:
        return "quality"
    if tier == ModelTier.MED:
        return "balanced"
    return "speed"


def quality_bucket_from_settings(raw: dict) -> str:
    return tier_quality_bucket(parse_tier(str(raw.get("tier", "MED"))))


def _first_available(order: tuple[str, ...], pv: dict[str, bool], default_p: str) -> str:
    for pid in order:
        if pv.get(pid):
            return pid
    if pv.get(default_p):
        return default_p
    for k, ok in pv.items():
        if ok:
            return str(k)
    return (default_p or "openai").strip() or "openai"


def _preferred_order(default_p: str, pv: dict[str, bool], base: tuple[str, ...]) -> tuple[str, ...]:
    """Try workspace primary first when it is one of the candidates and is connected (fixes custom gateway + Smart)."""
    d = (default_p or "").strip().lower() or "openai"
    if d in base and pv.get(d):
        return (d,) + tuple(x for x in base if x != d)
    return base


def smart_provider_for_task(task_id: str, default_p: str, raw: dict, pv: dict[str, bool]) -> tuple[str, str]:
    """Return (provider_id, routing_note) for smart multi-model routing."""
    bucket = quality_bucket_from_settings(raw)
    d = (default_p or "openai").strip().lower() or "openai"

    def pick(*order: str) -> tuple[str, str]:
        pid = _first_available(order, pv, d)
        return pid, f"smart:{task_id}:{bucket}→{pid}"

    if task_id == "embeddings_indexing":
        return pick("ollama", "openai_compatible", "openai", "gemini", d)
    if task_id == "vision_ocr":
        return pick("gemini", "openai", "anthropic", "ollama", "openai_compatible", d)
    if task_id == "code_automation":
        if bucket == "speed":
            return pick("openai", "ollama", "gemini", "openai_compatible", "anthropic", d)
        if bucket == "max":
            return pick("anthropic", "openai", "gemini", "ollama", d)
        if bucket == "quality":
            return pick("anthropic", "openai", "gemini", "ollama", d)
        return pick("openai", "anthropic", "gemini", "ollama", d)
    if task_id == "plans_generation":
        if bucket == "speed":
            return pick("gemini", "openai", "ollama", d)
        if bucket in ("quality", "max"):
            return pick("anthropic", "openai", "gemini", d)
        return pick("openai", "anthropic", "gemini", d)
    if task_id == "site_drafting":
        return pick("openai", "gemini", "anthropic", "ollama", d)
    if task_id == "extraction_classification":
        if bucket == "speed":
            return pick("gemini", "openai", "ollama", d)
        return pick("openai", "gemini", "anthropic", d)
    if task_id == "search_knowledge":
        base = ("openai", "gemini", "anthropic", "ollama", "openai_compatible")
        return pick(*_preferred_order(d, pv, base))
    if task_id == "chat_assistant":
        if bucket == "speed":
            return pick("gemini", "openai", "ollama", "openai_compatible", "anthropic", d)
        if bucket == "max":
            return pick("anthropic", "openai", "gemini", d)
        if bucket == "quality":
            return pick("anthropic", "openai", "gemini", "ollama", d)
        return pick("openai", "gemini", "anthropic", "ollama", d)
    if task_id in (
        "docs_health_enricher",
        "docs_health_cluster",
        "docs_health_writer",
        "docs_health_diagram",
        "docs_health_decision",
        "docs_health_reviewer",
    ):
        return pick("ollama", "openai_compatible", "openai", "gemini", "anthropic", d)
    # default / unknown task id
    base = ("openai", "gemini", "anthropic", "ollama", "openai_compatible")
    return pick(*_preferred_order(d, pv, base))


def apply_privacy_policy(
    provider: str,
    model_override: str | None,
    privacy: str,
    pv: dict[str, bool],
) -> tuple[str, str | None, str | None]:
    """
    Enforce per-task privacy. Returns (provider, model_override, warn_code or None).

    ``warn_code`` is ``local_unsatisfied`` when local_only could not move off cloud.
    """
    p = (provider or "").strip().lower()
    pr = (privacy or "cloud_allowed").strip().lower()
    if pr not in ("local_only", "prefer_local", "cloud_allowed"):
        pr = "cloud_allowed"
    mo = (model_override or "").strip() or None
    mo_s = mo if mo else None

    def local_substitute() -> tuple[str, str | None] | None:
        if pv.get("ollama"):
            return "ollama", None
        if pv.get("openai_compatible"):
            return "openai_compatible", None
        return None

    if p in _LOCALISH or pr == "cloud_allowed":
        return p, mo_s, None

    if pr == "local_only":
        sub = local_substitute()
        if sub:
            return sub[0], sub[1], None
        return p, mo_s, "local_unsatisfied"

    if pr == "prefer_local":
        sub = local_substitute()
        if sub:
            return sub[0], sub[1], None
        return p, mo_s, None

    return p, mo_s, None
