"""File-backed sessions for async multi-step Copilot (SSE progress)."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SessionEvent = dict[str, Any]


def _event_seq(ev: dict) -> int | None:
    raw = ev.get("seq")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sessions_dir(workspace_root: Path) -> Path:
    d = workspace_root.resolve() / ".lenses-local" / "copilot_async"
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d.parent.parent, 0o700)
        os.chmod(d.parent, 0o700)
        os.chmod(d, 0o700)
    except OSError:
        pass
    return d


def _session_path(workspace_root: Path, session_id: str) -> Path:
    safe = session_id.strip().replace(os.sep, "_").replace("/", "_")
    if not safe or ".." in safe or len(safe) > 80:
        raise ValueError("invalid_session_id")
    if not all(c in "0123456789abcdef" for c in safe.lower()):
        raise ValueError("invalid_session_id")
    return _sessions_dir(workspace_root) / f"{safe}.json"


def create_session(workspace_root: Path) -> str:
    sid = uuid.uuid4().hex
    ts = now_iso()
    doc: dict[str, Any] = {
        "id": sid,
        "status": "queued",
        "created_at": ts,
        "updated_at": ts,
        "events": [
            {
                "seq": 0,
                "ts": ts,
                "type": "queued",
                "payload": {"message": "Copilot session created"},
            },
        ],
    }
    save_session(workspace_root, doc)
    return sid


def load_session(workspace_root: Path, session_id: str) -> dict[str, Any] | None:
    try:
        p = _session_path(workspace_root, session_id)
    except ValueError:
        return None
    if not p.is_file():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def save_session(workspace_root: Path, doc: dict[str, Any]) -> None:
    sid = str(doc.get("id") or "").strip()
    if not sid:
        raise ValueError("session_id_required")
    doc["updated_at"] = now_iso()
    p = _session_path(workspace_root, sid)
    p.write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8")
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
        seq_i = _event_seq(ev)
        if seq_i is None:
            continue
        if seq_i > since_seq:
            out.append(ev)
    return out


def set_session_status(workspace_root: Path, session_id: str, status: str) -> None:
    sess = load_session(workspace_root, session_id)
    if not sess:
        return
    sess["status"] = status
    save_session(workspace_root, sess)


def session_status(workspace_root: Path, session_id: str) -> str | None:
    sess = load_session(workspace_root, session_id)
    if not sess:
        return None
    return str(sess.get("status") or "")


def write_copilot_chat_sse(
    handler: Any,
    workspace_root: Path,
    session_id: str,
    *,
    max_wait_sec: float = 120.0,
    poll_sec: float = 0.35,
) -> None:
    """Stream session events as SSE until final, error, done, or timeout."""
    import time

    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream; charset=utf-8")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "keep-alive")
    handler.send_header("X-Accel-Buffering", "no")
    handler.end_headers()
    last_seq = -1
    deadline = time.monotonic() + max_wait_sec
    try:
        while time.monotonic() < deadline:
            if load_session(workspace_root, session_id) is None:
                chunk = json.dumps({"ok": False, "error": "session_not_found"}, sort_keys=True)
                handler.wfile.write(f"data: {chunk}\n\n".encode("utf-8"))
                handler.wfile.flush()
                break
            evs = list_events_since(workspace_root, session_id, since_seq=last_seq)
            for ev in evs:
                s = _event_seq(ev)
                if s is not None:
                    last_seq = max(last_seq, s)
                chunk = json.dumps({"ok": True, "event": ev}, sort_keys=True)
                handler.wfile.write(f"data: {chunk}\n\n".encode("utf-8"))
                handler.wfile.flush()
                typ = str(ev.get("type") or "")
                if typ in ("final", "error"):
                    handler.wfile.write(b'data: {"ok":true,"done":true}\n\n')
                    handler.wfile.flush()
                    return
            st = session_status(workspace_root, session_id)
            if st in ("done", "error") and not evs:
                handler.wfile.write(b'data: {"ok":true,"done":true}\n\n')
                handler.wfile.flush()
                return
            time.sleep(poll_sec)
        chunk = json.dumps({"ok": False, "error": "stream_timeout"}, sort_keys=True)
        handler.wfile.write(f"data: {chunk}\n\n".encode("utf-8"))
        handler.wfile.write(b'data: {"ok":true,"done":true}\n\n')
        handler.wfile.flush()
    except (BrokenPipeError, ConnectionResetError, OSError):
        return
