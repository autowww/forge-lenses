"""HTTP handlers for Sprint B2 methodology artifacts API."""

from __future__ import annotations

import json
import urllib.parse
from typing import Any, Callable

from lenses.bridge.methodology_b2_feature_flag import experimental_methodology_bridge_b2_enabled
from lenses.bridge.methodology_b2_registry import load_methodology_b2_registry
from lenses.bridge.methodology_service import (
    build_assay_packet_view,
    build_review_pack_view,
    create_assay_packet,
    create_decision,
    create_review_pack,
    evidence_search,
    get_entity_bundle,
    import_markdown_paths,
    link_entities,
    list_artifacts,
    list_decisions,
    readiness_gaps_for_release,
    signoff_decision,
)
from lenses.orchestration_graph.db import connect

SendJson = Callable[[int, dict[str, Any]], None]


def _disabled() -> dict[str, Any]:
    return {"ok": False, "feature_disabled": True}


def handle_methodology_b2_get(
    *,
    workspace_root,
    path: str,
    parsed: urllib.parse.ParseResult,
    send_json: SendJson,
) -> bool:
    p = path.rstrip("/") or "/"
    if not (
        p.startswith("/api/artifacts")
        or p.startswith("/api/decisions")
        or p.startswith("/api/review-packs")
        or p.startswith("/api/assay-packets")
        or p.startswith("/api/evidence/")
        or p.startswith("/api/methodology/")
    ):
        return False

    if p == "/api/artifacts/enabled":
        reg = load_methodology_b2_registry()
        send_json(
            200,
            {
                "ok": True,
                "enabled": experimental_methodology_bridge_b2_enabled(),
                "registry_version": reg.get("registry_version"),
                "forge_artifact_profiles": list((reg.get("forge_artifact_profiles") or {}).keys()),
                "decision_type_profiles": list((reg.get("decision_type_profiles") or {}).keys()),
            },
        )
        return True

    if not experimental_methodology_bridge_b2_enabled():
        send_json(200, _disabled())
        return True

    conn = connect(workspace_root)
    if conn is None:
        send_json(503, {"ok": False, "error": "graph_unavailable"})
        return True

    try:
        qs = urllib.parse.parse_qs(parsed.query or "")

        if p == "/api/artifacts":
            try:
                limit = int(str(qs.get("limit", ["100"])[0] or "100"))
                offset = int(str(qs.get("offset", ["0"])[0] or "0"))
            except ValueError:
                limit, offset = 100, 0
            send_json(200, list_artifacts(conn, limit=limit, offset=offset))
            return True

        if p.startswith("/api/artifacts/") and not p.endswith("/link"):
            rest = p[len("/api/artifacts/") :].strip("/")
            eid = urllib.parse.unquote(rest)
            if not eid or eid in ("import", "enabled"):
                send_json(404, {"ok": False, "error": "not_found"})
                return True
            bundle = get_entity_bundle(conn, eid)
            send_json(200 if bundle.get("ok") else 404, bundle)
            return True

        if p == "/api/review-packs":
            rows = conn.execute(
                """
                SELECT id, display_name, summary, updated_at FROM ogs_entity
                WHERE kind = 'review_pack' ORDER BY updated_at DESC LIMIT 200
                """
            ).fetchall()
            send_json(
                200,
                {
                    "ok": True,
                    "packs": [
                        {
                            "id": r["id"],
                            "display_name": r["display_name"],
                            "summary": r["summary"] or "",
                            "updated_at": r["updated_at"],
                        }
                        for r in rows
                    ],
                },
            )
            return True

        if p == "/api/assay-packets":
            rows = conn.execute(
                """
                SELECT id, display_name, summary, updated_at FROM ogs_entity
                WHERE kind = 'assay_packet' ORDER BY updated_at DESC LIMIT 200
                """
            ).fetchall()
            send_json(
                200,
                {
                    "ok": True,
                    "packets": [
                        {
                            "id": r["id"],
                            "display_name": r["display_name"],
                            "summary": r["summary"] or "",
                            "updated_at": r["updated_at"],
                        }
                        for r in rows
                    ],
                },
            )
            return True

        if p == "/api/decisions":
            try:
                limit = int(str(qs.get("limit", ["100"])[0] or "100"))
                offset = int(str(qs.get("offset", ["0"])[0] or "0"))
            except ValueError:
                limit, offset = 100, 0
            send_json(200, list_decisions(conn, limit=limit, offset=offset))
            return True

        if p.startswith("/api/decisions/") and p.endswith("/signoff"):
            send_json(404, {"ok": False, "error": "use_post"})
            return True

        if p.startswith("/api/review-packs/"):
            rid = urllib.parse.unquote(p[len("/api/review-packs/") :].strip("/"))
            if not rid:
                send_json(404, {"ok": False, "error": "not_found"})
                return True
            out = build_review_pack_view(conn, rid)
            send_json(200 if out.get("ok") else 404, out)
            return True

        if p.startswith("/api/assay-packets/"):
            aid = urllib.parse.unquote(p[len("/api/assay-packets/") :].strip("/"))
            if not aid:
                send_json(404, {"ok": False, "error": "not_found"})
                return True
            out = build_assay_packet_view(conn, aid)
            send_json(200 if out.get("ok") else 404, out)
            return True

        if p == "/api/evidence/search":
            q = str(qs.get("q", [""])[0] or "").strip()
            try:
                limit = int(str(qs.get("limit", ["50"])[0] or "50"))
            except ValueError:
                limit = 50
            send_json(200, evidence_search(conn, q, limit=limit))
            return True

        if p == "/api/methodology/readiness":
            rid = str(qs.get("release_id", [""])[0] or "").strip()
            send_json(200, readiness_gaps_for_release(conn, rid))
            return True

        if p.startswith("/api/methodology/records/"):
            rid = urllib.parse.unquote(p[len("/api/methodology/records/") :].strip("/"))
            if not rid:
                send_json(404, {"ok": False, "error": "not_found"})
                return True
            bundle = get_entity_bundle(conn, rid)
            send_json(200 if bundle.get("ok") else 404, bundle)
            return True

    finally:
        conn.close()

    send_json(404, {"ok": False, "error": "not_found"})
    return True


def handle_methodology_b2_post(
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
        p == "/api/artifacts/import"
        or p.startswith("/api/artifacts/")
        or p == "/api/decisions"
        or p.startswith("/api/decisions/")
        or p == "/api/review-packs"
        or p == "/api/assay-packets"
    ):
        return False

    if not experimental_methodology_bridge_b2_enabled():
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
        if p == "/api/artifacts/import":
            paths = body.get("paths")
            scan_roots = body.get("scan_roots")
            pl = paths if isinstance(paths, list) else None
            sr = scan_roots if isinstance(scan_roots, list) else None
            out = import_markdown_paths(workspace_root, conn, rel_paths=pl, scan_roots=sr)
            send_json(200, out)
            return True

        if p.startswith("/api/artifacts/") and p.endswith("/link"):
            inner = p[len("/api/artifacts/") : -len("/link")].strip("/")
            eid = urllib.parse.unquote(inner)
            to_id = str(body.get("to_id") or "").strip()
            kind = str(body.get("kind") or "references").strip()
            if not eid or not to_id:
                send_json(400, {"ok": False, "error": "entity_ids_required"})
                return True
            r = link_entities(conn, eid, to_id, kind)
            send_json(200 if r.get("ok") else 400, r)
            return True

        if p == "/api/decisions":
            r = create_decision(conn, body)
            send_json(201 if r.get("ok") else 400, r)
            return True

        if p.startswith("/api/decisions/") and p.endswith("/signoff"):
            inner = p[len("/api/decisions/") : -len("/signoff")].strip("/")
            eid = urllib.parse.unquote(inner)
            r = signoff_decision(conn, eid, body)
            send_json(200 if r.get("ok") else 400, r)
            return True

        if p == "/api/review-packs":
            r = create_review_pack(conn, body)
            send_json(201 if r.get("ok") else 400, r)
            return True

        if p == "/api/assay-packets":
            r = create_assay_packet(conn, body)
            send_json(201 if r.get("ok") else 400, r)
            return True

        send_json(404, {"ok": False, "error": "not_found"})
        return True
    finally:
        conn.close()
