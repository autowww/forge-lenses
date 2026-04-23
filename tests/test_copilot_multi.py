"""Multi-step grounded copilot orchestration (mocked LLM)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses import llm_chat
from lenses.sdlc_copilot.chat import run_copilot_chat_multi
from lenses.sdlc_copilot.copilot_async_session import append_event, create_session, list_events_since


def test_multi_retries_after_deflection(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Second LLM call runs when first reply matches deflection heuristics."""
    tmp = tmp_path
    n = {"c": 0}

    def fake_chat(*_a, **_k):
        n["c"] += 1
        if n["c"] == 1:
            return {
                "ok": True,
                "text": "I'm unable to assist with that from this context alone; none of these items pertain.",
                "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
            }
        return {
            "ok": True,
            "text": "Here is a concrete answer with citation [1].",
            "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        }

    monkeypatch.delenv("LENSES_EXPERIMENTAL_SDLC_COPILOT", raising=False)
    monkeypatch.setattr(llm_chat, "chat", fake_chat)
    events: list[tuple[str, dict]] = []

    def on_event(typ: str, payload: dict) -> None:
        events.append((typ, payload))

    r = run_copilot_chat_multi(
        workspace_root=tmp,
        provider="ollama",
        user_message="Where are sticky notes?",
        model_override=None,
        refine=False,
        tool_mode="read_only",
        route="overview",
        project_slug=None,
        entity_id=None,
        scope_site="",
        login=None,
        scan_state={"children": [], "resolved_at": None},
        max_rounds=3,
        on_event=on_event,
    )
    assert n["c"] == 2
    assert r.get("ok") is True
    assert "Here is a concrete answer" in str(r.get("text") or "")
    trace = r.get("copilot_trace")
    assert isinstance(trace, dict)
    assert trace.get("stopped_reason") == "answered"
    rounds = trace.get("rounds")
    assert isinstance(rounds, list) and len(rounds) == 2
    assert rounds[0].get("deflected") is True
    assert rounds[1].get("deflected") is False
    u = r.get("usage")
    assert isinstance(u, dict)
    assert int(u.get("total_tokens") or 0) == 20
    assert any(t == "usage" for t, _ in events)


def test_multi_stops_on_max_rounds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tmp = tmp_path

    def fake_chat(*_a, **_k):
        return {
            "ok": True,
            "text": "I'm unable to assist; apologies for any inconvenience.",
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }

    monkeypatch.delenv("LENSES_EXPERIMENTAL_SDLC_COPILOT", raising=False)
    monkeypatch.setattr(llm_chat, "chat", fake_chat)
    r = run_copilot_chat_multi(
        workspace_root=tmp,
        provider="ollama",
        user_message="q",
        model_override=None,
        refine=False,
        tool_mode="read_only",
        route="overview",
        project_slug=None,
        entity_id=None,
        scope_site="",
        login=None,
        scan_state={"children": [], "resolved_at": None},
        max_rounds=2,
        on_event=None,
    )
    assert r.get("ok") is True
    trace = r.get("copilot_trace")
    assert trace.get("stopped_reason") == "max_rounds"
    assert len(trace.get("rounds") or []) == 2


def test_copilot_async_session_events(tmp_path: Path) -> None:
    sid = create_session(tmp_path)
    assert len(sid) == 32
    append_event(tmp_path, sid, "usage", {"cumulative": {"total_tokens": 3}})
    evs = list_events_since(tmp_path, sid, since_seq=-1)
    types = [e.get("type") for e in evs]
    assert "queued" in types
    assert "usage" in types
