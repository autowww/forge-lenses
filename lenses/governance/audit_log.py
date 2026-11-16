"""Append-only governance audit log (data change, approval, AI, connector sync)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_FILENAME = "governance-audit.jsonl"
_MAX_LINE = 32_000

# event kinds
KIND_DATA_CHANGE = "data_change"
KIND_APPROVAL = "approval"
KIND_AI_ACTION = "ai_action"
KIND_CONNECTOR_SYNC = "connector_sync"


def audit_path(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local" / AUDIT_FILENAME


def append_event(
    workspace_root: Path,
    *,
    kind: str,
    actor: str | None,
    resource: str,
    detail: dict[str, Any] | None = None,
    project_slug: str | None = None,
) -> str:
    """Append one JSON line; returns event id."""
    eid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    row: dict[str, Any] = {
        "id": eid,
        "ts": now,
        "kind": kind,
        "actor": (actor or "").strip().lower()[:200] or None,
        "resource": (resource or "").strip()[:500],
        "project_slug": (project_slug or "").strip()[:200] or None,
        "detail": detail if isinstance(detail, dict) else {},
    }
    p = audit_path(workspace_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
    if len(line) > _MAX_LINE:
        row["detail"] = {"truncated": True}
        line = json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
    with p.open("a", encoding="utf-8") as f:
        f.write(line)
    try:
        p.chmod(0o600)
    except OSError:
        pass
    return eid


def read_recent(workspace_root: Path, *, limit: int = 100) -> list[dict[str, Any]]:
    p = audit_path(workspace_root)
    if not p.is_file():
        return []
    lim = max(1, min(limit, 500))
    lines: list[str] = []
    try:
        with p.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for raw in lines[-lim:]:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out
