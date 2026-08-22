"""Operator-approved export of a persisted proposal."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.access_policy import load_policy

from lenses.sdlc_copilot.audit import log_commit, new_audit_id
from lenses.sdlc_copilot.drafts import (
    delete_proposal_file,
    export_committed_proposal,
    load_proposal,
    proposal_is_fresh,
)
from lenses.sdlc_copilot.permissions import may_commit_proposal


def commit_stored_proposal(
    workspace_root: Path,
    proposal_id: str,
    *,
    login: str | None,
    confirm: bool,
) -> dict[str, Any]:
    if not confirm:
        return {"ok": False, "error": "confirm_required"}
    rec = load_proposal(workspace_root, proposal_id)
    if rec is None:
        return {"ok": False, "error": "proposal_not_found"}
    if not proposal_is_fresh(rec):
        return {"ok": False, "error": "proposal_expired"}

    policy = load_policy(workspace_root)
    slug = rec.get("project_slug")
    slug_s = str(slug).strip() if slug else None
    if not may_commit_proposal(policy, login, slug_s):
        return {"ok": False, "error": "copilot_commit_forbidden"}

    try:
        path = export_committed_proposal(workspace_root, rec)
    except OSError as ex:
        aid = new_audit_id()
        log_commit(
            workspace_root,
            audit_id=aid,
            proposal_id=proposal_id,
            tool_id=str(rec.get("tool_id") or ""),
            login=login,
            project_slug=slug_s,
            ok=False,
            error=str(ex),
            export_path=None,
        )
        return {"ok": False, "error": "export_failed", "detail": str(ex)}

    rel = str(path.relative_to(workspace_root.resolve()))
    delete_proposal_file(workspace_root, proposal_id)
    aid = new_audit_id()
    log_commit(
        workspace_root,
        audit_id=aid,
        proposal_id=proposal_id,
        tool_id=str(rec.get("tool_id") or ""),
        login=login,
        project_slug=slug_s,
        ok=True,
        error=None,
        export_path=rel,
    )
    try:
        from lenses.governance.audit_log import KIND_APPROVAL, append_event

        append_event(
            workspace_root,
            kind=KIND_APPROVAL,
            actor=login,
            resource="sdlc-copilot:commit-proposal",
            project_slug=slug_s,
            detail={
                "proposal_id": proposal_id,
                "tool_id": str(rec.get("tool_id") or ""),
                "export_path": rel,
            },
        )
    except OSError:
        pass
    return {"ok": True, "export_path": rel, "audit_id": aid}
