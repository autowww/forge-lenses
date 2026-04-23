"""Run artifact generation recheck and persist ``recheck_summary`` + pack sync."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.blueprints_wizard.artifact_generation_recheck import ArtifactGenerationRecheckStub
from lenses.blueprints_wizard.artifact_pack_sync import apply_pack_sync_to_document
from lenses.blueprints_wizard.session_store import load_session, save_session_replace, validate_session_id
from lenses.blueprints_wizard.wizard_session_state import merge_wizard_domain


def _coerce_dry_run(raw: Any) -> bool:
    if raw is True:
        return True
    if raw is False or raw is None:
        return False
    if isinstance(raw, (int, float)) and raw == 1:
        return True
    if isinstance(raw, str):
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return False


def run_artifact_recheck(workspace_root: Path, session_id: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compute recheck summary; merge into session, sync artifact pack rows, and save unless ``dry_run``."""
    if not validate_session_id(session_id):
        return {"ok": False, "error": "invalid_session_id"}
    doc = load_session(workspace_root, session_id)
    if doc is None:
        return {"ok": False, "error": "not_found"}

    dry_run = _coerce_dry_run((body or {}).get("dry_run"))

    summary = ArtifactGenerationRecheckStub().summarize(doc.payload)
    if dry_run:
        return {
            "ok": True,
            "recheck_summary": summary,
            "dry_run": True,
        }

    doc2 = merge_wizard_domain(doc, {"recheck_summary": summary})
    doc3 = apply_pack_sync_to_document(doc2)

    ok_save, err_save = save_session_replace(workspace_root, session_id, doc3.to_dict())
    if not ok_save:
        return {"ok": False, "error": err_save or "save_failed"}

    return {
        "ok": True,
        "recheck_summary": summary,
        "dry_run": False,
        "session": doc3.to_dict(),
    }
