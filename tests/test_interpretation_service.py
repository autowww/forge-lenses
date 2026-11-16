"""Interpretation service and LLM path (mocked)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.blueprints_wizard.api import parse_session_interpret_path
from lenses.blueprints_wizard.interpretation_service import interpret_wizard_session, interpretation_mock_enabled
from lenses.blueprints_wizard.session_store import create_session, load_session


def test_parse_session_interpret_path() -> None:
    sid = "a" * 16
    assert parse_session_interpret_path(f"/api/blueprints/wizard/session/{sid}/interpret") == sid
    assert parse_session_interpret_path(f"/api/blueprints/wizard/session/{sid}/interpret/") == sid
    assert parse_session_interpret_path("/api/blueprints/wizard/session/") is None
    assert parse_session_interpret_path(f"/api/blueprints/wizard/session/{sid}") is None


def test_interpret_mock_persists(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LENSES_INTERPRETATION_MOCK", "1")
    sid = create_session(tmp_path)
    out = interpret_wizard_session(tmp_path, sid, {})
    assert out.get("ok") is True
    assert out.get("interpretation", {}).get("what_user_said")
    loaded = load_session(tmp_path, sid)
    assert loaded is not None
    interp = loaded.payload.get("interpretation")
    assert isinstance(interp, dict)
    assert interp.get("schema_version") == 1


def test_interpret_mock_disabled_requires_provider(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LENSES_INTERPRETATION_MOCK", raising=False)
    sid = create_session(tmp_path)
    out = interpret_wizard_session(tmp_path, sid, {})
    assert out.get("ok") is False
    assert out.get("error") == "invalid_provider"


def test_interpret_llm_path_monkeypatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LENSES_INTERPRETATION_MOCK", raising=False)
    sid = create_session(tmp_path)
    doc = load_session(tmp_path, sid)
    assert doc is not None
    merged = dict(doc.payload)
    merged["mission"] = {"mode": "define", "title": "T", "outcome": "O", "notes": ""}
    from lenses.blueprints_wizard.schemas import WizardSessionDocument

    save_ok, _ = __import__(
        "lenses.blueprints_wizard.session_store", fromlist=["save_session_replace"]
    ).save_session_replace(tmp_path, sid, doc.__class__(
        version=doc.version,
        updated_at=doc.updated_at,
        step_index=doc.step_index,
        payload=merged,
    ).to_dict())
    assert save_ok

    def fake_chat(provider: str, message: str, model_override, **kwargs):
        return {
            "ok": True,
            "text": '{"what_user_said":"u","inferred":[],"needs_confirmation":[],"unknowns":[],"foundation_brief_draft":{}}',
            "model": "m",
        }

    monkeypatch.setattr("lenses.llm_chat.chat", fake_chat)
    out = interpret_wizard_session(tmp_path, sid, {"provider": "openai"})
    assert out.get("ok") is True
    assert out.get("model") == "m"
    assert out.get("interpretation", {}).get("what_user_said") == "u"


def test_interpretation_mock_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LENSES_INTERPRETATION_MOCK", "true")
    assert interpretation_mock_enabled() is True
    monkeypatch.setenv("LENSES_INTERPRETATION_MOCK", "")
    assert interpretation_mock_enabled() is False
