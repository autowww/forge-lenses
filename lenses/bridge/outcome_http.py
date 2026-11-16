"""HTTP handlers for Sprint B6 PDLC outcome bridge API."""

from __future__ import annotations

import urllib.parse
from typing import Any, Callable

from lenses.bridge.outcome_b6_feature_flag import experimental_outcome_bridge_b6_enabled
from lenses.bridge.outcome_service import (
    create_followon_ore,
    create_launch_record,
    create_outcome_entity,
    explain_scores_for_launch,
    get_launch_bundle,
    link_outcome_to_launch,
    list_launches_for_work_item,
    list_outcomes,
    pdlc_bridge_for_entity,
    trace_outcome_entity,
)
from lenses.bridge.pdlc_outcome_bridge_registry import load_pdlc_outcome_bridge_registry
from lenses.orchestration_graph.db import connect
from lenses.orchestration_graph.query import fetch_entity

SendJson = Callable[[int, dict[str, Any]], None]


def _disabled() -> dict[str, Any]:
    return {"ok": False, "feature_disabled": True}


def handle_outcome_b6_get(
    *,
    workspace_root,
    path: str,
    parsed: urllib.parse.ParseResult,
    send_json: SendJson,
) -> bool:
    p = path.rstrip("/") or "/"
    if not (
        p.startswith("/api/outcomes")
        or p.startswith("/api/launches")
        or p.startswith("/api/pdlc/bridge")
    ):
        return False

    if p == "/api/outcomes/enabled":
        reg = load_pdlc_outcome_bridge_registry()
        send_json(
            200,
            {
                "ok": True,
                "enabled": experimental_outcome_bridge_b6_enabled(),
                "registry_version": reg.get("registry_version"),
            },
        )
        return True

    if not experimental_outcome_bridge_b6_enabled():
        send_json(200, _disabled())
        return True

    conn = connect(workspace_root)
    if conn is None:
        send_json(503, {"ok": False, "error": "graph_unavailable"})
        return True

    try:
        if p == "/api/outcomes":
            send_json(200, list_outcomes(conn))
            return True

        if p.startswith("/api/outcomes/by-work-unit"):
            q = urllib.parse.parse_qs(parsed.query or "")
            wid = str(q.get("work_item_id", [""])[0] or "").strip()
            if not wid:
                send_json(400, {"ok": False, "error": "work_item_id_required"})
                return True
            lids = list_launches_for_work_item(conn, wid)
            send_json(200, {"ok": True, "work_item_id": wid, "launch_ids": lids})
            return True

        if p.startswith("/api/outcomes/") and p.endswith("/trace"):
            inner = urllib.parse.unquote(p[len("/api/outcomes/") : -len("/trace")].strip("/"))
            if not inner or "/" in inner:
                send_json(404, {"ok": False, "error": "not_found"})
                return True
            out = trace_outcome_entity(conn, inner)
            send_json(200 if out.get("ok") else 404, out)
            return True

        if p.startswith("/api/outcomes/") and "/" not in p[len("/api/outcomes/") :].strip("/"):
            inner = urllib.parse.unquote(p[len("/api/outcomes/") :].strip("/"))
            if not inner:
                send_json(404, {"ok": False, "error": "not_found"})
                return True
            ent = fetch_entity(conn, inner)
            if ent is None:
                send_json(404, {"ok": False, "error": "entity_not_found"})
                return True
            k = str(ent.get("kind"))
            scores = explain_scores_for_launch(conn, inner) if k == "launch_record" else None
            send_json(200, {"ok": True, "entity": ent, "scores": scores})
            return True

        if p == "/api/launches":
            send_json(200, list_outcomes(conn))
            return True

        if p.startswith("/api/launches/") and "/" not in p[len("/api/launches/") :].strip("/"):
            lid = urllib.parse.unquote(p[len("/api/launches/") :].strip("/"))
            if not lid:
                send_json(404, {"ok": False, "error": "not_found"})
                return True
            send_json(200, get_launch_bundle(conn, lid))
            return True

        if p.startswith("/api/pdlc/bridge/") and "/" not in p[len("/api/pdlc/bridge/") :].strip("/"):
            eid = urllib.parse.unquote(p[len("/api/pdlc/bridge/") :].strip("/"))
            if not eid:
                send_json(404, {"ok": False, "error": "not_found"})
                return True
            send_json(200, pdlc_bridge_for_entity(conn, eid))
            return True

    finally:
        conn.close()

    send_json(404, {"ok": False, "error": "not_found"})
    return True


def handle_outcome_b6_post(
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
        p.startswith("/api/outcomes")
        or p.startswith("/api/launches")
    ):
        return False

    if not experimental_outcome_bridge_b6_enabled():
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
        if p == "/api/outcomes":
            r = create_outcome_entity(conn, body)
            send_json(201 if r.get("ok") else 400, r)
            return True

        if p.startswith("/api/outcomes/") and p.endswith("/create-followon-ore"):
            inner = urllib.parse.unquote(
                p[len("/api/outcomes/") : -len("/create-followon-ore")].strip("/")
            )
            if not inner or "/" in inner:
                send_json(404, {"ok": False, "error": "not_found"})
                return True
            r = create_followon_ore(conn, inner, body)
            send_json(200 if r.get("ok") else 400, r)
            return True

        if p == "/api/launches":
            r = create_launch_record(conn, body)
            send_json(201 if r.get("ok") else 400, r)
            return True

        if p.startswith("/api/launches/") and p.endswith("/link-outcome"):
            inner = urllib.parse.unquote(
                p[len("/api/launches/") : -len("/link-outcome")].strip("/")
            )
            if not inner or "/" in inner:
                send_json(404, {"ok": False, "error": "not_found"})
                return True
            r = link_outcome_to_launch(conn, inner, body)
            send_json(200 if r.get("ok") else 400, r)
            return True

        send_json(404, {"ok": False, "error": "not_found"})
        return True
    finally:
        conn.close()
