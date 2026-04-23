"""HTTP handlers for Sprint B5 handoff / execution-return API."""

from __future__ import annotations

import urllib.parse
from typing import Any, Callable

from lenses.bridge.handoff_b5_feature_flag import experimental_handoff_bridge_b5_enabled
from lenses.bridge.handoff_bridge_registry import load_handoff_bridge_registry
from lenses.bridge.handoff_service import (
    create_handoff_package,
    execution_session_bundle,
    export_handoff,
    get_handoff_bundle,
    handoff_gaps,
    handoff_status,
    ingest_return,
    list_handoff_packages,
    list_handoff_packages_for_work_item,
    reconcile_execution_session,
)
from lenses.orchestration_graph.db import connect

SendJson = Callable[[int, dict[str, Any]], None]


def _disabled() -> dict[str, Any]:
    return {"ok": False, "feature_disabled": True}


def handle_handoff_b5_get(
    *,
    workspace_root,
    path: str,
    parsed: urllib.parse.ParseResult,
    send_json: SendJson,
) -> bool:
    p = path.rstrip("/") or "/"
    if not (p.startswith("/api/handoffs") or p.startswith("/api/execution-sessions")):
        return False

    if p == "/api/handoffs/enabled":
        reg = load_handoff_bridge_registry()
        send_json(
            200,
            {
                "ok": True,
                "enabled": experimental_handoff_bridge_b5_enabled(),
                "registry_version": reg.get("registry_version"),
            },
        )
        return True

    if not experimental_handoff_bridge_b5_enabled():
        send_json(200, _disabled())
        return True

    conn = connect(workspace_root)
    if conn is None:
        send_json(503, {"ok": False, "error": "graph_unavailable"})
        return True

    try:
        if p == "/api/handoffs":
            send_json(200, list_handoff_packages(conn))
            return True

        if p.startswith("/api/handoffs/by-work-unit"):
            q = urllib.parse.parse_qs(parsed.query or "")
            wid = str(q.get("work_item_id", [""])[0] or "").strip()
            if not wid:
                send_json(400, {"ok": False, "error": "work_item_id_required"})
                return True
            ids = list_handoff_packages_for_work_item(conn, wid)
            send_json(200, {"ok": True, "work_item_id": wid, "package_ids": ids})
            return True

        if p.startswith("/api/handoffs/") and "/export" not in p and "/returns" not in p:
            inner = urllib.parse.unquote(p[len("/api/handoffs/") :].strip("/"))
            if not inner:
                send_json(404, {"ok": False, "error": "not_found"})
                return True
            if inner.endswith("/status"):
                pid = inner[: -len("/status")].strip("/").strip()
                send_json(200, handoff_status(conn, pid))
                return True
            if inner.endswith("/gaps"):
                pid = inner[: -len("/gaps")].strip("/").strip()
                send_json(200, handoff_gaps(conn, pid))
                return True
            if "/" in inner:
                send_json(404, {"ok": False, "error": "not_found"})
                return True
            send_json(200, get_handoff_bundle(conn, inner))
            return True

        if p.startswith("/api/execution-sessions/"):
            rest = urllib.parse.unquote(p[len("/api/execution-sessions/") :].strip("/"))
            if not rest or "/" in rest:
                send_json(404, {"ok": False, "error": "not_found"})
                return True
            send_json(200, execution_session_bundle(conn, rest))
            return True

    finally:
        conn.close()

    send_json(404, {"ok": False, "error": "not_found"})
    return True


def handle_handoff_b5_post(
    *,
    workspace_root,
    post_path: str,
    body: dict[str, Any],
    send_json: SendJson,
    client_ip: str,
    may_run_actions,
) -> bool:
    p = post_path.rstrip("/") or "/"
    if not (p.startswith("/api/handoffs") or p.startswith("/api/execution-sessions")):
        return False

    if not experimental_handoff_bridge_b5_enabled():
        send_json(404, _disabled())
        return True

    if not may_run_actions(client_ip):
        send_json(403, {"ok": False, "error": "allowed_from_loopback_or_lenses_allow_actions"})
        return True

    conn = connect(workspace_root)
    if conn is None:
        send_json(503, {"ok": False, "error": "graph_unavailable"})
        return True

    try:
        if p == "/api/handoffs":
            r = create_handoff_package(conn, body)
            send_json(201 if r.get("ok") else 400, r)
            return True

        if p.startswith("/api/handoffs/") and p.endswith("/export"):
            inner = p[len("/api/handoffs/") : -len("/export")].strip("/")
            pid = urllib.parse.unquote(inner)
            r = export_handoff(conn, pid, body)
            send_json(200 if r.get("ok") else 404, r)
            return True

        if p.startswith("/api/handoffs/") and p.endswith("/returns"):
            inner = p[len("/api/handoffs/") : -len("/returns")].strip("/")
            pid = urllib.parse.unquote(inner)
            r = ingest_return(conn, pid, body)
            send_json(200 if r.get("ok") else 400, r)
            return True

        if p.startswith("/api/execution-sessions/") and p.endswith("/reconcile"):
            inner = p[len("/api/execution-sessions/") : -len("/reconcile")].strip("/")
            sid = urllib.parse.unquote(inner)
            r = reconcile_execution_session(conn, sid, body)
            send_json(200 if r.get("ok") else 404, r)
            return True

        send_json(404, {"ok": False, "error": "not_found"})
        return True
    finally:
        conn.close()
