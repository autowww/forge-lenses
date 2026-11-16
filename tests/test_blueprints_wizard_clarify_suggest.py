"""Tests for clarification suggest API (experimental Blueprints Wizard)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.blueprints_wizard.api import parse_session_clarify_suggest_path
from lenses.blueprints_wizard.clarification_llm import suggest_clarification_questions
from lenses.blueprints_wizard.session_store import create_session


def test_parse_clarify_suggest_path() -> None:
    assert parse_session_clarify_suggest_path("/api/blueprints/wizard/session/abcdef12/clarify-suggest") == "abcdef12"
    assert parse_session_clarify_suggest_path("/api/blueprints/wizard/session/abc/extra") is None


def test_suggest_without_llm_returns_deterministic(tmp_path: Path) -> None:
    sid = create_session(tmp_path)
    det = [{"id": "q1", "text": "Q?", "why_it_matters": "w", "answer_type": "short_text", "default_assumption_if_skipped": "d", "priority": 1}]
    out = suggest_clarification_questions(tmp_path, sid, {"deterministic_questions": det, "use_llm": False})
    assert out.get("ok") is True
    assert len(out.get("questions", [])) == 1


def test_suggest_mock_llm_merges(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LENSES_CLARIFICATION_SUGGEST_MOCK", "1")
    sid = create_session(tmp_path)
    det = [{"id": "q1", "text": "Q?", "why_it_matters": "w", "answer_type": "short_text", "default_assumption_if_skipped": "d", "priority": 1}]
    out = suggest_clarification_questions(tmp_path, sid, {"deterministic_questions": det, "use_llm": True})
    assert out.get("ok") is True
    qs = out.get("questions", [])
    assert len(qs) >= 2
