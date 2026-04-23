"""HTTP dispatch for ``/api/bridge/*`` (used from ``serve.py``)."""

from __future__ import annotations

import urllib.parse
from typing import Any, Callable

from lenses.bridge.feature_flag import experimental_bridge_spine_enabled
from lenses.bridge.projection import project_entity
from lenses.bridge.registry import load_bridge_registry, validate_registry_struct
from lenses.bridge.trace_service import (
    bridge_impact_payload,
    bridge_provenance_payload,
    bridge_trace_payload,
    compute_gaps,
    compute_traceability_score,
    immediate_neighbors,
    insert_bridge_link,
    spine_meta_for_entity,
)
from lenses.orchestration_graph.db import connect
from lenses.orchestration_graph.feature_flag import experimental_orchestration_graph_enabled
from lenses.orchestration_graph.query import fetch_entity

SendJson = Callable[[int, dict[str, Any]], None]


def _disabled() -> dict[str, Any]:
    return {"ok": False, "feature_disabled": True}


def handle_bridge_get(
    *,
    workspace_root,
    path: str,
    parsed: urllib.parse.ParseResult,
    send_json: SendJson,
) -> bool:
    if not path.startswith("/api/bridge/"):
        return False

    rest = path[len("/api/bridge/") :].strip("/")
    parts = [p for p in rest.split("/") if p]

    if not parts:
        send_json(404, {"ok": False, "error": "not_found"})
        return True

    if parts[0] == "enabled":
        send_json(
            200,
            {
                "ok": True,
                "enabled": experimental_bridge_spine_enabled(),
                "orchestration_enabled": experimental_orchestration_graph_enabled(),
            },
        )
        return True

    reg = load_bridge_registry()

    if parts[0] == "registry":
        if len(parts) == 1:
            issues = validate_registry_struct(reg)
            send_json(
                200,
                {
                    "ok": True,
                    "validation_issues": issues,
                    "registry": reg.public_payload(),
                },
            )
            return True
        if len(parts) >= 3 and parts[1] == "terms":
            term = "/".join(parts[2:])
            term = urllib.parse.unquote(term)
            row = reg.lookup_neutral_term(term)
            rev = reg.reverse_lookup_labels(term)
            send_json(
                200,
                {
                    "ok": True,
                    "term_query": term,
                    "neutral_entry": row,
                    "reverse_hits": rev,
                    "collisions": reg.term_collisions(),
                },
            )
            return True
        send_json(404, {"ok": False, "error": "not_found"})
        return True

    if not experimental_bridge_spine_enabled():
        send_json(200, _disabled())
        return True

    conn = connect(workspace_root)
    if conn is None:
        send_json(503, {"ok": False, "error": "graph_unavailable"})
        return True

    try:
        if parts[0] == "trace" and len(parts) >= 2:
            root_id = "/".join(parts[1:])
            root_id = urllib.parse.unquote(root_id)
            q = urllib.parse.parse_qs(parsed.query or "")
            md = int(str(q.get("max_depth", ["8"])[0] or "8"))
            mn = int(str(q.get("max_nodes", ["500"])[0] or "500"))
            payload = bridge_trace_payload(conn, root_id, reg, max_depth=md, max_nodes=mn)
            send_json(200, payload)
            return True

        if parts[0] == "impact" and len(parts) >= 2:
            root_id = urllib.parse.unquote("/".join(parts[1:]))
            q = urllib.parse.parse_qs(parsed.query or "")
            md = int(str(q.get("max_depth", ["8"])[0] or "8"))
            mn = int(str(q.get("max_nodes", ["400"])[0] or "400"))
            payload = bridge_impact_payload(conn, root_id, reg, max_depth=md, max_nodes=mn)
            send_json(200, payload)
            return True

        if parts[0] == "provenance" and len(parts) >= 2:
            root_id = urllib.parse.unquote("/".join(parts[1:]))
            q = urllib.parse.parse_qs(parsed.query or "")
            md = int(str(q.get("max_depth", ["8"])[0] or "8"))
            mn = int(str(q.get("max_nodes", ["400"])[0] or "400"))
            payload = bridge_provenance_payload(conn, root_id, reg, max_depth=md, max_nodes=mn)
            send_json(200, payload)
            return True

        if parts[0] == "neighbors" and len(parts) >= 2:
            eid = urllib.parse.unquote("/".join(parts[1:]))
            try:
                cap = int(str(urllib.parse.parse_qs(parsed.query or "").get("max_entities", ["200"])[0] or "200"))
            except ValueError:
                cap = 200
            cap = max(1, min(cap, 500))
            payload = immediate_neighbors(conn, eid, reg, max_neighbor_entities=cap)
            send_json(200 if payload.get("ok") else 404, payload)
            return True

        if parts[0] == "gaps" and len(parts) >= 2:
            root_id = urllib.parse.unquote("/".join(parts[1:]))
            gaps_payload = compute_gaps(conn, root_id, reg)
            score = compute_traceability_score(conn, root_id, reg)
            if not gaps_payload.get("ok"):
                send_json(404, {**gaps_payload, "traceability_score": score})
                return True
            send_json(200, {**gaps_payload, "traceability_score": score})
            return True

        if parts[0] == "projections" and len(parts) >= 2:
            eid = urllib.parse.unquote("/".join(parts[1:]))
            q = urllib.parse.parse_qs(parsed.query or "")
            lens_raw = str(q.get("lens", ["neutral"])[0] or "neutral").lower()
            lens = lens_raw if lens_raw in ("neutral", "forge", "sdlc", "pdlc") else "neutral"
            ent = fetch_entity(conn, eid)
            if ent is None:
                send_json(404, {"ok": False, "error": "entity_not_found", "id": eid})
                return True
            spine_meta = spine_meta_for_entity(conn, eid)
            send_json(
                200,
                {
                    "ok": True,
                    "lens": lens,
                    "projection": project_entity(ent, reg, lens),  # type: ignore[arg-type]
                    "all_lenses": {
                        "neutral": project_entity(ent, reg, "neutral"),
                        "forge": project_entity(ent, reg, "forge"),
                        "sdlc": project_entity(ent, reg, "sdlc"),
                        "pdlc": project_entity(ent, reg, "pdlc"),
                    },
                    "spine_meta": spine_meta,
                    "registry_version": reg.registry_version,
                },
            )
            return True

    finally:
        conn.close()

    send_json(404, {"ok": False, "error": "not_found"})
    return True


def handle_bridge_post(
    *,
    workspace_root,
    post_path: str,
    body: dict[str, Any] | None,
    send_json: SendJson,
    client_ip: str,
    may_run_actions,
) -> bool:
    if post_path.rstrip("/") != "/api/bridge/links":
        return False

    if not experimental_bridge_spine_enabled():
        send_json(404, {"ok": False, "error": "feature_disabled"})
        return True

    if not may_run_actions(client_ip):
        send_json(
            403,
            {"ok": False, "error": "allowed_from_loopback_or_lenses_allow_actions"},
        )
        return True

    if not isinstance(body, dict):
        send_json(400, {"ok": False, "error": "json_body_required"})
        return True

    from_id = str(body.get("from_id") or "").strip()
    to_id = str(body.get("to_id") or "").strip()
    kind = str(body.get("kind") or "").strip()
    if not from_id or not to_id or not kind:
        send_json(400, {"ok": False, "error": "from_id_to_id_kind_required"})
        return True

    conn = connect(workspace_root)
    if conn is None:
        send_json(503, {"ok": False, "error": "graph_unavailable"})
        return True
    try:
        payload = body.get("payload_json")
        pdict = payload if isinstance(payload, dict) else {}
        out = insert_bridge_link(
            conn,
            from_id=from_id,
            to_id=to_id,
            kind=kind,
            source_system=str(body.get("source_system") or "bridge_api"),
            source_record_id=str(body.get("source_record_id") or ""),
            payload=pdict,
        )
        send_json(200 if out.get("ok") else 400, out)
    finally:
        conn.close()
    return True
