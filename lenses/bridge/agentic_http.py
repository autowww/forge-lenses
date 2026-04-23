"""HTTP handlers for Sprint B3 agentic bridge API."""

from __future__ import annotations

import urllib.parse
from typing import Any, Callable

from lenses.bridge.agentic_b3_feature_flag import experimental_agentic_bridge_b3_enabled
from lenses.bridge.agentic_bridge_registry import load_agentic_bridge_registry
from lenses.bridge.agentic_service import (
    approve_agent_run,
    create_agent_run,
    create_launch_pack,
    drift_payload,
    get_entity_bundle,
    link_agent_output_to_artifact,
    list_agent_runs,
    list_pending_approvals,
    manifests_payload,
    policies_payload,
    recipes_payload,
    tasklets_payload,
    versonas_payload,
)
from lenses.orchestration_graph.db import connect

SendJson = Callable[[int, dict[str, Any]], None]


def _disabled() -> dict[str, Any]:
    return {"ok": False, "feature_disabled": True}


def handle_agentic_b3_get(
    *,
    workspace_root,
    path: str,
    parsed: urllib.parse.ParseResult,
    send_json: SendJson,
) -> bool:
    p = path.rstrip("/") or "/"
    if not p.startswith("/api/agents"):
        return False

    if p == "/api/agents/enabled":
        reg = load_agentic_bridge_registry()
        send_json(
            200,
            {
                "ok": True,
                "enabled": experimental_agentic_bridge_b3_enabled(),
                "registry_version": reg.get("registry_version"),
            },
        )
        return True

    if not experimental_agentic_bridge_b3_enabled():
        send_json(200, _disabled())
        return True

    conn = connect(workspace_root)
    if conn is None:
        send_json(503, {"ok": False, "error": "graph_unavailable"})
        return True

    try:
        if p == "/api/agents/versonas":
            send_json(200, versonas_payload(workspace_root, conn))
            return True
        if p == "/api/agents/recipes":
            send_json(200, recipes_payload(workspace_root, conn))
            return True
        if p == "/api/agents/tasklets":
            send_json(200, tasklets_payload(conn))
            return True
        if p == "/api/agents/drift":
            send_json(200, drift_payload(workspace_root))
            return True
        if p == "/api/agents/policies":
            send_json(200, policies_payload(conn))
            return True
        if p == "/api/agents/manifests":
            send_json(200, manifests_payload(workspace_root, conn))
            return True
        if p == "/api/agents/runs":
            send_json(200, list_agent_runs(conn))
            return True
        if p == "/api/agents/approvals":
            send_json(200, list_pending_approvals(conn))
            return True

        if p.startswith("/api/agents/runs/") and not p.endswith("/approve"):
            rid = urllib.parse.unquote(p[len("/api/agents/runs/") :].strip("/"))
            if not rid:
                send_json(404, {"ok": False, "error": "not_found"})
                return True
            bundle = get_entity_bundle(conn, rid)
            send_json(200 if bundle.get("ok") else 404, bundle)
            return True

        if p.startswith("/api/agents/outputs/") and p.endswith("/link"):
            send_json(405, {"ok": False, "error": "use_post"})
            return True

    finally:
        conn.close()

    send_json(404, {"ok": False, "error": "not_found"})
    return True


def handle_agentic_b3_post(
    *,
    workspace_root,
    post_path: str,
    body: dict[str, Any],
    send_json: SendJson,
    client_ip: str,
    may_run_actions,
) -> bool:
    p = post_path.rstrip("/") or "/"
    if not (
        p == "/api/agents/launch-packs"
        or p == "/api/agents/runs"
        or (p.startswith("/api/agents/runs/") and p.endswith("/approve"))
        or (p.startswith("/api/agents/outputs/") and p.endswith("/link"))
    ):
        return False

    if not experimental_agentic_bridge_b3_enabled():
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
        if p == "/api/agents/launch-packs":
            r = create_launch_pack(conn, body)
            send_json(201 if r.get("ok") else 400, r)
            return True

        if p == "/api/agents/runs":
            r = create_agent_run(conn, body)
            send_json(201 if r.get("ok") else 400, r)
            return True

        if p.startswith("/api/agents/runs/") and p.endswith("/approve"):
            inner = p[len("/api/agents/runs/") : -len("/approve")].strip("/")
            rid = urllib.parse.unquote(inner)
            r = approve_agent_run(conn, rid, body)
            send_json(200 if r.get("ok") else 400, r)
            return True

        if p.startswith("/api/agents/outputs/") and p.endswith("/link"):
            inner = p[len("/api/agents/outputs/") : -len("/link")].strip("/")
            oid = urllib.parse.unquote(inner)
            aid = str(body.get("artifact_id") or body.get("to_id") or "").strip()
            if not oid or not aid:
                send_json(400, {"ok": False, "error": "output_id_and_artifact_id_required"})
                return True
            r = link_agent_output_to_artifact(conn, oid, aid)
            send_json(200 if r.get("ok") else 400, r)
            return True

        send_json(404, {"ok": False, "error": "not_found"})
        return True
    finally:
        conn.close()
