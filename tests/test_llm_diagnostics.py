"""Tests for lenses.llm_diagnostics."""

from __future__ import annotations

from pathlib import Path

from lenses.llm_diagnostics import build_llm_diagnostics
from lenses.llm_usage_store import record_llm_chat_result, record_provider_probe


def test_build_llm_diagnostics_shape(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("LENSES_OPENAI_COMPAT_BASE_URL", raising=False)
    record_provider_probe(root, "openai", "health", {"ok": True, "healthy": False, "error": "not_configured"})
    record_llm_chat_result(
        root,
        "openai",
        ok=True,
        result={"ok": True, "usage": {"total_tokens": 3}},
        message="x",
        refine=False,
        routing_debug={"source": "override", "studio_task_id": "chat_assistant", "fallback_from": "ollama"},
        model_id="gpt-4o-mini",
    )
    out = build_llm_diagnostics(root)
    assert out.get("ok") is True
    assert isinstance(out.get("providers"), list)
    assert len(out["providers"]) == 5
    ids = [p["id"] for p in out["providers"]]
    assert ids == ["anthropic", "openai", "gemini", "ollama", "openai_compatible"]
    oa = next(p for p in out["providers"] if p["id"] == "openai")
    assert oa["last_probe"]["ok"] is False
    evs = out.get("routing_events") or []
    assert len(evs) >= 1
    assert evs[-1].get("studio_task_id") == "chat_assistant"
