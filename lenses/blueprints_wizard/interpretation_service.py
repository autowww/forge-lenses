"""Orchestrate interpretation: mock vs LLM, persist session."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lenses.blueprints_wizard.interpretation_normalize import normalize_interpretation_payload
from lenses.blueprints_wizard.interpreter_llm import run_interpret_llm
from lenses.blueprints_wizard.interpreter_mock import mock_interpretation_normalized
from lenses.blueprints_wizard.schemas import WizardSessionDocument
from lenses.blueprints_wizard.session_store import load_session, save_session_replace, validate_session_id


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def interpretation_mock_enabled() -> bool:
    raw = (os.environ.get("LENSES_INTERPRETATION_MOCK") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def interpret_wizard_session(
    workspace_root: Path,
    session_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    """
    Run interpretation and persist ``payload.interpretation``.

    Body: ``provider``, optional ``model``, optional ``refine`` (bool).
    """
    if not validate_session_id(session_id):
        return {"ok": False, "error": "invalid_session_id"}
    doc = load_session(workspace_root, session_id)
    if doc is None:
        return {"ok": False, "error": "not_found"}

    provider = str(body.get("provider", "")).strip().lower()
    model_raw = body.get("model")
    model_override: str | None
    if model_raw is None:
        model_override = None
    else:
        ms = str(model_raw).strip()
        model_override = ms if ms else None
    refine = bool(body.get("refine"))

    llm_extra: dict[str, Any] = {}

    if interpretation_mock_enabled():
        interpretation = mock_interpretation_normalized()
    else:
        if not provider:
            return {"ok": False, "error": "invalid_provider", "detail": "(empty)"}
        inner = run_interpret_llm(
            workspace_root=workspace_root,
            session_payload=doc.payload,
            provider=provider,
            model_override=model_override,
            refine=refine,
        )
        if not inner.get("ok"):
            return inner
        interpretation = inner.get("interpretation")
        if not isinstance(interpretation, dict):
            return {"ok": False, "error": "interpretation_invalid"}
        for k in ("model", "usage", "routing"):
            if k in inner:
                llm_extra[k] = inner[k]

    interpretation = normalize_interpretation_payload(interpretation)
    interpretation["updated_at"] = _utc_now_iso()

    merged_payload = dict(doc.payload)
    merged_payload["interpretation"] = interpretation

    merged = WizardSessionDocument(
        version=doc.version,
        updated_at=doc.updated_at,
        step_index=doc.step_index,
        payload=merged_payload,
    )
    ok_save, err_save = save_session_replace(workspace_root, session_id, merged.to_dict())
    if not ok_save:
        return {"ok": False, "error": err_save or "save_failed"}

    out: dict[str, Any] = {
        "ok": True,
        "interpretation": interpretation,
        "session": merged.to_dict(),
    }
    out.update(llm_extra)
    return out
