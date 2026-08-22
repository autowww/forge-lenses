"""Append-only audit log for copilot prompts and outcomes (local workspace only)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIT_FILENAME = "sdlc-copilot-audit.jsonl"
_MAX_LINE = 24_000


def audit_log_path(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local" / AUDIT_FILENAME


def new_audit_id() -> str:
    return str(uuid.uuid4())


def append_audit_event(workspace_root: Path, event: dict[str, Any]) -> None:
    p = audit_log_path(workspace_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
    if len(line) > _MAX_LINE:
        slim = {k: event[k] for k in ("id", "ts", "kind", "ok") if k in event}
        line = json.dumps(slim, ensure_ascii=False, sort_keys=True) + "\n"
    with p.open("a", encoding="utf-8") as f:
        f.write(line)
    try:
        p.chmod(0o600)
    except OSError:
        pass


def log_chat_turn(
    workspace_root: Path,
    *,
    audit_id: str,
    kind: str,
    tool_mode: str,
    route: str,
    project_slug: str | None,
    entity_id: str | None,
    login: str | None,
    provider: str,
    user_message_excerpt: str,
    citation_count: int,
    response_ok: bool,
    error: str | None,
    proposals_count: int,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    append_audit_event(
        workspace_root,
        {
            "id": audit_id,
            "ts": now,
            "kind": kind,
            "tool_mode": tool_mode,
            "route": (route or "").strip()[:120],
            "project_slug": (project_slug or "").strip()[:120] or None,
            "entity_id": (entity_id or "").strip()[:200] or None,
            "operator_login": (login or "").strip().lower()[:200] or None,
            "provider": (provider or "").strip()[:40],
            "prompt_excerpt": (user_message_excerpt or "")[:500],
            "citation_count": int(citation_count),
            "ok": bool(response_ok),
            "error": (error or "")[:500] or None,
            "proposals_count": int(proposals_count),
        },
    )


def log_commit(
    workspace_root: Path,
    *,
    audit_id: str,
    proposal_id: str,
    tool_id: str,
    login: str | None,
    project_slug: str | None,
    ok: bool,
    error: str | None,
    export_path: str | None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    append_audit_event(
        workspace_root,
        {
            "id": audit_id,
            "ts": now,
            "kind": "commit_proposal",
            "proposal_id": proposal_id,
            "tool_id": tool_id,
            "operator_login": (login or "").strip().lower()[:200] or None,
            "project_slug": (project_slug or "").strip()[:120] or None,
            "ok": bool(ok),
            "error": (error or "")[:500] or None,
            "export_relpath": export_path,
        },
    )
