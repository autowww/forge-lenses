"""Pure selectors and immutable actions on ``WizardSessionDocument`` (experimental)."""

from __future__ import annotations

import copy
from typing import Any

from lenses.blueprints_wizard.schemas import (
    CURRENT_VERSION,
    WizardSessionDocument,
    normalize_wizard_payload,
)
from lenses.blueprints_wizard.wizard_domain_normalize import (
    normalize_assumption_ledger_entry,
    normalize_run_plan,
    normalize_wizard_domain,
)


def _utc_now_iso() -> str:
    from lenses.blueprints_wizard.schemas import _utc_now_iso as _u

    return _u()


def get_wizard_domain(doc: WizardSessionDocument) -> dict[str, Any]:
    return normalize_wizard_domain(doc.payload.get("wizard_domain"))


def get_run_plan(doc: WizardSessionDocument) -> dict[str, Any]:
    return normalize_run_plan(get_wizard_domain(doc).get("run_plan"))


def get_prompt_snapshot(doc: WizardSessionDocument) -> dict[str, Any] | None:
    wd = get_wizard_domain(doc)
    ps = wd.get("prompt_snapshot")
    if ps is None:
        return None
    from lenses.blueprints_wizard.wizard_domain_normalize import normalize_prompt_snapshot

    return normalize_prompt_snapshot(ps)


def is_draft(doc: WizardSessionDocument) -> bool:
    st = doc.payload.get("state")
    return str(st or "").strip().lower() == "draft"


def set_step_index(doc: WizardSessionDocument, step_index: int) -> WizardSessionDocument:
    pl = copy.deepcopy(doc.payload)
    return WizardSessionDocument(
        version=CURRENT_VERSION,
        updated_at=_utc_now_iso(),
        step_index=int(step_index),
        payload=normalize_wizard_payload(pl),
    )


def merge_wizard_domain(doc: WizardSessionDocument, partial: dict[str, Any]) -> WizardSessionDocument:
    pl = copy.deepcopy(doc.payload)
    cur = pl.get("wizard_domain")
    if not isinstance(cur, dict):
        cur = {}
    merged = {**cur, **partial}
    pl["wizard_domain"] = normalize_wizard_domain(merged)
    return WizardSessionDocument(
        version=CURRENT_VERSION,
        updated_at=_utc_now_iso(),
        step_index=doc.step_index,
        payload=normalize_wizard_payload(pl),
    )


def remove_assumption_by_id(doc: WizardSessionDocument, entry_id: str) -> WizardSessionDocument:
    """Drop ledger rows whose ``id`` matches ``entry_id`` (after normalize)."""
    pl = copy.deepcopy(doc.payload)
    wd = pl.get("wizard_domain")
    if not isinstance(wd, dict):
        wd = {}
    ledger = wd.get("assumption_ledger")
    if not isinstance(ledger, list):
        ledger = []
    eid = str(entry_id).strip()
    filtered = [x for x in ledger if not (isinstance(x, dict) and str(x.get("id", "")).strip() == eid)]
    wd = {**wd, "assumption_ledger": filtered}
    pl["wizard_domain"] = normalize_wizard_domain(wd)
    return WizardSessionDocument(
        version=CURRENT_VERSION,
        updated_at=_utc_now_iso(),
        step_index=doc.step_index,
        payload=normalize_wizard_payload(pl),
    )


def append_assumption_entry(doc: WizardSessionDocument, entry: dict[str, Any]) -> WizardSessionDocument:
    pl = copy.deepcopy(doc.payload)
    wd = pl.get("wizard_domain")
    if not isinstance(wd, dict):
        wd = {}
    ledger = wd.get("assumption_ledger")
    if not isinstance(ledger, list):
        ledger = []
    n = normalize_assumption_ledger_entry(entry)
    if n is not None:
        ledger = list(ledger) + [n]
    wd = {**wd, "assumption_ledger": ledger}
    pl["wizard_domain"] = normalize_wizard_domain(wd)
    return WizardSessionDocument(
        version=CURRENT_VERSION,
        updated_at=_utc_now_iso(),
        step_index=doc.step_index,
        payload=normalize_wizard_payload(pl),
    )


def set_payload_state_draft(doc: WizardSessionDocument) -> WizardSessionDocument:
    pl = copy.deepcopy(doc.payload)
    pl["state"] = "draft"
    return WizardSessionDocument(
        version=CURRENT_VERSION,
        updated_at=_utc_now_iso(),
        step_index=doc.step_index,
        payload=normalize_wizard_payload(pl),
    )


def clone_document_for_put(doc: WizardSessionDocument) -> dict[str, Any]:
    """Fresh document dict suitable for ``save_session_replace`` (version + timestamp from server store)."""
    return WizardSessionDocument(
        version=CURRENT_VERSION,
        updated_at=_utc_now_iso(),
        step_index=doc.step_index,
        payload=normalize_wizard_payload(copy.deepcopy(doc.payload)),
    ).to_dict()
