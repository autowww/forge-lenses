"""Persistence for Doc Management sessions under ``<workspace>/.lenses-local/doc-management/``."""

from __future__ import annotations

import json
import os
import re
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")

_LIVE_STATUSES = frozenset({"running", "awaiting_approval", "awaiting_input"})


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def store_root(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local" / "doc-management"


def sessions_root(workspace_root: Path) -> Path:
    d = store_root(workspace_root) / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(store_root(workspace_root), 0o700)
        os.chmod(d, 0o700)
    except OSError:
        pass
    return d


def validate_session_id(session_id: str) -> bool:
    s = (session_id or "").strip()
    return bool(s and _SESSION_ID_RE.fullmatch(s))


def session_dir(workspace_root: Path, session_id: str) -> Path:
    sid = (session_id or "").strip()
    if not validate_session_id(sid):
        raise ValueError("invalid_session_id")
    return sessions_root(workspace_root) / sid


def session_json_path(workspace_root: Path, session_id: str) -> Path:
    return session_dir(workspace_root, session_id) / "session.json"


def ensure_session_dirs(workspace_root: Path, session_id: str) -> Path:
    root = session_dir(workspace_root, session_id)
    for sub in ("intake", "pack", "promotion"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def new_forge_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y_%m_%d")
    tail = uuid.uuid4().hex[:8]
    return f"frun_{stamp}_doc_mgmt_{tail}"


def default_session(*, display_name: str = "Doc management session") -> dict[str, Any]:
    sid = secrets.token_urlsafe(16)
    ts = now_iso()
    return {
        "id": sid,
        "display_name": display_name,
        "status": "draft",
        "created_at": ts,
        "updated_at": ts,
        "forge_run_id": new_forge_run_id(),
        "wizard": {
            "step_index": 0,
            "intake_source": None,
            "persona": "architect",
            "target_surfaces": [],
            "use_llm": False,
            "source_url": None,
            "blog_slug": None,
        },
        "intake": {"seeds": []},
        "workflow": {"stage": "intake", "stages_completed": []},
        "events": [],
        "step_metrics": [],
        "promotion": {},
    }


def load_session(workspace_root: Path, session_id: str) -> dict[str, Any] | None:
    p = session_json_path(workspace_root, session_id)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def save_session(workspace_root: Path, session: dict[str, Any]) -> None:
    sid = str(session.get("id") or "").strip()
    if not validate_session_id(sid):
        raise ValueError("invalid_session_id")
    ensure_session_dirs(workspace_root, sid)
    session["updated_at"] = now_iso()
    p = session_json_path(workspace_root, sid)
    p.write_text(json.dumps(session, indent=2, sort_keys=True), encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def create_session(
    workspace_root: Path,
    *,
    display_name: str = "Doc management session",
    wizard: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sess = default_session(display_name=display_name)
    if wizard:
        w = sess["wizard"]
        if isinstance(w, dict):
            w.update({k: v for k, v in wizard.items() if v is not None})
    ensure_session_dirs(workspace_root, sess["id"])
    save_session(workspace_root, sess)
    return sess


def list_sessions(workspace_root: Path, *, limit: int = 50) -> list[dict[str, Any]]:
    root = sessions_root(workspace_root)
    if not root.is_dir():
        return []
    rows: list[tuple[float, dict[str, Any]]] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        sid = child.name
        if not validate_session_id(sid):
            continue
        sess = load_session(workspace_root, sid)
        if not sess:
            continue
        try:
            mtime = session_json_path(workspace_root, sid).stat().st_mtime
        except OSError:
            mtime = 0.0
        wizard = sess.get("wizard") if isinstance(sess.get("wizard"), dict) else {}
        rows.append(
            (
                mtime,
                {
                    "session_id": sid,
                    "display_name": sess.get("display_name") or "Doc management session",
                    "status": sess.get("status") or "draft",
                    "updated_at": sess.get("updated_at"),
                    "created_at": sess.get("created_at"),
                    "forge_run_id": sess.get("forge_run_id"),
                    "workflow_stage": (sess.get("workflow") or {}).get("stage"),
                    "intake_source": wizard.get("intake_source"),
                    "target_surfaces": wizard.get("target_surfaces") or [],
                },
            )
        )
    rows.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in rows[:limit]]


def append_event(session: dict[str, Any], event: dict[str, Any]) -> None:
    events = session.setdefault("events", [])
    if not isinstance(events, list):
        session["events"] = events = []
    row = dict(event)
    row.setdefault("ts", now_iso())
    events.append(row)


def cancel_session(workspace_root: Path, session_id: str) -> dict[str, Any] | None:
    sess = load_session(workspace_root, session_id)
    if not sess:
        return None
    sess["status"] = "cancelled"
    append_event(sess, {"type": "cancelled", "title": "Session cancelled"})
    save_session(workspace_root, sess)
    return sess


def intake_dir(workspace_root: Path, session_id: str) -> Path:
    return ensure_session_dirs(workspace_root, session_id) / "intake"


def pack_dir(workspace_root: Path, session_id: str) -> Path:
    return ensure_session_dirs(workspace_root, session_id) / "pack"


def promotion_dir(workspace_root: Path, session_id: str) -> Path:
    return ensure_session_dirs(workspace_root, session_id) / "promotion"
