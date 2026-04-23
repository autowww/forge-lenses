"""Persistent agent sessions and typed events."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lenses.agent_runtime.types import AgentDefinition, AgentSession, SessionEvent


def _sessions_dir(workspace_root: Path) -> Path:
    d = workspace_root.resolve() / ".lenses-local" / "agent-runtime" / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d.parent.parent, 0o700)
        os.chmod(d.parent, 0o700)
        os.chmod(d, 0o700)
    except OSError:
        pass
    return d


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def session_path(workspace_root: Path, session_id: str) -> Path:
    safe = session_id.strip().replace(os.sep, "_").replace("/", "_")
    if not safe or ".." in safe:
        raise ValueError("invalid_session_id")
    return _sessions_dir(workspace_root) / f"{safe}.json"


def create_session(
    workspace_root: Path,
    *,
    kind: str,
    project_slug: str | None = None,
    scan_run_id: str | None = None,
    cluster_id: str | None = None,
    docs_health_run_id: str | None = None,
    agent: AgentDefinition | None = None,
    metadata: dict[str, Any] | None = None,
) -> AgentSession:
    sid = uuid.uuid4().hex
    ag: AgentDefinition = agent or {"id": "generic", "version": 1, "label": "Agent"}
    ts = now_iso()
    sess: AgentSession = {
        "id": sid,
        "kind": kind,
        "project_slug": project_slug,
        "scan_run_id": scan_run_id,
        "cluster_id": cluster_id,
        "docs_health_run_id": docs_health_run_id,
        "agent": ag,
        "status": "live",
        "created_at": ts,
        "updated_at": ts,
        "events": [],
        "usage": {
            "calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated": False,
            "by_slot": {},
        },
    }
    if metadata:
        sess["metadata"] = metadata  # type: ignore[assignment]
    save_session(workspace_root, sess)
    append_event(
        workspace_root,
        sid,
        "session_created",
        {"kind": kind, "project_slug": project_slug, "agent": ag},
    )
    return load_session(workspace_root, sid) or sess


def load_session(workspace_root: Path, session_id: str) -> AgentSession | None:
    p = session_path(workspace_root, session_id)
    if not p.is_file():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def save_session(workspace_root: Path, sess: AgentSession) -> None:
    sid = str(sess.get("id") or "").strip()
    if not sid:
        raise ValueError("session_id_required")
    p = session_path(workspace_root, sid)
    sess["updated_at"] = now_iso()
    p.write_text(json.dumps(sess, indent=2, sort_keys=True), encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def append_event(workspace_root: Path, session_id: str, typ: str, payload: dict[str, Any]) -> SessionEvent | None:
    sess = load_session(workspace_root, session_id)
    if not sess:
        return None
    evs = sess.setdefault("events", [])
    seq = len(evs)
    ev: SessionEvent = {"seq": seq, "ts": now_iso(), "type": typ, "payload": dict(payload)}
    evs.append(ev)
    save_session(workspace_root, sess)
    return ev


def list_events_since(workspace_root: Path, session_id: str, *, since_seq: int = -1) -> list[SessionEvent]:
    sess = load_session(workspace_root, session_id)
    if not sess:
        return []
    out: list[SessionEvent] = []
    for ev in sess.get("events") or []:
        if not isinstance(ev, dict):
            continue
        if int(ev.get("seq") or -1) > since_seq:
            out.append(ev)  # type: ignore[arg-type]
    return out


def list_recent_session_ids(workspace_root: Path, *, limit: int = 20) -> list[str]:
    d = _sessions_dir(workspace_root)
    rows: list[tuple[float, str]] = []
    for p in d.glob("*.json"):
        try:
            rows.append((p.stat().st_mtime, p.stem))
        except OSError:
            continue
    rows.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in rows[:limit]]
