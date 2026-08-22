"""Tests for Blueprints Wizard refine (LLM merge + persistence; llm_chat mocked)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from lenses.blueprints_wizard.api import parse_session_refine_path, post_refine_session
from lenses.blueprints_wizard.session_store import create_session, load_session


def test_parse_session_refine_path() -> None:
    sid = "a" * 12
    assert parse_session_refine_path(f"/api/blueprints/wizard/session/{sid}/refine") == sid
    assert parse_session_refine_path(f"/api/blueprints/wizard/session/{sid}/refine/") == sid
    assert parse_session_refine_path("/api/blueprints/wizard/session/") is None
    assert parse_session_refine_path(f"/api/blueprints/wizard/session/{sid}") is None
    assert parse_session_refine_path(f"/api/blueprints/wizard/session/{sid}/extra/refine") is None


def test_refine_persists_foundation_brief(tmp_path: Path) -> None:
    sid = create_session(tmp_path)
    doc = load_session(tmp_path, sid)
    assert doc is not None
    body = doc.to_dict()
    body["payload"] = {"stepNotes": {"0": "Ship SSO by Q3"}}
    from lenses.blueprints_wizard.session_store import save_session_replace

    ok, err = save_session_replace(tmp_path, sid, body)
    assert ok and err == ""

    def fake_chat(provider: str, message: str, model_override, **kwargs):
        assert "Ship SSO" in message
        assert provider == "ollama"
        return {"ok": True, "text": "# Brief\n\nDone.", "model": "m"}

    with patch("lenses.llm_chat.chat", side_effect=fake_chat):
        out = post_refine_session(tmp_path, sid, {"provider": "ollama"})

    assert out.get("ok") is True
    assert out.get("text") == "# Brief\n\nDone."
    assert out.get("session", {}).get("payload", {}).get("foundation_brief") == "# Brief\n\nDone."
    loaded = load_session(tmp_path, sid)
    assert loaded is not None
    assert loaded.payload.get("foundation_brief") == "# Brief\n\nDone."
    wd = loaded.payload.get("wizard_domain")
    assert isinstance(wd, dict)
    fb = wd.get("foundation_brief")
    assert isinstance(fb, dict)
    assert fb.get("markdown") == "# Brief\n\nDone."
    fs = fb.get("field_statuses")
    assert isinstance(fs, dict)
    assert fs.get("llm_foundation_brief") == "inferred"


def test_refine_with_mission_structured_only(tmp_path: Path) -> None:
    """Mission step fields alone supply prompt text (no stepNotes required)."""
    sid = create_session(tmp_path)
    doc = load_session(tmp_path, sid)
    assert doc is not None
    body = doc.to_dict()
    body["payload"] = {
        "mission": {"title": "Harden onboarding", "outcome": "Reduce time-to-first-commit.", "notes": ""},
        "stepNotes": {},
    }
    from lenses.blueprints_wizard.session_store import save_session_replace

    ok, err = save_session_replace(tmp_path, sid, body)
    assert ok and err == ""

    def fake_chat(provider: str, message: str, model_override, **kwargs):
        assert "Harden onboarding" in message
        assert "Reduce time" in message
        assert provider == "ollama"
        return {"ok": True, "text": "# Brief\n\nOK.", "model": "m"}

    with patch("lenses.llm_chat.chat", side_effect=fake_chat):
        out = post_refine_session(tmp_path, sid, {"provider": "ollama"})

    assert out.get("ok") is True
    assert out.get("session", {}).get("payload", {}).get("foundation_brief") == "# Brief\n\nOK."


def test_refine_with_contribution_setup_structured_only(tmp_path: Path) -> None:
    """Contribution Setup fields alone supply prompt text."""
    sid = create_session(tmp_path)
    doc = load_session(tmp_path, sid)
    assert doc is not None
    body = doc.to_dict()
    body["payload"] = {
        "contributionSetup": {
            "deliverable": "Handbook pages",
            "landingPlace": "github.com/org/docs",
            "notes": "",
        },
        "stepNotes": {},
    }
    from lenses.blueprints_wizard.session_store import save_session_replace

    ok, err = save_session_replace(tmp_path, sid, body)
    assert ok and err == ""

    def fake_chat(provider: str, message: str, model_override, **kwargs):
        assert "Handbook pages" in message
        assert "github.com/org/docs" in message
        assert provider == "ollama"
        return {"ok": True, "text": "# Brief\n\nCS.", "model": "m"}

    with patch("lenses.llm_chat.chat", side_effect=fake_chat):
        out = post_refine_session(tmp_path, sid, {"provider": "ollama"})

    assert out.get("ok") is True
    assert out.get("session", {}).get("payload", {}).get("foundation_brief") == "# Brief\n\nCS."


def test_refine_with_context_intake_structured_only(tmp_path: Path) -> None:
    """Context Intake fields alone supply prompt text."""
    sid = create_session(tmp_path)
    doc = load_session(tmp_path, sid)
    assert doc is not None
    body = doc.to_dict()
    body["payload"] = {
        "contextIntake": {
            "sources": "Confluence, Slack #proj",
            "summary": "We need SSO and audit logs.",
            "notes": "",
        },
        "stepNotes": {},
    }
    from lenses.blueprints_wizard.session_store import save_session_replace

    ok, err = save_session_replace(tmp_path, sid, body)
    assert ok and err == ""

    def fake_chat(provider: str, message: str, model_override, **kwargs):
        assert "Confluence" in message
        assert "audit logs" in message
        assert provider == "ollama"
        return {"ok": True, "text": "# Brief\n\nCI.", "model": "m"}

    with patch("lenses.llm_chat.chat", side_effect=fake_chat):
        out = post_refine_session(tmp_path, sid, {"provider": "ollama"})

    assert out.get("ok") is True
    assert out.get("session", {}).get("payload", {}).get("foundation_brief") == "# Brief\n\nCI."


def test_refine_missing_notes(tmp_path: Path) -> None:
    sid = create_session(tmp_path)
    with patch("lenses.llm_chat.chat") as m:
        out = post_refine_session(tmp_path, sid, {"provider": "ollama"})
    m.assert_not_called()
    assert out == {"ok": False, "error": "missing_notes", "detail": "Add notes on wizard steps before refining."}


def test_refine_llm_error_passthrough(tmp_path: Path) -> None:
    sid = create_session(tmp_path)
    doc = load_session(tmp_path, sid)
    assert doc is not None
    body = doc.to_dict()
    body["payload"] = {"stepNotes": {"0": "x"}}
    from lenses.blueprints_wizard.session_store import save_session_replace

    ok, err = save_session_replace(tmp_path, sid, body)
    assert ok and err == ""

    with patch(
        "lenses.llm_chat.chat",
        return_value={"ok": False, "error": "invalid_provider", "detail": "bad"},
    ):
        out = post_refine_session(tmp_path, sid, {"provider": "nope"})

    assert out.get("ok") is False
    assert out.get("error") == "invalid_provider"
    loaded = load_session(tmp_path, sid)
    assert loaded is not None
    assert "foundation_brief" not in loaded.payload


def test_notes_markdown_skips_step_note_when_understanding_structured() -> None:
    """Structured understanding replaces freeform step 3 note in refine prompt."""
    from lenses.blueprints_wizard.refine import _notes_markdown

    payload = {
        "understanding": {"summary": "Core summary", "knownGaps": "Gap A"},
        "stepNotes": {"3": "Should not duplicate structured fields"},
    }
    md = _notes_markdown(payload)
    assert "Core summary" in md
    assert "Gap A" in md
    assert "Should not duplicate" not in md
