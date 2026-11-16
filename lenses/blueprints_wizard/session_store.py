"""Persist Blueprints Wizard sessions under ``<workspace_root>/.lenses-local/``."""

from __future__ import annotations

import json
import os
import re
import secrets
from pathlib import Path
from typing import Any

from lenses.blueprints_wizard.schemas import CURRENT_VERSION, WizardSessionDocument, _utc_now_iso

_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")

_DIR = "blueprints-wizard"
_SUB = "sessions"


def sessions_dir(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local" / _DIR / _SUB


def validate_session_id(session_id: str) -> bool:
    s = (session_id or "").strip()
    return bool(s and _SESSION_ID_RE.fullmatch(s))


def session_file(workspace_root: Path, session_id: str) -> Path:
    return sessions_dir(workspace_root) / f"{session_id}.json"


def list_session_summaries(workspace_root: Path) -> list[dict[str, Any]]:
    """Return session list metadata for hub UI (newest mtime first)."""
    d = sessions_dir(workspace_root)
    if not d.is_dir():
        return []
    rows: list[tuple[float, dict[str, Any]]] = []
    for p in d.glob("*.json"):
        sid = p.stem
        if not validate_session_id(sid):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        doc = WizardSessionDocument.from_dict(data)
        if doc is None:
            continue
        try:
            mtime = p.stat().st_mtime
        except OSError:
            mtime = 0.0
        pl = doc.payload
        rows.append(
            (
                mtime,
                {
                    "session_id": sid,
                    "updated_at": doc.updated_at,
                    "step_index": doc.step_index,
                    "title": pl.get("title", ""),
                    "purpose": pl.get("purpose", ""),
                    "state": pl.get("state", "draft"),
                    "mode": pl.get("mode", "existing_workspace"),
                },
            )
        )
    rows.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in rows]


def create_session(workspace_root: Path) -> str:
    """Create a new session file; return session id."""
    sid = secrets.token_urlsafe(16)
    doc = WizardSessionDocument.new_empty()
    _write_document(workspace_root, sid, doc)
    return sid


def load_session(workspace_root: Path, session_id: str) -> WizardSessionDocument | None:
    if not validate_session_id(session_id):
        return None
    p = session_file(workspace_root, session_id)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return WizardSessionDocument.from_dict(data)


def save_session_replace(
    workspace_root: Path,
    session_id: str,
    body: dict[str, Any],
) -> tuple[bool, str]:
    if not validate_session_id(session_id):
        return False, "invalid_session_id"
    parsed = WizardSessionDocument.from_dict(body)
    if parsed is None:
        return False, "invalid_session"
    p = session_file(workspace_root, session_id)
    if not p.is_file():
        return False, "not_found"
    doc = WizardSessionDocument(
        version=CURRENT_VERSION,
        updated_at=_utc_now_iso(),
        step_index=parsed.step_index,
        payload=parsed.payload,
    )
    _write_document(workspace_root, session_id, doc)
    return True, ""


def _write_document(workspace_root: Path, session_id: str, doc: WizardSessionDocument) -> None:
    p = session_file(workspace_root, session_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p.parent, 0o700)
    except OSError:
        pass
    try:
        os.chmod(p.parent.parent, 0o700)
    except OSError:
        pass
    tmp = p.with_suffix(".tmp")
    out = json.dumps(doc.to_dict(), indent=2, sort_keys=True)
    tmp.write_text(out + "\n", encoding="utf-8")
    tmp.replace(p)
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
