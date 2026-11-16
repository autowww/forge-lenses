"""HTTP entrypoints for agent runtime (GET/POST/SSE)."""

from __future__ import annotations

import json
import time
import urllib.parse
from pathlib import Path
from typing import Any, Callable

from lenses.agent_runtime.capabilities import (
    build_provider_endpoints,
    build_routing_policy_summary,
    default_model_slots,
)
from lenses.agent_runtime.endpoint_registry import build_endpoint_registry_payload
from lenses.agent_runtime.feature_flag import agent_runtime_enabled
from lenses.agent_runtime.ledger import read_ledger_tail, summarize_ledger
from lenses.agent_runtime import sessions as sess

SendJson = Callable[[int, dict[str, Any]], None]


def _parse_subpath(path: str, prefix: str) -> str | None:
    if not path.startswith(prefix):
        return None
    rest = path[len(prefix) :].strip("/")
    return rest or None


def parse_stream_session_id(path: str) -> str | None:
    """``/api/agent-runtime/sessions/<id>/stream`` → session id."""
    suf = "/api/agent-runtime/sessions/"
    if not path.startswith(suf) or not path.endswith("/stream"):
        return None
    mid = path[len(suf) : -len("/stream")].strip("/")
    return mid or None


def handle_agent_runtime_get(
    workspace_root: Path,
    path: str,
    parsed: urllib.parse.ParseResult,
    *,
    send_json: SendJson,
) -> bool:
    """Return True if handled."""
    if not agent_runtime_enabled():
        return False
    base = "/api/agent-runtime"
    if not path.startswith(base):
        return False

    qs = urllib.parse.parse_qs(parsed.query or "")

    if path == f"{base}/overview":
        reg = build_endpoint_registry_payload(workspace_root)
        tail = read_ledger_tail(workspace_root, max_lines=5)
        send_json(
            200,
            {
                "ok": True,
                **reg,
                "last_ledger_records": tail,
            },
        )
        return True

    if path == f"{base}/providers":
        send_json(200, {"ok": True, "providers": build_provider_endpoints(workspace_root)})
        return True

    if path == f"{base}/slots":
        send_json(200, {"ok": True, "slots": default_model_slots()})
        return True

    if path == f"{base}/policy":
        send_json(200, {"ok": True, **build_routing_policy_summary(workspace_root)})
        return True

    if path == f"{base}/token-usage":
        session_id = str(qs.get("session_id", [""])[0] or "").strip() or None
        project_slug = str(qs.get("project", [""])[0] or "").strip() or None
        scan_run_id = str(qs.get("scan_run_id", [""])[0] or "").strip() or None
        send_json(200, summarize_ledger(workspace_root, session_id=session_id, project_slug=project_slug, scan_run_id=scan_run_id))
        return True

    if path == f"{base}/sessions/recent":
        send_json(200, {"ok": True, "session_ids": sess.list_recent_session_ids(workspace_root)})
        return True

    sub = _parse_subpath(path, f"{base}/sessions/")
    if sub and "/events" in sub:
        parts = sub.split("/")
        if len(parts) >= 2 and parts[1] == "events":
            sid = parts[0]
            since_raw = str(qs.get("since_seq", ["-1"])[0] or "-1")
            try:
                since_seq = int(since_raw)
            except ValueError:
                since_seq = -1
            evs = sess.list_events_since(workspace_root, sid, since_seq=since_seq)
            send_json(200, {"ok": True, "session_id": sid, "events": evs})
            return True

    if sub and "/" not in sub.strip("/"):
        sid = sub.strip("/")
        if sid and sid not in ("recent",):
            row = sess.load_session(workspace_root, sid)
            if not row:
                send_json(404, {"ok": False, "error": "session_not_found"})
            else:
                send_json(200, {"ok": True, "session": row})
            return True

    return False


def handle_agent_runtime_post(
    workspace_root: Path,
    path: str,
    body: dict[str, Any],
    *,
    send_json: SendJson,
) -> bool:
    if not agent_runtime_enabled():
        return False
    base = "/api/agent-runtime"

    if path == f"{base}/sessions":
        kind = str(body.get("kind") or "generic").strip()
        project_slug = str(body.get("project_slug") or "").strip() or None
        scan_run_id = str(body.get("scan_run_id") or "").strip() or None
        cluster_id = str(body.get("cluster_id") or "").strip() or None
        docs_health_run_id = str(body.get("docs_health_run_id") or "").strip() or None
        agent = body.get("agent") if isinstance(body.get("agent"), dict) else None
        created = sess.create_session(
            workspace_root,
            kind=kind,
            project_slug=project_slug,
            scan_run_id=scan_run_id,
            cluster_id=cluster_id,
            docs_health_run_id=docs_health_run_id,
            agent=agent,  # type: ignore[arg-type]
            metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else None,
        )
        send_json(200, {"ok": True, "session": created})
        return True

    sub = _parse_subpath(path, f"{base}/sessions/")
    if sub and sub.endswith("/events"):
        sid = sub[: -len("/events")]
        typ = str(body.get("type") or "").strip()
        payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}
        if not typ:
            send_json(400, {"ok": False, "error": "missing_type"})
            return True
        ev = sess.append_event(workspace_root, sid, typ, payload)
        if not ev:
            send_json(404, {"ok": False, "error": "session_not_found"})
        else:
            send_json(200, {"ok": True, "event": ev})
        return True

    return False


def write_session_sse(handler: Any, workspace_root: Path, session_id: str) -> None:
    """SSE: poll session file for new events (MVP). ``handler`` is BaseHTTPRequestHandler."""
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream; charset=utf-8")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "keep-alive")
    handler.send_header("X-Accel-Buffering", "no")
    handler.end_headers()
    last_seq = -1
    for _ in range(120):
        evs = sess.list_events_since(workspace_root, session_id, since_seq=last_seq)
        for ev in evs:
            last_seq = max(last_seq, int(ev.get("seq") or -1))
            chunk = json.dumps({"ok": True, "event": ev}, sort_keys=True)
            handler.wfile.write(f"data: {chunk}\n\n".encode("utf-8"))
            handler.wfile.flush()
        time.sleep(0.5)
    handler.wfile.write(b"data: {\"ok\":true,\"done\":true}\n\n")
    handler.wfile.flush()
