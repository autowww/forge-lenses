"""Tests for Copilot map-reduce executor (mocked LLM)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses import llm_chat
from lenses.sdlc_copilot.map_reduce import run_copilot_map_reduce


def test_map_reduce_synthesizes_from_map_slices(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_chat(provider: str, message: str, model_override=None, **kwargs) -> dict:
        calls.append(message[:80])
        if "--- MAP TASK ---" in message:
            if "alpha" in message.lower():
                return {"ok": True, "text": "alpha: SDLC product site."}
            if "beta" in message.lower():
                return {"ok": True, "text": "beta: Shared design system."}
        if "--- MAP SUMMARIES ---" in message:
            return {
                "ok": True,
                "text": "1. alpha — SDLC product site.\n2. beta — Shared design system.",
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            }
        return {"ok": False, "error": "unexpected"}

    monkeypatch.setattr(llm_chat, "chat", fake_chat)

    scan = {
        "children": [
            {"name": "alpha", "is_git": True},
            {"name": "beta", "is_git": True},
        ],
        "resolved_at": None,
    }
    events: list[tuple[str, dict]] = []

    def emit(typ: str, payload: dict) -> None:
        events.append((typ, payload))

    out = run_copilot_map_reduce(
        workspace_root=tmp_path,
        provider="openai_compatible",
        user_message="describe each project in one sentence",
        model_override=None,
        refine=False,
        tool_mode="read_only",
        route="projects",
        project_slug=None,
        entity_id=None,
        scope_site="",
        login=None,
        scan_state=scan,
        strategy="portfolio_map_reduce",
        on_event=emit,
    )
    assert out.get("ok") is True
    assert "alpha" in str(out.get("text") or "")
    assert out.get("copilot_trace", {}).get("strategy") == "portfolio_map_reduce"
    assert out.get("copilot_trace", {}).get("map_results_count") == 2
    assert any(t == "plan" for t, _ in events)
    assert any(t == "subtask_start" for t, _ in events)
    assert len(calls) == 3  # 2 map + 1 reduce
