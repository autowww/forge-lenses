"""Tests for lenses.llm_usage_store."""

from __future__ import annotations

from pathlib import Path

from lenses.llm_usage_store import (
    get_usage_summary,
    ollama_model_last_used_iso,
    record_chat_completion,
    record_llm_chat_result,
    record_provider_probe,
)


def test_record_and_summary(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    record_chat_completion(
        root,
        "openai",
        {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    )
    s = get_usage_summary(root)
    assert "openai" in s["totals"]
    assert s["totals"]["openai"]["total_tokens"] == 15
    assert s["totals"]["openai"]["requests"] == 1
    assert s["totals"]["openai"]["attempts"] == 1
    assert s["totals"]["openai"]["failures"] == 0
    assert "openai" in s["last_ok"]
    assert len(s["recent_events"]) == 1
    assert s["recent_events"][0].get("ok") is True


def test_record_failure_increments_failures(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    record_llm_chat_result(
        root,
        "ollama",
        ok=False,
        result={"ok": False, "error": "llm_transport", "detail": "connection refused"},
        message="hello",
        refine=False,
        routing_debug={"source": "manual_main"},
        model_id="llama3.2",
    )
    s = get_usage_summary(root)
    t = s["totals"]["ollama"]
    assert t["attempts"] == 1
    assert t["failures"] == 1
    assert t["requests"] == 0
    assert t["total_tokens"] == 0
    assert "ollama" not in s["last_ok"]
    ev = s["recent_events"][0]
    assert ev.get("ok") is False
    assert ev.get("error") == "llm_transport"
    assert ev.get("message_chars") == 5


def test_ollama_model_last_used_iso_newest_wins(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    record_llm_chat_result(
        root,
        "ollama",
        ok=True,
        result={"ok": True, "usage": {"total_tokens": 1}},
        message="a",
        refine=False,
        routing_debug={},
        model_id="llama3.2:latest",
    )
    record_llm_chat_result(
        root,
        "ollama",
        ok=True,
        result={"ok": True, "usage": {"total_tokens": 1}},
        message="b",
        refine=False,
        routing_debug={},
        model_id="mistral:7b",
    )
    m = ollama_model_last_used_iso(root)
    assert "llama3.2:latest" in m
    assert "mistral:7b" in m
    assert len(m["llama3.2:latest"]) > 10
    assert len(m["mistral:7b"]) > 10


def test_record_provider_probe_in_summary(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    record_provider_probe(root, "openai", "health", {"ok": True, "healthy": True, "model_count": 3})
    s = get_usage_summary(root)
    pl = s.get("probe_log") or []
    assert len(pl) == 1
    assert pl[0].get("provider") == "openai"
    assert pl[0].get("action") == "health"
    assert pl[0].get("ok") is True


def test_routing_fields_on_chat_event(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    record_llm_chat_result(
        root,
        "openai",
        ok=True,
        result={"ok": True, "usage": {"total_tokens": 2}},
        message="hi",
        refine=False,
        routing_debug={
            "source": "task_route",
            "model": "gpt-4o-mini",
            "fallback_from": "ollama",
            "studio_task_id": "chat_assistant",
        },
        model_id="gpt-4o-mini",
    )
    ev = get_usage_summary(root)["recent_events"][-1]
    assert ev.get("routing_source") == "task_route"
    assert ev.get("fallback_from") == "ollama"
    assert ev.get("studio_task_id") == "chat_assistant"
