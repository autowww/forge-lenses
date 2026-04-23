"""Scope readiness for execution artifact generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.blueprints_wizard.artifact_generation_execution_readiness import (
    scope_fingerprint_payload,
    validate_scope_complete_for_execution,
)
from lenses.blueprints_wizard.artifact_generation_inputs import canonical_inputs_fingerprint_payload
from lenses.blueprints_wizard.schemas import WizardSessionDocument, normalize_wizard_payload
from lenses.blueprints_wizard.session_store import create_session, load_session
from lenses.blueprints_wizard.wizard_domain_normalize import normalize_run_plan, normalize_wizard_domain


def _doc_with_scope(tmp_path: Path, *, milestone_ref: str = "") -> WizardSessionDocument:
    sid = create_session(tmp_path)
    doc = load_session(tmp_path, sid)
    assert doc is not None
    pl = dict(doc.payload)
    wd = dict(pl.get("wizard_domain") or {})
    wd["foundation_brief"] = {"markdown": "# B\n", "field_statuses": {}}
    wd["run_plan"] = normalize_run_plan(
        {"title": "Plan", "steps": [{"id": "s1", "title": "Step one", "detail": "d"}]}
    )
    spec = dict(wd.get("scope_spec") or {})
    spec["scope_boundary"] = "milestone"
    spec["milestone_ref"] = milestone_ref
    wd["scope_spec"] = spec
    pl["wizard_domain"] = normalize_wizard_domain(wd)
    pl["foundation_brief"] = "# B\n"
    return WizardSessionDocument.from_dict({**doc.to_dict(), "payload": normalize_wizard_payload(pl)})  # type: ignore[arg-type]


def test_validate_scope_milestone_requires_ref(tmp_path: Path) -> None:
    doc = _doc_with_scope(tmp_path, milestone_ref="")
    ok, err, det = validate_scope_complete_for_execution(doc)
    assert ok is False
    assert err == "scope_incomplete"
    assert "milestone_ref" in (det or "")


def test_validate_scope_milestone_ok(tmp_path: Path) -> None:
    doc = _doc_with_scope(tmp_path, milestone_ref="M1")
    ok, err, _ = validate_scope_complete_for_execution(doc)
    assert ok is True
    assert err is None


def test_fingerprint_includes_execution_scope_payload(tmp_path: Path) -> None:
    doc = _doc_with_scope(tmp_path, milestone_ref="M1")
    pl = doc.payload
    fp1 = canonical_inputs_fingerprint_payload(pl, include_execution_scope=True)
    wd = dict(pl.get("wizard_domain") or {})
    spec = dict(wd.get("scope_spec") or {})
    spec["summary"] = "changed"
    wd["scope_spec"] = spec
    pl2 = dict(pl)
    pl2["wizard_domain"] = normalize_wizard_domain(wd)
    fp2 = canonical_inputs_fingerprint_payload(pl2, include_execution_scope=True)
    assert fp1 != fp2


def test_scope_fingerprint_payload_stable_keys() -> None:
    blob = scope_fingerprint_payload({"wizard_domain": {"scope_spec": {}}, "scope": {}})
    assert "scope_spec" in blob
    assert "payload_scope" in blob
