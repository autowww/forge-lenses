"""Tests for Markdown export of wizard artifacts."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.blueprints_wizard.api import post_artifact_export
from lenses.blueprints_wizard.artifact_generation_service import generate_artifacts
from lenses.blueprints_wizard.schemas import WizardSessionDocument, normalize_wizard_payload
from lenses.blueprints_wizard.session_store import create_session, load_session, save_session_replace
from lenses.blueprints_wizard.wizard_domain_normalize import normalize_run_plan


def _minimal_session(tmp_path: Path) -> str:
    sid = create_session(tmp_path)
    doc = load_session(tmp_path, sid)
    assert doc is not None
    pl = dict(doc.payload)
    wd = dict(pl.get("wizard_domain") or {})
    wd["foundation_brief"] = {"markdown": "x", "field_statuses": {}}
    wd["run_plan"] = normalize_run_plan(
        {"title": "P", "steps": [{"id": "1", "title": "S", "detail": ""}]}
    )
    wd["scope_spec"] = dict(wd.get("scope_spec") or {})
    wd["scope_spec"]["scope_boundary"] = "full_plan"
    pl["wizard_domain"] = wd
    pl["foundation_brief"] = "x"
    doc2 = WizardSessionDocument.from_dict({**doc.to_dict(), "payload": normalize_wizard_payload(pl)})
    assert doc2 is not None
    save_session_replace(tmp_path, sid, doc2.to_dict())
    return sid


def test_export_markdown_contains_heading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LENSES_ARTIFACT_GENERATION_MOCK", "1")
    sid = _minimal_session(tmp_path)
    g = generate_artifacts(tmp_path, sid, {"provider": "openai", "artifact": "roadmap"})
    assert g.get("ok") is True
    out = post_artifact_export(tmp_path, sid, {"artifact_keys": ["roadmap"]})
    assert out.get("ok") is True
    md = str(out.get("markdown") or "")
    assert "roadmap" in md.lower() or "Roadmap" in md or "mock" in md.lower()
