"""Tests for lenses.llm_smart_routes."""

from __future__ import annotations

from lenses.llm_routing import ModelTier
from lenses.llm_smart_routes import apply_privacy_policy, smart_provider_for_task, tier_quality_bucket


def test_tier_quality_bucket() -> None:
    assert tier_quality_bucket(ModelTier.EXTRA_LOW) == "speed"
    assert tier_quality_bucket(ModelTier.MED) == "balanced"
    assert tier_quality_bucket(ModelTier.HIGH) == "quality"
    assert tier_quality_bucket(ModelTier.TOP) == "max"


def test_smart_provider_docs_health_prefers_local_first() -> None:
    pv = {
        "anthropic": True,
        "openai": True,
        "gemini": True,
        "ollama": True,
        "openai_compatible": True,
    }
    raw = {"provider": "openai", "tier": "MED"}
    p, _note = smart_provider_for_task("docs_health_writer", "openai", raw, pv)
    assert p == "ollama"


def test_smart_provider_embeddings_prefers_ollama() -> None:
    pv = {
        "anthropic": False,
        "openai": True,
        "gemini": False,
        "ollama": True,
        "openai_compatible": False,
    }
    raw = {"provider": "openai", "tier": "MED"}
    p, _note = smart_provider_for_task("embeddings_indexing", "openai", raw, pv)
    assert p == "ollama"


def test_apply_privacy_local_only() -> None:
    pv = {"ollama": True, "openai": True}
    p, mo, w = apply_privacy_policy("openai", "gpt-4o", "local_only", pv)
    assert p == "ollama"
    assert mo is None
    assert w is None


def test_apply_privacy_local_only_unsatisfied() -> None:
    pv = {"ollama": False, "openai_compatible": False, "openai": True}
    p, mo, w = apply_privacy_policy("openai", "gpt-4o", "local_only", pv)
    assert p == "openai"
    assert w == "local_unsatisfied"


def test_smart_provider_search_knowledge_prefers_primary_openai_compatible() -> None:
    """Lenses Copilot uses ``search_knowledge``; custom gateway as primary must win over hosted APIs."""
    pv = {
        "anthropic": True,
        "openai": True,
        "gemini": True,
        "ollama": True,
        "openai_compatible": True,
    }
    raw = {"provider": "openai_compatible", "tier": "MED"}
    p, note = smart_provider_for_task("search_knowledge", "openai_compatible", raw, pv)
    assert p == "openai_compatible"
    assert "openai_compatible" in note


def test_smart_provider_search_knowledge_lists_openai_compatible() -> None:
    """Previously ``search_knowledge`` never considered openai_compatible when OpenAI was connected."""
    pv = {
        "anthropic": False,
        "openai": True,
        "gemini": False,
        "ollama": False,
        "openai_compatible": True,
    }
    raw = {"provider": "openai", "tier": "MED"}
    p, _note = smart_provider_for_task("search_knowledge", "openai", raw, pv)
    assert p == "openai"
    p2, _note2 = smart_provider_for_task("search_knowledge", "openai_compatible", raw, pv)
    assert p2 == "openai_compatible"
