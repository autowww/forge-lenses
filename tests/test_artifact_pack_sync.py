"""Tests for artifact pack sync from artifact_generation."""

from __future__ import annotations

from pathlib import Path

from lenses.blueprints_wizard.artifact_generation_inputs import canonical_inputs_fingerprint_payload
from lenses.blueprints_wizard.artifact_pack_sync import (
    apply_pack_sync_to_document,
    slice_key_for_pack_label,
    sync_artifact_pack_items_from_generation,
)
from lenses.blueprints_wizard.artifact_generation_normalize import (
    QUALITY_DIMENSIONS,
    normalize_artifact_generation,
    normalize_provenance,
)
from lenses.blueprints_wizard.wizard_domain_normalize import normalize_wizard_domain
from lenses.blueprints_wizard.mock_artifact_generation import mock_artifact_bundle_partial
from lenses.blueprints_wizard.schemas import WizardSessionDocument, normalize_wizard_payload
from lenses.blueprints_wizard.session_store import create_session, load_session, save_session_replace
from lenses.blueprints_wizard.wizard_domain_normalize import normalize_run_plan
from lenses.blueprints_wizard.wizard_session_state import get_wizard_domain


def test_slice_key_for_pack_label() -> None:
    assert slice_key_for_pack_label("Roadmap") == "roadmap"
    assert slice_key_for_pack_label("Foundation Brief (final)") == "foundation_brief_final"
    assert slice_key_for_pack_label("PRD") == "prd"
    assert slice_key_for_pack_label("WBE tree") == "wbe_tree"
    assert slice_key_for_pack_label("Ownership matrix") == "ownership_review_matrix"
    assert slice_key_for_pack_label("Sparks plan") == "sparks_plan"
    assert slice_key_for_pack_label("Rollout notes") == "rollout_notes"


def test_sync_sets_ready_when_approved(tmp_path: Path) -> None:
    sid = create_session(tmp_path)
    doc = load_session(tmp_path, sid)
    assert doc is not None
    pl = dict(doc.payload)
    wd = dict(pl.get("wizard_domain") or {})
    wd["foundation_brief"] = {"markdown": "x", "field_statuses": {}}
    wd["run_plan"] = normalize_run_plan({"title": "P", "steps": [{"id": "1", "title": "S", "detail": ""}]})
    arts = mock_artifact_bundle_partial(None)
    for k, rec in list(arts.items()):
        if isinstance(rec, dict):
            rec = dict(rec)
            rec["review_status"] = "approved"
            arts[k] = rec
    wd["artifact_generation"] = {"schema_version": 1, "artifacts": arts}
    wd["artifact_packs"] = [
        {
            "id": "pack1",
            "label": "Pack",
            "items": [
                {"id": "a", "label": "Roadmap", "status": "draft"},
                {"id": "b", "label": "Other line", "status": "ready"},
            ],
        }
    ]
    pl["wizard_domain"] = wd
    pl["foundation_brief"] = "x"
    pl = normalize_wizard_payload(pl)
    fp = canonical_inputs_fingerprint_payload(pl, include_execution_scope=True)
    wd_n = dict(pl["wizard_domain"])
    ag = normalize_artifact_generation(wd_n.get("artifact_generation"))
    arts_n = dict(ag.get("artifacts") or {})
    for k, rec in arts_n.items():
        rec = dict(rec)
        prov = dict(rec.get("provenance") or {})
        prov["input_fingerprint"] = fp
        rec["provenance"] = normalize_provenance(prov)
        arts_n[k] = rec
    ag["artifacts"] = arts_n
    wd_n["artifact_generation"] = ag
    pl["wizard_domain"] = normalize_wizard_domain(wd_n)
    doc2 = WizardSessionDocument.from_dict({**doc.to_dict(), "payload": pl})
    assert doc2 is not None
    save_session_replace(tmp_path, sid, doc2.to_dict())

    doc3 = load_session(tmp_path, sid)
    assert doc3 is not None
    synced = sync_artifact_pack_items_from_generation(
        dict(doc3.payload.get("wizard_domain") or {}),
        doc3.payload,
    )
    items = synced["artifact_packs"][0]["items"]
    by_label = {str(x["label"]): x["status"] for x in items}
    assert by_label["Roadmap"] == "ready"
    # Unmapped labels keep existing pack status (not forced to draft).
    assert by_label["Other line"] == "ready"


def test_apply_pack_sync_to_document_roundtrip(tmp_path: Path) -> None:
    sid = create_session(tmp_path)
    doc = load_session(tmp_path, sid)
    assert doc is not None
    pl = dict(doc.payload)
    wd = dict(pl.get("wizard_domain") or {})
    wd["foundation_brief"] = {"markdown": "brief", "field_statuses": {}}
    wd["run_plan"] = normalize_run_plan({"title": "P", "steps": [{"id": "1", "title": "S", "detail": ""}]})
    q = {d: {"score": 0.8, "rationale": ""} for d in QUALITY_DIMENSIONS}
    wd["artifact_generation"] = {
        "schema_version": 1,
        "artifacts": {
            "roadmap": {
                "content": {"summary": "s", "themes": [], "horizons": [], "trace_refs": []},
                "quality": q,
                "review_status": "pending",
                "locked": False,
                "feedback": "",
                "provenance": {"generation_id": "g", "created_at": "", "input_fingerprint": ""},
            }
        },
    }
    wd["artifact_packs"] = [
        {
            "id": "p",
            "label": "L",
            "items": [{"id": "i0", "label": "Roadmap", "status": "missing"}],
        }
    ]
    pl["wizard_domain"] = wd
    pl["foundation_brief"] = "brief"
    doc2 = WizardSessionDocument.from_dict({**doc.to_dict(), "payload": normalize_wizard_payload(pl)})
    assert doc2 is not None
    d3 = apply_pack_sync_to_document(doc2)
    st = get_wizard_domain(d3)["artifact_packs"][0]["items"][0]["status"]
    assert st == "draft"
