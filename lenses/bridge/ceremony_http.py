"""HTTP handlers for Sprint B4 ceremony bridge API."""

from __future__ import annotations

import urllib.parse
from typing import Any, Callable

from lenses.bridge.ceremony_b4_feature_flag import experimental_ceremony_bridge_b4_enabled
from lenses.bridge.ceremony_bridge_registry import load_ceremony_bridge_registry
from lenses.bridge.ceremony_service import (
    add_ceremony_output,
    agenda_payload,
    ceremony_instance_bundle,
    create_ceremony_instance,
    intents_payload,
    list_ceremony_instances,
    mapping_inspector_row,
    mappings_payload,
    readiness_payload,
    signoff_ceremony,
    templates_payload,
)
from lenses.orchestration_graph.db import connect

SendJson = Callable[[int, dict[str, Any]], None]


def _disabled() -> dict[str, Any]:
    return {"ok": False, "feature_disabled": True}


def handle_ceremony_b4_get(
    *,
    workspace_root,
    path: str,
    parsed: urllib.parse.ParseResult,
    send_json: SendJson,
) -> bool:
    p = path.rstrip("/") or "/"
    if not p.startswith("/api/ceremonies"):
        return False

    if p == "/api/ceremonies/enabled":
        reg = load_ceremony_bridge_registry()
        send_json(
            200,
            {
                "ok": True,
                "enabled": experimental_ceremony_bridge_b4_enabled(),
                "registry_version": reg.get("registry_version"),
            },
        )
        return True

    if not experimental_ceremony_bridge_b4_enabled():
        send_json(200, _disabled())
        return True

    conn = connect(workspace_root)
    if conn is None:
        send_json(503, {"ok": False, "error": "graph_unavailable"})
        return True

    try:
        if p == "/api/ceremonies/intents":
            send_json(200, intents_payload())
            return True
        if p == "/api/ceremonies/mappings":
            send_json(200, mappings_payload())
            return True

        if p == "/api/ceremonies/templates":
            send_json(200, templates_payload(conn))
            return True
        if p == "/api/ceremonies/instances":
            send_json(200, list_ceremony_instances(conn))
            return True

        if p.startswith("/api/ceremonies/instances/"):
            rest = urllib.parse.unquote(p[len("/api/ceremonies/instances/") :].strip("/"))
            if not rest or "/" in rest:
                send_json(404, {"ok": False, "error": "not_found"})
                return True
            bundle = ceremony_instance_bundle(conn, rest)
            send_json(200 if bundle.get("ok") else 404, bundle)
            return True

        if p.startswith("/api/ceremonies/agenda/"):
            iid = urllib.parse.unquote(p[len("/api/ceremonies/agenda/") :].strip("/"))
            if not iid:
                send_json(404, {"ok": False, "error": "not_found"})
                return True
            send_json(200, agenda_payload(conn, iid))
            return True

        if p.startswith("/api/ceremonies/readiness/"):
            iid = urllib.parse.unquote(p[len("/api/ceremonies/readiness/") :].strip("/"))
            if not iid:
                send_json(404, {"ok": False, "error": "not_found"})
                return True
            send_json(200, readiness_payload(conn, iid))
            return True

        if p.startswith("/api/ceremonies/inspector/"):
            iid = urllib.parse.unquote(p[len("/api/ceremonies/inspector/") :].strip("/"))
            if not iid:
                send_json(404, {"ok": False, "error": "not_found"})
                return True
            send_json(200, mapping_inspector_row(conn, iid))
            return True

    finally:
        conn.close()

    send_json(404, {"ok": False, "error": "not_found"})
    return True


def handle_ceremony_b4_post(
    *,
    workspace_root,
    post_path: str,
    body: dict[str, Any],
    send_json: SendJson,
    client_ip: str,
    may_run_actions,
) -> bool:
    p = post_path.rstrip("/") or "/"
    if not p.startswith("/api/ceremonies"):
        return False

    if not (
        p == "/api/ceremonies/instances"
        or (p.startswith("/api/ceremonies/instances/") and p.endswith("/outputs"))
        or (p.startswith("/api/ceremonies/instances/") and p.endswith("/signoff"))
    ):
        return False

    if not experimental_ceremony_bridge_b4_enabled():
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
        if p == "/api/ceremonies/instances":
            r = create_ceremony_instance(conn, body)
            send_json(201 if r.get("ok") else 400, r)
            return True

        if "/outputs" in p and p.startswith("/api/ceremonies/instances/"):
            inner = p[len("/api/ceremonies/instances/") :]
            if not inner.endswith("/outputs"):
                send_json(404, {"ok": False, "error": "not_found"})
                return True
            iid = urllib.parse.unquote(inner[: -len("/outputs")].strip("/"))
            r = add_ceremony_output(conn, iid, body)
            send_json(201 if r.get("ok") else 400, r)
            return True

        if "/signoff" in p and p.startswith("/api/ceremonies/instances/"):
            inner = p[len("/api/ceremonies/instances/") :]
            if not inner.endswith("/signoff"):
                send_json(404, {"ok": False, "error": "not_found"})
                return True
            iid = urllib.parse.unquote(inner[: -len("/signoff")].strip("/"))
            r = signoff_ceremony(conn, iid, body)
            send_json(200 if r.get("ok") else 400, r)
            return True

        send_json(404, {"ok": False, "error": "not_found"})
        return True
    finally:
        conn.close()
