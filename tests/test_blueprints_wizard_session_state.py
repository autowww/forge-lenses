"""Pure session state helpers (experimental Blueprints Wizard)."""

from __future__ import annotations

from lenses.blueprints_wizard.recheck_provider import NullRecheckProvider
from lenses.blueprints_wizard.schemas import WizardSessionDocument, normalize_wizard_payload
from lenses.blueprints_wizard.wizard_session_state import (
    append_assumption_entry,
    clone_document_for_put,
    get_run_plan,
    get_wizard_domain,
    is_draft,
    merge_wizard_domain,
    remove_assumption_by_id,
    set_payload_state_draft,
    set_step_index,
)


def test_get_wizard_domain_defaults() -> None:
    doc = WizardSessionDocument.new_empty()
    wd = get_wizard_domain(doc)
    assert wd["mission_type"] == "explore"


def test_set_step_index() -> None:
    doc = WizardSessionDocument.new_empty()
    d2 = set_step_index(doc, 3)
    assert d2.step_index == 3
    assert doc.step_index == 0


def test_merge_wizard_domain() -> None:
    doc = WizardSessionDocument.new_empty()
    d2 = merge_wizard_domain(doc, {"mission_type": "deliver", "target_stage": "charges"})
    wd = get_wizard_domain(d2)
    assert wd["mission_type"] == "deliver"
    assert wd["target_stage"] == "charges"


def test_append_assumption() -> None:
    doc = WizardSessionDocument.new_empty()
    d2 = append_assumption_entry(doc, {"text": "Users need SSO"})
    wd = get_wizard_domain(d2)
    assert len(wd["assumption_ledger"]) == 1
    assert wd["assumption_ledger"][0]["text"] == "Users need SSO"


def test_remove_assumption_by_id() -> None:
    doc = WizardSessionDocument.new_empty()
    d2 = append_assumption_entry(doc, {"id": "rm1", "text": "To remove"})
    eid = get_wizard_domain(d2)["assumption_ledger"][0]["id"]
    d3 = remove_assumption_by_id(d2, eid)
    assert get_wizard_domain(d3)["assumption_ledger"] == []


def test_get_run_plan() -> None:
    doc = merge_wizard_domain(
        WizardSessionDocument.new_empty(),
        {"run_plan": {"title": "Plan A", "steps": [{"title": "S1", "detail": "D"}]}},
    )
    rp = get_run_plan(doc)
    assert rp["title"] == "Plan A"
    assert len(rp["steps"]) == 1


def test_is_draft_and_set_draft() -> None:
    doc = WizardSessionDocument.new_empty()
    assert is_draft(doc) is True
    pl = dict(doc.payload)
    pl["state"] = "ready"
    doc2 = WizardSessionDocument(
        version=doc.version,
        updated_at=doc.updated_at,
        step_index=doc.step_index,
        payload=normalize_wizard_payload(pl),
    )
    assert is_draft(doc2) is False
    d3 = set_payload_state_draft(doc2)
    assert is_draft(d3) is True


def test_clone_document_for_put_roundtrip() -> None:
    doc = merge_wizard_domain(WizardSessionDocument.new_empty(), {"mission_type": "sunset"})
    body = clone_document_for_put(doc)
    again = WizardSessionDocument.from_dict(body)
    assert again is not None
    assert get_wizard_domain(again)["mission_type"] == "sunset"


def test_null_recheck_provider() -> None:
    p = NullRecheckProvider()
    s = p.summarize({})
    assert s.get("passed") is False
