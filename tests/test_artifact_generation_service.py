"""Tests for artifact generation service (mock LLM, no network)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.blueprints_wizard.artifact_generation_service import (
    apply_artifact_review,
    artifact_generation_mock_enabled,
    generate_artifacts,
)
from lenses.blueprints_wizard.schemas import WizardSessionDocument, normalize_wizard_payload
from lenses.blueprints_wizard.session_store import create_session, load_session
from lenses.blueprints_wizard.wizard_domain_normalize import normalize_run_plan, normalize_scope_spec


def _doc_with_prereqs(tmp_path: Path) -> tuple[str, WizardSessionDocument]:
    sid = create_session(tmp_path)
    doc = load_session(tmp_path, sid)
    assert doc is not None
    pl = dict(doc.payload)
    wd = dict(pl.get("wizard_domain") or {})
    wd["foundation_brief"] = {"markdown": "# Brief\n\nText.", "field_statuses": {}}
    wd["run_plan"] = normalize_run_plan(
        {"title": "Plan", "steps": [{"id": "s1", "title": "Step one", "detail": "d"}]}
    )
    pl["wizard_domain"] = wd
    pl["foundation_brief"] = "# Brief\n\nText."
    doc = WizardSessionDocument.from_dict(
        {**doc.to_dict(), "payload": normalize_wizard_payload(pl)}
    )
    assert doc is not None
    from lenses.blueprints_wizard.session_store import save_session_replace

    save_session_replace(tmp_path, sid, doc.to_dict())
    return sid, doc


def test_generate_mock_persists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LENSES_ARTIFACT_GENERATION_MOCK", "1")
    assert artifact_generation_mock_enabled() is True
    sid, _ = _doc_with_prereqs(tmp_path)
    out = generate_artifacts(
        tmp_path,
        sid,
        {"provider": "openai", "refine": False},
    )
    assert out.get("ok") is True
    assert out.get("session")
    doc2 = load_session(tmp_path, sid)
    assert doc2 is not None
    wd = doc2.payload.get("wizard_domain")
    assert isinstance(wd, dict)
    ag = wd.get("artifact_generation")
    assert isinstance(ag, dict)
    arts = ag.get("artifacts")
    assert isinstance(arts, dict)
    assert "foundation_brief_final" in arts


def test_generate_requires_prereqs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LENSES_ARTIFACT_GENERATION_MOCK", "1")
    sid = create_session(tmp_path)
    out = generate_artifacts(tmp_path, sid, {"provider": "openai"})
    assert out.get("ok") is False
    assert out.get("error") == "prerequisites_not_met"


def test_review_approve(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LENSES_ARTIFACT_GENERATION_MOCK", "1")
    sid, _ = _doc_with_prereqs(tmp_path)
    g = generate_artifacts(tmp_path, sid, {"provider": "openai"})
    assert g.get("ok") is True
    out = apply_artifact_review(
        tmp_path,
        sid,
        {"action": "approve", "artifact_key": "roadmap"},
    )
    assert out.get("ok") is True
    doc = load_session(tmp_path, sid)
    assert doc is not None
    arts = (doc.payload.get("wizard_domain") or {}).get("artifact_generation", {}).get("artifacts")
    assert arts["roadmap"]["review_status"] == "approved"


def test_review_lock_blocks_regen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LENSES_ARTIFACT_GENERATION_MOCK", "1")
    sid, _ = _doc_with_prereqs(tmp_path)
    generate_artifacts(tmp_path, sid, {"provider": "openai"})
    apply_artifact_review(tmp_path, sid, {"action": "lock", "artifact_key": "roadmap"})
    out = generate_artifacts(
        tmp_path,
        sid,
        {"provider": "openai", "artifact": "roadmap"},
    )
    assert out.get("ok") is False
    assert out.get("error") == "artifact_locked"


def test_review_unlock_then_regen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LENSES_ARTIFACT_GENERATION_MOCK", "1")
    sid, _ = _doc_with_prereqs(tmp_path)
    generate_artifacts(tmp_path, sid, {"provider": "openai"})
    apply_artifact_review(tmp_path, sid, {"action": "lock", "artifact_key": "roadmap"})
    assert (
        apply_artifact_review(tmp_path, sid, {"action": "approve", "artifact_key": "roadmap"}).get("ok")
        is False
    )
    un = apply_artifact_review(tmp_path, sid, {"action": "unlock", "artifact_key": "roadmap"})
    assert un.get("ok") is True
    out = generate_artifacts(
        tmp_path,
        sid,
        {"provider": "openai", "artifact": "roadmap"},
    )
    assert out.get("ok") is True


def test_review_unlock_requires_locked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LENSES_ARTIFACT_GENERATION_MOCK", "1")
    sid, _ = _doc_with_prereqs(tmp_path)
    generate_artifacts(tmp_path, sid, {"provider": "openai"})
    out = apply_artifact_review(tmp_path, sid, {"action": "unlock", "artifact_key": "roadmap"})
    assert out.get("ok") is False
    assert out.get("error") == "artifact_not_locked"


def test_generate_engineering_block_without_upstream(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LENSES_ARTIFACT_GENERATION_MOCK", "1")
    sid, _ = _doc_with_prereqs(tmp_path)
    out = generate_artifacts(
        tmp_path,
        sid,
        {"provider": "openai", "refine": False, "artifact_bundle": "engineering"},
    )
    assert out.get("ok") is False
    assert out.get("error") == "upstream_not_approved"


def test_lineage_and_fingerprint_on_mock_generate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LENSES_ARTIFACT_GENERATION_MOCK", "1")
    sid, _ = _doc_with_prereqs(tmp_path)
    out = generate_artifacts(
        tmp_path,
        sid,
        {"provider": "openai", "artifact_keys": ["foundation_brief_final", "roadmap"]},
    )
    assert out.get("ok") is True
    doc = load_session(tmp_path, sid)
    assert doc is not None
    arts = (doc.payload.get("wizard_domain") or {}).get("artifact_generation", {}).get("artifacts")
    prd = arts.get("prd")
    # not in this request
    assert prd is None
    fb = arts.get("foundation_brief_final")
    assert fb and "lineage" in fb["provenance"]
    assert isinstance(fb["provenance"]["lineage"].get("upstream"), list)


def test_approve_bundle_approves_multiple(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LENSES_ARTIFACT_GENERATION_MOCK", "1")
    sid, _ = _doc_with_prereqs(tmp_path)
    generate_artifacts(tmp_path, sid, {"provider": "openai"})
    out = apply_artifact_review(
        tmp_path,
        sid,
        {"action": "approve_bundle", "artifact_keys": ["roadmap", "assumptions_ledger"]},
    )
    assert out.get("ok") is True
    doc = load_session(tmp_path, sid)
    assert doc is not None
    arts = (doc.payload.get("wizard_domain") or {}).get("artifact_generation", {}).get("artifacts")
    assert arts["roadmap"]["review_status"] == "approved"
    assert arts["assumptions_ledger"]["review_status"] == "approved"


def test_generate_execution_scope_incomplete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LENSES_ARTIFACT_GENERATION_MOCK", "1")
    sid = create_session(tmp_path)
    doc = load_session(tmp_path, sid)
    assert doc is not None
    pl = dict(doc.payload)
    wd = dict(pl.get("wizard_domain") or {})
    wd["foundation_brief"] = {"markdown": "# B\n", "field_statuses": {}}
    wd["run_plan"] = normalize_run_plan(
        {"title": "Plan", "steps": [{"id": "s1", "title": "Step", "detail": "d"}]}
    )
    wd["scope_spec"] = normalize_scope_spec({"scope_boundary": "milestone", "milestone_ref": ""})
    pl["wizard_domain"] = wd
    pl["foundation_brief"] = "# B\n"
    doc2 = WizardSessionDocument.from_dict(
        {**doc.to_dict(), "payload": normalize_wizard_payload(pl)}
    )
    assert doc2 is not None
    from lenses.blueprints_wizard.session_store import save_session_replace

    save_session_replace(tmp_path, sid, doc2.to_dict())
    out = generate_artifacts(tmp_path, sid, {"provider": "openai", "artifact_bundle": "execution"})
    assert out.get("ok") is False
    assert out.get("error") == "scope_incomplete"
