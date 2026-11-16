"""Tests for Blueprints Wizard session persistence (no HTTP server)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.blueprints_wizard.schemas import WizardSessionDocument
from lenses.blueprints_wizard.session_store import (
    create_session,
    load_session,
    save_session_replace,
    validate_session_id,
)


def test_create_load_round_trip(tmp_path: Path) -> None:
    sid = create_session(tmp_path)
    assert validate_session_id(sid)
    doc = load_session(tmp_path, sid)
    assert doc is not None
    assert doc.version == 2
    assert doc.step_index == 0
    assert doc.payload.get("state") == "draft"
    assert doc.payload.get("mode") == "existing_workspace"
    wd = doc.payload.get("wizard_domain")
    assert isinstance(wd, dict)
    assert wd.get("mission_type") == "explore"


def test_save_session_replace_preserves_wizard_domain(tmp_path: Path) -> None:
    sid = create_session(tmp_path)
    doc = load_session(tmp_path, sid)
    assert doc is not None
    body = doc.to_dict()
    body["payload"] = dict(body["payload"])
    body["payload"]["wizard_domain"] = {
        **(body["payload"].get("wizard_domain") or {}),
        "mission_type": "sunset",
        "assumption_ledger": [{"id": "x", "text": "test"}],
    }
    ok, err = save_session_replace(tmp_path, sid, body)
    assert ok and err == ""
    loaded = load_session(tmp_path, sid)
    assert loaded is not None
    wd = loaded.payload.get("wizard_domain")
    assert isinstance(wd, dict)
    assert wd.get("mission_type") == "sunset"
    assert len(wd.get("assumption_ledger", [])) == 1


def test_save_session_replace_updates(tmp_path: Path) -> None:
    sid = create_session(tmp_path)
    doc = load_session(tmp_path, sid)
    assert doc is not None
    body = doc.to_dict()
    body["step_index"] = 2
    body["payload"] = {"note": "hello"}
    ok, err = save_session_replace(tmp_path, sid, body)
    assert ok and err == ""
    loaded = load_session(tmp_path, sid)
    assert loaded is not None
    assert loaded.step_index == 2
    assert loaded.payload.get("note") == "hello"
    assert loaded.payload.get("state") == "draft"


def test_invalid_session_id_rejected() -> None:
    assert validate_session_id("") is False
    assert validate_session_id("../etc/passwd") is False
    assert validate_session_id("ab") is False  # too short
    assert validate_session_id("bad!") is False


def test_save_unknown_session(tmp_path: Path) -> None:
    ok, err = save_session_replace(
        tmp_path,
        "x" * 12,
        WizardSessionDocument.new_empty().to_dict(),
    )
    assert ok is False
    assert err == "not_found"


def test_save_invalid_body(tmp_path: Path) -> None:
    sid = create_session(tmp_path)
    ok, err = save_session_replace(tmp_path, sid, {"not": "a valid session"})
    assert ok is False
    assert err == "invalid_session"
